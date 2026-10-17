"""
Radar Mikro-nisz - Main Streamlit Page.

The home page of the Streamlit application displaying project details
and an introduction to the IT job market analysis.
"""

from zoneinfo import ZoneInfo

import streamlit as st

from utils.db_handler import DatabaseHandler

# Page configuration (must always be the first Streamlit command in the entry file)
st.set_page_config(page_title="Radar Mikro-Nisz IT", page_icon=":material/radar:", layout="wide")

# --- Header and Logo ---
col1, col2 = st.columns([4, 1], vertical_alignment="center")

with col1:
    # Added a main, short title and moved the long academic title to the subheader
    st.title("Radar Mikro-Nisz IT")
    st.subheader("Wpływ niszowości technologii na opłacalność i czas zatrudnienia")

with col2:
    try:
        st.image("assets/wsb_logo.png", width=150)
    except Exception:
        # Fallback in case the file path is invalid or the image is missing
        st.caption("[Logo Uczelni]")

st.markdown("---")

# --- Introduction ---
st.markdown("""
Witamy w interaktywnym raporcie analitycznym!  
Aplikacja ta bada zjawiska **asymetrii informacji** i **bezrobocia strukturalnego** na współczesnym rynku pracy IT w Polsce.

Zamiast zgadywać, w jakim kierunku rozwijać karierę, opieramy się na twardych danych pozyskanych z tysięcy ogłoszeń o pracę.
""")

# --- Live market snapshot ---
st.markdown("### Rynek w liczbach")
try:
    db = DatabaseHandler()
    record_count = db.get_record_count()
    last_success = db.get_last_scrape_run(only_success=True)
    medians = {}
    for typ in ("B2B (netto)", "UoP (brutto)"):
        df_raw, _, _ = DatabaseHandler.get_cached_market_data(typ)
        salaries = df_raw["Srednia_Kwota"].dropna() if not df_raw.empty else df_raw
        medians[typ] = (salaries.median(), len(salaries)) if len(salaries) else (None, 0)
except Exception as e:
    st.warning(f"Nie udało się pobrać statystyk z bazy: {e}")
    record_count, last_success, medians = 0, None, {}

k1, k2, k3, k4 = st.columns(4)
k1.metric("Ofert w bazie", f"{record_count:,}".replace(",", " "))
k2.metric(
    "Ostatnia aktualizacja",
    last_success["finished_at"].astimezone(ZoneInfo("Europe/Warsaw")).strftime("%d.%m.%Y %H:%M")
    if last_success
    else "Brak",
)
for col, typ in ((k3, "B2B (netto)"), (k4, "UoP (brutto)")):
    median, n = medians.get(typ, (None, 0))
    col.metric(
        f"Mediana {typ}",
        f"{median:,.0f} PLN".replace(",", " ") if median else "-",
        delta=f"n = {n}",
        delta_color="off",
        delta_arrow="off",
        help="Środek widełek, wszystkie technologie i poziomy, oferty z podanymi widełkami.",
    )

st.markdown("### Moduły")
MODULES = [
    (
        "pages/2_Konkurencja.py",
        "Radar Błękitnych Oceanów",
        "Technologie o wysokich zarobkach i małej liczbie ofert - mapa nisz z przedziałami "
        "ufności i rozkładami wynagrodzeń.",
    ),
    (
        "pages/3_Regresja.py",
        "Weryfikacja Statystyczna",
        "Czy rynek płaci premię za rzadkie kompetencje? Korelacje, model OLS i statystyki "
        "opisowe.",
    ),
    (
        "pages/4_Kalkulator_ROI.py",
        "Kalkulator ROI",
        "Ile kosztuje przebranżowienie przez bootcamp i po jakim czasie się zwróci.",
    ),
    (
        "pages/6_Dla_Firm.py",
        "Dla Firm",
        "Benchmark wynagrodzeń, trudność rekrutacji, konkurencja o talenty i wskazówki do "
        "ogłoszenia.",
    ),
]
m_cols = st.columns(2)
for i, (page, title, description) in enumerate(MODULES):
    with m_cols[i % 2].container(border=True):
        st.markdown(f"**{title}**")
        st.caption(description)
        st.page_link(page, label="Otwórz", icon=":material/arrow_forward:")

# --- Academic Footer ---
st.markdown("---")
# Use st.caption for a subtle, grey text at the bottom instead of a prominent st.info block
st.caption("""
**Projekt zrealizowany w ramach przedmiotu Projekt Semestralny II i rozwijany w ramach Projekt Semestralny III.** **Zespół badawczy:** Dawid Krysa, Wojciech Pomarkiewicz, Wiktor Daniel, Krzysztof Krajewski
""")
