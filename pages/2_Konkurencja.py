import streamlit as st
import pandas as pd
import plotly.express as px
from utils.db_handler import DatabaseHandler
import matplotlib.pyplot as plt
import seaborn as sns

# Header and description
st.title("Strategia Błękitnego Oceanu 🌊")

st.markdown("""
**Odkryj ukryty potencjał polskiego rynku IT.** Ten moduł służy do identyfikacji tzw. "błękitnych oceanów" – wysokopłatnych i deficytowych technologii, które są często pomijane w standardowych bootcampach. 

Zamiast konkurować w przesyconych obszarach, zoptymalizuj ścieżkę kariery bazując na danych.
""")

st.info("💡 **Wskazówka:** Użyj suwaków w panelu bocznym, aby zdefiniować własne ramy dla wielkości niszy rynkowej.")

# --- Sidebar for user-defined parameters defining what constitutes a niche ---
st.sidebar.markdown("### Parametry Niszy")
min_jobs = st.sidebar.slider("Minimalna liczba ofert", min_value=1, max_value=50, value=15, step=1, help="Wiarygodność rynku – odrzuca anomalie.")
max_jobs = st.sidebar.slider("Maksymalna liczba ofert", min_value=30, max_value=200, value=70, step=1, help="Brak nasycenia – odrzuca 'czerwone oceany'.")

# Init database handler with caching to avoid reinitialization on every interaction
@st.cache_resource
def get_db_handler():
    return DatabaseHandler()

try:
    db = get_db_handler()
except Exception as e:
    st.error(f"❌ Błąd połączenia: {e}")
    st.stop()

# --- Download and analyze data with a spinner to indicate processing ---
with st.spinner("Przetwarzanie tysięcy ofert pracy... ⏳"):
    try:
        df_niches = db.get_blue_ocean_niches(min_jobs=min_jobs, max_jobs=max_jobs)
        raw_jobs = db.get_all_jobs()
        df_raw = pd.DataFrame(raw_jobs)
        df_raw = db._prepare_salary_data(df_raw)
        df_exploded = db._explode_technologies(df_raw.copy())
    except Exception as e:
        st.error(f"❌ Błąd: {e}")
        st.stop()

# --- Presentation of results ---
if df_niches is None or df_niches.empty:
    st.warning(f"⚠️ Brak technologii spełniających kryterium {min_jobs} - {max_jobs} ofert. Zmień parametry.")
else:
    # Metryki KPI
    st.markdown("### 🏆 Lider Zestawienia")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Zidentyfikowane nisze", len(df_niches))
    col2.metric("Najlepsza technologia", df_niches.iloc[0]['Technologia_Pojedyncza'].title())
    col3.metric("Mediana zarobków", f"{df_niches.iloc[0]['Mediana_Zarobkow']:,.0f} PLN")
    
    top_transparency = df_niches.iloc[0]['Procent_Ofert_Z_Widelkami']
    transparency_emoji = '🟢' if top_transparency >= 50 else ('🟡' if top_transparency >= 25 else '🔴')
    col4.metric(
        "Transparentność danych",
        f"{transparency_emoji} {top_transparency:.1f}%",
        help="🟢≥50% 🟡≥25% 🔴<25%"
    )
    
    low_quality_niches = df_niches[df_niches['Procent_Ofert_Z_Widelkami'] < 25]
    if len(low_quality_niches) > 0:
        st.warning(f"⚠️ {len(low_quality_niches)} z {len(df_niches)} nisz ma niską transparentność płacową (<25%). Ich mediany mogą być zawyżone.")

    st.markdown("---")
    st.subheader("Wizualizacja Top 15 Nisz")
    
    # Zamieniono st.info na zwykły markdown (czyściej)
    st.markdown("*Wysokość słupka = zarobki. Kolor = czas aktywności ogłoszenia (ciemniejszy = trudniej zrekrutować).*")
    
    top_15 = df_niches.head(15).copy().dropna(subset=['Mediana_Zarobkow', 'Sredni_Czas_Zatrudnienia'])
    top_15['Mediana_Zarobkow'] = top_15['Mediana_Zarobkow'].round(2)
    top_15['Sredni_Czas_Zatrudnienia'] = top_15['Sredni_Czas_Zatrudnienia'].round(2)
    top_15['Jakosc_Danych'] = top_15['Procent_Ofert_Z_Widelkami'].apply(lambda x: '🟢' if x >= 50 else ('🟡' if x >= 25 else '🔴'))

    fig = px.bar(
        top_15,
        x='Technologia_Pojedyncza',
        y='Mediana_Zarobkow',
        color='Sredni_Czas_Zatrudnienia',
        hover_data={'Procent_Ofert_Z_Widelkami': ':.1f', 'Jakosc_Danych': True, 'Liczba_Ofert': True, 'Technologia_Pojedyncza': False},
        color_continuous_scale='Blues',
        labels={
            'Technologia_Pojedyncza': 'Technologia',
            'Mediana_Zarobkow': 'Mediana (PLN)',
            'Sredni_Czas_Zatrudnienia': 'Czas na Rynku (Dni)'
        },
        title="Opłacalność vs. Deficyt Kandydatów"
    )
    fig.update_layout(xaxis={'categoryorder':'total descending'})
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Tabela: Pełne zestawienie analityczne"):
        formatted_df = df_niches.copy()
        formatted_df['Mediana_Zarobkow'] = formatted_df['Mediana_Zarobkow'].apply(lambda x: f"{x:,.2f} PLN".replace(',', ' ') if pd.notnull(x) else "Brak")
        formatted_df['Sredni_Czas_Zatrudnienia'] = formatted_df['Sredni_Czas_Zatrudnienia'].apply(lambda x: f"{x:.0f} dni" if pd.notnull(x) else "Brak")
        formatted_df.columns = ['Technologia', 'Liczba Ofert', 'Mediana Zarobków', 'Czas na Rynku', 'Z widełkami (%)']
        st.dataframe(formatted_df, use_container_width=True, hide_index=True)

