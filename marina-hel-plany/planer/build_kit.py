"""Buduje planer/kit.json: obrysy (rzuty z góry) budynków każdej wersji zespołu Marina Hel + liczby lokali,
oraz kopiuje geometrię brył do planer/geo. Uruchamiać z katalogu projektu po zbudowaniu viewer3d."""
import json, shutil, numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
from skimage import measure
from shapely.geometry import Polygon
D = json.load(open('viewer3d/data.json')); R = 5.0
def load(path):
    g = json.load(open('viewer3d/' + path)); p = np.array(g['pos'], float).reshape(-1, 3) / 100
    return np.stack([p[:, 0], -p[:, 2]], 1), p[:, 1], np.array(g['idx']).reshape(-1, 3)
def outline(path):
    xy, z, tri = load(path); x0, y0 = xy.min(0) - 3; W, H = ((xy.max(0) - xy.min(0) + 6) * R).astype(int)
    im = Image.new('L', (W, H), 0); d = ImageDraw.Draw(im)
    for t in tri: d.polygon([((xy[i, 0] - x0) * R, (xy[i, 1] - y0) * R) for i in t], fill=255)
    m = ndi.binary_fill_holes(np.array(im) > 0); m = np.pad(m, 2)
    c = max(measure.find_contours(m.astype(float), 0.5), key=len)
    poly = Polygon([((q[1] - 2) / R + x0, (q[0] - 2) / R + y0) for q in c]).simplify(0.6)
    return [[round(x, 2), round(y, 2)] for x, y in list(poly.exterior.coords)[:-1]], round(poly.area, 1), [float(z.min()), float(z.max())]
# liczby lokali: lista dewelopera (A 123 lok. / 5109,88 m2, B 42 / 1983,13 m2); C brak danych
A0 = dict(lokale=123, pu=5109.9); B0 = dict(lokale=42, pu=1983.1)
A2 = dict(lokale=123 - 13, pu=round(5109.9 - D['v2']['pu_mniej'], 1))
defs = {'A': ('geo/Budynek_A.json', D['buildings']['A']['groups'], A0, 'Budynek A'),
        'A2': ('geo/Budynek_A_v2.json', D['v2']['building']['groups'], A2, 'Budynek A skrócony'),
        'B': ('geo/Budynek_B.json', D['buildings']['B']['groups'], B0, 'Budynek B'),
        'C': ('geo/Budynek_C.json', D['buildings']['C']['groups'], dict(lokale=None, pu=None), 'Budynek C'),
        'C3': ('geo/Budynek_C_v3.json', D['v3']['building']['groups'], A2, 'Lustrzane A w miejscu C')}
kit = dict(buildings={}, variants=dict(base=dict(name='Wersja podstawowa', b=['A', 'B', 'C']), v2=dict(name='Po modyfikacji', b=['A2', 'B', 'C']),
                                       v3=dict(name='Po modyfikacji + lustrzane A w miejscu C', b=['A2', 'B', 'C3'])))
for k, (path, groups, st, name) in defs.items():
    o, area, zr = outline(path)
    kit['buildings'][k] = dict(name=name, file=path, groups=groups, outline=o, pow_zabudowy=area, z=zr, kond=5 if k == 'B' else 6, **st)   # kondygnacje nadziemne: A parter+5, B parter+4, C wg wysokości bryły
    print(k, len(o), 'pkt', area, 'm2', st)
for v in kit['variants'].values():      # środek i prostokąt obejmujący zespołu w jego własnych osiach (obrót 17,12 st = długa elewacja A)
    pts = np.array([q for k in v['b'] for q in kit['buildings'][k]['outline']]); th = np.radians(17.12)
    Rm = np.array([[np.cos(th), np.sin(th)], [-np.sin(th), np.cos(th)]]); u = pts @ Rm.T
    c = Rm.T @ ((u.min(0) + u.max(0)) / 2); v['center'] = c.round(2).tolist(); v['axis_deg'] = 17.12; v['size'] = (u.max(0) - u.min(0)).round(1).tolist()
    print(v['name'], v['size'], v['center'])
# plany pięter (tekstury z numerami lokali) dla każdego typu: poziom podłogi w modelu i prostokąt tekstury we współrzędnych modelu
import os
os.makedirs('planer/tex', exist_ok=True)
def fl(k, lst): 
    out = []
    for f in lst:
        shutil.copy('viewer3d/' + f['tex'], 'planer/' + f['tex']); out.append(dict(fl=f['fl'], name=f['name'], z=f['z'], quad=f['quad'], tex=f['tex']))
    kit['buildings'][k]['floors'] = out
