"""
Radar Mikro-nisz - Employer Perspective Module.

Market insights for companies hiring IT staff: a salary benchmark for a given
competence, how hard it is to hire for it, who else competes for the same
people, and data-backed hints for writing the job ad.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from scipy import stats

from utils.db_handler import SALARY_TYPE_COLUMNS, DatabaseHandler

BOOTSTRAP_RESAMPLES = 2000
RELIABLE_N = 10  # below this many observations a statistic is flagged as unreliable
LEVEL_LABELS = {"TRAINEE": "Trainee", "JUNIOR": "Junior", "MID": "Mid", "SENIOR": "Senior"}
BAR_COLOR = "#4e79a7"


def bootstrap_median_ci(values: np.ndarray, alpha: float = 0.05) -> tuple[float, float]:
    """
    Percentile-bootstrap confidence interval for the median.

    Args:
        values (np.ndarray): Observations (no NaN).
        alpha (float): Significance level (0.05 -> 95% interval).

    Returns:
        tuple[float, float]: Lower and upper bound; (nan, nan) for fewer than 2 values.
    """
    if len(values) < 2:
        return float("nan"), float("nan")
    rng = np.random.default_rng(42)  # fixed seed -> stable numbers between reruns
    medians = np.median(
        rng.choice(values, size=(BOOTSTRAP_RESAMPLES, len(values)), replace=True), axis=1
    )
    low, high = np.quantile(medians, [alpha / 2, 1 - alpha / 2])
    return float(low), float(high)


def fmt_money(value: float, unit: str) -> str:
    """Format an amount as e.g. "12 500 PLN" (or "-" when missing)."""
    if pd.isna(value):
        return "-"
    return f"{value:,.0f} {unit}".replace(",", " ")


# --- Header ---
st.title("Perspektywa Pracodawcy")
st.markdown(
    "Dane z tych samych ogłoszeń co reszta raportu, ale z pytaniami, które zadaje firma: "
    "**ile zaoferować**, **jak trudno będzie zatrudnić**, **kto jeszcze szuka tych samych ludzi** "
    "i **jak napisać ogłoszenie**."
)

# --- Sidebar filters ---
st.sidebar.markdown("### Kogo szukasz?")
typ_wynagrodzenia = st.sidebar.selectbox(
    "Forma zatrudnienia (widełki):", options=list(SALARY_TYPE_COLUMNS.keys())
)
unit = "PLN/h" if typ_wynagrodzenia == "Stawka godzinowa" else "PLN"

with st.spinner("Przetwarzanie ofert pracy..."):
    try:
        df_raw, df_exploded, _ = DatabaseHandler.get_cached_market_data(typ_wynagrodzenia)
    except Exception as e:
        st.error(f"Błąd połączenia z bazą danych: {e}")
        st.stop()

if df_raw.empty or df_exploded.empty:
    st.warning("Baza danych jest pusta - uruchom scraping w panelu administracyjnym.")
    st.stop()

available_levels = [lvl for lvl in LEVEL_LABELS if lvl in set(df_raw["Poziom"].dropna())]
poziomy = st.sidebar.multiselect(
    "Poziom doświadczenia:",
    options=available_levels,
    default=[lvl for lvl in ("JUNIOR", "MID", "SENIOR") if lvl in available_levels],
    format_func=lambda lvl: LEVEL_LABELS[lvl],
)
if not poziomy:
    st.info("Wybierz co najmniej jeden poziom doświadczenia w panelu bocznym.")
    st.stop()

market = df_raw[df_raw["Poziom"].isin(poziomy)].copy()
# Salary transparency is about disclosing *any* range, whatever the contract form.
market["Ma_Jakiekolwiek_Widelki"] = market[
    [od_col for od_col, _ in SALARY_TYPE_COLUMNS.values()]
].notna().any(axis=1)
market_tech = df_exploded[df_exploded["ID"].isin(market["ID"])]

tech_counts = market_tech["Technologia_Pojedyncza"].value_counts()
tech_options = tech_counts[tech_counts >= 5].index.tolist()
if not tech_options:
    st.warning("Za mało ofert dla wybranych filtrów.")
    st.stop()
technologia = st.sidebar.selectbox(
    "Technologia / kompetencja:",
    options=tech_options,
    format_func=lambda t: f"{t} ({tech_counts[t]} ofert)",
    help="Lista posortowana według liczby ofert; pokazane są technologie z co najmniej 5 ofertami.",
)

offer_ids = market_tech.loc[market_tech["Technologia_Pojedyncza"] == technologia, "ID"].unique()
offers = market[market["ID"].isin(offer_ids)]
salaries = offers["Srednia_Kwota"].dropna()

st.caption(
    f"Analiza: **{technologia}**, poziomy {', '.join(LEVEL_LABELS[p] for p in poziomy)}, "
    f"widełki {typ_wynagrodzenia}. Ofert z tą technologią: **{len(offers)}**, "
    f"w tym z podanymi widełkami: **{len(salaries)}**. Kwoty to środek widełek (Od+Do)/2."
)

tab_bench, tab_hard, tab_comp, tab_ad = st.tabs(
    ["Benchmark wynagrodzeń", "Trudność rekrutacji", "Konkurencja o talenty", "Pisanie ogłoszenia"]
)

# ==========================================
# TAB 1: Salary benchmark
# ==========================================
with tab_bench:
    st.subheader("Ile zaoferować?")
    if len(salaries) < 2:
        st.warning(
            "Za mało ofert z widełkami, żeby policzyć benchmark. "
            "Zmień formę zatrudnienia lub poszerz poziomy doświadczenia."
        )
    else:
        p25, med, p75 = salaries.quantile([0.25, 0.5, 0.75])
        ci_low, ci_high = bootstrap_median_ci(salaries.to_numpy())
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Dolny kwartyl (P25)", fmt_money(p25, unit), help="25% ofert płaci mniej.")
        c2.metric(
            "Mediana rynku",
            fmt_money(med, unit),
            help=f"95% przedział ufności mediany: {fmt_money(ci_low, unit)} - {fmt_money(ci_high, unit)}.",
        )
        c3.metric("Górny kwartyl (P75)", fmt_money(p75, unit), help="25% ofert płaci więcej.")
        c4.metric("Liczba obserwacji (n)", len(salaries))
        if len(salaries) < RELIABLE_N:
            st.warning(
                f"Tylko {len(salaries)} ofert z widełkami - traktuj benchmark orientacyjnie."
            )

        st.markdown("**Gdzie wypada Twoja oferta?**")
        twoja = st.number_input(
            f"Planowany środek widełek ({unit}):",
            min_value=0.0,
            value=float(round(med, -2)),
            step=100.0 if unit == "PLN/h" else 500.0,
        )
        percentile = (salaries < twoja).mean() * 100
        st.markdown(
            f"Twoja oferta jest wyższa niż **{percentile:.0f}%** ofert rynkowych dla tej kompetencji."
        )
        if percentile < 25:
            st.caption("Poniżej dolnego kwartyla - ryzyko małej liczby aplikacji.")
        elif percentile > 75:
            st.caption("Powyżej górnego kwartyla - silny argument w rekrutacji.")

        by_level = (
            offers.dropna(subset=["Srednia_Kwota"])
            .groupby("Poziom")["Srednia_Kwota"]
            .agg(
                n="count",
                P25=lambda x: x.quantile(0.25),
                Mediana="median",
                P75=lambda x: x.quantile(0.75),
            )
            .reindex([p for p in LEVEL_LABELS if p in poziomy])
            .dropna(how="all")
        )
        if not by_level.empty:
            st.markdown("**Benchmark według poziomu**")
            table = by_level.copy()
            for col in ("P25", "Mediana", "P75"):
                table[col] = table[col].map(lambda v: fmt_money(v, unit))
            table.index = [LEVEL_LABELS[i] for i in table.index]
            st.dataframe(table, width="stretch")

            plot_df = offers.dropna(subset=["Srednia_Kwota"]).copy()
            plot_df["Poziom"] = plot_df["Poziom"].map(LEVEL_LABELS)
            fig = px.box(
                plot_df,
                x="Poziom",
                y="Srednia_Kwota",
                points="outliers",
                category_orders={"Poziom": [LEVEL_LABELS[p] for p in LEVEL_LABELS]},
                labels={"Srednia_Kwota": f"Środek widełek ({unit})"},
                color_discrete_sequence=[BAR_COLOR],
            )
            st.plotly_chart(fig, width="stretch")

# ==========================================
# TAB 2: Hiring difficulty
# ==========================================
with tab_hard:
    st.subheader("Jak trudno będzie zatrudnić?")
    st.caption(
        "Miarą jest wiek aktywnych ogłoszeń w chwili ostatniego scrapingu. Portale liczą go różnie "
        "(NoFluffJobs i TheProtocol co ok. 30 dni publikują ogłoszenie na nowo, JustJoinIT trzyma "
        "pierwotną datę), więc dni nie są porównywalne między portalami. Dlatego główną miarą jest "
        "**względny wiek**: percentyl wieku ogłoszenia w obrębie jego portalu (50 = typowe "
        "ogłoszenie, wyżej = wisi dłużej niż większość). To przybliżenie trudności rekrutacji - nie "
        "wiemy, kiedy ogłoszenie faktycznie zakończyło się zatrudnieniem."
    )
    # Within-portal age percentile, so the portal mix of a technology doesn't bias it.
    age_pct = (
        market.dropna(subset=["Czas_Na_Rynku_Dni"])
        .groupby("Source")["Czas_Na_Rynku_Dni"]
        .rank(pct=True)
        .mul(100)
    )
    age_pct_by_id = pd.Series(age_pct.values, index=market.loc[age_pct.index, "ID"].values)
    pct_tech = age_pct.loc[age_pct.index.intersection(offers.index)]
    n_companies = offers["Firma"].nunique()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Względny wiek ogłoszeń",
        f"{pct_tech.median():.0f} / 100" if not pct_tech.empty else "-",
        delta=f"{pct_tech.median() - 50:+.0f} vs typowe" if not pct_tech.empty else None,
        delta_color="inverse",
        help="Mediana percentyla wieku w obrębie portalu; 50 = typowe ogłoszenie.",
    )
    c2.metric(
        "Mediana wieku (dni)",
        f"{offers['Czas_Na_Rynku_Dni'].median():.0f}" if not offers.empty else "-",
        help="Informacyjnie - zależy od miksu portali.",
    )
    c3.metric("Firmy szukające tej kompetencji", n_companies)
    c4.metric(
        "Ofert na firmę",
        f"{len(offers) / n_companies:.1f}" if n_companies else "-",
        help="Ile ogłoszeń średnio publikuje jedna firma - wysoka wartość = intensywny nabór.",
    )

    rest = age_pct.drop(pct_tech.index, errors="ignore")
    if len(pct_tech) >= RELIABLE_N and len(rest) >= RELIABLE_N:
        _, p_age = stats.mannwhitneyu(pct_tech, rest, alternative="two-sided")
        verdict = (
            "istotnie różni się od reszty rynku"
            if p_age < 0.05
            else "nie różni się istotnie od reszty rynku"
        )
        st.caption(
            f"Test Manna-Whitneya na względnym wieku: ta kompetencja {verdict} (p = {p_age:.3f})."
        )

    st.markdown("**Kompetencje, których ogłoszenia wiszą najdłużej (względnie)**")
    min_n_age = st.slider(
        "Minimalna liczba ofert technologii:",
        5,
        100,
        20,
        5,
        key="min_n_age",
        help="Odrzuca rzadkie technologie, których mediana byłaby przypadkowa.",
    )
    tech_age = market_tech.assign(Wiek_Pct=market_tech["ID"].map(age_pct_by_id)).dropna(
        subset=["Wiek_Pct"]
    )
    ages = tech_age.groupby("Technologia_Pojedyncza")["Wiek_Pct"].agg(n="count", Mediana="median")
    ages = ages[ages["n"] >= min_n_age].sort_values("Mediana", ascending=False).head(20)
    if ages.empty:
        st.info("Brak technologii spełniających próg liczby ofert.")
    else:
        ages = ages.reset_index()
        ages["Wybrana"] = np.where(
            ages["Technologia_Pojedyncza"] == technologia, "wybrana technologia", "pozostałe"
        )
        fig = px.bar(
            ages,
            x="Mediana",
            y="Technologia_Pojedyncza",
            orientation="h",
            color="Wybrana",
            color_discrete_map={"wybrana technologia": "#e15759", "pozostałe": BAR_COLOR},
            hover_data={"n": True, "Wybrana": False},
            labels={"Mediana": "Względny wiek ogłoszeń (percentyl w portalu)",
                    "Technologia_Pojedyncza": ""},
        )
        fig.add_vline(x=50, line_dash="dash", line_color="grey")
        fig.update_layout(yaxis={"categoryorder": "total ascending"}, legend_title_text="")
        st.plotly_chart(fig, width="stretch")

# ==========================================
# TAB 3: Competition for talent
# ==========================================
with tab_comp:
    st.subheader("Kto jeszcze szuka tych samych ludzi?")
    company_counts = offers["Firma"].value_counts()
    if company_counts.empty:
        st.info("Brak ofert dla wybranych filtrów.")
    else:
        top5_share = company_counts.head(5).sum() / company_counts.sum() * 100
        c1, c2 = st.columns(2)
        c1.metric("Firm rekrutujących", len(company_counts))
        c2.metric(
            "Udział 5 największych rekruterów",
            f"{top5_share:.0f}%",
            help="Wysoki udział = rynek zdominowany przez kilku dużych graczy.",
        )

        top_companies = company_counts.head(15).rename_axis("Firma").reset_index(name="Oferty")
        fig = px.bar(
            top_companies,
            x="Oferty",
            y="Firma",
            orientation="h",
            color_discrete_sequence=[BAR_COLOR],
            title="Najaktywniej rekrutujące firmy",
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, width="stretch")

        col_city, col_src = st.columns(2)
        with col_city:
            cities = (
                offers["Lokalizacja"]
                .fillna("Nieznana")
                .value_counts()
                .head(10)
                .rename_axis("Miasto")
                .reset_index(name="Oferty")
            )
            fig = px.bar(
                cities,
                x="Oferty",
                y="Miasto",
                orientation="h",
                color_discrete_sequence=[BAR_COLOR],
                title="Oferty według miasta (top 10)",
            )
            fig.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig, width="stretch")
        with col_src:
            sources = (
                offers["Source"]
                .fillna("Nieznane")
                .value_counts()
                .rename_axis("Portal")
                .reset_index(name="Oferty")
            )
            fig = px.bar(
                sources,
                x="Portal",
                y="Oferty",
                color_discrete_sequence=[BAR_COLOR],
                title="Oferty według portalu",
            )
            st.plotly_chart(fig, width="stretch")

# ==========================================
# TAB 4: Writing the job ad
# ==========================================
with tab_ad:
    st.subheader("Jakie wymagania dopisać?")
    st.caption(
        "Technologie, które najczęściej pojawiają się w ogłoszeniach razem z wybraną. "
        "**Lift** > 1 oznacza, że dana technologia występuje z wybraną częściej, niż wynikałoby "
        "z jej ogólnej popularności - to typowy element tego profilu, a nie po prostu popularny tag."
    )
    n_offers_total = market["ID"].nunique()
    co = market_tech[
        market_tech["ID"].isin(offer_ids) & (market_tech["Technologia_Pojedyncza"] != technologia)
    ]
    if co.empty or len(offer_ids) == 0:
        st.info("Brak danych o współwystępowaniu technologii.")
    else:
        co_share = co.drop_duplicates(["ID", "Technologia_Pojedyncza"])[
            "Technologia_Pojedyncza"
        ].value_counts() / len(offer_ids)
        base_share = (
            market_tech.drop_duplicates(["ID", "Technologia_Pojedyncza"])[
                "Technologia_Pojedyncza"
            ].value_counts()
            / n_offers_total
        )
        co_df = (
            pd.DataFrame(
                {"Udział": co_share * 100, "Lift": co_share / base_share.reindex(co_share.index)}
            )
            .head(15)
            .reset_index(names="Technologia")
        )
        fig = px.bar(
            co_df,
            x="Udział",
            y="Technologia",
            orientation="h",
            color_discrete_sequence=[BAR_COLOR],
            hover_data={"Lift": ":.2f"},
            labels={"Udział": f"% ofert z '{technologia}', które wymagają też tej technologii"},
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, width="stretch")

    st.markdown("---")
    st.subheader("Czy podawanie widełek skraca rekrutację?")
    st.caption(
        "Porównanie wieku aktywnych ogłoszeń z widełkami i bez nich, **osobno w każdym portalu** "
        "(test Manna-Whitneya). Portale różnią się zarówno odsetkiem ofert z widełkami, jak i "
        "typowym wiekiem ogłoszeń, więc porównanie łączne pokazywałoby głównie różnice między "
        "portalami. Ujemna różnica = ogłoszenia z widełkami są młodsze (szybciej znikają). "
        "To korelacja, nie dowód przyczynowy."
    )

    def transparency_by_portal(df: pd.DataFrame) -> pd.DataFrame:
        """
        Compare ad age with vs without a disclosed salary range, within each portal.

        Args:
            df (pd.DataFrame): Offers with "Source", "Ma_Jakiekolwiek_Widelki"
                and "Czas_Na_Rynku_Dni" columns.

        Returns:
            pd.DataFrame: One row per portal with group sizes, median ages,
                their difference and the Mann-Whitney p-value (NaN if too few data).
        """
        rows = []
        for portal, grp in df.dropna(subset=["Czas_Na_Rynku_Dni"]).groupby("Source"):
            with_salary = grp.loc[grp["Ma_Jakiekolwiek_Widelki"], "Czas_Na_Rynku_Dni"]
            without = grp.loc[~grp["Ma_Jakiekolwiek_Widelki"], "Czas_Na_Rynku_Dni"]
            enough = len(with_salary) >= RELIABLE_N and len(without) >= RELIABLE_N
            p = (
                stats.mannwhitneyu(with_salary, without, alternative="two-sided").pvalue
                if enough
                else float("nan")
            )
            rows.append(
                {
                    "Portal": portal,
                    "n z widełkami": len(with_salary),
                    "n bez widełek": len(without),
                    "Mediana z widełkami (dni)": with_salary.median(),
                    "Mediana bez widełek (dni)": without.median(),
                    "Różnica (dni)": with_salary.median() - without.median(),
                    "p": p,
                    "Wniosek": (
                        "za mało danych"
                        if not enough
                        else ("istotna różnica" if p < 0.05 else "brak istotnej różnicy")
                    ),
                }
            )
        return pd.DataFrame(rows)

    for label, subset in (
        (f"Oferty z technologią {technologia}", offers),
        ("Cały rynek (wybrane poziomy)", market),
    ):
        st.markdown(f"**{label}**")
        result = transparency_by_portal(subset)
        if result.empty:
            st.caption("Brak danych.")
        else:
            st.dataframe(
                result.round({"Mediana z widełkami (dni)": 1, "Mediana bez widełek (dni)": 1,
                              "Różnica (dni)": 1, "p": 4}),
                width="stretch",
                hide_index=True,
            )
