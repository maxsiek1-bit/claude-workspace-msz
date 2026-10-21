# Wadliwość urządzeń wg kohort numerów seryjnych

Łączy produkcję z Odoo 16 (numer seryjny → zlecenie MO → zużyte komponenty i ich partie)
ze zgłoszeniami błędów (zgłoszenia z Conpeek + helpdesk / naprawy / alerty jakości w Odoo) po **numerze seryjnym**.

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
export ODOO_URL=...           # adres instancji Odoo
export ODOO_DB=...            # nazwa bazy
export ODOO_USER=...          # login użytkownika
export ODOO_API_KEY=...       # Preferencje → Bezpieczeństwo konta → Klucze API
export CONPEEK_URL=...       # Conpeek: Ustawienia → Usługi → API → „Adres serwera API”
export CONPEEK_KEY=...
python run.py --period M      # W / M / Q / Y
python run.py --demo                                       # dane testowe
```
Numer seryjny w zgłoszeniu Conpeek wyszukiwany jest w nazwie, opisie i polach dodatkowych i dopasowywany do SN z Odoo; kod błędu = kategoria zgłoszenia (lub tagi). Zamiast API można podać eksport: `--conpeek-file plik.csv` (mapowanie kolumn w `conpeek.py`, `COLUMN_MAP`).
