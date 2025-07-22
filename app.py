import streamlit as st
import pandas as pd
import re
import os
import plotly.express as px
from io import BytesIO

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

# 🧠 Zweck extrahieren
def extrahiere_zweck(text):
    if isinstance(text, str) and "-" in text:
        zweck_raw = text.split("-")[-1].strip()
        return re.sub(r"^\d+_?", "", zweck_raw)
    return None

# 📁 Mapping laden/speichern
def lade_mapping():
    if os.path.exists("mapping.csv"):
        return pd.read_csv("mapping.csv")
    else:
        return pd.DataFrame(columns=["Zweck", "Verrechenbarkeit"])

def speichere_mapping(mapping_df):
    mapping_df.drop_duplicates(subset=["Zweck"], inplace=True)
    mapping_df.to_csv("mapping.csv", index=False)

# Session init
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
            st.error("❌ Spalten 'Unterprojekt' oder 'Mitarbeiter' fehlen.")
        else:
            df["Zweck"] = df["Unterprojekt"].apply(extrahiere_zweck)
            st.session_state["df"] = df
            st.success("✅ Datei erfolgreich geladen.")
            st.subheader("📄 Vorschau der Daten")
            st.dataframe(df)

# 🧠 Zweck-Kategorisierung
elif page == "🧠 Zweck-Kategorisierung":
    st.title("🧠 Zweck-Kategorisierung & Mapping")

    if df is None or "Zweck" not in df.columns:
        st.warning("Bitte zuerst eine Excel-Datei hochladen.")
    else:
        mapping_df = st.session_state["mapping_df"]
        bekannte_zwecke = set(mapping_df["Zweck"])
        aktuelle_zwecke = set(df["Zweck"].dropna())
        neue_zwecke = aktuelle_zwecke - bekannte_zwecke

        st.markdown(f"🔍 Neue Zwecke im aktuellen Datensatz: **{len(neue_zwecke)}**")

        if st.button("🤖 Mapping mit KI aktualisieren", disabled=(len(neue_zwecke) == 0)):
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

                if "df" in st.session_state:
                    df = st.session_state["df"]
                    df = df.drop(columns=["Verrechenbarkeit"], errors="ignore")
                    df = df.merge(edited_df, on="Zweck", how="left")
                    st.session_state["df"] = df

                st.success("✅ Mapping gespeichert.")

        df = df.drop(columns=["Verrechenbarkeit"], errors="ignore")
        df = df.merge(st.session_state["mapping_df"], on="Zweck", how="left")
        st.session_state["df"] = df

# 📊 Analyse & Visualisierung – ✅ STUNDENBASIERT
elif page == "📊 Analyse & Visualisierung":
    st.title("📊 Verrechenbarkeit pro Mitarbeiter")

    if df is None or "Verrechenbarkeit" not in df.columns:
        st.warning("Bitte zuerst Datei hochladen **und** Mapping durchführen.")
    else:
        # Zeitraum anzeigen
        datumsspalten = [col for col in df.columns if col.lower() in ["datum", "von", "bis"]]
        if datumsspalten:
            spalte = datumsspalten[0]
            try:
                zeitraum_start = pd.to_datetime(df[spalte]).min().strftime("%d.%m.%Y")
                zeitraum_ende = pd.to_datetime(df[spalte]).max().strftime("%d.%m.%Y")
                st.markdown(f"🗓️ Zeitraum im Datensatz: **{zeitraum_start} – {zeitraum_ende}**")
            except:
                st.info("🗓️ Zeitraum konnte nicht automatisch erkannt werden.")
        else:
            st.info("🗓️ Keine Datumsspalte erkannt.")

        mitarbeiterliste = df["Mitarbeiter"].dropna().unique()
        selected = st.selectbox("👤 Mitarbeiter auswählen", options=mitarbeiterliste)

        df_user = df[df["Mitarbeiter"] == selected]

        # Dauer berechnen
        if "Dauer" not in df_user.columns:
            if {"Von", "Bis"}.issubset(df_user.columns):
                df_user["Von"] = pd.to_datetime(df_user["Von"], errors="coerce")
                df_user["Bis"] = pd.to_datetime(df_user["Bis"], errors="coerce")
                df_user["Dauer"] = (df_user["Bis"] - df_user["Von"]).dt.total_seconds() / 3600
            else:
                df_user["Dauer"] = 1.0

        # Summieren nach Verrechenbarkeit
        dauer_summe = df_user.groupby("Verrechenbarkeit")["Dauer"].sum()
        gesamt = dauer_summe.sum()
        anteile = (dauer_summe / gesamt * 100).round(1)

        st.subheader(f"💼 Aufteilung für: {selected}")
        st.write(anteile.astype(str) + " %")

        fig = px.pie(
            names=anteile.index,
            values=anteile.values,
            title="Anteil Intern vs Extern (nach Stunden)",
            hole=0.4
        )
        st.plotly_chart(fig, use_container_width=True)

# ⬇️ Export – ✅ STUNDENBASIERT
elif page == "⬇️ Export":
    st.title("⬇️ Datenexport")

    if df is not None:
        export_df = df.copy()

        if "Verrechenbarkeit" not in export_df.columns:
            export_df = export_df.merge(st.session_state["mapping_df"], on="Zweck", how="left")

        if "Dauer" not in export_df.columns:
            if {"Von", "Bis"}.issubset(export_df.columns):
                export_df["Von"] = pd.to_datetime(export_df["Von"], errors="coerce")
                export_df["Bis"] = pd.to_datetime(export_df["Bis"], errors="coerce")
                export_df["Dauer"] = (export_df["Bis"] - export_df["Von"]).dt.total_seconds() / 3600
            else:
                export_df["Dauer"] = 1.0

        export_df = export_df[export_df["Verrechenbarkeit"].isin(["Intern", "Extern"])]

        pivot_df = export_df.groupby(["Mitarbeiter", "Verrechenbarkeit"])["Dauer"].sum().unstack(fill_value=0)
        pivot_df["Gesamtstunden"] = pivot_df.sum(axis=1)
        pivot_df["% Intern"] = (pivot_df.get("Intern", 0) / pivot_df["Gesamtstunden"]) * 100
        pivot_df["% Extern"] = (pivot_df.get("Extern", 0) / pivot_df["Gesamtstunden"]) * 100

        export_summary = pivot_df.reset_index()
        export_summary = export_summary[["Mitarbeiter", "Intern", "Extern", "Gesamtstunden", "% Intern", "% Extern"]]
        export_summary[["Intern", "Extern", "Gesamtstunden"]] = export_summary[["Intern", "Extern", "Gesamtstunden"]].round(2)
        export_summary[["% Intern", "% Extern"]] = export_summary[["% Intern", "% Extern"]].round(1)

        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            export_summary.to_excel(writer, index=False, sheet_name="Zusammenfassung")
            export_df.to_excel(writer, index=False, sheet_name="Originaldaten")

        st.download_button(
            "📥 Gesamtauswertung als Excel herunterladen",
            data=output.getvalue(),
            file_name="zeitdaten_auswertung.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("❗ Bitte zuerst Daten hochladen und klassifizieren.")

