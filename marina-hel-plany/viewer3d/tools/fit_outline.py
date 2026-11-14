"""Dopasowanie plan -> model po obrysie: maksymalizuje pokrycie (IoU) maski typowych pięter z obrysem bryły z góry.
Start z dopasowania v1 (bryły lokali). Użycie: python3 viewer3d/tools/fit_outline.py <katalog z .npz>. Nadpisuje tools/fit.json."""
import json, sys, os, math, numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi, optimize
Image.MAX_IMAGE_PIXELS = None
src = sys.argv[1]; T = 'viewer3d/tools/'; v1 = json.load(open(T + 'fit_v1_bryly_lokali.json')); R = 4.0
out = {}
for B, floors in (('A', [2, 3, 4]), ('B', [1, 2, 3])):
    z = np.load(os.path.join(src, f'Budynek_{B}.npz')); co, t = z['co'], z['t']
    x0, y0 = co[:, 0].min() - 20, co[:, 1].min() - 20; W = int((np.ptp(co[:, 0]) + 40) * R); H = int((np.ptp(co[:, 1]) + 40) * R)
    tri = co[t]; zf = v1[B]['z'][str(floors[0])]; sel = tri[:, :, 2].max(1) > zf - 0.45
    im = Image.new('L', (W, H), 0); dr = ImageDraw.Draw(im)
    for p in tri[sel]: dr.polygon([((q[0] - x0) * R, (q[1] - y0) * R) for q in p], fill=255)
    foot = ndi.binary_fill_holes(np.array(im) > 0)
    mk = None
    for fl in floors:
        m = np.asarray(Image.open(f'out/maski/MarinaHel_{B}_pietro{fl}.png')) > 0; mk = m if mk is None else (mk & m)
    mki = Image.fromarray((mk * 255).astype(np.uint8))
    ys, xs = np.where(mk); pc = np.array([xs.mean(), ys.mean()]) / 40.0          # środek maski w metrach planu
    A1 = np.array(v1[B]['A']); t1 = np.array(v1[B]['t']); U, S_, Vt = np.linalg.svd(A1); Rm = U @ Vt     # część obrotowo-odbiciowa v1
    th0 = math.atan2(Rm[1, 0], Rm[0, 0]); c1 = A1 @ pc + t1
    def mat(p):
        th, sx, sy, cx, cy = p; rot = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])
        A = rot @ np.diag([sx, -sy]); return A, np.array([cx, cy]) - A @ pc
    def iou(p):
        A, tt = mat(p); Ai = np.linalg.inv(A); M = Ai / R * 40.0; off = Ai @ (np.array([x0, y0]) - tt) * 40.0
        plan = np.array(mki.transform((W, H), Image.AFFINE, (M[0, 0], M[0, 1], off[0], M[1, 0], M[1, 1], off[1]), Image.NEAREST)) > 0
        return (plan & foot).sum() / max(1, (plan | foot).sum())
    best = None
    for iso in (True, False):
        f = (lambda q: -iou([q[0], q[1], q[1], q[2], q[3]])) if iso else (lambda q: -iou(q))
        start = [th0, 1.0, c1[0], c1[1]] if iso else [th0, 1.0, 1.0, c1[0], c1[1]]
        cand = None
        for dth in (0, -0.03, 0.03):
            for ds in (1.0, 1.05, 0.95):
                s0 = list(start); s0[0] += dth; s0[1] *= ds
                if not iso: s0[2] *= ds
                r = optimize.minimize(f, s0, method='Nelder-Mead', options=dict(xatol=1e-3, fatol=1e-5, maxiter=600,
                    initial_simplex=np.array([s0] + [[s0[j] + (d if j == i else 0) for j in range(len(s0))] for i, d in enumerate(([0.02, 0.03, 1.5, 1.5] if iso else [0.02, 0.03, 0.03, 1.5, 1.5]))])))
                if cand is None or r.fun < cand.fun: cand = r
        p = [cand.x[0], cand.x[1], cand.x[1], cand.x[2], cand.x[3]] if iso else list(cand.x)
        print(B, 'jednolita skala' if iso else 'dwie skale', 'IoU %.4f' % -cand.fun, 'obrot %.2f st' % math.degrees(p[0]), 'skala %.4f %.4f' % (p[1], p[2]))
        if iso: best = (p, -cand.fun)
        elif -cand.fun > best[1] + 0.02: best = (p, -cand.fun)        # dwie skale tylko gdy wyraźnie lepiej
    A, tt = mat(best[0]); print(B, 'wybrane: skala %.4f %.4f IoU %.4f; IoU v1 = %.4f' % (best[0][1], best[0][2], best[1], (lambda: 0)() or 0))
    out[B] = dict(A=A.tolist(), t=tt.tolist(), z=v1[B]['z'], ztop=v1[B]['ztop'], iou=round(best[1], 4), skala=[round(best[0][1], 4), round(best[0][2], 4)], obrot_st=round(math.degrees(best[0][0]), 2))
json.dump(out, open(T + 'fit.json', 'w'), indent=1)
