"""
Radar Mikro-nisz - Statistical Correlation Analysis Module.

This module verifies the "Blue Ocean" strategy hypotheses using statistical
methods (Spearman and Kendall correlation tests) to analyze the relationship
between technology niche size, vacancy duration, and salary levels.
"""

import pandas as pd
import plotly.express as px
import statsmodels.api as sm
import streamlit as st
from scipy import stats

from utils.db_handler import SALARY_TYPE_COLUMNS, DatabaseHandler

# --- Configuration and Header ---
st.title("Analiza Korelacji: Niszowość vs Wynagrodzenia")

st.markdown("""
**Cel analizy:** Weryfikujemy, czy strategia "Błękitnego Oceanu" ma rzeczywiste pokrycie w danych finansowych polskiego rynku IT. Sprawdzamy dwie kluczowe hipotezy badawcze:

1. **Hipoteza Niszowości (Podaż):** Zakładamy, że rzadkie technologie (niski wybór ofert) wymuszają na pracodawcach oferowanie wyższych stawek z powodu trudności w znalezieniu specjalisty.
2. **Hipoteza Deficytu (Czas):** Zakładamy, że ogłoszenia, które najdłużej "wiszą" na rynku (najtrudniejsze do obsadzenia), oferują wyższe wynagrodzenia jako formę przyciągnięcia talentów.
""")

with st.expander("Słowniczek pojęć statystycznych (Rozwiń, jeśli potrzebujesz)"):
    st.markdown("""
    * **Korelacja (ρ / τ):** Wynik od -1 do 1. 
      * Wartość blisko **1** oznacza, że gdy rośnie jedna rzecz, rośnie też druga (np. więcej ofert = wyższa płaca).
      * Wartość blisko **-1** oznacza, że gdy jedna rośnie, druga maleje (np. więcej ofert = niższa płaca).
      * Wartość blisko **0** to brak związku.
    * **Wartość p (p-value):** Prawdopodobieństwo, że nasz wynik to tylko zbieg okoliczności (szum w danych).
      * **p < 0.05** oznacza, że mamy mniej niż 5% szans na przypadek. Uznajemy wtedy wynik za **istotny statystycznie** (prawdziwy trend).
    * **Test Spearmana / Kendalla:** Dwa różne wzory matematyczne do liczenia korelacji. Używamy ich, ponieważ zarobki w IT nie rosną idealnie "od linijki", a te testy świetnie radzą sobie z takimi danymi.
    * **Regresja OLS:** Dopasowuje linię prostą (y = a + b·x) do danych metodą najmniejszych kwadratów. Współczynnik **b (nachylenie)** mówi, o ile zmienia się wynagrodzenie przy wzroście x o 1 jednostkę.
    * **R² (R-kwadrat):** Odsetek (0-1) zmienności wynagrodzeń, który model wyjaśnia samym x. Blisko 1 = model dobrze pasuje, blisko 0 = x prawie nic nie tłumaczy.
    * **Skośność:** Mówi, czy rozkład danych jest symetryczny. Dodatnia = ogon wartości wysokich (nieliczne bardzo drogie oferty ciągną średnią w górę), ujemna = odwrotnie.
    * **Kurtoza:** Mówi o "grubości ogonów" rozkładu względem rozkładu normalnego. Wysoka wartość = więcej skrajnych wartości odstających niż w typowym rozkładzie.
    """)


# --- Database Initialization ---
@st.cache_resource
def get_db_handler() -> DatabaseHandler:
    """
    Initialize and cache the database handler.

    Returns:
        DatabaseHandler: The cached database connection instance.
    """
    return DatabaseHandler()


try:
    db = get_db_handler()
except Exception as e:
    st.error(f"Błąd połączenia z bazą danych: {e}")
    st.stop()

# --- Sidebar Panel ---
st.sidebar.markdown("### Typ wynagrodzenia")
typ_wynagrodzenia = st.sidebar.selectbox(
    "Widełki do analizy:",
    options=list(SALARY_TYPE_COLUMNS.keys()),
    help=(
        "Każda oferta może mieć kilka wariantów wynagrodzenia naraz "
        "(UoP, B2B, stawka godzinowa) — wybierz, który ma być porównywany."
    ),
)
jest_stawka_godzinowa = typ_wynagrodzenia == "Stawka godzinowa"
jednostka_label = "PLN/h" if jest_stawka_godzinowa else "PLN"

