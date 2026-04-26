"""
Radar Mikro-nisz - Main Streamlit Application.

Multi-page Streamlit application for IT job market analysis.
Manages navigation, page routing, and provides a global sidebar config.
"""

import streamlit as st
from utils.logging_config import setup_logging
from config.settings import Settings

# 1. GLOBALNA KONFIGURACJA (Usuń st.set_page_config z innych plików!)
st.set_page_config(
    page_title="Radar Mikro-Nisz IT",
    page_icon=":material/radar:", # Ikona z Material Design
    layout="wide",
    initial_sidebar_state="expanded"
)

ADMIN_KEY = Settings().ADMIN_KEY

# Inicjalizacja logowania
logger = setup_logging()

# DEFINICJA STRON Z IKONAMI MATERIAL DESIGN
# Używamy ujednoliconych ikon, które wyglądają profesjonalnie na każdym urządzeniu
strona_glowna = st.Page("pages/1_Home.py", title="Strona Główna", icon=":material/home:")
strona_konkurencji = st.Page("pages/2_Konkurencja.py", title="Radar Błękitnych Oceanów", icon=":material/troubleshoot:")
strona_regresji = st.Page("pages/3_Regresja.py", title="Weryfikacja Statystyczna", icon=":material/analytics:")
strona_roi = st.Page("pages/4_Kalkulator_ROI.py", title="Kalkulator ROI", icon=":material/calculate:")
strona_metodologii = st.Page("pages/5_Metodologia.py", title="Silnik Danych", icon=":material/database:")

# GRUPOWANIE NAWIGACJI (Bardziej biznesowe nazewnictwo)
nav_structure = st.navigation(
    {
        "Wprowadzenie": [strona_glowna],
        "Analiza Rynku": [strona_konkurencji, strona_regresji],
        "Decyzje Finansowe": [strona_roi],
        "Administracja": [strona_metodologii]
    }
)

# GLOBALNY PASEK BOCZNY
with st.sidebar:
    st.caption("🧭 **Radar Mikro-Nisz IT v1.0**")
    st.markdown("---")

    with st.expander("🔐 Panel Dostępu"):
        access_code = st.text_input("Kod dostępu", type="password")

    if access_code == ADMIN_KEY:
        nav_structure["Administracja"] = [strona_metodologii]
        st.success("Tryb Admina: Aktywny")

    st.info("💡 Wybierz moduł z menu powyżej, aby rozpocząć analizę danych z rynku.")
    
    # Miejsce na ewentualne globalne filtry w przyszłości (np. "Wybierz Miasto")

# Uruchomienie aplikacji
pg = st.navigation(nav_structure)
pg.run()