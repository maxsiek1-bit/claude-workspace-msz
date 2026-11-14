/* ===== Planer: automatyczne wypełnianie terenu budynkami z biblioteki typów =====
   Ten blok jest wklejany do wnętrza skryptu edytora (ma dostęp do S, render, el, inside, segs, wx, hAt, T, is3, balance ...).
   Sam generator to czysta funkcja GenCore.generate (gen_core.js), liczona w Web Workerze. */
const PKEY='planer-zabudowa-v2';
let KIT=null, PLAN={preset:'v3',types:null,sb:4,se:0,dist:8,goal:'lokale',maxCover:100,sel:0,gap:12}, GEN=null, ZESP=null, planTimer=0, planSeq=0, planSig='', worker=null;
try{const o=JSON.parse(localStorage.getItem(PKEY));if(o&&typeof o==='object')PLAN=Object.assign(PLAN,o)}catch(e){}
function planPersist(){try{localStorage.setItem(PKEY,JSON.stringify(PLAN))}catch(e){}}
const BCOL={A:'#3f9fc6',A2:'#3f9fc6',B:'#f0b441',C:'#8f6fd6',C3:'#b58ae6'}, SHORT={A:'A',A2:'A′',B:'B',C:'C',C3:'A′L'};
const GOALS={lokale:'liczba lokali',pu:'powierzchnia użytkowa',budynki:'liczba budynków',zabudowa:'powierzchnia zabudowy'};
const m2px=q=>[q[0]/S.mpp,-q[1]/S.mpp], px2m=q=>[q[0]*S.mpp,-q[1]*S.mpp];
function planTypes(){return Object.keys(KIT.buildings).filter(k=>PLAN.types[k]).map(k=>{const b=KIT.buildings[k];
  return {id:k,outline:b.outline,axis_deg:KIT.axis_deg,lokale:b.lokale,pu:b.pu,zab:b.pow_zabudowy,kond:b.kond}})}

