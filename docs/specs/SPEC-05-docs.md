# SPEC-05: Aktualna dokumentacja

**Problem:** README i CLAUDE.md opisują uruchamianie przez Docker Compose (i Railway),
a demo działa na Streamlit Community Cloud + Neon + GitHub Actions. Brakuje opisu celu,
odbiorców, strony „Dla Firm”, definicji niszy i ograniczeń metodologii. Dokumentacja ma
być źródłem dla raportu i prezentacji (D10).

**Zakres:**
- Wziąć niezmergowaną aktualizację README z gałęzi `docs/readme-deploy` (commit `067301c`)
  i na niej oprzeć zmiany.
- README: cel i problem (juniorzy, rozszerzenie na mid/senior), odbiorcy, moduły z pytaniami,
  na które odpowiadają, metodologia (typy wynagrodzeń, względny wiek, definicja niszy,
  zasady statystyczne, ograniczenia), architektura wdrożenia (Streamlit Cloud + Neon +
  GitHub Actions, darmowe plany, wybudzanie przed demo), opinie, uruchomienie lokalne
  (Docker Compose).
- CLAUDE.md: realne wdrożenie, `level_selector`, definicja niszy, tabela `feedback`,
  guard na stronie admina.
- Usunąć nieaktualne wzmianki o Railway z komentarzy w kodzie.

**Kryteria akceptacji:**
- Każda decyzja D1-D10 z `docs/specs/README.md` ma odzwierciedlenie w README lub CLAUDE.md.
- Komendy w README odpowiadają kodowi (`run_scrape_job`, a nie `ScraperManager`).
