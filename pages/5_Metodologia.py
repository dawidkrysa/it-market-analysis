"""
Radar Mikro-nisz - Methodology and Data Management Page.

This Streamlit page handles data management operations for the application.
It provides functionalities to fetch job offers via web scraping from
portals like JustJoin.it, view raw records, and clear the database.
"""

import streamlit as st
import pandas as pd
from scrapers.scraper_manager import ScraperManager
from utils.db_handler import DatabaseHandler
import time

st.set_page_config(page_title="Zarządzanie Danymi", page_icon="⚙️", layout="wide")

st.title("⚙️ Ekstrakcja i Zarządzanie Danymi")
st.markdown("""
Ta sekcja to centrum dowodzenia silnika danych aplikacji **Radar Mikro-Nisz**. 
Pozwala na ręczne uruchamianie procesu web scrapingu, monitorowanie stanu bazy oraz podgląd surowych rekordów z rynkowych portali pracy.
""")

# --- Database Initialization ---
@st.cache_resource
def get_db_handler() -> DatabaseHandler:
    """
    Initialize and cache the database handler instance.

    Creates necessary database tables if they do not exist.

    Returns:
        DatabaseHandler: The cached database connection instance.
    """
    handler = DatabaseHandler()
    handler.create_tables()
    return handler

try:
    db_handler = get_db_handler()
    record_count = db_handler.get_record_count()
except Exception as e:
    st.error(f"❌ Nie można połączyć się z bazą danych: {e}")
    st.stop()

# --- Helper Function: Native Streamlit Modal Dialog ---
@st.dialog("⚠️ Potwierdzenie czyszczenia bazy")
def confirm_clear_database() -> None:
    """
    Render a modal dialog to confirm the database deletion operation.

    If confirmed, it clears all job records, sets a success message in the
    session state, and forces an app rerun.
    """
    st.error(f"Czy na pewno chcesz nieodwracalnie usunąć **{record_count} rekordów**?")
    st.markdown("Tej operacji nie można cofnąć.")

    col1, col2 = st.columns(2)
    if col1.button("Tak, usuń wszystko", type="primary", width="stretch"):
        try:
            deleted_count = db_handler.clear_database()
            st.session_state.action_msg = f"✅ Pomyślnie usunięto {deleted_count} rekordów!"
            st.rerun()
        except Exception as e:
            st.error(f"Błąd podczas czyszczenia bazy: {e}")

    if col2.button("Anuluj", width="stretch"):
        st.rerun()

# --- Display Global Success Messages ---
if "action_msg" in st.session_state:
    st.success(st.session_state.action_msg)
    del st.session_state.action_msg


# --- Tabs ---
tab_status, tab_fetch, tab_view, tab_clear = st.tabs([
    "📊 Status bazy",
    "⬇️ Pobieranie danych",
    "📋 Przeglądarka danych",
    "🗑️ Czyszczenie bazy"
])

# ==========================================
# TAB 1: Database Status
# ==========================================
with tab_status:
    st.subheader("Aktualny stan bazy danych")

    col1, col2, col3 = st.columns(3)
    col1.metric("Liczba zebranych ofert", f"{record_count:,}".replace(',', ' '))
    col2.metric("Status Bazy", "🟢 Aktywna" if record_count > 0 else "🔴 Pusta")
    col3.metric("Ostatnia aktualizacja", "Dziś" if record_count > 0 else "Brak")

    if record_count > 0:
        st.markdown("---")
        st.markdown("### Top 15 zeskrapowanych technologii ogółem")
        try:
            df = pd.DataFrame(db_handler.get_all_jobs())
            if not df.empty:
                # Extract and count the most frequently occurring technologies
                tech_counts = df['Technologie'].dropna().str.split(',').explode().str.strip().value_counts().head(15)
                st.bar_chart(tech_counts, color="#4e79a7")
        except Exception as e:
            st.error(f"Błąd generowania podsumowania: {e}")

