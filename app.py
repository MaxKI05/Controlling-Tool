import streamlit as st
import pandas as pd
import re
from datetime import datetime
import os

# 📐 Layout-Konfiguration
st.set_page_config(
    page_title="Zeitdatenanalyse Dashboard",
    page_icon="📊",
    layout="wide"
)

# 📥 Excel-Laden
@st.cache_data
def load_excel(file):
    return pd.read_excel(file)

# 🔍 Zweck extrahieren
def extrahiere_zweck(text):
    if isinstance(text, str) and "-" in text:
        zweck_raw = text.split("-")[-1].strip()
        return re.sub(r"^\d+_?", "", zweck_raw)
    return None

# 🔄 df abrufen aus Session (wenn vorhanden)
df = st.session_state.get("df", None)

# 🔧 Sidebar
with st.sidebar:
    st.markdown("### 🧭 Navigation")
    page = st.radio(
        label="Menü",
        options=[
            "🏠 Start",
            "📁 Daten hochladen",
            "🧠 Zweck-Kategorisierung",
            "📊 Analyse & Visualisierung",
            "⬇️ Export"
        ],
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.markdown("👤 Max KI Dashboard v0.1")

# 🏠 Startseite
if page == "🏠 Start":
    st.title("👋 Willkommen im Zeitdatenanalyse-Dashboard")
    st.markdown("""
    Diese App hilft dir bei der Analyse und Klassifikation von Zeitbuchungsdaten.

    **Funktionen:**
    - 📁 Excel-Zeitdaten hochladen
    - 🧠 GPT-gestützte Kategorisierung (intern vs. extern)
    - 📊 Visualisierung
    - ⬇️ Exportieren
    """)

# 📁 Upload-Seite
elif page == "📁 Daten hochladen":
    st.title("📁 Excel-Datei hochladen")

    uploaded_file = st.file_uploader("Lade eine `.xlsx` Datei hoch", type=["xlsx"])

    if uploaded_file:
        df = load_excel(uploaded_file)

        if "Unterprojekt" not in df.columns:
            st.error("❌ Spalte 'Unterprojekt' nicht gefunden.")
        else:
            df["Zweck"] = df["Unterprojekt"].apply(extrahiere_zweck)
            st.session_state["df"] = df  # Speichern für andere Seiten

            st.success("✅ Datei erfolgreich geladen und verarbeitet.")
            st.subheader("📄 Extrahierte Zwecke")
            st.dataframe(df[["Unterprojekt", "Zweck"]].drop_duplicates().sort_values("Zweck"))

# 🧠 Zweck-Kategorisierung
elif page == "🧠 Zweck-Kategorisierung":
    st.title("🧠 GPT-Zweck-Kategorisierung")

    if df is None or "Zweck" not in df.columns:
        st.warning("Bitte zuerst eine Excel-Datei hochladen.")
    else:
        st.markdown("GPT entscheidet, ob ein Zweck **intern** oder **extern verrechenbar** ist.")
        unique_zwecke = df["Zweck"].dropna().unique()
        unique_zwecke.sort()

        st.write("🎯 Anzahl zu klassifizierender Zwecke:", len(unique_zwecke))

        if st.button("🚀 GPT-Klassifizierung starten"):
            from utils.gpt import klassifiziere_verrechenbarkeit

            verrechnungsergebnisse = {}
            with st.spinner("GPT denkt nach..."):
                for zweck in unique_zwecke:
                    kategorie = klassifiziere_verrechenbarkeit(zweck)
                    verrechnungsergebnisse[zweck] = kategorie

            df["Verrechenbarkeit"] = df["Zweck"].map(verrechnungsergebnisse)
            st.session_state["df"] = df  # aktualisieren

            st.success("✅ Klassifizierung abgeschlossen.")
            st.dataframe(df[["Zweck", "Verrechenbarkeit"]].drop_duplicates().sort_values("Zweck"))

            csv = df[["Zweck", "Verrechenbarkeit"]].drop_duplicates().to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Klassifizierte Liste herunterladen", data=csv, file_name="verrechenbarkeit.csv")

# 📊 Visualisierung (Platzhalter)
elif page == "📊 Analyse & Visualisierung":
    st.title("📊 Analyse & Visualisierung")

    if df is None:
        st.warning("Bitte zuerst eine Excel-Datei hochladen.")
    else:
        st.write("🔍 Vorschau auf Daten")
        st.dataframe(df.head())
        # Hier kannst du später Plotly/Charts einfügen

# ⬇️ Exportseite
elif page == "⬇️ Export":
    st.title("⬇️ Exportieren")

    if df is not None:
        excel = df.to_excel(index=False, engine='openpyxl')
        st.download_button("⬇️ Vollständige Tabelle exportieren", data=excel, file_name="zeitdaten_export.xlsx")
    else:
        st.info("Kein Datensatz zum Exportieren gefunden.")


