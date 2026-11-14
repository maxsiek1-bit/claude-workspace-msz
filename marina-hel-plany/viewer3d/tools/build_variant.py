"""Wersja po modyfikacji: budynek A skrócony o pas XA..XB (metry planu) na wszystkich piętrach.
Część zachodnia (szczyt z A 510 / A 511) jest dosunięta do reszty; lokale z pasa znikają, A 512 łączy się z A 513.
Uruchamiać po build_assets.py: python3 viewer3d/tools/build_variant.py <katalog z .npz>. Dopisuje data['v2'] do viewer3d/data.json."""
import json, sys, os, numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
Image.MAX_IMAGE_PIXELS = None
src = sys.argv[1]; T = 'viewer3d/tools/'
XA, XB = 24.9, 37.4; SH = XB - XA          # linie cięcia: ściana szczytowych lokali | ściana lokalu naprzeciw A 512
D = json.load(open('viewer3d/data.json')); an = json.load(open(T + 'analysis.json'))
A = np.array(D['fitA']['A']); tt = np.array(D['fitA']['t']); Ai = np.linalg.inv(A)
PPM = 40

# ---------- bryła ----------
z = np.load(os.path.join(src, 'Budynek_A.npz')); co, t, mi = z['co'].astype(np.float64), z['t'], z['mi']
tri = co[t]                                                  # (N,3,3)
px = lambda p: (p[..., :2] - tt) @ Ai.T[:, 0]                # współrzędna x planu punktu modelu
f = px(tri)
shift3 = np.append(A @ np.array([SH, 0.0]), 0.0)
def clip(poly, fv, keep_lt, c):
    """Przycina wielokąt do półprzestrzeni f<c (keep_lt) albo f>=c."""
    out = []
    n = len(poly)
    for i in range(n):
        p, q, fp, fq = poly[i], poly[(i + 1) % n], fv[i], fv[(i + 1) % n]
        ip = (fp < c) if keep_lt else (fp >= c); iq = (fq < c) if keep_lt else (fq >= c)
        if ip: out.append(p)
        if ip != iq: out.append(p + (q - p) * ((c - fp) / (fq - fp)))
    return out
west = (f < XA).all(1); east = (f >= XB).all(1); gone = ((f >= XA) & (f < XB)).all(1)
parts = [tri[west] + shift3, tri[east]]; mats = [mi[west], mi[east]]
extra = []; em = []
for i in np.where(~(west | east | gone))[0]:
    for keep_lt, c, mv in ((True, XA, shift3), (False, XB, 0.0)):
        poly = clip(list(tri[i]), list(f[i]), keep_lt, c)
        for k in range(1, len(poly) - 1):
            extra.append(np.array([poly[0], poly[k], poly[k + 1]]) + mv); em.append(mi[i])
if extra: parts.append(np.array(extra)); mats.append(np.array(em))
tri2 = np.concatenate(parts); mi2 = np.concatenate(mats)
order = np.argsort(mi2, kind='stable'); tri2 = tri2[order]; mi2 = mi2[order]
v = np.round(np.stack([tri2[..., 0], tri2[..., 2], -tri2[..., 1]], -1).reshape(-1, 3) * 100).astype(np.int64)
uniq, inv = np.unique(v, axis=0, return_inverse=True)
json.dump(dict(pos=uniq.ravel().tolist(), idx=inv.ravel().tolist()), open('viewer3d/geo/Budynek_A_v2.json', 'w'), separators=(',', ':'))
names = list(an['Budynek_A']['matcol'].keys()); groups = []
for i, m in enumerate(names):
    idx = np.where(mi2 == i)[0]
    if len(idx): groups.append(dict(mat=m, start=int(idx[0]) * 3, count=int(len(idx)) * 3, color=an['Budynek_A']['matcol'][m]))
m2 = tri2.reshape(-1, 3)
bldA = dict(file='geo/Budynek_A_v2.json', verts=int(len(uniq)), groups=groups, bbmin=m2.min(0).tolist(), bbmax=m2.max(0).tolist())

# ---------- lokale ----------
units = []; removed = []; merged = None
u512 = next(u for u in D['units'] if u['id'] == 'A512')
for u in D['units']:
    if u['b'] != 'A': continue
    xs = [q[0] for pl in u['poly'] for q in pl]; cx = (min(xs) + max(xs)) / 2
    if u['id'] == 'A512': removed.append(u); continue
    if XA <= cx < XB: removed.append(u); continue
    n = json.loads(json.dumps(u))
    if cx < XA: n['poly'] = [[[round(q[0] + SH, 2), q[1]] for q in pl] for pl in n['poly']]
    if u['id'] == 'A513':
        x5 = [q[0] for pl in u512['poly'] for q in pl]; part = max(0.0, max(x5) - XB) / (max(x5) - min(x5))
        add = round(u512['pu'] * part, 1)
        ys = [q[1] for pl in u512['poly'] for q in pl]
        n['poly'] = n['poly'] + [[[XB, min(ys)], [max(x5), min(ys)], [max(x5), max(ys)], [XB, max(ys)]]]
        n['n'] = '512+513'; n['pu'] = round(u['pu'] + add, 1); n['w'] = round(u['w'] + max(x5) - XB, 1); n['est'] = True
        n['rooms'] = u['rooms'] + [['CZĘŚĆ PO A 512 (SZACUNEK)', add]]
        merged = dict(pu=n['pu'], dodane=add, czesc=round(part, 2), cx=(min(xs) + max(xs)) / 2, cy=(min(q[1] for pl in u['poly'] for q in pl) + max(q[1] for pl in u['poly'] for q in pl)) / 2)
    units.append(n)

