import streamlit as st
import pandas as pd
import re
import os
import plotly.express as px
from io import BytesIO

# Layout
st.set_page_config(page_title="Zeitdatenanalyse Dashboard", page_icon="📊", layout="wide")

@st.cache_data
def load_excel(file):
    return pd.read_excel(file)

def extrahiere_zweck(text):
    if isinstance(text, str) and "-" in text:
        zweck_raw = text.split("-")[-1].strip()
        return re.sub(r"^\d+_?", "", zweck_raw)
    return None

def lade_mapping():
    if os.path.exists("mapping.csv"):
        return pd.read_csv("mapping.csv")
    else:
        return pd.DataFrame(columns=["Zweck", "Verrechenbarkeit"])

def speichere_mapping(mapping_df):
    mapping_df.drop_duplicates(subset=["Zweck"], inplace=True)
    mapping_df.to_csv("mapping.csv", index=False)

# Session init
if "mapping_df" not in st.session_state:
    st.session_state["mapping_df"] = lade_mapping()

if "df" not in st.session_state:
    st.session_state["df"] = None

df = st.session_state["df"]
mapping_df = st.session_state["mapping_df"]

# Sidebar
with st.sidebar:
    page = st.radio("Menü", [
        "🏠 Start",
        "📁 Daten hochladen",
        "🧠 Zweck-Kategorisierung",
        "📊 Analyse & Visualisierung",
        "⬇️ Export"
    ])
    st.markdown("---")
    st.markdown("👤 Max KI Dashboard – v0.2")

# Startseite
if page == "🏠 Start":
    st.title("👋 Willkommen im Zeitdatenanalyse-Dashboard")
    st.markdown("""
    **Funktionen:**
    - Excel-Zeitdaten hochladen
    - GPT-Klassifizierung (intern/extern)
    - Visualisierung: Prozent oder Stunden
    - Export mit Summen & Anteilen
    """)

# Excel Upload
elif page == "📁 Daten hochladen":
    st.title("📁 Excel-Datei hochladen")
    uploaded_file = st.file_uploader("Lade eine `.xlsx` Datei hoch", type=["xlsx"])

    if uploaded_file:
        df = load_excel(uploaded_file)

        if "Unterprojekt" not in df.columns or "Mitarbeiter" not in df.columns:
            st.error("❌ 'Unterprojekt' oder 'Mitarbeiter' fehlt.")
        else:
            df["Zweck"] = df["Unterprojekt"].apply(extrahiere_zweck)
            st.session_state["df"] = df
            st.success("✅ Datei geladen.")
            st.dataframe(df)

# GPT Mapping
elif page == "🧠 Zweck-Kategorisierung":
    st.title("🧠 Zweck-Kategorisierung & Mapping")

    if df is None:
        st.warning("Bitte zuerst Excel hochladen.")
    else:
        bekannte = set(mapping_df["Zweck"])
        aktuelle = set(df["Zweck"].dropna())
        neue_zwecke = aktuelle - bekannte

        st.markdown(f"🔍 Neue Zwecke: **{len(neue_zwecke)}**")

        if st.button("🤖 Mapping mit KI aktualisieren", disabled=(len(neue_zwecke) == 0)):
            from utils.gpt import klassifiziere_verrechenbarkeit
            neu = []
            with st.spinner("GPT denkt..."):
                for z in neue_zwecke:
                    k = klassifiziere_verrechenbarkeit(z)
                    neu.append({"Zweck": z, "Verrechenbarkeit": k})
            new_df = pd.DataFrame(neu)
            mapping_df = pd.concat([mapping_df, new_df], ignore_index=True)
            speichere_mapping(mapping_df)
            st.session_state["mapping_df"] = mapping_df
            df = df.drop(columns=["Verrechenbarkeit"], errors="ignore")
            df = df.merge(mapping_df, on="Zweck", how="left")
            st.session_state["df"] = df
            st.success("✅ Mapping aktualisiert.")

        tab1, tab2 = st.tabs(["📋 Aktuelles Mapping", "✍️ Manuell bearbeiten"])
        with tab1:
            st.dataframe(mapping_df.sort_values("Zweck"), use_container_width=True)
        with tab2:
            edit = st.data_editor(mapping_df, num_rows="dynamic", use_container_width=True)
            if st.button("💾 Änderungen speichern"):
                speichere_mapping(edit)
                st.session_state["mapping_df"] = edit
                if df is not None:
                    df = df.drop(columns=["Verrechenbarkeit"], errors="ignore")
                    df = df.merge(edit, on="Zweck", how="left")
                    st.session_state["df"] = df
                st.success("✅ Gespeichert.")

# Analyse
elif page == "📊 Analyse & Visualisierung":
    st.title("📊 Analyse nach Verrechenbarkeit")

    if df is None or "Verrechenbarkeit" not in df.columns:
        st.warning("Bitte Datei laden & klassifizieren.")
    else:
        # Zeitraum anzeigen
        datumsspalten = [c for c in df.columns if c.lower() in ["datum", "von", "bis"]]
        if datumsspalten:
            try:
                zeitraum = pd.to_datetime(df[datumsspalten[0]])
                st.markdown(f"🗓️ Zeitraum: **{zeitraum.min().date()} – {zeitraum.max().date()}**")
            except:
                st.info("❗ Datumsspalte konnte nicht gelesen werden.")

        darstellung = st.radio("Anzeigen als:", ["Prozent", "Stunden"], horizontal=True)
        mitarbeiterliste = df["Mitarbeiter"].dropna().unique()
        selected = st.selectbox("👤 Mitarbeiter", mitarbeiterliste)

        df_user = df[df["Mitarbeiter"] == selected]

        if "Dauer" in df_user.columns:
            agg = df_user.groupby("Verrechenbarkeit")["Dauer"].sum()
        else:
            agg = df_user["Verrechenbarkeit"].value_counts()

        if darstellung == "Prozent":
            values = agg / agg.sum() * 100
            st.write(values.round(2).astype(str) + " %")
        else:
            values = agg
            st.write(values.round(2).astype(str) + " h")

        fig = px.pie(
            names=values.index,
            values=values.values,
            title=f"Verteilung ({darstellung})",
            hole=0.4
        )
        st.plotly_chart(fig, use_container_width=True)

# Export
elif page == "⬇️ Export":
    st.title("⬇️ Excel Export")

    if df is not None:
        df_export = df.copy()
        if "Dauer" not in df_export.columns:
            df_export["Dauer"] = 1  # Dummy-Stunden falls keine vorhanden

        summary = df_export.groupby(["Mitarbeiter", "Verrechenbarkeit"]).agg({"Dauer": "sum"}).reset_index()
        pivot = summary.pivot(index="Mitarbeiter", columns="Verrechenbarkeit", values="Dauer").fillna(0)
        pivot["Gesamt"] = pivot.sum(axis=1)
        for col in [c for c in pivot.columns if c not in ["Gesamt"]]:
            pivot[f"{col}_%"] = (pivot[col] / pivot["Gesamt"]) * 100

        excel_io = BytesIO()
        with pd.ExcelWriter(excel_io, engine="xlsxwriter") as writer:
            df_export.to_excel(writer, sheet_name="Originaldaten", index=False)
            pivot.to_excel(writer, sheet_name="Zusammenfassung")
        excel_io.seek(0)

        st.download_button("⬇️ Excel-Datei herunterladen", data=excel_io, file_name="zeitdaten_auswertung.xlsx")
    else:
        st.info("Bitte zuerst Daten laden.")
