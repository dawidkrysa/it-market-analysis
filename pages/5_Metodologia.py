"""
Metodologia i Dane - Streamlit Page.

Strona do zarządzania danymi w aplikacji Radar Mikro-nisz.
Umożliwia pobieranie ofert pracy z JustJoin.it oraz czyszczenie bazy danych.
"""

import streamlit as st
import pandas as pd
from utils.job_pages import JustJoinIT
from utils.db_handler import DatabaseHandler

st.title("Metodologia i Dane")

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

# Database status
st.markdown("### Status bazy danych")
col1, col2, col3 = st.columns(3)
col1.metric("Liczba ofert", record_count)
col2.metric("Status", "Aktywna" if record_count > 0 else "Pusta")
if record_count > 0:
    col3.metric("Ostatnia aktualizacja", "Dziś")

st.divider()

# Data fetching
st.markdown("### Pobieranie danych")
st.write("Pobierz najnowsze oferty pracy z portalu **JustJoin.it** dla poziomu Junior.")

if st.button("Pobierz dane", type="primary", use_container_width=True):
    with st.spinner("Trwa pobieranie danych z JustJoin.it..."):
        try:
            jji_result: JustJoinIT = JustJoinIT(experience_levels="junior")
            jji_df: pd.DataFrame = pd.DataFrame(jji_result.getData())
            st.session_state.fetch_success_message = f"Pomyślnie przetworzono i zapisano {len(jji_df)} ofert!"
            st.rerun()
        except Exception as e:
            st.error("Wystąpił błąd podczas pobierania danych.")
            st.exception(e)

st.divider()

# Database clearing
st.markdown("### Czyszczenie bazy danych")

with st.expander("Informacje o czyszczeniu bazy"):
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
    st.markdown("---")
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
