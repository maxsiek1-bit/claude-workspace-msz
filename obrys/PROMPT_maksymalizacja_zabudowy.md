# Prompt: automatyczne maksymalne wypełnienie terenu zabudową

Wklej całość do nowego czatu w Claude Code razem z paczką plików (edytor, podkłady,
`INSTRUKCJA.md`) i z eksportem JSON aktualnego terenu.

---

## Rola i cel

Rozwijasz moje narzędzie do planowania zabudowy terenu. Mam już edytor, w którym na
ortofotomapie zaznaczam granicę terenu, strefy wyłączone i ręcznie ustawiam obrysy
budynków. Chcę, żeby narzędzie samo, na żywo, wypełniało zaznaczony obszar zabudową
tak gęsto, jak pozwalają na to zadane ograniczenia, i pokazywało mi liczby. Wzorem
jest zasada działania narzędzi typu „generative site planning” (znam ją z rolki na
Instagramie): zmieniam granicę albo parametr, a plan i statystyki przeliczają się od
razu. Nie kopiuj nazwy, logo ani interfejsu żadnego istniejącego produktu.

## Stan obecny (jak wygląda konfiguracja teraz)

Na załączonym zrzucie widać aktualny stan:

- **Podkład:** ortofotomapa, północ u góry, z georeferencją w EPSG:2180 (szczegóły w
  `INSTRUKCJA.md` i `podklad_georef.json`). Teren to pas startowy przy polu golfowym,
  okolice 54°34'53.49"N 18°12'38.62"E.
- **Granica terenu:** jeden wielokąt o 8 punktach, zaznaczony ręcznie. Długości boków:
  1–2: 77,6 m; 2–3: 278,5 m; 3–4: 77,7 m; 4–5: 229,4 m; 5–6: 69,5 m; 6–7: 117,8 m;
  7–8: 75,5 m; 8–1: 281,7 m. Kształt: długi pas biegnący z północnego zachodu na
  południowy wschód, z wypustką w stronę północnego wschodu (punkty 5–6–7).
- **Strefa wyłączona:** jeden przykładowy prostokąt „Wyłączona 1 (przykład)”, 3771 m²,
  z teksturą drzew, mniej więcej w środku pasa.
- **Budynki:** trzy obrysy ustawione ręcznie w południowo-wschodniej części pasa,
  obrócone zgodnie z kierunkiem pasa:
  - niebieski, długi budynek w kształcie litery L,
  - fioletowy, długi budynek w kształcie litery L (odbicie lustrzane niebieskiego),
  - pomarańczowy, mniejszy budynek oznaczony „Z1”, między nimi.
- **Czego nie ma:** budynki stoją tam, gdzie je ręcznie postawiłem. Nic nie układa się
  samo, większość terenu jest pusta, nie ma dróg ani dojazdów, nie ma liczb
  opisujących wykorzystanie terenu.

Dokładne współrzędne granicy, strefy i obrysów budynków weź z eksportu JSON i z kodu
edytora. Wymiarów budynków nie zgaduj ze zrzutu: odczytaj je z danych albo z mojego
modelu, a jeśli ich tam nie ma, zapytaj mnie.

## Stan docelowy (jak ma wyglądać konfiguracja)

W obszarze, który zaznaczam, zabudowa ma być rozmieszczona automatycznie i możliwie
najgęściej. Konkretnie:

1. **Obszar do zabudowy** wylicza się sam: granica terenu, minus strefy wyłączone,
   minus odsunięcie od granicy (parametr, domyślnie 4 m), minus odsunięcie od stref
   wyłączonych (parametr, domyślnie 0 m). Jeśli zaznaczę strefy „pod zabudowę”,
   zabudowa trafia tylko do nich.
2. **Biblioteka typów budynków:** moje trzy obrysy (L niebieski, L fioletowy, Z1) są
   typami w bibliotece. Każdy typ ma: obrys (wielokąt), liczbę kondygnacji,
   powierzchnię zabudowy, powierzchnię użytkową na kondygnację, liczbę lokali,
   dozwolone obroty i odbicie lustrzane, oraz udział w planie (np. 40 / 40 / 20 %
   albo „dowolnie”). Mogę dodawać własne typy i wyłączać istniejące.
3. **Automatyczne rozmieszczenie:** generator ustawia tyle budynków wybranych typów,
   ile się zmieści, przy zachowaniu:
   - minimalnej odległości między budynkami (parametr, domyślnie 8 m; osobno dla
     ścian z oknami, domyślnie 16 m, jeśli typ to rozróżnia),
   - dojazdu: każdy budynek musi przylegać do drogi wewnętrznej albo mieć do niej
     dojście nie dłuższe niż zadana wartość,
   - sieci dróg wewnętrznych o zadanej szerokości (domyślnie 6 m jezdnia + 2 m
     chodnik) z jednym lub kilkoma wjazdami, które wskazuję na granicy,
   - limitów: maksymalny procent powierzchni zabudowy, minimalny procent powierzchni
     biologicznie czynnej, maksymalna intensywność zabudowy, maksymalna wysokość,
     minimalna liczba miejsc postojowych na lokal (parkingi naziemne jako prostokąty
     przy drogach).
4. **Maksymalizacja:** generator porównuje kilka wariantów (kierunek siatki zgodny z
   najdłuższym bokiem, z każdym z dłuższych boków, obrót co 15°; układ rzędowy,
   grzebieniowy, wokół dziedzińców; różna kolejność typów) i wybiera najlepszy według
   wybranego celu. Cel wybieram z listy: największa liczba lokali, największa
   powierzchnia użytkowa, największa liczba budynków, największa powierzchnia
   zabudowy. Pokaż też 3–5 najlepszych wariantów do przełączania.
