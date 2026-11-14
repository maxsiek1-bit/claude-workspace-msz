"""Wersja 3: jak wersja po modyfikacji, a w miejscu budynku C stoi lustrzane odbicie skróconego budynku A (bryła + plany pięter).
Uruchamiać po build_variant.py: python3 viewer3d/tools/build_variant3.py. Dopisuje data['v3'] do viewer3d/data.json.
Odbicie: względem osi równoległej do długiej elewacji A, potem przesunięcie maksymalizujące pokrycie z obrysem C (tools/mirror.json)."""
import json, math, numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi, signal
Image.MAX_IMAGE_PIXELS = None
D = json.load(open('viewer3d/data.json')); V2 = D['v2']
def load(path):
    g = json.load(open(path)); p = np.array(g['pos'], float).reshape(-1, 3) / 100
    return np.stack([p[:, 0], -p[:, 2], p[:, 1]], 1), np.array(g['idx']).reshape(-1, 3)      # -> układ modelu (x, y, z)
A2, tA = load('viewer3d/geo/Budynek_A_v2.json'); C, tC = load('viewer3d/geo/Budynek_C.json')
fa = np.array(D['fitA']['A']); ta = np.array(D['fitA']['t']); th = math.atan2(fa[1, 0], fa[0, 0])
Rf = np.array([[math.cos(2 * th), math.sin(2 * th)], [math.sin(2 * th), -math.cos(2 * th)]])
R = 4
def sil(xy, tri, x0, y0, W, H):
    im = Image.new('L', (W, H), 0); d = ImageDraw.Draw(im)
    for t in tri: d.polygon([((xy[i, 0] - x0) * R, (xy[i, 1] - y0) * R) for i in t], fill=255)
    return ndi.binary_fill_holes(np.array(im) > 0)
Am = A2[:, :2] @ Rf.T; allp = np.vstack([Am, C[:, :2]]); x0, y0 = allp.min(0) - 10; W, H = ((allp.max(0) - allp.min(0) + 20) * R).astype(int)
sa = sil(Am, tA, x0, y0, W, H); sc = sil(C[:, :2], tC, x0, y0, W, H)
cc = signal.fftconvolve(sc.astype(np.float32), sa[::-1, ::-1].astype(np.float32), mode='full')
iy, ix = np.unravel_index(cc.argmax(), cc.shape); t3 = np.array([ix - (W - 1), iy - (H - 1)]) / R
iou = float(cc.max() / (sa.sum() + sc.sum() - cc.max()))
json.dump(dict(Rf=Rf.tolist(), t3=t3.tolist(), iou=iou), open('viewer3d/tools/mirror.json', 'w'))

# ---------- bryła ----------
P = np.column_stack([Am + t3, A2[:, 2]])
v = np.round(np.stack([P[:, 0], P[:, 2], -P[:, 1]], 1) * 100).astype(int)
json.dump(dict(pos=v.ravel().tolist(), idx=tA.ravel().tolist()), open('viewer3d/geo/Budynek_C_v3.json', 'w'), separators=(',', ':'))
bld = dict(file='geo/Budynek_C_v3.json', verts=int(len(v)), groups=V2['building']['groups'], bbmin=P.min(0).tolist(), bbmax=P.max(0).tolist())

# ---------- dopasowanie planu (współrzędne planu A po skróceniu, z odwróconą osią Y, żeby opisy były czytelne) ----------
Wm, Hm = next(f for f in D['floors'] if f['b'] == 'A')['sheet']
Ac = Rf @ fa @ np.diag([1.0, -1.0]); tc = Rf @ (fa @ np.array([0.0, Hm]) + ta) + t3
quad = [(Ac @ np.array(c) + tc).round(3).tolist() for c in ([0, 0], [Wm, 0], [Wm, Hm], [0, Hm])]

# ---------- lokale ----------
units = []
for u in V2['units']:
    n = json.loads(json.dumps(u)); n['b'] = 'C'; n['id'] = 'C' + u['id'][1:]; n['st'] = 'variant'; n['src'] = 'A ' + u['n']
    n['poly'] = [[[q[0], round(Hm - q[1], 2)] for q in pl] for pl in u['poly']]
    units.append(n)

# ---------- tekstury: plan odbity w pionie + nowe, czytelne etykiety ----------
fonts = '/usr/share/fonts/truetype/dejavu/'; floors = []
baseA = {f['fl']: f for f in D['floors'] if f['b'] == 'A'}
for f2 in V2['floors']:
    fl = f2['fl']; im = Image.open('viewer3d/' + f2['tex']).convert('RGBA').transpose(Image.FLIP_TOP_BOTTOM)
    im.save(f'viewer3d/tex/C{fl}_v3.webp', quality=80, method=4)
    s = im.width / Wm; d = ImageDraw.Draw(im); fb = ImageFont.truetype(fonts + 'DejaVuSans-Bold.ttf', 27); fr = ImageFont.truetype(fonts + 'DejaVuSans.ttf', 21)
    for u in units:
        if u['fl'] != fl: continue
        pts = [q for pl in u['poly'][:1] for q in pl]; x = (min(q[0] for q in pts) + max(q[0] for q in pts)) / 2 * s; y = (min(q[1] for q in pts) + max(q[1] for q in pts)) / 2 * s
        t1 = 'C ' + u['n']; t2 = (('~' if u.get('est') else '') + '%.2f m²' % u['pu']).replace('.', ',')
        w = max(d.textlength(t1, font=fb), d.textlength(t2, font=fr)) + 26
        d.rectangle([x - w / 2, y - 34, x + w / 2, y + 34], fill=(255, 255, 255, 235), outline=(70, 90, 110, 255), width=4)
        d.text((x - d.textlength(t1, font=fb) / 2, y - 30), t1, font=fb, fill=(50, 70, 95, 255))
        d.text((x - d.textlength(t2, font=fr) / 2, y + 4), t2, font=fr, fill=(40, 40, 40, 255))
    im.save(f'viewer3d/tex/C{fl}_opis_v3.webp', quality=80, method=4)
    bb = f2['bbox']; b = baseA[fl]
    floors.append(dict(b='C', fl=fl, name=b['name'], z=b['z'], quad=quad, sheet=[Wm, Hm], tex=f'tex/C{fl}_v3.webp', texl=f'tex/C{fl}_opis_v3.webp',
                       bbox=[bb[0], round(Hm - bb[3], 2), bb[2], round(Hm - bb[1], 2)]))
D['v3'] = dict(building=bld, floors=floors, units=units, fit=dict(A=Ac.tolist(), t=tc.tolist()), pokrycie_z_C=round(iou, 2),
               lokali=len(units), pu=round(sum(u['pu'] for u in units), 1),
               dluzszy_niz_C_m=round(float(np.ptp(P[:, :2] @ np.array([math.cos(th), math.sin(th)])) - np.ptp(C[:, :2] @ np.array([math.cos(th), math.sin(th)]))), 1))
json.dump(D, open('viewer3d/data.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print({k: v for k, v in D['v3'].items() if k not in ('building', 'floors', 'units', 'fit')})
