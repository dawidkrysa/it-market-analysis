import streamlit as st
import pandas as pd
import plotly.express as px
from scipy import stats
from utils.db_handler import DatabaseHandler

# --- Konfiguracja i Nagłówek ---
st.title("📊 Analiza Korelacji: Niszowość vs Wynagrodzenia")

st.markdown("""
**Cel analizy:** Weryfikujemy, czy strategia "Błękitnego Oceanu" ma rzeczywiste pokrycie w danych finansowych polskiego rynku IT. Sprawdzamy dwie kluczowe hipotezy badawcze:

1. **Hipoteza Niszowości (Podaż):** Zakładamy, że rzadkie technologie (niski wybór ofert) wymuszają na pracodawcach oferowanie wyższych stawek z powodu trudności w znalezieniu specjalisty.
2. **Hipoteza Deficytu (Czas):** Zakładamy, że ogłoszenia, które najdłużej "wiszą" na rynku (najtrudniejsze do obsadzenia), oferują wyższe wynagrodzenia jako formę przyciągnięcia talentów.
""")

with st.expander("❓ Słowniczek pojęć statystycznych (Rozwiń, jeśli potrzebujesz)"):
    st.markdown("""
    * **Korelacja (ρ / τ):** Wynik od -1 do 1. 
      * Wartość blisko **1** oznacza, że gdy rośnie jedna rzecz, rośnie też druga (np. więcej ofert = wyższa płaca).
      * Wartość blisko **-1** oznacza, że gdy jedna rośnie, druga maleje (np. więcej ofert = niższa płaca).
      * Wartość blisko **0** to brak związku.
    * **Wartość p (p-value):** Prawdopodobieństwo, że nasz wynik to tylko zbieg okoliczności (szum w danych).
      * **p < 0.05** oznacza, że mamy mniej niż 5% szans na przypadek. Uznajemy wtedy wynik za **istotny statystycznie** (prawdziwy trend).
    * **Test Spearmana / Kendalla:** Dwa różne wzory matematyczne do liczenia korelacji. Używamy ich, ponieważ zarobki w IT nie rosną idealnie "od linijki", a te testy świetnie radzą sobie z takimi danymi.
    """)

# --- Inicjalizacja Bazy Danych ---
@st.cache_resource
def get_db_handler():
    return DatabaseHandler()

try:
    db = get_db_handler()
except Exception as e:
    st.error(f"❌ Błąd połączenia z bazą danych: {e}")
    st.stop()

# --- Panel Boczny (Sidebar) ---
st.sidebar.markdown("### Wielkość rynku")
min_jobs = st.sidebar.slider("Min. liczba ofert (wiarygodność)", 1, 50, 10, 1, help="Odrzuca technologie, które pojawiły się np. tylko raz (literówki, błędy).")
max_jobs = st.sidebar.slider("Max. liczba ofert (nasycenie)", 30, 300, 150, 10, help="Górny limit niszy. Powyżej tej wartości zaczyna się 'Czerwony Ocean' (duża konkurencja).")

st.sidebar.markdown("### Filtry anomalii płacowych")
min_salary = st.sidebar.slider("Minimalna mediana (PLN)", 0, 20000, 1000, 500, help="Odrzuca darmowe staże i błędy danych wejściowych.")
max_salary = st.sidebar.slider("Maksymalna mediana (PLN)", 10000, 50000, 20000, 1000, help="Odrzuca pojedyncze oferty dyrektorskie z kosmicznymi stawkami, które fałszują trend ogólny.")

# --- Pobieranie i Filtrowanie Danych ---
with st.spinner("Szybkie filtrowanie danych..."):
    try:
        df_raw, df_exploded, niche_analysis = DatabaseHandler.get_cached_market_data()
        if not niche_analysis.empty:
            df_niches = db._filter_viable_niches(niche_analysis, min_jobs, max_jobs)
        else:
            df_niches = pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Błąd: {e}")
        st.stop()

if df_niches is None or len(df_niches) < 3:
    st.warning("⚠️ Zbyt mało danych do analizy (minimum to 3 technologie). Dostosuj suwaki w panelu bocznym.")
    st.stop()

correlation_data = df_niches.dropna(subset=['Liczba_Ofert', 'Sredni_Czas_Zatrudnienia', 'Mediana_Zarobkow']).copy()
correlation_data = correlation_data[
    (correlation_data['Mediana_Zarobkow'] >= min_salary) &
    (correlation_data['Mediana_Zarobkow'] <= max_salary)
]

if len(correlation_data) < 3:
    st.warning(f"⚠️ Po zastosowaniu filtrów płacowych pozostało tylko {len(correlation_data)} technologii. Rozszerz zakres.")
    st.stop()

# --- Funkcja Pomocnicza dla Etykiet ---
def get_significance_label(p_value):
    if p_value < 0.001: return "🟢 Bardzo silnie istotna (p < 0.001)"
    if p_value < 0.01:  return "🟢 Silnie istotna (p < 0.01)"
    if p_value < 0.05:  return "🟡 Istotna statystycznie (p < 0.05)"
    return "🔴 Nieistotna (przypadek)"

