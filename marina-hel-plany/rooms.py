"""Krok 3: z każdej karty czyta pomieszczenia (nazwa + m2) i szacuje skalę rzutu (m na pt) z powierzchni pomieszczeń.
Wynik: data/rooms.json."""
import fitz, glob, json, os, re, sys, numpy as np
from scipy import ndimage as ndi
from PIL import Image, ImageDraw
from mhlib import info, isgray, PLAN_X1
Z = 3  # px na pt
AREA = re.compile(r'(\d+[.,]\d+)\s*m\s*[²2]')
def parse_rooms(p, pc):
    """Czyta pary nazwa pomieszczenia + powierzchnia z linii tekstu rzutu."""
    lines = []
    for b in p.get_text('dict')['blocks']:
        for l in b.get('lines', []):
            t = ' '.join(''.join(s['text'] for s in l['spans']).split())
            x0, y0, x1, y1 = l['bbox']
            if t and x1 < PLAN_X1 and y0 > pc.y0 and y1 < pc.y1 and abs(l['dir'][0]) > 0.9: lines.append([x0, y0, x1, y1, t])
    UP = r'[A-ZĄĆĘŁŃÓŚŹŻ]{3,}'
    isname = lambda t: re.search(UP, t) and not AREA.search(t) and not re.search(r'SUFIT|SIEMENS|TM\+TT', t)
    out = []
    for r in lines:
        m = AREA.search(r[4])
        if not m: continue
        a = float(m.group(1).replace(',', '.')); name = r[4][:m.start()].strip(' :≈'); box = list(r[:4])
        if not re.search(UP + '|w tym', name):
            cx = (r[0] + r[2]) / 2; parts = []; y = r[1]
            while True:   # zbieraj linie nazwy bezpośrednio nad powierzchnią
                cand = [n for n in lines if isname(n[4]) and -2 <= y - n[1] < 13 and n is not r and abs((n[0] + n[2]) / 2 - cx) < 40 and n[4] not in parts]
                if not cand: break
                n = min(cand, key=lambda n: abs(y - n[1] - 8)); parts.insert(0, n[4]); y = n[1]
                box = [min(box[0], n[0]), n[1], max(box[2], n[2]), box[3]]
                if len(parts) >= 3: break
            if not parts: continue
            name = ' '.join(parts)
        out.append(dict(name=name, area=a, cx=(box[0] + box[2]) / 2, cy=(box[1] + box[3]) / 2, approx='≈' in r[4]))
    return out
def barriers(p, pc):
    W, H = int(pc.width * Z), int(pc.height * Z)
    im = Image.new('L', (W, H), 0); d0 = ImageDraw.Draw(im); im2 = Image.new('L', (W, H), 0); d = d0
    T = lambda q: ((q.x - pc.x0) * Z, (q.y - pc.y0) * Z)
    for g in p.get_drawings():
        r = g['rect']
        if r.x0 > PLAN_X1 or r.y1 < pc.y0 or r.y0 > pc.y1: continue
        fl = g.get('fill'); co = g.get('color'); w = g.get('width') or 0; d = d0
        if fl is not None and isgray(fl, 0.27, 0.06):          # ściany konstrukcyjne
            pts = []
            for it in g['items']:
                if it[0] == 'l': pts += [T(it[1]), T(it[2])]
                elif it[0] == 're':
                    q = it[1]; d.rectangle([(q.x0 - pc.x0) * Z, (q.y0 - pc.y0) * Z, (q.x1 - pc.x0) * Z, (q.y1 - pc.y0) * Z], fill=255)
            if len(pts) >= 3: d.polygon(pts, fill=255)
        elif co is not None and fl is None and not d0 is None:
            d = ImageDraw.Draw(im2)       # obrys/kreskowanie ścianek działowych
            for it in g['items']:
                if it[0] == 'l':
                    dx, dy = abs(it[1].x - it[2].x), abs(it[1].y - it[2].y)
                    if isgray(co, 0.27, 0.04) and 0.4 < w < 0.7: d.line([T(it[1]), T(it[2])], fill=255, width=int(1.3 * Z))
    st = np.array(im) > 0
    return st | (np.array(im2) > 0), st
