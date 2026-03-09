import streamlit as st
import pandas as pd
from utils.job_pages import NoFluffJobs, ApiError

st.set_page_config(page_title="Rynek i Konkurencja", page_icon="🌊")

if st.button("Pobierz dane z NoFluffjobs"):

    with st.spinner(text="Trwa pobieranie...", show_time=False, width="content"):
        try:
            # Określamy typ result jako klasę NoFluffJobs
            result: NoFluffJobs = NoFluffJobs(pages_to_fetch=10)
            
            # Tworzenie DataFrame musi być tutaj, żeby wykonało się 
            # TYLKO gdy pobieranie zakończy się sukcesem!
            df: pd.DataFrame = pd.DataFrame(result.getData())

            st.success(f"Pomyślnie przetworzono {len(df)} ofert!")
            
            # Wyświetlamy interaktywną tabelę w Streamlit
            st.dataframe(df, use_container_width=True) # type: ignore

        except ApiError as e:
            st.error(f"Kod błędu: {e.error_code}")
            st.write(e.message)
        except Exception as e:
            # Warto też złapać inne nieoczekiwane błędy (np. brak internetu)
            st.error("Wystąpił nieoczekiwany błąd podczas pobierania danych.")
            st.write(str(e))