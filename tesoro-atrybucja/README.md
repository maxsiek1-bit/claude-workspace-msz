# Atrybucja leadów Tesoro

Dashboard: https://claude.ai/artifact/4DxV1oydwHhHgf1yLs25yB

Źródło: VoxDeveloper Power BI API (`https://tsinvest.voxdeveloper.com/webservice/power-bi/source/...`,
nagłówek `Api-key`). Klucz API trzymaj poza repozytorium.

Endpointy dostępne dla klucza: `lead-comparision`, `schedule-payment-list`, `meeting`,
`agreements-registry`, `transaction-list`, `reservations-list`, `leads-list`, `endpoints`.

## Odtworzenie danych

1. Pobierz do `data/leads/RRRR-MM.json` miesięczne odpowiedzi
   `leads-list/date-from/RRRR-MM-01/date-to/RRRR-MM-DD` (pełny zakres zwraca 504).
2. Pobierz `data/trans.json` z `transaction-list/all-agreements/1`
   oraz `data/meet.json` z `meeting/date-from/2018-01-01/date-to/2026-12-31`.
3. `python3 build_dataset.py` (z katalogu `data/`) tworzy `dataset.json`; z niego powstają
   zanonimizowane CSV wgrane do dashboardu (`leady_atrybucja.csv`, `sprzedaz_zrodla.csv`).

Logika: lead łączony z klientem po telefonie / e-mailu; spotkanie i sprzedaż
(umowa deweloperska, przedwstępna, akt notarialny, bez anulowanych) przypisane do
pierwszego leada klienta utworzonego przed umową.

## Czego brakuje, aby analizować AdSety i kreacje

- dostęp do `leads-report` (pole `utm_data`, `lead_conversion_date`), `clients-report`, `clients-list`;
- w integracji leadów Meta/Google przekazywanie `adset_id/name`, `ad_id/name`, `form_id`,
  `adgroup_id`, `creative_id`, `keyword`, `gclid`;
- UTM + `gclid`/`fbclid` w formularzu na stronie WWW;
- koszty z kont reklamowych (Meta, Google Ads) do liczenia kosztu leada / spotkania / sprzedaży;
- konwersje offline (`gclid-conversions`, `google-ads-conversions`).
