import fitz,numpy as np,re,json,sys,glob
from scipy import ndimage as ndi
from numpy.fft import rfft2,irfft2
def info(f):
    p=fitz.open(f)[0]
    hl=fitz.Rect();polys=[]
    for g in p.get_drawings():
        r=g['rect'];fl=g.get('fill')
        if r.x0>590 and 225<r.y0 and r.y1<440 and fl and abs(fl[0]-0.502)<0.02 and abs(fl[1]-0.502)<0.02 and abs(fl[2]-0.502)<0.02:
            hl|=r
            pts=[]
            for it in g['items']:
                if it[0]=='l': pts.append((it[1].x,it[1].y))
                elif it[0]=='re':
                    q=it[1];pts+= [(q.x0,q.y0),(q.x1,q.y0),(q.x1,q.y1),(q.x0,q.y1)]
            polys.append(pts)
    y1=548
    for b in p.get_text('blocks'):
        t=b[4]
        if b[0]<590 and re.search('Planowana lokalizacja|cianki dzia|Lokal przystosowany|Zmiany lokatorskie',t): y1=min(y1,b[1]-4)
    return p,hl,polys,fitz.Rect(0,72,590,y1)
def gray(p,clip,z):
    pm=p.get_pixmap(matrix=fitz.Matrix(z,z),clip=clip,colorspace=fitz.csGRAY)
    return np.frombuffer(pm.samples,np.uint8).reshape(pm.h,pm.w)
def feat(a,thr=110,s=1.5):
    b=(a<thr).astype(np.float32)
    b=ndi.gaussian_filter(b,s)
    return b-b.mean()
def register(f,K=15.0,M=260,rots=(0,1,2,3)):
    p,hl,polys,pc=info(f)
    cx,cy=(hl.x0+hl.x1)/2,(hl.y0+hl.y1)/2
    kc=fitz.Rect(cx-M/K,cy-M/K,cx+M/K,cy+M/K)
    kimg=gray(p,kc,K); kf=feat(kimg,thr=100)
    pimg=gray(p,pc,1.0)
    best=None
    H,W=kf.shape
    for rot in rots:
        pr=np.rot90(pimg,rot)  # ccw rot*90
        pf=feat(pr)
        h,w=pf.shape
        SH,SW=H+h,W+w
        A=np.zeros((SH,SW),np.float32);A[:H,:W]=kf
        B=np.zeros((SH,SW),np.float32);B[:h,:w]=pf
        c=irfft2(rfft2(A)*np.conj(rfft2(B)),s=(SH,SW))
        i=np.unravel_index(np.argmax(c),c.shape)
        dy,dx=i
        if dy>SH-h: dy-=SH
        if dx>SW-w: dx-=SW
        sc=c[i]/ (np.linalg.norm(pf)*np.linalg.norm(kf)+1e-9)
        if best is None or sc>best[0]: best=(float(sc),rot,int(dx),int(dy))
    return best,hl,polys,pc,kc
if __name__=='__main__':
    for n in sys.argv[1:]:
        for K in (14.0,14.5,15.0,15.5,16.0):
            b=register(f'cards/A{n}.pdf',K)[0]
            print(n,K,'%.3f rot%d dx%d dy%d'%b)
