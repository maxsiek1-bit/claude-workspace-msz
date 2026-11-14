# Marina Hel Apartamenty – plany pięter złożone z kart lokali (budynki A i B)

Projekt dla Maxa (TS Invest). Odpowiadaj po polsku, krótko i konkretnie.

## Co to jest

Plany całych kondygnacji budynków A i B inwestycji Marina Hel Apartamenty (Euro Styl, Hel), złożone automatycznie
z kart lokali dewelopera, we wspólnym układzie współrzędnych w metrach. Cel: nałożenie płaszczyzn pięter na model 3D
i pokazywanie wymiarów lokali, pomieszczeń i części wspólnych. Stan danych: 14.11.2026.

## Co jest w paczce

- `out/plany/MarinaHel_{A|B}_pietro{n}.pdf|png` – plan piętra z etykietami (numer, PU, kolor = status), podziałką 10 m.
- `out/tekstury/MarinaHel_{A|B}_pietro{n}.png|pdf` – czysta płaszczyzna piętra bez opisów, 40 px = 1 m,
  ten sam rozmiar i to samo położenie dla wszystkich pięter budynku (do nakładania na model 3D).
- `out/kontrola/` – obrazy kontrolne wydzielenia części wspólnych (pomarańczowy = korytarz, zielony = lokale).
- `data/lokale.json` / `data/lokale.csv` – 163 lokale: numer, piętro, status, PU, pomieszczenia z powierzchniami,
  obrys i wymiary w metrach, ścieżka karty i rzutów 3D. Pole `cena` jest puste (patrz niżej).
- `data/budynki.json` – skala, rozmiar arkusza/tekstury, lista pięter.
- `data/czesci_wspolne.json` – korytarze i inne strefy poza lokalami: powierzchnia, długość, szerokość w świetle.
- `data/viewer.json` – surowe dane z makiety 3D dewelopera (wszystkie lokale, statusy, linki do kart i rzutów 3D).
- `cards/` – 163 karty lokali PDF. `renders/` – 795 rzutów 3D PNG (807 MB, poza repozytorium; odtwarza `fetch.py`).

Numeracja pięter: budynek A – 1xx = piętro 1 (parter to lokale usługowe U1, U2); budynek B – 1xx = parter, 2xx = piętro 1 itd.

## Ceny

Deweloper nie publikuje cen: API listy lokali zwraca dla każdego lokalu „Zapytaj o cenę", a dane makiety 3D nie mają pola ceny.
Kolumna `cena_PLN` w CSV i pole `cena` w JSON czekają na cennik od dewelopera.

## Dokładność

- Karty nie mają wymiarów liniowych, tylko powierzchnie pomieszczeń. Skala jest wyliczona z tych powierzchni:
  budynek B 0,2159 m na 1 pt planu piętra (rozrzut 0,7%), budynek A 0,3947 m (rozrzut 1,5%).
  Wymiary liniowe traktuj jako ±1–3%, nie do wymiarowania wykonawczego.
- Powierzchnie pomieszczeń i PU pochodzą wprost z kart (suma pomieszczeń = PU dla 159 z 163 lokali).
- Piętra jednego budynku pokrywają się między sobą z dokładnością ok. 0,1 m.
- Części wspólne liczone są z małego planu piętra – wartości przybliżone; „inne strefy" obejmują też balkony i tarasy.
- Braki: A 514 i B 104 nie mają karty (puste miejsce na planie). Karty lokali usługowych (A U1, A U2, B U101) mają inny układ –
  ich rzuty są wstawione mniej pewnie. Współrzędne nie mają kierunku północy (strzałka jest na kartach, nie została odczytana).

## Jak to działa

1. `node fetch_viewer.js` – otwiera publiczną makietę 3D i zapisuje dane lokali, które strona sama pobiera (`data/viewer.json`).
2. `python3 fetch.py` – pobiera karty PDF i rzuty 3D.
3. `python3 register.py` – dopasowuje każdy rzut do zaznaczenia na planie piętra z karty (korelacja FFT, skala K + przesunięcie) → `data/reg.json`. Ok. 10 min na 4 rdzeniach.
4. `python3 rooms.py` – czyta pomieszczenia i szacuje skalę rzutu z ich powierzchni → `data/rooms.json`.
5. `python3 scale.py` – skala planu piętra na budynek → `data/scale.json`.
6. `python3 compose.py A B` – plany, tekstury, `lokale.json`, `budynki.json`.
7. `python3 commons.py` – części wspólne. 8. `python3 export_csv.py` – tabela CSV.

