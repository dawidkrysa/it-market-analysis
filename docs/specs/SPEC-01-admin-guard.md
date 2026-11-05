# SPEC-01: Strona admina sama sprawdza uprawnienia

**Problem:** `pages/5_Metodologia.py` (scraping, czyszczenie bazy, edycja bootcampów) jest
chroniona tylko tym, że `app.py` nie dodaje jej do `st.navigation`, gdy
`st.session_state.is_admin` jest fałszywe. Na publicznym demo to jedyna ochrona akcji
niszczących.

**Zakres:**
- Na samym początku strony, przed jakimkolwiek dostępem do bazy: jeśli
  `st.session_state.get("is_admin")` nie jest `True`, pokaż komunikat o braku dostępu
  i wywołaj `st.stop()`.

**Kryteria akceptacji:**
- `AppTest.from_file("pages/5_Metodologia.py")` bez ustawionego `is_admin` kończy się bez
  wyjątku, pokazuje komunikat o braku dostępu i nie renderuje zakładek.
- Z `is_admin = True` strona działa jak dotąd.