/* --- Układ zespołami A+B+C w regularnej siatce (dotychczasowy tryb; służy jako wariant porównawczy) --- */
function zespoly(){
  const V=KIT.variants[PLAN.preset],ok=p=>p.v.length>=3,site=S.polys[0].v;if(site.length<3)return null;
  const ex=S.polys.filter(p=>p.kind==='excl'&&ok(p)).map(p=>p.v),bu=S.polys.filter(p=>p.kind==='build'&&ok(p)).map(p=>p.v),mpp=S.mpp;
  const edges=GenCore.edgesOf([site].concat(ex,bu)),c=V.center,ax=KIT.axis_deg*Math.PI/180;
  const allowed=(x,y)=>{if(!inside(x,y,site))return false;for(const e of ex)if(inside(x,y,e))return false;if(bu.length){for(const b of bu)if(inside(x,y,b))return true;return false}return true};
  const outs=V.b.map(k=>GenCore.offsetPoly(KIT.buildings[k].outline,PLAN.sb).map(q=>[q[0]-c[0],q[1]-c[1]]));
  let x0=1e9,y0=1e9,x1=-1e9,y1=-1e9;for(const q of site){x0=Math.min(x0,q[0]);y0=Math.min(y0,q[1]);x1=Math.max(x1,q[0]);y1=Math.max(y1,q[1])}
  const w=V.size[0]+PLAN.gap,h=V.size[1]+PLAN.gap,cx=(x0+x1)/2,cy=(y0+y1)/2,rad=Math.hypot(x1-x0,y1-y0)*mpp/2+Math.hypot(w,h);
  const fits=(px,py,phi)=>{const co=Math.cos(phi),si=Math.sin(phi);
    for(const o of outs){const n=o.length,pts=new Array(n);
      for(let i=0;i<n;i++){const x=px+(o[i][0]*co-o[i][1]*si)/mpp,y=py-(o[i][0]*si+o[i][1]*co)/mpp;if(!allowed(x,y))return false;pts[i]=[x,y]}
      if(GenCore.crosses(pts,edges))return false;for(const e of ex)if(inside(e[0][0],e[0][1],pts))return false}
    return true};
  let best={n:0,phi:0,pos:[]};
  for(let deg=0;deg<360;deg+=6){const al=deg*Math.PI/180,phi=al-ax,ux=Math.cos(al),uy=Math.sin(al),ni=Math.ceil(rad/w),nj=Math.ceil(rad/h);
    for(let a=0;a<4;a++)for(let b=0;b<4;b++){const pos=[];
      for(let i=-ni;i<=ni;i++)for(let j=-nj;j<=nj;j++){const mx=(i+a/4)*w*ux-(j+b/4)*h*uy,my=(i+a/4)*w*uy+(j+b/4)*h*ux,px=cx+mx/mpp,py=cy-my/mpp;
        if(px<x0-40||px>x1+40||py<y0-40||py>y1+40)continue;if(fits(px,py,phi))pos.push([px,py])}
      if(pos.length>best.n)best={n:pos.length,phi,pos}}}
  // zamiana na listę budynków w tym samym formacie co generator
  const items=[];
  best.pos.forEach((p,zi)=>{const co=Math.cos(best.phi),si=Math.sin(best.phi);
    V.b.forEach(k=>{const o=KIT.buildings[k].outline;let bx=0,by=0;for(const q of o){bx+=q[0];by+=q[1]}bx/=o.length;by/=o.length;
      const dx=bx-c[0],dy=by-c[1],P=px2m(p),X=P[0]+dx*co-dy*si,Y=P[1]+dx*si+dy*co;
      items.push({id:k,x:X,y:Y,rot:best.phi+ax,z:zi+1,pts:o.map(q=>{const ex_=q[0]-c[0],ey=q[1]-c[1];return [P[0]+ex_*co-ey*si,P[1]+ex_*si+ey*co]})})})});
  return {name:'Zespoły A+B+C w siatce ('+best.n+' zesp.)',items,zesp:best.n};
}
function statsOf(items,terrain){
  const s={n:items.length,lokale:0,pu:0,zab:0,kub:0,byType:{},unk:0};
  for(const it of items){const b=KIT.buildings[it.id];s.byType[it.id]=(s.byType[it.id]||0)+1;s.zab+=b.pow_zabudowy;s.kub+=b.pow_zabudowy*b.kond;if(b.lokale==null)s.unk++;else{s.lokale+=b.lokale;s.pu+=b.pu}}
  s.pokrycie=terrain?s.zab/terrain:0;s.intens=terrain?s.kub/terrain:0;s.lok_ha=terrain?s.lokale/(terrain/1e4):0;return s;
}
function goalVal(s){return PLAN.goal==='pu'?s.pu:PLAN.goal==='budynki'?s.n:PLAN.goal==='zabudowa'?s.zab:s.lokale}
function variantsList(){     // 5 najlepszych z generatora + układ zespołami
  const L=[],seen={};
  if(GEN)for(const v of GEN.variants){            // pokazuj warianty różniące się wynikiem (te same liczby budynków każdego typu pomijam)
    const sig=JSON.stringify(v.stats.byType);if(seen[sig])continue;seen[sig]=1;
    L.push({name:(L.length?'Wariant '+(L.length+1):'Najlepszy')+': '+v.name,items:v.items,gen:true});if(L.length>=5)break}
  if(ZESP)L.push({name:ZESP.name,items:ZESP.items,gen:false});return L;
}
function curVariant(){const L=variantsList();return L[Math.min(PLAN.sel,L.length-1)]||null}

/* --- Przeliczanie: tylko gdy zmieni się teren albo parametry; generator w Web Workerze, najpierw szybki wynik, potem pełny --- */
function planSchedule(){
  if(!KIT)return;
  const sig=JSON.stringify(S.polys.map(p=>[p.kind,p.v]))+'|'+JSON.stringify([PLAN.preset,PLAN.types,PLAN.sb,PLAN.se,PLAN.dist,PLAN.goal,PLAN.maxCover]);
  if(sig===planSig)return;planSig=sig;clearTimeout(planTimer);planTimer=setTimeout(planNow,160)}
function mkWorker(){
  try{const src=document.getElementById('gen-core').textContent+'\nonmessage=function(e){var r=GenCore.generate(e.data.inp);postMessage({seq:e.data.seq,full:e.data.full,r:r})};';
    return new Worker(URL.createObjectURL(new Blob([src],{type:'text/javascript'})))}catch(e){return null}}
