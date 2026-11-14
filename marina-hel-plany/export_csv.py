"""Krok 7: tabela wszystkich lokali (data/lokale.csv) z danych data/lokale.json."""
import json, csv, re
u = json.load(open('data/lokale.json')); ST = {'available': 'dostępny', 'reserved': 'zarezerwowany', 'sold': 'sprzedany', 'not_available': 'niedostępny'}
with open('data/lokale.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f, delimiter=';')
    w.writerow(['budynek', 'numer', 'pietro', 'status', 'PU_m2', 'cena_PLN', 'szer_X_m', 'gleb_Y_m', 'liczba_pokoi', 'balkon_taras_ogrodek_m2', 'pomieszczenia', 'karta_pdf', 'strona'])
    for x in u:
        ins = [r for r in x['pomieszczenia'] if not re.search('BALKON|TARAS|OGR|LOGGIA|w tym', r['nazwa'], re.I)]
        outd = [r for r in x['pomieszczenia'] if re.search('BALKON|TARAS|OGR|LOGGIA', r['nazwa'], re.I)]
        w.writerow([x['budynek'], x['numer'], x['pietro'], ST.get(x['status'], x['status']), str(x['pu_m2']).replace('.', ','), '',
                    str(x['szer_x_m']).replace('.', ','), str(x['gleb_y_m']).replace('.', ','), sum(1 for r in ins if r['nazwa'].startswith('POKÓJ')),
                    ' + '.join(f"{r['nazwa'].lower()} {str(r['m2']).replace('.', ',')}" for r in outd),
                    ' | '.join(f"{r['nazwa']} {str(r['m2']).replace('.', ',')}" for r in ins), x['karta_pdf'], x['strona']])
print(len(u))
