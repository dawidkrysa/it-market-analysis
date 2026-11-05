# SPEC-04: Formularz opinii

**Problem:** „realni użytkownicy” to kryterium sukcesu, ale aplikacja nie zbiera żadnego
sygnału od użytkowników.

**Zakres:**
- Model `Feedback` (tabela `feedback`), tworzony przez `create_tables()`, więc nie trzeba
  pisać `ALTER`. Kolumny: `id`, `created_at`, `strona`, `perspektywa`
  (kandydat / firma / inne), `ocena` (pomogło / częściowo / nie), `komentarz`
  (do 1000 znaków).
- Formularz „Twoja opinia” w globalnym sidebarze (`app.py`), widoczny na każdej stronie.
  Nazwa bieżącej strony jest zapisywana automatycznie.
- Panel admina, zakładka „Opinie”: tabela opinii i rozkład ocen.

**Ochrona przed spamem (D7):**
- Jedna opinia na sesję przeglądarki. Po wysłaniu formularz zamienia się w podziękowanie.
- Minimalny czas od otwarcia sesji do wysłania: 10 s (odsiewa automaty).
- Globalny limit: najwyżej 30 opinii na godzinę. Ponad limit formularz odmawia zapisu.
- Komentarz przycinany do 1000 znaków. Pusty formularz, czyli brak oceny, nie jest zapisywany.

**Kryteria akceptacji:**
- Wysłanie opinii zapisuje dokładnie jeden wiersz, a drugie wysłanie w tej samej sesji
  jest niemożliwe.
- Formularz bez działającej bazy pokazuje komunikat zamiast wyjątku i nie blokuje strony.
- Opinie są widoczne w panelu admina.
