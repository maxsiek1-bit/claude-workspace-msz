# Linki i źródła (stan 14.11.2026)

## Strona inwestycji
- Marina Hel Apartamenty – Euro Styl:
  https://www.eurostyl.com.pl/pl-pl/trojmiasto/lista-inwestycji/marina-hel-apartamenty?tabInTabs=1

## Makieta 3D (z niej pochodzi zrzut z zielonymi lokalami; adres z API, nie otwierałem jej)
- https://allinone.prod.resimo.io/eurostyl/marina-hel-apartamenty/

## API listy lokali (zapisane jako data/single.json)
- https://www.eurostyl.com.pl/iapi/search/single?resultsFor=5a97de5c-d52e-ef11-b825-005056927028&city=trojmiasto&language=pl-pl&apartmentsCount=500
  - `tabs[0].investments[0].flats` – 111 lokali (A: 85, B: 26); pola m.in. `flat`, `area`, `floor`, `more.href`
  - identyfikatory budynków: A = 12d43540-163d-ef11-b825-005056927028, B = 06a8754e-163d-ef11-b825-005056927028

## Inne wywołania API widziane na stronie (nieużywane)
- https://www.eurostyl.com.pl/iapi/search/searchlayercities?city=trojmiasto&language=pl-pl&apartmentsCount=7
- https://www.eurostyl.com.pl/iapi/map/domdevelopmentinvestmentgeojson?investmentPath=/Inwestycje/Marina-Hel-Apartamenty&lang=pl-pl&siteName=EuroStyl

## Strony kart lokali
- Wzorzec: https://www.eurostyl.com.pl/pl-pl/trojmiasto/mieszkanie?id=marina%20hel%20apartamenty_1_1_a_lu_{NR}
  - przykład: ...lu_102 (zapisany jako data/a102.html)
  - lokal sprzedany (sprawdzone na ...lu_101) zwraca 404
- Odwiedzone karty budynku A (85):
  - piętro 1: 102, 103, 107, 109, 110, 114, 115, 116, 118, 119
  - piętro 2: 204, 205, 206, 207, 208, 210, 212, 217, 218, 219, 220, 221, 222, 223, 224, 225, 226, 227
  - piętro 3: 301–313, 317–328
  - piętro 4: 401–411, 417, 418, 419, 421, 423–428
  - piętro 5: 501, 503, 504, 505, 506, 512, 513, 515, 516, 517, 518

## Pliki kart (PDF)
- Wzorzec: https://www.eurostyl.com.pl/getmedia/{GUID}/[MARINA HEL APARTAMENTY_1_1_A_{PIĘTRO}_{NR}][LU][RZUT][Plan lokalu użytkowego].pdf
  - GUID jest inny dla każdego lokalu – `dl.py` wyciąga pełny link ze strony karty
  - przykład (A 102): https://www.eurostyl.com.pl/getmedia/a1f4b702-3eed-4e73-8b59-f5b5ed77e9c5/[MARINA%20HEL%20APARTAMENTY_1_1_A_1_102][LU][RZUT][Plan%20lokalu%20u%c5%bcytkowego].pdf
- Na stronie karty są też: JPG karty (`..._l.jpg`) i rzuty 3D (`..._Rzut 3D_1..5.png`) – nieużywane.

## Dokumentacja Claude Code (pytanie o eksport czatu)
- https://code.claude.com/docs/en/sessions

## Dodane 14.11.2026 (praca w Claude Code)
- Makieta 3D (publiczna strona): https://allinone.prod.resimo.io/eurostyl/marina-hel-apartamenty/
  - strona sama pobiera listę wszystkich lokali obu budynków (statusy, linki do kart PDF i rzutów 3D); zapis w `data/viewer.json`
  - karty i rzuty 3D leżą pod adresami `https://prdddstructure.blob.core.windows.net/plans/...` (pełne linki w `data/viewer.json`)
- Ceny: brak w obu źródłach (API Euro Stylu: „Zapytaj o cenę"; makieta 3D: brak pola ceny).
