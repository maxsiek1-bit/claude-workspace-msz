"""Przygotowanie zanonimizowanych danych (bez numerów seryjnych) dla dashboardu HTML."""
import re

import numpy as np
import pandas as pd

import conpeek
import defects as dfx
import odoo_extract as ox

MODEL_NAMES = {
    "ST01": "Enbio S", "ST02": "Enbio PRO", "ST03": "Enbio PRO UK", "ST04": "Enbio S Beauty",
    "ST05": "Enbio S JP (100V)", "ST06": "Enbio PRO US (120V)", "ST07": "Enbio PRO (EUU)",
    "SR01": "Enbio S – odnowiony", "SR02": "Enbio PRO – odnowiony", "SR03": "Enbio PRO UK – odnowiony",
    "SR04": "Enbio S Beauty – odnowiony", "SR07": "Enbio PRO (EUU) – odnowiony",
}
WARRANTY = {"Warranty replacement", "Warranty repair"}
EPOCH = pd.Timestamp("2024-01-01")
COUNTRY_PL = {
    "Poland": "Polska", "Switzerland": "Szwajcaria", "Italy": "Włochy", "Germany": "Niemcy", "Spain": "Hiszpania",
    "France": "Francja", "United Kingdom": "Wielka Brytania", "Netherlands": "Holandia", "Ireland": "Irlandia",
    "Romania": "Rumunia", "Belgium": "Belgia", "Latvia": "Łotwa", "Portugal": "Portugalia", "Austria": "Austria",
    "Slovenia": "Słowenia", "Croatia": "Chorwacja", "Slovakia": "Słowacja", "Greece": "Grecja", "Hungary": "Węgry",
    "Sweden": "Szwecja", "Bulgaria": "Bułgaria", "Denmark": "Dania", "Lithuania": "Litwa", "Norway": "Norwegia",
    "Estonia": "Estonia", "Czech Republic": "Czechy", "Czechia": "Czechy", "United States": "USA", "Finland": "Finlandia",
    "Algeria": "Algieria", "Israel": "Izrael", "Japan": "Japonia", "India": "Indie", "Cyprus": "Cypr",
    "Luxembourg": "Luksemburg", "Serbia": "Serbia", "Ukraine": "Ukraina", "Turkey": "Turcja", "Canada": "Kanada",
    "Australia": "Australia", "Malta": "Malta", "Iceland": "Islandia", "Bosnia and Herzegovina": "Bośnia i Hercegowina",
}


def line_of(model):
    name = MODEL_NAMES.get(model, model)
    return "Enbio S Beauty" if "Beauty" in name else "Enbio PRO" if "PRO" in name else "Enbio S"


def voltage_of(product):
    p = product or ""
    return "100 V" if "100V" in p or "-JP" in p else "120 V" if ("120V" in p or "-US" in p) else "230 V"


class Index:
    def __init__(self):
        self.items, self.pos = [], {}

    def __call__(self, v):
        v = "(brak)" if v is None or (isinstance(v, float) and np.isnan(v)) else str(v)
        if v not in self.pos:
            self.pos[v] = len(self.items)
            self.items.append(v)
        return self.pos[v]


def _days(ts):
    return int((ts - EPOCH).days)


