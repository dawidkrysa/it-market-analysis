"""
Radar Mikro-nisz - Blue Ocean Strategy Module.

This module helps identify 'blue oceans' in the IT job market:
high-paying, high-demand, but low-supply technology niches.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.db_handler import SALARY_TYPE_COLUMNS, DatabaseHandler

BOOTSTRAP_RESAMPLES = 2000
RELIABLE_N = 10  # below this many salary observations a median is flagged as shaky


def bootstrap_median_ci(values: np.ndarray, alpha: float = 0.05) -> tuple[float, float]:
    """
    Percentile-bootstrap confidence interval for the median.

    Args:
        values (np.ndarray): Salary observations (no NaN).
        alpha (float): Significance level (0.05 -> 95% interval).

    Returns:
        tuple[float, float]: Lower and upper bound; (nan, nan) for fewer than 2 values.
    """
    if len(values) < 2:
        return float("nan"), float("nan")
    rng = np.random.default_rng(42)  # fixed seed -> stable chart between reruns
    medians = np.median(
        rng.choice(values, size=(BOOTSTRAP_RESAMPLES, len(values)), replace=True), axis=1
    )
    low, high = np.quantile(medians, [alpha / 2, 1 - alpha / 2])
    return float(low), float(high)


# --- Header and Description ---
st.title("Strategia Błękitnego Oceanu ")

st.markdown("""
**Odkryj ukryty potencjał polskiego rynku IT.** Ten moduł służy do identyfikacji tzw. "błękitnych oceanów" – wysokopłatnych i deficytowych technologii, które są często pomijane w standardowych bootcampach. 

