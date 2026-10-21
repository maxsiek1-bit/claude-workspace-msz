# Wadliwość urządzeń wg kohort numerów seryjnych

Łączy produkcję z Odoo 16 (numer seryjny → zlecenie MO → zużyte komponenty i ich partie)
ze zgłoszeniami błędów (Compika + helpdesk / naprawy / alerty jakości w Odoo) po **numerze seryjnym**.

## Co daje raport (`output/wadliwosc_kohorty.xlsx` + `.html`)
| Arkusz | Treść |
|---|---|
| Kohorty | wyprodukowane / wadliwe / % wadliwości / top 3 błędy w każdej kohorcie, % narastająco od początku |
| Krzywa kohort | % jednostek z awarią do N miesięcy od produkcji (porównanie kohorta do kohorty w tym samym „wieku”) |
| Błędy x kohorta | liczba wadliwych SN per kod błędu i kohorta |
| Komponenty / Partie komponentów | wadliwość jednostek z danym komponentem/partią, *lift* vs średnia, udział we wszystkich wadliwych |
| Komponenty x kohorta | jak wyżej, w rozbiciu na kohorty |
| Partie x błędy | które partie komponentów współwystępują z którymi błędami |
| Numery seryjne | pełna lista SN z kohortą, datą pierwszego zgłoszenia i kodami błędów |
| Niedopasowane SN | zgłoszenia z SN, którego nie ma w produkcji Odoo (jakość danych) |

## Uruchomienie
```bash
export ODOO_URL=https://myodoo-pl-enbio.odoo.com
export ODOO_DB=myodoo-pl-enbio-master-6316047
export ODOO_USER=...          # login użytkownika
export ODOO_API_KEY=...       # Preferencje → Bezpieczeństwo konta → Klucze API
python run.py --compika eksport_compika.csv --period M    # W / M / Q / Y
python run.py --demo                                       # dane testowe
```
Mapowanie kolumn eksportu Compika ustawia się w `compika.py` (`COLUMN_MAP`).
