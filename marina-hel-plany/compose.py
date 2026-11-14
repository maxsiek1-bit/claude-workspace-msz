"""Krok 5: składa plany pięter (PDF + PNG), tekstury pięter w stałej skali i dane wymiarowe.
Układ współrzędnych budynku: metry, oś X w prawo, oś Y w dół, wspólny dla wszystkich pięter budynku.
Użycie: python3 compose.py [A|B ...]"""
import fitz, json, re, sys, os, io, glob, collections, numpy as np
from numpy.fft import rfft2, irfft2
from PIL import Image
from mhlib import info, gray, KEY, PLAN_X1
PPM = 40.0                       # pt strony (i px tekstury) na 1 metr
D = '/usr/share/fonts/truetype/dejavu/'
STATUS = {'available': ('dostępny', (0.10, 0.55, 0.20)), 'reserved': ('zarezerwowany', (0.90, 0.55, 0.05)),
          'sold': ('sprzedany', (0.75, 0.15, 0.10)), 'not_available': ('niedostępny', (0.45, 0.45, 0.45))}
reg = json.load(open('data/reg.json')); rooms = json.load(open('data/rooms.json')); scale = json.load(open('data/scale.json'))
viewer = {}
for b in json.load(open('data/viewer.json')):
    for x in b['apartments']:
        k = b['number'] + x['symbol']
        if k not in viewer or x['status'] == 'available' or (viewer[k]['status'] != 'available' and x['pdfUrl']): viewer[k] = x
def floor_of(n):
    b, s = n[0], n[1:]
    if s[0] == 'U': return 0
    return int(s[0]) if b == 'A' else int(s[0]) - 1
def fname(fl): return 'parter' if fl == 0 else f'piętro {fl}'
def keyimg(p, z=4): return gray(p, KEY, z)
def shift(a, b, z=4):
    fa = (a < 120).astype(np.float32); fb = (b < 120).astype(np.float32)
    c = irfft2(rfft2(fa) * np.conj(rfft2(fb)), s=fa.shape)
    i = np.unravel_index(np.argmax(c), c.shape); dy, dx = i
    if dy > fa.shape[0] // 2: dy -= fa.shape[0]
    if dx > fa.shape[1] // 2: dx -= fa.shape[1]
    return dx / z, dy / z
def clean_key(p, z):
    a = gray(p, KEY, z).astype(np.float32); a[np.abs(a - 128) < 14] = 255; return a
def layout(bld):
    """Zbiera położenie wszystkich lokali budynku we wspólnych współrzędnych keyplanu (pt)."""
    units = sorted(n for n in reg if n[0] == bld and reg[n] and 'K' in reg[n])
    floors = collections.defaultdict(list)
    for n in units: floors[floor_of(n)].append(n)
    gfl = max(floors, key=lambda f: len(floors[f])); gref = floors[gfl][0]
    gimg = keyimg(info(f'cards/{gref}.pdf')[0])
    L = {}
    for fl, us in sorted(floors.items()):
        ref = us[0]; pref = info(f'cards/{ref}.pdf')[0]; kref = keyimg(pref)
        goff = (0, 0) if ref == gref else shift(kref, gimg)
        items = []
        for n in us:
            f = f'cards/{n}.pdf'; p, hl, polys, pc, walls = info(f)
            o = (0, 0) if n == ref else shift(keyimg(p), kref)
            off = (o[0] + goff[0], o[1] + goff[1])
            r = reg[n]; K = r['K']; M = r['M']
            cx, cy = (hl.x0 + hl.x1) / 2, (hl.y0 + hl.y1) / 2
            kx0 = cx - M / K + r['dx'] / K - off[0]; ky0 = cy - M / K + r['dy'] / K - off[1]
            items.append(dict(n=n, f=f, pc=pc, K=K, rect=(kx0, ky0, kx0 + pc.width / K, ky0 + pc.height / K),
                              polys=[[(x - off[0], y - off[1]) for x, y in pl] for pl in polys if len(pl) >= 3],
                              c=(cx - off[0], cy - off[1]), score=r['score']))
        L[fl] = dict(ref=ref, goff=goff, items=items)
    return L
def content_bbox(L):
    pts = [q for d in L.values() for it in d['items'] for pl in it['polys'] for q in pl]
    xs = [q[0] for q in pts]; ys = [q[1] for q in pts]
    return fitz.Rect(min(xs), min(ys), max(xs), max(ys))
