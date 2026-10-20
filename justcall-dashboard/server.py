#!/usr/bin/env python3
"""Sales team dashboard backed by the JustCall v2.1 API.

Standard library only. Credentials come from environment variables or a local
.env file (never from the browser), and the browser receives call metadata
without contact phone numbers, names or message bodies.

Usage:
    python server.py                         # serve on http://localhost:8050
    python server.py snapshot --days 60 --out snapshot.html
"""

import argparse
import base64
import concurrent.futures
import datetime as dt
import gzip
import hashlib
import hmac
import http.server
import json
import os
import secrets
import socketserver
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CACHE_DIR = ROOT / ".cache"
INDEX_HTML = ROOT / "static" / "index.html"
API_BASE = "https://api.justcall.io/v2.1"
PAGE_SIZE = 100  # JustCall maximum
MAX_RANGE_DAYS = 120


def load_env_file(path):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file(ROOT / ".env")

API_KEY = os.environ.get("JUSTCALL_API_KEY", "")
API_SECRET = os.environ.get("JUSTCALL_API_SECRET", "")
DASHBOARD_TZ = os.environ.get("DASHBOARD_TZ", "Europe/Warsaw")
DASHBOARD_USER = os.environ.get("DASHBOARD_USER", "admin")
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "")


# --------------------------------------------------------------------------
# JustCall client with rate limiting
# --------------------------------------------------------------------------

class RateLimiter:
    """Sliding window under JustCall's burst limit (60 requests / minute)."""

    def __init__(self, per_minute=55, concurrency=6):
        self.per_minute = per_minute
        self.stamps = deque()
        self.lock = threading.Lock()
        self.slots = threading.Semaphore(concurrency)

    def acquire(self):
        self.slots.acquire()
        while True:
            with self.lock:
                now = time.monotonic()
                while self.stamps and now - self.stamps[0] > 60:
                    self.stamps.popleft()
                if len(self.stamps) < self.per_minute:
                    self.stamps.append(now)
                    return
                wait = 60 - (now - self.stamps[0]) + 0.05
            time.sleep(wait)

    def release(self):
        self.slots.release()


limiter = RateLimiter()


class JustCallError(Exception):
    pass


def api_get(path, params=None):
    if not API_KEY or not API_SECRET:
        raise JustCallError("Brak JUSTCALL_API_KEY / JUSTCALL_API_SECRET w pliku .env")
    url = f"{API_BASE}/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = {"Authorization": f"{API_KEY}:{API_SECRET}", "Accept": "application/json"}
    for attempt in range(5):
        limiter.acquire()
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            if err.code == 429 or err.code >= 500:
                retry = err.headers.get("x-rate-limit-burst-reset") or err.headers.get("retry-after")
                time.sleep(min(float(retry or 5), 60) if attempt < 4 else 0)
                continue
            body = err.read().decode("utf-8", "replace")[:300]
            raise JustCallError(f"JustCall {err.code}: {body}") from err
        except urllib.error.URLError as err:
            time.sleep(2 ** attempt)
            continue
        finally:
            limiter.release()
    raise JustCallError(f"JustCall nie odpowiada: {url}")


def fetch_all(path, params):
    """Fetch every page of a list endpoint; pages after the first run in parallel."""
    first = api_get(path, {**params, "per_page": PAGE_SIZE, "page": 0})
    rows = list(first.get("data") or [])
    total = int(first.get("total_count") or len(rows))
    pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    if pages > 1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = pool.map(
                lambda p: api_get(path, {**params, "per_page": PAGE_SIZE, "page": p}).get("data") or [],
                range(1, pages),
            )
            for chunk in results:
                rows.extend(chunk)
    return rows


# --------------------------------------------------------------------------
# Slimming: keep only what the dashboard needs, hash contact numbers
# --------------------------------------------------------------------------

def contact_salt():
    CACHE_DIR.mkdir(exist_ok=True)
    salt_file = CACHE_DIR / "salt"
    if not salt_file.exists():
        salt_file.write_text(secrets.token_hex(16))
    return salt_file.read_text().strip().encode()


SALT = None


def contact_id(number):
    global SALT
    if SALT is None:
        SALT = contact_salt()
    digits = "".join(ch for ch in str(number or "") if ch.isdigit())
    if not digits:
        return ""
    return hmac.new(SALT, digits.encode(), hashlib.sha256).hexdigest()[:10]


def utc_epoch(date_str, time_str):
    stamp = dt.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S")
    return int(stamp.replace(tzinfo=dt.timezone.utc).timestamp())


