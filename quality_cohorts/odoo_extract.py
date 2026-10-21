"""Pobieranie danych z Odoo 16 (XML-RPC) i budowa genealogii numerów seryjnych urządzeń.

Surowe dane są zapisywane w katalogu cache (pickle), żeby kolejne analizy nie pobierały
ponownie ~5 mln linii zużycia komponentów.
"""
import os
import re
import time
import xmlrpc.client
from pathlib import Path

import pandas as pd

BATCH = 20000
# Numer seryjny urządzenia, np. ST04-PL-24-04037, ST02-CH-23-01014, SR01-PL-22-00012
DEVICE_SN = r"^S[TR]\d\d"
# Wyroby, które nie są pierwotną produkcją urządzenia (serwis, wymiany, refurbish)
NOT_ORIGINAL = re.compile(r"under repair|refurb|exchange", re.I)


class Odoo:
    def __init__(self, url=None, db=None, user=None, key=None):
        self.url = (url or os.environ["ODOO_URL"]).rstrip("/")
        self.db = db or os.environ["ODOO_DB"]
        self.user = user or os.environ["ODOO_USER"]
        self.key = key or os.environ["ODOO_API_KEY"]
        common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common", allow_none=True)
        self.uid = common.authenticate(self.db, self.user, self.key, {})
        if not self.uid:
            raise RuntimeError("Logowanie do Odoo nieudane – sprawdź ODOO_USER / ODOO_API_KEY")
        self.models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object", allow_none=True)

    def call(self, model, method, *args, **kw):
        for attempt in range(5):
            try:
                return self.models.execute_kw(self.db, self.uid, self.key, model, method, list(args), kw)
            except (OSError, xmlrpc.client.ProtocolError):
                if attempt == 4:
                    raise
                time.sleep(2 ** attempt)

    def has_model(self, model):
        return bool(self.call("ir.model", "search_count", [("model", "=", model)]))

    def fields(self, model):
        return set(self.call(model, "fields_get", attributes=["type"]))

    def search_read(self, model, domain, fields, log=None):
        """Stronicowanie po id (szybsze niż offset przy milionach rekordów)."""
        out, last = [], 0
        while True:
            rows = self.call(model, "search_read", domain + [("id", ">", last)], fields=fields, limit=BATCH, order="id")
            out += rows
            if log:
                print(f"  {model}: {len(out)}", flush=True)
            if len(rows) < BATCH:
                return out
            last = rows[-1]["id"]


def _name(m2o):
    return m2o[1] if m2o else None


def _id(m2o):
    return m2o[0] if m2o else None


def _cached(cache, name, fn, refresh=False):
    p = Path(cache) / f"{name}.pkl"
    if p.exists() and not refresh:
        return pd.read_pickle(p)
    df = fn()
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_pickle(p)
    return df


def fetch_mos(odoo):
    rows = odoo.search_read("mrp.production", [("state", "=", "done")],
                            ["name", "product_id", "lot_producing_id", "date_finished"], log=True)
    return pd.DataFrame({
        "mo": [r["name"] for r in rows],
        "product": [_name(r["product_id"]) for r in rows],
        "lot_id": [_id(r["lot_producing_id"]) for r in rows],
        "lot": [_name(r["lot_producing_id"]) for r in rows],
        "date_finished": pd.to_datetime([r["date_finished"] for r in rows]),
    })


def fetch_consumption(odoo):
    rows = odoo.search_read("stock.move.line",
                            [("move_id.raw_material_production_id", "!=", False), ("state", "=", "done")],
                            ["reference", "product_id", "lot_id", "qty_done"], log=True)
    df = pd.DataFrame({
        "mo": [r["reference"] for r in rows],
        "product_id": [_id(r["product_id"]) for r in rows],
        "product": [_name(r["product_id"]) for r in rows],
        "lot_id": [_id(r["lot_id"]) for r in rows],
        "lot": [_name(r["lot_id"]) for r in rows],
        "qty": [r["qty_done"] for r in rows],
    })
    for c in ("mo", "product", "lot"):
        df[c] = df[c].astype("category")
    return df


def fetch_tickets(odoo):
    rows = odoo.search_read("helpdesk.ticket", [],
                            ["name", "product_serial_number", "create_date", "tag_ids", "ticket_type_id", "team_id",
                             "partner_id", "repair_report_ids"], log=True)
    tags = {t["id"]: t["name"] for t in odoo.call("helpdesk.tag", "search_read", [], fields=["name"])}
    return pd.DataFrame({
        "ticket_id": [r["id"] for r in rows],
        "ticket": [r["name"] for r in rows],
        "serial": [(r["product_serial_number"] or "").strip().upper() or None for r in rows],
        "reported_at": pd.to_datetime([r["create_date"] for r in rows]),
        "tags": [[tags.get(t, str(t)) for t in r["tag_ids"]] for r in rows],
        "ticket_type": [_name(r["ticket_type_id"]) for r in rows],
        "team": [_name(r["team_id"]) for r in rows],
        "partner": [_name(r["partner_id"]) for r in rows],
    })


