"""Krok 6b: maska każdej płaszczyzny piętra = obrys budynku + własny obszar każdego lokalu (z balkonem/tarasem/ogródkiem).
Wszystko poza maską (schody terenowe, garaż pod dziedzińcem, opisy z odnośnikami) jest wycinane z tekstur.
Wynik: out/maski/*.png, out/kontrola/maska_*.png (czerwone = wycięte), data/maski_kontrola.json."""
import json, os, re, sys, numpy as np, fitz
from scipy import ndimage as ndi
from PIL import Image, ImageDraw
import compose as c
from commons import sq
from mhlib import info, KEY
Image.MAX_IMAGE_PIXELS = None
PPM = c.PPM; Z = 8
def run(bld):
    sk = c.scale[bld]['m_per_keypt']; L = c.layout(bld); bb = c.content_bbox(L)
    ox, oy = bb.x0 - 10 / sk, bb.y0 - 10 / sk
    W, H = Image.open(f'out/tekstury/MarinaHel_{bld}_pietro2.png').size
    S = lambda x, y: ((x - ox) * sk * PPM, (y - oy) * sk * PPM)
    foot = {}; out = []
    for fl, d in sorted(L.items()):
        # obrys budynku z planu piętra (grube ściany + lokale, domknięte)
        a = c.clean_key(info(f"cards/{d['ref']}.pdf")[0], Z); h, w = a.shape; g = d['goff']
        walls = sq(a < 150, 3, 'open'); um = Image.new('L', (w, h), 0); dr = ImageDraw.Draw(um)
        for it in d['items']:
            for pl in it['polys']: dr.polygon([((x + g[0] - KEY.x0) * Z, (y + g[1] - KEY.y0) * Z) for x, y in pl], fill=255)
        mpp = sk / Z
        inside = ndi.binary_fill_holes(sq(walls | (np.array(um) > 0), int(2.6 / mpp) | 1, 'close'))
        x0, y0 = S(KEY.x0 - g[0], KEY.y0 - g[1]); sc = sk * PPM / Z
        F = Image.new('L', (W, H), 0)
        F.paste(Image.fromarray((inside * 255).astype(np.uint8)).resize((round(w * sc), round(h * sc)), Image.NEAREST), (round(x0), round(y0)))
        foot[fl] = np.array(F) > 0
    typ = foot[2]
    for fl, d in sorted(L.items()):
        F = foot[fl].copy()
        if bld == 'A' and fl == 0: F &= sq(typ, 81, 'close') | ndi.maximum_filter1d(ndi.maximum_filter1d(typ.view(np.uint8), 81, axis=0), 81, axis=1) > 0
        mask = F.copy(); rep = []
        for it in d['items']:
            doc = fitz.open(); page = doc.new_page(width=W, height=H)
            x0, y0 = S(it['rect'][0], it['rect'][1]); x1, y1 = S(it['rect'][2], it['rect'][3])
            page.show_pdf_page(fitz.Rect(x0, y0, x1, y1), fitz.open(it['f']), 0, clip=it['pc'], keep_proportion=False)
            clip = fitz.Rect(max(0, x0), max(0, y0), min(W, x1), min(H, y1)).round()
            pm = page.get_pixmap(clip=clip, colorspace=fitz.csGRAY, alpha=False)
            ink = np.frombuffer(pm.samples, np.uint8).reshape(pm.h, pm.w) < 235
            reg = sq(ndi.binary_fill_holes(sq(ink, 17, 'close')), 33, 'open')       # domknięcie 0,4 m, wypełnienie, usunięcie cienkich odnośników (<0,8 m)
            lab, n = ndi.label(reg)
            if n > 1:      # zostaw części stykające się z obrysem lokalu z keyplanu (odrzuca luźne opisy)
                pm2 = Image.new('L', (pm.w, pm.h), 0); dr = ImageDraw.Draw(pm2)
                for pl in it['polys']: dr.polygon([(S(*q)[0] - clip.x0, S(*q)[1] - clip.y0) for q in pl], fill=255)
                keep = np.unique(lab[np.array(pm2) > 0]); reg = np.isin(lab, keep[keep > 0])
            mask[clip.y0:clip.y0 + pm.h, clip.x0:clip.x0 + pm.w] |= reg
            poly_m2 = sum(abs(sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))) / 2 for p in it['polys']) * sk * sk
            rooms = c.rooms.get(it['n'], {}).get('rooms', [])
            outd = sum(r['area'] for r in rooms if re.search('BALKON|TARAS|OGR|LOGGIA', r['name'], re.I) and not re.search('w tym', r['name'], re.I))
            area = reg.sum() / PPM / PPM
            rep.append(dict(id=it['n'], obszar_m2=round(float(area), 1), oczekiwane_m2=round(float(poly_m2 + outd), 1), zewn_m2=round(outd, 1), stosunek=round(float(area / (poly_m2 + outd)), 3)))
        os.makedirs('out/maski', exist_ok=True)
        Image.fromarray((mask * 255).astype(np.uint8)).save(f'out/maski/MarinaHel_{bld}_pietro{fl}.png')
        tex = np.asarray(Image.open(f'out/tekstury/MarinaHel_{bld}_pietro{fl}.png').convert('RGB'))
        ink = tex.min(2) < 200; cut = ink & ~mask
        lab, n = ndi.label(sq(cut, 9, 'close')); blobs = []
        for i, sl in enumerate(ndi.find_objects(lab), 1):
            ar = (sl[0].stop - sl[0].start) * (sl[1].stop - sl[1].start) / PPM / PPM
            if ar > 1.0: blobs.append(dict(m2=round(ar, 1), x=round(sl[1].start / PPM, 1), y=round(sl[0].start / PPM, 1), w=round((sl[1].stop - sl[1].start) / PPM, 1), h=round((sl[0].stop - sl[0].start) / PPM, 1)))
        vis = tex.copy(); vis[~mask] = (vis[~mask] * 0.35 + np.array([40, 60, 90]) * 0.65).astype(np.uint8); vis[cut] = (230, 30, 30)
        Image.fromarray(vis).resize((W // 2, H // 2)).save(f'out/kontrola/maska_{bld}_pietro{fl}.png')
        out.append(dict(budynek=bld, pietro=fl, wyciete_wieksze_niz_1m2=sorted(blobs, key=lambda b: -b['m2'])[:12], lokale=rep))
        low = [r for r in rep if r['stosunek'] < 0.93]
        print(bld, fl, 'lokali', len(rep), 'min stosunek %.2f' % min(r['stosunek'] for r in rep), 'ponizej 0.93:', [(r['id'], r['stosunek'], r['zewn_m2']) for r in low], '| wyciete >1m2:', [(b['m2'], b['x'], b['y']) for b in out[-1]['wyciete_wieksze_niz_1m2'][:6]])
    return out
if __name__ == '__main__':
    res = run('A') + run('B'); json.dump(res, open('data/maski_kontrola.json', 'w'), ensure_ascii=False, indent=1)
