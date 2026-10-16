"""
Radar Mikro-nisz - ROI Calculator Module.

This module provides an interactive Return on Investment (ROI) calculator
to help users evaluate the financial viability of learning specific IT
technologies via bootcamps based on living costs and expected salaries.
"""

from typing import Any

import pandas as pd
import streamlit as st

from utils.db_handler import SALARY_TYPE_COLUMNS, DatabaseHandler

# The ROI formulas below treat the suggested salary as a flat monthly figure,
# so only the two monthly-quoted salary types apply here -- hourly rates would
# need to be converted to a monthly equivalent first to stay meaningful.
ROI_SALARY_TYPES = [t for t in SALARY_TYPE_COLUMNS if t != "Stawka godzinowa"]


# --- Helper Functions for Data Cleaning ---


def clean_currency(val: Any) -> float:
    """
    Convert raw currency strings to a float value.

    Handles string formats such as '7136,26 PLN' and edge cases like 'No data'.

    Args:
        val (Any): The raw currency value to be cleaned.

    Returns:
        float: The cleaned currency value as a float, or 0.0 if the input is invalid.
    """
    val_str = str(val).strip()
    if pd.isna(val) or "Brak" in val_str or val_str == "":
        return 0.0

    # Remove 'PLN' and spaces, then replace the decimal comma with a dot
    cleaned = val_str.replace("PLN", "").replace(" ", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def clean_days(val: Any) -> float:
    """
    Convert duration strings representing days to a float value.

    Handles missing data and edge cases.

    Args:
        val (Any): The raw duration value to be cleaned.

    Returns:
        float: The cleaned duration value as a float, or 0.0 if the input is invalid.
    """
    val_str = str(val).strip()
    if pd.isna(val) or "Brak" in val_str or val_str == "":
        return 0.0

    try:
        return float(val_str.replace(",", "."))
    except ValueError:
        return 0.0


# --- Step 1 & 2: Loading and Preparing Data ---


@st.cache_data
def load_market_data(typ_wynagrodzenia: str) -> pd.DataFrame:
    """
    Fetch aggregated market data from the database.

    Args:
        typ_wynagrodzenia (str): Which salary type to suggest earnings from
            (one of `ROI_SALARY_TYPES`). Cached separately per type.

    Returns:
        pd.DataFrame: A DataFrame containing blue ocean niche market data.
    """
    db = DatabaseHandler()
    df_niche = db.get_blue_ocean_niches(
        min_jobs=5, max_jobs=1000, typ_wynagrodzenia=typ_wynagrodzenia
    )
    return df_niche


@st.cache_data
def load_data() -> pd.DataFrame:
    """
    Load bootcamp data from the database.

    Returns:
        pd.DataFrame: Bootcamp cost/duration data. If the database table is
        missing, an empty DataFrame with the expected schema is returned.
    """
    db = DatabaseHandler()

    try:
        df_bootcamp = pd.read_sql_table("bootcamp_data", con=db.engine)
    except ValueError:
        st.warning(
            "Nie znaleziono tabeli 'bootcamp_data' w bazie danych. Proszę uruchomić notatnik ładujący dane."
        )
        df_bootcamp = pd.DataFrame(
            columns=[
                "Technologia",
                "Średni Koszt",
                "Mediana Kosztu",
                "Średni Czas (dni)",
                "Mediana Czasu (dni)",
            ]
        )
    except Exception as e:
        st.error(f"Błąd podczas czytania danych bootcampów z bazy: {e}")
        df_bootcamp = pd.DataFrame(
            columns=[
                "Technologia",
                "Średni Koszt",
                "Mediana Kosztu",
                "Średni Czas (dni)",
                "Mediana Czasu (dni)",
            ]
        )

    return df_bootcamp


df_bootcamp = load_data()

# --- Visual Layout ---

# Create a container to force the calculator to render at the top of the page
calc_container = st.container()

typ_wynagrodzenia = calc_container.selectbox(
    "Typ wynagrodzenia dla sugerowanych zarobków:",
    options=ROI_SALARY_TYPES,
    index=ROI_SALARY_TYPES.index("B2B (netto)"),
    help="Stawka godzinowa nie jest tu dostępna - kalkulator liczy w okresach miesięcznych.",
)
df_market = load_market_data(typ_wynagrodzenia)

st.divider()

# Create an expander section for editable data tables at the bottom
tables_expander = st.expander("📋 Edytuj dane źródłowe (Bootcampy)")

with tables_expander:
    # Render interactive data editor
    st.header("Dane Bootcampów (Edytowalne)")
    st.caption(
        "Kliknij dwukrotnie komórkę, aby zmienić jej wartość. Zmiany zaktualizują obliczenia w czasie rzeczywistym."
    )
    edited_df_bootcamp = st.data_editor(
        df_bootcamp, num_rows="dynamic", width="stretch", key="bootcamp_editor"
    )

# --- Calculator Engine (Rendered in the top container) ---

with calc_container:
    st.header("Kalkulator ROI (Zwrotu z Inwestycji) 💰")

    # User input parameters for ROI calculation
    col1, col2 = st.columns(2)
    with col1:
        czas_szukania_pracy_msc = st.number_input(
            "Czas szukania pracy (w miesiącach):", min_value=0.0, value=3.0, step=0.5
        )

        bootcamp_techs = (
            [] if edited_df_bootcamp.empty else edited_df_bootcamp["Technologia"].unique()
        )
        wybrana_technologia = st.selectbox("Wybierz technologię (Bootcamp):", bootcamp_techs)
    with col2:
        czas_przepracowany_msc = st.number_input(
            "Czas zatrudnienia i zarabiania (w miesiącach):", min_value=0.0, value=12.0, step=1.0
        )

        koszt_zycia_msc = st.number_input(
            "Twój miesięczny koszt życia (PLN):",
            min_value=0.0,
            value=3000.0,
            step=100.0,
            key="koszt_zycia_msc_input",
            help=(
                "Wpisz swój własny, indywidualny koszt utrzymania zamiast szacunku dla miasta "
                "- wartość zostaje zapamiętana do końca tej sesji przeglądarki."
            ),
        )

    # Suggest expected earnings based on market data median
    sugerowane_zarobki = 6000.0
    if (
        not df_market.empty
        and wybrana_technologia
        and wybrana_technologia.lower() in df_market["Technologia_Pojedyncza"].str.lower().values
    ):
        sugerowane_zarobki = df_market[
            df_market["Technologia_Pojedyncza"].str.lower() == wybrana_technologia.lower()
        ]["Mediana_Zarobkow"].iloc[0]

    szacowane_zarobki = st.number_input(
        f"Szacowane miesięczne zarobki ({typ_wynagrodzenia}) dla: "
        f"{wybrana_technologia if wybrana_technologia else 'wybranej technologii'} (PLN):",
        min_value=0.0,
        value=float(sugerowane_zarobki),
        step=500.0,
        help="Domyślna wartość opiera się na medianie zarobków w bazie danych dla tej konkretnej technologii.",
    )

    # Retrieve and clean selected data values
    try:
        if wybrana_technologia:
            # Retrieve bootcamp education costs and duration
            wiersz_bootcamp = edited_df_bootcamp[
                edited_df_bootcamp["Technologia"] == wybrana_technologia
            ].iloc[0]
            koszt_bootcampu = clean_currency(wiersz_bootcamp["Mediana Kosztu"])
            czas_edukacji_dni = clean_days(wiersz_bootcamp["Mediana Czasu (dni)"])
            czas_edukacji_msc = (
                czas_edukacji_dni / 30.0
            )  # Convert days to months (assuming 30 days/month)

            # ---------------------------------------------------------
            # Calculation Formulas
            # ---------------------------------------------------------

            # Cost of living during the transition period (education + job search)
            koszt_utrzymania_okres_przejsciowy = koszt_zycia_msc * (
                czas_edukacji_msc + czas_szukania_pracy_msc
            )

            # Total investment cost calculation
            calkowity_koszt = koszt_bootcampu + koszt_utrzymania_okres_przejsciowy

            # Total projected revenue
            calkowity_przychod = czas_przepracowany_msc * szacowane_zarobki

            # Final financial balance
            bilans = calkowity_przychod - calkowity_koszt

            # Break-even point in months
            miesiace_do_zwrotu = (
                calkowity_koszt / szacowane_zarobki if szacowane_zarobki > 0 else float("inf")
            )

            # ---------------------------------------------------------

            # --- Results Presentation ---
            st.markdown("### Wyniki Kalkulacji")
            st.info(
                f"**Wymagany budżet początkowy:** Koszt edukacji ({koszt_bootcampu:.2f} PLN) "
                f"+ Koszty życia w trakcie nauki i szukania pracy ({koszt_utrzymania_okres_przejsciowy:.2f} PLN)."
            )

            mcol1, mcol2, mcol3 = st.columns(3)
            with mcol1:
                st.metric(
                    "Inwestycja (Koszty ogółem)", f"{calkowity_koszt:,.2f} PLN".replace(",", " ")
                )
            with mcol2:
                st.metric(
                    f"Przychód ({czas_przepracowany_msc:.0f} mies.)",
                    f"{calkowity_przychod:,.2f} PLN".replace(",", " "),
                )
            with mcol3:
                # Display visual profitability indicator via Streamlit's metric delta
                st.metric(
                    "Bilans po ustalonym czasie",
                    f"{bilans:,.2f} PLN".replace(",", " "),
                    delta=f"{bilans:,.2f} PLN",
                )

            st.subheader("Czas Zwrotu z Inwestycji (ROI)")
            if miesiace_do_zwrotu <= czas_przepracowany_msc:
                st.success(
                    f"Inwestycja całkowicie się zwróci po około **{miesiace_do_zwrotu:.1f}** miesiącach pracy na nowym stanowisku."
                )
            else:
                st.warning(
                    f"Inwestycja zwróci się po około **{miesiace_do_zwrotu:.1f}** miesiącach (to wykracza poza zakres wybranej przez Ciebie symulacji)."
                )
        else:
            st.info(
                "Niewystarczające dane do wykonania obliczeń. Upewnij się, że baza danych jest zaktualizowana."
            )

    except Exception as e:
        st.warning(
            "Upewnij się, że tabela bootcampów zawiera poprawne wartości dla wybranej technologii."
        )
        st.error(f"Szczegóły błędu: {e}")
