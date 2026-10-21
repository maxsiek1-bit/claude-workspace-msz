"""Definicja „wady” na podstawie zgłoszeń serwisowych Odoo + ujednolicenie kodów błędów."""
import re

import pandas as pd

# Typy zgłoszeń, które nie oznaczają usterki urządzenia
NON_DEFECT_TYPES = {"Periodic maintenance", "Question", "Akcesoria", "Refund", "Refurbished",
                    "Replacement after warranty - utylisation"}
NON_DEFECT_TAGS = re.compile(r"periodic mainten|przegl|główne działanie|^\[\]$", re.I)
DEFECT_TYPES = {"Warranty replacement", "Warranty repair", "Post-warranty repair", "Expertise", "Rework"}

# Tagi opisowe (PL/EN) sprowadzone do wspólnej nazwy
SYNONYMS = {
    "błąd próżni": "Vacuum error",
    "vacuum error": "Vacuum error",
    "błąd wyświetlacza": "Display failure",
    "display failure": "Display failure",
    "wyciek / przeciek wody": "Water leak",
    "water leak from the device": "Water leak",
    "water leakage from the device": "Water leak",
    "uszkodzenie mechaniczne": "Mechanical damage",
    "mechanical damage": "Mechanical damage",
    "problem z otwieraniem drzwi": "Door open / blocked drawer",
    "door open": "Door open / blocked drawer",
    "blocked drawer (cannot be opened)": "Door open / blocked drawer",
    "wilgotny wsad": "Wet load",
    "wet load": "Wet load",
}
_ECODE = re.compile(r"\b(?:error|e)\s*[-_ ]?(\d{1,2})\b", re.I)
_ENAMES = {}


def normalize_code(label):
    """'Error 12 - Prevacuum fail' / 'E12 – Vacuum generation error' -> 'E12 Prevacuum fail / check outlet'."""
    if not isinstance(label, str) or not label:
        return None
    last = label.split("/")[-1].strip()
    m = _ECODE.search(last) or _ECODE.search(label)
    if m:
        code = f"E{int(m.group(1))}"
        if label.lower().startswith("error"):
            _ENAMES.setdefault(code, label.split("-", 1)[-1].strip())
        return code
    return SYNONYMS.get(last.lower(), last)


def label(code):
    return f"{code} {_ENAMES[code]}" if code in _ENAMES else code


def from_tickets(tickets):
    t = tickets.dropna(subset=["serial"]).copy()
    t = t[~t["ticket_type"].isin(NON_DEFECT_TYPES)]
    t["fault_tags"] = t["tags"].apply(lambda ts: [x for x in ts if not NON_DEFECT_TAGS.search(x)])
    keep = t["ticket_type"].isin(DEFECT_TYPES) | (t["fault_tags"].str.len() > 0)
    t = t[keep].explode("fault_tags")
    t["error_code"] = t["fault_tags"].map(normalize_code).fillna("(bez tagu)")
    t["error_code"] = t["error_code"].map(label)
    t["source"] = "odoo_helpdesk"
    return t[["serial", "reported_at", "error_code", "source", "ticket", "ticket_type"]]


def from_repairs(repairs, tickets):
    """Naprawy bez powiązanego zgłoszenia helpdesk (te z ticketem już są policzone)."""
    r = repairs[repairs["ticket_id"].isna() | ~repairs["ticket_id"].isin(tickets["ticket_id"])].copy()
    r = r[r["serial"].str.match(r"^S[TR]\d\d")]
    r["error_code"] = "(naprawa bez zgłoszenia)"
    r["source"] = "odoo_repair"
    r["ticket"] = r["repair"]
    r["ticket_type"] = None
    return r[["serial", "reported_at", "error_code", "source", "ticket", "ticket_type"]]


def build(tickets, repairs):
    return pd.concat([from_tickets(tickets), from_repairs(repairs, tickets)], ignore_index=True)