def build(bld):
    sk = scale[bld]['m_per_keypt']; S = PPM * sk
    L = layout(bld); bb = content_bbox(L)
    pad_m = 10.0; ox, oy = bb.x0 - pad_m / sk, bb.y0 - pad_m / sk      # początek układu (m) = obrys wszystkich lokali budynku + margines 10 m
    Wm, Hm = bb.width * sk + 2 * pad_m, bb.height * sk + 2 * pad_m
    W, H = Wm * PPM, Hm * PPM; TOP = 110
    k2m = lambda x, y: ((x - ox) * sk, (y - oy) * sk)
    out_units = []; out_floors = []
    for fl, d in sorted(L.items()):
        pref = info(f"cards/{d['ref']}.pdf")[0]
        base = clean_key(pref, 12); base = 255 - (255 - base) * 0.45
        bio = io.BytesIO(); Image.fromarray(base.astype(np.uint8)).save(bio, 'PNG')
        kx, ky = k2m(KEY.x0 - d['goff'][0], KEY.y0 - d['goff'][1])
        for variant in ('tekstura', 'plan'):
            top = TOP if variant == 'plan' else 0
            doc = fitz.open(); page = doc.new_page(width=W, height=H + top)
            P = lambda x, y: (k2m(x, y)[0] * PPM, k2m(x, y)[1] * PPM + top)
            page.insert_image(fitz.Rect(kx * PPM, ky * PPM + top, kx * PPM + KEY.width * S, ky * PPM + top + KEY.height * S), stream=bio.getvalue())
            sh = page.new_shape()
            for it in d['items']:
                for pl in it['polys']:
                    sh.draw_polyline([fitz.Point(*P(*q)) for q in pl] + [fitz.Point(*P(*pl[0]))]); sh.finish(fill=(1, 1, 1), color=None)
            sh.commit()
            for it in d['items']:
                x0, y0 = P(it['rect'][0], it['rect'][1]); x1, y1 = P(it['rect'][2], it['rect'][3])
                page.show_pdf_page(fitz.Rect(x0, y0, x1, y1), fitz.open(it['f']), 0, clip=it['pc'], keep_proportion=False)
            if variant == 'plan':
                for it in d['items']:
                    v = viewer.get(it['n'], {}); st = STATUS.get(v.get('status'), STATUS['not_available'])
                    c = P(*it['c']); t = f"{bld} {it['n'][1:]}"; t2 = f"{float(v.get('area', 0)):.2f} m²".replace('.', ',')
                    fs = 13; tw = max(fitz.get_text_length(t, 'hebo', fs), fitz.get_text_length(t2, 'helv', fs * 0.75)) + 12
                    box = fitz.Rect(c[0] - tw / 2, c[1] - 15, c[0] + tw / 2, c[1] + 15)
                    page.draw_rect(box, color=st[1], fill=(1, 1, 1), width=1.6, fill_opacity=0.9, radius=0.15)
                    page.insert_text((c[0] - fitz.get_text_length(t, 'hebo', fs) / 2, c[1] - 1.5), t, fontname='hebo', fontsize=fs, color=st[1])
                    page.insert_text((c[0] - fitz.get_text_length(t2, 'helv', fs * 0.75) / 2, c[1] + 10.5), t2, fontname='dj', fontfile=D + 'DejaVuSans.ttf', fontsize=fs * 0.75, color=(0.15, 0.15, 0.15))
                page.insert_text((30, 46), f'MARINA HEL APARTAMENTY · budynek {bld} · {fname(fl)}', fontname='djb', fontfile=D + 'DejaVuSans-Bold.ttf', fontsize=28, color=(0.1, 0.1, 0.1))
                cnt = collections.Counter(viewer.get(it['n'], {}).get('status', 'not_available') for it in d['items'])
                page.insert_text((30, 70), f"Złożenie z {len(d['items'])} kart lokali Euro Stylu (stan 14.11.2026). Skala: 1 m = {PPM:.0f} pt, wyliczona z powierzchni pomieszczeń (dokładność ok. ±{max(1, round(2 * scale[bld]['spread_pct']))}%). "
                                 f"Arkusz {Wm:.1f} × {Hm:.1f} m.", fontname='dj', fontfile=D + 'DejaVuSans.ttf', fontsize=12, color=(0.3, 0.3, 0.3))
                x = 30
                for k, (lab, col) in STATUS.items():
                    page.draw_rect(fitz.Rect(x, 82, x + 14, 96), color=col, fill=(1, 1, 1), width=1.6)
                    page.insert_text((x + 20, 94), f'{lab}: {cnt.get(k, 0)}', fontname='dj', fontfile=D + 'DejaVuSans.ttf', fontsize=12, color=col); x += 170
                # podziałka 10 m
                page.draw_line((W - 30 - 10 * PPM, 60), (W - 30, 60), color=(0, 0, 0), width=2)
                for i in range(11): page.draw_line((W - 30 - i * PPM, 54 if i % 5 else 48), (W - 30 - i * PPM, 60), color=(0, 0, 0), width=1)
                page.insert_text((W - 30 - 10 * PPM, 78), '0', fontname='helv', fontsize=11); page.insert_text((W - 52, 78), '10 m', fontname='helv', fontsize=11)
                stem = f'out/plany/MarinaHel_{bld}_pietro{fl}'
                doc.save(stem + '.pdf', deflate=True, garbage=3)
                z = min(1.0, 5000 / W); doc[0].get_pixmap(matrix=fitz.Matrix(z, z)).save(stem + '.png')
            else:
                stem = f'out/tekstury/MarinaHel_{bld}_pietro{fl}'
                doc.save(stem + '.pdf', deflate=True, garbage=3)
                doc[0].get_pixmap(matrix=fitz.Matrix(1, 1)).save(stem + '.png')
        out_floors.append(dict(budynek=bld, pietro=fl, nazwa=fname(fl), lokali_na_planie=len(d['items']),
                               tekstura=f'out/tekstury/MarinaHel_{bld}_pietro{fl}.png', plan=f'out/plany/MarinaHel_{bld}_pietro{fl}.pdf'))
        for it in d['items']:
            v = viewer.get(it['n'], {}); rm = rooms.get(it['n'], {})
            polys = [[[round(c, 2) for c in k2m(*q)] for q in pl] for pl in it['polys']]
            xs = [q[0] for pl in polys for q in pl]; ys = [q[1] for pl in polys for q in pl]
            out_units.append(dict(id=it['n'], budynek=bld, numer=it['n'][1:], pietro=fl, status=v.get('status'), pu_m2=float(v['area']) if v.get('area') else None,
                cena=None, obrys_m=polys, bbox_m=[round(min(xs), 2), round(min(ys), 2), round(max(xs), 2), round(max(ys), 2)],
                szer_x_m=round(max(xs) - min(xs), 2), gleb_y_m=round(max(ys) - min(ys), 2), srodek_m=[round(c, 2) for c in k2m(*it['c'])],
                skala_rzutu_m_na_pt=round(sk / it['K'], 5), dopasowanie=round(it['score'], 3),
                pomieszczenia=[dict(nazwa=r['name'], m2=r['area']) for r in rm.get('rooms', [])],
                karta_pdf=it['f'], rzuty_3d=sorted(glob.glob(f"renders/{it['n']}_*.png")), strona=v.get('webUrl')))
    meta = dict(budynek=bld, m_na_pt_keyplanu=sk, px_na_m=PPM, arkusz_m=[round(Wm, 2), round(Hm, 2)], tekstura_px=[round(W), round(H)],
                dokladnosc_skali_pct=round(2 * scale[bld]['spread_pct'], 1), pietra=out_floors,
                opis='Współrzędne w metrach: (0,0) = lewy górny róg tekstury, X w prawo, Y w dół; ten sam układ dla wszystkich pięter budynku.')
    return meta, out_units
if __name__ == '__main__':
    os.makedirs('out/plany', exist_ok=True); os.makedirs('out/tekstury', exist_ok=True)
    blds = sys.argv[1:] or ['A', 'B']
    allm = json.load(open('data/budynki.json')) if os.path.exists('data/budynki.json') else {}
    allu = json.load(open('data/lokale.json')) if os.path.exists('data/lokale.json') else []
    for b in blds:
        meta, units = build(b); allm[b] = meta
        allu = [u for u in allu if u['budynek'] != b] + units
        print(b, meta['arkusz_m'], len(units))
    json.dump(allm, open('data/budynki.json', 'w'), ensure_ascii=False, indent=1)
    json.dump(sorted(allu, key=lambda u: u['id']), open('data/lokale.json', 'w'), ensure_ascii=False, indent=1)
