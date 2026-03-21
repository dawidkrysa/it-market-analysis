import streamlit as st
import pandas as pd
import plotly.express as px
from utils.db_handler import DatabaseHandler

# Header and description
st.title("Strategia Błękitnego Oceanu")

st.markdown("""
**Odkryj ukryty potencjał polskiego rynku IT.** Ten moduł analityczny służy do identyfikacji tzw. "błękitnych oceanów" – wysokopłatnych i deficytowych technologii dla stanowisk typu Junior, które są często pomijane w standardowych programach szkoleń i bootcampach. 

Zamiast konkurować w przesyconych obszarach (tzw. "czerwonych oceanach"), radar pomaga zoptymalizować ścieżkę kariery i zminimalizować koszt utraconych korzyści (Opportunity Cost).

**Jak to działa?**
Algorytm analizuje oferty pracy w czasie rzeczywistym, krzyżując dwie kluczowe metryki:
* 💰 **Premię płacową:** Mediana wynagrodzeń w danej niszy na tle ogółu rynku.
* ⏳ **Presję popytową (Time-to-Fill):** Średni czas aktywności ogłoszenia, będący wskaźnikiem braku odpowiednich kandydatów.
""")

st.info("💡 **Wskazówka:** Użyj suwaków w panelu bocznym, aby dostosować czułość radaru – zdefiniuj własne ramy dla minimalnej i maksymalnej wielkości niszy rynkowej.")

# --- Sidebar for user-defined parameters defining what constitutes a niche ---
st.sidebar.markdown("Zdefiniuj, co oznacza dla Ciebie nisza na podstawie liczby aktywnych ofert na rynku:")

min_jobs = st.sidebar.slider("Minimalna liczba ofert (wiarygodność rynku)", min_value=1, max_value=50, value=15, step=1)
max_jobs = st.sidebar.slider("Maksymalna liczba ofert (brak nasycenia)", min_value=30, max_value=200, value=70, step=1)

# Init database handler with caching to avoid reinitialization on every interaction
@st.cache_resource
def get_db_handler():
    return DatabaseHandler()

try:
    db = get_db_handler()
except Exception as e:
    st.error(f"❌ Błąd połączenia z bazą danych: {e}")
    st.stop()

# --- Download and analyze data with a spinner to indicate processing ---
with st.spinner("Trwa analiza tysięcy ofert pracy... ⏳"):
    try:
        df_niches = db.get_blue_ocean_niches(min_jobs=min_jobs, max_jobs=max_jobs)
    except Exception as e:
        st.error(f"❌ Błąd podczas analizy danych: {e}")
        st.stop()

# --- Presentation of results ---
if df_niches is None or df_niches.empty:
    st.warning(f"⚠️ Nie znaleziono żadnych technologii spełniających kryterium {min_jobs} - {max_jobs} ofert. Zmień parametry w panelu bocznym.")
