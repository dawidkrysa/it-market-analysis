import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy import stats
from utils.db_handler import DatabaseHandler

# Header and description
st.title("📊 Analiza Korelacji: Niszowość Technologii vs Wynagrodzenia")

st.markdown("""
**Pytanie badawcze:** Czy istnieje statystycznie istotna zależność między charakterystykami niszy technologicznej 
(liczba ofert, czas na rynku) a wysokością oferowanego wynagrodzenia?

**Hipotezy do weryfikacji:**
1. **Liczba ofert vs Wynagrodzenie:** Czy technologie z mniejszą liczbą ofert (bardziej niszowe) oferują wyższe wynagrodzenia?
2. **Czas na rynku vs Wynagrodzenie:** Czy oferty pozostające dłużej aktywne (trudniejsze do zapełnienia) oferują wyższe wynagrodzenia?
""")

# Init database handler with caching
@st.cache_resource
def get_db_handler():
    return DatabaseHandler()

try:
    db = get_db_handler()
except Exception as e:
    st.error(f"❌ Błąd połączenia z bazą danych: {e}")
    st.stop()

# Sidebar parameters
st.sidebar.markdown("### Parametry analizy")
min_jobs = st.sidebar.slider("Minimalna liczba ofert", min_value=1, max_value=50, value=10, step=1)
max_jobs = st.sidebar.slider("Maksymalna liczba ofert", min_value=30, max_value=300, value=150, step=10)

st.sidebar.markdown("### Filtry wynagrodzeń")
min_salary = st.sidebar.slider(
    "Minimalna mediana (PLN)",
    min_value=0, max_value=20000, value=1000, step=500,
    help="Pozwala odrzucić błędy danych (np. oferty z zarobkami 0 PLN) lub darmowe staże."
)

max_salary = st.sidebar.slider(
    "Maksymalna mediana (PLN)",
    min_value=10000, max_value=50000, value=20000, step=1000,
    help="Pozwala odrzucić 'anegdoty' - pojedyncze oferty z kosmicznymi stawkami fałszującymi trend."
)

# Download and analyze data
with st.spinner("Pobieranie danych z bazy... ⏳"):
    try:
        df_niches = db.get_blue_ocean_niches(min_jobs=min_jobs, max_jobs=max_jobs)
    except Exception as e:
        st.error(f"❌ Błąd podczas analizy danych: {e}")
        st.stop()

# Check if we have data
if df_niches is None or df_niches.empty:
    st.warning("⚠️ Baza danych jest pusta. Uruchom scrapery, aby zebrać dane z portali z ofertami pracy.")
    st.info("💡 Użyj przycisku 'Uruchom scrapery' na stronie głównej lub uruchom je ręcznie z linii poleceń.")
    st.stop()

if len(df_niches) < 3:
    st.warning(f"⚠️ Zbyt mało danych do przeprowadzenia analizy korelacji. Znaleziono {len(df_niches)} technologii. Wymagane minimum: 3. Zmień parametry w panelu bocznym.")
    st.stop()

# Prepare data - remove rows with missing values and apply salary filters
correlation_data = df_niches.dropna(subset=['Liczba_Ofert', 'Sredni_Czas_Zatrudnienia', 'Mediana_Zarobkow']).copy()
correlation_data = correlation_data[
    (correlation_data['Mediana_Zarobkow'] >= min_salary) &
    (correlation_data['Mediana_Zarobkow'] <= max_salary)
]

if len(correlation_data) < 3:
    st.warning(f"⚠️ Po zastosowaniu filtrów pozostało {len(correlation_data)} technologii. Wymagane minimum: 3. Zmień parametry filtrów w panelu bocznym.")
    st.stop()

st.success(f"✅ Analiza obejmuje **{len(correlation_data)} technologii** z kompletnymi danymi (zakres wynagrodzeń: {min_salary:,} - {max_salary:,} PLN).")

# --- Analysis 1: Number of Offers vs Salary ---
st.markdown("---")
st.header("1️⃣ Liczba Ofert vs Mediana Wynagrodzeń")

st.markdown("""
**Hipoteza:** Technologie bardziej niszowe (mniej ofert) mogą oferować wyższe wynagrodzenia ze względu na 
niedobór specjalistów i mniejszą konkurencję między kandydatami.
""")

# Calculate correlations for offers vs salary
spearman_offers, spearman_offers_p = stats.spearmanr(
    correlation_data['Liczba_Ofert'], 
    correlation_data['Mediana_Zarobkow']
)

kendall_offers, kendall_offers_p = stats.kendalltau(
    correlation_data['Liczba_Ofert'], 
    correlation_data['Mediana_Zarobkow']
)

