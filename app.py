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

# 📁 Mapping laden oder erstellen
def lade_mapping():
    if os.path.exists("mapping.csv"):
        return pd.read_csv("mapping.csv")
    else:
        return pd.DataFrame(columns=["Zweck", "Verrechenbarkeit"])

def speichere_mapping(mapping_df):
    mapping_df.drop_duplicates(subset=["Zweck"], inplace=True)
    mapping_df.to_csv("mapping.csv", index=False)

# 🔄 Globaler DF aus Session
df = st.session_state.get("df", None)
if "mapping_df" not in st.session_state:
    st.session_state["mapping_df"] = lade_mapping()

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

# 🧠 Zweck-Kategorisierung und Mapping
elif page == "🧠 Zweck-Kategorisierung":
    st.title("🧠 Zweck-Kategorisierung & Mapping")

    if df is None or "Zweck" not in df.columns:
        st.warning("Bitte zuerst eine Excel-Datei hochladen.")
    else:
        mapping_df = st.session_state["mapping_df"]
        bekannte_zwecke = set(mapping_df["Zweck"])
        aktuelle_zwecke = set(df["Zweck"].dropna())
        neue_zwecke = aktuelle_zwecke - bekannte_zwecke

        if neue_zwecke:
            st.info(f"🔍 {len(neue_zwecke)} neue Zwecke erkannt, die noch nicht im Mapping enthalten sind.")

            if st.button("🤖 Mapping mit KI aktualisieren"):
                from utils.gpt import klassifiziere_verrechenbarkeit
                neue_mapping = []

                with st.spinner("GPT klassifiziert neue Zwecke..."):
                    for zweck in neue_zwecke:
                        kat = klassifiziere_verrechenbarkeit(zweck)
                        neue_mapping.append({"Zweck": zweck, "Verrechenbarkeit": kat})

                new_df = pd.DataFrame(neue_mapping)
                mapping_df = pd.concat([mapping_df, new_df], ignore_index=True)
                mapping_df.drop_duplicates(subset=["Zweck"], inplace=True)
                st.session_state["mapping_df"] = mapping_df
                speichere_mapping(mapping_df)

                # auch df aktualisieren
                df = df.drop(columns=["Verrechenbarkeit"], errors="ignore")
                df = df.merge(mapping_df, on="Zweck", how="left")
                st.session_state["df"] = df

                st.success("✅ Mapping mit GPT aktualisiert.")

        tab1, tab2 = st.tabs(["📋 Aktuelles Mapping", "✍️ Manuell bearbeiten"])

        with tab1:
            st.dataframe(mapping_df.sort_values("Zweck"), use_container_width=True)

        with tab2:
            edited_df = st.data_editor(
                mapping_df,
                num_rows="dynamic",
                use_container_width=True,
                key="mapping_editor"
            )

            if st.button("💾 Änderungen speichern"):
                st.session_state["mapping_df"] = edited_df
                speichere_mapping(edited_df)

                # Falls df bereits geladen ist: neu mergen
                if "df" in st.session_state:
                    df = st.session_state["df"]
                    df = df.drop(columns=["Verrechenbarkeit"], errors="ignore")
                    df = df.merge(edited_df, on="Zweck", how="left")
                    st.session_state["df"] = df

                st.success("✅ Mapping gespeichert und aktualisiert.")

        # Merge in df sicherstellen
        df = df.drop(columns=["Verrechenbarkeit"], errors="ignore")
        df = df.merge(st.session_state["mapping_df"], on="Zweck", how="left")
        st.session_state["df"] = df

# 📊 Visualisierung
elif page == "📊 Analyse & Visualisierung":
    st.title("📊 Verrechenbarkeit pro Mitarbeiter")

    if df is None or "Verrechenbarkeit" not in df.columns:
        st.warning("Bitte zuerst Datei hochladen **und** Zweck-Mapping durchführen.")
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
        export_df = df.copy()
        if "Verrechenbarkeit" not in export_df.columns:
            export_df = export_df.merge(st.session_state["mapping_df"], on="Zweck", how="left")

        output = export_df.to_excel(index=False, engine="openpyxl")
        st.download_button("⬇️ Excel exportieren", data=output, file_name="zeitdaten_export.xlsx")
    else:
        st.info("Kein Datensatz gefunden.")
