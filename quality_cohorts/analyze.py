"""Analiza wadliwości po kohortach produkcyjnych numerów seryjnych."""
import pandas as pd


def prepare(units, defects, period="M"):
    units = units.drop_duplicates("serial").copy()
    units["cohort"] = units["produced_at"].dt.to_period(period).astype(str)
    defects = defects.dropna(subset=["serial"]).copy()
    defects["serial"] = defects["serial"].astype(str).str.strip()
    defects = defects.merge(units[["serial", "cohort", "produced_at", "product"]], on="serial", how="left")
    defects["error_code"] = defects["error_code"].fillna("(brak kodu)")
    defects["months_in_field"] = ((defects["reported_at"] - defects["produced_at"]).dt.days // 30).clip(lower=0)
    units["defective"] = units["serial"].isin(defects["serial"])
    return units, defects


def cohort_summary(units, defects):
    s = units.groupby("cohort").agg(produced=("serial", "size"), defective_units=("defective", "sum"))
    s["defect_rate_%"] = (100 * s["defective_units"] / s["produced"]).round(2)
    known = defects.dropna(subset=["cohort"])
    s["defect_reports"] = known.groupby("cohort").size()
    top = (known.groupby(["cohort", "error_code"]).size().rename("n").reset_index()
           .sort_values(["cohort", "n"], ascending=[True, False]).groupby("cohort").head(3))
    s["top_errors"] = top.groupby("cohort").apply(lambda g: "; ".join(f"{e} ({n})" for e, n in zip(g.error_code, g.n)))
    s["cumulative_defect_rate_%"] = (100 * s["defective_units"].cumsum() / s["produced"].cumsum()).round(2)
    return s.fillna({"defect_reports": 0, "top_errors": ""}).reset_index()


def cohort_matrix(units, defects, max_months=24):
    """% numerów seryjnych z kohorty, które miały pierwszą awarię do N miesięcy od produkcji (narastająco)."""
    first = defects.dropna(subset=["cohort"]).groupby("serial").agg(cohort=("cohort", "first"), m=("months_in_field", "min"))
    first["m"] = first["m"].clip(upper=max_months)
    counts = first.pivot_table(index="cohort", columns="m", values="cohort", aggfunc="size", fill_value=0)
    counts = counts.reindex(columns=range(int(first["m"].max()) + 1 if len(first) else 1), fill_value=0).cumsum(axis=1)
    produced = units.groupby("cohort").size()
    m = (100 * counts.div(produced, axis=0)).reindex(produced.index).fillna(0).round(2)
    # ukryj miesiące, które dla danej kohorty jeszcze nie minęły
    today = pd.Timestamp.today().to_period("M")
    for c in m.index:
        age = (today - pd.Period(c).asfreq("M", "start")).n
        m.loc[c, [col for col in m.columns if col > age]] = None
    m.columns = [f"M{c}" for c in m.columns]
    return m.reset_index()


def errors_by_cohort(defects):
    d = defects.dropna(subset=["cohort"])
    return d.pivot_table(index="error_code", columns="cohort", values="serial", aggfunc="nunique", fill_value=0) \
        .assign(TOTAL=lambda x: x.sum(axis=1)).sort_values("TOTAL", ascending=False).reset_index()


def component_risk(units, components, key="component", min_units=10):
    """Wadliwość jednostek zawierających dany komponent / partię komponentu vs średnia (lift)."""
    base = units["defective"].mean() or 1e-9
    c = components.dropna(subset=[key]).drop_duplicates(["serial", key]) \
        .merge(units[["serial", "defective"]], on="serial")
    r = c.groupby(key).agg(units=("serial", "nunique"), defective_units=("defective", "sum"))
    r = r[r["units"] >= min_units]
    r["defect_rate_%"] = (100 * r["defective_units"] / r["units"]).round(2)
    r["lift_vs_avg"] = (r["defective_units"] / r["units"] / base).round(2)
    r["share_of_defective_%"] = (100 * r["defective_units"] / max(units["defective"].sum(), 1)).round(1)
    if key == "component_lot":
        r = r.join(c.drop_duplicates(key).set_index(key)["component"])
    return r.sort_values(["lift_vs_avg", "defective_units"], ascending=False).reset_index()


def component_by_cohort(units, components):
    c = components.drop_duplicates(["serial", "component"]).merge(units[["serial", "cohort", "defective"]], on="serial")
    g = c.groupby(["cohort", "component"]).agg(units=("serial", "nunique"), defective_units=("defective", "sum")).reset_index()
    g["defect_rate_%"] = (100 * g["defective_units"] / g["units"]).round(2)
    return g


def component_error_matrix(units, components, defects, key="component_lot", top=30):
    """Które partie komponentów współwystępują z którymi kodami błędów."""
    d = defects.dropna(subset=["cohort"])[["serial", "error_code"]].drop_duplicates()
    c = components.dropna(subset=[key])[["serial", key]].drop_duplicates()
    m = c.merge(d, on="serial").pivot_table(index=key, columns="error_code", values="serial", aggfunc="nunique", fill_value=0)
    m["TOTAL"] = m.sum(axis=1)
    return m.sort_values("TOTAL", ascending=False).head(top).reset_index()


def serial_detail(units, defects):
    agg = defects.groupby("serial").agg(first_report=("reported_at", "min"), reports=("error_code", "size"),
                                        error_codes=("error_code", lambda s: "; ".join(sorted(set(s)))),
                                        sources=("source", lambda s: ", ".join(sorted(set(s)))))
    return units.merge(agg, on="serial", how="left").sort_values(["cohort", "serial"])


def unmatched(defects):
    """Zgłoszenia z numerem seryjnym, którego nie ma w produkcji Odoo – do weryfikacji jakości danych."""
    return defects[defects["cohort"].isna()][["serial", "reported_at", "error_code", "source"]]


def run_all(units, components, defects, period="M", min_units=10):
    units, defects = prepare(units, defects, period)
    return {
        "Kohorty": cohort_summary(units, defects),
        "Krzywa kohort": cohort_matrix(units, defects),
        "Błędy x kohorta": errors_by_cohort(defects),
        "Komponenty": component_risk(units, components, "component", min_units),
        "Partie komponentów": component_risk(units, components, "component_lot", min_units),
        "Komponenty x kohorta": component_by_cohort(units, components),
        "Partie x błędy": component_error_matrix(units, components, defects),
        "Numery seryjne": serial_detail(units, defects),
        "Niedopasowane SN": unmatched(defects),
    }
