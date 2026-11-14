"""Buduje zasoby przeglądarki 3D: geometrię brył (z plików .npz wyeksportowanych przez blend_export.py),
tekstury pięter z przezroczystym tłem i data.json. Użycie: python3 viewer3d/tools/build_assets.py <katalog z .npz>"""
import json, sys, os, numpy as np
from PIL import Image
from scipy import ndimage as ndi
Image.MAX_IMAGE_PIXELS = None
src = sys.argv[1]; T = 'viewer3d/tools/'; an = json.load(open(T + 'analysis.json')); fit = json.load(open(T + 'fit.json'))
bud = json.load(open('data/budynki.json')); lok = json.load(open('data/lokale.json'))
data = dict(buildings={}, floors=[], units=[])
def fmask(a, k=61):
    ink = (a.min(2) < 245)
    cl = ndi.minimum_filter1d(ndi.minimum_filter1d(ndi.maximum_filter1d(ndi.maximum_filter1d(np.pad(ink.view(np.uint8), k), k, axis=0), k, axis=1), k, axis=0), k, axis=1)[k:-k, k:-k]
    return ndi.binary_fill_holes(cl > 0)
for name in ['Budynek_A', 'Budynek_B', 'Budynek_C']:
    z = np.load(os.path.join(src, name + '.npz')); co, t, mi = z['co'], z['t'], z['mi']
    mats = list(an[name]['matcol'].keys()); order = np.argsort(mi, kind='stable'); t = t[order]; mi = mi[order]
    used = np.unique(t); remap = np.full(len(co), -1, np.int64); remap[used] = np.arange(len(used)); t = remap[t]; c = co[used]
    v = np.stack([c[:, 0], c[:, 2], -c[:, 1]], 1)                      # three.js: Y w górę
    json.dump(dict(pos=np.round(v * 100).astype(int).ravel().tolist(), idx=t.ravel().tolist()), open(f'viewer3d/geo/{name}.json', 'w'), separators=(',', ':'))
    groups = []
    for i, m in enumerate(mats):
        idx = np.where(mi == i)[0]
        if len(idx): groups.append(dict(mat=m, start=int(idx[0]) * 3, count=int(len(idx)) * 3, color=an[name]['matcol'][m]))
    data['buildings'][name[-1]] = dict(file=f'geo/{name}.json', verts=int(len(v)), groups=groups, bbmin=an[name]['bbmin'], bbmax=an[name]['bbmax'])
for B in 'AB':
    A = np.array(fit[B]['A']); tt = np.array(fit[B]['t']); Wm, Hm = bud[B]['arkusz_m']
    zf = {int(k): v for k, v in fit[B]['z'].items()}
    if B == 'A': zf[0] = round(zf[1] - 2.95, 2)
    corners = [[0, 0], [Wm, 0], [Wm, Hm], [0, Hm]]
    quad = [(A @ np.array(c) + tt).round(3).tolist() for c in corners]
    for fl in sorted(zf):
        for suf in ('', '_opis'):
            im = Image.open(f'out/tekstury/MarinaHel_{B}_pietro{fl}{suf}.png').convert('RGB'); a = np.asarray(im)
            mask = fmask(a)
            if B == 'A' and fl == 0:      # parter A: plan obejmuje też halę garażową pod dziedzińcem i schody terenowe - zostaje tylko obrys budynku
                ref = fmask(np.asarray(Image.open('out/tekstury/MarinaHel_A_pietro2.png').convert('RGB')))
                mask &= ndi.maximum_filter1d(ndi.maximum_filter1d(ref.view(np.uint8), 81, axis=0), 81, axis=1) > 0
            rgba = np.dstack([a, (mask * 255).astype(np.uint8)]); im2 = Image.fromarray(rgba, 'RGBA')
            if im2.width > 4096: im2 = im2.resize((4096, round(im2.height * 4096 / im2.width)), Image.LANCZOS)
            im2.save(f'viewer3d/tex/{B}{fl}{suf}.webp', quality=80, method=4)
        data['floors'].append(dict(b=B, fl=fl, name='parter' if fl == 0 else f'piętro {fl}', z=zf[fl], quad=quad, sheet=[Wm, Hm], tex=f'tex/{B}{fl}.webp', texl=f'tex/{B}{fl}_opis.webp'))
    data['fit' + B] = dict(A=A.tolist(), t=tt.tolist())
