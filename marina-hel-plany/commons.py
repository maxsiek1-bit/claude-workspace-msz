"""Krok 6: części wspólne (korytarze, hole, klatki) z planu piętra: powierzchnia i rozpiętości w metrach.
Wynik: data/czesci_wspolne.json + obrazy kontrolne out/kontrola/*.png. Wartości przybliżone (z małego planu piętra)."""
import json, os, numpy as np, fitz
from scipy import ndimage as ndi
from PIL import Image, ImageDraw
import compose as c
from mhlib import info, KEY
Z = 8
def sq(a, k, op):
    f1, f2 = (ndi.minimum_filter1d, ndi.maximum_filter1d) if op == 'open' else (ndi.maximum_filter1d, ndi.minimum_filter1d)
    u = np.pad(a.astype(np.uint8), k)
    for f in (f1, f2):
        u = f(f(u, k, axis=0), k, axis=1)
    return u[k:-k, k:-k] > 0
def run(bld):
    sk = c.scale[bld]['m_per_keypt']; mpp = sk / Z; L = c.layout(bld); bb = c.content_bbox(L)
    ox, oy = bb.x0 - 10 / sk, bb.y0 - 10 / sk; res = []
    for fl, d in sorted(L.items()):
        if len(d['items']) < 3: continue
        a = c.clean_key(info(f"cards/{d['ref']}.pdf")[0], Z); H, W = a.shape
        walls = sq(a < 150, 3, 'open')                      # grube ściany, bez cienkich linii balkonów
        um = Image.new('L', (W, H), 0); dr = ImageDraw.Draw(um)
        g = d['goff']
        for it in d['items']:
            for pl in it['polys']: dr.polygon([((x + g[0] - KEY.x0) * Z, (y + g[1] - KEY.y0) * Z) for x, y in pl], fill=255)
        units = np.array(um) > 0
        solid = sq(walls | units, int(2.6 / mpp) | 1, 'close')
        inside = ndi.binary_fill_holes(solid)
        free = inside & ~units & ~walls
        op = sq(free, int(0.9 / mpp) | 1, 'open')
        lab, n = ndi.label(op); comps = []
        dt = ndi.distance_transform_edt(free) * mpp
        for i, sl in enumerate(ndi.find_objects(lab), 1):
            m = lab[sl] == i; area = m.sum() * mpp * mpp
            if area < 3: continue
            h, w = (sl[0].stop - sl[0].start) * mpp, (sl[1].stop - sl[1].start) * mpp
            dd = dt[sl] * m; ridge = dd[(dd == ndi.maximum_filter(dd, 5)) & (dd > 0.3)]
            x0 = (KEY.x0 + sl[1].start / Z - g[0] - ox) * sk; y0 = (KEY.y0 + sl[0].start / Z - g[1] - oy) * sk
            comps.append(dict(pow_m2=round(float(area), 1), dlugosc_m=round(float(max(h, w)), 1), poprzecznie_m=round(float(min(h, w)), 1),
                              szer_w_swietle_m=round(float(2 * np.median(ridge)), 2) if len(ridge) else None,
                              bbox_m=[round(x0, 1), round(y0, 1), round(x0 + w, 1), round(y0 + h, 1)], _sl=sl, _i=i))
        comps.sort(key=lambda q: -q['pow_m2'])
        kor = max([q for q in comps if (q['szer_w_swietle_m'] or 9) <= 2.5] or comps, key=lambda q: q['dlugosc_m'])
        comps.remove(kor); comps.insert(0, kor)
        vis = np.stack([a.astype(np.uint8)] * 3, -1)
        for j, q in enumerate(comps):
            q['nazwa'] = 'korytarz główny (z holami)' if j == 0 else f'inna strefa poza lokalami {j} (hol, klatka, taras/balkon lub lokal bez karty)'
            m = lab == q.pop('_i'); q.pop('_sl'); vis[m] = (255, 170, 60) if j == 0 else (120, 190, 255)
        vis[units] = (vis[units] * 0.5 + np.array([120, 200, 120]) * 0.5).astype(np.uint8)
        ys, xs = np.where(inside)
        os.makedirs('out/kontrola', exist_ok=True); Image.fromarray(vis).save(f'out/kontrola/czesci_wspolne_{bld}_pietro{fl}.png')
        bx = [round(float(((KEY.x0, KEY.y0)[i % 2] + v / Z - g[i % 2] - (ox, oy)[i % 2]) * sk), 2) for i, v in enumerate((xs.min(), ys.min(), xs.max(), ys.max()))]
        res.append(dict(budynek=bld, pietro=fl, obrys_bbox_m=bx, obrys_budynku_m=[round(float((xs.max() - xs.min()) * mpp), 1), round(float((ys.max() - ys.min()) * mpp), 1)],
                        pow_zabudowy_kondygnacji_m2=round(float(inside.sum() * mpp * mpp)), pow_lokali_brutto_m2=round(float(units.sum() * mpp * mpp)),
                        strefy=comps))
    return res
if __name__ == '__main__':
    out = run('A') + run('B')
    json.dump(out, open('data/czesci_wspolne.json', 'w'), ensure_ascii=False, indent=1)
    for r in out:
        print(r['budynek'], r['pietro'], r['obrys_budynku_m'], r['pow_zabudowy_kondygnacji_m2'], r['pow_lokali_brutto_m2'], [(q['nazwa'][:9], q['pow_m2'], q['dlugosc_m'], q['szer_w_swietle_m']) for q in r['strefy'][:4]])
