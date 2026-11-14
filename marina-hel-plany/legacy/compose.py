import fitz,json,re,sys,glob,numpy as np
from reg import info,gray
from numpy.fft import rfft2,irfft2
from PIL import Image
import io
reg=json.load(open('data/reg.json'))
single=json.load(open('data/single.json'))
area={x['flat'].split()[1]:x['area'].split()[0] for x in single['tabs'][0]['investments'][0]['flats'] if x['flat'].startswith('A ')}
KEY=fitz.Rect(563,230,803,362)   # keyplan window on the card page
Z=4
def keyimg(p,polys=None):
    return gray(p,KEY,Z)
def shift(a,b):
    fa=(a<120).astype(np.float32);fb=(b<120).astype(np.float32)
    c=irfft2(rfft2(fa)*np.conj(rfft2(fb)),s=fa.shape)
    i=np.unravel_index(np.argmax(c),c.shape);dy,dx=i
    if dy>fa.shape[0]//2: dy-=fa.shape[0]
    if dx>fa.shape[1]//2: dx-=fa.shape[1]
    return dx/Z,dy/Z
def build(floor,S=15.0,minscore=0.0):
    units=sorted(n for n in reg if n[0]==str(floor))
    ref=units[0]
    pref,_,_,_=info(f'cards/A{ref}.pdf')
    kref=keyimg(pref)
    out=fitz.open()
    W,H=KEY.width*S,KEY.height*S
    page=out.new_page(width=W,height=H)
    # base: keyplan of ref card, highlight removed, lightened
    base=gray(pref,KEY,8).astype(np.float32)
    hlmask=(np.abs(base-128)<14)
    base[hlmask]=255
    base=255-(255-base)*0.38
    im=Image.fromarray(base.astype(np.uint8));bio=io.BytesIO();im.save(bio,'PNG')
    page.insert_image(fitz.Rect(0,0,W,H),stream=bio.getvalue())
    def k2c(x,y,off=(0,0)): return ((x-off[0]-KEY.x0)*S,(y-off[1]-KEY.y0)*S)
    todo=[]
    for n in units:
        f=f'cards/A{n}.pdf'
        p,hl,polys,pc=info(f)
        off=(0,0) if n==ref else shift(keyimg(p),kref)   # this card's key = ref shifted by off
        r=reg[n];K=r['K'];rot=r['rot'];M=r.get('M',260);pc=fitz.Rect(pc.x0,pc.y0,556,pc.y1)
        cx,cy=(hl.x0+hl.x1)/2,(hl.y0+hl.y1)/2
        # plan clip pc rendered at 1px/pt, rotated ccw rot*90 -> size (w,h); placed at (dx,dy) px in key crop (K px per key pt), crop origin = (cx-M/K, cy-M/K)
        pw,ph=pc.width,pc.height
        w,h=(pw,ph) if rot%2==0 else (ph,pw)
        kx0=cx-M/K+r['dx']/K; ky0=cy-M/K+r['dy']/K
        x0,y0=k2c(kx0,ky0,off); x1,y1=k2c(kx0+w/K,ky0+h/K,off)
        todo.append((n,f,pc,rot,fitz.Rect(x0,y0,x1,y1),[[k2c(x,y,off) for x,y in pl] for pl in polys],k2c(cx,cy,off),r['score']))
    sh=page.new_shape()
    for n,f,pc,rot,tr,polys,c,sc in todo:
        for pl in polys:
            if len(pl)>=3:
                sh.draw_polyline([fitz.Point(*q) for q in pl]+[fitz.Point(*pl[0])]); sh.finish(fill=(1,1,1),color=None)
    sh.commit()
    for n,f,pc,rot,tr,polys,c,sc in todo:
        src=fitz.open(f)
        page.show_pdf_page(tr,src,0,clip=pc,rotate=(-90*rot)%360,keep_proportion=False)
    for n,f,pc,rot,tr,polys,c,sc in todo:
        t=f'A {n}';t2=f'{area[n]} m²'
        fs=13
        tw=max(fitz.get_text_length(t,'hebo',fs),fitz.get_text_length(t2,'helv',fs*0.75))+10
        box=fitz.Rect(c[0]-tw/2,c[1]-15,c[0]+tw/2,c[1]+15)
        page.draw_rect(box,color=(0.85,0.2,0.1),fill=(1,1,1),width=0.8,fill_opacity=0.88,radius=0.15)
        page.insert_text((c[0]-fitz.get_text_length(t,'hebo',fs)/2,c[1]-1.5),t,fontname='hebo',fontsize=fs,color=(0.8,0.15,0.05))
        page.insert_text((c[0]-fitz.get_text_length(t2,'helv',fs*0.75)/2,c[1]+10.5),t2,fontname='helv',fontsize=fs*0.75,color=(0.15,0.15,0.15))
    D='/usr/share/fonts/truetype/dejavu/'
    page.insert_text((30,50),f'MARINA HEL APARTAMENTY · budynek A · piętro {floor}',fontname='djb',fontfile=D+'DejaVuSans-Bold.ttf',fontsize=30,color=(0.1,0.1,0.1))
    page.insert_text((30,78),f'Złożenie z {len(units)} kart lokali dostępnych na eurostyl.com.pl (stan 14.11.2026). Szare kontury bez rzutu = lokale niedostępne oraz części wspólne (hole, klatki, windy) według planu piętra z kart.',fontname='dj',fontfile=D+'DejaVuSans.ttf',fontsize=13,color=(0.3,0.3,0.3))
    out.save(f'out/MarinaHel_A_pietro{floor}.pdf',deflate=True,garbage=3)
    pm=out[0].get_pixmap(matrix=fitz.Matrix(1.6,1.6));pm.save(f'out/MarinaHel_A_pietro{floor}.png')
    return [(t[0],round(t[7],2)) for t in todo]
if __name__=='__main__':
    import os;os.makedirs('out',exist_ok=True)
    for fl in sys.argv[1:]: print(fl,build(int(fl)))
