"""Pipedrive data for the sales dashboard: lead inflow, lead handling, team e-mail.

Standard library only. Uses PIPEDRIVE_API_TOKEN from the environment.

Region rules are read from the user's own Pipedrive lead filters (PIPEDRIVE_LEAD_FILTERS,
e.g. "59:PL,157:EU,60:US"), so the dashboard counts leads the same way those filters
select them, minus the owner condition: the filters show the unassigned queue, while the
dashboard counts every lead that came in, whoever owns it now.

Team e-mail: the mailbox API only exposes the token owner's own mailbox, so team
messages are read through the contacts they are linked to (persons/{id}/mailMessages).
Messages to addresses that are not Pipedrive contacts are not counted.
"""

import concurrent.futures
import datetime as dt
import json
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

V1 = "https://api.pipedrive.com/v1"
V2 = "https://api.pipedrive.com/api/v2"
TOKEN = os.environ.get("PIPEDRIVE_API_TOKEN", "")
PERSONS_TTL = int(os.environ.get("PIPEDRIVE_PERSONS_TTL", "900"))
LEADS_TTL = 120

_slots = threading.Semaphore(8)


class PipedriveError(Exception):
    pass


def enabled():
    return bool(TOKEN)


def get(path, base=V1, **params):
    params["api_token"] = TOKEN
    url = f"{base}/{path}?" + urllib.parse.urlencode(params)
    for attempt in range(6):
        with _slots:
            try:
                with urllib.request.urlopen(url, timeout=60) as resp:
                    return json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as err:
                if err.code == 429 or err.code >= 500:
                    wait = err.headers.get("retry-after") or err.headers.get("x-ratelimit-reset") or 2 ** attempt
                    time.sleep(min(float(wait), 30))
                    continue
                body = err.read().decode("utf-8", "replace")[:300]
                raise PipedriveError(f"Pipedrive {err.code}: {body}") from err
            except urllib.error.URLError:
                time.sleep(2 ** attempt)
    raise PipedriveError(f"Pipedrive nie odpowiada: {path}")


def get_all_v1(path, **params):
    rows, start = [], 0
    while True:
        r = get(path, limit=500, start=start, **params)
        rows.extend(r.get("data") or [])
        page = (r.get("additional_data") or {}).get("pagination") or {}
        if not page.get("more_items_in_collection"):
            return rows
        start = page["next_start"]


def get_all_v2(path, **params):
    rows, cursor = [], None
    while True:
        q = dict(limit=500, **params)
        if cursor:
            q["cursor"] = cursor
        r = get(path, base=V2, **q)
        rows.extend(r.get("data") or [])
        cursor = (r.get("additional_data") or {}).get("next_cursor")
        if not cursor:
            return rows


def iso_epoch(value):
    if not value:
        return None
    value = value.replace("Z", "+00:00")
    if "T" not in value:
        value = value.replace(" ", "T") + ("+00:00" if "+" not in value else "")
    return int(dt.datetime.fromisoformat(value).timestamp())


def digits9(value):
    d = "".join(ch for ch in str(value or "") if ch.isdigit())
    return d[-9:] if len(d) >= 7 else ""


def values_of(v):
    if v is None or v == "":
        return set()
    if isinstance(v, list):
        return {str(x) for x in v}
    return {s.strip() for s in str(v).split(",") if s.strip()}


# --------------------------------------------------------------------------
# Account metadata and region rules
# --------------------------------------------------------------------------

_meta = {"at": 0, "data": None}


def metadata():
    if _meta["data"] and time.time() - _meta["at"] < 3600:
        return _meta["data"]
    fields = get("leadFields", limit=500).get("data") or []
    by_id = {str(f["id"]): f for f in fields}
    by_key = {f["key"]: f for f in fields}
    options = lambda key: {str(o["id"]): o["label"] for o in (by_key.get(key, {}).get("options") or [])}
    regions = []
    spec = os.environ.get("PIPEDRIVE_LEAD_FILTERS", "")
    for part in [p for p in spec.split(",") if ":" in p]:
        fid, name = part.split(":", 1)
        flt = get(f"filters/{fid.strip()}").get("data") or {}
        include, exclude = {}, {}

        def walk(node):
            for c in node.get("conditions") or []:
                if "conditions" in c:
                    walk(c)
                    continue
                f = by_id.get(str(c.get("field_id")))
                if c.get("object") != "lead" or not f or f["key"] == "owner_id":
                    continue
                vals = values_of(c.get("value"))
                target = exclude if c.get("operator") in ("!=", "NOT IN") else include
                target.setdefault(f["key"], set()).update(vals)

        walk(flt.get("conditions") or {})
        regions.append({"name": name.strip(), "filter_id": int(fid), "include": include, "exclude": exclude})
    users = get("users").get("data") or []
    data = {
        "regions": regions,
        "channels": options("channel"),
        "labels": {l["id"]: l["name"] for l in get("leadLabels").get("data") or []},
        "pipelines": {str(p["id"]): p["name"] for p in get("pipelines").get("data") or []},
        "users": [
            {"id": u["id"], "name": u["name"], "email": (u.get("email") or "").lower(), "active": bool(u.get("active_flag"))}
            for u in users
        ],
    }
    _meta.update(at=time.time(), data=data)
    return data