for u in lok:
    data['units'].append(dict(id=u['id'], b=u['budynek'], n=u['numer'], fl=u['pietro'], st=u['status'], pu=u['pu_m2'], w=u['szer_x_m'], d=u['gleb_y_m'],
                              poly=u['obrys_m'], rooms=[[r['nazwa'], r['m2']] for r in u['pomieszczenia']]))
# ---- wymiary zewnętrzne (czerwone linie) ----
import math
cw = json.load(open('data/czesci_wspolne.json')); dims = []
def add(b, p, q, label, exts): dims.append(dict(b=b, a=[round(float(v), 2) for v in p], c=[round(float(v), 2) for v in q], label=label, ext=[[[round(float(v), 2) for v in e] for e in ex] for ex in exts]))
fmt = lambda v: ('%.1f' % v).replace('.', ',')
O = 4.0; ZG = 0.4
for B in 'AB':
    A = np.array(fit[B]['A']); tt = np.array(fit[B]['t']); M = lambda x, y, z=ZG: list(A @ np.array([x, y]) + tt) + [z]
    fl = [r['obrys_bbox_m'] for r in cw if r['budynek'] == B and (r['pietro'] >= 2 if B == 'A' else 1 <= r['pietro'] <= 3)]
    x0, y0, x1, y1 = np.median(np.array(fl), 0)
    zb, zt = an['Budynek_' + B]['bbmin'][2], an['Budynek_' + B]['bbmax'][2]
    ys, yo, s = (y0, y1, -1) if B == 'A' else (y1, y0, 1)       # strona zewnętrzna: A od długiej elewacji, B od frontu
    add(B, M(x0, ys + s * O), M(x1, ys + s * O), fmt(x1 - x0) + ' m', [[M(x0, ys), M(x0, ys + s * (O + 1))], [M(x1, ys), M(x1, ys + s * (O + 1))]])
    add(B, M(x0 - O, y0), M(x0 - O, y1), fmt(y1 - y0) + ' m', [[M(x0, y0), M(x0 - O - 1, y0)], [M(x0, y1), M(x0 - O - 1, y1)]])
    add(B, M(x0 - O, ys + s * O, zb), M(x0 - O, ys + s * O, zt), '~' + fmt(zt - zb) + ' m*', [[M(x0 - O - 1, ys + s * O, zt), M(x0, ys, zt)]])
th = an['Budynek_C']['rot'][2]; R = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])
co = np.load(os.path.join(src, 'Budynek_C.npz'))['co']; uv = co[:, :2] @ R            # obrót o -th
x0, y0 = uv.min(0); x1, y1 = uv.max(0); M = lambda x, y, z=ZG: list(R @ np.array([x, y])) + [z]
zb, zt = float(co[:, 2].min()), float(co[:, 2].max()); ZR = ZG
add('C', M(x0, y0 - O, ZR), M(x1, y0 - O, ZR), '~' + fmt(x1 - x0) + ' m*', [[M(x0, y0, ZR), M(x0, y0 - O - 1, ZR)], [M(x1, y0, ZR), M(x1, y0 - O - 1, ZR)]])
add('C', M(x1 + O, y0, ZR), M(x1 + O, y1, ZR), '~' + fmt(y1 - y0) + ' m*', [[M(x1, y0, ZR), M(x1 + O + 1, y0, ZR)], [M(x1, y1, ZR), M(x1 + O + 1, y1, ZR)]])
add('C', M(x1 + O, y0 - O, zb), M(x1 + O, y0 - O, zt), '~' + fmt(zt - zb) + ' m*', [[M(x1 + O + 1, y0 - O, zt), M(x1, y0, zt)]])
data['dims'] = dims
for d in dims: print(d['b'], d['label'])
json.dump(data, open('viewer3d/data.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print({k: v['verts'] for k, v in data['buildings'].items()}, len(data['floors']), len(data['units']))
