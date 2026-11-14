"""Wspólne funkcje: odczyt karty lokalu (PDF Euro Styl) i dopasowanie rzutu do planu piętra (keyplanu)."""
import fitz, numpy as np, re
from scipy import ndimage as ndi
from numpy.fft import rfft2, irfft2

PLAN_X1 = 556            # rzut lokalu leży na lewo od tej współrzędnej (pt)
KEY = fitz.Rect(566, 180, 800, 400)   # okno planu piętra na karcie (pt)

def isgray(c, v, tol=0.03):
    return c is not None and all(abs(x - v) < tol for x in c[:3])

def info(f):
    """Zwraca: strona, obrys zaznaczenia na keyplanie, jego wielokąty, prostokąt rzutu, bbox ścian rzutu."""
    p = fitz.open(f)[0]
    hl = fitz.Rect(); polys = []; walls = fitz.Rect()
    for g in p.get_drawings():
        r = g['rect']; fl = g.get('fill')
        if fl is None: continue
        if r.x0 > PLAN_X1 and r.y0 > KEY.y0 and r.y1 < KEY.y1 + 40 and isgray(fl, 0.502):
            hl |= r; pts = []
            for it in g['items']:
                if it[0] == 'l': pts.append((it[1].x, it[1].y))
                elif it[0] == 're':
                    q = it[1]; pts += [(q.x0, q.y0), (q.x1, q.y0), (q.x1, q.y1), (q.x0, q.y1)]
            polys.append(pts)
        elif r.x1 < PLAN_X1 and r.y0 > 72 and isgray(fl, 0.27, 0.06):
            walls |= r
    y1 = 548
    for b in p.get_text('blocks'):
        if b[0] < 590 and re.search('Planowana lokalizacja|cianki dzia|Lokal przystosowany|Zmiany lokatorskie', b[4]):
            y1 = min(y1, b[1] - 4)
    return p, hl, polys, fitz.Rect(0, 72, PLAN_X1, y1), walls

def gray(p, clip, z):
    pm = p.get_pixmap(matrix=fitz.Matrix(z, z), clip=clip, colorspace=fitz.csGRAY)
    return np.frombuffer(pm.samples, np.uint8).reshape(pm.h, pm.w)

def feat(a, thr=110, s=1.5):
    b = ndi.gaussian_filter((a < thr).astype(np.float32), s)
    return b - b.mean()

def register(p, hl, pc, K, M=330):
    """Korelacja FFT rzutu (1 px/pt) z wycinkiem keyplanu wyrenderowanym w skali K px/pt."""
    cx, cy = (hl.x0 + hl.x1) / 2, (hl.y0 + hl.y1) / 2
    kc = fitz.Rect(cx - M / K, cy - M / K, cx + M / K, cy + M / K)
    kf = feat(gray(p, kc, K), thr=100)
    pf = feat(gray(p, pc, 1.0))
    H, W = kf.shape; h, w = pf.shape; SH, SW = H + h, W + w
    A = np.zeros((SH, SW), np.float32); A[:H, :W] = kf
    B = np.zeros((SH, SW), np.float32); B[:h, :w] = pf
    c = irfft2(rfft2(A) * np.conj(rfft2(B)), s=(SH, SW))
    i = np.unravel_index(np.argmax(c), c.shape); dy, dx = i
    if dy > SH - h: dy -= SH
    if dx > SW - w: dx -= SW
    sc = c[i] / (np.linalg.norm(pf) * np.linalg.norm(kf) + 1e-9)
    return float(sc), int(dx), int(dy)
