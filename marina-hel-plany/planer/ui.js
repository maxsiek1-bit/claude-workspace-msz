/* ===== Planer: automatyczne wypełnianie terenu budynkami z biblioteki typów =====
   Ten blok jest wklejany do wnętrza skryptu edytora (ma dostęp do S, render, el, inside, segs, wx, hAt, T, is3, balance ...).
   Sam generator to czysta funkcja GenCore.generate (gen_core.js), liczona w Web Workerze. */
const PKEY='planer-zabudowa-v3';
let KIT=null, PLAN={preset:'v3',types:null,sb:4,se:0,dist:8,goal:'lokale',maxCover:100,sel:0,gap:12,mode:'widok',view:'auto',roadW:8}, GEN=null, planTimer=0, planSeq=0, planSig='', worker=null;
try{const o=JSON.parse(localStorage.getItem(PKEY));if(o&&typeof o==='object')PLAN=Object.assign(PLAN,o)}catch(e){}
function planPersist(){try{localStorage.setItem(PKEY,JSON.stringify(PLAN))}catch(e){}}
const BCOL={A:'#3f9fc6',A2:'#3f9fc6',B:'#f0b441',C:'#8f6fd6',C3:'#b58ae6'}, SHORT={A:'A',A2:'A′',B:'B',C:'C',C3:'A′L'};
const GOALS={lokale:'liczba lokali',pu:'powierzchnia użytkowa',budynki:'liczba budynków',zabudowa:'powierzchnia zabudowy'};
const COMPASS={E:0,NE:45,N:90,NW:135,W:180,SW:225,S:270,SE:315}, CNAME=['wschód','północny wschód','północ','północny zachód','zachód','południowy zachód','południe','południowy wschód'];
const V3={op:1,fl:{0:true,1:true,2:true,3:true,4:true,5:true}};
const m2px=q=>[q[0]/S.mpp,-q[1]/S.mpp], px2m=q=>[q[0]*S.mpp,-q[1]*S.mpp];
const rotP=(p,a)=>{const c=Math.cos(a),s=Math.sin(a);return p.map(q=>[q[0]*c-q[1]*s,q[0]*s+q[1]*c])};
const cen=o=>{let x=0,y=0;for(const q of o){x+=q[0];y+=q[1]}return [x/o.length,y/o.length]};
function planTypes(){return Object.keys(KIT.buildings).filter(k=>PLAN.types[k]).map(k=>{const b=KIT.buildings[k];
  return {id:k,outline:b.outline,axis_deg:KIT.axis_deg,lokale:b.lokale,pu:b.pu,zab:b.pow_zabudowy,kond:b.kond}})}
const roads=()=>S.polys.filter(p=>p.kind==='road'&&p.v.length>=2);

/* Kierunek widoku (radiany, x na wschód, y na północ): automatycznie = od drogi w stronę terenu, prostopadle do drogi. */
function viewAngle(){
  if(PLAN.view!=='auto'&&COMPASS[PLAN.view]!=null)return COMPASS[PLAN.view]*Math.PI/180;
  const r=roads()[0],site=S.polys[0].v;
  if(!r||site.length<3)return Math.PI;                      // bez drogi: zachód
  const a=px2m(r.v[0]),b=px2m(r.v[r.v.length-1]),c=cen(site.map(px2m)),m=cen(r.v.map(px2m));
  let nx=-(b[1]-a[1]),ny=b[0]-a[0];if(nx*(c[0]-m[0])+ny*(c[1]-m[1])<0){nx=-nx;ny=-ny}
  return Math.atan2(ny,nx);
}
const viewName=a=>CNAME[((Math.round(a*180/Math.PI/45)%8)+8)%8];

