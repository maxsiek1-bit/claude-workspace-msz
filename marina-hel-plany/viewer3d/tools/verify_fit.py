"""Kontrola nałożenia: maska każdego piętra przeniesiona do układu modelu vs rzut bryły na tej kondygnacji.
Użycie: python3 viewer3d/tools/verify_fit.py <katalog z .npz>. Wynik: data/dopasowanie_kontrola.json, out/kontrola/model_*.png"""
import json, sys, os, numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi
Image.MAX_IMAGE_PIXELS = None
src = sys.argv[1]; D = json.load(open('viewer3d/data.json')); R = 10      # px na metr
res = []
for B in 'AB':
    z = np.load(os.path.join(src, f'Budynek_{B}.npz')); co, t = z['co'], z['t']
    x0, y0 = co[:, 0].min() - 15, co[:, 1].min() - 15; W = int((np.ptp(co[:, 0]) + 30) * R); H = int((np.ptp(co[:, 1]) + 30) * R)
    tri = co[t]; zc = tri[:, :, 2]
    A = np.array(D['fit' + B]['A']); tt = np.array(D['fit' + B]['t']); Ai = np.linalg.inv(A)
    for f in [f for f in D['floors'] if f['b'] == B]:
        sel = zc.max(1) > f['z'] - 0.45          # obrys bryły od tej kondygnacji w górę (model nie ma stropów pośrednich)
        im = Image.new('L', (W, H), 0); dr = ImageDraw.Draw(im)
        for p in tri[sel]: dr.polygon([((q[0] - x0) * R, (q[1] - y0) * R) for q in p], fill=255)
        foot = ndi.binary_fill_holes(np.array(im) > 0)
        mk = Image.open(f"out/maski/MarinaHel_{B}_pietro{f['fl']}.png"); s = 40.0
        # piksel modelu (u,v) -> metry modelu -> metry planu -> piksel maski
        M = Ai / R * s; off = Ai @ (np.array([x0, y0]) - tt) * s
        plan = np.array(mk.transform((W, H), Image.AFFINE, (M[0, 0], M[0, 1], off[0], M[1, 0], M[1, 1], off[1]), Image.NEAREST)) > 0
        dfoot = ndi.distance_transform_edt(~foot) / R; dplan = ndi.distance_transform_edt(~plan) / R
        out_p = plan & ~foot; out_f = foot & ~plan
        r = dict(budynek=B, pietro=f['fl'], plan_m2=round(plan.sum() / R / R), bryla_m2=round(foot.sum() / R / R), wspolne_m2=round((plan & foot).sum() / R / R),
                 plan_poza_bryla_m2=round(out_p.sum() / R / R), plan_poza_bryla_ponad_1m_m2=round((out_p & (dfoot > 1)).sum() / R / R), max_wystaje_m=round(float(dfoot[plan].max()), 1),
                 bryla_bez_planu_m2=round(out_f.sum() / R / R), bryla_bez_planu_ponad_1m_m2=round((out_f & (dplan > 1)).sum() / R / R))
        res.append(r); print(r)
        vis = np.full((H, W, 3), 235, np.uint8); vis[foot] = (190, 190, 190); vis[plan & foot] = (150, 205, 150); vis[out_p] = (230, 60, 50); vis[out_f] = (70, 110, 220)
        Image.fromarray(vis[::-1]).save(f"out/kontrola/model_{B}_pietro{f['fl']}.png")
json.dump(res, open('data/dopasowanie_kontrola.json', 'w'), ensure_ascii=False, indent=1)