# ==========================================
# TAB 2: Fetch Data (Scraping)
# ==========================================
with tab_fetch:
    st.subheader("Uruchom Web Scraper")
    st.markdown("Moduł pobiera najnowsze oferty pracy (poziom Junior) z połączonych portali ogłoszeniowych.")

    if st.button("🚀 Rozpocznij Scraping Danych", type="primary"):
        progress_bar = st.progress(0, text="Inicjalizacja scraperów...")
        status_box = st.info("Uruchamianie silnika...")

        try:
            manager = ScraperManager()

            # Simulated progress feedback
            progress_bar.progress(25, text="Nawiązywanie połączeń z portalami...")
            time.sleep(1) # Visual pause

            progress_bar.progress(50, text="Pobieranie i parsowanie ofert. To może potrwać kilka minut...")
            all_jobs = manager.run_all(experience_level="junior")

            progress_bar.progress(85, text="Zapisywanie do lokalnej bazy danych...")
            if all_jobs:
                saved_count = db_handler.save_jobs(all_jobs)
                st.session_state.action_msg = f"✅ Sukces! Pomyślnie zeskrapowano i zapisano {saved_count} nowych ofert."
            else:
                st.session_state.action_msg = "⚠️ Scraper zakończył pracę, ale nie znalazł nowych ofert pasujących do kryteriów."

            progress_bar.progress(100, text="Zakończono!")
            time.sleep(1)
            st.rerun()

        except Exception as e:
            progress_bar.empty()
            status_box.error(f"❌ Krytyczny błąd scrapera: {e}")

# ==========================================
# TAB 3: Data Viewer
# ==========================================
with tab_view:
    st.subheader("Eksplorator Surowych Danych")

    if record_count == 0:
        st.info("Baza danych jest pusta. Uruchom scraper w zakładce 'Pobieranie danych'.")
    else:
        @st.cache_data(ttl=60)
        def load_df() -> pd.DataFrame:
            """
            Load all job records from the database into a DataFrame.

            Results are cached for 60 seconds to optimize filtering performance.

            Returns:
                pd.DataFrame: A DataFrame containing all job records.
            """
            return pd.DataFrame(db_handler.get_all_jobs())

        df = load_df()

        # Column filters
        col1, col2 = st.columns(2)
        with col1:
            levels = ["Wszystkie"] + list(df['Poziom'].dropna().unique())
            level_filter = st.selectbox("Filtruj po poziomie (Seniority):", levels)

        with col2:
            all_techs = sorted(set(df['Technologie'].dropna().str.split(',').explode().str.strip()))
            tech_filter = st.multiselect("Wymagane technologie (AND):", all_techs, help="Pokaże tylko oferty zawierające wybrane technologie.")

        # Apply filters
        filtered_df = df.copy()
        if level_filter != "Wszystkie":
            filtered_df = filtered_df[filtered_df['Poziom'] == level_filter]

        if tech_filter:
            for tech in tech_filter:
                filtered_df = filtered_df[filtered_df['Technologie'].str.contains(tech, case=False, na=False)]

        # Render dataframe
        st.caption(f"Pokazano {len(filtered_df):,} z {record_count:,} całkowitych ofert w bazie.")
        st.dataframe(filtered_df, width="stretch", height=500, hide_index=True)

# ==========================================
# TAB 4: Clear Database
# ==========================================
with tab_clear:
    st.subheader("Opcje Administracyjne")

    st.error("""
    **⚠️ Strefa Niebezpieczna**
    Poniższa operacja usunie wszystkie zebrane oferty pracy z bazy. Zrób to tylko, jeśli:
    * Chcesz zebrać świeże dane z rynku (stare oferty wygasły).
    * Testujesz aplikację i chcesz wyczyścić bazę.
    """)

    # Trigger the native Streamlit modal dialog function
    if st.button("🗑️ Wyczyść całą bazę danych", type="primary", disabled=(record_count == 0)):
        confirm_clear_database()