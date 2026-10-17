"""
Radar Mikro-nisz - Methodology and Data Management Page.

This Streamlit page handles data management operations for the application.
It provides functionalities to fetch job offers via web scraping from
portals like JustJoin.it, view raw records, and clear the database.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from config.settings import Settings
from scrapers.scrape_job import run_scrape_job
from utils.charts import palette
from utils.db_handler import DatabaseHandler

LOCAL_TZ = ZoneInfo("Europe/Warsaw")


def format_local(ts: datetime) -> str:
    """Format a UTC timestamp in Polish local time, e.g. "17.10.2026 09:30"."""
    return ts.astimezone(LOCAL_TZ).strftime("%d.%m.%Y %H:%M")

st.set_page_config(page_title="Zarządzanie Danymi", page_icon=":material/database:", layout="wide")

st.title("Ekstrakcja i Zarządzanie Danymi")
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
    st.error(f"Nie można połączyć się z bazą danych: {e}")
    st.stop()


# --- Helper Function: Native Streamlit Modal Dialog ---
@st.dialog("Potwierdzenie czyszczenia bazy")
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
            st.session_state.action_msg = f"Pomyślnie usunięto {deleted_count} rekordów!"
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
tab_status, tab_fetch, tab_view, tab_bootcamps, tab_clear = st.tabs(
    [
        "Status bazy",
        "Pobieranie danych",
        "Przeglądarka danych",
        "Bootcampy",
        "Czyszczenie bazy",
    ]
)

# ==========================================
# TAB 1: Database Status
# ==========================================
with tab_status:
    st.subheader("Aktualny stan bazy danych")

    last_run = db_handler.get_last_scrape_run()
    last_success = db_handler.get_last_scrape_run(only_success=True)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Liczba zebranych ofert", f"{record_count:,}".replace(",", " "))
    col2.metric("Status Bazy", "Aktywna" if record_count > 0 else "Pusta")
    col3.metric(
        "Ostatnia aktualizacja",
        format_local(last_success["finished_at"]) if last_success else "Brak",
        help="Ostatni udany scraping (automatyczny lub ręczny).",
    )
    if Settings.SCRAPE_INTERVAL_HOURS > 0:
        next_run = (
            last_success["finished_at"] + timedelta(hours=Settings.SCRAPE_INTERVAL_HOURS)
            if last_success
            else None
        )
        col4.metric(
            "Następny automatyczny scraping",
            format_local(next_run) if next_run else "Wkrótce",
            help=f"Co {Settings.SCRAPE_INTERVAL_HOURS:g} h (zmienna SCRAPE_INTERVAL_HOURS).",
        )
    else:
        col4.metric("Automatyczny scraping", "Wyłączony")

    if last_run and last_run["status"] == "running":
        st.info(
            f"Scraping w toku ({'automatyczny' if last_run['trigger'] == 'auto' else 'ręczny'}),"
            f" rozpoczęty {format_local(last_run['started_at'])}."
        )
    elif last_run and last_run["status"] == "failed":
        st.warning(
            f"Ostatni scraping ({format_local(last_run['started_at'])}) zakończył się błędem: "
            f"{last_run['error']}"
        )

    if record_count > 0:
        st.markdown("---")
        st.markdown("### Top 15 zeskrapowanych technologii ogółem")
        try:
            df = pd.DataFrame(db_handler.get_all_jobs())
            if not df.empty:
                # Extract and count the most frequently occurring technologies
                tech_counts = (
                    df["Technologie"]
                    .dropna()
                    .str.split(",")
                    .explode()
                    .str.strip()
                    .value_counts()
                    .head(15)
                )
                st.bar_chart(tech_counts, color=palette().accent)
        except Exception as e:
            st.error(f"Błąd generowania podsumowania: {e}")

# ==========================================
# TAB 2: Fetch Data (Scraping)
# ==========================================
with tab_fetch:
    st.subheader("Uruchom Web Scraper")
    st.markdown(
        "Moduł pobiera najnowsze oferty pracy z połączonych portali ogłoszeniowych, "
        "dla wybranych poziomów doświadczenia."
    )

    level_labels = {
        "Trainee": "trainee",
        "Junior": "junior",
        "Mid": "mid",
        "Senior": "senior",
    }
    selected_labels = st.multiselect(
        "Poziomy doświadczenia do pobrania:",
        options=list(level_labels.keys()),
        default=["Junior", "Mid", "Senior"],
    )

    if st.button("Rozpocznij Scraping Danych", type="primary", disabled=not selected_labels):
        experience_levels = ",".join(level_labels[label] for label in selected_labels)
        with st.spinner("Pobieranie i zapisywanie ofert. To może potrwać kilka minut..."):
            result = run_scrape_job("manual", experience_levels)

        if result.status == "success":
            st.session_state.action_msg = (
                f"Sukces! Pobrano i zapisano {result.saved_count} ofert."
            )
            st.rerun()
        elif result.status == "skipped":
            st.warning(
                "Inny scraping (np. automatyczny) jest właśnie w toku. Spróbuj ponownie później."
            )
        else:
            st.error(f"Krytyczny błąd scrapera: {result.error}")

# ==========================================
# TAB 3: Data Viewer
# ==========================================
with tab_view:
    st.subheader("Eksplorator Surowych Danych")

    if record_count == 0:
        st.info("Baza danych jest pusta. Uruchom scraper w zakładce 'Pobieranie danych'.")
    else:

        @st.cache_data(ttl=60, show_spinner=False)
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
            levels = ["Wszystkie"] + list(df["Poziom"].dropna().unique())
            level_filter = st.selectbox("Filtruj po poziomie (Seniority):", levels)

        with col2:
            all_techs = sorted(set(df["Technologie"].dropna().str.split(",").explode().str.strip()))
            tech_filter = st.multiselect(
                "Wymagane technologie (AND):",
                all_techs,
                help="Pokaże tylko oferty zawierające wybrane technologie.",
            )

        # Apply filters
        filtered_df = df.copy()
        if level_filter != "Wszystkie":
            filtered_df = filtered_df[filtered_df["Poziom"] == level_filter]

        if tech_filter:
            for tech in tech_filter:
                filtered_df = filtered_df[
                    filtered_df["Technologie"].str.contains(tech, case=False, na=False)
                ]

        # Render dataframe
        st.caption(f"Pokazano {len(filtered_df):,} z {record_count:,} całkowitych ofert w bazie.")
        st.dataframe(filtered_df, width="stretch", height=500, hide_index=True)

# ==========================================
# TAB 4: Bootcamp Management
# ==========================================
with tab_bootcamps:
    st.subheader("Katalog Bootcampów")
    st.markdown(
        "Dane kosztów i czasu trwania bootcampów używane przez **Kalkulator ROI**. "
        "Edytuj ręcznie poniżej albo wgraj plik, żeby zastąpić lub uzupełnić katalog."
    )

    with st.expander("Import z pliku (CSV / XLSX)"):
        uploaded_file = st.file_uploader(
            "Plik z kolumnami: Technologia, Średni Koszt, Mediana Kosztu, "
            "Średni Czas (dni), Mediana Czasu (dni)",
            type=["csv", "xlsx"],
        )
        dolacz_do_istniejacych = st.checkbox(
            "Dołącz do istniejących danych (zamiast je nadpisać)", value=False
        )

        if uploaded_file is not None and st.button("Importuj plik"):
            try:
                if uploaded_file.name.lower().endswith(".xlsx"):
                    df_import = pd.read_excel(uploaded_file)
                else:
                    df_import = pd.read_csv(uploaded_file)

                missing_cols = {"Technologia"} - set(df_import.columns)
                if missing_cols:
                    st.error(f"Brakuje wymaganej kolumny: {', '.join(missing_cols)}")
                else:
                    if dolacz_do_istniejacych:
                        df_import = pd.concat(
                            [db_handler.get_bootcamps(), df_import], ignore_index=True
                        )
                    saved_count = db_handler.save_bootcamps(df_import)
                    st.session_state.action_msg = (
                        f"Zaimportowano i zapisano {saved_count} wierszy bootcampów."
                    )
                    st.rerun()
            except Exception as e:
                st.error(f"Błąd importu pliku: {e}")

    st.markdown("---")
    st.markdown("### Edytuj ręcznie")
    st.caption(
        "Kliknij dwukrotnie komórkę, aby zmienić jej wartość. Dodawaj/usuwaj wiersze "
        "paskiem narzędzi tabeli, a na końcu zapisz zmiany."
    )

    df_bootcamps_admin = db_handler.get_bootcamps()
    edited_bootcamps = st.data_editor(
        df_bootcamps_admin.drop(columns=["ID"], errors="ignore"),
        num_rows="dynamic",
        width="stretch",
        key="bootcamp_admin_editor",
    )

    if st.button("Zapisz zmiany", type="primary"):
        try:
            saved_count = db_handler.save_bootcamps(edited_bootcamps)
            st.session_state.action_msg = f"Zapisano {saved_count} wierszy bootcampów."
            st.rerun()
        except Exception as e:
            st.error(f"Błąd zapisu: {e}")

# ==========================================
# TAB 5: Clear Database
# ==========================================
with tab_clear:
    st.subheader("Opcje Administracyjne")

    st.error("""
    **Strefa Niebezpieczna**
    Poniższa operacja usunie wszystkie zebrane oferty pracy z bazy. Zrób to tylko, jeśli:
    * Chcesz zebrać świeże dane z rynku (stare oferty wygasły).
    * Testujesz aplikację i chcesz wyczyścić bazę.
    """)

    # Trigger the native Streamlit modal dialog function
    if st.button("Wyczyść całą bazę danych", type="primary", disabled=(record_count == 0)):
        confirm_clear_database()
