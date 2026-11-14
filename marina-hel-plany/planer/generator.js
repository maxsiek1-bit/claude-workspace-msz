/* ===== Generator zabudowy: układa jak najwięcej zespołów budynków (A+B+C w wybranej wersji) na dostępnym terenie =====
   Ten blok jest wklejany do wnętrza skryptu edytora (ma dostęp do S, render, el, inside, segs, wx, hAt, T, is3 ...). */
const PKEY='planer-zabudowa-v1';
let KIT=null, PLAN={variant:'base',gap:12,setback:6,auto:true,angle:0}, RES={}, planTimer=0, planSeq=0;
try{const o=JSON.parse(localStorage.getItem(PKEY));if(o&&typeof o==='object')PLAN=Object.assign(PLAN,o)}catch(e){}
function planPersist(){try{localStorage.setItem(PKEY,JSON.stringify(PLAN))}catch(e){}}
const BCOL={A:'#3f9fc6',A2:'#3f9fc6',B:'#f0b441',C:'#b58ae6',C3:'#b58ae6'}, BCOL3={A:0x3f9fc6,B:0xf0b441,C:0xb58ae6};

/* Obrys odsunięty na zewnątrz o d metrów (przesunięcie wierzchołków wzdłuż dwusiecznych). */
function offsetPoly(p,d){
  if(d<=0)return p;
  let a=0;for(let i=0;i<p.length;i++){const q=p[(i+1)%p.length];a+=p[i][0]*q[1]-q[0]*p[i][1]}
  const sg=a>0?1:-1,n=p.length,out=[];
  for(let i=0;i<n;i++){
    const p0=p[(i+n-1)%n],p1=p[i],p2=p[(i+1)%n];
    let e1x=p1[0]-p0[0],e1y=p1[1]-p0[1],e2x=p2[0]-p1[0],e2y=p2[1]-p1[1];
    const l1=Math.hypot(e1x,e1y)||1,l2=Math.hypot(e2x,e2y)||1;e1x/=l1;e1y/=l1;e2x/=l2;e2y/=l2;
    let nx=sg*(e1y+e2y),ny=-sg*(e1x+e2x);const l=Math.hypot(nx,ny);
    if(l<1e-6){nx=sg*e1y;ny=-sg*e1x}else{nx/=l;ny/=l}
    const cosHalf=Math.max(.35,Math.sqrt(Math.max(0,(1+e1x*e2x+e1y*e2y)/2)));
    out.push([p1[0]+nx*d/cosHalf,p1[1]+ny*d/cosHalf]);
  }
  return out;
}
function segX(a,b,c,d){const o=(p,q,r)=>(q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0]);
  const d1=o(c,d,a),d2=o(c,d,b),d3=o(a,b,c),d4=o(a,b,d);return ((d1>0&&d2<0)||(d1<0&&d2>0))&&((d3>0&&d4<0)||(d3<0&&d4>0))}

