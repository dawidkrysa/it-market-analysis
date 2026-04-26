"""
Radar Mikro-nisz - Main Streamlit Application.

Entry point for the multi-page Streamlit application analyzing the IT job market.
This module manages navigation, page routing, secure admin access,
and provides a global sidebar configuration.
"""

import streamlit as st
from utils.logging_config import setup_logging
from config.settings import Settings

# 1. GLOBAL CONFIGURATION (Ensure st.set_page_config is removed from all other files!)
st.set_page_config(
    page_title="Radar Mikro-Nisz IT",
    page_icon=":material/radar:", # Material Design icon
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state for admin access flag if it doesn't exist yet
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# Retrieve the admin key securely from settings without instantiating the class
ADMIN_KEY = Settings.ADMIN_KEY

# Initialize application logging
logger = setup_logging()

# --- PAGE DEFINITIONS WITH MATERIAL DESIGN ICONS ---
# Utilizing unified icons for a consistent and professional look across all devices
strona_glowna = st.Page("pages/1_Home.py", title="Strona Główna", icon=":material/home:")
strona_konkurencji = st.Page("pages/2_Konkurencja.py", title="Radar Błękitnych Oceanów", icon=":material/troubleshoot:")
strona_regresji = st.Page("pages/3_Regresja.py", title="Weryfikacja Statystyczna", icon=":material/analytics:")
strona_roi = st.Page("pages/4_Kalkulator_ROI.py", title="Kalkulator ROI", icon=":material/calculate:")
strona_metodologii = st.Page("pages/5_Metodologia.py", title="Silnik Danych", icon=":material/database:")

# --- NAVIGATION GROUPING ---
# Structured with business-oriented naming for the end-user
pages_dict =  {
    "Wprowadzenie": [strona_glowna],
    "Analiza Rynku": [strona_konkurencji, strona_regresji],
    "Decyzje Finansowe": [strona_roi],
}

def check_password() -> None:
    """
    Callback function to verify the entered admin access code.

    If the password matches the ADMIN_KEY, it grants admin privileges
    via session state and clears the input field. Otherwise, it displays an error.
    """
    if st.session_state["pwd_input"] == ADMIN_KEY:
        st.session_state.is_admin = True
        st.session_state.pwd_input = "" # Clear the input field upon successful authentication
    else:
        st.error("❌ Błędny kod dostępu")

# --- GLOBAL SIDEBAR ---
with st.sidebar:
    st.caption("🧭 **Radar Mikro-Nisz IT v1.0**")
    st.markdown("---")

    # Display the login expander only if the user is not authenticated
    if not st.session_state.is_admin:
        with st.expander("🔐 Panel Dostępu"):
            st.text_input(
                "Kod dostępu",
                type="password",
                key="pwd_input",
                on_change=check_password  # Callback triggers immediately after pressing Enter
            )
    else:
        # Display admin status and logout option
        st.success("🔓 Tryb Admina aktywny")
        if st.button("Wyloguj"):
            st.session_state.is_admin = False
            st.rerun()

    st.info("💡 Wybierz moduł z menu powyżej, aby rozpocząć analizę danych z rynku.")

    # Placeholder for potential global filters in the future (e.g., "Select City")

# Append the administration page to the navigation menu if the user is an admin
if st.session_state.is_admin:
    pages_dict["Administracja"] = [strona_metodologii]

# --- APP EXECUTION ---
# Initialize and run the application navigation routing
pg = st.navigation(pages_dict)
pg.run()