Wymagania: `pip install pymupdf numpy scipy pillow`, Node z Playwright (krok 1), czcionki DejaVu (Linux).
Skrypty uruchamiać z katalogu projektu. `legacy/` – pierwsza wersja skryptów (tylko budynek A, tylko lokale dostępne).

## Pliki pomocnicze

- `ROZMOWA.md` – zapis pierwszej rozmowy. `LINKI.md` – źródła i adresy.

## Przeglądarka 3D (`viewer3d/`)

Strona WWW (three.js) z bryłami `Budynek_A/B/C` z pliku Blendera Maxa (`Marina_Hel_Apartamenty1.blend`, nie ma go w repozytorium)
i płaszczyznami pięter A i B. Opublikowana: https://claude.ai/artifact/Ckzwo1cb29QiaA5b1MtcwQ

- `index.html` – przeglądarka: prześwit każdej bryły, włączanie pięter, przekrój na wybranym piętrze, rozsuwanie pięter, karta lokalu po kliknięciu.
- `geo/*.json` – geometria brył (cm, oś Y w górę). `tex/*.webp` – tekstury pięter z przezroczystym tłem (wersja `_opis` z numerami). `data.json` – piętra, lokale, dopasowanie.
- `tools/blend_export.py <plik.blend> <katalog>` (wymaga `pip install bpy`) – eksport brył do `.npz` i `analysis.json`.
- `tools/fit_outline.py <katalog z .npz>` – dopasowanie plan → model po obrysie (podobieństwo: obrót ok. 17°, skala 1,022 dla A i 1,029 dla B, IoU 0,94 / 0,93) → `tools/fit.json`.
  `tools/fit_v1_bryly_lokali.json` – pierwsze dopasowanie z brył lokali kolekcji `MH_Referencja_dewelopera` (odrzucone: bryły są za głębokie i rozciągały plany); z niego pochodzą tylko poziomy podłóg.
- `masks.py` (katalog główny) – maska każdego piętra = obrys budynku + własny obszar każdego lokalu z balkonem/tarasem/ogródkiem; reszta (schody terenowe, garaż pod dziedzińcem, luźne opisy) jest wycinana. Kontrola: `data/maski_kontrola.json`, `out/kontrola/maska_*.png` (czerwone = wycięte).
- `tools/verify_fit.py <katalog z .npz>` – porównanie każdej płaszczyzny z obrysem bryły → `data/dopasowanie_kontrola.json`, `out/kontrola/model_*.png`.
- `tools/build_assets.py <katalog z .npz>` – buduje `geo/`, `tex/`, `data.json` (w tym czerwone wymiary zewnętrzne).

Kolejność po zmianie planów: `compose.py` → `commons.py` → `masks.py` → `fit_outline.py` → `build_assets.py` → `verify_fit.py`.
Poziomy podłóg w modelu: 3,62 / 6,57 / 9,52 / 12,47 / 15,58 m (A: piętra 1–5, B: parter–piętro 4); parter A 0,67 m.

### Wersja po modyfikacji (przełącznik pod tytułem w przeglądarce)

`tools/build_variant.py <katalog z .npz>` (po `build_assets.py`) – budynek A skrócony o pas planu x = 24,9–37,4 m (12,5 m) na wszystkich piętrach:
znika klatka schodowa od strony szczytu i 12 lokali (A 109, 110, 212, 213, 218, 312, 313, 318, 412, 413, 418, 509), szczyt z A 510 / A 511 jest dosunięty,
a reszta A 512 (ok. 37%) połączona z A 513 (PU szacunkowe). Lokali A na planach: 122 → 109, suma PU 5062 → 4557 m².
Wynik: `geo/Budynek_A_v2.json`, `tex/A*_v2.webp`, `data.json` → `v2`. Wersja podstawowa zostaje bez zmian. Ściana między A 512 a A 513 jest nadal narysowana na planie.