# Display results
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🔢 Korelacja Spearmana")
    st.metric("Współczynnik ρ (rho)", f"{spearman_offers:.4f}")
    st.metric("Wartość p", f"{spearman_offers_p:.4f}")
    
    if spearman_offers_p < 0.001:
        significance = "🟢 **Bardzo silnie istotna** (p < 0.001)"
    elif spearman_offers_p < 0.01:
        significance = "🟢 **Silnie istotna** (p < 0.01)"
    elif spearman_offers_p < 0.05:
        significance = "🟡 **Istotna** (p < 0.05)"
    else:
        significance = "🔴 **Nieistotna statystycznie** (p ≥ 0.05)"
    
    st.markdown(f"**Istotność:** {significance}")

with col2:
    st.markdown("### 🔢 Korelacja Kendalla")
    st.metric("Współczynnik τ (tau)", f"{kendall_offers:.4f}")
    st.metric("Wartość p", f"{kendall_offers_p:.4f}")
    
    if kendall_offers_p < 0.001:
        significance = "🟢 **Bardzo silnie istotna** (p < 0.001)"
    elif kendall_offers_p < 0.01:
        significance = "🟢 **Silnie istotna** (p < 0.01)"
    elif kendall_offers_p < 0.05:
        significance = "🟡 **Istotna** (p < 0.05)"
    else:
        significance = "🔴 **Nieistotna statystycznie** (p ≥ 0.05)"
    
    st.markdown(f"**Istotność:** {significance}")

# Visualization: Scatter plot for offers vs salary
fig1 = px.scatter(
    correlation_data,
    x='Liczba_Ofert',
    y='Mediana_Zarobkow',
    hover_data=['Technologia_Pojedyncza', 'Sredni_Czas_Zatrudnienia'],
    labels={
        'Liczba_Ofert': 'Liczba Ofert',
        'Mediana_Zarobkow': 'Mediana Wynagrodzeń (PLN)',
        'Technologia_Pojedyncza': 'Technologia',
        'Sredni_Czas_Zatrudnienia': 'Średni czas na rynku (dni)'
    },
    title=f"Liczba Ofert vs Mediana Wynagrodzeń (Spearman ρ={spearman_offers:.3f}, p={spearman_offers_p:.4f})"
)
fig1.update_traces(marker=dict(size=10, opacity=0.6))
st.plotly_chart(fig1, use_container_width=True)

# Interpretation for offers vs salary
st.markdown("### 📖 Interpretacja")
both_significant_offers = spearman_offers_p < 0.05 and kendall_offers_p < 0.05

if both_significant_offers:
    if spearman_offers < 0:
        st.success(f"""
        ✅ **Wniosek:** Oba testy potwierdzają istotną statystycznie **ujemną korelację** między liczbą ofert 
        a medianą wynagrodzeń (Spearman ρ={spearman_offers:.3f}, p={spearman_offers_p:.4f}; 
        Kendall τ={kendall_offers:.3f}, p={kendall_offers_p:.4f}).
        
        **Praktyczne znaczenie:** Technologie bardziej niszowe (mniej ofert) rzeczywiście oferują wyższe wynagrodzenia. 
        To potwierdza strategię "błękitnego oceanu" – specjalizacja w rzadszych technologiach może być bardziej opłacalna.
        """)
    else:
        st.warning(f"""
        ⚠️ **Wniosek:** Oba testy potwierdzają istotną statystycznie **dodatnią korelację** między liczbą ofert 
        a medianą wynagrodzeń (Spearman ρ={spearman_offers:.3f}, p={spearman_offers_p:.4f}; 
        Kendall τ={kendall_offers:.3f}, p={kendall_offers_p:.4f}).
        
        **Praktyczne znaczenie:** Technologie z większą liczbą ofert oferują wyższe wynagrodzenia. 
        To może sugerować, że popularne technologie są również lepiej płatne, prawdopodobnie ze względu na 
        wysokie zapotrzebowanie rynkowe.
        """)
else:
    st.info(f"""
    ℹ️ **Wniosek:** Nie wykryto statystycznie istotnej korelacji między liczbą ofert a medianą wynagrodzeń 
    (Spearman p={spearman_offers_p:.4f}; Kendall p={kendall_offers_p:.4f}).
    
    **Praktyczne znaczenie:** Niszowość technologii (mierzona liczbą ofert) nie jest silnie powiązana 
    z wysokością wynagrodzenia w analizowanej próbie. Inne czynniki mogą mieć większy wpływ na zarobki.
    """)

# --- Analysis 2: Time on Market vs Salary ---
st.markdown("---")
st.header("2️⃣ Czas na Rynku vs Mediana Wynagrodzeń")

st.markdown("""
**Hipoteza:** Oferty pozostające dłużej aktywne na rynku (trudniejsze do zapełnienia) mogą oferować wyższe 
wynagrodzenia jako sposób przyciągnięcia kandydatów w warunkach niedoboru specjalistów.
""")

