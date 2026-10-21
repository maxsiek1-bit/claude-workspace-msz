"""Buduje samodzielny plik HTML z dashboardem jakości (działa offline, bez numerów seryjnych).

  python build_dashboard.py --out ../output/dashboard_jakosci.html [--json gotowe_dane.json]
"""
import argparse
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="output/dashboard_jakosci.html")
    p.add_argument("--json", help="użyj wcześniej przygotowanych danych zamiast liczyć od nowa")
    p.add_argument("--cache", default="cache")
    p.add_argument("--no-conpeek", action="store_true")
    p.add_argument("--artifact", action="store_true", help="wersja do publikacji jako artifact claude.ai (Chart.js z CDN, bez szkieletu)")
    a = p.parse_args()
    if a.json:
        payload = Path(a.json).read_text(encoding="utf-8")
    else:
        import dashboard_data
        comps = pd.read_pickle(Path(a.cache) / "genealogy.pkl")
        payload = json.dumps(dashboard_data.build(a.cache, not a.no_conpeek, comps),
                             separators=(",", ":"), ensure_ascii=False, default=str)
    html = (HERE / "dashboard_template.html").read_text(encoding="utf-8")
    chart = (HERE / "vendor" / "chart.umd.min.js").read_text(encoding="utf-8")
    if a.artifact:
        html = html.replace("<script>/*__CHARTJS__*/</script>",
                            '<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>')
        for tag in ("<!doctype html>", '<html lang="pl">', "<head>", "</head>", "<body>", "</body>", "</html>",
                    '<meta charset="utf-8">', '<meta name="viewport" content="width=device-width, initial-scale=1">'):
            html = html.replace(tag + "\n", "").replace(tag, "")
    else:
        html = html.replace("/*__CHARTJS__*/", chart.replace("</script", "<\\/script"))
    html = html.replace("/*__DATA__*/", payload.replace("</", "<\\/"))
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"Zapisano {out} ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