Zamiast konkurować w przesyconych obszarach, zoptymalizuj ścieżkę kariery bazując na danych.
""")

st.info(
    "**Wskazówka:** Użyj suwaków w panelu bocznym, aby zdefiniować własne ramy dla wielkości niszy rynkowej."
)

# --- Sidebar: Salary type selector ---
st.sidebar.markdown("### Typ wynagrodzenia")
typ_wynagrodzenia = st.sidebar.selectbox(
    "Widełki do analizy:",
    options=list(SALARY_TYPE_COLUMNS.keys()),
    help=(
        "Każda oferta może mieć kilka wariantów wynagrodzenia naraz "
        "(UoP, B2B, stawka godzinowa) — wybierz, który ma być porównywany."
    ),
)

unit_label = "PLN/h" if typ_wynagrodzenia == "Stawka godzinowa" else "PLN"

# --- Sidebar: User-defined parameters for niche sizing ---
st.sidebar.markdown("### Parametry Niszy")
min_jobs = st.sidebar.slider(
    "Minimalna liczba ofert",
    min_value=1,
    max_value=50,
    value=15,
    step=1,
    help="Wiarygodność rynku – odrzuca anomalie.",
)
max_jobs = st.sidebar.slider(
    "Maksymalna liczba ofert",
    min_value=30,
    max_value=200,
    value=70,
    step=1,
    help="Brak nasycenia – odrzuca 'czerwone oceany'.",
)

min_n_salary = st.sidebar.slider(
    "Min. ofert z widełkami (n)",
    min_value=1,
    max_value=30,
    value=5,
    step=1,
    help=(
        "Mediana z kilku ogłoszeń jest niewiarygodna - nisze z mniejszą liczbą "
        "obserwacji płacowych są pomijane."
    ),
)


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
    st.error(f"Błąd połączenia: {e}")
    st.stop()

# --- Data Processing: Download and analyze data with a loading spinner ---
with st.spinner("Przetwarzanie tysięcy ofert pracy... "):
    try:
        df_raw, df_exploded, niche_analysis = DatabaseHandler.get_cached_market_data(
            typ_wynagrodzenia
        )

        if not niche_analysis.empty:
            df_niches = db._filter_viable_niches(niche_analysis, min_jobs, max_jobs)
            df_niches = df_niches[df_niches["Liczba_Ofert_Z_Widelkami"] >= min_n_salary]
        else:
            df_niches = pd.DataFrame()
    except Exception as e:
        st.error(f"Błąd: {e}")
        st.stop()

# --- Results Presentation ---
if df_niches is None or df_niches.empty:
    st.warning(
        f"Brak technologii spełniających kryterium {min_jobs} - {max_jobs} ofert. Zmień parametry."
    )
else:
    # KPI Metrics
    st.markdown("### Lider Zestawienia")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Zidentyfikowane nisze", len(df_niches))
    col2.metric("Najlepsza technologia", df_niches.iloc[0]["Technologia_Pojedyncza"].title())
    col3.metric("Mediana zarobków", f"{df_niches.iloc[0]['Mediana_Zarobkow']:,.0f} PLN")

    top_transparency = df_niches.iloc[0]["Procent_Ofert_Z_Widelkami"]
    transparency_label = (
        "wysoka" if top_transparency >= 50 else ("średnia" if top_transparency >= 25 else "niska")
    )
    col4.metric(
        "Transparentność danych",
        f"{transparency_label} ({top_transparency:.1f}%)",
        help="wysoka ≥50%, średnia ≥25%, niska <25%",
    )

    # Warning for low data quality (low salary transparency)
    low_quality_niches = df_niches[df_niches["Procent_Ofert_Z_Widelkami"] < 25]
    if len(low_quality_niches) > 0:
        st.warning(
            f"{len(low_quality_niches)} z {len(df_niches)} nisz ma niską transparentność płacową (<25%). Ich mediany mogą być zawyżone."
        )

    st.markdown("---")
    st.subheader("Mapa Nisz: popyt vs wynagrodzenie")
    st.markdown(
        "*Oś X (skala log) = liczba ofert, oś Y = mediana płac, rozmiar = liczba ofert z "
        "widełkami (n), kolor = czas aktywności ogłoszenia. Linie przerywane to mediany "
        "całego zestawu - lewy górny róg to kandydaci na błękitny ocean.*"
    )
    bubble = df_niches.dropna(subset=["Mediana_Zarobkow", "Sredni_Czas_Zatrudnienia"]).copy()
    bubble["Sredni_Czas_Zatrudnienia"] = bubble["Sredni_Czas_Zatrudnienia"].round(1)
    fig_map = px.scatter(
        bubble,
        x="Liczba_Ofert",
        y="Mediana_Zarobkow",
        size="Liczba_Ofert_Z_Widelkami",
        color="Sredni_Czas_Zatrudnienia",
        hover_name="Technologia_Pojedyncza",
        hover_data={
            "Procent_Ofert_Z_Widelkami": ":.1f",
            "Liczba_Ofert_Z_Widelkami": True,
            "Liczba_Ofert": True,
            "Sredni_Czas_Zatrudnienia": ":.1f",
        },
        log_x=True,
        color_continuous_scale="Blues",
        labels={
            "Liczba_Ofert": "Liczba ofert (log)",
            "Mediana_Zarobkow": f"Mediana ({unit_label})",
            "Liczba_Ofert_Z_Widelkami": "n z widełkami",
            "Sredni_Czas_Zatrudnienia": "Czas na rynku (dni)",
            "Procent_Ofert_Z_Widelkami": "Transparentność (%)",
        },
    )
    fig_map.add_vline(x=bubble["Liczba_Ofert"].median(), line_dash="dash", line_color="grey")
    fig_map.add_hline(y=bubble["Mediana_Zarobkow"].median(), line_dash="dash", line_color="grey")
    st.plotly_chart(fig_map, width="stretch")

    st.subheader("Top 15 Nisz z przedziałami ufności")
    st.markdown(
        f"*Słupek = mediana, wąsy = 95% przedział ufności mediany (bootstrap, "
        f"{BOOTSTRAP_RESAMPLES} losowań). Szare słupki: mniej niż {RELIABLE_N} obserwacji "
        "płacowych - traktuj ostrożnie.*"
    )
    top_15 = df_niches.head(15).copy().dropna(subset=["Mediana_Zarobkow"])
    salary_by_tech = {
        tech: grp["Srednia_Kwota"].dropna().to_numpy()
        for tech, grp in df_exploded[
            df_exploded["Technologia_Pojedyncza"].isin(top_15["Technologia_Pojedyncza"])
        ].groupby("Technologia_Pojedyncza")
    }
    ci = [
        bootstrap_median_ci(salary_by_tech.get(t, np.array([])))
        for t in top_15["Technologia_Pojedyncza"]
    ]
    top_15["ci_low"] = [c[0] for c in ci]
    top_15["ci_high"] = [c[1] for c in ci]
    reliable = top_15["Liczba_Ofert_Z_Widelkami"] >= RELIABLE_N
    fig = go.Figure(
        go.Bar(
            x=top_15["Technologia_Pojedyncza"],
            y=top_15["Mediana_Zarobkow"],
            marker_color=np.where(reliable, "#4e79a7", "#b0b0b0"),
            error_y={
                "type": "data",
                "symmetric": False,
                "array": (top_15["ci_high"] - top_15["Mediana_Zarobkow"]).fillna(0),
                "arrayminus": (top_15["Mediana_Zarobkow"] - top_15["ci_low"]).fillna(0),
            },
            customdata=top_15[
                ["Liczba_Ofert", "Liczba_Ofert_Z_Widelkami", "Procent_Ofert_Z_Widelkami"]
            ],
            hovertemplate=(
                "<b>%{x}</b><br>Mediana: %{y:,.0f}<br>Ofert: %{customdata[0]}"
                "<br>n z widełkami: %{customdata[1]}"
                "<br>Transparentność: %{customdata[2]:.1f}%<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        yaxis_title=f"Mediana ({unit_label})", xaxis_title="Technologia", showlegend=False
    )
    st.plotly_chart(fig, width="stretch")

    # Detailed data table expander
    with st.expander("Tabela: Pełne zestawienie analityczne"):
        formatted_df = df_niches.copy()
        formatted_df["Mediana_Zarobkow"] = formatted_df["Mediana_Zarobkow"].apply(
            lambda x: f"{x:,.2f} PLN".replace(",", " ") if pd.notnull(x) else "Brak"
        )
        formatted_df["Sredni_Czas_Zatrudnienia"] = formatted_df["Sredni_Czas_Zatrudnienia"].apply(
            lambda x: f"{x:.0f} dni" if pd.notnull(x) else "Brak"
        )
        formatted_df.columns = [
            "Technologia",
            "Liczba Ofert",
            "Mediana Zarobków",
            "Czas na Rynku",
            "Z widełkami (%)",
            "n z widełkami",
        ]
        st.dataframe(formatted_df, width="stretch", hide_index=True)

# --- General Market Overview ---
st.markdown("---")
st.header("Ogólny przegląd rynku IT")

st.subheader("Popularność technologii w ofertach pracy")

# Create tabs for technology popularity sections
tab_top, tab_bottom = st.tabs(
    ["Główne Technologie (Czerwony Ocean)", "Rzadkie Technologie (Nisze)"]
)

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
        orientation="h",
        color="Liczba Ofert",
        color_continuous_scale="viridis",
        title="Top 20 Najpopularniejszych Technologii",
    )
    # Sort so the most popular technology is at the top and hide the color scale
    fig_tech_top.update_layout(
        yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False
    )

    # Display the chart stretching to the full column width
    st.plotly_chart(fig_tech_top, width="stretch")

with tab_bottom:
    st.caption(
        f"Technologie odfiltrowane według Twoich suwaków: od {min_jobs} do {max_jobs} ofert."
    )

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
            orientation="h",
            color="Liczba Ofert",
            color_continuous_scale="magma",
            title=f"Top 20 Najrzadszych Technologii ({min_jobs}-{max_jobs} ofert)",
        )
        fig_tech_bottom.update_layout(
            yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False
        )
        st.plotly_chart(fig_tech_bottom, width="stretch")

# --- Salary Distributions (Tabs) ---
st.markdown("<br>", unsafe_allow_html=True)
st.header("Rozkład wynagrodzeń")
st.caption(
    f"Typ wynagrodzenia: **{typ_wynagrodzenia}**. Analizujemy środek widełek (Od+Do)/2 - "
    "jedną wartość na ofertę, zamiast dwóch zależnych od siebie rozkładów."
)
tab_hist, tab_box = st.tabs(["Rozkład ogólny", "Rozkład per technologia"])

with tab_hist:
    midpoints = df_raw["Srednia_Kwota"].dropna()
    if midpoints.empty:
        st.warning("Brak ofert z widełkami dla wybranego typu wynagrodzenia.")
    else:
        fig_hist = px.histogram(
            midpoints.to_frame("Kwota"),
            x="Kwota",
            nbins=50,
            title=f"Środek widełek - {typ_wynagrodzenia} (n={len(midpoints)})",
            labels={"Kwota": f"Środek widełek ({unit_label})"},
            color_discrete_sequence=["#4e79a7"],
        )
        fig_hist.add_vline(
            x=midpoints.median(),
            line_dash="dash",
            annotation_text=f"mediana {midpoints.median():,.0f}",
        )
        fig_hist.update_layout(yaxis_title="Liczba ofert")
        st.plotly_chart(fig_hist, width="stretch")

with tab_box:
    tech_counts = df_exploded.dropna(subset=["Srednia_Kwota"])[
        "Technologia_Pojedyncza"
    ].value_counts()
    eligible = tech_counts[tech_counts >= min_n_salary]
    if eligible.empty:
        st.warning("Żadna technologia nie ma wystarczająco obserwacji płacowych (zmniejsz n).")
    else:
        default_techs = (
            df_niches["Technologia_Pojedyncza"].head(8).tolist()
            if not df_niches.empty
            else eligible.index[:8].tolist()
        )
        default_techs = [t for t in default_techs if t in eligible.index]
        chosen = st.multiselect(
            "Technologie do porównania:", options=list(eligible.index), default=default_techs
        )
        if chosen:
            subset = df_exploded[df_exploded["Technologia_Pojedyncza"].isin(chosen)].dropna(
                subset=["Srednia_Kwota"]
            )
            order = list(
                subset.groupby("Technologia_Pojedyncza")["Srednia_Kwota"]
                .median()
                .sort_values(ascending=False)
                .index
            )
            n_labels = subset["Technologia_Pojedyncza"].value_counts()
            fig_box = px.box(
                subset,
                x="Technologia_Pojedyncza",
                y="Srednia_Kwota",
                points="outliers",
                category_orders={"Technologia_Pojedyncza": order},
                labels={
                    "Technologia_Pojedyncza": "Technologia",
                    "Srednia_Kwota": f"Środek widełek ({unit_label})",
                },
                title="Rozkład wynagrodzeń per technologia (posortowane wg mediany)",
            )
            fig_box.update_xaxes(
                tickvals=order, ticktext=[f"{t}<br>n={n_labels[t]}" for t in order]
            )
            st.plotly_chart(fig_box, width="stretch")