def calibrate(f, door_m=1.15):
    p, hl, polys, pc, walls = info(f)
    rooms = parse_rooms(p, pc)
    bar, struct = barriers(p, pc)
    bar = ndi.binary_closing(bar, np.ones((3, 3)))
    H_, W_ = bar.shape
    est = []
    # skala startowa z bilansu: suma pomieszczeń ~ 0.86 pola obrysu ścian
    inner = [r for r in rooms if not re.search('BALKON|TARAS|OGR|LOGGIA|w tym', r['name'], re.I)]
    for it in range(3):
        s0 = est and float(np.median(est)) or None
        if s0 is None:
            tot = sum(r['area'] for r in inner)
            s0 = (tot / 0.8 / max(walls.get_area(), 1)) ** 0.5 if inner else 0.03
        k = max(3, int(door_m / s0 * Z)) | 1
        L = int(3.2 / s0 * Z) | 1; R = int(0.7 / s0 * Z) | 1; u = struct.view(np.uint8)
        pad = np.pad(u, L); cl = np.pad(bar.view(np.uint8), L)
        free = cl[L:-L, L:-L] == 0
        er = ndi.minimum_filter1d(ndi.minimum_filter1d(free.view(np.uint8), k, axis=0), k, axis=1)
        op = ndi.maximum_filter1d(ndi.maximum_filter1d(er, k, axis=0), k, axis=1) > 0
        lab, nl = ndi.label(op)
        est = []
        for r in inner:
            r.pop('lab', None); r.pop('s', None)
            x, y = int((r['cx'] - pc.x0) * Z), int((r['cy'] - pc.y0) * Z)
            if not (0 <= y < lab.shape[0] and 0 <= x < lab.shape[1]): continue
            l = lab[y, x]
            if l == 0:
                w = lab[max(0, y - 20):y + 20, max(0, x - 20):x + 20]; v = w[w > 0]
                if not len(v): continue
                l = np.bincount(v).argmax()
            # region pomieszczenia: składowa po otwarciu, dopełniona o wolne piksele w sąsiedztwie (narożniki)
            reg = lab == l
            if reg[0].any() or reg[-1].any() or reg[:, 0].any() or reg[:, -1].any(): continue   # przeciek na zewnątrz
            apx = reg.sum() / Z / Z
            r['pt2'] = float(apx); r['lab'] = int(l)
        # pomieszczenia, które zlały się w jedną składową, sumujemy
        groups = {}
        for r in inner:
            if 'lab' in r: groups.setdefault(r['lab'], []).append(r)
        for l, rs in groups.items():
            a = sum(x['area'] for x in rs); s = (a / rs[0]['pt2']) ** 0.5
            est.append(s)
            for x in rs: x['s'] = s; x['merged'] = len(rs)
    return dict(rooms=[{k: v for k, v in r.items() if k != 'lab'} for r in rooms],
                s_all=est, s=float(np.median(est)) if est else None, pc=list(pc), walls=list(walls))
if __name__ == '__main__':
    from multiprocessing import Pool
    fs = sorted(glob.glob('cards/*.pdf'))
    if len(sys.argv) > 1:
        for n in sys.argv[1:]:
            c = calibrate(f'cards/{n}.pdf'); print(n, 's=%.4f' % c['s'], ['%.4f' % x for x in c['s_all']])
            for r in c['rooms']: print('   ', r['name'], r['area'], '%.4f' % r.get('s', 0), r.get('merged'))
    else:
        with Pool(2) as pool: r = pool.map(calibrate, fs)
        json.dump({os.path.basename(f)[:-4]: c for f, c in zip(fs, r)}, open('data/rooms.json', 'w'), ensure_ascii=False, indent=0)
        print(len(r))
