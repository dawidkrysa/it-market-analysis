"""
Shared UI building blocks, so every page's sidebar reads the same way.

Sidebar order across pages: "Typ wynagrodzenia" first, then "Poziom doświadczenia"
(candidate pages), then page-specific filters.
"""

from collections.abc import Iterable

import pandas as pd
import streamlit as st

from utils.db_handler import SALARY_TYPE_COLUMNS

# Display labels for the seniority levels stored in job_postings.poziom, in career order.
LEVEL_LABELS: dict[str, str] = {
    "TRAINEE": "Trainee",
    "JUNIOR": "Junior",
    "MID": "Mid",
    "SENIOR": "Senior",
}
# Levels treated as "entry level": niche thresholds are lowered when only these are chosen,
# because far fewer postings exist per technology.
ENTRY_LEVELS: frozenset[str] = frozenset({"TRAINEE", "JUNIOR"})
DEFAULT_LEVELS: list[str] = ["JUNIOR"]

# Persistent (non-widget) key: Streamlit drops a widget's state when the user navigates to
# a page that doesn't render it, so the selection is mirrored here to survive page changes.
_LEVELS_STATE_KEY = "wybrane_poziomy"
_LEVELS_WIDGET_KEY = "_level_selector_widget"


def salary_type_selector() -> tuple[str, str]:
    """
    Render the common "Typ wynagrodzenia" sidebar section.

    Returns:
        tuple[str, str]: The selected salary type (a key of `SALARY_TYPE_COLUMNS`)
            and its unit label ("PLN" or "PLN/h").
    """
    st.sidebar.markdown("### Typ wynagrodzenia")
    typ = st.sidebar.selectbox(
        "Widełki do analizy:",
        options=list(SALARY_TYPE_COLUMNS.keys()),
        help=(
            "Oferta może podawać kilka wariantów naraz (UoP brutto, B2B netto, stawka "
            "godzinowa) - analizy porównują zawsze tylko jeden z nich."
        ),
    )
    unit = "PLN/h" if typ == "Stawka godzinowa" else "PLN"
    return typ, unit


def available_levels(df_raw: pd.DataFrame) -> list[str]:
    """
    List the seniority levels present in the data, in career order.

    Args:
        df_raw (pd.DataFrame): Job postings with a "Poziom" column.

    Returns:
        list[str]: Level codes (keys of `LEVEL_LABELS`) that occur in the data.
    """
    present = set(df_raw["Poziom"].dropna().astype(str)) if "Poziom" in df_raw else set()
    return [lvl for lvl in LEVEL_LABELS if lvl in present]


def _remember_levels() -> None:
    """Mirror the widget's selection into the persistent session-state key."""
    st.session_state[_LEVELS_STATE_KEY] = list(st.session_state[_LEVELS_WIDGET_KEY])


def level_selector(levels: list[str]) -> list[str]:
    """
    Render the shared "Poziom doświadczenia" sidebar section of the candidate pages.

    Defaults to Junior (the project's core problem) and keeps the choice across pages
    for the rest of the browser session.

    Args:
        levels (list[str]): Level codes available in the data (see `available_levels`).

    Returns:
        list[str]: The selected level codes; empty if the user cleared the selection.
    """
    stored = st.session_state.get(_LEVELS_STATE_KEY, DEFAULT_LEVELS)
    if _LEVELS_WIDGET_KEY not in st.session_state:
        st.session_state[_LEVELS_WIDGET_KEY] = [lvl for lvl in stored if lvl in levels]

    st.sidebar.markdown("### Poziom doświadczenia")
    return st.sidebar.multiselect(
        "Analizuj oferty dla poziomów:",
        options=levels,
        format_func=lambda lvl: LEVEL_LABELS.get(lvl, lvl),
        key=_LEVELS_WIDGET_KEY,
        on_change=_remember_levels,
        help=(
            "Domyślnie Junior - mediany i nisze liczone są tylko z ofert na wybranych "
            "poziomach. Wybór obowiązuje na wszystkich stronach dla kandydata."
        ),
    )


def is_entry_level(levels: Iterable[str]) -> bool:
    """
    Tell whether the selection contains only entry levels (Trainee/Junior).

    Args:
        levels (Iterable[str]): Selected level codes.

    Returns:
        bool: True if non-empty and every level is in `ENTRY_LEVELS`.
    """
    levels = set(levels)
    return bool(levels) and levels <= ENTRY_LEVELS


def levels_label(levels: Iterable[str]) -> str:
    """
    Format selected levels for captions, e.g. "Junior, Mid".

    Args:
        levels (Iterable[str]): Selected level codes.

    Returns:
        str: Comma-separated display labels in career order.
    """
    chosen = set(levels)
    return ", ".join(label for lvl, label in LEVEL_LABELS.items() if lvl in chosen)
