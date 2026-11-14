import json,numpy as np
from multiprocessing import Pool
from reg import register
def work(n):
    f=f'cards/A{n}.pdf';best=None
    for K in np.arange(9,34.01,0.25):
        b=register(f,float(K),M=330,rots=(0,))[0]
        if best is None or b[0]>best[1][0]: best=(float(K),b)
    K0=best[0]
    for K in np.arange(K0-0.2,K0+0.21,0.05):
        b=register(f,float(K),M=330,rots=(0,))[0]
        if b[0]>best[1][0]: best=(float(K),b)
    return n,best
if __name__=='__main__':
    ns=['301','401','328','428','501','518']
    with Pool(6) as p: r=p.map(work,ns)
    reg=json.load(open('data/reg.json'))
    for n,b in r:
        print(n,b)
        reg[n]=dict(K=b[0],score=b[1][0],rot=0,dx=b[1][2],dy=b[1][3],M=330)
    json.dump(reg,open('data/reg.json','w'))