def build(cache="cache", with_conpeek=True, components=None):
    data = ox.load_all(cache)
    units = ox.device_units(data["mos"])
    units = units[units["model"].isin(MODEL_NAMES)]
    defects = dfx.build(data["tickets"], data["repairs"])
    defects = defects.merge(data["tickets"][["ticket", "ticket_id"]], on="ticket", how="left") \
        .merge(data["ticket_details"], on="ticket_id", how="left")
    ship = data["shipments"].sort_values("shipped_at").drop_duplicates("serial").set_index("serial")
    as_of = max(data["tickets"]["reported_at"].max(), data["mos"]["date_finished"].max()).normalize()

    I = {k: Index() for k in ["model", "line", "volt", "snm", "country", "type", "code", "tcountry", "part", "kind"]}
    out = []
    for u in units.itertuples():
        s = ship.loc[u.serial] if u.serial in ship.index else None
        cust = s["customer"] if s is not None and isinstance(s["customer"], str) else ""
        if s is None:
            ctry = "Niewysłane / brak wydania"
        elif re.search(r"enbio group", cust, re.I):
            ctry = "Enbio Group AG (CH – dystrybucja)"
        else:
            ctry = COUNTRY_PL.get(s["country"], s["country"] if isinstance(s["country"], str) else "(brak)")
        start = s["shipped_at"] if s is not None else u.produced_at
        rec = {
            "m": I["model"](f"{u.model} {MODEL_NAMES[u.model]}"), "l": I["line"](line_of(u.model)),
            "v": I["volt"](voltage_of(u.product)), "k": I["kind"]("Odnowione (SR)" if u.model.startswith("SR") else "Nowe"),
            "n": I["snm"](u.serial[5:7] if re.match(r"^S[TR]\d\d-[A-Z]{2}-", u.serial) else "?"),
            "c": I["country"](ctry), "p": _days(u.produced_at), "s": _days(start), "sh": int(s is not None),
        }
        out.append((u.serial, rec))
    pos = {sn: i for i, (sn, _) in enumerate(out)}
    recs = [r for _, r in out]
    for r in recs:
        r["e"], r["r"] = [], []

    # zgłoszenia: jedno zdarzenie na ticket (z listą kodów)
    d = defects[defects["serial"].isin(pos)]
    for (sn, tk), g in d.groupby(["serial", "ticket"], sort=False):
        r = recs[pos[sn]]
        first = g.iloc[0]
        day = _days(first["reported_at"]) - r["s"]
        ttype = first["ticket_type"] if isinstance(first["ticket_type"], str) else (
            "Naprawa bez zgłoszenia" if first["source"] == "odoo_repair" else "(bez typu)")
        close = (first["closed_at"] - first["reported_at"]).days if pd.notna(first.get("closed_at")) else -1
        r["e"].append([day, I["type"](ttype), sorted({I["code"](c) for c in g["error_code"]}),
                       I["tcountry"](COUNTRY_PL.get(first.get("ticket_country"), first.get("ticket_country"))), close])
    for r in recs:
        r["e"].sort(key=lambda e: e[0])
    parts = data["repair_parts"]
    for p in parts[parts["serial"].isin(pos)].itertuples():
        recs[pos[p.serial]]["r"].append(I["part"](p.part))

    payload = {
        "asOf": _days(as_of), "epoch": str(EPOCH.date()),
        "dims": {k: v.items for k, v in I.items()},
        "units": [[r["m"], r["l"], r["v"], r["k"], r["n"], r["c"], r["p"], r["s"], r["sh"], r["e"], sorted(set(r["r"]))]
                  for r in recs],
        "static": static_sections(data, units, defects, components, with_conpeek),
    }
    return payload


def static_sections(data, units, defects, components, with_conpeek):
    """Sekcje liczone raz (komponenty, partie, Conpeek, urządzenia sprzed Odoo, jakość danych)."""
    import analyze
    st = {}
    u, d = analyze.prepare(units.assign(model=units["model"]), defects)
    if components is not None:
        comp = components[components["serial"].isin(u["serial"])]
        cr = analyze.component_risk(u, comp, "component", 50)
        lr = analyze.component_risk(u, comp, "component_lot", 50)
        keep = ["units", "defective_units", "expected", "defect_rate_%", "lift_vs_cohort", "z_score"]
        st["components"] = cr[["component"] + keep].head(25).values.tolist()
        st["lots"] = lr[["component_lot", "component"] + keep].head(25).values.tolist()
        # studium przypadku: czujnik wytwornicy pary vs E2
        e2 = set(d[d["error_code"].str.startswith("E2 ")]["serial"])
        sg = comp[comp["component"].str.contains("steam gen temp sensor PT1000")].drop_duplicates("serial")
        sg = sg.merge(u[["serial", "produced_at"]], on="serial")
        sg["e2"] = sg["serial"].isin(e2)
        lots = sg.groupby(["component", "component_lot"]).agg(n=("serial", "size"), e2=("e2", "mean"),
                                                             first=("produced_at", "min")).reset_index()
        lots = lots[lots["n"] >= 40].sort_values("first")
        st["sensor_case"] = [[r.component[1:9], r.component_lot, int(r.n), round(100 * r.e2, 1), str(r.first.date())]
                             for r in lots.itertuples()]
    st["legacy"] = analyze.legacy_devices(d).fillna("").values.tolist()
    st["legacy_cols"] = list(analyze.legacy_devices(d).columns)
    t = data["tickets"]
    st["quality"] = {
        "tickets": int(len(t)),
        "tickets_with_sn": int(t["serial"].notna().sum()),
        "defect_tickets": int(defects["ticket"].nunique()),
        "defect_tickets_matched": int(d.dropna(subset=["cohort"])["ticket"].nunique()),
        "defect_tickets_legacy": int(d[d["cohort"].isna()]["ticket"].nunique()),
        "units": int(len(units)),
        "units_shipped": int(units["serial"].isin(data["shipments"]["serial"]).sum()),
        "mos": int(len(data["mos"])), "consumption": int(len(data["consumption"])),
    }
    if with_conpeek:
        dialogs = conpeek.fetch_dialogs()
        tr = conpeek.call_error_trend(dialogs)
        months = [c for c in tr.columns if re.match(r"\d{4}-\d{2}", str(c))]
        st["conpeek"] = {"months": months, "rows": [[r["error_code"], [int(r[m]) for m in months]]
                                                    for _, r in tr.iterrows()]}
        cats = pd.Series([(x.get("category_name") or "(bez kategorii)").split("/")[0].strip() for x in dialogs])
        st["conpeek"]["total"] = len(dialogs)
        st["conpeek"]["by_group"] = cats.value_counts().head(10).reset_index().values.tolist()
    return st
