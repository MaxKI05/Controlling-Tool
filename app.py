import streamlit as st
import pandas as pd
import re
import os
import plotly.express as px
from io import BytesIO
from datetime import datetime

# 📁 Ordner für Historie vorbereiten
os.makedirs("history/exports", exist_ok=True)
os.makedirs("history/analysen", exist_ok=True)

# ⚙️ Layout
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

# 🗂️ Mapping laden/speichern
def lade_mapping():
    if os.path.exists("mapping.csv"):
        return pd.read_csv("mapping.csv")
    else:
        return pd.DataFrame(columns=["Zweck", "Verrechenbarkeit"])

def speichere_mapping(mapping_df):
    mapping_df.drop_duplicates(subset=["Zweck"], inplace=True)
    mapping_df.to_csv("mapping.csv", index=False)

# 🔄 Historie laden
@st.cache_data
def lade_export_historie():
    return sorted([f for f in os.listdir("history/exports") if f.endswith(".xlsx")], reverse=True)

@st.cache_data
def lade_analyse_historie():
    try:
        return pd.read_csv("history/analysen/analysen.csv")
    except:
        return pd.DataFrame(columns=["Mitarbeiter", "Datum", "Intern", "Extern", "% Intern", "% Extern"])

# 🧾 Session init
df = st.session_state.get("df", None)
if "mapping_df" not in st.session_state:
    st.session_state["mapping_df"] = lade_mapping()

# 🧭 Sidebar
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
    st.markdown("🧠 Max KI Dashboard – v0.1")

# 🏠 Startseite
if page == "🏠 Start":
    st.title("👋 Willkommen im Zeitdatenanalyse-Dashboard")
    st.markdown("""
    **Was kann dieses Tool?**

    - 📁 Excel-Zeitdaten hochladen
    - 🧠 KI-gestützte Klassifizierung (intern/extern)
    - 📊 Interaktive Diagramme
    - ⬇️ Export der Ergebnisse
    - 📚 Verlauf vergangener Analysen & Exporte
    """)

    st.subheader("📚 Export-Historie")
    for file in lade_export_historie():
        with open(f"history/exports/{file}", "rb") as f:
            st.download_button(
                label=f"📤 {file}",
                data=f,
                file_name=file,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    st.subheader("📈 Analyse-Historie")
    analysen_df = lade_analyse_historie()
    if not analysen_df.empty:
        st.dataframe(analysen_df.sort_values("Datum", ascending=False), use_container_width=True)
    else:
        st.info("Noch keine gespeicherten Analysen vorhanden.")

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
            else:
                df["Dauer"] = 1.0

            st.session_state["df"] = df
            st.success("✅ Datei erfolgreich geladen.")
            st.subheader("📄 Vorschau der Daten")
            st.dataframe(df)

# 🧠 Zweck-Kategorisierung
elif page == "🧠 Zweck-Kategorisierung":
    ...  # bleibt unverändert

# 📊 Analyse & Visualisierung
elif page == "📊 Analyse & Visualisierung":
    st.title("📊 Verrechenbarkeit pro Mitarbeiter")

    if df is None or "Verrechenbarkeit" not in df.columns:
        st.warning("⚠️ Bitte zuerst Datei hochladen und Mapping durchführen.")
    else:
        mitarbeiterliste = df["Mitarbeiter"].dropna().unique()
        selected = st.selectbox("👤 Mitarbeiter auswählen", options=mitarbeiterliste)

        df_user = df[df["Mitarbeiter"] == selected]

        if "Dauer" not in df_user.columns:
            st.error("❌ Keine 'Dauer'-Spalte gefunden. Bitte sicherstellen, dass in der Excel eine Stunden-Spalte vorhanden ist.")
            st.stop()

        dauer_summe = df_user.groupby("Verrechenbarkeit")["Dauer"].sum()
        gesamt = dauer_summe.sum()
        anteile = (dauer_summe / gesamt * 100).round(1)

        st.subheader(f"📌 Aufteilung für: {selected}")
        st.write(anteile.astype(str) + " %")

        # 📦 Analyse speichern
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        analyse_row = pd.DataFrame.from_records([{
            "Mitarbeiter": selected,
            "Datum": timestamp,
            "Intern": dauer_summe.get("Intern", 0),
            "Extern": dauer_summe.get("Extern", 0),
            "% Intern": anteile.get("Intern", 0),
            "% Extern": anteile.get("Extern", 0),
        }])

        if os.path.exists("history/analysen/analysen.csv"):
            alt = pd.read_csv("history/analysen/analysen.csv")
            gesamt = pd.concat([alt, analyse_row], ignore_index=True)
        else:
            gesamt = analyse_row

        gesamt.to_csv("history/analysen/analysen.csv", index=False)

        fig = px.pie(
            names=anteile.index,
            values=anteile.values,
            title="Anteil Intern vs Extern (nach Stunden)",
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
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"zeitdaten_auswertung_{timestamp}.xlsx"

        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            export_summary.to_excel(writer, index=False, sheet_name="Zusammenfassung")
            export_df.to_excel(writer, index=False, sheet_name="Originaldaten")

        with open(f"history/exports/{filename}", "wb") as f_out:
            f_out.write(output.getvalue())

        st.download_button(
            "📤 Gesamtauswertung als Excel herunterladen",
            data=output.getvalue(),
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("ℹ️ Bitte zuerst Daten hochladen und klassifizieren.")