5. **Na żywo:** po przeciągnięciu punktu granicy, przesunięciu strefy wyłączonej albo
   zmianie parametru plan przelicza się sam, bez przycisku. Cel: poniżej ok. 300 ms dla
   terenu do 10 ha; jeśli pełna optymalizacja trwa dłużej, najpierw pokaż szybki
   wariant, a lepszy podmień, gdy się policzy (Web Worker).
6. **Ręczne poprawki:** mogę przypiąć budynek w miejscu (generator go nie rusza i
   układa resztę wokół), usunąć budynek albo zablokować fragment terenu. Mój obecny
   ręczny układ trzech budynków ma zostać zapisany jako osobny wariant „ręczny” do
   porównania z wynikiem generatora.
7. **Panel wyników:** liczba budynków ogółem i według typów, liczba lokali, powierzchnia
   zabudowy i jej udział w terenie, powierzchnia użytkowa łącznie, intensywność
   zabudowy, długość i powierzchnia dróg, liczba miejsc postojowych, powierzchnia
   biologicznie czynna i jej udział, gęstość (lokale na hektar). Przekroczone limity na
   czerwono. Obok porównanie: wariant ręczny a wariant wygenerowany.
8. **Podgląd 3D:** budynki jako bryły o wysokości wynikającej z liczby kondygnacji,
   na prawdziwej rzeźbie terenu, w kolorach typów. Docelowo zamiast brył wstawiam mój
   model 3D budynku (glTF/GLB) i zmieniam liczbę pięter suwakiem.
9. **Eksport:** JSON całego planu (granica, strefy, drogi, budynki z typem, pozycją,
   obrotem i współrzędnymi w EPSG:2180), CSV ze statystykami, a w kolejnym kroku DXF i
   PDF.

## Wygląd

- Teren: ciemna zieleń, półprzezroczysta na zdjęciu. Strefa wyłączona: intensywnie
  zielona tekstura drzew. Drogi: ciemnoszare z jaśniejszą osią. Parkingi: jasnoszare.
- Budynki w kolorach typów (obecne: niebieski, fioletowy, pomarańczowy) z etykietą typu
  i numerem. Budynki przypięte ręcznie z wyraźną obwódką.
- Uchwyty edycji jako małe niebieskie kwadraty. Wymiary boków po zewnętrznej stronie
  obrysu, w metrach.

## Wymagania techniczne

- Generator jako czysta funkcja: (granica, strefy, typy budynków, parametry) →
  (drogi, budynki, parkingi, statystyki, lista wariantów). Bez dostępu do DOM, żeby
  dało się go uruchomić w Web Workerze i przetestować osobno.
- Geometria: przycinanie i odsunięcia wielokątów biblioteką (np. polygon-clipping,
  Clipper, Turf lub JSTS). Kolizje budynków liczone na prawdziwych obrysach, nie na
  prostokątach otaczających.
- Jednostki: metry i m². Układ współrzędnych jak w obecnym edytorze (1 piksel = 0,30 m,
  przeliczenie do EPSG:2180 opisane w `INSTRUKCJA.md`).
- Zachowaj to, co już działa: rysowanie granicy i stref, bilans powierzchni, podgląd
  3D, zapisane tereny, eksport JSON.
- Testy generatora: żaden budynek nie wychodzi poza obszar do zabudowy, nie nachodzi na
  strefę wyłączoną ani na inny budynek, odległości i limity są spełnione, każdy budynek
  ma dojazd.

## Kolejność prac

1. Przeczytaj `INSTRUKCJA.md`, kod edytora i mój eksport JSON. Opisz mi krótko, co
   zastałeś, i zapytaj tylko o to, czego nie da się ustalić z plików (wymiary i
   kondygnacje typów budynków, wymagane odległości, miejsce wjazdu).
2. Obszar do zabudowy z odsunięciami i jego powierzchnia w panelu.
3. Biblioteka typów z moich trzech obrysów.
4. Pierwsza wersja generatora: układ rzędowy wzdłuż najdłuższego boku, bez dróg, z
   kontrolą kolizji i odległości. Pokaż działający wynik.
5. Drogi wewnętrzne, wjazdy, parkingi i warunek dojazdu.
6. Warianty i wybór najlepszego według celu; porównanie z wariantem ręcznym.
7. Przypinanie budynków, bryły w 3D, eksport.

Po każdym etapie pokaż działającą wersję i napisz, co jest uproszczone względem tego
opisu.

## Kryteria odbioru

- Po wczytaniu mojego terenu generator sam wypełnia cały obszar do zabudowy, a nie
  tylko jego fragment; liczba budynków jest wyraźnie większa niż w wariancie ręcznym
  (3 budynki) przy spełnionych ograniczeniach.
- Przesunięcie punktu granicy lub strefy wyłączonej zmienia plan i liczby bez
  klikania czegokolwiek.
- Zmiana celu optymalizacji zmienia wybrany wariant, a panel pokazuje dlaczego
  (wartość celu dla każdego wariantu).
- Wynik da się wyeksportować i wczytać z powrotem bez utraty danych.

## Zastrzeżenie

Wynik to analiza chłonności terenu, nie projekt budowlany. Parametry domyślne
(odległości, wskaźniki, miejsca postojowe) są przykładowe; właściwe wartości wynikają
z miejscowego planu lub warunków zabudowy oraz przepisów i podam je sam.
