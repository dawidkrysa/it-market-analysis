"""
Radar Mikro-nisz - Blue Ocean Strategy Module.

This module helps identify 'blue oceans' in the IT job market:
high-paying, high-demand, but low-supply technology niches.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from utils.db_handler import DatabaseHandler

# --- Header and Description ---
st.title("Strategia Błękitnego Oceanu 🌊")

st.markdown("""
**Odkryj ukryty potencjał polskiego rynku IT.** Ten moduł służy do identyfikacji tzw. "błękitnych oceanów" – wysokopłatnych i deficytowych technologii, które są często pomijane w standardowych bootcampach. 

Zamiast konkurować w przesyconych obszarach, zoptymalizuj ścieżkę kariery bazując na danych.
""")

st.info("💡 **Wskazówka:** Użyj suwaków w panelu bocznym, aby zdefiniować własne ramy dla wielkości niszy rynkowej.")

# --- Sidebar: User-defined parameters for niche sizing ---
st.sidebar.markdown("### Parametry Niszy")
min_jobs = st.sidebar.slider("Minimalna liczba ofert", min_value=1, max_value=50, value=15, step=1,
                             help="Wiarygodność rynku – odrzuca anomalie.")
max_jobs = st.sidebar.slider("Maksymalna liczba ofert", min_value=30, max_value=200, value=70, step=1,
                             help="Brak nasycenia – odrzuca 'czerwone oceany'.")


@st.cache_resource
def get_db_handler() -> DatabaseHandler:
    """
    Initialize and cache the database handler.

    Prevents reinitialization of the database connection on every user interaction.
    """
    return DatabaseHandler()


# Database connection handling
try:
    db = get_db_handler()
except Exception as e:
    st.error(f"❌ Błąd połączenia: {e}")
    st.stop()

# --- Data Processing: Download and analyze data with a loading spinner ---
with st.spinner("Przetwarzanie tysięcy ofert pracy... "):
    try:
        df_raw, df_exploded, niche_analysis = DatabaseHandler.get_cached_market_data()

        if not niche_analysis.empty:
            df_niches = db._filter_viable_niches(niche_analysis, min_jobs, max_jobs)
        else:
            df_niches = pd.DataFrame()
    except Exception as e:
        st.error(f"❌ Błąd: {e}")
        st.stop()

# --- Results Presentation ---
if df_niches is None or df_niches.empty:
    st.warning(f"⚠️ Brak technologii spełniających kryterium {min_jobs} - {max_jobs} ofert. Zmień parametry.")
else:
    # KPI Metrics
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

    # Warning for low data quality (low salary transparency)
    low_quality_niches = df_niches[df_niches['Procent_Ofert_Z_Widelkami'] < 25]
    if len(low_quality_niches) > 0:
        st.warning(
            f"⚠️ {len(low_quality_niches)} z {len(df_niches)} nisz ma niską transparentność płacową (<25%). Ich mediany mogą być zawyżone.")

    st.markdown("---")
    st.subheader("Wizualizacja Top 15 Nisz")

    # Replaced st.info with standard markdown for a cleaner look
    st.markdown("*Wysokość słupka = zarobki. Kolor = czas aktywności ogłoszenia (ciemniejszy = trudniej zrekrutować).*")

    top_15 = df_niches.head(15).copy().dropna(subset=['Mediana_Zarobkow', 'Sredni_Czas_Zatrudnienia'])
    top_15['Mediana_Zarobkow'] = top_15['Mediana_Zarobkow'].round(2)
    top_15['Sredni_Czas_Zatrudnienia'] = top_15['Sredni_Czas_Zatrudnienia'].round(2)
    top_15['Jakosc_Danych'] = top_15['Procent_Ofert_Z_Widelkami'].apply(
        lambda x: '🟢' if x >= 50 else ('🟡' if x >= 25 else '🔴'))

    # Create the Top 15 Niches bar chart
    fig = px.bar(
        top_15,
        x='Technologia_Pojedyncza',
        y='Mediana_Zarobkow',
        color='Sredni_Czas_Zatrudnienia',
        hover_data={'Procent_Ofert_Z_Widelkami': ':.1f', 'Jakosc_Danych': True, 'Liczba_Ofert': True,
                    'Technologia_Pojedyncza': False},
        color_continuous_scale='Blues',
        labels={
            'Technologia_Pojedyncza': 'Technologia',
            'Mediana_Zarobkow': 'Mediana (PLN)',
            'Sredni_Czas_Zatrudnienia': 'Czas na Rynku (Dni)'
        },
        title="Opłacalność vs. Deficyt Kandydatów"
    )
    fig.update_layout(xaxis={'categoryorder': 'total descending'})
    st.plotly_chart(fig, width="stretch")

    # Detailed data table expander
    with st.expander("Tabela: Pełne zestawienie analityczne"):
        formatted_df = df_niches.copy()
        formatted_df['Mediana_Zarobkow'] = formatted_df['Mediana_Zarobkow'].apply(
            lambda x: f"{x:,.2f} PLN".replace(',', ' ') if pd.notnull(x) else "Brak")
        formatted_df['Sredni_Czas_Zatrudnienia'] = formatted_df['Sredni_Czas_Zatrudnienia'].apply(
            lambda x: f"{x:.0f} dni" if pd.notnull(x) else "Brak")
        formatted_df.columns = ['Technologia', 'Liczba Ofert', 'Mediana Zarobków', 'Czas na Rynku', 'Z widełkami (%)']
        st.dataframe(formatted_df, width="stretch", hide_index=True)

# --- General Market Overview ---
st.markdown("---")
st.header("📊 Ogólny przegląd rynku IT")

st.subheader("Popularność technologii w ofertach pracy")

# Create tabs for technology popularity sections
tab_top, tab_bottom = st.tabs(["🔥 Główne Technologie (Czerwony Ocean)", "🧊 Rzadkie Technologie (Nisze)"])

with tab_top:
    st.caption("Najczęściej wymagane umiejętności. Duża konkurencja, ale najwięcej ofert.")

    # Prepare data for Plotly (Top 20 most popular technologies)
    top_20_techs = df_exploded["Technologia_Pojedyncza"].value_counts().head(20).reset_index()
    top_20_techs.columns = ["Technologia", "Liczba Ofert"]

    # Create an interactive horizontal bar chart
    fig_tech_top = px.bar(
        top_20_techs,
        x="Liczba Ofert",
        y="Technologia",
        orientation='h',
        color="Liczba Ofert",
        color_continuous_scale="viridis",
        title="Top 20 Najpopularniejszych Technologii"
    )
    # Sort so the most popular technology is at the top and hide the color scale
    fig_tech_top.update_layout(yaxis={'categoryorder': 'total ascending'}, coloraxis_showscale=False)

    # Display the chart stretching to the full column width
    st.plotly_chart(fig_tech_top, width="stretch")

with tab_bottom:
    st.caption(f"Technologie odfiltrowane według Twoich suwaków: od {min_jobs} do {max_jobs} ofert.")

    # Prepare data for the rarest technologies within user-defined boundaries
    all_counts = df_exploded["Technologia_Pojedyncza"].value_counts()
    niche_counts = all_counts[(all_counts >= min_jobs) & (all_counts <= max_jobs)]
    bottom_20_techs = niche_counts.tail(20).reset_index()
    bottom_20_techs.columns = ["Technologia", "Liczba Ofert"]

    if bottom_20_techs.empty:
        st.warning("Zbyt wąski przedział suwaków.")
    else:
        fig_tech_bottom = px.bar(
            bottom_20_techs,
            x="Liczba Ofert",
            y="Technologia",
            orientation='h',
            color="Liczba Ofert",
            color_continuous_scale="magma",
            title=f"Top 20 Najrzadszych Technologii ({min_jobs}-{max_jobs} ofert)"
        )
        fig_tech_bottom.update_layout(yaxis={'categoryorder': 'total ascending'}, coloraxis_showscale=False)
        st.plotly_chart(fig_tech_bottom, width="stretch")

# --- Salary Distributions (Tabs) ---
st.markdown("<br>", unsafe_allow_html=True)
tab_hist, tab_box = st.tabs(["📈 Rozkład Wynagrodzeń", "📦 Zakresy Wynagrodzeń"])

# Prepare data (Melt) - Plotly handles overlaid charts much better when data is in a long format
df_wages = df_raw[['Wynagrodzenie Od', 'Wynagrodzenie Do']].melt(
    var_name='Typ',
    value_name='Kwota'
)

with tab_hist:
    st.caption("Dystrybucja dolnych (niebieski) i górnych (czerwony) widełek płacowych.")

    fig_hist = px.histogram(
        df_wages,
        x="Kwota",
        color="Typ",
        barmode="overlay",  # Overlay the bars
        nbins=50,
        color_discrete_map={'Wynagrodzenie Od': '#4e79a7', 'Wynagrodzenie Do': '#e15759'},
        title="Rozkład widełek płacowych (PLN)",
        labels={"Kwota": "Kwota (PLN)"}
    )
    # Increase transparency to show overlapping data points
    fig_hist.update_traces(opacity=0.75)
    # Hide the default legend title for a cleaner UI
    fig_hist.update_layout(legend_title_text='')

    st.plotly_chart(fig_hist, width="stretch")

with tab_box:
    st.caption("Kwartyle i wartości odstające w ofertach pracy.")

    fig_box = px.box(
        df_wages,
        x="Typ",
        y="Kwota",
        color="Typ",
        color_discrete_map={'Wynagrodzenie Od': '#4e79a7', 'Wynagrodzenie Do': '#e15759'},
        title="Zakresy wynagrodzeń miesięcznych (PLN)",
        labels={"Kwota": "Kwota (PLN)", "Typ": ""}
    )
    # Hide legend as the X-axis already describes the data types
    fig_box.update_layout(showlegend=False)

    st.plotly_chart(fig_box, width="stretch")