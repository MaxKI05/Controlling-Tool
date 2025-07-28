import streamlit as st
import pandas as pd
import re
import os
import plotly.express as px
from io import BytesIO
from datetime import datetime

# 📐 Layout
st.set_page_config(
    page_title="Zeitdatenanalyse Dashboard",
    page_icon="🧠",
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

# 📂 Historie-Verzeichnisse anlegen
os.makedirs("history/exports", exist_ok=True)
os.makedirs("history/uploads", exist_ok=True)


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
            "📤 Export"
        ],
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.markdown("🧠 Max KI Dashboard – v0.1")

# 🏠 Startseite
if page == "🏠 Start":
    st.title("Willkommen im Zeitdatenanalyse-Dashboard")
    st.markdown("""
    **Was kann dieses Tool?**

    - 📁 Excel-Zeitdaten hochladen
    - 🤖 KI-gestützte Klassifizierung (intern/extern)
    - 📊 Interaktive Diagramme
    - 📤 Export der Ergebnisse
    - 📚 Verlauf vergangener Analysen & Exporte
    """)

    st.markdown("## 📤 Export-Historie")
    export_files = sorted(os.listdir("history/exports"), reverse=True)
    for f in export_files:
        cols = st.columns([8, 1])
        with open(os.path.join("history/exports", f), "rb") as file:
            cols[0].download_button(label=f"⬇️ {f}", data=file.read(), file_name=f)
        if cols[1].button("❌", key=f"del_{f}"):
    os.remove(os.path.join("history/exports", f))
    st.rerun()  # <- ersetzt st.experimental_rerun()


# 📁 Datei hochladen
elif page == "📁 Daten hochladen":
    st.title("📁 Excel-Datei hochladen")
    uploaded_file = st.file_uploader("Lade eine `.xlsx` Datei hoch", type=["xlsx"])

    if uploaded_file:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        save_path = os.path.join("history/uploads", f"upload_{timestamp}.xlsx")
        with open(save_path, "wb") as f:
            f.write(uploaded_file.getvalue())

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
            else:
                df["Dauer"] = 1.0

            st.session_state["df"] = df
            st.success("✅ Datei erfolgreich geladen.")
            st.subheader("📄 Vorschau der Daten")
            st.dataframe(df)

    st.markdown("## 📂 Hochgeladene Dateien")
    upload_files = sorted(os.listdir("history/uploads"), reverse=True)
    for f in upload_files:
        with open(os.path.join("history/uploads", f), "rb") as file:
            st.download_button(label=f"📄 {f}", data=file.read(), file_name=f)
elif page == "🧠 Zweck-Kategorisierung":
    st.title("🧠 Zweck-Kategorisierung & Mapping")

    if df is None or "Zweck" not in df.columns:
        st.warning("⚠️ Bitte zuerst eine Excel-Datei hochladen.")
    else:
        mapping_df = st.session_state["mapping_df"]
        bekannte_zwecke = set(mapping_df["Zweck"])
        aktuelle_zwecke = set(df["Zweck"].dropna())
        neue_zwecke = aktuelle_zwecke - bekannte_zwecke

        st.markdown(f"🔍 Neue Zwecke im aktuellen Datensatz: **{len(neue_zwecke)}**")

        if st.button("🤖 Mapping mit KI aktualisieren", disabled=(len(neue_zwecke) == 0)):
            from utils.gpt import klassifiziere_verrechenbarkeit
            neue_mapping = []

            with st.spinner("🧠 GPT klassifiziert neue Zwecke..."):
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
# 📊 Analyse & Visualisierung
elif page == "📊 Analyse & Visualisierung":
    st.title("📊 Verrechenbarkeit pro Mitarbeiter")

    if df is None or "Verrechenbarkeit" not in df.columns:
        st.warning("Bitte zuerst Datei hochladen **und** Mapping durchführen.")
    else:
        mitarbeiterliste = df["Mitarbeiter"].dropna().unique()
        selected = st.selectbox("👤 Mitarbeiter auswählen", options=mitarbeiterliste)

        df_user = df[df["Mitarbeiter"] == selected]

        if "Dauer" not in df_user.columns:
            st.error("❌ Keine 'Dauer'-Spalte gefunden.")
            st.stop()

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

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if st.button("📌 Analyse speichern"):
            eintrag = {
                "Mitarbeiter": selected,
                "Datum": now,
                "Intern": dauer_summe.get("Intern", 0),
                "Extern": dauer_summe.get("Extern", 0),
                "% Intern": anteile.get("Intern", 0),
                "% Extern": anteile.get("Extern", 0)
            }
            speichere_analysehistorie(eintrag)
            st.success("✅ Analyse gespeichert.")

# 📤 Export
elif page == "📤 Export":
    st.title("📤 Datenexport")

    if df is not None:
        export_df = df.copy()

        if "Verrechenbarkeit" not in export_df.columns:
            export_df = export_df.merge(st.session_state["mapping_df"], on="Zweck", how="left")

        if "Dauer" not in export_df.columns:
            st.error("❌ Keine 'Dauer'-Spalte gefunden.")
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

        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"auswertung_{now}.xlsx"
        path = os.path.join("history/exports", filename)
        with open(path, "wb") as f:
            f.write(output.getvalue())

        st.download_button(
            "⬇️ Gesamtauswertung als Excel herunterladen",
            data=output.getvalue(),
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Bitte zuerst Daten hochladen und klassifizieren.")
