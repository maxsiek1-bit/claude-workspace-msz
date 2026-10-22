import json,glob,collections,re,datetime as dt
D=lambda s: dt.date.fromisoformat(str(s)[:10]) if s and str(s)[:4]>'1971' else None
def ph(p):
  d=re.sub(r'\D','',str(p or '')); return d[-9:] if len(d)>=9 else None
def em(e):
  e=str(e or '').strip().lower(); return e if '@' in e else None
def kv(o,k):
  m=re.search(r'^\s*'+k+r':\s*(.*)$',str(o or ''),re.M); return m.group(1).strip() if m else None

PORTALS={'Nieruchomości online','Nieruchomości on line','Rynekpierwotny.pl','Otodom.pl','Zgłoszenie z portalu Noweinwestycje.pl','Noweinwestycje.pl','Morizon','Gratka','TabelaOfert.pl','Domiporta.pl','Olx','Domy.pl'}
OFFLINE={'Banery','Wizyta','Targi','Autobus','Centrum handlowe'}
SRCNORM={'Nieruchomości on line':'Nieruchomości online','Zgłoszenie z portalu Noweinwestycje.pl':'Noweinwestycje.pl','internet':'Internet'}
def channel(src,plat):
  if src in('Facebook','Instagram'): return 'Meta Ads'
  if src=='Google': return 'Google Ads'
  if src in('Www','Landing','Internet','internet'): return 'Strona WWW'
  if src in PORTALS: return 'Portale'
  if src=='Z polecenia': return 'Polecenie'
  if src in OFFLINE: return 'Offline'
  if src in('Pośrednik',): return 'Pośrednik'
  if src=='Mailing': return 'Mailing'
  return 'Inne / brak'

# --- clients from agreements + meetings
T=json.load(open('trans.json')); M=json.load(open('meet.json'))
key2cid={}
cl=collections.defaultdict(lambda:{'meets':[],'meet':None,'res':None,'sale':None,'units':{},'created':None,'src':None,'inv':None})
def link(cid,p,e):
  for k in (ph(p),em(e)):
    if k: key2cid.setdefault(k,cid)
SALE={'Umowa deweloperska','Umowa przedwstępna','Akt notarialny'}
for t in T:
  cid=t['ID klienta']
  if not cid: continue
  link(cid,t['Telefon klienta'],t['E-mail klienta'])
  c=cl[cid]; d=D(t['Data podpisania umowy']) or D(t['Data utworzenia'])
  c['created']=D(t['Data utworzenia klienta']); c['src']=t['Źródło pochodzenia']; c['inv']=c['inv'] or t['Inwestycja']
  if not d: continue
  if t['Typ'] in SALE|{'Umowa rezerwacyjna'}:
    c['res']=min(filter(None,[c['res'],d]))
  if t['Typ'] in SALE and t['Status umowy']!='Anulowana':
    c['sale']=min(filter(None,[c['sale'],d]))
    u=t['ID lokalu głównego'] or t['Numer lokalu']
    c['units'][u]=max(c['units'].get(u,0),t['Cena całkowita brutto'] or 0)
for m in M:
  cid=m['Id Klienta']
  if not cid: continue
  link(cid,m['Telefon klienta'],m['E-mail klienta'])
  if m['Status spotkania']=='Odbyło się':
    c=cl[cid]; d=D(m['Data spotkania']); c['meet']=min(filter(None,[c['meet'],d])); c['meets'].append(d)
    c['created']=c['created'] or D(m['Utworzono klienta']); c['src']=c['src'] or m['Źródło pochodzenia']

# --- leads
L={}
for f in sorted(glob.glob('leads/*.json')):
  for l in json.load(open(f)): L[l['Id Lead']]=l
