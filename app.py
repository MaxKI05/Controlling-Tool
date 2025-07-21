import streamlit as st
import pandas as pd
import re
from datetime import datetime
import os
import plotly.express as px

# 📐 Layout
st.set_page_config(
    page_title="Zeitdatenanalyse Dashboard",
    page_icon="📊",
    layout="wide"
)

# 📥 Excel laden
@st.cache_data
def load_excel(file):
    return pd.read_excel(file)

# 🧠 Zweck aus Unterprojekt extrahieren
def extrahiere_zweck(text):
    if isinstance(text, str) and "-" in text:
        zweck_raw = text.split("-")[-1].strip()
        return re.sub(r"^\d+_?", "", zweck_raw)
    return None

# 🔄 Globaler DF aus Session
df = st.session_state.get("df", None)

# Sidebar
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
    st.markdown("👤 Max KI Dashboard – v0.1")

# 🏠 Startseite
if page == "🏠 Start":
    st.title("👋 Willkommen im Zeitdatenanalyse-Dashboard")
    st.markdown("""
    **Was kann dieses Tool?**

    - 📁 Excel-Zeitdaten hochladen
    - 🧠 KI-gestützte Klassifizierung (intern/extern)
    - 📊 Interaktive Diagramme
    - ⬇️ Export der Ergebnisse
    """)

# 📁 Datei hochladen
elif page == "📁 Daten hochladen":
    st.title("📁 Excel-Datei hochladen")
    uploaded_file = st.file_uploader("Lade eine `.xlsx` Datei hoch", type=["xlsx"])

    if uploaded_file:
        df = load_excel(uploaded_file)

        if "Unterprojekt" not in df.columns or "Mitarbeiter" not in df.columns:
            st.error("❌ Erforderliche Spalten 'Unterprojekt' oder 'Mitarbeiter' fehlen.")
        else:
            df["Zweck"] = df["Unterprojekt"].apply(extrahiere_zweck)
            st.session_state["df"] = df

            st.success("✅ Datei erfolgreich geladen und verarbeitet.")
            st.subheader("📄 Hochgeladene Tabelle")
            st.dataframe(df)

# 🧠 GPT-Kategorisierung
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
            st.session_state["df"] = df

            st.success("✅ Klassifizierung abgeschlossen.")
            st.dataframe(df[["Zweck", "Verrechenbarkeit"]].drop_duplicates().sort_values("Zweck"))

            csv = df[["Zweck", "Verrechenbarkeit"]].drop_duplicates().to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Klassifizierte Liste herunterladen", data=csv, file_name="verrechenbarkeit.csv")

# 📊 Visualisierung
elif page == "📊 Analyse & Visualisierung":
    st.title("📊 Verrechenbarkeit pro Mitarbeiter")

    if df is None or "Verrechenbarkeit" not in df.columns:
        st.warning("Bitte zuerst Datei hochladen **und** GPT-Klassifizierung durchführen.")
    else:
        mitarbeiterliste = df["Mitarbeiter"].dropna().unique()
        selected = st.selectbox("👤 Mitarbeiter auswählen", options=mitarbeiterliste)

        df_user = df[df["Mitarbeiter"] == selected]
        agg = df_user["Verrechenbarkeit"].value_counts(normalize=True) * 100

        st.subheader(f"💼 Aufteilung für: {selected}")
        st.write(agg.round(2).astype(str) + " %")

        fig = px.pie(
            names=agg.index,
            values=agg.values,
            title="Anteil Intern vs Extern",
            hole=0.4
        )
        st.plotly_chart(fig, use_container_width=True)

# ⬇️ Export
elif page == "⬇️ Export":
    st.title("⬇️ Datenexport")

    if df is not None:
        output = df.to_excel(index=False, engine="openpyxl")
        st.download_button("⬇️ Excel exportieren", data=output, file_name="zeitdaten_export.xlsx")
    else:
        st.info("Kein Datensatz gefunden.")

