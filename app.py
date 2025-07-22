import streamlit as st
import pandas as pd
import re
import os
import plotly.express as px
from io import BytesIO

# ⚙️ Layout
st.set_page_config(
    page_title="Zeitdatenanalyse Dashboard",
    page_icon="⚙️",
    layout="wide"
)

# 📅 Excel laden
@st.cache_data
def load_excel(file):
    return pd.read_excel(file)

# 🧠 Zweck extrahieren
def extrahiere_zweck(text):
    if isinstance(text, str) and "-" in text:
        zweck_raw = text.split("-")[-1].strip()
        return re.sub(r"^\d+_?", "", zweck_raw)
    return None

# 📂 Mapping laden/speichern
def lade_mapping():
    if os.path.exists("mapping.csv"):
        return pd.read_csv("mapping.csv")
    else:
        return pd.DataFrame(columns=["Zweck", "Verrechenbarkeit"])

def speichere_mapping(mapping_df):
    mapping_df.drop_duplicates(subset=["Zweck"], inplace=True)
    mapping_df.to_csv("mapping.csv", index=False)

# 🔄 Session init
df = st.session_state.get("df", None)
if "mapping_df" not in st.session_state:
    st.session_state["mapping_df"] = lade_mapping()

# Sidebar
with st.sidebar:
    st.markdown("### 🗺️ Navigation")
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
    if st.button("🔄 Zurücksetzen"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
    st.markdown("---")
    st.markdown("🧠 Max KI Dashboard – v0.2")

# 🏠 Startseite
if page == "🏠 Start":
    st.title("👋 Willkommen im Zeitdatenanalyse-Dashboard")
    st.markdown("""
    **Was kann dieses Tool?**

    - 📁 Excel-Zeitdaten hochladen
    - 🤖 KI-gestützte Klassifizierung (intern/extern)
    - 📊 Interaktive Diagramme & Übersichten
    - 📤 Export der Ergebnisse
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

            dauer_spalte = None
            for spalte in df.columns:
                if spalte.lower() in ["stunden", "dauer"]:
                    dauer_spalte = spalte
                    break

            if dauer_spalte:
                df["Dauer"] = pd.to_numeric(df[dauer_spalte], errors="coerce").fillna(0)
                if (df["Dauer"] < 0).any():
                    st.warning("⚠️ Es wurden negative Werte in der Stundenspalte gefunden.")
            else:
                df["Dauer"] = 1.0

            st.session_state["df"] = df
            st.success("✅ Datei erfolgreich geladen.")
            st.subheader("📄 Vorschau der Daten")
            st.dataframe(df)

# 📊 Analyse & Visualisierung
elif page == "📊 Analyse & Visualisierung":
    st.title("📊 Analyseübersicht")

    if df is None or "Verrechenbarkeit" not in df.columns:
        st.warning("Bitte zuerst Datei hochladen und Mapping durchführen.")
    else:
        df = df[df["Verrechenbarkeit"].isin(["Intern", "Extern"])]

        # Filteroptionen
        with st.expander("🔍 Filteroptionen"):
            mitarbeiter = st.multiselect("👤 Mitarbeiter filtern", df["Mitarbeiter"].unique())
            projekte = st.multiselect("🗂️ Projekte filtern", df["Zweck"].unique())
            datum_min = df["Datum"].min() if "Datum" in df.columns else None
            datum_max = df["Datum"].max() if "Datum" in df.columns else None
            datum_range = st.date_input("🗓️ Zeitraum", [datum_min, datum_max]) if datum_min and datum_max else None

        df_filtered = df.copy()
        if mitarbeiter:
            df_filtered = df_filtered[df_filtered["Mitarbeiter"].isin(mitarbeiter)]
        if projekte:
            df_filtered = df_filtered[df_filtered["Zweck"].isin(projekte)]
        if datum_range and "Datum" in df.columns:
            df_filtered["Datum"] = pd.to_datetime(df_filtered["Datum"], errors="coerce")
            df_filtered = df_filtered[(df_filtered["Datum"] >= datum_range[0]) & (df_filtered["Datum"] <= datum_range[1])]

        # Zusammenfassung
        st.subheader("📋 Übersicht pro Mitarbeiter")
        summary = df_filtered.groupby(["Mitarbeiter", "Verrechenbarkeit"])["Dauer"].sum().unstack(fill_value=0)
        summary["Gesamt"] = summary.sum(axis=1)
        summary["% Intern"] = (summary.get("Intern", 0) / summary["Gesamt"] * 100).round(1)
        summary["% Extern"] = (summary.get("Extern", 0) / summary["Gesamt"] * 100).round(1)

        if "Datum" in df_filtered.columns:
            letzter_eintrag = df_filtered.groupby("Mitarbeiter")["Datum"].max()
            summary["Letzter Eintrag"] = letzter_eintrag

        st.dataframe(summary.reset_index(), use_container_width=True)

        # Visualisierung
        st.subheader("📈 Visualisierung auswählen")
        mitarbeiter_liste = summary.index.tolist()
        selected = st.selectbox("👤 Mitarbeiter auswählen", options=mitarbeiter_liste)

        user_data = summary.loc[selected]
        st.columns(2)[0].metric("Intern (h)", f"{user_data.get('Intern', 0):.1f}")
        st.columns(2)[1].metric("Extern (h)", f"{user_data.get('Extern', 0):.1f}")

        fig = px.pie(
            names=["Intern", "Extern"],
            values=[user_data.get("Intern", 0), user_data.get("Extern", 0)],
            title=f"Anteil für {selected}",
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

        if "Dauer" not in export_df.columns:
            st.error("❌ Keine 'Dauer'-Spalte gefunden. Bitte sicherstellen, dass in der Excel eine Stunden-Spalte vorhanden ist.")
            st.stop()

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
            "📤 Gesamtauswertung als Excel herunterladen",
            data=output.getvalue(),
            file_name="zeitdaten_auswertung.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("ℹ️ Bitte zuerst Daten hochladen und klassifizieren.")

