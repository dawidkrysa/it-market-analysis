import streamlit as st
import pandas as pd
from utils.db_handler import DatabaseHandler

# --- Helper functions for data cleaning ---
def clean_currency(val):
    """Converts strings like '7136,26 PLN' to float 7136.26. Handles 'No data' cases."""
    val_str = str(val).strip()
    if pd.isna(val) or "Brak" in val_str or val_str == "":
        return 0.0
    # Removes 'PLN', spaces and replaces comma with dot
    cleaned = val_str.replace("PLN", "").replace(" ", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0

def clean_days(val):
    """Converts days to float. Handles 'No data' cases."""
    val_str = str(val).strip()
    if pd.isna(val) or "Brak" in val_str or val_str == "":
        return 0.0
    try:
        return float(val_str.replace(",", "."))
    except ValueError:
        return 0.0

# --- STEP 1 & 2: Loading and preparing data ---
@st.cache_data
def load_market_data():
    """Fetches aggregated market data from the database."""
    db = DatabaseHandler()
    df_niche = db.get_blue_ocean_niches(min_jobs=5, max_jobs=1000)
    return df_niche

@st.cache_data
def load_data():
    db = DatabaseHandler()

    # 1. Bootcamp data from DB
    try:
        df_bootcamp = pd.read_sql_table('bootcamp_data', con=db.engine)
    except ValueError:
        st.warning("Nie znaleziono tabeli 'bootcamp_data' w bazie danych. Proszę uruchomić notatnik ładujący dane.")
        df_bootcamp = pd.DataFrame(columns=[
            "Technologia", "Średni Koszt", "Mediana Kosztu",
            "Średni Czas (dni)", "Mediana Czasu (dni)"
        ])
    except Exception as e:
        st.error(f"Błąd podczas czytania danych bootcampów z bazy: {e}")
        df_bootcamp = pd.DataFrame(columns=[
            "Technologia", "Średni Koszt", "Mediana Kosztu",
            "Średni Czas (dni)", "Mediana Czasu (dni)"
        ])

    # 2. Living costs data from DB
    try:
        df_koszty = pd.read_sql_table('living_costs_data', con=db.engine)
    except ValueError:
        st.warning("Nie znaleziono tabeli 'living_costs_data' w bazie danych. Proszę uruchomić notatnik ładujący dane.")
        df_koszty = pd.DataFrame(columns=[
            "Województwo", "Miasto", "Średni koszt życia / utrzymania",
            "Średni czas szukania pracy (dn)"
        ])
    except Exception as e:
        st.error(f"Błąd podczas czytania danych kosztów życia z bazy: {e}")
        df_koszty = pd.DataFrame(columns=[
            "Województwo", "Miasto", "Średni koszt życia / utrzymania",
            "Średni czas szukania pracy (dn)"
        ])

    return df_bootcamp, df_koszty

df_bootcamp, df_koszty = load_data()
df_market = load_market_data()

# --- VISUAL LAYOUT ---
# Create a container for the calculator to force it to appear at the TOP of the page
calc_container = st.container()

st.divider()

# Create an expander section for tables at the BOTTOM of the page
tables_expander = st.expander("📋 Edytuj dane źródłowe (Koszty życia i Bootcampy)")

with tables_expander:
    # Display and edit tables
    st.header("1. Dane Bootcampów (Edytowalne)")
    st.caption("Kliknij dwukrotnie komórkę, aby zmienić jej wartość. Zmiany zaktualizują obliczenia w czasie rzeczywistym.")
    edited_df_bootcamp = st.data_editor(df_bootcamp, num_rows="dynamic", width="stretch", key="bootcamp_editor")

    st.header("2. Koszty życia w miastach wojewódzkich (Edytowalne)")
    st.caption("Kliknij dwukrotnie komórkę, aby zmienić jej wartość.")
    edited_df_koszty = st.data_editor(df_koszty, num_rows="dynamic", width="stretch", key="koszty_editor")


# --- CALCULATOR (Visually rendered at the top thanks to st.container) ---
with calc_container:
    st.header("Kalkulator ROI (Zwrotu z Inwestycji) 💰")

    # User input parameters
    col1, col2 = st.columns(2)
    with col1:
        czas_szukania_pracy_msc = st.number_input(
            "Czas szukania pracy (w miesiącach):",
            min_value=0.0, value=3.0, step=0.5
        )

        bootcamp_techs = [] if edited_df_bootcamp.empty else edited_df_bootcamp['Technologia'].unique()
        wybrana_technologia = st.selectbox(
            "Wybierz technologię (Bootcamp):",
            bootcamp_techs
        )
    with col2:
        czas_przepracowany_msc = st.number_input(
            "Czas zatrudnienia i zarabiania (w miesiącach):",
            min_value=0.0, value=12.0, step=1.0
        )

        cities = [] if edited_df_koszty.empty else edited_df_koszty['Miasto'].unique()
        wybrane_miasto = st.selectbox(
            "Wybierz miasto (Koszty życia):",
            cities
        )

    # Earnings suggestion based on market data
    sugerowane_zarobki = 6000.0
    if not df_market.empty and wybrana_technologia and wybrana_technologia.lower() in df_market['Technologia_Pojedyncza'].str.lower().values:
        sugerowane_zarobki = df_market[
            df_market['Technologia_Pojedyncza'].str.lower() == wybrana_technologia.lower()
        ]['Mediana_Zarobkow'].iloc[0]

    szacowane_zarobki = st.number_input(
        f"Szacowane miesięczne zarobki netto dla: {wybrana_technologia if wybrana_technologia else 'wybranej technologii'} (PLN):",
        min_value=0.0, value=float(sugerowane_zarobki), step=500.0,
        help="Domyślna wartość opiera się na medianie zarobków w bazie danych dla tej konkretnej technologii."
    )

    # Fetching selected and cleaned values
    try:
        if wybrana_technologia and wybrane_miasto:
            # Living costs
            wiersz_miasto = edited_df_koszty[edited_df_koszty['Miasto'] == wybrane_miasto].iloc[0]
            koszt_zycia_msc = clean_currency(wiersz_miasto['Średni koszt życia / utrzymania'])

            # Education data
            wiersz_bootcamp = edited_df_bootcamp[edited_df_bootcamp['Technologia'] == wybrana_technologia].iloc[0]
            koszt_bootcampu = clean_currency(wiersz_bootcamp['Mediana Kosztu'])
            czas_edukacji_dni = clean_days(wiersz_bootcamp['Mediana Czasu (dni)'])
            czas_edukacji_msc = czas_edukacji_dni / 30.0  # Simple conversion of days to months

            # ---------------------------------------------------------
            # CALCULATION FORMULA
            # ---------------------------------------------------------

            # Opportunity cost / Cost of living = Living costs * (Education time + Job search time)
            koszt_utrzymania_okres_przejsciowy = koszt_zycia_msc * (czas_edukacji_msc + czas_szukania_pracy_msc)

            # Total investment cost
            calkowity_koszt = koszt_bootcampu + koszt_utrzymania_okres_przejsciowy

            # Revenue (Time employed * Earnings from new job)
            calkowity_przychod = czas_przepracowany_msc * szacowane_zarobki

            # Result (Balance)
            bilans = calkowity_przychod - calkowity_koszt

            # Break-even point
            miesiace_do_zwrotu = calkowity_koszt / szacowane_zarobki if szacowane_zarobki > 0 else float('inf')
            # ---------------------------------------------------------

            # --- Presentation of Results ---
            st.markdown("### Wyniki Kalkulacji")
            st.info(
                f"**Wymagany budżet początkowy:** Koszt edukacji ({koszt_bootcampu:.2f} PLN) "
                f"+ Koszty życia w trakcie nauki i szukania pracy ({koszt_utrzymania_okres_przejsciowy:.2f} PLN)."
            )

            mcol1, mcol2, mcol3 = st.columns(3)
            with mcol1:
                st.metric("Inwestycja (Koszty ogółem)", f"{calkowity_koszt:,.2f} PLN".replace(",", " "))
            with mcol2:
                st.metric(f"Przychód ({czas_przepracowany_msc:.0f} mies.)", f"{calkowity_przychod:,.2f} PLN".replace(",", " "))
            with mcol3:
                # Visual profitability indicator (green = positive, red = negative)
                st.metric("Bilans po ustalonym czasie", f"{bilans:,.2f} PLN".replace(",", " "), delta=f"{bilans:,.2f} PLN")

            st.subheader("Czas Zwrotu z Inwestycji (ROI)")
            if miesiace_do_zwrotu <= czas_przepracowany_msc:
                st.success(f"Inwestycja całkowicie się zwróci po około **{miesiace_do_zwrotu:.1f}** miesiącach pracy na nowym stanowisku.")
            else:
                st.warning(
                    f"Inwestycja zwróci się po około **{miesiace_do_zwrotu:.1f}** miesiącach (to wykracza poza zakres wybranej przez Ciebie symulacji).")
        else:
            st.info("Niewystarczające dane do wykonania obliczeń. Upewnij się, że baza danych jest zaktualizowana.")

    except Exception as e:
        st.warning("Upewnij się, że tabele zawierają poprawne wartości dla wybranego miasta i technologii.")
        st.error(f"Szczegóły błędu: {e}")