st.sidebar.markdown("### Wielkość rynku")
min_jobs = st.sidebar.slider(
    "Min. liczba ofert (wiarygodność)",
    1,
    50,
    10,
    1,
    help="Odrzuca technologie, które pojawiły się np. tylko raz (literówki, błędy).",
)
max_jobs = st.sidebar.slider(
    "Max. liczba ofert (nasycenie)",
    30,
    300,
    150,
    10,
    help="Górny limit niszy. Powyżej tej wartości zaczyna się 'Czerwony Ocean' (duża konkurencja).",
)

st.sidebar.markdown("### Filtry anomalii płacowych")
if jest_stawka_godzinowa:
    min_salary = st.sidebar.slider(
        "Minimalna mediana (PLN/h)",
        0,
        200,
        20,
        5,
        help="Odrzuca darmowe staże i błędy danych wejściowych.",
    )
    max_salary = st.sidebar.slider(
        "Maksymalna mediana (PLN/h)",
        100,
        1000,
        400,
        50,
        help="Odrzuca pojedyncze oferty z kosmicznymi stawkami, które fałszują trend ogólny.",
    )
else:
    min_salary = st.sidebar.slider(
        "Minimalna mediana (PLN)",
        0,
        20000,
        1000,
        500,
        help="Odrzuca darmowe staże i błędy danych wejściowych.",
    )
    max_salary = st.sidebar.slider(
        "Maksymalna mediana (PLN)",
        10000,
        50000,
        20000,
        1000,
        help="Odrzuca pojedyncze oferty dyrektorskie z kosmicznymi stawkami, które fałszują trend ogólny.",
    )

# --- Data Retrieval and Filtering ---
with st.spinner("Szybkie filtrowanie danych..."):
    try:
        df_raw, df_exploded, niche_analysis = DatabaseHandler.get_cached_market_data(
            typ_wynagrodzenia
        )
        if not niche_analysis.empty:
            df_niches = db._filter_viable_niches(niche_analysis, min_jobs, max_jobs)
        else:
            df_niches = pd.DataFrame()
    except Exception as e:
        st.error(f"Błąd: {e}")
        st.stop()

# Validate the retrieved dataset size before proceeding
if df_niches is None or len(df_niches) < 3:
    st.warning(
        "Zbyt mało danych do analizy (minimum to 3 technologie). Dostosuj suwaki w panelu bocznym."
    )
    st.stop()

correlation_data = df_niches.dropna(
    subset=["Liczba_Ofert", "Wzgledny_Wiek_Ogloszen", "Mediana_Zarobkow"]
).copy()
correlation_data = correlation_data[
    (correlation_data["Mediana_Zarobkow"] >= min_salary)
    & (correlation_data["Mediana_Zarobkow"] <= max_salary)
]

# Ensure we still have enough data points after applying salary filters
if len(correlation_data) < 3:
    st.warning(
        f"Po zastosowaniu filtrów płacowych pozostało tylko {len(correlation_data)} technologii. Rozszerz zakres."
    )
    st.stop()


# --- Helper Function for Labels ---
def get_significance_label(p_value: float) -> str:
    """
    Determine the statistical significance label based on the calculated p-value.

    Args:
        p_value (float): The p-value resulting from a statistical test.

    Returns:
        str: A formatted string containing an indicator emoji and explanation.
    """
    if p_value < 0.001:
        return "Bardzo silnie istotna (p < 0.001)"
    if p_value < 0.01:
        return "Silnie istotna (p < 0.01)"
    if p_value < 0.05:
        return "Istotna statystycznie (p < 0.05)"
    return "Nieistotna (przypadek)"


def fit_ols(x: pd.Series, y: pd.Series) -> dict:
    """
    Fit a simple OLS regression (y = intercept + slope * x) via statsmodels.

    Args:
        x (pd.Series): Independent variable.
        y (pd.Series): Dependent variable (salary).

    Returns:
        dict: r2, r2_adj, intercept, slope, slope_p (p-value of the slope),
            slope_ci (95% confidence interval tuple), and the full
            statsmodels summary as text.
    """
    model = sm.OLS(y, sm.add_constant(x)).fit()
    ci_low, ci_high = model.conf_int().iloc[1]
    return {
        "r2": model.rsquared,
        "r2_adj": model.rsquared_adj,
        "intercept": model.params.iloc[0],
        "slope": model.params.iloc[1],
        "slope_p": model.pvalues.iloc[1],
        "slope_ci": (ci_low, ci_high),
        "summary": str(model.summary()),
    }


# ==========================================
# DESCRIPTIVE STATISTICS
# ==========================================
st.markdown("---")
st.header("0. Statystyki Opisowe")
st.caption(
    f"Policzone na {len(correlation_data)} technologiach spełniających aktualne filtry w panelu bocznym."
)