# ==========================================
# ANALIZA 1: Liczba Ofert vs Wynagrodzenie
# ==========================================
st.markdown("---")
st.header("1️⃣ Liczba Ofert vs Wynagrodzenie")

spearman_off, spearman_off_p = stats.spearmanr(correlation_data['Liczba_Ofert'], correlation_data['Mediana_Zarobkow'])
kendall_off, kendall_off_p = stats.kendalltau(correlation_data['Liczba_Ofert'], correlation_data['Mediana_Zarobkow'])

col1, col2 = st.columns(2)
with col1:
    st.metric(
        "Korelacja Spearmana (ρ)", 
        f"{spearman_off:.3f}", 
        get_significance_label(spearman_off_p),
        help="Główny wskaźnik siły związku między liczbą ofert a płacą."
    )
with col2:
    st.metric(
        "Korelacja Kendalla (τ)", 
        f"{kendall_off:.3f}", 
        get_significance_label(kendall_off_p),
        help="Test pomocniczy, często dokładniejszy dla małych próbek danych."
    )

fig1 = px.scatter(
    correlation_data, x='Liczba_Ofert', y='Mediana_Zarobkow',
    hover_data={'Technologia_Pojedyncza': True, 'Sredni_Czas_Zatrudnienia': ':.1f', 'Mediana_Zarobkow': ':.0f'},
    labels={'Liczba_Ofert': 'Liczba Ofert na Rynku', 'Mediana_Zarobkow': 'Mediana Wynagrodzeń (PLN)', 'Technologia_Pojedyncza': 'Technologia'},
    trendline="ols",
    title="Wizualizacja trendu: Podaż ofert a zarobki"
)
fig1.update_traces(marker=dict(size=10, opacity=0.7))
st.plotly_chart(fig1, width="stretch")

# Interpretacja
if spearman_off_p < 0.05:
    if spearman_off < 0:
        st.success("**Wniosek (Potwierdzenie hipotezy):** Statystyka wykazuje ujemną korelację. Mniej popularne technologie (nisze) faktycznie oferują wyższe wynagrodzenia w badanej próbie.")
    else:
        st.warning("**Wniosek (Odrzucenie hipotezy):** Statystyka wykazuje dodatnią korelację. To technologie z największą liczbą ofert płacą najlepiej, co przeczy założeniom błękitnego oceanu.")
else:
    st.info("**Wniosek (Brak dowodów):** Obecne dane nie wykazują statystycznego związku między tym, jak rzadka jest technologia, a tym, ile się w niej zarabia (wynik może być dziełem przypadku).")

# ==========================================
# ANALIZA 2: Czas na Rynku vs Wynagrodzenie
# ==========================================
st.markdown("---")
st.header("2️⃣ Czas na Rynku vs Wynagrodzenie")

spearman_time, spearman_time_p = stats.spearmanr(correlation_data['Sredni_Czas_Zatrudnienia'], correlation_data['Mediana_Zarobkow'])
kendall_time, kendall_time_p = stats.kendalltau(correlation_data['Sredni_Czas_Zatrudnienia'], correlation_data['Mediana_Zarobkow'])

col3, col4 = st.columns(2)
with col3:
    st.metric(
        "Korelacja Spearmana (ρ)", 
        f"{spearman_time:.3f}", 
        get_significance_label(spearman_time_p),
        help="Sprawdza, czy im dłużej wisi oferta, tym wyższa jest mediana płac."
    )
with col4:
    st.metric(
        "Korelacja Kendalla (τ)", 
        f"{kendall_time:.3f}", 
        get_significance_label(kendall_time_p)
    )

fig2 = px.scatter(
    correlation_data, x='Sredni_Czas_Zatrudnienia', y='Mediana_Zarobkow',
    hover_data={'Technologia_Pojedyncza': True, 'Liczba_Ofert': True, 'Mediana_Zarobkow': ':.0f'},
    labels={'Sredni_Czas_Zatrudnienia': 'Średni Czas Aktywności Oferty (Dni)', 'Mediana_Zarobkow': 'Mediana Wynagrodzeń (PLN)', 'Technologia_Pojedyncza': 'Technologia'},
    color_discrete_sequence=['coral'],
    trendline="ols",
    title="Wizualizacja trendu: Czas wakatu a zarobki"
)
fig2.update_traces(marker=dict(size=10, opacity=0.7))
st.plotly_chart(fig2, width="stretch")

# Interpretacja
if spearman_time_p < 0.05:
    if spearman_time > 0:
        st.success("**Wniosek (Potwierdzenie hipotezy):** Statystyka wykazuje dodatnią korelację. Oferty, które najtrudniej obsadzić (wiszą najdłużej), faktycznie próbują kusić wyższymi stawkami.")
    else:
        st.warning("**Wniosek (Odrzucenie hipotezy):** Statystyka wykazuje ujemną korelację. Oferty z najwyższymi stawkami znikają z rynku najszybciej (są błyskawicznie obsadzane).")
else:
    st.info("**Wniosek (Brak dowodów):** Nie ma mocnych dowodów na to, że czas aktywności oferty ma matematyczny związek z wysokością proponowanego w niej wynagrodzenia.")