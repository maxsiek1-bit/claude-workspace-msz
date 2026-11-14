"""Pobiera karty PDF i rzuty 3D (PNG) wszystkich lokali z danych makiety 3D (data/viewer.json)."""
import json,os,subprocess,sys,concurrent.futures as cf
j=json.load(open('data/viewer.json'))
os.makedirs('cards',exist_ok=True);os.makedirs('renders',exist_ok=True)
jobs=[]
for b in j:
    for x in b['apartments']:
        key=b['number']+x['symbol']
        if x['status']!='available' and any(y['symbol']==x['symbol'] and y['status']=='available' for y in b['apartments']): continue
        if x['pdfUrl']: jobs.append((x['pdfUrl'],f'cards/{key}.pdf'))
        for i,u in enumerate(x['files'] or [],1): jobs.append((u,f'renders/{key}_{i}.png'))
def get(job):
    u,out=job
    if os.path.exists(out) and os.path.getsize(out)>5000: return out,'ok'
    subprocess.run(['curl','-sS','-g','-m','120','--retry','3','-A','Mozilla/5.0',u,'-o',out+'.part'])
    if os.path.exists(out+'.part') and os.path.getsize(out+'.part')>5000:
        os.replace(out+'.part',out);return out,'new'
    return out,'FAIL'
with cf.ThreadPoolExecutor(8) as ex: r=list(ex.map(get,jobs))
print(len(r),'plików;','nowe',sum(1 for x in r if x[1]=='new'),'; błędy',[x[0] for x in r if x[1]=='FAIL'])