def region_of(lead, regions):
    excluded_everywhere = bool(regions)
    for reg in regions:
        if any(values_of(lead.get(k)) & vals for k, vals in reg["exclude"].items()):
            continue
        excluded_everywhere = False
        if all(values_of(lead.get(k)) & vals for k, vals in reg["include"].items()):
            return reg["name"]
    return None if excluded_everywhere else "Inne"


def market_of(lead, regions):
    """Market by the filters' include rules only (exclusions such as the newsletter import ignored)."""
    for reg in regions:
        if all(values_of(lead.get(k)) & vals for k, vals in reg["include"].items()):
            return reg["name"]
    return "Inne"


def portfolio(leads, regions):
    """Open leads and open deals per owner and market, with the state of their planned activities.

    Rows: [kind ("L" lead / "D" deal), owner, market, newsletter flag, state, items, overdue activities]
    where state is the state of the item's earliest open activity: none / overdue / today / future.
    """
    tz_name = os.environ.get("DASHBOARD_TZ", "Europe/Warsaw")
    try:
        from zoneinfo import ZoneInfo
        today = dt.datetime.now(ZoneInfo(tz_name)).date().isoformat()
    except Exception:
        today = dt.date.today().isoformat()
    first_due, overdue_n = {}, {}
    for a in get_all_v2("activities", done="false"):
        due = a.get("due_date") or "9999-12-31"
        for key in (("L", a.get("lead_id")), ("D", a.get("deal_id"))):
            if not key[1]:
                continue
            if due < first_due.get(key, "9999-12-32"):
                first_due[key] = due
            if due < today:
                overdue_n[key] = overdue_n.get(key, 0) + 1

    counts = {}

    def add(kind, item_id, owner, market, ex):
        due = first_due.get((kind, item_id))
        state = "none" if due is None else "overdue" if due < today else "today" if due == today else "future"
        key = (kind, owner or 0, market, ex, state)
        row = counts.setdefault(key, [0, 0])
        row[0] += 1
        row[1] += overdue_n.get((kind, item_id), 0)

    for l in leads:
        if not l.get("is_archived"):
            add("L", l["id"], l.get("owner_id"), market_of(l, regions), 1 if region_of(l, regions) is None else 0)
    for d in get_all_v2("deals", status="open"):
        fields = {**d, **(d.get("custom_fields") or {})}
        add("D", d["id"], d.get("owner_id"), market_of(fields, regions), 0)
    return {"today": today, "rows": [[k, o, m, ex, st, n, od] for (k, o, m, ex, st), (n, od) in counts.items()]}


# --------------------------------------------------------------------------
# Persons (phones, mail activity) and per-person mail cache
# --------------------------------------------------------------------------

_persons = {"at": 0, "rows": None}
_persons_lock = threading.Lock()


def persons():
    with _persons_lock:
        if _persons["rows"] is None or time.time() - _persons["at"] > PERSONS_TTL:
            rows = get_all_v1("persons")
            _persons["rows"] = {
                p["id"]: {
                    "phones": [digits9(x.get("value")) for x in p.get("phone") or [] if digits9(x.get("value"))],
                    "mail": max(p.get("last_incoming_mail_time") or "", p.get("last_outgoing_mail_time") or ""),
                }
                for p in rows
            }
            _persons["at"] = time.time()
        return _persons["rows"]


def slim_message(m, pid):
    frm = (m.get("from") or [{}])[0]
    return {
        "id": m["id"],
        "t": iso_epoch(m.get("message_time")),
        "u": m.get("user_id") or 0,
        "s": 1 if m.get("sent_flag") else 0,
        "th": m.get("mail_thread_id") or 0,
        "p": pid,
        "op": 1 if m.get("mail_tracking_status") in ("opened", "clicked") else 0,
        "fr": (frm.get("email_address") or "").lower(),
    }