/* Teren dopuszczony: wewnątrz granicy, wewnątrz stref pod zabudowę (jeśli są), poza strefami wyłączonymi. */
function planArea(){
  const ok=p=>p.v.length>=3, site=S.polys[0].v;
  if(site.length<3)return null;
  const ex=S.polys.filter(p=>p.kind==='excl'&&ok(p)).map(p=>p.v), bu=S.polys.filter(p=>p.kind==='build'&&ok(p)).map(p=>p.v);
  const edges=[];for(const v of [site].concat(ex,bu))for(let i=0;i<v.length;i++)edges.push([v[i],v[(i+1)%v.length]]);
  let x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;for(const q of site){x0=Math.min(x0,q[0]);y0=Math.min(y0,q[1]);x1=Math.max(x1,q[0]);y1=Math.max(y1,q[1])}
  return {site,ex,bu,edges,bb:[x0,y0,x1,y1],
    allowed(x,y){if(!inside(x,y,site))return false;for(const e of ex)if(inside(x,y,e))return false;if(bu.length){for(const b of bu)if(inside(x,y,b))return true;return false}return true}};
}
/* Najlepszy układ dla jednej wersji. Zwraca {n, angle, items:[{x,y,phi}]} (x, y w pikselach edytora, phi w radianach). */
function planFor(vk,area){
  const V=KIT.variants[vk],mpp=S.mpp,c=V.center,ax=V.axis_deg*Math.PI/180;
  const outs=V.b.map(k=>offsetPoly(KIT.buildings[k].outline,PLAN.setback).map(q=>[q[0]-c[0],q[1]-c[1]]));
  const raw=V.b.map(k=>KIT.buildings[k].outline.map(q=>[q[0]-c[0],q[1]-c[1]]));
  const w=V.size[0]+PLAN.gap,h=V.size[1]+PLAN.gap,[bx0,by0,bx1,by1]=area.bb,cx=(bx0+bx1)/2,cy=(by0+by1)/2;
  const rad=Math.hypot(bx1-bx0,by1-by0)*mpp/2+Math.hypot(w,h);
  const fits=(px,py,phi)=>{
    const co=Math.cos(phi),si=Math.sin(phi);
    for(let b=0;b<outs.length;b++){
      const o=outs[b],n=o.length,pts=new Array(n);
      for(let i=0;i<n;i++){const x=px+(o[i][0]*co-o[i][1]*si)/mpp,y=py-(o[i][0]*si+o[i][1]*co)/mpp;if(!area.allowed(x,y))return false;pts[i]=[x,y]}
      for(let i=0;i<n;i++){const a=pts[i],bq=pts[(i+1)%n];for(const e of area.edges)if(segX(a,bq,e[0],e[1]))return false}
      for(const e of area.ex)if(inside(e[0][0],e[0][1],pts))return false;
    }
    return true;
  };
  const tryLattice=(alpha,oa,ob)=>{
    const phi=alpha-ax,ux=Math.cos(alpha),uy=Math.sin(alpha),ni=Math.ceil(rad/w),nj=Math.ceil(rad/h),items=[];
    for(let i=-ni;i<=ni;i++)for(let j=-nj;j<=nj;j++){
      const mx=(i+oa)*w*ux-(j+ob)*h*uy,my=(i+oa)*w*uy+(j+ob)*h*ux,px=cx+mx/mpp,py=cy-my/mpp;
      if(px<bx0-40||px>bx1+40||py<by0-40||py>by1+40)continue;
      if(fits(px,py,phi))items.push({x:px,y:py,phi});
    }
    return items;
  };
  let best={n:0,angle:0,items:[]};
  const angles=[];if(PLAN.auto)for(let a=0;a<360;a+=6)angles.push(a);else angles.push(PLAN.angle);
  const N=PLAN.auto?5:9;
  for(const deg of angles){const al=deg*Math.PI/180;
    for(let a=0;a<N;a++)for(let b=0;b<N;b++){const it=tryLattice(al,a/N,b/N);if(it.length>best.n)best={n:it.length,angle:deg,items:it}}}
  if(PLAN.auto&&best.n){                                           // doszlifowanie kąta wokół najlepszego
    for(const dd of [-3,-1.5,1.5,3]){const al=(best.angle+dd)*Math.PI/180;
      for(let a=0;a<N;a++)for(let b=0;b<N;b++){const it=tryLattice(al,a/N,b/N);if(it.length>best.n)best={n:it.length,angle:best.angle+dd,items:it}}}
  }
  best.raw=raw;return best;
}
function planStats(vk,n){
  const V=KIT.variants[vk];let lok=0,pu=0,zab=0,unk=0;
  for(const k of V.b){const b=KIT.buildings[k];zab+=b.pow_zabudowy;if(b.lokale==null)unk++;else{lok+=b.lokale;pu+=b.pu}}
  return {zesp:n,bud:n*V.b.length,lok:n*lok,pu:n*pu,zab:n*zab,unk,lok1:lok,pu1:pu,zab1:zab};
}
let planSig='';
function planSchedule(){   // przelicz tylko wtedy, gdy zmieniła się geometria terenu albo parametry
  const sig=JSON.stringify(S.polys.map(p=>[p.kind,p.v]))+'|'+PLAN.gap+'|'+PLAN.setback+'|'+PLAN.auto+'|'+(PLAN.auto?0:PLAN.angle);
  if(sig===planSig)return;planSig=sig;clearTimeout(planTimer);planTimer=setTimeout(planNow,180)}
