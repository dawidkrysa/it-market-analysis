"""
Metodologia i Dane - Streamlit Page.

Strona do zarządzania danymi w aplikacji Radar Mikro-nisz.
Umożliwia pobieranie ofert pracy z JustJoin.it oraz czyszczenie bazy danych.
"""

import streamlit as st
import pandas as pd
from scrapers.scraper_manager import ScraperManager
from utils.db_handler import DatabaseHandler

st.title("⚙️ Metodologia i Ekstrakcja Danych")
st.markdown("""
Ta sekcja służy jako centrum dowodzenia dla silnika danych aplikacji **Radar Mikro-Nisz**. 
Pozwala na ręczne uruchamianie procesu web scrapingu, monitorowanie stanu bazy danych oraz podgląd surowych rekordów pozyskanych z rynkowych portali pracy.
""")

# Initialize database
db_handler = DatabaseHandler()
db_handler.create_tables()

# Get record count
try:
    record_count: int = db_handler.get_record_count()
except Exception as e:
    st.error("Nie można połączyć się z bazą danych.")
    st.exception(e)
    record_count = 0

# Display success messages
for msg_key in ["delete_success_message", "fetch_success_message"]:
    if msg_key in st.session_state:
        st.success(st.session_state[msg_key])
        del st.session_state[msg_key]

# Save the active tab in session state
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "📊 Status bazy"

# Tabs for better organization
tab_status, tab_fetch, tab_view, tab_clear = st.tabs(
    ["📊 Status bazy", "⬇️ Pobieranie danych", "📋 Wyświetlanie danych", "🗑️ Czyszczenie bazy"],
    key="tabs",
    on_change=lambda: st.session_state.update(active_tab=st.session_state.tabs)
)

# Restore the active tab after rerun
if st.session_state.active_tab == "📊 Status bazy":
    with tab_status:
        st.markdown("### Status bazy danych")
        col1, col2, col3 = st.columns(3)
        col1.metric("Liczba ofert", record_count)
        col2.metric("Status", "Aktywna" if record_count > 0 else "Pusta")
        if record_count > 0:
            col3.metric("Ostatnia aktualizacja", "Dziś")
        
        # Add a simple chart if data exists
        if record_count > 0:
            try:
                all_jobs = db_handler.get_all_jobs()
                df = pd.DataFrame(all_jobs)
                if not df.empty:
                    tech_counts = df['Technologie'].str.split(',').explode().value_counts().head(10)
                    st.bar_chart(tech_counts)
            except:
                pass

with tab_fetch:
    st.markdown("### Pobieranie danych")
    st.write("Pobierz najnowsze oferty pracy z portalów dla poziomu Junior.")
    
    # Obsługa pobierania danych z postępem przez session_state
    if st.button("Pobierz dane", type="primary", use_container_width=True):
        st.session_state.fetching = True
        st.rerun()

    if st.session_state.get("fetching", False):
        progress_bar = st.progress(0)
        status_text = st.empty()
        try:
            manager = ScraperManager()
            status_text.text("Pobieranie danych...")
            progress_bar.progress(40)
            all_jobs = manager.run_all(experience_level="junior")
            progress_bar.progress(80)
            status_text.text("Zapis do bazy danych...")
            if all_jobs:
                saved_count = db_handler.save_jobs(all_jobs)  # Pobranie liczby zapisanych ofert
                progress_bar.progress(100)
                st.session_state.fetch_success_message = f"Pomyślnie przetworzono i zapisano {saved_count} ofert!"
            else:
                st.warning("Nie znaleziono żadnych ofert do zapisania.")
            st.session_state.fetching = False
            st.rerun()
        except Exception as e:
            st.session_state.fetching = False
            st.error("Wystąpił błąd podczas pobierania danych.")
            st.exception(e)
        finally:
            progress_bar.empty()
            status_text.empty()

with tab_view:
    st.markdown("### Wyświetlanie surowych danych")
    st.write("Zobacz wszystkie oferty pracy w bazie danych.")
    
    if record_count == 0:
        st.info("Baza danych jest pusta. Pobierz dane najpierw.")
    else:
        with st.expander("Filtry i opcje", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                level_filter = st.selectbox("Filtruj po poziomie", ["Wszystkie"] + ["JUNIOR", "MID", "SENIOR", "TRAINEE"])
            with col2:
                tech_options = []
                try:
                    all_jobs = db_handler.get_all_jobs()
                    df = pd.DataFrame(all_jobs)
                    tech_options = sorted(set(df['Technologie'].str.split(',').explode().str.strip().dropna()))
                except:
                    pass
                tech_filter = st.multiselect("Filtruj po technologii", tech_options)
        
        if st.button("Pokaż dane", type="secondary", use_container_width=True):
            try:
                all_jobs = db_handler.get_all_jobs()
                df = pd.DataFrame(all_jobs)
                
                # Apply filters
                if level_filter != "Wszystkie":
                    df = df[df['Poziom'] == level_filter]
                if tech_filter:
                    df = df[df['Technologie'].str.contains('|'.join(tech_filter), na=False)]
                
                st.dataframe(df, use_container_width=True, height=400)
                st.caption(f"Pokazano {len(df)} ofert (z {record_count} całkowitych)")
            except Exception as e:
                st.error("Błąd podczas ładowania danych.")
                st.exception(e)

with tab_clear:
    st.markdown("### Czyszczenie bazy danych")
    
    with st.expander("Informacje o czyszczeniu bazy", expanded=False):
        st.warning("""
        **Uwaga:** Ta operacja usunie wszystkie dane z bazy danych i jest **nieodwracalna**.
        
        Użyj tej funkcji tylko wtedy, gdy:
        - Chcesz rozpocząć zbieranie danych od nowa
        - Dane w bazie są nieaktualne lub uszkodzone
        - Testujesz aplikację
        """)
    
    if st.button("Wyczyść bazę danych", type="secondary", disabled=record_count == 0, use_container_width=True):
        st.session_state.show_clear_dialog = True
        st.rerun()
    
    # Confirmation dialog
    if st.session_state.get("show_clear_dialog", False):
        st.error(f"### Potwierdzenie usunięcia")
        st.write(f"Czy na pewno chcesz usunąć **{record_count} rekordów**? Ta operacja jest nieodwracalna!")
        
        col1, col2 = st.columns(2)
        
        if col1.button("Tak, usuń wszystko", type="primary", use_container_width=True):
            try:
                deleted_count = db_handler.clear_database()
                st.session_state.show_clear_dialog = False
                st.session_state.delete_success_message = f"Pomyślnie usunięto {deleted_count} rekordów!"
                st.rerun()
            except Exception as e:
                st.session_state.show_clear_dialog = False
                st.error("Wystąpił błąd podczas czyszczenia bazy danych.")
                st.exception(e)
        
        if col2.button("Anuluj", use_container_width=True):
            st.session_state.show_clear_dialog = False
            st.rerun()
