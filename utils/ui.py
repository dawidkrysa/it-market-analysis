"""
Shared UI building blocks, so every page's sidebar reads the same way.

Sidebar order across pages: "Typ wynagrodzenia" first, then page-specific filters.
"""

import streamlit as st

from utils.db_handler import SALARY_TYPE_COLUMNS


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
