"""Krok 2: dla każdej karty szuka skali K (rzut/keyplan) i przesunięcia. Wynik: data/reg.json."""
import glob, json, re, os, sys, numpy as np
from multiprocessing import Pool
from mhlib import info, register
def work(f):
    n = os.path.basename(f)[:-4]
    try:
        p, hl, polys, pc, walls = info(f)
        if hl.is_empty or walls.is_empty: return n, None
        K0 = (walls.get_area() / hl.get_area()) ** 0.5
        best = None
        for K in K0 * np.arange(0.6, 1.5001, 0.025):
            b = register(p, hl, pc, float(K))
            if best is None or b[0] > best[1][0]: best = (float(K), b)
        Kc = best[0]
        for K in Kc * np.arange(0.98, 1.0201, 0.004):
            b = register(p, hl, pc, float(K))
            if b[0] > best[1][0]: best = (float(K), b)
        return n, dict(K=best[0], K0=K0, score=best[1][0], dx=best[1][1], dy=best[1][2], M=330)
    except Exception as e:
        return n, dict(error=str(e))
if __name__ == '__main__':
    fs = sorted(glob.glob('cards/*.pdf'))
    if len(sys.argv) > 1: fs = [f for f in fs if re.search(sys.argv[1], f)]
    with Pool(4) as pool: r = pool.map(work, fs, chunksize=1)
    reg = json.load(open('data/reg.json')) if os.path.exists('data/reg.json') else {}
    reg.update({n: v for n, v in r})
    json.dump(reg, open('data/reg.json', 'w'), indent=0)
    for n, v in r: print(n, v and ('K%.2f (K0 %.2f) s%.2f' % (v['K'], v['K0'], v['score']) if 'K' in v else v))
