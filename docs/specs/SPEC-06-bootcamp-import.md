# SPEC-06: Import bootcampów odczytuje kwoty zapisane jako tekst

**Problem:** w `examples/Bootcamps.xlsx` koszty i czasy trwania są tekstem („2000.00 PLN”,
„Brak danych”). `_to_float_or_none` w `utils/db_handler.py` przyjmował tylko czyste liczby,
więc import tego pliku w panelu admina (zakładka „Bootcampy”) zapisywał wszystkie kwoty
jako `NULL`. Kalkulator ROI traktuje brak kosztu jako 0 PLN, więc pokazywał zaniżony koszt
inwestycji i zawyżony zwrot.

**Zakres:**
- `_to_float_or_none` usuwa oznaczenia waluty („PLN”, „zł”) i spacje (także twarde) oraz
  akceptuje przecinek dziesiętny.
- Tekst bez liczby (np. „Brak danych”) nadal daje `None`.
- Ta sama funkcja obsługuje import pliku i ręczną edycję tabeli, więc obie ścieżki działają tak samo.

**Kryteria akceptacji:**
- `"2000.00 PLN"` → 2000.0, `"3 870,50 zł"` → 3870.5, `5` → 5.0, `"Brak danych"` → `None`,
  pusta komórka → `None`.
- Import `examples/Bootcamps.xlsx` zapisuje koszty jako liczby (np. `.net`: 3870 PLN, 5 dni).
