import streamlit as st
import pandas as pd
from datetime import datetime

# 📐 Streamlit Seitenkonfiguration
st.set_page_config(
    page_title="Zeitdatenanalyse Dashboard",
    page_icon="📊",
    layout="wide"
)

# 🎛️ Sidebar – Navigation & Info
with st.sidebar:
    st.markdown("### 🧭 Navigation")
    
    page = st.radio(
        label="Menü",
        options=[
            "📁 Daten hochladen",
            "🧠 Zweck-Kategorisierung",
            "📊 Analyse & Visualisierung",
            "⬇️ Export"
        ],
        label_visibility="collapsed",
        index=0
    )

    st.markdown("---")
    st.markdown("### ℹ️ Info")
    st.markdown("Baustatus: **UI-Prototyp**")
    st.caption("Funktionen werden schrittweise aktiviert.")

    st.markdown("---")
    st.markdown("👤 **Max KI Dashboard**  \nVersion 0.1 – Juli 2025")

# 🧱 Dummy-Daten (temporär bis Excel-Upload aktiv ist)
@st.cache_data
def load_dummy_data():
    return pd.DataFrame({
        "Mitarbeiter": ["Anna", "Ben", "Anna", "Clara", "Ben"],
        "Projekt": ["Projekt X", "Projekt Y", "Projekt X", "Projekt Z", "Projekt Y"],
        "Zweck": ["Analyse", "Meeting", "Workshop", "Analyse", "Schulung"],
        "Datum": pd.to_datetime(["2024-01-10", "2024-01-15", "2024-02-05", "2024-02-20", "2024-03-10"]),
        "Stunden": [3.5, 2.0, 5.0, 4.0, 6.0]
    })

df = load_dummy_data()

# 📁 Seite 1 – Upload
if page == "📁 Daten hochladen":
    st.title("📁 Excel-Datei hochladen")
    st.markdown("Hier kannst du deine Excel-Zeitdaten hochladen und validieren.")
    
    uploaded_file = st.file_uploader("Wähle eine `.xlsx` Datei", type=["xlsx"])
    if uploaded_file:
        st.success("✅ Datei erfolgreich hochgeladen (Verarbeitung folgt).")
        # TODO: parse Excel
    else:
        st.info("Beispieldaten werden verwendet.")
        st.dataframe(df)

# 🧠 Seite 2 – Zweck-Kategorisierung
elif page == "🧠 Zweck-Kategorisierung":
    st.title("🧠 Zweck-Kategorisierung")
    st.markdown("Bekannte Zwecke werden automatisch zugeordnet. Unbekannte Zwecke kannst du später per KI analysieren lassen.")
    st.warning("⚠️ Funktion noch nicht implementiert.")
    st.dataframe(df[["Zweck"]].drop_duplicates())

# 📊 Seite 3 – Analyse & Visualisierung
elif page == "📊 Analyse & Visualisierung":
    st.title("📊 Analyse & Visualisierung")
    st.markdown("Hier erscheinen später interaktive Diagramme zu Zeitaufwand, Kategorien und Projekten.")

    col1, col2 = st.columns(2)
    with col1:
        st.selectbox("🔎 Wähle Mitarbeiter", options=["Alle", "Anna", "Ben", "Clara"])
    with col2:
        st.selectbox("📅 Zeitraum", options=["Alle", "2024-01", "2024-02", "2024-03"])

    st.info("📉 Diagramm-Platzhalter (Plot folgt)")
    # TODO: Plotly Diagramm

# ⬇️ Seite 4 – Export
elif page == "⬇️ Export":
    st.title("⬇️ Export der aggregierten Daten")
    st.markdown("Hier kannst du deine Auswertung als Excel-Datei herunterladen.")
    st.download_button("Download Excel-Datei", data=b"", file_name="zeitdaten_auswertung.xlsx", disabled=True)