desc_source = correlation_data[["Liczba_Ofert", "Mediana_Zarobkow", "Wzgledny_Wiek_Ogloszen"]]
desc_table = desc_source.agg(["mean", "median", "std", "min", "max"]).T
desc_table["skośność"] = desc_source.skew()
desc_table["kurtoza"] = desc_source.kurt()
desc_table.index = [
    "Liczba Ofert",
    f"Mediana Wynagrodzeń ({jednostka_label})",
    "Względny wiek ogłoszeń (0-100)",
]
desc_table.columns = [
    "Średnia",
    "Mediana",
    "Odch. std.",
    "Min",
    "Max",
    "Skośność",
    "Kurtoza",
]
st.dataframe(desc_table.round(2), width="stretch")

# ==========================================
# ANALYSIS 1: Number of Offers vs. Salary
# ==========================================
st.markdown("---")
st.header("1. Liczba Ofert vs Wynagrodzenie")

# Calculate correlations
spearman_off, spearman_off_p = stats.spearmanr(
    correlation_data["Liczba_Ofert"], correlation_data["Mediana_Zarobkow"]
)
kendall_off, kendall_off_p = stats.kendalltau(
    correlation_data["Liczba_Ofert"], correlation_data["Mediana_Zarobkow"]
)

col1, col2 = st.columns(2)
with col1:
    st.metric(
        "Korelacja Spearmana (ρ)",
        f"{spearman_off:.3f}",
        get_significance_label(spearman_off_p),
        help="Główny wskaźnik siły związku między liczbą ofert a płacą.",
    )
with col2:
    st.metric(
        "Korelacja Kendalla (τ)",
        f"{kendall_off:.3f}",
        get_significance_label(kendall_off_p),
        help="Test pomocniczy, często dokładniejszy dla małych próbek danych.",
    )

# Fit and display an OLS regression model
ols_off = fit_ols(correlation_data["Liczba_Ofert"], correlation_data["Mediana_Zarobkow"])
col1b, col2b, col3b = st.columns(3)
with col1b:
    st.metric(
        "R² modelu OLS",
        f"{ols_off['r2']:.3f}",
        help="Jaką część zmienności wynagrodzeń wyjaśnia liczba ofert.",
    )
with col2b:
    st.metric(
        "Nachylenie (β)",
        f"{ols_off['slope']:.2f} {jednostka_label}",
        get_significance_label(ols_off["slope_p"]),
        help="O ile zmienia się mediana wynagrodzeń przy wzroście liczby ofert o 1.",
    )
with col3b:
    st.metric(
        "95% przedział ufności dla β",
        f"[{ols_off['slope_ci'][0]:.2f}; {ols_off['slope_ci'][1]:.2f}]",
    )
st.caption(
    f"Model: Mediana Wynagrodzeń = {ols_off['intercept']:.1f} + {ols_off['slope']:.3f} × Liczba Ofert"
)
with st.expander("Pełne podsumowanie modelu OLS (statsmodels)"):
    st.code(ols_off["summary"])

# Render scatter plot with trendline
fig1 = px.scatter(
    correlation_data,
    x="Liczba_Ofert",
    y="Mediana_Zarobkow",
    hover_data={
        "Technologia_Pojedyncza": True,
        "Wzgledny_Wiek_Ogloszen": ":.1f",
        "Mediana_Zarobkow": ":.0f",
    },
    labels={
        "Liczba_Ofert": "Liczba Ofert na Rynku",
        "Mediana_Zarobkow": f"Mediana Wynagrodzeń ({jednostka_label})",
        "Technologia_Pojedyncza": "Technologia",
    },
    trendline="ols",
    title="Wizualizacja trendu: Podaż ofert a zarobki",
)
fig1.update_traces(marker=dict(size=10, opacity=0.7))
st.plotly_chart(fig1, width="stretch")

# Statistical interpretation display
if spearman_off_p < 0.05:
    if spearman_off < 0:
        st.success(
            "**Wniosek (Potwierdzenie hipotezy):** Statystyka wykazuje ujemną korelację. Mniej popularne technologie (nisze) faktycznie oferują wyższe wynagrodzenia w badanej próbie."
        )
    else:
        st.warning(
            "**Wniosek (Odrzucenie hipotezy):** Statystyka wykazuje dodatnią korelację. To technologie z największą liczbą ofert płacą najlepiej, co przeczy założeniom błękitnego oceanu."
        )
else:
    st.info(
        "**Wniosek (Brak dowodów):** Obecne dane nie wykazują statystycznego związku między tym, jak rzadka jest technologia, a tym, ile się w niej zarabia (wynik może być dziełem przypadku)."
    )