/* Zespół A+B+C jako typ złożony: części w układzie lokalnym (długa oś budynków wzdłuż +x, dziedziniec otwarty w stronę -x). */
function compound(pk){
  const V=KIT.variants[pk],c=V.center,ax=KIT.axis_deg*Math.PI/180;let zab=0;
  const parts=V.b.map(k=>{zab+=KIT.buildings[k].pow_zabudowy;return rotP(KIT.buildings[k].outline.map(q=>[q[0]-c[0],q[1]-c[1]]),-ax)});
  return {id:'Z:'+pk,parts,members:V.b,zab,lokale:1,pu:1,kond:6};
}
/* Zamiana zespołów na pojedyncze budynki (ten sam format co budynki z generatora). */
function expand(items){
  const out=[];let z=0;
  for(const it of items){
    if(String(it.id).indexOf('Z:')!==0){out.push({id:it.id,x:it.x,y:it.y,rot:it.rot,pts:it.pts});continue}
    const V=KIT.variants[it.id.slice(2)],c=V.center,ax=KIT.axis_deg*Math.PI/180;z++;
    V.b.forEach((k,i)=>{const cb=cen(KIT.buildings[k].outline),l=rotP([[cb[0]-c[0],cb[1]-c[1]]],it.rot-ax)[0];
      out.push({id:k,x:it.x+l[0],y:it.y+l[1],rot:it.rot,pts:it.parts[i],z})});
  }
  return out;
}
/* Statystyki z uwzględnieniem włączonych pięter. */
function typeNow(k){
  const b=KIT.buildings[k];let lok=0,pu=0,kond=0;
  if(b.floors&&b.floors.length){for(const f of b.floors)if(V3.fl[f.fl]){lok+=f.lokale;pu+=f.pu;kond++}return {lok,pu,kond,unk:false}}
  for(const s of b.slabs)if(typeof s.key==='number'&&V3.fl[s.key])kond++;
  return {lok:0,pu:0,kond,unk:true};
}
function statsOf(items,terrain){
  const s={n:items.length,lokale:0,pu:0,zab:0,kub:0,byType:{},unk:0},cache={};
  for(const it of items){const b=KIT.buildings[it.id],t=cache[it.id]||(cache[it.id]=typeNow(it.id));s.byType[it.id]=(s.byType[it.id]||0)+1;s.zab+=b.pow_zabudowy;s.kub+=b.pow_zabudowy*t.kond;if(t.unk)s.unk++;s.lokale+=t.lok;s.pu+=t.pu}
  s.pokrycie=terrain?s.zab/terrain:0;s.intens=terrain?s.kub/terrain:0;s.lok_ha=terrain?s.lokale/(terrain/1e4):0;return s;
}
function goalVal(s){return PLAN.goal==='pu'?s.pu:PLAN.goal==='budynki'?s.n:PLAN.goal==='zabudowa'?s.zab:s.lokale}
function variantsList(){
  const L=[],seen={};
  if(GEN)for(const v of GEN.variants){const sig=v.name.split(',')[0]+JSON.stringify(statsOf(v.items,1).byType);if(seen[sig]||!v.items.length)continue;seen[sig]=1;L.push({name:v.name,items:v.items})}
  L.sort((a,b)=>goalVal(statsOf(b.items,1))-goalVal(statsOf(a.items,1)));
  return L.slice(0,6);
}
function curVariant(){const L=variantsList();return L[Math.min(PLAN.sel,L.length-1)]||null}

/* --- Przeliczanie w Web Workerze --- */
function planSchedule(){
  if(!KIT)return;
  const sig=JSON.stringify(S.polys.map(p=>[p.kind,p.v]))+'|'+JSON.stringify([PLAN.preset,PLAN.types,PLAN.sb,PLAN.se,PLAN.dist,PLAN.goal,PLAN.maxCover,PLAN.mode,PLAN.view,PLAN.roadW]);
  if(sig===planSig)return;planSig=sig;clearTimeout(planTimer);planTimer=setTimeout(planNow,160)}
function mkWorker(){
  try{const src=document.getElementById('gen-core').textContent+'\nonmessage=function(e){var t0=Date.now(),out={variants:[],area_m2:0,terrain_m2:0};e.data.inps.forEach(function(inp){var r=GenCore.generate(inp);out.area_m2=r.area_m2;out.terrain_m2=r.terrain_m2;out.variants=out.variants.concat(r.variants)});out.ms=Date.now()-t0;postMessage({seq:e.data.seq,full:e.data.full,r:out})};';
    return new Worker(URL.createObjectURL(new Blob([src],{type:'text/javascript'})))}catch(e){return null}}
