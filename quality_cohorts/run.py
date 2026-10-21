"""Raport wadliwości po kohortach numerów seryjnych (Odoo + Conpeek).

Przykłady:
  python run.py --demo
  python run.py --period M            # Odoo + API Conpeek
Zmienne środowiskowe: ODOO_URL, ODOO_DB, ODOO_USER, ODOO_API_KEY, CONPEEK_URL, CONPEEK_KEY
"""
import argparse
import html
from pathlib import Path

import numpy as np
import pandas as pd

import analyze


def demo_data(n=6000, seed=7):
    rng = np.random.default_rng(seed)
    start = pd.Timestamp("2023-01-01")
    produced = start + pd.to_timedelta(np.sort(rng.integers(0, 1000, n)), unit="D")
    units = pd.DataFrame({"serial": [f"EN{100000 + i}" for i in range(n)], "product": "Enbio PRO",
                          "produced_at": produced, "mo": [f"MO/{i // 20:05d}" for i in range(n)]})
    comp_rows, risk = [], np.full(n, 0.03)
    for comp, lots in {"Grzałka H-200": 6, "Płyta główna PCB v3": 8, "Pompa P-12": 5, "Uszczelka komory": 10}.items():
        lot_idx = np.minimum((np.arange(n) / n * lots).astype(int) + rng.integers(0, 2, n), lots - 1)
        names = np.array([f"{comp[:3].upper()}-L{j:02d}" for j in range(lots)])[lot_idx]
        if comp == "Pompa P-12":
            risk += np.where(lot_idx == 2, 0.12, 0)
        if comp == "Płyta główna PCB v3":
            risk += np.where(lot_idx == 5, 0.06, 0)
        comp_rows.append(pd.DataFrame({"serial": units.serial, "component": comp, "component_lot": names, "qty": 1}))
    components = pd.concat(comp_rows)
    hit = rng.random(n) < risk
    codes = np.where(risk[hit] > 0.1, rng.choice(["E07 ciśnienie", "E12 czas cyklu"], hit.sum()),
                     rng.choice(["E03 temperatura", "E12 czas cyklu", "E21 komunikacja", "E07 ciśnienie"], hit.sum()))
    delay = rng.exponential(150, hit.sum()).astype(int)
    defects = pd.DataFrame({"serial": units.serial[hit].values, "reported_at": units.produced_at[hit].values
                            + pd.to_timedelta(delay, unit="D"), "error_code": codes, "source": "conpeek"})
    defects = defects[defects.reported_at < pd.Timestamp.today()]
    return units, components, defects


def heat(v, vmax):
    if pd.isna(v) or not isinstance(v, (int, float, np.number)) or vmax <= 0:
        return ""
    a = min(float(v) / vmax, 1) * 0.6
    return f' style="background:rgba(214,69,65,{a:.2f})"'


def to_html(sheets, path, title):
    parts = [f"<!doctype html><meta charset=utf-8><title>{title}</title><style>"
             "body{font:13px system-ui;margin:24px;color:#222}table{border-collapse:collapse;margin:8px 0 28px}"
             "td,th{border:1px solid #ddd;padding:3px 7px;text-align:right}th{background:#f3f3f3;position:sticky;top:0}"
             "td:first-child{text-align:left}</style>", f"<h1>{title}</h1>"]
    heat_cols = {"defect_rate_%", "lift_vs_avg"}
    for name, df in sheets.items():
        if name in ("Numery seryjne", "Komponenty x kohorta"):
            continue
        parts.append(f"<h2>{name}</h2><table><tr>" + "".join(f"<th>{html.escape(str(c))}</th>" for c in df.columns) + "</tr>")
        num = df.select_dtypes("number")
        matrix = name in ("Krzywa kohort", "Błędy x kohorta", "Partie x błędy")
        vmax = num.drop(columns=["TOTAL"], errors="ignore").max().max() if matrix and not num.empty else 0
        for _, row in df.head(60).iterrows():
            cells = []
            for c, v in row.items():
                hv = vmax if matrix and c != "TOTAL" else (num[c].max() if c in heat_cols else 0)
                txt = "" if pd.isna(v) else html.escape(str(v))
                cells.append(f"<td{heat(v, hv) if hv else ''}>{txt}</td>")
            parts.append("<tr>" + "".join(cells) + "</tr>")
        parts.append("</table>")
    Path(path).write_text("\n".join(parts), encoding="utf-8")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--demo", action="store_true", help="dane syntetyczne do sprawdzenia raportu")
    p.add_argument("--conpeek-file", nargs="*", default=[], help="eksport(y) zgłoszeń z Conpeek (CSV/XLSX) zamiast API")
    p.add_argument("--no-conpeek-api", action="store_true", help="nie pobieraj zgłoszeń z API Conpeek")
    p.add_argument("--no-odoo-defects", action="store_true", help="nie bierz zgłoszeń z Odoo (helpdesk/naprawy/jakość)")
    p.add_argument("--products", nargs="*", help="filtr: kody wewnętrzne wyrobów gotowych")
    p.add_argument("--period", default="M", choices=["W", "M", "Q", "Y"], help="długość kohorty")
    p.add_argument("--min-units", type=int, default=10)
    p.add_argument("--out", default="output")
    a = p.parse_args()

    if a.demo:
        units, components, defects = demo_data()
    else:
        import conpeek
        import odoo_extract
        odoo = odoo_extract.Odoo()
        units, components = odoo_extract.extract_units_and_components(odoo, a.products)
        frames = [conpeek.load_file(f) for f in a.conpeek_file]
        if not a.no_conpeek_api and not a.conpeek_file:
            frames.append(conpeek.load_api(units["serial"].dropna().unique()))
        if not a.no_odoo_defects:
            frames.append(odoo_extract.extract_defects(odoo))
        defects = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=["serial", "reported_at", "error_code", "source"])

    sheets = analyze.run_all(units, components, defects, a.period, a.min_units)
    out = Path(a.out)
    out.mkdir(exist_ok=True)
    with pd.ExcelWriter(out / "wadliwosc_kohorty.xlsx") as xw:
        for name, df in sheets.items():
            df.to_excel(xw, sheet_name=name[:31], index=False)
    to_html(sheets, out / "wadliwosc_kohorty.html", "Wadliwość urządzeń wg kohort produkcyjnych")
    s = sheets["Kohorty"]
    print(f"Jednostek: {s.produced.sum()}, wadliwych: {s.defective_units.sum()} "
          f"({100 * s.defective_units.sum() / max(s.produced.sum(), 1):.2f}%), kohort: {len(s)}, "
          f"niedopasowanych SN w zgłoszeniach: {len(sheets['Niedopasowane SN'])}")
    print(f"Zapisano: {out / 'wadliwosc_kohorty.xlsx'}, {out / 'wadliwosc_kohorty.html'}")


if __name__ == "__main__":
    main()