# ==========================================
# ANALYSIS 2: Time on Market vs. Salary
# ==========================================
st.markdown("---")
st.header("2. Czas na Rynku vs Wynagrodzenie")
st.caption(
    "Czas na rynku mierzymy względnie: percentyl wieku ogłoszenia w obrębie jego portalu "
    "(50 = typowe ogłoszenie). Portale datują ogłoszenia różnie (NoFluffJobs i TheProtocol "
    "publikują je ponownie co ok. 30 dni, JustJoinIT trzyma pierwotną datę), więc surowe dni "
    "mierzyłyby głównie to, na jakim portalu ogłasza się dana technologia."
)

# Calculate correlations
spearman_time, spearman_time_p = stats.spearmanr(
    correlation_data["Wzgledny_Wiek_Ogloszen"], correlation_data["Mediana_Zarobkow"]
)
kendall_time, kendall_time_p = stats.kendalltau(
    correlation_data["Wzgledny_Wiek_Ogloszen"], correlation_data["Mediana_Zarobkow"]
)

col3, col4 = st.columns(2)
with col3:
    st.metric(
        "Korelacja Spearmana (ρ)",
        f"{spearman_time:.3f}",
        get_significance_label(spearman_time_p),
        help="Sprawdza, czy im dłużej (względnie) wiszą ogłoszenia, tym wyższa jest mediana płac.",
    )
with col4:
    st.metric(
        "Korelacja Kendalla (τ)", f"{kendall_time:.3f}", get_significance_label(kendall_time_p)
    )

# Fit and display an OLS regression model
ols_time = fit_ols(
    correlation_data["Wzgledny_Wiek_Ogloszen"], correlation_data["Mediana_Zarobkow"]
)
col3b, col4b, col5b = st.columns(3)
with col3b:
    st.metric(
        "R² modelu OLS",
        f"{ols_time['r2']:.3f}",
        help="Jaką część zmienności wynagrodzeń wyjaśnia względny wiek ogłoszeń.",
    )
with col4b:
    st.metric(
        "Nachylenie (β)",
        f"{ols_time['slope']:.2f} {jednostka_label}/pkt",
        get_significance_label(ols_time["slope_p"]),
        help="O ile zmienia się mediana wynagrodzeń przy wzroście względnego wieku o 1 punkt percentyla.",
    )
with col5b:
    st.metric(
        "95% przedział ufności dla β",
        f"[{ols_time['slope_ci'][0]:.2f}; {ols_time['slope_ci'][1]:.2f}]",
    )
st.caption(
    f"Model: Mediana Wynagrodzeń = {ols_time['intercept']:.1f} + "
    f"{ols_time['slope']:.3f} × Względny Wiek Ogłoszeń"
)
with st.expander("Pełne podsumowanie modelu OLS (statsmodels)"):
    st.code(ols_time["summary"])

# Render scatter plot with trendline
fig2 = px.scatter(
    correlation_data,
    x="Wzgledny_Wiek_Ogloszen",
    y="Mediana_Zarobkow",
    hover_data={"Technologia_Pojedyncza": True, "Liczba_Ofert": True, "Mediana_Zarobkow": ":.0f"},
    labels={
        "Wzgledny_Wiek_Ogloszen": "Względny wiek ogłoszeń (percentyl w portalu, 0-100)",
        "Mediana_Zarobkow": f"Mediana Wynagrodzeń ({jednostka_label})",
        "Technologia_Pojedyncza": "Technologia",
    },
    color_discrete_sequence=["coral"],
    trendline="ols",
    title="Wizualizacja trendu: Czas wakatu a zarobki",
)
fig2.update_traces(marker=dict(size=10, opacity=0.7))
st.plotly_chart(fig2, width="stretch")

# Statistical interpretation display
if spearman_time_p < 0.05:
    if spearman_time > 0:
        st.success(
            "**Wniosek (Potwierdzenie hipotezy):** Statystyka wykazuje dodatnią korelację. Oferty, które najtrudniej obsadzić (wiszą najdłużej), faktycznie próbują kusić wyższymi stawkami."
        )
    else:
        st.warning(
            "**Wniosek (Odrzucenie hipotezy):** Statystyka wykazuje ujemną korelację. Oferty z najwyższymi stawkami znikają z rynku najszybciej (są błyskawicznie obsadzane)."
        )
else:
    st.info(
        "**Wniosek (Brak dowodów):** Nie ma mocnych dowodów na to, że czas aktywności oferty ma matematyczny związek z wysokością proponowanego w niej wynagrodzenia."
    )