function planNow(){
  const seq=++planSeq,ok=p=>p.v.length>=3,site=S.polys[0].v;
  if(site.length<3){GEN=null;ZESP=null;planUI();drawPlan();return}
  const inp={site:site.map(px2m),excl:S.polys.filter(p=>p.kind==='excl'&&ok(p)).map(p=>p.v.map(px2m)),build:S.polys.filter(p=>p.kind==='build'&&ok(p)).map(p=>p.v.map(px2m)),
    types:planTypes(),params:{sb:PLAN.sb,se:PLAN.se,dist:PLAN.dist,step:4,goal:PLAN.goal,maxCover:PLAN.maxCover/100}};
  const done=(r,full)=>{if(seq!==planSeq)return;GEN=r;if(full){$('pl-state').textContent='Policzono '+r.variants.length+' wariantów w '+fmt(r.ms/1000,1)+' s.'}planUI();drawPlan();if(is3)plan3();
    if(document.activeElement!==$('json'))$('json').value=JSON.stringify(exportData(),null,1)};
  $('pl-state').textContent='Liczę układ…';
  if(!inp.types.length){GEN={variants:[],area_m2:0,terrain_m2:0};$('pl-state').textContent='Włącz co najmniej jeden typ budynku.';planUI();drawPlan();if(is3)plan3();return}
  setTimeout(()=>{if(seq===planSeq){ZESP=zespoly();planUI()}},0);
  if(worker)worker.terminate();worker=mkWorker();
  const quick=Object.assign({},inp,{params:Object.assign({},inp.params,{maxVariants:2})});
  if(worker){worker.onmessage=e=>{if(e.data.seq===seq)done(e.data.r,e.data.full)};worker.postMessage({seq,inp:quick,full:false});worker.postMessage({seq,inp,full:true})}
  else setTimeout(()=>{done(GenCore.generate(quick),false);setTimeout(()=>done(GenCore.generate(inp),true),0)},0);
}

/* --- Rysunek 2D --- */
function drawPlan(){
  gB.textContent='';const v=curVariant();if(!v||!KIT)return;
  const rc=svg.getBoundingClientRect(),k=rc.width?view.w/rc.width:1,cnt={};
  v.items.forEach(it=>{
    el('polygon',{points:it.pts.map(q=>m2px(q).join(',')).join(' '),fill:BCOL[it.id],'fill-opacity':.9,stroke:'#ffffff','stroke-width':1.2*k,'pointer-events':'none'},gB);
    cnt[it.id]=(cnt[it.id]||0)+1;const p=m2px([it.x,it.y]);
    const t=el('text',{x:p[0],y:p[1],'text-anchor':'middle','dominant-baseline':'central','font-size':11*k,'font-weight':700,'font-family':'system-ui,sans-serif',fill:'#ffffff',stroke:'#0b2a36','stroke-width':3*k,'paint-order':'stroke','pointer-events':'none'},gB);
    t.textContent=SHORT[it.id]+cnt[it.id]});
}

/* --- Panel --- */
function planUI(){
  if(!KIT)return;
  document.querySelectorAll('#pl-var button').forEach(b=>b.setAttribute('aria-pressed',b.dataset.v===PLAN.preset));
  for(const [id,key,unit] of [['pl-sb','sb',' m'],['pl-se','se',' m'],['pl-dist','dist',' m'],['pl-cov','maxCover',' %']]){$(id).value=PLAN[key];$(id+'v').textContent=fmt(PLAN[key],0)+unit}
  $('pl-goal').value=PLAN.goal;
  $('pl-types').innerHTML=Object.keys(KIT.buildings).map(k=>{const b=KIT.buildings[k];
    return '<tr><td><label class="chk"><input type="checkbox" data-type="'+k+'"'+(PLAN.types[k]?' checked':'')+'> <i class="sw" style="background:'+BCOL[k]+'"></i> '+b.name+'</label></td><td class="n">'+b.kond+'</td><td class="n">'+(b.lokale==null?'b.d.':b.lokale)+'</td><td class="n">'+(b.pu==null?'b.d.':fmt(b.pu,0))+'</td><td class="n">'+fmt(b.pow_zabudowy,0)+'</td></tr>'}).join('');
  const L=variantsList(),sel=Math.min(PLAN.sel,Math.max(0,L.length-1)),terrain=GEN?GEN.terrain_m2:0;
  $('pl-vars').innerHTML=L.map((v,i)=>{const s=statsOf(v.items,terrain);
    return '<button class="var" data-var="'+i+'" aria-pressed="'+(i===sel)+'"><span>'+v.name+'</span><b>'+fmt(goalVal(s),0)+'</b></button>'}).join('')||'<p class="note">Narysuj granicę terenu, aby zobaczyć warianty.</p>';
  const v=L[sel],row=(l,x,key,bad)=>'<tr'+(key?' class="key"':'')+'><td>'+l+'</td><td class="n"'+(bad?' style="color:var(--warn)"':'')+'>'+x+'</td></tr>';
  if(v&&GEN){const s=statsOf(v.items,terrain),by=Object.keys(s.byType).map(k=>s.byType[k]+' × '+KIT.buildings[k].name).join(', ');
    $('pl-res').innerHTML=row('Obszar do zabudowy (po odsunięciach)',fmt(GEN.area_m2,0)+' m²')+row('Budynków',fmt(s.n,0),1)+row('w tym',by||'–')
      +row('Lokali'+(s.unk?' (bez bud. C)':''),fmt(s.lokale,0),1)+row('Powierzchnia użytkowa lokali',fmt(s.pu,0)+' m²',1)
      +row('Powierzchnia zabudowy',fmt(s.zab,0)+' m²')+row('Udział zabudowy w terenie',fmt(100*s.pokrycie,1)+' %',0,s.pokrycie>PLAN.maxCover/100+1e-6)
      +row('Intensywność zabudowy',fmt(s.intens,2))+row('Teren niezabudowany (bez dróg)',fmt(100*(1-s.pokrycie),1)+' %')+row('Lokali na hektar',fmt(s.lok_ha,0));
    $('totz').textContent=fmt(s.n,0)+' bud. · '+fmt(s.lokale,0)+' lok.';
    const g=GEN.variants[0],gs=g?statsOf(g.items,terrain):null,zs=ZESP?statsOf(ZESP.items,terrain):null,cmp=(l,s2,k)=>'<tr'+(k?' class="key"':'')+'><td>'+l+'</td><td class="n">'+(s2?fmt(s2.n,0):'…')+'</td><td class="n">'+(s2?fmt(s2.lokale,0)+(s2.unk?'*':''):'…')+'</td><td class="n">'+(s2?fmt(s2.pu,0):'…')+'</td><td class="n">'+(s2?fmt(100*s2.pokrycie,0)+' %':'…')+'</td></tr>';
    $('pl-cmp').innerHTML=cmp('Generator (najlepszy)',gs,1)+cmp('Zespoły A+B+C w siatce',zs);
  }else{$('pl-res').innerHTML=row('Narysuj granicę terenu','–');$('pl-cmp').innerHTML='';$('totz').textContent='–'}
}

