"""Buduje zasoby przeglądarki 3D: geometrię brył (z plików .npz wyeksportowanych przez blend_export.py),
tekstury pięter z przezroczystym tłem i data.json. Użycie: python3 viewer3d/tools/build_assets.py <katalog z .npz>"""
import json, sys, os, numpy as np
from PIL import Image
from scipy import ndimage as ndi
Image.MAX_IMAGE_PIXELS = None
src = sys.argv[1]; T = 'viewer3d/tools/'; an = json.load(open(T + 'analysis.json')); fit = json.load(open(T + 'fit.json'))
bud = json.load(open('data/budynki.json')); lok = json.load(open('data/lokale.json'))
data = dict(buildings={}, floors=[], units=[])
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
            ink = (a.min(2) < 245); k = 61
            cl = ndi.minimum_filter1d(ndi.minimum_filter1d(ndi.maximum_filter1d(ndi.maximum_filter1d(np.pad(ink.view(np.uint8), k), k, axis=0), k, axis=1), k, axis=0), k, axis=1)[k:-k, k:-k]
            mask = ndi.binary_fill_holes(cl > 0)
            rgba = np.dstack([a, (mask * 255).astype(np.uint8)]); im2 = Image.fromarray(rgba, 'RGBA')
            if im2.width > 4096: im2 = im2.resize((4096, round(im2.height * 4096 / im2.width)), Image.LANCZOS)
            im2.save(f'viewer3d/tex/{B}{fl}{suf}.webp', quality=80, method=4)
        data['floors'].append(dict(b=B, fl=fl, name='parter' if fl == 0 else f'piętro {fl}', z=zf[fl], quad=quad, sheet=[Wm, Hm], tex=f'tex/{B}{fl}.webp', texl=f'tex/{B}{fl}_opis.webp'))
    data['fit' + B] = dict(A=A.tolist(), t=tt.tolist())
for u in lok:
    data['units'].append(dict(id=u['id'], b=u['budynek'], n=u['numer'], fl=u['pietro'], st=u['status'], pu=u['pu_m2'], w=u['szer_x_m'], d=u['gleb_y_m'],
                              poly=u['obrys_m'], rooms=[[r['nazwa'], r['m2']] for r in u['pomieszczenia']]))
json.dump(data, open('viewer3d/data.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print({k: v['verts'] for k, v in data['buildings'].items()}, len(data['floors']), len(data['units']))