function planNow(){
  if(!KIT)return;const seq=++planSeq,area=planArea();
  if(!area){RES={};planUI();drawPlan();return}
  const order=[PLAN.variant].concat(Object.keys(KIT.variants).filter(k=>k!==PLAN.variant));let i=0;
  $('pl-state').textContent='Liczę układ…';
  const step=()=>{if(seq!==planSeq)return;const vk=order[i++];RES[vk]=planFor(vk,area);planUI();if(vk===PLAN.variant){drawPlan();if(is3)plan3()}
    if(i<order.length)setTimeout(step,0);else $('pl-state').textContent=''};
  setTimeout(step,0);
}
/* Rysunek 2D: obrysy budynków każdego zespołu. */
function drawPlan(){
  gB.textContent='';const r=RES[PLAN.variant];if(!r||!KIT)return;
  const V=KIT.variants[PLAN.variant],mpp=S.mpp,rc=svg.getBoundingClientRect(),k=rc.width?view.w/rc.width:1;
  r.items.forEach((it,n)=>{const co=Math.cos(it.phi),si=Math.sin(it.phi);
    r.raw.forEach((o,b)=>{
      el('polygon',{points:o.map(q=>(it.x+(q[0]*co-q[1]*si)/mpp)+','+(it.y-(q[0]*si+q[1]*co)/mpp)).join(' '),fill:BCOL[V.b[b]],'fill-opacity':.88,stroke:'#ffffff','stroke-width':1.2*k,'pointer-events':'none'},gB)});
    const t=el('text',{x:it.x,y:it.y,'text-anchor':'middle','dominant-baseline':'central','font-size':16*k,'font-weight':700,'font-family':'system-ui,sans-serif',fill:'#ffffff',stroke:'#0b2a36','stroke-width':3.5*k,'paint-order':'stroke','pointer-events':'none'},gB);t.textContent='Z'+(n+1)});
}
/* Panel wyników. */
function planUI(){
  if(!KIT)return;
  document.querySelectorAll('#pl-var button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.v===PLAN.variant));
  $('pl-gap').value=PLAN.gap;$('pl-gapv').textContent=fmt(PLAN.gap,0)+' m';$('pl-set').value=PLAN.setback;$('pl-setv').textContent=fmt(PLAN.setback,0)+' m';
  $('pl-auto').checked=PLAN.auto;$('pl-ang').disabled=PLAN.auto;
  const r=RES[PLAN.variant],b=balance(),avail=b.hasSite&&!b.err?(b.hasBuild?b.B:b.A-b.E):0;
  if(r){if(PLAN.auto){$('pl-ang').value=((r.angle%360)+360)%360}$('pl-angv').textContent=fmt(((r.angle%360)+360)%360,0)+'°'}
  const row=(l,x,key)=>'<tr'+(key?' class="key"':'')+'><td>'+l+'</td><td class="n">'+x+'</td></tr>';
  let h='';
  if(!S.polys[0].v.length||S.polys[0].v.length<3)h=row('Narysuj granicę terenu','–');
  else if(r){const s=planStats(PLAN.variant,r.n),V=KIT.variants[PLAN.variant];
    h=row('Zespołów budynków',fmt(s.zesp,0),1)+row('Budynków',fmt(s.bud,0),1)+row('Lokali'+(s.unk?' (bez bud. C)':''),fmt(s.lok,0),1)
      +row('Powierzchnia użytkowa lokali',fmt(s.pu,0)+' m²')+row('Powierzchnia zabudowy',fmt(s.zab,0)+' m²')
      +row('Udział zabudowy w terenie',avail?fmt(100*s.zab/avail,1)+' %':'–')+row('Lokali na hektar',avail?fmt(s.lok/(avail/1e4),0):'–')
      +row('Jeden zespół: wymiary',fmt(V.size[0],0)+' × '+fmt(V.size[1],0)+' m')+row('Jeden zespół: lokale / PU',fmt(s.lok1,0)+' / '+fmt(s.pu1,0)+' m²');
    $('totz').textContent=fmt(s.zesp,0)+' zesp. · '+fmt(s.bud,0)+' bud. · '+fmt(s.lok,0)+' lok.';
  }else $('totz').textContent='–';
  $('pl-res').innerHTML=h;
  let c='';for(const vk in KIT.variants){const rr=RES[vk],s=rr?planStats(vk,rr.n):null;
    c+='<tr'+(vk===PLAN.variant?' class="key"':'')+'><td>'+KIT.variants[vk].name+'</td><td class="n">'+(s?fmt(s.zesp,0):'…')+'</td><td class="n">'+(s?fmt(s.bud,0):'…')+'</td><td class="n">'+(s?fmt(s.lok,0)+(s.unk?'*':''):'…')+'</td><td class="n">'+(s?fmt(s.pu,0):'…')+'</td></tr>'}
  $('pl-cmp').innerHTML=c;
}
/* Podgląd 3D: prawdziwe bryły budynków postawione na rzeźbie terenu. */
const G3={};let plan3Seq=0;
async function geo3(k){
  if(G3[k])return G3[k];const b=KIT.buildings[k],gj=await (await fetch(b.file)).json();
  const pos=new Float32Array(gj.pos.length);for(let i=0;i<pos.length;i++)pos[i]=gj.pos[i]/100;
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(pos,3));g.setIndex(new THREE.BufferAttribute(new Uint32Array(gj.idx),1));
  const sr=v=>Math.max(0,v);      // kolory liniowe: renderer edytora sam koduje wyjście do sRGB
  const mats=b.groups.map((gr,i)=>{g.addGroup(gr.start,gr.count,i);const gl=/szklo/i.test(gr.mat);
    return new THREE.MeshLambertMaterial({color:new THREE.Color(sr(gr.color[0]),sr(gr.color[1]),sr(gr.color[2])),side:THREE.DoubleSide,flatShading:true,transparent:gl,opacity:gl?(gr.color[3]<1?.35:.8):1})});
  g.computeVertexNormals();
  let cx=0,cy=0;for(const q of b.outline){cx+=q[0];cy+=q[1]}
  return G3[k]={g,mats,c:[cx/b.outline.length,cy/b.outline.length]};
}
async function plan3(){
  if(!T||!KIT)return;const seq=++plan3Seq,r=RES[PLAN.variant];
  if(!T.bld){T.bld=new THREE.Group();T.sc.add(T.bld);T.sc.add(new THREE.HemisphereLight(0xffffff,0x8a8f94,1.0));const s=new THREE.DirectionalLight(0xffffff,.55);s.position.set(-300,500,200);T.sc.add(s)}
  const V=KIT.variants[PLAN.variant];
  if(r&&r.n){$('pl-state').textContent='Wczytuję bryły budynków…';try{await Promise.all(V.b.map(geo3))}catch(e){$('pl-state').textContent='Nie udało się wczytać brył budynków.';return}$('pl-state').textContent=''}
  if(seq!==plan3Seq)return;
  while(T.bld.children.length)T.bld.remove(T.bld.children[0]);
  if(!r||!r.n)return;
  const c=V.center,M=new THREE.Matrix4(),Rm=new THREE.Matrix4(),Tm=new THREE.Matrix4();
  for(const k of V.b){const G=G3[k],im=new THREE.InstancedMesh(G.g,G.mats,r.n);
    r.items.forEach((it,n)=>{const co=Math.cos(it.phi),si=Math.sin(it.phi),dx=G.c[0]-c[0],dy=G.c[1]-c[1];
      const bx=wx(it.x+(dx*co-dy*si)/S.mpp),bz=wx(it.y-(dx*si+dy*co)/S.mpp),gy=hAt(bx,bz)-KIT.buildings[k].z[0]-.2;
      M.makeTranslation(wx(it.x),gy,wx(it.y));Rm.makeRotationY(it.phi);Tm.makeTranslation(-c[0],0,c[1]);
      im.setMatrixAt(n,M.multiply(Rm).multiply(Tm))});
    im.instanceMatrix.needsUpdate=true;im.frustumCulled=false;T.bld.add(im)}
}
function planInit(){
  document.querySelectorAll('#pl-var button').forEach(b=>b.addEventListener('click',()=>{PLAN.variant=b.dataset.v;planPersist();planUI();drawPlan();if(is3)plan3();if(!RES[PLAN.variant])planNow()}));
  const ch=()=>{planPersist();planUI();planSchedule()};
  $('pl-gap').addEventListener('input',e=>{PLAN.gap=+e.target.value;ch()});
  $('pl-set').addEventListener('input',e=>{PLAN.setback=+e.target.value;ch()});
  $('pl-auto').addEventListener('change',e=>{PLAN.auto=e.target.checked;ch()});
  $('pl-ang').addEventListener('input',e=>{PLAN.angle=+e.target.value;$('pl-angv').textContent=fmt(PLAN.angle,0)+'°';ch()});
  fetch('kit.json').then(r=>r.json()).then(k=>{KIT=k;planSig='';planUI();planSchedule()}).catch(()=>{$('pl-state').textContent='Nie udało się wczytać danych budynków (kit.json).'});
}