# ---------- tekstury pięter ----------
ca, cb = round(XA * PPM), round(XB * PPM)
def cut(arr, fill):
    blank = np.full((arr.shape[0], cb - ca) + arr.shape[2:], fill, arr.dtype)
    return np.concatenate([blank, arr[:, :ca], arr[:, cb:]], 1)
fonts = '/usr/share/fonts/truetype/dejavu/'
floors = []
for fl in [fl_['fl'] for fl_ in D['floors'] if fl_['b'] == 'A']:
    mk = np.asarray(Image.open(f'out/maski/MarinaHel_A_pietro{fl}.png')) > 0
    mask = cut(ndi.maximum_filter1d(ndi.maximum_filter1d(mk.view(np.uint8), 7, axis=0), 7, axis=1) > 0, False)
    for suf in ('', '_opis'):
        a0 = np.asarray(Image.open(f'out/tekstury/MarinaHel_A_pietro{fl}{suf}.png').convert('RGB')).copy()
        if suf and fl == 5:                      # resztka przeciętej etykiety A 512 tuż za linią cięcia: bierz ten fragment z planu bez opisów
            y5 = [q[1] for pl in u512['poly'] for q in pl]; cy = round((min(y5) + max(y5)) / 2 * PPM)
            plain = np.asarray(Image.open(f'out/tekstury/MarinaHel_A_pietro{fl}.png').convert('RGB'))
            a0[cy - 70:cy + 70, cb:cb + 80] = plain[cy - 70:cy + 70, cb:cb + 80]
        a = cut(a0, 255)
        im = Image.fromarray(np.dstack([a, (mask * 255).astype(np.uint8)]), 'RGBA')
        if suf and fl == 5 and merged:           # nowa etykieta połączonego lokalu
            d = ImageDraw.Draw(im); fb = ImageFont.truetype(fonts + 'DejaVuSans-Bold.ttf', 27); fr = ImageFont.truetype(fonts + 'DejaVuSans.ttf', 21)
            t1, t2 = 'A 512+513', ('~%.1f m²' % merged['pu']).replace('.', ',')
            w = max(d.textlength(t1, font=fb), d.textlength(t2, font=fr)) + 26; x, y = merged['cx'] * PPM, merged['cy'] * PPM
            d.rectangle([x - w / 2, y - 34, x + w / 2, y + 34], fill=(255, 255, 255, 255), outline=(26, 140, 51, 255), width=4)
            d.text((x - d.textlength(t1, font=fb) / 2, y - 30), t1, font=fb, fill=(26, 140, 51, 255))
            d.text((x - d.textlength(t2, font=fr) / 2, y + 4), t2, font=fr, fill=(40, 40, 40, 255))
        if im.width > 4096: im = im.resize((4096, round(im.height * 4096 / im.width)), Image.LANCZOS)
        im.save(f'viewer3d/tex/A{fl}{suf}_v2.webp', quality=80, method=4)
    base = next(f_ for f_ in D['floors'] if f_['b'] == 'A' and f_['fl'] == fl); bb = list(base['bbox'])
    if bb[0] < XA: bb[0] = round(bb[0] + SH, 2)
    floors.append(dict(fl=fl, tex=f'tex/A{fl}_v2.webp', texl=f'tex/A{fl}_opis_v2.webp', bbox=bb))

pu_gone = sum(u['pu'] for u in removed) - (merged['dodane'] if merged else 0)
D['v2'] = dict(building=bldA, floors=floors, units=units, skrocenie_m=round(SH, 1), pas_planu_m=[XA, XB],
               usuniete=[u['b'] + ' ' + u['n'] for u in removed if u['id'] != 'A512'], polaczone='A 512 + A 513',
               lokali_przed=sum(1 for u in D['units'] if u['b'] == 'A'), lokali_po=len(units),
               pu_przed=round(sum(u['pu'] for u in D['units'] if u['b'] == 'A'), 1), pu_po=round(sum(u['pu'] for u in units), 1), pu_mniej=round(pu_gone, 1))
json.dump(D, open('viewer3d/data.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print({k: v for k, v in D['v2'].items() if k not in ('building', 'floors', 'units')}, 'tris', len(tri), '->', len(tri2), 'przyciete', len(extra))
