"""
Radar Mikro-nisz - Main Streamlit Page.

Strona domowa aplikacji Streamlit, która wyświetla szczegóły dot. projektu
oraz wprowadzenie do analizy rynku pracy IT.
"""

import streamlit as st

# Konfiguracja strony (powinna być zawsze na samej górze pliku wejściowego)
st.set_page_config(
    page_title="Radar Mikro-Nisz IT",
    page_icon="🧭",
    layout="wide"
)

# --- Nagłówek i Logo ---
col1, col2 = st.columns([4, 1], vertical_alignment="center")

with col1:
    # Dodano główny, krótki tytuł i przeniesiono długi tytuł akademicki do subheadera
    st.title("🧭 Radar Mikro-Nisz IT")
    st.subheader("Wpływ niszowości technologii na opłacalność i czas zatrudnienia")

with col2:
    try:
        st.image("assets/wsb_logo.png", width=150)
    except:
        st.caption("[Logo Uczelni]") # Zabezpieczenie, jeśli ścieżka do pliku nie zadziała

st.markdown("---")

# --- Wprowadzenie ---
st.markdown("""
Witamy w interaktywnym raporcie analitycznym!  
Aplikacja ta bada zjawiska **asymetrii informacji** i **bezrobocia strukturalnego** na współczesnym rynku pracy IT w Polsce.

Zamiast zgadywać, w jakim kierunku rozwijać karierę, opieramy się na twardych danych pozyskanych z tysięcy ogłoszeń o pracę.
""")

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("### 📌 Czego dowiesz się z tej aplikacji?")

# --- Karty nawigacyjne (Feature Cards) zamiast zwykłej listy ---
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

# --- Stopka Akademicka ---
st.markdown("---")
# Używamy st.caption dla szarego, dyskretnego tekstu na dole strony zamiast krzyczących niebieskich st.info
st.caption("""
**Projekt zrealizowany w ramach przedmiotu Projekt Semestralny II.** 👨‍💻 **Zespół badawczy:** Dawid Krysa, Wojciech Pomarkiewicz, Wiktor Daniel, Krzysztof Krajewski
""")