# SPEC-02: Filtr poziomu na stronach kandydata

**Problem:** Radar, Weryfikacja Statystyczna i Kalkulator ROI liczą mediany i nisze na
łącznych ofertach junior, mid i senior. Juniorowi pokazują więc głównie zarobki starszych
poziomów. Filtr poziomu ma tylko strona „Dla Firm”.

**Zakres:**
- Wspólny widżet `level_selector()` w `utils/ui.py` w sekcji „Poziom doświadczenia”
  w sidebarze, zaraz po „Typie wynagrodzenia”. Jest to multiselect, domyślnie Junior.
- Wybór jest zapamiętany w `session_state`, więc przenosi się między stronami kandydata.
- Wspólna mapa etykiet `LEVEL_LABELS` w `utils/ui.py`. Używa jej też „Dla Firm”, ale jej
  domyślny wybór się nie zmienia.
- Radar i Weryfikacja: wszystkie metryki i wykresy liczone są z ofert na wybranych poziomach.
- Progi liczby ofert zależą od wyboru (D6). Gdy wybrano tylko Trainee/Junior, domyślne
  wartości suwaków są niższe:

  | Strona | Suwak | Cały rynek | Tylko junior |
  |---|---|---|---|
  | Radar | min. ofert | 15 | 5 |
  | Radar | max. ofert | 70 | 40 |
  | Radar | min. n z widełkami | 5 | 3 |
  | Weryfikacja | min. ofert | 10 | 5 |
  | Weryfikacja | max. ofert | 150 | 80 |

  Te wartości startowe trzeba zweryfikować na danych produkcyjnych.
- Kalkulator ROI: sugerowane zarobki to mediana dla technologii na wybranych poziomach
  (domyślnie junior), z podanym n. Przy n < 10 pojawia się ostrzeżenie. Nie stosujemy
  filtra „błękitnego oceanu”, bo bootcamp może uczyć dowolnej technologii.
- Przy każdej metryce widać, na jakich poziomach ją policzono.

**Kryteria akceptacji:**
- Domyślnie (Junior) wszystkie trzy strony liczą tylko oferty juniorskie, a podpis to mówi.
- Zmiana poziomu na jednej stronie jest widoczna po przejściu na drugą.
- Pusty wybór pokazuje komunikat zamiast błędu.
- AppTest na danych syntetycznych przechodzi bez wyjątków dla: Junior, Junior+Mid+Senior
  i pustego wyboru.