def slim_call(c):
    info = c.get("call_info") or {}
    dur = c.get("call_duration") or {}
    return {
        "id": c["id"],
        "t": utc_epoch(c["call_date"], c["call_time"]),
        "a": c.get("agent_id") or 0,
        "an": c.get("agent_name") or "",
        "d": "O" if info.get("direction") == "Outgoing" else "I",
        "ty": info.get("type") or "",
        "cv": int(dur.get("conversation_time") or 0),
        "rg": int(dur.get("ring_time") or 0),
        "c": contact_id(c.get("contact_number")),
        "ln": c.get("justcall_line_name") or c.get("justcall_number") or "",
        "mr": info.get("missed_call_reason") or "",
        "dp": info.get("disposition") or "",
        "rec": 1 if info.get("recording") else 0,
        # call log fields
        "cn": c.get("contact_name") or "",
        "num": str(c.get("contact_number") or ""),
        "nt": (info.get("notes") or "")[:500],
        "ru": info.get("recording") or "",
    }


def slim_text(s):
    return {
        "id": s["id"],
        "t": utc_epoch(s["sms_date"], s["sms_time"]),
        "a": s.get("agent_id") or 0,
        "an": s.get("agent_name") or "",
        "d": "O" if s.get("direction") == "Outgoing" else "I",
        "st": s.get("delivery_status") or "",
        "c": contact_id(s.get("contact_number")),
    }


# --------------------------------------------------------------------------
# Per-day cache: finished days live on disk, recent days in memory briefly
# --------------------------------------------------------------------------

KINDS = {"calls": slim_call, "texts": slim_text}
mem_cache = {}
mem_lock = threading.Lock()
RECENT_TTL = 90
CACHE_VERSION = 2  # bump when slim_call/slim_text change shape


def fetch_day(kind, day):
    today = dt.datetime.now(dt.timezone.utc).date()
    disk = CACHE_DIR / f"{kind}-v{CACHE_VERSION}" / f"{day.isoformat()}.json"
    settled = day <= today - dt.timedelta(days=2)
    if settled and disk.exists():
        return json.loads(disk.read_text(encoding="utf-8"))
    key = (kind, day)
    with mem_lock:
        hit = mem_cache.get(key)
        if hit and time.time() - hit[0] < RECENT_TTL:
            return hit[1]
    params = {
        "from_datetime": f"{day.isoformat()} 00:00:00",
        "to_datetime": f"{day.isoformat()} 23:59:59",
    }
    rows = [KINDS[kind](r) for r in fetch_all(kind, params)]
    if settled:
        disk.parent.mkdir(parents=True, exist_ok=True)
        disk.write_text(json.dumps(rows, separators=(",", ":")), encoding="utf-8")
    with mem_lock:
        mem_cache[key] = (time.time(), rows)
    return rows


def fetch_range(kind, start, end):
    days = [start + dt.timedelta(days=i) for i in range((end - start).days + 1)]
    seen, out = set(), []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for rows in pool.map(lambda d: fetch_day(kind, d), days):
            for r in rows:
                if r["id"] not in seen:
                    seen.add(r["id"])
                    out.append(r)
    out.sort(key=lambda r: r["t"])
    return out


live_cache = {"at": 0, "data": None}


def fetch_team():
    if live_cache["data"] and time.time() - live_cache["at"] < 20:
        return live_cache["data"]
    users = api_get("users", {"per_page": 100}).get("data") or []
    groups = api_get("user_groups", {"per_page": 100}).get("data") or []
    data = {
        "users": [
            {
                "id": u["id"],
                "name": u.get("name") or "",
                "email": u.get("email") or "",
                "role": (u.get("role") or "").strip(),
                "groups": [g.get("group_name") for g in u.get("groups") or []],
                "available": u.get("available") == "Yes",
                "on_call": u.get("on_call") == "Yes",
                "reason": u.get("unavailability_reason") or "",
                "last_login": u.get("last_login_timestamp") or "",
                "timezone": u.get("timezone") or "",
            }
            for u in users
        ],
        "groups": sorted(g.get("group_name") for g in groups if g.get("group_name")),
    }
    live_cache.update(at=time.time(), data=data)
    return data


def pack(rows, cols, index_cols=()):
    """Column-oriented packing; string columns in index_cols become lookup indices."""
    dicts = {c: [] for c in index_cols}
    lookups = {c: {} for c in index_cols}
    packed = []
    for r in rows:
        row = []
        for c in cols:
            v = r.get(c, "")
            if c in lookups:
                if v not in lookups[c]:
                    lookups[c][v] = len(dicts[c])
                    dicts[c].append(v)
                v = lookups[c][v]
            row.append(v)
        packed.append(row)
    return {"cols": cols, "rows": packed, "dict": dicts}


CALL_COLS = ["id", "t", "a", "d", "ty", "cv", "rg", "c", "ln", "mr", "dp", "rec", "cn", "num", "nt", "rt", "rs"]


def split_recording(rows):
    """Recording links differ only by recSid; ship the shared template once."""
    for r in rows:
        url = r.get("ru") or ""
        sid = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("recSid", [""])[0]
        r["rt"], r["rs"] = (url.replace(sid, "{sid}"), sid) if sid else (url, "")
    return rows
TEXT_COLS = ["t", "a", "d", "st", "c"]


