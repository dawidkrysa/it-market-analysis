"""
Shared chart styling for every page.

One restrained, colour-blind-safe palette (validated reference palette: categorical
slots in fixed order, a single-hue blue sequential ramp) instead of per-chart colour
scales. Light and dark steps are separate; `palette()` picks the set matching the
viewer's active Streamlit theme.
"""

from dataclasses import dataclass

import plotly.express as px
import streamlit as st


@dataclass(frozen=True)
class Palette:
    """Colour roles used by the charts."""

    accent: str  # the single series colour / "our" data
    highlight: str  # the one mark the user picked (contrasts with accent)
    neutral: str  # de-emphasised marks (e.g. unreliable estimates)
    categorical: tuple[str, ...]  # fixed-order slots for multi-series charts
    sequential: tuple[str, ...]  # single-hue ramp for magnitude, light -> dark


LIGHT = Palette(
    accent="#2a78d6",
    highlight="#eb6834",
    neutral="#c3c2b7",
    categorical=("#2a78d6", "#eb6834", "#1baf7a"),
    sequential=("#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"),
)
DARK = Palette(
    accent="#3987e5",
    highlight="#d95926",
    neutral="#52514e",
    categorical=("#3987e5", "#d95926", "#199e70"),
    sequential=("#0d366b", "#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4", "#cde2fb"),
)


def palette() -> Palette:
    """
    Return the palette for the viewer's active Streamlit theme.

    Returns:
        Palette: DARK when the app renders in dark mode, LIGHT otherwise.
    """
    try:
        is_dark = st.context.theme.type == "dark"
    except Exception:  # outside a running app (e.g. bare scripts)
        is_dark = False
    pal = DARK if is_dark else LIGHT
    # Defaults for every Plotly Express chart that doesn't set colours itself.
    px.defaults.color_discrete_sequence = list(pal.categorical)
    px.defaults.color_continuous_scale = list(pal.sequential)
    return pal