st.markdown("---")
st.header("📊 Ogólny przegląd rynku IT")

# Set Seaborn theme for consistent styling
sns.set_theme(style="whitegrid")

st.subheader("Popularność technologii w ofertach pracy")

# Create two new tabs for the technology section
tab_top, tab_bottom = st.tabs(["🔥 Główne Technologie (Czerwony Ocean)", "🧊 Rzadkie Technologie (Nisze)"])

with tab_top:
    st.caption("Najczęściej wymagane umiejętności. Duża konkurencja, ale najwięcej ofert.")
    fig_tech_top, ax_tech_top = plt.subplots(figsize=(10, 6))
    top_20_techs = df_exploded["Technologia_Pojedyncza"].value_counts().head(20)
    sns.countplot(data=df_exploded[df_exploded["Technologia_Pojedyncza"].isin(top_20_techs.index)], y="Technologia_Pojedyncza", order=top_20_techs.index, palette='viridis', ax=ax_tech_top)
    ax_tech_top.set_title("Top 20 Najpopularniejszych Technologii", pad=10)
    ax_tech_top.set_xlabel("Liczba Ofert")
    ax_tech_top.set_ylabel("")
    st.pyplot(fig_tech_top)

with tab_bottom:
    st.caption(f"Technologie odfiltrowane według Twoich suwaków: od {min_jobs} do {max_jobs} ofert.")
    fig_tech_bottom, ax_tech_bottom = plt.subplots(figsize=(10, 6))
    all_counts = df_exploded["Technologia_Pojedyncza"].value_counts()
    niche_counts = all_counts[(all_counts >= min_jobs) & (all_counts <= max_jobs)]
    bottom_20_techs = niche_counts.tail(20)
    
    if bottom_20_techs.empty:
        st.warning("Zbyt wąski przedział suwaków.")
    else:
        sns.countplot(data=df_exploded[df_exploded["Technologia_Pojedyncza"].isin(bottom_20_techs.index)], y="Technologia_Pojedyncza", order=bottom_20_techs.index, palette='magma', ax=ax_tech_bottom)
        ax_tech_bottom.set_title(f"Top 20 Najrzadszych Technologii ({min_jobs}-{max_jobs} ofert)", pad=10)
        ax_tech_bottom.set_xlabel("Liczba Ofert")
        ax_tech_bottom.set_ylabel("")
        st.pyplot(fig_tech_bottom)

# Wynagrodzenia (Zakładki)
st.markdown("<br>", unsafe_allow_html=True)
tab_hist, tab_box = st.tabs(["📈 Rozkład Wynagrodzeń", "📦 Zakresy Wynagrodzeń"])

with tab_hist:
    st.caption("Dystrybucja dolnych (niebieski) i górnych (czerwony) widełek płacowych.")
    fig_hist, ax_hist = plt.subplots(figsize=(10, 5))
    sns.histplot(data=df_raw, x='Wynagrodzenie Od', bins=50, kde=True, color='#4e79a7', label='Zarobki Od', element="step", ax=ax_hist)
    sns.histplot(data=df_raw, x='Wynagrodzenie Do', bins=50, kde=True, color='#e15759', alpha=0.5, label='Zarobki Do', element="step", ax=ax_hist)
    ax_hist.set_title("Rozkład widełek płacowych (PLN)")
    ax_hist.set_xlabel("Kwota (PLN)")
    ax_hist.set_ylabel("Liczba ofert")
    ax_hist.legend()
    st.pyplot(fig_hist)

with tab_box:
    st.caption("Kwartyle i wartości odstające w ofertach pracy.")
    fig_box, ax_box = plt.subplots(figsize=(10, 5))
    sns.boxplot(data=df_raw[["Wynagrodzenie Od", "Wynagrodzenie Do"]], palette=["#4e79a7", "#e15759"], width=0.5, ax=ax_box)
    ax_box.set_xticks([0, 1])
    ax_box.set_xticklabels(["Zarobki Od", "Zarobki Do"])
    ax_box.set_title("Zakresy wynagrodzeń miesięcznych (PLN)")
    st.pyplot(fig_box)