# Calculate correlations for time vs salary
spearman_time, spearman_time_p = stats.spearmanr(
    correlation_data['Sredni_Czas_Zatrudnienia'], 
    correlation_data['Mediana_Zarobkow']
)

kendall_time, kendall_time_p = stats.kendalltau(
    correlation_data['Sredni_Czas_Zatrudnienia'], 
    correlation_data['Mediana_Zarobkow']
)

# Display results
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🔢 Korelacja Spearmana")
    st.metric("Współczynnik ρ (rho)", f"{spearman_time:.4f}")
    st.metric("Wartość p", f"{spearman_time_p:.4f}")
    
    if spearman_time_p < 0.001:
        significance = "🟢 **Bardzo silnie istotna** (p < 0.001)"
    elif spearman_time_p < 0.01:
        significance = "🟢 **Silnie istotna** (p < 0.01)"
    elif spearman_time_p < 0.05:
        significance = "🟡 **Istotna** (p < 0.05)"
    else:
        significance = "🔴 **Nieistotna statystycznie** (p ≥ 0.05)"
    
    st.markdown(f"**Istotność:** {significance}")

with col2:
    st.markdown("### 🔢 Korelacja Kendalla")
    st.metric("Współczynnik τ (tau)", f"{kendall_time:.4f}")
    st.metric("Wartość p", f"{kendall_time_p:.4f}")
    
    if kendall_time_p < 0.001:
        significance = "🟢 **Bardzo silnie istotna** (p < 0.001)"
    elif kendall_time_p < 0.01:
        significance = "🟢 **Silnie istotna** (p < 0.01)"
    elif kendall_time_p < 0.05:
        significance = "🟡 **Istotna** (p < 0.05)"
    else:
        significance = "🔴 **Nieistotna statystycznie** (p ≥ 0.05)"
    
    st.markdown(f"**Istotność:** {significance}")

# Visualization: Scatter plot for time vs salary
fig2 = px.scatter(
    correlation_data,
    x='Sredni_Czas_Zatrudnienia',
    y='Mediana_Zarobkow',
    hover_data=['Technologia_Pojedyncza', 'Liczba_Ofert'],
    labels={
        'Sredni_Czas_Zatrudnienia': 'Średni Czas na Rynku (Dni)',
        'Mediana_Zarobkow': 'Mediana Wynagrodzeń (PLN)',
        'Technologia_Pojedyncza': 'Technologia',
        'Liczba_Ofert': 'Liczba ofert'
    },
    title=f"Czas na Rynku vs Mediana Wynagrodzeń (Spearman ρ={spearman_time:.3f}, p={spearman_time_p:.4f})"
)
fig2.update_traces(marker=dict(size=10, opacity=0.6, color='coral'))
st.plotly_chart(fig2, use_container_width=True)

# Interpretation for time vs salary
st.markdown("### 📖 Interpretacja")
both_significant_time = spearman_time_p < 0.05 and kendall_time_p < 0.05

if both_significant_time:
    if spearman_time > 0:
        st.success(f"""
        ✅ **Wniosek:** Oba testy potwierdzają istotną statystycznie **dodatnią korelację** między czasem na rynku 
        a medianą wynagrodzeń (Spearman ρ={spearman_time:.3f}, p={spearman_time_p:.4f}; 
        Kendall τ={kendall_time:.3f}, p={kendall_time_p:.4f}).
        
        **Praktyczne znaczenie:** Oferty pozostające dłużej aktywne rzeczywiście oferują wyższe wynagrodzenia. 
        To potwierdza hipotezę, że wysokie płace są odpowiedzią na trudności w rekrutacji i niedobór specjalistów 
        w danej niszy technologicznej.
        """)
    else:
        st.warning(f"""
        ⚠️ **Wniosek:** Oba testy potwierdzają istotną statystycznie **ujemną korelację** między czasem na rynku 
        a medianą wynagrodzeń (Spearman ρ={spearman_time:.3f}, p={spearman_time_p:.4f}; 
        Kendall τ={kendall_time:.3f}, p={kendall_time_p:.4f}).
        
        **Praktyczne znaczenie:** Oferty z wyższymi wynagrodzeniami są szybciej zapełniane. 
        To sugeruje, że wysokie płace skutecznie przyciągają kandydatów, lub że technologie z wyższymi 
        zarobkami są bardziej popularne wśród specjalistów.
        """)
else:
    st.info(f"""
    ℹ️ **Wniosek:** Nie wykryto statystycznie istotnej korelacji między czasem na rynku a medianą wynagrodzeń 
    (Spearman p={spearman_time_p:.4f}; Kendall p={kendall_time_p:.4f}).
    
    **Praktyczne znaczenie:** Czas, przez który oferta pozostaje aktywna, nie jest silnie powiązany 
    z wysokością wynagrodzenia. Inne czynniki (np. popularność technologii, wymagania kompetencyjne, 
    lokalizacja) mogą mieć większy wpływ na czas rekrutacji.
    """)