def person_mail(cache_dir, pid, stamp):
    path = cache_dir / f"{pid}.json"
    if path.exists():
        cached = json.loads(path.read_text(encoding="utf-8"))
        if cached.get("stamp") == stamp:
            return cached["rows"]
    rows, start = [], 0
    while True:
        r = get(f"persons/{pid}/mailMessages", limit=500, start=start)
        for item in r.get("data") or []:
            msg = item.get("data", item)
            if msg.get("message_time"):
                rows.append(slim_message(msg, pid))
        page = (r.get("additional_data") or {}).get("pagination") or {}
        if not page.get("more_items_in_collection"):
            break
        start = page["next_start"]
    path.write_text(json.dumps({"stamp": stamp, "rows": rows}, separators=(",", ":")), encoding="utf-8")
    return rows


def mail_messages(cache_dir, start_day):
    cache_dir.mkdir(parents=True, exist_ok=True)
    cutoff = start_day.isoformat()
    active = [(pid, p["mail"]) for pid, p in persons().items() if p["mail"] and p["mail"][:10] >= cutoff]
    seen, out = set(), []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for rows in pool.map(lambda a: person_mail(cache_dir, *a), active):
            for m in rows:
                if m["id"] not in seen and m["t"] and m["t"] >= int(dt.datetime.combine(start_day, dt.time(), dt.timezone.utc).timestamp()):
                    seen.add(m["id"])
                    out.append(m)
    out.sort(key=lambda m: m["t"])
    return out


# --------------------------------------------------------------------------
# Leads, queue, won deals
# --------------------------------------------------------------------------

_leads = {"at": 0, "rows": None}


def all_leads():
    if _leads["rows"] is None or time.time() - _leads["at"] > LEADS_TTL:
        _leads["rows"] = get_all_v1("leads", archived_status="all")
        _leads["at"] = time.time()
    return _leads["rows"]


def queue_counts(regions):
    out = {}
    for reg in regions:
        n, start = 0, 0
        while True:
            r = get("leads", filter_id=reg["filter_id"], limit=500, start=start)
            n += len(r.get("data") or [])
            page = (r.get("additional_data") or {}).get("pagination") or {}
            if not page.get("more_items_in_collection"):
                break
            start = page["next_start"]
        out[reg["name"]] = n
    return out


def won_deals(start_day, pipelines):
    since = dt.datetime.combine(start_day, dt.time(), dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows = []
    for d in get_all_v2("deals", status="won", updated_since=since):
        t = iso_epoch(d.get("won_time"))
        if t and t >= iso_epoch(since):
            rows.append({"t": t, "o": d.get("owner_id") or 0, "pl": pipelines.get(str(d.get("pipeline_id")), ""),
                         "v": d.get("value") or 0, "cur": d.get("currency") or ""})
    return rows


def build(start_day, cache_root):
    meta = metadata()
    regions = meta["regions"]
    start_ts = int(dt.datetime.combine(start_day, dt.time(), dt.timezone.utc).timestamp())
    people = persons()
    leads = []
    every_lead = all_leads()
    for l in every_lead:
        t = iso_epoch(l.get("add_time"))
        if not t or t < start_ts:
            continue
        reg = region_of(l, regions)
        if reg is None:
            continue
        p = people.get(l.get("person_id")) or {}
        leads.append({
            "t": t,
            "o": l.get("owner_id") or 0,
            "r": reg,
            "ch": meta["channels"].get(str(l.get("channel")), "Brak kanału") if l.get("channel") else "Brak kanału",
            "src": l.get("source_name") or "",
            "ar": 1 if l.get("is_archived") else 0,
            "na": 1 if l.get("next_activity_id") else 0,
            "lb": ",".join(meta["labels"].get(x, "") for x in l.get("label_ids") or []),
            "pid": l.get("person_id") or 0,
            "ph": ",".join(p.get("phones") or []),
            "ti": l.get("title") or "",
        })
    return {
        "regions": [r["name"] for r in regions],
        "users": meta["users"],
        "queue": queue_counts(regions),
        "portfolio": portfolio(every_lead, regions),
        "leads": leads,
        "mails": mail_messages(cache_root / "pd-mail", start_day),
        "won": won_deals(start_day, meta["pipelines"]),
        "generated_at": int(time.time()),
    }