function planNow(){
  const seq=++planSeq,ok=p=>p.v.length>=3,site=S.polys[0].v;PLAN.sel=0;
  if(site.length<3){GEN=null;planUI();drawPlan();if(is3)plan3();return}
  const base={site:site.map(px2m),excl:S.polys.filter(p=>p.kind==='excl'&&ok(p)).map(p=>p.v.map(px2m)),build:S.polys.filter(p=>p.kind==='build'&&ok(p)).map(p=>p.v.map(px2m)),
    roads:roads().map(r=>({pts:r.v.map(px2m),d:PLAN.roadW/2+2}))};
  const prm={sb:PLAN.sb,se:PLAN.se,dist:PLAN.dist,step:4,goal:PLAN.goal,maxCover:PLAN.maxCover/100},types=planTypes();
  let quick=null,full=[];
  if(PLAN.mode==='widok'){                          // rzędy z widokiem: zespoły U otwarte na widok oraz pojedyncze typy długą elewacją do widoku
    const th=viewAngle(),vp=Object.assign({},prm,{step:2,scanAngle:th-Math.PI/2,viewAngle:th});
    for(const pk in KIT.variants){const t=compound(pk);t.fixedRot=th-Math.PI;full.push(Object.assign({},base,{types:[t],params:Object.assign({},vp,{name:'Zespoły U otwarte na widok – '+KIT.variants[pk].name.toLowerCase()})}))}
    for(const t of types)for(const [sg,nm] of [[1,''],[-1,' (odwrócony)']])
      full.push(Object.assign({},base,{types:[Object.assign({},t,{fixedRot:th+sg*Math.PI/2})],params:Object.assign({},vp,{name:'Rząd: '+KIT.buildings[t.id].name+nm})}));
  }else{
    if(!types.length){GEN={variants:[],area_m2:0,terrain_m2:0};$('pl-state').textContent='Włącz co najmniej jeden typ budynku.';planUI();drawPlan();if(is3)plan3();return}
    quick=[Object.assign({},base,{types,params:Object.assign({},prm,{maxVariants:2})})];full=[Object.assign({},base,{types,params:prm})];
  }
  const done=(r,isFull)=>{if(seq!==planSeq)return;r.variants.forEach(v=>{v.items=expand(v.items)});GEN=r;
    if(isFull)$('pl-state').textContent='Policzono '+r.variants.length+' wariantów w '+fmt(r.ms/1000,1)+' s.';planUI();drawPlan();if(is3)plan3();
    if(document.activeElement!==$('json'))$('json').value=JSON.stringify(exportData(),null,1)};
  $('pl-state').textContent='Liczę układ…';
  if(worker)worker.terminate();worker=mkWorker();
  const run=(inps)=>{const out={variants:[],area_m2:0,terrain_m2:0},t0=Date.now();inps.forEach(i=>{const r=GenCore.generate(i);out.area_m2=r.area_m2;out.terrain_m2=r.terrain_m2;out.variants=out.variants.concat(r.variants)});out.ms=Date.now()-t0;return out};
  if(worker){worker.onmessage=e=>{if(e.data.seq===seq)done(e.data.r,e.data.full)};if(quick)worker.postMessage({seq,inps:quick,full:false});worker.postMessage({seq,inps:full,full:true})}
  else setTimeout(()=>{if(quick)done(run(quick),false);setTimeout(()=>done(run(full),true),0)},0);
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
  for(const [id,key,unit] of [['pl-sb','sb',' m'],['pl-se','se',' m'],['pl-dist','dist',' m'],['pl-road','roadW',' m']]){$(id).value=PLAN[key];$(id+'v').textContent=fmt(PLAN[key],0)+unit}
  if(document.activeElement!==$('pl-cov'))$('pl-cov').value=PLAN.maxCover;
  $('pl-goal').value=PLAN.goal;$('pl-mode').value=PLAN.mode;$('pl-view').value=PLAN.view;
  $('pl-view').closest('.line').hidden=PLAN.mode!=='widok';$('pl-var').hidden=PLAN.mode==='widok';
  $('pl-types').innerHTML=Object.keys(KIT.buildings).map(k=>{const b=KIT.buildings[k],t=typeNow(k);
    return '<tr><td><label class="chk"><input type="checkbox" data-type="'+k+'"'+(PLAN.types[k]?' checked':'')+'> <i class="sw" style="background:'+BCOL[k]+'"></i> '+b.name+'</label></td><td class="n">'+t.kond+'</td><td class="n">'+(t.unk?'b.d.':t.lok)+'</td><td class="n">'+(t.unk?'b.d.':fmt(t.pu,0))+'</td><td class="n">'+fmt(b.pow_zabudowy,0)+'</td></tr>'}).join('');
  const L=variantsList(),sel=Math.min(PLAN.sel,Math.max(0,L.length-1)),terrain=GEN?GEN.terrain_m2:0;
  $('pl-vars').innerHTML=L.map((v,i)=>{const s=statsOf(v.items,terrain);
    return '<button class="var" data-var="'+i+'" aria-pressed="'+(i===sel)+'"><span>'+v.name+'</span><b>'+fmt(goalVal(s),0)+'</b></button>'}).join('')||'<p class="note">Brak wariantów: narysuj granicę terenu albo zmniejsz odsunięcia.</p>';
  const v=L[sel],row=(l,x,key,bad)=>'<tr'+(key?' class="key"':'')+'><td>'+l+'</td><td class="n"'+(bad?' style="color:var(--warn)"':'')+'>'+x+'</td></tr>';
  const th=viewAngle(),info=[];
  if(PLAN.mode==='widok')info.push('widok na '+viewName(th)+(PLAN.view==='auto'?(roads().length?' (od drogi)':' (brak drogi – przyjęty zachód)'):''));
  const fo=[0,1,2,3,4,5].filter(f=>!V3.fl[f]);if(fo.length)info.push('bez: '+fo.map(f=>f?'piętra '+f:'parteru').join(', '));
  if(v&&GEN){const s=statsOf(v.items,terrain),by=Object.keys(s.byType).map(k=>s.byType[k]+' × '+KIT.buildings[k].name).join(', ');
    $('pl-res').innerHTML=row('Obszar do zabudowy (po odsunięciach)',fmt(GEN.area_m2,0)+' m²')+row('Budynków',fmt(s.n,0),1)+row('w tym',by||'–')
      +row('Lokali'+(s.unk?' (bez bud. C)':''),fmt(s.lokale,0),1)+row('Powierzchnia użytkowa lokali',fmt(s.pu,0)+' m²',1)
      +row('Powierzchnia zabudowy',fmt(s.zab,0)+' m²')+row('Udział zabudowy w terenie',fmt(100*s.pokrycie,1)+' %',0,s.pokrycie>PLAN.maxCover/100+1e-6)
      +row('Intensywność zabudowy',fmt(s.intens,2))+row('Teren niezabudowany (bez dróg)',fmt(100*(1-s.pokrycie),1)+' %')+row('Lokali na hektar',fmt(s.lok_ha,0));
    $('kpi-n').textContent=fmt(s.n,0);$('kpi-lok').textContent=fmt(s.lokale,0)+(s.unk?'*':'');$('kpi-pu').textContent=fmt(s.pu,0);$('kpi-cov').textContent=fmt(100*s.pokrycie,1)+' %';
    $('kpi-var').textContent=v.name+(info.length?' · '+info.join(' · '):'');
    $('pl-cmp').innerHTML=L.map((x,i)=>{const q=statsOf(x.items,terrain);return '<tr'+(i===sel?' class="key"':'')+'><td>'+x.name+'</td><td class="n">'+fmt(q.n,0)+'</td><td class="n">'+fmt(q.lokale,0)+(q.unk?'*':'')+'</td><td class="n">'+fmt(q.pu,0)+'</td><td class="n">'+fmt(100*q.pokrycie,0)+' %</td></tr>'}).join('');
  }else{$('pl-res').innerHTML=row('Brak układu','–');$('pl-cmp').innerHTML='';for(const k of ['kpi-n','kpi-lok','kpi-pu','kpi-cov'])$(k).textContent='–';$('kpi-var').textContent=info.join(' · ')}
}

