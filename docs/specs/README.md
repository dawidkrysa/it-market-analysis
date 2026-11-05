# Specyfikacje przed obroną

Małe, niezależnie wdrażane specyfikacje ustalone w wywiadzie 2026-11-05.
Obrona projektu semestralnego: przed ok. 2026-12-05.

## Cel projektu

Narzędzie oparte na danych z ogłoszeń: pomaga kandydatom (pierwotnie juniorom, od tego
semestru również mid i senior) zdecydować, **czego się uczyć**, **ile żądać** i **czy opłaca się
bootcamp**, a firmom pokazuje, **co oferuje konkurencja**, jak **lepiej napisać ogłoszenie**
i dlaczego **warto zatrudniać juniorów**. Działa na darmowej infrastrukturze
(Streamlit Community Cloud + Neon + GitHub Actions).

Kryteria sukcesu: działające publiczne demo, wiarygodne statystycznie wnioski, realni
użytkownicy (mierzeni formularzem opinii).

## Kluczowe decyzje

| # | Decyzja |
|---|---|
| D1 | Projekt jest jednocześnie zaliczeniem przedmiotu i pozycją w portfolio, z możliwością dalszego rozwoju. |
| D2 | Kandydaci i firmy to równorzędni odbiorcy. |
| D3 | Zakres to junior, mid i senior. Junior jest domyślnym poziomem na stronach kandydata. |
| D4 | „Błękitny ocean” liczony jest względem wybranego poziomu: duży udział ofert na tym poziomie, przyzwoita mediana, trudność obsadzenia. |
| D5 | Trudność obsadzenia = względny wiek ogłoszenia (percentyl w obrębie portalu). |
| D6 | Dla samych juniorów progi liczby ofert są niższe niż dla całego rynku. |
| D7 | Opinie trafiają do tabeli `feedback` w Postgresie i są chronione przed spamem. |
| D8 | Strona admina sama sprawdza uprawnienia. Ukrycie w nawigacji nie wystarcza. |
| D9 | Przed obroną zespół wybudza demo ręcznie, bez automatycznego „keep-alive”. |
| D10 | Dokumentacja w repo jest źródłem dla raportu, prezentacji i karty projektu. |

## Specyfikacje

| Spec | Temat | Zależy od |
|---|---|---|
| [SPEC-01](SPEC-01-admin-guard.md) | Strona admina sama sprawdza uprawnienia | - |
| [SPEC-02](SPEC-02-level-filter.md) | Filtr poziomu na stronach kandydata | - |
| [SPEC-03](SPEC-03-level-niche.md) | Nisza liczona względem wybranego poziomu | SPEC-02 |
| [SPEC-04](SPEC-04-feedback.md) | Formularz opinii | - |
| [SPEC-05](SPEC-05-docs.md) | Aktualna dokumentacja | 01-04 |