else:
    # Additional check to ensure DataFrame has rows after filtering
    if len(df_niches) == 0:
        st.warning(f"⚠️ Nie znaleziono żadnych technologii spełniających kryterium {min_jobs} - {max_jobs} ofert. Zmień parametry w panelu bocznym.")
    else:
        # KPI Metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Liczba zidentyfikowanych nisz", len(df_niches))
        col2.metric("Najbardziej opłacalna nisza", df_niches.iloc[0]['Technologia_Pojedyncza'].title())
        col3.metric("Mediana zarobków lidera", f"{df_niches.iloc[0]['Mediana_Zarobkow']:,.0f} PLN")
        
        # Add quality indicator for top niche
        top_transparency = df_niches.iloc[0]['Procent_Ofert_Z_Widelkami']
        transparency_emoji = '🟢' if top_transparency >= 50 else ('🟡' if top_transparency >= 25 else '🔴')
        col4.metric(
            "Transparentność lidera",
            f"{transparency_emoji} {top_transparency:.1f}%",
            help="Procent ofert z realnymi widełkami płacowymi. 🟢≥50% 🟡≥25% 🔴<25%"
        )
        
        # Data quality warning
        low_quality_niches = df_niches[df_niches['Procent_Ofert_Z_Widelkami'] < 25]
        if len(low_quality_niches) > 0:
            st.warning(f"""
            ⚠️ **Uwaga o jakości danych**: {len(low_quality_niches)} z {len(df_niches)} nisz ma niską transparentność płacową (<25% ofert z widełkami).
            Mediana wynagrodzeń dla tych technologii jest obliczana z ograniczonej próbki i może być mniej wiarygodna.
            """)

    st.markdown("---")

    st.subheader("Wizualizacja Top 15 Nisz rynkowych")
    
    # Info box explaining the metrics
    st.info("""
    📊 **Jak interpretować wykres:**
    - **Wysokość słupka**: Mediana wynagrodzeń (wyższa = lepiej płatna nisza)
    - **Kolor słupka**: Średni czas ogłoszenia na rynku (ciemniejszy = dłużej aktywne)
    - **Transparentność danych**: % ofert z realnymi widełkami płacowymi (wyświetlane przy najechaniu)
    
    ⚠️ **Uwaga**: Długi czas na rynku może oznaczać trudności w rekrutacji (brak kandydatów) LUB niski popyt na stanowisko.
    """)
    
    top_15 = df_niches.head(15).copy()
    
    # Remove rows with missing values in critical columns to avoid errors in plotting
    top_15 = top_15.dropna(subset=['Mediana_Zarobkow', 'Sredni_Czas_Zatrudnienia'])
    
    # Round the values for better display in the tooltip
    top_15['Mediana_Zarobkow'] = top_15['Mediana_Zarobkow'].round(2)
    top_15['Sredni_Czas_Zatrudnienia'] = top_15['Sredni_Czas_Zatrudnienia'].round(2)
    
    # Create quality indicator for hover data
    top_15['Jakosc_Danych'] = top_15['Procent_Ofert_Z_Widelkami'].apply(
        lambda x: '🟢 Wysoka' if x >= 50 else ('🟡 Średnia' if x >= 25 else '🔴 Niska')
    )

    fig = px.bar(
        top_15,
        x='Technologia_Pojedyncza',
        y='Mediana_Zarobkow',
        color='Sredni_Czas_Zatrudnienia',
        hover_data={
            'Procent_Ofert_Z_Widelkami': ':.1f',
            'Jakosc_Danych': True,
            'Liczba_Ofert': True,
            'Technologia_Pojedyncza': False
        },
        color_continuous_scale='Blues',
        labels={
            'Technologia_Pojedyncza': 'Technologia',
            'Mediana_Zarobkow': 'Mediana Wynagrodzeń (PLN)',
            'Sredni_Czas_Zatrudnienia': 'Średni Czas na Rynku (Dni)',
            'Procent_Ofert_Z_Widelkami': 'Transparentność (%)',
            'Jakosc_Danych': 'Jakość danych',
            'Liczba_Ofert': 'Liczba ofert'
        },
        title="Mediana Wynagrodzeń vs Czas na Rynku (kolor = dni aktywności)"
    )
    fig.update_layout(xaxis={'categoryorder':'total descending'})
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Pełne zestawienie analityczne")
    # Format the DataFrame for better readability in the table
    formatted_df = df_niches.copy()
    formatted_df['Mediana_Zarobkow'] = formatted_df['Mediana_Zarobkow'].apply(
        lambda x: f"{x:,.2f} PLN".replace(',', ' ') if pd.notnull(x) else "Brak danych"
    )
    formatted_df['Sredni_Czas_Zatrudnienia'] = formatted_df['Sredni_Czas_Zatrudnienia'].apply(
        lambda x: f"{x:.2f} dni" if pd.notnull(x) else "Brak danych"
    )

    formatted_df.columns = [
        'Technologia',
        'Liczba Ofert',
        'Mediana Zarobków',
        'Czas na Rynku',
        'Procent ofert z widełkami (%)'
    ]
    
    st.dataframe(
        formatted_df,
        use_container_width=True,
        hide_index=True,
        height=400
    )