L=sorted(L.values(),key=lambda l:l['Utworzono'])
camp_inv=collections.defaultdict(collections.Counter)
rows=[]; first_lead_of={}
for l in L:
  src=l['Źródło pochodzenia'] or 'brak'
  plat=(kv(l['Opis'],'Platform') or '').lower()
  camp=kv(l['Opis'],'Campaign Name')
  if plat.startswith('campaign name'): plat='fb'
  if camp is not None and (camp=='' or camp.startswith('Typ:')): camp=None
  ch=channel(src,plat)
  if ch=='Meta Ads': place='Instagram' if plat=='ig' or src=='Instagram' else 'Facebook'
  elif ch=='Google Ads': place='Google'
  else: place=''
  cid=None
  for k in (ph(l['Telefon']),em(l['E-mail'])):
    if k and k in key2cid: cid=key2cid[k]; break
  inv=(l['Inwestycja'] or 'brak').split(',')[0]
  typ=kv(l['Opis'],'Typ')
  if typ:
    t=typ.lower().replace('_',' ')
    typ='Dom' if 'dom' in t or 'will' in t or 'bli' in t else 'Mieszkanie/apartament' if ('mieszk' in t or 'apart' in t) else 'Nie wie' if 'wiem' in t else None
  if camp: camp_inv[camp][inv]+=1
  r={'d':l['Utworzono'][:10],'src':SRCNORM.get(src,src),'ch':ch,'pl':place,'camp':camp,'inv':inv,'typ':typ,
     'conv':int(l['Status'] in('Skonwertowany','Powiązany')),'del':int(l['Status']=='Usunięto'),
     'q':int('Zakwalifikowany' in str(l['Klasyfikacja klienta'] or '')),'cid':cid}
  rows.append(r)
# first-touch: each client's sale/meeting attributed only to their earliest lead
seen=set(); matched_cids=set()
for r in rows:
  cid=r.pop('cid'); r['m']=r['r']=r['s']=0; r['ds']=None; r['v']=0; r['dk']=r['dm']=r['dr']=None; r['nm']=0; r['d2']=None
  if cid is None or cid in seen: continue
  c=cl.get(cid)
  if not c: continue
  seen.add(cid); ld=D(r['d'])
  if c['created'] and c['created']>=ld: r['dk']=(c['created']-ld).days
  if c['meet'] and c['meet']>=ld: r['dm']=(c['meet']-ld).days
  ms=sorted(x for x in c['meets'] if x>=ld); r['nm']=len(ms)
  if len(ms)>=2: r['d2']=(ms[1]-ms[0]).days
  if c['res'] and c['res']>=ld: r['dr']=(c['res']-ld).days
  if c['meet'] and c['meet']>=ld: r['m']=1
  if c['res'] and c['res']>=ld: r['r']=1
  if c['sale'] and c['sale']>=ld:
    r['s']=1; r['ds']=(c['sale']-ld).days; r['v']=round(sum(c['units'].values())); matched_cids.add(cid)
    r['m']=r['m'] or 0
  if r['s'] or r['r']: r['m']=1 if c['meet'] else r['m']
# campaign label
def clabel(c):
  if not c: return None
  inv=camp_inv[c].most_common(1)[0][0]
  return f'{c}' if not c.isdigit() else f'ID {c} · {inv}'
for r in rows: r['camp']=clabel(r['camp'])

# sales view (all signed clients, CRM source vs lead source)
lead_src={}
seen2=set()
for l,r in zip(L,rows): pass
sales=[]
attributed={}
# re-run attribution map cid->row for sales view
seen=set()
for l,r in zip(L,rows):
  cid=None
  for k in (ph(l['Telefon']),em(l['E-mail'])):
    if k and k in key2cid: cid=key2cid[k]; break
  if cid and cid not in attributed and cl.get(cid) and cl[cid]['sale'] and cl[cid]['sale']>=D(r['d']): attributed[cid]=r
for cid,c in cl.items():
  if not c['sale']: continue
  a=attributed.get(cid)
  crm=SRCNORM.get(c['src'],c['src']) or 'brak'
  sales.append({'d':c['sale'].isoformat(),'crm':crm,'crmch':channel(c['src'],''),'lch':a['ch'] if a else None,'lsrc':a['src'] if a else None,
     'camp':a['camp'] if a else None,'inv':c['inv'] or 'brak','v':round(sum(c['units'].values())),
     'dc':(c['sale']-c['created']).days if c['created'] else None,'dl':a['ds'] if a else None})
json.dump({'leads':rows,'sales':sales,'generated':dt.date.today().isoformat()},open('../dataset.json','w'),ensure_ascii=False)
print(len(rows),sum(r['conv'] for r in rows),sum(r['m'] for r in rows),sum(r['r'] for r in rows),sum(r['s'] for r in rows),len(sales),len(attributed))
print(collections.Counter((s['crmch'],s['lch']) for s in sales if s['d']>='2023-08').most_common(25))
c=collections.Counter(); s=collections.Counter()
for r in rows: c[r['ch']]+=1; s[r['ch']]+=r['s']
print(c,s)
cc=collections.Counter(); cs=collections.Counter()
for r in rows:
  if r['camp']: cc[r['camp']]+=1; cs[r['camp']]+=r['s']
for k,v in cc.most_common(30): print(v,cs[k],k)
