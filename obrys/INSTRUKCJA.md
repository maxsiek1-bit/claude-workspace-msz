# Generator planu zabudowy terenu: zamysł i stan prac

Ten dokument jest przeznaczony dla kolejnego czatu w Claude Code. Opisuje, co chcę
zbudować, co już istnieje w tej paczce i od czego zacząć dalej.

## 1. Zamysł w skrócie

Pomysł pochodzi z rolki na Instagramie pokazującej narzędzie typu „generative site
planning”. Chcę własne narzędzie o podobnej zasadzie działania (bez kopiowania nazwy,
logo ani interfejsu żadnego istniejącego produktu):

1. Na mapie mojego terenu zaznaczam granicę oraz strefy, gdzie chcę wchodzić z zabudową
   i gdzie nie chcę (las, staw, pas startowy itp.).
2. Narzędzie samo, na żywo, układa drogi wewnętrzne, działki i budynki, tak aby
   uzyskać jak najwięcej działek przy zadanych ograniczeniach.
3. Równolegle tworzę własny model 3D budynku (z piętrami). Docelowo chcę wstawiać ten
   model na wygenerowane działki i oglądać całość w 3D na prawdziwym terenie: z lotu
   ptaka i chodząc po terenie.
4. Wszystko ma być połączone w jedną całość: rzut 2D do zaznaczania, podgląd 3D do
   oglądania, liczby (powierzchnie, liczba działek i lokali) aktualizowane na żywo.

Teren: okolice 54°34'53.49"N 18°12'38.62"E (pas startowy przy polu golfowym).

## 2. Co już jest zrobione (ta paczka)

| Plik | Co zawiera |
|---|---|
| `edytor_obrysu.html` | Cały edytor w jednym pliku. Otwiera się w przeglądarce. |
| `ortofoto.jpg` | Środkowe 600 × 600 m terenu, 0,30 m na piksel, północ u góry. |
| `ortofoto_szerokie.jpg` | Otoczenie 1800 × 1800 m, 0,90 m na piksel. |
| `podklad_georef.json` | Georeferencja obu zdjęć (EPSG:2180) i siatka wysokości terenu 61 × 61 co 30 m. |
| `INSTRUKCJA.md` | Ten dokument. |

Edytor potrafi:

- **Rzut 2D:** „Dodaj punkt” stawia punkty obrysu kliknięciem; punkty można przesuwać,
  usuwać, wstawiać na boku; całość można przesuwać i obracać; cofanie zmian.
- **Warstwy:** granica terenu, strefy pod zabudowę, strefy wyłączone (tekstura drzew).
- **Bilans terenu na żywo:** teren w granicy, strefy wyłączone, dostępne pod zabudowę,
  zaznaczone pod zabudowę. Strefy liczą się tylko wewnątrz granicy, wyłączenie ma
  pierwszeństwo.
- **Wymiary:** długość każdego boku po zewnętrznej stronie obrysu; długość można wpisać
  ręcznie.
- **Podgląd 3D:** zdjęcie nałożone na prawdziwą rzeźbę terenu, widok z lotu ptaka i
  spacer na wysokości oczu; strzałki w prawym dolnym rogu i na klawiaturze.
- **Zapisane tereny:** nazwane warianty (np. „MS zabudowa”) w pamięci przeglądarki.
- **Eksport / import JSON:** przycisk „Kopiuj JSON do eksportu”.

Uwaga: mój zaznaczony teren „MS zabudowa” jest zapisany w pamięci przeglądarki, nie w
pliku. Żeby go przenieść, w edytorze klikam „Kopiuj JSON do eksportu” i wklejam tekst
do nowego czatu (albo w edytorze: „Dane JSON” → wklej → „Wczytaj z pola”).

## 3. Dane techniczne potrzebne do dalszej pracy

- **Układ pikseli edytora:** 1 piksel = 0,30 m. Początek (0, 0) to lewy górny róg
  środkowego zdjęcia: E = 448703,16, N = 746996,62 w EPSG:2180 (PUWG 1992). Oś x na
  wschód, oś y na południe. Szeroki podkład obejmuje piksele od −2000 do 4000.
- **Przeliczenie:** `E = 448703.16 + x * 0.3`, `N = 746996.62 − y * 0.3`.
- **Eksport JSON** (dla każdej warstwy): `kind` (`site` = granica, `build` = strefa pod
  zabudowę, `excl` = strefa wyłączona), `vertices_m` (metry lokalne, x na wschód, y na
  północ), `vertices_puwg1992` (`[E, N, H]`, H = wysokość terenu w m n.p.m.),
  `vertices_px`, `area_m2`, `perimeter_m`; do tego `balance_m2`.
- **Wysokości:** `podklad_georef.json` → `elevation.h`, wiersze od północy, kolumny od
  zachodu, 61 × 61 punktów na obszarze 1800 × 1800 m.
- **Źródła:** ortofotomapa i numeryczny model terenu z Geoportalu (GUGiK). W południowej
  części zdjęcia usunięto niebieską mgłę korektą kolorów. Nie są to dane Google.
- **Budowa pliku HTML:** jeden plik, zdjęcia wbudowane jako base64, biblioteka
  `polygon-clipping` wbudowana, `three.js r128` ładowany z cdnjs (podgląd 3D wymaga
  internetu). Stan trzymany w `localStorage` (`obrys-edytor-v4`, `obrys-tereny-v1`).

## 4. Co jest uproszczone względem zamysłu

