"""Radar Mikro-nisz - Main Streamlit Application.

Multi-page Streamlit application for IT job market analysis.
Manages navigation, page routing, and provides a sidebar for project configuration.
"""

from logging import Logger
import streamlit as st
import platform

from streamlit.navigation.page import StreamlitPage
from utils.logging_config import setup_logging

st.set_page_config(
    page_title="Analiza Rynku IT: Nisze vs Mainstream",
)

logger: Logger = setup_logging()

strona_glowna: StreamlitPage = st.Page("pages/1_Home.py", title="Strona Główna", icon="🏠")
strona_konkurencji: StreamlitPage = st.Page("pages/2_Konkurencja.py", title="Popyt i Podaż (Nisze)", icon="🌊")
strona_regresji: StreamlitPage = st.Page("pages/3_Regresja.py", title="Weryfikacja Statystyczna", icon="📊")
strona_roi: StreamlitPage = st.Page("pages/4_Kalkulator_ROI.py", title="Kalkulator Opłacalności", icon="📈")
strona_metodologii: StreamlitPage = st.Page("pages/5_Metodologia.py", title="Metodologia i Dane", icon="⚙️")

pg: StreamlitPage = st.navigation(
    {
        "Wprowadzenie": [strona_glowna],
        "Ekonometria i Rynek": [strona_konkurencji, strona_regresji],
        "Finanse": [strona_roi],
        "Metodologia": [strona_metodologii]
    }
)

with st.sidebar:
    st.header("Konfiguracja")
    st.caption(f"Środowisko: Python {platform.python_version()}")

pg.run()