# --- Summary Section ---
st.markdown("---")
st.header("📋 Podsumowanie Analizy")

summary_col1, summary_col2 = st.columns(2)

with summary_col1:
    st.markdown("### Liczba Ofert → Wynagrodzenie")
    if both_significant_offers:
        direction = "ujemna ↘️" if spearman_offers < 0 else "dodatnia ↗️"
        st.markdown(f"**Status:** ✅ Korelacja {direction} istotna statystycznie")
    else:
        st.markdown("**Status:** ❌ Brak istotnej korelacji")
    
    st.markdown(f"- Spearman ρ: **{spearman_offers:.3f}** (p={spearman_offers_p:.4f})")
    st.markdown(f"- Kendall τ: **{kendall_offers:.3f}** (p={kendall_offers_p:.4f})")

with summary_col2:
    st.markdown("### Czas na Rynku → Wynagrodzenie")
    if both_significant_time:
        direction = "dodatnia ↗️" if spearman_time > 0 else "ujemna ↘️"
        st.markdown(f"**Status:** ✅ Korelacja {direction} istotna statystycznie")
    else:
        st.markdown("**Status:** ❌ Brak istotnej korelacji")
    
    st.markdown(f"- Spearman ρ: **{spearman_time:.3f}** (p={spearman_time_p:.4f})")
    st.markdown(f"- Kendall τ: **{kendall_time:.3f}** (p={kendall_time_p:.4f})")

# Technical notes
st.markdown("---")
with st.expander("ℹ️ Informacje techniczne o testach statystycznych"):
    st.markdown(f"""
    **Wielkość próby:** {len(correlation_data)} technologii z kompletnymi danymi
    
    **Korelacja Spearmana (ρ):**
    - Test nieparametryczny oparty na rangach
    - Zakres: od -1 (idealna korelacja ujemna) do +1 (idealna korelacja dodatnia)
    - Odporny na wartości odstające i rozkłady nienormalne
    - Wykrywa monotoniczną zależność (niekoniecznie liniową)
    
    **Korelacja Kendalla (τ):**
    - Alternatywny test nieparametryczny oparty na rangach
    - Zakres: od -1 do +1
    - Bardziej konserwatywny niż Spearman (zwykle niższe wartości współczynnika)
    - Lepiej radzi sobie z małymi próbami i wieloma wartościami równymi
    - Interpretacja: prawdopodobieństwo zgodności minus prawdopodobieństwo niezgodności par obserwacji
    
    **Wartość p (p-value):**
    - Prawdopodobieństwo uzyskania obserwowanego wyniku (lub bardziej ekstremalnego) przy założeniu braku korelacji (hipoteza zerowa)
    - **p < 0.05:** wynik istotny statystycznie (odrzucamy hipotezę o braku korelacji)
    - **p < 0.01:** wynik silnie istotny statystycznie
    - **p < 0.001:** wynik bardzo silnie istotny statystycznie
    
    **Siła korelacji (wartości bezwzględne):**
    - **Spearman:** |ρ| ≥ 0.7 (silna), 0.4-0.7 (umiarkowana), 0.2-0.4 (słaba), < 0.2 (bardzo słaba)
    - **Kendall:** |τ| ≥ 0.5 (silna), 0.3-0.5 (umiarkowana), 0.1-0.3 (słaba), < 0.1 (bardzo słaba)
    
    **Dlaczego testy nieparametryczne?**
    - Nie wymagają założenia o normalności rozkładu danych
    - Odporne na wartości odstające (outliers)
    - Odpowiednie dla danych rankingowych lub porządkowych
    - Bardziej wiarygodne dla małych i średnich prób
    """)

# Data table
st.markdown("---")
st.subheader("📊 Dane użyte w analizie")
st.caption(f"Zastosowane filtry: Liczba ofert: {min_jobs}-{max_jobs} | Mediana wynagrodzeń: {min_salary:,}-{max_salary:,} PLN")
display_df = correlation_data[['Technologia_Pojedyncza', 'Liczba_Ofert', 'Mediana_Zarobkow', 'Sredni_Czas_Zatrudnienia', 'Procent_Ofert_Z_Widelkami']].copy()
display_df.columns = ['Technologia', 'Liczba Ofert', 'Mediana Zarobków (PLN)', 'Średni Czas na Rynku (dni)', 'Transparentność (%)']
display_df = display_df.sort_values('Mediana Zarobków (PLN)', ascending=False)
st.dataframe(display_df, use_container_width=True, hide_index=True)