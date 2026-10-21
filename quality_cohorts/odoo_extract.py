"""Pobieranie danych produkcyjnych i reklamacyjnych z Odoo 16 przez XML-RPC.

Wynik (DataFrame'y):
  units       – jeden wiersz na wyprodukowany numer seryjny (serial, product, produced_at, mo)
  components  – komponenty zużyte na MO danego numeru seryjnego (serial, component, component_lot, qty)
  defects     – zgłoszenia/naprawy z Odoo powiązane z numerem seryjnym (serial, reported_at, error_code, source)
"""
import os
import xmlrpc.client

import pandas as pd

BATCH = 2000


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
        return self.models.execute_kw(self.db, self.uid, self.key, model, method, list(args), kw)

    def has_model(self, model):
        return bool(self.call("ir.model", "search_count", [("model", "=", model)]))

    def fields(self, model):
        return set(self.call(model, "fields_get", attributes=["type"]))

    def search_read(self, model, domain, fields):
        out, offset = [], 0
        while True:
            rows = self.call(model, "search_read", domain, fields=fields, limit=BATCH, offset=offset, order="id")
            out += rows
            if len(rows) < BATCH:
                return out
            offset += BATCH


def _name(m2o):
    return m2o[1] if m2o else None


def _id(m2o):
    return m2o[0] if m2o else None


def extract_units_and_components(odoo, product_filter=None):
    """Numery seryjne z zakończonych zleceń produkcyjnych oraz komponenty z tych zleceń."""
    mo_domain = [("state", "=", "done")]
    if product_filter:
        mo_domain.append(("product_id.default_code", "in", product_filter))
    mos = odoo.search_read("mrp.production", mo_domain, ["name", "product_id", "date_finished"])
    mo_by_id = {m["id"]: m for m in mos}
    mo_ids = list(mo_by_id)

    # Wyroby gotowe: linie ruchów wyjściowych MO z numerem seryjnym (obsługuje MO > 1 szt.)
    fin_moves = odoo.search_read("stock.move", [("production_id", "in", mo_ids), ("state", "=", "done")],
                                 ["production_id"])
    fin_move_mo = {m["id"]: _id(m["production_id"]) for m in fin_moves}
    fin_lines = odoo.search_read("stock.move.line", [("move_id", "in", list(fin_move_mo)), ("lot_id", "!=", False)],
                                 ["move_id", "lot_id", "product_id", "date"])
    units = []
    for ln in fin_lines:
        mo = mo_by_id[fin_move_mo[_id(ln["move_id"])]]
        units.append({
            "serial": _name(ln["lot_id"]),
            "product": _name(ln["product_id"]),
            "produced_at": mo["date_finished"] or ln["date"],
            "mo": mo["name"],
            "mo_id": mo["id"],
        })

    # Komponenty: ruchy surowcowe MO
    raw_moves = odoo.search_read("stock.move", [("raw_material_production_id", "in", mo_ids), ("state", "=", "done")],
                                 ["raw_material_production_id"])
    raw_move_mo = {m["id"]: _id(m["raw_material_production_id"]) for m in raw_moves}
    raw_lines = odoo.search_read("stock.move.line", [("move_id", "in", list(raw_move_mo))],
                                 ["move_id", "product_id", "lot_id", "qty_done"])
    comps = [{
        "mo_id": raw_move_mo[_id(ln["move_id"])],
        "component": _name(ln["product_id"]),
        "component_lot": _name(ln["lot_id"]),
        "qty": ln["qty_done"],
    } for ln in raw_lines]

    units = pd.DataFrame(units, columns=["serial", "product", "produced_at", "mo", "mo_id"])
    units["produced_at"] = pd.to_datetime(units["produced_at"])
    comps = pd.DataFrame(comps, columns=["mo_id", "component", "component_lot", "qty"])
    components = units[["serial", "mo_id"]].merge(comps, on="mo_id").drop(columns="mo_id")
    return units.drop(columns="mo_id"), components


# model -> (pole daty, pola kandydujące na "kod błędu"/opis)
DEFECT_SOURCES = {
    "helpdesk.ticket": ("create_date", ["tag_ids", "ticket_type_id", "name"]),
    "repair.order": ("create_date", ["tag_ids", "name"]),
    "quality.alert": ("create_date", ["reason_id", "tag_ids", "name"]),
}


def extract_defects(odoo):
    """Zgłoszenia z Odoo, które mają przypięty numer seryjny (lot_id)."""
    rows = []
    for model, (date_field, label_fields) in DEFECT_SOURCES.items():
        if not odoo.has_model(model):
            continue
        avail = odoo.fields(model)
        if "lot_id" not in avail:
            continue
        labels = [f for f in label_fields if f in avail]
        recs = odoo.search_read(model, [("lot_id", "!=", False)], ["lot_id", date_field] + labels)
        tag_names = {}
        if "tag_ids" in labels:
            tag_model = odoo.call(model, "fields_get", ["tag_ids"], attributes=["relation"])["tag_ids"]["relation"]
            ids = sorted({t for r in recs for t in r["tag_ids"]})
            if ids:
                tag_names = {t["id"]: t["name"] for t in odoo.call(tag_model, "read", ids, fields=["name"])}
        for r in recs:
            code = None
            for f in labels:
                v = r.get(f)
                if f == "tag_ids" and v:
                    code = ", ".join(tag_names.get(t, str(t)) for t in v)
                elif isinstance(v, list) and v:
                    code = v[1]
                elif isinstance(v, str) and v:
                    code = v
                if code:
                    break
            rows.append({"serial": _name(r["lot_id"]), "reported_at": r[date_field],
                         "error_code": code, "source": model})
    df = pd.DataFrame(rows, columns=["serial", "reported_at", "error_code", "source"])
    df["reported_at"] = pd.to_datetime(df["reported_at"])
    return df
