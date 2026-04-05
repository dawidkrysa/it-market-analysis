"""
Radar Mikro-nisz - Main Streamlit Application.

Multi-page Streamlit application for IT job market analysis.
Manages navigation, page routing, and provides a global sidebar config.
"""

import streamlit as st
from utils.logging_config import setup_logging

# 1. GLOBALNA KONFIGURACJA (Usuń st.set_page_config z innych plików!)
st.set_page_config(
    page_title="Radar Mikro-Nisz IT",
    page_icon=":material/radar:", # Ikona z Material Design
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicjalizacja logowania
logger = setup_logging()

# 2. DEFINICJA STRON Z IKONAMI MATERIAL DESIGN
# Używamy ujednoliconych ikon, które wyglądają profesjonalnie na każdym urządzeniu
strona_glowna = st.Page("pages/1_Home.py", title="Strona Główna", icon=":material/home:")
strona_konkurencji = st.Page("pages/2_Konkurencja.py", title="Radar Błękitnych Oceanów", icon=":material/troubleshoot:")
strona_regresji = st.Page("pages/3_Regresja.py", title="Weryfikacja Statystyczna", icon=":material/analytics:")
strona_roi = st.Page("pages/4_Kalkulator_ROI.py", title="Kalkulator ROI", icon=":material/calculate:")
strona_metodologii = st.Page("pages/5_Metodologia.py", title="Silnik Danych", icon=":material/database:")

# 3. GRUPOWANIE NAWIGACJI (Bardziej biznesowe nazewnictwo)
pg = st.navigation(
    {
        "Wprowadzenie": [strona_glowna],
        "Analiza Rynku": [strona_konkurencji, strona_regresji],
        "Decyzje Finansowe": [strona_roi],
        "Administracja": [strona_metodologii]
    }
)

# 4. GLOBALNY PASEK BOCZNY
with st.sidebar:
    st.caption("🧭 **Radar Mikro-Nisz IT v1.0**")
    st.markdown("---")
    st.info("💡 Wybierz moduł z menu powyżej, aby rozpocząć analizę danych z rynku.")
    
    # Miejsce na ewentualne globalne filtry w przyszłości (np. "Wybierz Miasto")

# Uruchomienie aplikacji
pg.run()