import json,re,html,urllib.parse,subprocess,os,concurrent.futures as cf
j=json.load(open('data/single.json'))
f=[x for x in j['tabs'][0]['investments'][0]['flats'] if x['flat'].startswith('A ')]
def get(x):
    n=x['flat'].split()[1]
    out=f'cards/A{n}.pdf'
    if os.path.exists(out) and os.path.getsize(out)>10000: return n,'ok'
    url='https://www.eurostyl.com.pl'+x['more']['href'].replace(' ','%20')
    h=subprocess.run(['curl','-sS','-m','60','-A','Mozilla/5.0',url],capture_output=True).stdout.decode('utf8','ignore')
    m=re.search(r'/getmedia/[^"\']*_A_\d_'+n+r'\]\[LU\]\[RZUT\][^"\']*\.pdf',h)
    if not m: return n,'nopdf'
    subprocess.run(['curl','-sS','-g','-m','90','-A','Mozilla/5.0','https://www.eurostyl.com.pl'+html.unescape(m.group(0)),'-o',out])
    return n,os.path.getsize(out)
with cf.ThreadPoolExecutor(6) as ex:
    r=list(ex.map(get,f))
print(len(r),[x for x in r if x[1] in('nopdf',) or (isinstance(x[1],int) and x[1]<10000)])
