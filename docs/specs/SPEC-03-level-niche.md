# SPEC-03: Nisza liczona względem wybranego poziomu

**Problem:** README obiecuje „duży popyt i małą konkurencję”, ale portale nie podają liczby
kandydatów. `_filter_viable_niches` wybiera po prostu technologie z niewielką liczbą ofert
i sortuje je po medianie. Dla celu projektu potrzebna jest definicja zależna od poziomu (D4)
z jawnie opisanymi przybliżeniami (D5).

**Definicja:** dla wybranych poziomów P i technologii T:

| Składnik | Metryka | Przybliża |
|---|---|---|
| Otwartość | `Udzial_Ofert_Poziomu` = oferty T na poziomach P / wszystkie oferty T (%) | jak bardzo technologia jest dostępna dla kandydata z tego poziomu |
| Płaca | `Mediana_Zarobkow` (na poziomach P, wybrany typ wynagrodzenia) | atrakcyjność finansowa |
| Trudność obsadzenia | `Wzgledny_Wiek_Ogloszen` (mediana percentyla wieku w portalu, oferty na P) | niedobór kandydatów: ogłoszenia wiszą dłużej |

`Wynik_Niszy` (0-100) to średnia percentyli trzech składników wśród nisz, które przeszły
filtry. Każdy składnik ma tę samą wagę, a wyższy wynik oznacza lepszą niszę. Filtry
pozostają bez zmian: liczba ofert w przedziale suwaków, transparentność ≥ 10%,
min. n z widełkami. Ranking sortuje się po `Wynik_Niszy`.

Gdy wybrane są wszystkie poziomy, otwartość wynosi 100% dla każdej technologii. Wynik opiera
się wtedy tylko na płacy i trudności obsadzenia, co UI zaznacza.

**Ograniczenia (opisane w UI i README):** wiek ogłoszenia to przybliżenie. Długo wiszące
ogłoszenie może oznaczać niedobór kandydatów, ale też wysokie wymagania albo ogłoszenie
„zawsze otwarte”. Oferty z kilkoma technologiami zasilają kilka nisz naraz.

**Zakres:**
- `utils/db_handler.py`: `level_niche_metrics(df_exploded, poziomy)` dodaje
  `Udzial_Ofert_Poziomu`. `_filter_viable_niches` liczy `Wynik_Niszy` i według niego sortuje.
- Radar: lider, mapa nisz (kolor = wynik, podpowiedź z udziałem poziomu), tabela z nowymi
  kolumnami, rozwijana sekcja „Jak liczymy niszę”.

**Kryteria akceptacji:**
- Na danych syntetycznych technologia z dużym udziałem ofert juniorskich, wysoką medianą
  i starymi ogłoszeniami wygrywa ranking dla poziomu Junior.
- AppTest strony Radar przechodzi bez wyjątków.
