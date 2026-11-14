"""Krok 4: skala planu piętra (m na 1 pt keyplanu) dla każdego budynku. Wynik: data/scale.json.
Dla karty: skala rzutu s [m/pt] z pomieszczeń >= 7 m2, których oszacowania są zgodne; s_key = s * K."""
import json, collections, numpy as np
r = json.load(open('data/reg.json')); m = json.load(open('data/rooms.json'))
per = collections.defaultdict(list); unit = {}
for n, c in m.items():
    seen = {}
    for x in c['rooms']:
        if x.get('s'): seen.setdefault(x['s'], 0); seen[x['s']] += x['area']
    big = sorted(s for s, a in seen.items() if a >= 7)
    if len(big) >= 2 and (big[-1] - big[0]) / big[0] < 0.03:
        sk = float(np.median(big)) * r[n]['K']; per[n[0]].append(sk); unit[n] = sk
out = {}
for b, v in per.items():
    a = np.array(v); med = float(np.median(a)); good = a[abs(a / med - 1) < 0.05]
    out[b] = dict(m_per_keypt=float(np.median(good)), n=len(good), spread_pct=float(100 * np.std(good) / np.median(good)),
                  p10=float(np.percentile(good, 10)), p90=float(np.percentile(good, 90)))
    fl = collections.defaultdict(list)
    for n, sk in unit.items():
        if n[0] == b and abs(sk / med - 1) < 0.05: fl[n[1]].append(sk)
    out[b]['per_floor'] = {k: [round(float(np.median(x)), 4), len(x)] for k, x in sorted(fl.items())}
json.dump(out, open('data/scale.json', 'w'), indent=1); print(json.dumps(out, indent=1))
