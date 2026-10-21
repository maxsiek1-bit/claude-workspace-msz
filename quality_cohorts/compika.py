"""Wczytywanie błędów urządzeń z Compika.

Do czasu podpięcia API Compika obsługiwany jest eksport CSV/XLSX. Mapowanie kolumn
ustawiasz w COLUMN_MAP (nazwa w pliku -> nazwa standardowa).
"""
import pandas as pd

COLUMN_MAP = {
    # "Numer seryjny": "serial",
    # "Data zgłoszenia": "reported_at",
    # "Kod błędu": "error_code",
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
    df["source"] = "compika"
    return df


def load_api():
    raise NotImplementedError("Integracja API Compika – do uzupełnienia po otrzymaniu dokumentacji/klucza")