def fetch_repairs(odoo):
    rows = odoo.search_read("repair.order", [("lot_id", "!=", False)],
                            ["name", "lot_id", "product_id", "create_date", "tag_ids", "ticket_id"], log=True)
    return pd.DataFrame({
        "repair": [r["name"] for r in rows],
        "serial": [(_name(r["lot_id"]) or "").strip().upper() for r in rows],
        "reported_at": pd.to_datetime([r["create_date"] for r in rows]),
        "ticket_id": [_id(r["ticket_id"]) for r in rows],
    })


def fetch_repair_parts(odoo):
    """Części dodane (wymienione) w naprawach, przypisane do numeru seryjnego naprawianego urządzenia."""
    orders = {r["id"]: r for r in odoo.search_read("repair.order", [("lot_id", "!=", False)], ["lot_id", "create_date"])}
    rows = odoo.search_read("repair.line", [("type", "=", "add")], ["repair_id", "product_id", "product_uom_qty"], log=True)
    out = []
    for r in rows:
        o = orders.get(_id(r["repair_id"]))
        if o:
            out.append({"serial": (_name(o["lot_id"]) or "").strip().upper(), "repaired_at": o["create_date"],
                        "part": _name(r["product_id"]), "qty": r["product_uom_qty"]})
    df = pd.DataFrame(out, columns=["serial", "repaired_at", "part", "qty"])
    df["repaired_at"] = pd.to_datetime(df["repaired_at"])
    return df


def load_all(cache="cache", refresh=False):
    odoo = Odoo()
    return {
        "mos": _cached(cache, "mos", lambda: fetch_mos(odoo), refresh),
        "consumption": _cached(cache, "consumption", lambda: fetch_consumption(odoo), refresh),
        "tickets": _cached(cache, "tickets", lambda: fetch_tickets(odoo), refresh),
        "repairs": _cached(cache, "repairs", lambda: fetch_repairs(odoo), refresh),
        "repair_parts": _cached(cache, "repair_parts", lambda: fetch_repair_parts(odoo), refresh),
    }


def device_units(mos):
    """Jedno urządzenie = numer seryjny; data produkcji = pierwsze zakończone MO wyrobu z tym numerem."""
    d = mos[mos["lot"].fillna("").str.upper().str.match(DEVICE_SN) & ~mos["product"].fillna("").str.contains(NOT_ORIGINAL)]
    d = d.assign(serial=d["lot"].str.strip().str.upper())
    # wyrób najwyższego poziomu = ostatnie MO (pakowanie); kohorta = pierwsze MO (start produkcji)
    first = d.sort_values("date_finished").groupby("serial")
    units = pd.DataFrame({
        "produced_at": first["date_finished"].first(),
        "packed_at": first["date_finished"].last(),
        "product": first["product"].last(),
        "top_mo": first["mo"].last(),
    }).reset_index()
    units["model"] = units["serial"].str[:4]
    return units


def genealogy(units, mos, consumption, cutoff=None, max_depth=8):
    """Wszystkie komponenty (z partiami) zużyte w pierwotnym drzewie produkcji każdego urządzenia.

    cutoff: Series serial -> data; zlecenia urządzenia zakończone później (np. ponowne pakowanie
    po naprawie) są pomijane, żeby części z serwisu nie wyglądały na przyczynę usterki.
    """
    producer = mos.dropna(subset=["lot_id"]).sort_values("date_finished") \
        .drop_duplicates("lot_id")[["lot_id", "mo"]].rename(columns={"mo": "child_mo"})
    producer = producer[~producer["child_mo"].isin(set())]
    cons = consumption[["mo", "product", "lot", "lot_id"]].copy()
    cons["mo"] = cons["mo"].astype(str)
    # wszystkie MO danego numeru seryjnego (montaż, walidacja, pakowanie) są korzeniami drzewa
    dev = mos[mos["lot"].fillna("").str.upper().str.match(DEVICE_SN) & ~mos["product"].fillna("").str.contains(NOT_ORIGINAL)]
    frontier = dev.assign(serial=dev["lot"].str.strip().str.upper())[["serial", "mo", "date_finished"]]
    frontier = frontier[frontier["serial"].isin(units["serial"])]
    if cutoff is not None:
        frontier = frontier[frontier["date_finished"] <= frontier["serial"].map(cutoff).fillna(pd.Timestamp.max)]
    frontier = frontier[["serial", "mo"]].drop_duplicates()
    seen = set(frontier["mo"])
    parts = []
    for depth in range(1, max_depth + 1):
        if frontier.empty:
            break
        lvl = frontier.merge(cons, on="mo").drop(columns="mo")
        lvl["depth"] = depth
        parts.append(lvl[["serial", "product", "lot", "depth", "lot_id"]])
        nxt = lvl.merge(producer, on="lot_id")[["serial", "child_mo"]].rename(columns={"child_mo": "mo"})
        nxt = nxt[~nxt["mo"].isin(seen)].drop_duplicates()
        seen |= set(nxt["mo"])
        frontier = nxt
        print(f"  poziom {depth}: {len(lvl)} linii, kolejne MO: {nxt['mo'].nunique()}", flush=True)
    comp = pd.concat(parts, ignore_index=True)
    comp = comp.rename(columns={"product": "component", "lot": "component_lot"})
    comp["component"] = comp["component"].astype(str)
    comp["component_lot"] = comp["component_lot"].astype(str)
    return comp.drop(columns="lot_id")