def build_payload(start, end):
    calls = fetch_range("calls", start, end)
    texts = fetch_range("texts", start, end)
    team = fetch_team()
    names = {u["id"]: u["name"] for u in team["users"]}
    for r in calls + texts:  # agents removed from the account still show by name
        if r["a"] and r["a"] not in names:
            names[r["a"]] = r["an"]
    return {
        "generated_at": int(time.time()),
        "tz": DASHBOARD_TZ,
        "range": {"from": start.isoformat(), "to": end.isoformat()},
        "users": team["users"],
        "groups": team["groups"],
        "agent_names": {str(k): v for k, v in names.items()},
        "calls": pack(split_recording(calls), CALL_COLS, ("ty", "ln", "mr", "dp", "rt")),
        "texts": pack(texts, TEXT_COLS, ("st",)),
    }


# --------------------------------------------------------------------------
# HTTP server
# --------------------------------------------------------------------------

PAGE_HEAD = (
    '<!doctype html><html lang="pl"><head><meta charset="utf-8">'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
    "</head><body>\n"
)


def render_page(snapshot=None):
    html = INDEX_HTML.read_text(encoding="utf-8")
    if snapshot is not None:
        blob = json.dumps(snapshot, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/")
        html = html.replace(
            '<script id="snapshot" type="application/json">null</script>',
            f'<script id="snapshot" type="application/json">{blob}</script>',
        )
    return html


def parse_day(value, fallback):
    try:
        return dt.date.fromisoformat(value) if value else fallback
    except ValueError:
        return fallback


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "SalesDashboard/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.log_date_time_string(), fmt % args))

    def authorized(self):
        if not DASHBOARD_PASSWORD:
            return True
        header = self.headers.get("Authorization", "")
        if header.startswith("Basic "):
            try:
                user, _, pwd = base64.b64decode(header[6:]).decode().partition(":")
            except Exception:
                return False
            return hmac.compare_digest(user, DASHBOARD_USER) and hmac.compare_digest(pwd, DASHBOARD_PASSWORD)
        return False

    def send(self, status, body, ctype="application/json; charset=utf-8"):
        data = body.encode("utf-8") if isinstance(body, str) else body
        gz = "gzip" in self.headers.get("Accept-Encoding", "") and len(data) > 1024
        if gz:
            data = gzip.compress(data)
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        if gz:
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self.authorized():
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Basic realm="Panel sprzedazy"')
            self.end_headers()
            return
        url = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(url.query)
        try:
            if url.path in ("/", "/index.html"):
                self.send(200, PAGE_HEAD + render_page(), "text/html; charset=utf-8")
            elif url.path == "/api/data":
                today = dt.datetime.now(dt.timezone.utc).date()
                end = min(parse_day(query.get("to", [""])[0], today), today)
                start = parse_day(query.get("from", [""])[0], end - dt.timedelta(days=30))
                start = max(start, end - dt.timedelta(days=MAX_RANGE_DAYS))
                self.send(200, json.dumps(build_payload(start, end), separators=(",", ":"), ensure_ascii=False))
            elif url.path == "/api/live":
                self.send(200, json.dumps(fetch_team(), ensure_ascii=False))
            else:
                self.send(404, json.dumps({"error": "Nie znaleziono"}))
        except JustCallError as err:
            self.send(502, json.dumps({"error": str(err)}, ensure_ascii=False))


class ThreadingServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    parser = argparse.ArgumentParser(description="Panel efektywności zespołu sprzedaży (JustCall)")
    sub = parser.add_subparsers(dest="cmd")
    serve = sub.add_parser("serve", help="uruchom panel (domyślnie)")
    serve.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    serve.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8050")))
    snap = sub.add_parser("snapshot", help="zapisz samodzielny plik HTML z danymi")
    snap.add_argument("--days", type=int, default=60)
    snap.add_argument("--out", default="snapshot.html")
    snap.add_argument("--fragment", action="store_true", help="bez <!doctype>/<head> (do publikacji jako Artifact)")
    args = parser.parse_args()

    if args.cmd == "snapshot":
        today = dt.datetime.now(dt.timezone.utc).date()
        payload = build_payload(today - dt.timedelta(days=args.days), today)
        html = render_page(payload)
        Path(args.out).write_text(html if args.fragment else PAGE_HEAD + html, encoding="utf-8")
        print(f"Zapisano {args.out}: {len(payload['calls']['rows'])} połączeń, {len(payload['texts']['rows'])} SMS")
        return

    host = getattr(args, "host", os.environ.get("HOST", "127.0.0.1"))
    port = getattr(args, "port", int(os.environ.get("PORT", "8050")))
    if not API_KEY:
        print("Uwaga: brak JUSTCALL_API_KEY. Skopiuj .env.example do .env i uzupełnij klucze.", file=sys.stderr)
    print(f"Panel działa: http://{host}:{port}")
    ThreadingServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
