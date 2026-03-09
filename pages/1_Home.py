"""Radar Mikro-nisz - Main Streamlit Page.

Strona domowa aplikacji Streamlit, która wyświetla szczegóły dot. projektu
oraz wprowadzenie do analizy rynku pracy IT.
"""

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

# Podział na kolumny dla tytułu i logo
# Proporcje [4, 1] oznaczają, że lewa kolumna jest 4 razy szersza od prawej
col1: DeltaGenerator
col2: DeltaGenerator
col1, col2 = st.columns([4, 1], vertical_alignment="center")

with col1:
    st.title("Wpływ niszowości technologii IT na opłacalność i czas zatrudnienia")

with col2:
    # Parametr width pozwala wymusić stałą szerokość obrazka
    st.image("assets/wsb_logo.png", width=150)

st.markdown("---")

st.write("""
Witamy w interaktywnym raporcie naszego projektu! 
Analizujemy tu zjawiska asymetrii informacji i bezrobocia strukturalnego na obecnym rynku pracy IT.

**Czego dowiesz się z tej aplikacji?**
* Jak trendy makroekonomiczne wpłynęły na branżę.
* Które technologie to **Błękitne Oceany** (wysoki popyt, niska podaż), a które to **Czerwone Oceany** (przesycenie).
* Czy statystyka potwierdza, że za niszowe umiejętności płaci się więcej.
* Jak wygląda twardy, finansowy zwrot z inwestycji (ROI) w naukę niszowej technologii.

Wybierz interesującą Cię sekcję z menu po lewej stronie.
""")

st.info("Projekt zrealizowany w ramach przedmiotu Projekt Semestralny II.") 
st.info("Zespół: Dawid Krysa, Wojciech Pomarkiewicz, Wiktor Daniel, Krzysztof Krajewski")