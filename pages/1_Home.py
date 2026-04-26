"""
Radar Mikro-nisz - Main Streamlit Page.

The home page of the Streamlit application displaying project details
and an introduction to the IT job market analysis.
"""

import streamlit as st

# Page configuration (must always be the first Streamlit command in the entry file)
st.set_page_config(
    page_title="Radar Mikro-Nisz IT",
    page_icon="🧭",
    layout="wide"
)

# --- Header and Logo ---
col1, col2 = st.columns([4, 1], vertical_alignment="center")

with col1:
    # Added a main, short title and moved the long academic title to the subheader
    st.title("🧭 Radar Mikro-Nisz IT")
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

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("### 📌 Czego dowiesz się z tej aplikacji?")

# --- Feature Cards (instead of a standard list) ---
f_col1, f_col2 = st.columns(2)

with f_col1:
    st.info("""
    **🌊 Strategia Błękitnego Oceanu** Identyfikacja technologii o wysokim popycie i niskiej podaży kandydatów. Odróżniamy rynkowe nisze od przesyconych 'Czerwonych Oceanów'.
    """)
    st.success("""
    **📈 Weryfikacja Hipotez (Korelacje)** Statystyczne sprawdzenie z użyciem testów Spearmana/Kendalla, czy za rzadkie kompetencje rynek faktycznie płaci premię.
    """)

with f_col2:
    st.warning("""
    **💰 Analiza Finansowa (ROI)** Kalkulacja twardego zwrotu z inwestycji w naukę konkretnych technologii. Ile kosztuje Cię utracony czas na naukę?
    """)
    st.error("""
    **⚙️ Metodologia i Dane** Centrum dowodzenia silnikiem aplikacji. Podgląd na żywo do bazy danych oraz możliwość uruchomienia web scraperów.
    """)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("👈 **Wybierz interesującą Cię sekcję z menu bocznego, aby rozpocząć.**")

# --- Academic Footer ---
st.markdown("---")
# Use st.caption for a subtle, grey text at the bottom instead of a prominent st.info block
st.caption("""
**Projekt zrealizowany w ramach przedmiotu Projekt Semestralny II.** 👨‍💻 **Zespół badawczy:** Dawid Krysa, Wojciech Pomarkiewicz, Wiktor Daniel, Krzysztof Krajewski
""")