/* --- Podgląd 3D: prawdziwe bryły na rzeźbie terenu --- */
const G3={};let plan3Seq=0;
async function geo3(k){
  if(G3[k])return G3[k];const b=KIT.buildings[k],gj=await (await fetch(b.file)).json();
  const pos=new Float32Array(gj.pos.length);for(let i=0;i<pos.length;i++)pos[i]=gj.pos[i]/100;
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(pos,3));g.setIndex(new THREE.BufferAttribute(new Uint32Array(gj.idx),1));
  const mats=b.groups.map((gr,i)=>{g.addGroup(gr.start,gr.count,i);const gl=/szklo/i.test(gr.mat);
    return new THREE.MeshLambertMaterial({color:new THREE.Color(gr.color[0],gr.color[1],gr.color[2]),side:THREE.DoubleSide,flatShading:true,transparent:gl,opacity:gl?(gr.color[3]<1?.35:.8):1})});
  g.computeVertexNormals();
  let cx=0,cy=0;for(const q of b.outline){cx+=q[0];cy+=q[1]}
  return G3[k]={g,mats,c:[cx/b.outline.length,cy/b.outline.length]};
}
async function plan3(){
  if(!T||!KIT)return;const seq=++plan3Seq,v=curVariant();
  if(!T.bld){T.bld=new THREE.Group();T.sc.add(T.bld);T.sc.add(new THREE.HemisphereLight(0xffffff,0x8a8f94,1.0));const s=new THREE.DirectionalLight(0xffffff,.55);s.position.set(-300,500,200);T.sc.add(s)}
  const ids=v?Array.from(new Set(v.items.map(it=>it.id))):[];
  if(ids.length){try{await Promise.all(ids.map(geo3))}catch(e){$('pl-state').textContent='Nie udało się wczytać brył budynków.';return}}
  if(seq!==plan3Seq)return;
  while(T.bld.children.length)T.bld.remove(T.bld.children[0]);
  const ax=KIT.axis_deg*Math.PI/180,M=new THREE.Matrix4(),Rm=new THREE.Matrix4(),Tm=new THREE.Matrix4();
  for(const k of ids){const G=G3[k],list=v.items.filter(it=>it.id===k),im=new THREE.InstancedMesh(G.g,G.mats,list.length);
    list.forEach((it,n)=>{const p=m2px([it.x,it.y]),bx=wx(p[0]),bz=wx(p[1]),gy=hAt(bx,bz)-KIT.buildings[k].z[0]-.2;
      M.makeTranslation(bx,gy,bz);Rm.makeRotationY(it.rot-ax);Tm.makeTranslation(-G.c[0],0,G.c[1]);im.setMatrixAt(n,M.multiply(Rm).multiply(Tm))});
    im.instanceMatrix.needsUpdate=true;im.frustumCulled=false;T.bld.add(im)}
}
/* --- Eksport planu --- */
function planExport(){
  const v=curVariant();if(!v||!GEN)return null;const s=statsOf(v.items,GEN.terrain_m2),r2=x=>Math.round(x*100)/100;
  return {wariant:v.name,cel:PLAN.goal,parametry:{odsuniecie_od_granicy_m:PLAN.sb,odsuniecie_od_stref_wylaczonych_m:PLAN.se,odleglosc_miedzy_budynkami_m:PLAN.dist,maks_udzial_zabudowy_proc:PLAN.maxCover},
    statystyki:{budynki:s.n,wg_typow:s.byType,lokale:s.lokale,pu_m2:r2(s.pu),pow_zabudowy_m2:r2(s.zab),udzial_zabudowy:r2(s.pokrycie),intensywnosc:r2(s.intens),lokale_na_ha:r2(s.lok_ha),obszar_do_zabudowy_m2:r2(GEN.area_m2)},
    budynki:v.items.map((it,i)=>{const p=m2px([it.x,it.y]);return {nr:i+1,typ:it.id,nazwa:KIT.buildings[it.id].name,obrot_st:r2(it.rot*180/Math.PI),srodek_puwg1992:[r2(GEO.e0+p[0]*MPP),r2(GEO.n1-p[1]*MPP)],
      obrys_puwg1992:it.pts.map(q=>{const a=m2px(q);return [r2(GEO.e0+a[0]*MPP),r2(GEO.n1-a[1]*MPP)]})}})};
}
function planCSV(){
  const v=curVariant();if(!v||!GEN)return '';const s=statsOf(v.items,GEN.terrain_m2),n=x=>String(Math.round(x*100)/100).replace('.',',');
  const rows=[['Wariant',v.name],['Cel',GOALS[PLAN.goal]],['Obszar do zabudowy [m2]',n(GEN.area_m2)],['Budynki',s.n]];
  for(const k in s.byType)rows.push(['Budynki: '+KIT.buildings[k].name,s.byType[k]]);
  rows.push(['Lokale',s.lokale],['Powierzchnia uzytkowa [m2]',n(s.pu)],['Powierzchnia zabudowy [m2]',n(s.zab)],['Udzial zabudowy [%]',n(100*s.pokrycie)],['Intensywnosc zabudowy',n(s.intens)],['Lokale na hektar',n(s.lok_ha)]);
  return rows.map(r=>r.join(';')).join('\n');
}
function planInit(){
  const PRESET={base:['A','B','C'],v2:['A2','B','C'],v3:['A2','B','C3']};
  const ch=()=>{PLAN.sel=0;planPersist();planUI();planSchedule()};
  document.querySelectorAll('#pl-var button').forEach(b=>b.addEventListener('click',()=>{PLAN.preset=b.dataset.v;PLAN.types={};PRESET[PLAN.preset].forEach(k=>PLAN.types[k]=true);ch()}));
  for(const [id,key] of [['pl-sb','sb'],['pl-se','se'],['pl-dist','dist'],['pl-cov','maxCover']])$(id).addEventListener('input',e=>{PLAN[key]=+e.target.value;ch()});
  $('pl-goal').addEventListener('change',e=>{PLAN.goal=e.target.value;ch()});
  $('pl-types').addEventListener('change',e=>{const k=e.target.dataset.type;if(k){PLAN.types[k]=e.target.checked;ch()}});
  $('pl-vars').addEventListener('click',e=>{const b=e.target.closest('[data-var]');if(!b)return;PLAN.sel=+b.dataset.var;planPersist();planUI();drawPlan();if(is3)plan3();
    if(document.activeElement!==$('json'))$('json').value=JSON.stringify(exportData(),null,1)});
  $('pl-csv').addEventListener('click',()=>{const t=planCSV();if(!t)return;(navigator.clipboard?navigator.clipboard.writeText(t):Promise.reject()).then(()=>say('Skopiowano statystyki w formacie CSV.'),()=>{$('json').value=t;$('det').open=true;say('Nie udało się skopiować. Statystyki CSV są w polu „Dane JSON”.')})});
  fetch('kit.json').then(r=>r.json()).then(k=>{KIT=k;if(!PLAN.types){PLAN.types={};PRESET[PLAN.preset].forEach(x=>PLAN.types[x]=true)}planSig='';planUI();planSchedule()})
    .catch(()=>{$('pl-state').textContent='Nie udało się wczytać danych budynków (kit.json).'});
}