- Podgląd 3D pokazuje tylko rzeźbę terenu ze zdjęciem. Nie ma budynków ani drzew w 3D.
- Nie ma jeszcze generatora dróg, działek i budynków.
- Nie ma importu mojego modelu 3D budynku.
- Podkład to gotowe zdjęcie, nie przesuwana mapa (MapLibre / Leaflet).
- Brak eksportu PDF, DXF i CSV; jest tylko JSON.

## 5. Proponowana kolejność dalszych prac

1. Wczytać mój eksport JSON („MS zabudowa”) jako dane wejściowe: granica, strefy pod
   zabudowę, strefy wyłączone.
2. Generator jako czysta funkcja: (granica, strefy wyłączone, typy działek, parametry
   dróg) → (drogi, działki, budynki, statystyki). Najpierw pętla drogi i działki w pasie
   zewnętrznym, potem kwartały wewnętrzne i wybór najlepszego wariantu.
3. Edytor typu działki i biblioteka typów (dom, ADU, utwardzenie, odsunięcia, limity).
4. Import mojego modelu 3D budynku (np. glTF / GLB) i wstawianie go na działki w
   podglądzie 3D, z możliwością zmiany liczby pięter.
5. Panel wyników oraz eksport planu do PDF, DXF i statystyk do CSV.

## 6. Pełna specyfikacja docelowa (z poprzedniego czatu)

To jest opis docelowego narzędzia. Nie trzeba go wykonywać krok po kroku od razu; to
kierunek, do którego zmierza projekt.

**Cel.** Parametryczny generator planu podziału terenu pod osiedle domów
jednorodzinnych. Użytkownik rysuje granicę terenu na mapie, a aplikacja automatycznie i
w czasie rzeczywistym generuje układ dróg wewnętrznych, działek i budynków,
maksymalizując liczbę działek przy zadanych ograniczeniach. Narzędzie służy do szybkiej
analizy chłonności terenu na etapie zakupu gruntu. Wynik jest wiarygodny tylko wtedy,
gdy liczony jest na realnych typach działek (z domem, podjazdem i budynkami
dodatkowymi), a nie na pustych prostokątach.

**Widok główny: mapa.**
- Podkład mapowy, widok z góry.
- Użytkownik rysuje wielokąt granicy i może przeciągać wierzchołki oraz krawędzie.
  Teren może być nieregularny.
- Po każdej zmianie geometrii plan przelicza się od razu, bez przycisku „generuj”,
  poniżej ok. 200 ms dla terenu do 10 ha.

**Generowanie układu.**
- Zaokrąglenie narożników terenu i odsunięcie zabudowy od granicy o zadany margines.
- Sieć dróg wewnętrznych: pętla równoległa do granicy plus poprzeczne łączniki dzielące
  wnętrze na kwartały. Zadana szerokość i promienie łuków, wyokrąglone skrzyżowania.
- Podział pasów między drogą a granicą oraz kwartałów wewnętrznych na działki o froncie
  przylegającym do drogi. Każda działka musi mieć dostęp do drogi.
- Działki narożne i przy łukach mogą być nieregularne, ale muszą spełniać minimalną
  szerokość frontu i minimalną powierzchnię.
- Resztki terenu, na których nie mieści się działka, zostają jako zieleń.
- Algorytm porównuje kilka wariantów układu dróg i wybiera ten z największą liczbą
  działek spełniających warunki.

**Edytor typu działki.**
- Osobny widok jednej prostokątnej działki, w którym rozmieszcza się i skaluje
  prostokątne elementy: Housing (dom główny), ADU (dodatkowy mały budynek mieszkalny),
  Impervious (nawierzchnia utwardzona), opcjonalnie garaż lub szopa.
- Każdy element pokazuje nazwę, powierzchnię brutto i liczbę lokali, na żywo.
- Parametry działki: szerokość, głębokość, odsunięcia od granic, maksymalny procent
  powierzchni zabudowy i utwardzonej. Przekroczenie limitu na czerwono.
- Typ działki zapisuje się w bibliotece pod własną nazwą z miniaturą. Użytkownik
  wybiera, które typy i w jakich proporcjach mają być użyte w planie.

**Strefy wyłączone.**
- Prostokąt lub wielokąt wewnątrz terenu wyłączony z zabudowy (las, park, zbiornik),
  który można przesuwać i skalować. Tekstura drzew. Drogi i działki układają się od
  nowa wokół niej przy każdej zmianie.

**Panel wyników.**
- Liczba działek ogółem i w podziale na typy, liczba lokali (domy + ADU).
- Łączna powierzchnia zabudowy brutto, powierzchnia utwardzona i jej udział.
- Długość i powierzchnia dróg, powierzchnia zieleni, gęstość (lokale/ha).

**Wygląd.**
- Teren: ciemna zieleń; drogi: ciemnoszary z osią; granice działek: cienka ciemna
  linia; dom: jasnozielony; ADU: jasnożółty; utwardzenie: szary; strefa wyłączona:
  intensywnie zielona tekstura drzew.
- Uchwyty edycji jako małe niebieskie kwadraty na wierzchołkach.

**Technologia (docelowo).**
- TypeScript + React, mapa w MapLibre GL, geometria w Turf.js lub JSTS.
- Generator jako czysta funkcja uruchamiana w Web Workerze.
- Jednostki metryczne z możliwością przełączenia na stopy.

## 7. Jak zacząć w nowym czacie

Wgraj tę paczkę i napisz na przykład:

> W paczce jest edytor obrysu terenu i plik INSTRUKCJA.md z moim zamysłem. Przeczytaj
> instrukcję, otwórz `edytor_obrysu.html` i kontynuuj od punktu 5.1. Poniżej wklejam
> JSON mojego terenu „MS zabudowa”.