/* --- Podgląd 3D: bryły pocięte na kondygnacje, plany pięter, prześwit --- */
const G3={},TEX3={};let plan3Seq=0,INST=[];
function ui3(){$('v3-fl').innerHTML=[0,1,2,3,4,5].map(f=>'<button data-fl="'+f+'" aria-pressed="'+!!V3.fl[f]+'" title="'+(f?'piętro '+f:'parter')+'">'+(f||'P')+'</button>').join('')}
function tex3(u){if(!TEX3[u]){const t=new THREE.TextureLoader().load(u);t.encoding=THREE.sRGBEncoding;t.anisotropy=T.R.capabilities.getMaxAnisotropy();TEX3[u]=t}return TEX3[u]}
async function geo3(k){
  if(G3[k])return G3[k];const b=KIT.buildings[k],sl=await (await fetch(b.slabs_file)).json();
  const mats=b.mats.map(m=>{const gl=/szklo/i.test(m.mat),x=new THREE.MeshLambertMaterial({color:new THREE.Color(m.color[0],m.color[1],m.color[2]),side:THREE.DoubleSide,flatShading:true});x.userData.base=gl?(m.color[3]<1?.35:.8):1;return x});
  const geos=sl.map(s=>{const pos=new Float32Array(s.pos.length);for(let i=0;i<pos.length;i++)pos[i]=s.pos[i]/100;
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(pos,3));g.setIndex(new THREE.BufferAttribute(new Uint32Array(s.idx),1));
    const used=[];s.groups.forEach((gr,i)=>{g.addGroup(gr.start,gr.count,i);used.push(mats[gr.m])});g.computeVertexNormals();return {g,mats:used}});
  return G3[k]={geos,mats,c:cen(b.outline)};
}
/* Prześwit, widoczność i położenie kondygnacji: wyłączone piętro znika z bryły, a wszystko nad nim opada. */
function apply3(){
  for(const k in G3)G3[k].mats.forEach(m=>{const v=m.userData.base*V3.op;m.opacity=v;m.transparent=v<.999;m.depthWrite=v>=.999;m.needsUpdate=true});
  const Tm=new THREE.Matrix4(),M=new THREE.Matrix4();
  for(const I of INST){const sl=KIT.buildings[I.k].slabs;let off=0;const offs=sl.map(s=>{const o=off,on=typeof s.key!=='number'||V3.fl[s.key];if(!on)off-=s.z1-s.z0;return {o,on}});
    I.slabs.forEach((im,i)=>{im.visible=offs[i].on&&V3.op>.005;Tm.makeTranslation(0,offs[i].o,0);I.base.forEach((b,n)=>im.setMatrixAt(n,M.copy(b).multiply(Tm)));im.instanceMatrix.needsUpdate=true});
    I.planes.forEach(p=>{const i=sl.findIndex(s=>s.key===p.fl);p.im.visible=i>=0&&offs[i].on&&V3.op<.999;Tm.makeTranslation(0,i>=0?offs[i].o:0,0);I.base.forEach((b,n)=>p.im.setMatrixAt(n,M.copy(b).multiply(Tm)));p.im.instanceMatrix.needsUpdate=true})}
}
async function plan3(){
  if(!T||!KIT)return;const seq=++plan3Seq,v=curVariant();
  if(!T.bld){T.bld=new THREE.Group();T.sc.add(T.bld);T.sc.add(new THREE.HemisphereLight(0xffffff,0x8a8f94,1.0));const s=new THREE.DirectionalLight(0xffffff,.55);s.position.set(-300,500,200);T.sc.add(s)}
  const ids=v?Array.from(new Set(v.items.map(it=>it.id))):[];
  if(ids.length){try{await Promise.all(ids.map(geo3))}catch(e){$('pl-state').textContent='Nie udało się wczytać brył budynków.';return}}
  if(seq!==plan3Seq)return;
  while(T.bld.children.length)T.bld.remove(T.bld.children[0]);INST=[];
  const ax=KIT.axis_deg*Math.PI/180,M=new THREE.Matrix4(),Rm=new THREE.Matrix4(),Tm=new THREE.Matrix4();
  for(const k of ids){const G=G3[k],list=v.items.filter(it=>it.id===k),base=[];
    list.forEach(it=>{const p=m2px([it.x,it.y]),bx=wx(p[0]),bz=wx(p[1]),gy=hAt(bx,bz)-KIT.buildings[k].z[0]-.2;
      M.makeTranslation(bx,gy,bz);Rm.makeRotationY(it.rot-ax);Tm.makeTranslation(-G.c[0],0,G.c[1]);base.push(M.multiply(Rm).multiply(Tm).clone())});
    const I={k,base,slabs:[],planes:[]};
    G.geos.forEach(ge=>{const im=new THREE.InstancedMesh(ge.g,ge.mats,list.length);im.frustumCulled=false;im.renderOrder=2;T.bld.add(im);I.slabs.push(im)});
    for(const f of KIT.buildings[k].floors||[]){const q=f.quad,y=f.z+.08,pg=new THREE.BufferGeometry();
      pg.setAttribute('position',new THREE.BufferAttribute(new Float32Array([q[0][0],y,-q[0][1],q[1][0],y,-q[1][1],q[2][0],y,-q[2][1],q[3][0],y,-q[3][1]]),3));
      pg.setAttribute('uv',new THREE.BufferAttribute(new Float32Array([0,1,1,1,1,0,0,0]),2));pg.setIndex([0,1,2,0,2,3]);
      const pm=new THREE.InstancedMesh(pg,new THREE.MeshBasicMaterial({map:tex3(f.tex),transparent:true,alphaTest:.5,side:THREE.DoubleSide}),list.length);
      pm.frustumCulled=false;pm.renderOrder=1;T.bld.add(pm);I.planes.push({im:pm,fl:f.fl})}
    INST.push(I)}
  apply3();
}
/* --- Eksport planu --- */
function planExport(){
  const v=curVariant();if(!v||!GEN)return null;const s=statsOf(v.items,GEN.terrain_m2),r2=x=>Math.round(x*100)/100;
  return {wariant:v.name,uklad:PLAN.mode,cel:PLAN.goal,kierunek_widoku_st:PLAN.mode==='widok'?r2(viewAngle()*180/Math.PI):null,wlaczone_pietra:[0,1,2,3,4,5].filter(f=>V3.fl[f]),
    parametry:{odsuniecie_od_granicy_m:PLAN.sb,odsuniecie_od_stref_wylaczonych_m:PLAN.se,odleglosc_miedzy_budynkami_m:PLAN.dist,maks_udzial_zabudowy_proc:PLAN.maxCover,szerokosc_drogi_m:PLAN.roadW},
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
  const ch=()=>{PLAN.sel=0;planPersist();planUI();planSchedule();if(!is3)render()};
  document.querySelectorAll('#pl-var button').forEach(b=>b.addEventListener('click',()=>{PLAN.preset=b.dataset.v;PLAN.types={};PRESET[PLAN.preset].forEach(k=>PLAN.types[k]=true);ch()}));
  for(const [id,key] of [['pl-sb','sb'],['pl-se','se'],['pl-dist','dist'],['pl-road','roadW']])$(id).addEventListener('input',e=>{PLAN[key]=+e.target.value;ch()});
  $('pl-cov').addEventListener('input',e=>{const v=+e.target.value;if(v>=1&&v<=100){PLAN.maxCover=v;ch()}});
  $('pl-cov').addEventListener('blur',e=>{e.target.value=PLAN.maxCover});
  $('pl-goal').addEventListener('change',e=>{PLAN.goal=e.target.value;ch()});
  $('pl-mode').addEventListener('change',e=>{PLAN.mode=e.target.value;ch()});
  $('pl-view').addEventListener('change',e=>{PLAN.view=e.target.value;ch()});
  $('pl-types').addEventListener('change',e=>{const k=e.target.dataset.type;if(k){PLAN.types[k]=e.target.checked;ch()}});
  const pick=()=>{planPersist();planUI();drawPlan();if(is3)plan3();if(document.activeElement!==$('json'))$('json').value=JSON.stringify(exportData(),null,1)};
  $('pl-vars').addEventListener('click',e=>{const b=e.target.closest('[data-var]');if(!b)return;PLAN.sel=+b.dataset.var;pick()});
  $('pl-csv').addEventListener('click',()=>{const t=planCSV();if(!t)return;(navigator.clipboard?navigator.clipboard.writeText(t):Promise.reject()).then(()=>say('Skopiowano statystyki w formacie CSV.'),()=>{$('json').value=t;$('det').open=true;say('Nie udało się skopiować. Statystyki CSV są w polu „Dane JSON”.')})});
  // górny pasek: prześwit budynków i piętra (użycie przełącza na podgląd 3D); piętra zmieniają też liczby
  const to3=()=>{if(!is3)setView('3d')};
  $('v3-op').addEventListener('input',e=>{V3.op=1-(+e.target.value);$('v3-opv').textContent=Math.round(+e.target.value*100)+'%';to3();apply3()});
  const flo=()=>{ui3();planUI();to3();apply3();if(document.activeElement!==$('json'))$('json').value=JSON.stringify(exportData(),null,1)};
  $('v3-fl').addEventListener('click',e=>{const b=e.target.closest('[data-fl]');if(!b)return;V3.fl[b.dataset.fl]=!V3.fl[b.dataset.fl];flo()});
  $('v3-all').addEventListener('click',()=>{for(let i=0;i<6;i++)V3.fl[i]=true;flo()});
  $('v3-none').addEventListener('click',()=>{for(let i=0;i<6;i++)V3.fl[i]=false;flo()});
  ui3();
  const ed=$('edit'),vm=()=>{svg.classList.toggle('viewing',!ed.open);if(!ed.open&&tool!=='pt'&&!is3)setTool('pt');else if(!is3)render()};ed.addEventListener('toggle',vm);vm();
  fetch('kit.json').then(r=>r.json()).then(k=>{KIT=k;if(!PLAN.types){PLAN.types={};PRESET[PLAN.preset].forEach(x=>PLAN.types[x]=true)}planSig='';planUI();planSchedule()})
    .catch(()=>{$('pl-state').textContent='Nie udało się wczytać danych budynków (kit.json).'});
}
