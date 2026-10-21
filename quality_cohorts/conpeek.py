"""Zgłoszenia serwisowe z Conpeek (API v1.3) jako błędy urządzeń.

Numer seryjny szukany jest we wszystkich polach tekstowych zgłoszenia (nazwa, opis,
pola dodatkowe) i dopasowywany do numerów seryjnych znanych z produkcji Odoo.
Kod błędu = kategoria zgłoszenia, a gdy jej brak – tagi.
Zmienne środowiskowe: CONPEEK_URL (adres serwera API), CONPEEK_KEY (klucz aplikacji).
Dodatkowo obsługiwany jest eksport CSV/XLSX (load_file).
"""
import json
import os
import re

import pandas as pd
import requests

PAGE = 1000
TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9/_.-]{3,}")


class Conpeek:
    def __init__(self, url=None, key=None):
        self.url = (url or os.environ["CONPEEK_URL"]).rstrip("/")
        self.s = requests.Session()
        self.s.headers.update({"Authorization": key or os.environ["CONPEEK_KEY"], "Content-Type": "application/json"})

    def get(self, path, **params):
        r = self.s.get(f"{self.url}/{path.lstrip('/')}", params=params, timeout=60)
        r.raise_for_status()
        return r.json()["data"]

    def tickets(self, created_from=None):
        flt = [{"property": "filter_from_created_date", "value": created_from}] if created_from else None
        out, offset = [], 0
        while True:
            params = {"limit": PAGE, "offset": offset}
            if flt:
                params["filter"] = json.dumps(flt)
            rows = self.get("/ticket", **params)
            out += rows
            if len(rows) < PAGE:
                return out
            offset += PAGE


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _strings(v)


def load_api(known_serials, created_from=None, client=None):
    cp = client or Conpeek()
    tags = {t.get("id", t.get("_id")): t.get("name") for t in cp.get("/custom_tag")}
    known = {s.upper(): s for s in known_serials}
    rows = []
    for t in cp.tickets(created_from):
        found = {known[tok.upper()] for txt in _strings(t) for tok in TOKEN.findall(txt) if tok.upper() in known}
        code = t.get("category_name") or ", ".join(str(tags.get(x, x)) for x in t.get("tags") or []) or None
        for sn in found:
            rows.append({"serial": sn, "reported_at": t.get("created_date"), "error_code": code,
                         "source": "conpeek", "ticket": t.get("ticket_number"), "state": t.get("state")})
    df = pd.DataFrame(rows, columns=["serial", "reported_at", "error_code", "source", "ticket", "state"])
    df["reported_at"] = pd.to_datetime(df["reported_at"])
    return df


COLUMN_MAP = {
    # "Numer seryjny": "serial",
    # "Data utworzenia": "reported_at",
    # "Kategoria": "error_code",
}
REQUIRED = ["serial", "reported_at", "error_code"]


def load_file(path):
    df = pd.read_excel(path) if str(path).lower().endswith((".xlsx", ".xls")) else pd.read_csv(path, sep=None, engine="python")
    df = df.rename(columns=COLUMN_MAP)
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Brak kolumn {missing} w {path}; dostępne: {list(df.columns)} – uzupełnij COLUMN_MAP")
    df = df[REQUIRED].copy()
    df["serial"] = df["serial"].astype(str).str.strip()
    df["reported_at"] = pd.to_datetime(df["reported_at"], dayfirst=True, errors="coerce")
    df["source"] = "conpeek"
    return df


def fetch_dialogs(client=None):
    cp = client or Conpeek()
    out, offset = [], 0
    while True:
        rows = cp.get("/cdr_dialog", limit=500, offset=offset)
        out += rows
        if len(rows) < 500:
            return out
        offset += 500


def call_error_trend(dialogs):
    """Połączenia z kategorią usterki (E-kody i opisowe) per miesiąc – Conpeek nie zapisuje numerów
    seryjnych, więc to sygnał trendu, a nie dane na poziomie urządzenia."""
    import defects as dfx
    rows = []
    for d in dialogs:
        cat = (d.get("category_name") or "").strip()
        if not cat or not re.search(r"autoclave|\bE\s?\d|failure|leak|damage|door|drawer|vacuum|wet load", cat, re.I):
            continue
        code = dfx.normalize_code(cat)
        if re.search(r"periodic maintenance", code or "", re.I):
            continue
        rows.append({"month": str(pd.Timestamp(d["start_time"]).to_period("M")), "error_code": dfx.label(code)})
    df = pd.DataFrame(rows, columns=["month", "error_code"])
    return df.pivot_table(index="error_code", columns="month", aggfunc="size", fill_value=0) \
        .assign(TOTAL=lambda x: x.sum(axis=1)).sort_values("TOTAL", ascending=False).reset_index()
