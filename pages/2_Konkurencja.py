"""Streamlit page for scraping and displaying NoFluffJobs data."""

import streamlit as st
import pandas as pd
from utils.job_pages import NoFluffJobCollector

st.set_page_config(page_title="Rynek i Konkurencja", page_icon="🌊")

if st.button("Pobierz dane z NoFluffjobs"):

    with st.spinner(text="Trwa pobieranie...", show_time=False, width="content"):
        try:
            result: NoFluffJobCollector = NoFluffJobCollector(pages_to_fetch=15)
            
            df: pd.DataFrame = pd.DataFrame(result.getData())

            st.success(f"Pomyślnie przetworzono i zapisano {len(df)} ofert do bazy danych!")
            
            st.dataframe(df, width="stretch") # type: ignore

        except Exception as e:
            st.error("Wystąpił nieoczekiwany błąd podczas pobierania danych.")
            st.write(str(e))