FA = [f for f in D['floors'] if f['b'] == 'A']; FB = [f for f in D['floors'] if f['b'] == 'B']
fl('A', [dict(f, tex=f['texl']) for f in FA]); fl('B', [dict(f, tex=f['texl']) for f in FB])
fl('A2', [dict(f, tex=next(x for x in D['v2']['floors'] if x['fl'] == f['fl'])['texl']) for f in FA])
fl('C3', [dict(f, tex=f['texl']) for f in D['v3']['floors']]); kit['buildings']['C']['floors'] = []
# ---- bryły pocięte na kondygnacje: wyłączenie piętra usuwa je z bryły, a wyższe opadają ----
LV = [3.62, 6.57, 9.52, 12.47, 15.58, 18.53]          # poziomy podłóg w modelu (m) i spód dachu
def slabs(k, path, groups):
    g = json.load(open('viewer3d/' + path)); P = np.array(g['pos'], float).reshape(-1, 3) / 100; I = np.array(g['idx']).reshape(-1, 3)
    mi = np.zeros(len(I), int)
    for gi, gr in enumerate(groups): mi[gr['start'] // 3:(gr['start'] + gr['count']) // 3] = gi
    if k == 'B': bounds = [-1e9] + LV + [1e9]; keys = ['base', 0, 1, 2, 3, 4, 'roof']
    else: bounds = [-1e9] + LV + [1e9]; keys = [0, 1, 2, 3, 4, 5, 'roof']
    tri = P[I]; y = tri[:, :, 1]; lo = np.searchsorted(bounds, y.min(1) + 1e-6) - 1; hi = np.searchsorted(bounds, y.max(1) - 1e-6) - 1
    out = [[] for _ in keys]; om = [[] for _ in keys]
    same = lo == hi
    for s in range(len(keys)): sel = same & (lo == s); out[s].append(tri[sel]); om[s].append(mi[sel])
    def clip(poly, c, keep_lt):
        res = []
        for i in range(len(poly)):
            p, q = poly[i], poly[(i + 1) % len(poly)]; ip = (p[1] < c) if keep_lt else (p[1] >= c); iq = (q[1] < c) if keep_lt else (q[1] >= c)
            if ip: res.append(p)
            if ip != iq: res.append(p + (q - p) * ((c - p[1]) / (q[1] - p[1])))
        return res
    for i in np.where(~same)[0]:
        for s in range(lo[i], hi[i] + 1):
            poly = list(tri[i])
            if bounds[s] > -1e8: poly = clip(poly, bounds[s], False)
            if len(poly) >= 3 and bounds[s + 1] < 1e8: poly = clip(poly, bounds[s + 1], True)
            for j in range(1, len(poly) - 1): out[s].append(np.array([[poly[0], poly[j], poly[j + 1]]])); om[s].append(np.array([mi[i]]))
    res = []; meta = []
    for s, key in enumerate(keys):
        T = np.concatenate(out[s]) if out[s] else np.zeros((0, 3, 3)); M = np.concatenate(om[s]) if om[s] else np.zeros(0, int)
        o = np.argsort(M, kind='stable'); T = T[o]; M = M[o]
        v = np.round(T.reshape(-1, 3) * 100).astype(np.int64); u, inv = np.unique(v, axis=0, return_inverse=True) if len(v) else (v, np.zeros(0, int))
        gs = [dict(m=gi, start=int(np.where(M == gi)[0][0]) * 3, count=int((M == gi).sum()) * 3) for gi in range(len(groups)) if (M == gi).any()]
        z0 = float(P[:, 1].min()) if bounds[s] < -1e8 else bounds[s]; z1 = float(P[:, 1].max()) if bounds[s + 1] > 1e8 else bounds[s + 1]
        res.append(dict(pos=u.ravel().tolist(), idx=np.asarray(inv).ravel().tolist(), groups=gs)); meta.append(dict(key=key, z0=round(z0, 2), z1=round(z1, 2)))
    f = 'geo/' + k + '_kond.json'; json.dump(res, open('planer/' + f, 'w'), separators=(',', ':'))
    return f, meta
for k, (path, groups, st, name) in defs.items():
    f, meta = slabs(k, path, groups); kit['buildings'][k]['slabs_file'] = f; kit['buildings'][k]['slabs'] = meta
    kit['buildings'][k]['mats'] = [dict(mat=gr['mat'], color=gr['color']) for gr in groups]
    if os.path.exists('planer/' + path): os.remove('planer/' + path)
    print(k, 'kondygnacje:', [(m['key'], m['z0'], m['z1']) for m in meta])
# ---- lokale i PU na kondygnację (z planów; lokale bez karty A 514 i B 104 dopisane do swoich pięter) ----
def per_floor(units, bkey, extra):
    d = {}
    for u in units:
        if u['b'] == bkey: e = d.setdefault(u['fl'], [0, 0.0]); e[0] += 1; e[1] += u['pu'] or 0
    for fl, pu in extra: e = d.setdefault(fl, [0, 0.0]); e[0] += 1; e[1] += pu
    return d
PF = {'A': per_floor(D['units'], 'A', [(5, 47.49)]), 'A2': per_floor(D['v2']['units'], 'A', [(5, 47.49)]), 'B': per_floor(D['units'], 'B', [(0, 42.57)]),
      'C3': per_floor(D['v3']['units'], 'C', [(5, 47.49)])}
for k, d in PF.items():
    bb = kit['buildings'][k]
    for f in bb['floors']: f['lokale'] = d.get(f['fl'], [0, 0])[0]; f['pu'] = round(d.get(f['fl'], [0, 0])[1], 1)
    bb['lokale'] = sum(f['lokale'] for f in bb['floors']); bb['pu'] = round(sum(f['pu'] for f in bb['floors']), 1)
    print(k, 'lokale', bb['lokale'], 'PU', bb['pu'], [(f['fl'], f['lokale']) for f in bb['floors']])
kit['axis_deg'] = 17.12      # kierunek długiej elewacji budynków w układzie modelu
json.dump(kit, open('planer/kit.json', 'w'), ensure_ascii=False, separators=(',', ':'))
