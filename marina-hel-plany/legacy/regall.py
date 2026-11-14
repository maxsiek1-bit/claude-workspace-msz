import glob,re,json,numpy as np
from multiprocessing import Pool
from reg import register
def work(f):
    n=re.search(r'A(\d+)',f).group(1)
    best=None
    for K in np.arange(11,20.01,0.5):
        b=register(f,float(K))[0]
        if best is None or b[0]>best[1][0]: best=(float(K),b)
    K0=best[0]
    for K in np.arange(K0-0.4,K0+0.41,0.1):
        b=register(f,float(K))[0]
        if b[0]>best[1][0]: best=(float(K),b)
    return n,best
if __name__=='__main__':
    with Pool(8) as p: r=p.map(work,sorted(glob.glob('cards/A*.pdf')))
    json.dump({n:dict(K=b[0],score=b[1][0],rot=b[1][1],dx=b[1][2],dy=b[1][3]) for n,b in r},open('data/reg.json','w'))
    for n,b in r: print(n,'K%.1f s%.2f rot%d'%(b[0],b[1][0],b[1][1]),end=' | ')
