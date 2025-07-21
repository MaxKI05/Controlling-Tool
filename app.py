import streamlit as st
import pandas as pd
import re
from datetime import datetime
import os

st.set_page_config(
    page_title="Zeitdatenanalyse Dashboard",
    page_icon="📊",
    layout="wide"
)

# 📁 Datei laden
@st.cache_data
def load_excel(file):
    return pd.read_excel(file)

# 🧠 Zweck aus Unterprojekt extrahieren
def extrahiere_zweck(text):
    if isinstance(text, str) and "-" in text:
        zweck_raw = text.split("-")[-1].strip()
        return re.sub(r"^\d+_?", "", zweck_raw)
    return None

# Sidebar Navigation
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
    st.markdown("### ℹ️ Info")
    st.caption("Max KI Dashboard – v0.1")

# Globaler DataFrame (wird überschrieben durch Upload)
df = None

# Startseite
if page == "🏠 Start":
    st.title("👋 Willkommen zur Zeitdatenanalyse")
    st.markdown("""
    Dieses Dashboard hilft dir, Zeitbuchungen aus Excel-Dateien zu analysieren und mit KI zu klassifizieren.

    **Was du tun kannst:**
    - 📁 Datei hochladen
    - 🧠 GPT-Kategorisierung: intern oder extern?
    - 📊 Visualisieren
    - ⬇️ Exportieren
    """)

# Upload
elif page == "📁 Daten hochladen":
    st.title("📁 Excel-Datei hochladen")

    uploaded_file = st.file_uploader("Wähle eine `.xlsx` Datei", type=["xlsx"])
    if uploaded_file:
        df = load_excel(uploaded_file)
        st.success("✅ Datei erfolgreich geladen")

        if "Unterprojekt" in df.columns:
            df["Zweck"] = df["Unterprojekt"].apply(extrahiere_zweck)
            st.subheader("📄 Extrahierte Zwecke")
            st.dataframe(df[["Unterprojekt", "Zweck"]].head())
        else:
            st.error("❌ Spalte 'Unterprojekt' nicht gefunden.")

# GPT-Zweck-Kategorisierung
elif page == "🧠 Zweck-Kategorisierung":
    st.title("🧠 Zweck-Kategorisierung")

    if df is None:
        st.warning("Bitte zuerst eine Excel-Datei hochladen.")
    elif "Zweck" not in df.columns:
        st.warning("Spalte 'Zweck' fehlt. Bitte Datei erneut prüfen.")
    else:
        st.markdown("GPT entscheidet, ob ein Zweck **extern verrechenbar** oder **intern** ist.")
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

            st.success("✅ Klassifizierung abgeschlossen.")
            st.dataframe(df[["Zweck", "Verrechenbarkeit"]].drop_duplicates().sort_values("Zweck"))

            csv = df[["Zweck", "Verrechenbarkeit"]].drop_duplicates().to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Klassifizierte Liste herunterladen", data=csv, file_name="verrechenbarkeit.csv")

# Visualisierung
elif page == "📊 Analyse & Visualisierung":
    st.title("📊 Analyse & Visualisierung")

    if df is None:
        st.warning("Bitte zuerst eine Datei hochladen.")
    else:
        st.markdown("Hier erscheinen später interaktive Diagramme.")
        st.dataframe(df.head())

# Export
elif page == "⬇️ Export":
    st.title("⬇️ Datenexport")

    if df is not None:
        excel_data = df.to_excel(index=False, engine='openpyxl')
        st.download_button("⬇️ Vollständige Tabelle exportieren", data=excel_data, file_name="zeitdaten_export.xlsx")
    else:
        st.info("Kein Datensatz verfügbar.")

