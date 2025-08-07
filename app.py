import streamlit as st
import pandas as pd
import re
import os
import plotly.express as px
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Image as RLImage, Table, TableStyle, Spacer
from reportlab.lib import colors
import plotly.io as pio

# 📐 Layout
st.set_page_config(
    page_title="Zeitdatenanalyse Dashboard",
    page_icon="🧠",
    layout="wide"
)

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

os.makedirs("history/exports", exist_ok=True)
os.makedirs("history/uploads", exist_ok=True)

df = st.session_state.get("df", None)
if "mapping_df" not in st.session_state:
    st.session_state["mapping_df"] = lade_mapping()

with st.sidebar:
    st.markdown("### 🧭 Navigation")
    page = st.radio(
        label="Menü",
        options=[
    "🏠 Start",
    "📁 Daten hochladen",
    "🧠 Zweck-Kategorisierung",
    "📊 Analyse & Visualisierung",
    "💰 Abrechnungs-Vergleich",
    "📤 Export"
        ],
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.markdown("🧠 Max KI Dashboard – v0.0.3")

if page == "🏠 Start":
    st.title("Willkommen im Zeitdatenanalyse-Dashboard")
    st.markdown("""
    **Was kann dieses Tool?**

    - 📁 Excel-Zeitdaten hochladen
    - 🤖 KI-gestützte Klassifizierung (intern/extern)
    - 📊 Interaktive Diagramme
    - 📤 Export der Ergebnisse
    - 📚 Verlauf vergangener Exporte
    """)

    st.markdown("## 📤 Export-Historie")
    export_files = sorted(os.listdir("history/exports"), reverse=True)
    for f in export_files:
        cols = st.columns([8, 1])
        with open(os.path.join("history/exports", f), "rb") as file:
            cols[0].download_button(label=f"⬇️ {f}", data=file.read(), file_name=f)
        if cols[1].button("❌", key=f"del_{f}"):
            os.remove(os.path.join("history/exports", f))
            st.rerun()

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
        # Verrechenbarkeit-Mapping
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

        # 👥 Kürzel-Mapping direkt auf dieser Seite
        st.markdown("---")
        st.subheader("👥 Mitarbeiter-Kürzel zuordnen")

        if "kuerzel_map" not in st.session_state:
            alle_namen = sorted(set(df["Mitarbeiter"]))
            kuerzel_df = pd.DataFrame(alle_namen, columns=["Name"])
            kuerzel_df["Kürzel"] = ""
            st.session_state["kuerzel_map"] = kuerzel_df

        edited_kuerzel_df = st.data_editor(
            st.session_state["kuerzel_map"],
            key="kuerzel_editor",
            use_container_width=True,
            num_rows="dynamic"
        )

        if st.button("💾 Kürzel speichern"):
            st.session_state["kuerzel_map"] = edited_kuerzel_df
            st.success("✅ Kürzel wurden gespeichert.")

        st.info("✏️ Trage hier die Kürzel zu den Mitarbeitenden aus der Zeitdaten-Excel ein. Diese werden im Abrechnungs-Vergleich verwendet.")


elif page == "📊 Analyse & Visualisierung":
    st.title("📊 Verrechenbarkeit Gesamtübersicht")

    if df is None or "Verrechenbarkeit" not in df.columns:
        st.warning("Bitte zuerst Datei hochladen **und** Mapping durchführen.")
    else:
        export_df = df.copy()
        export_df = export_df[export_df["Verrechenbarkeit"].isin(["Intern", "Extern"])]

        pivot_df = export_df.groupby(["Mitarbeiter", "Verrechenbarkeit"])["Dauer"].sum().unstack(fill_value=0)
        pivot_df["Gesamtstunden"] = pivot_df.sum(axis=1)
        pivot_df["% Intern"] = (pivot_df.get("Intern", 0) / pivot_df["Gesamtstunden"]) * 100
        pivot_df["% Extern"] = (pivot_df.get("Extern", 0) / pivot_df["Gesamtstunden"]) * 100

        export_summary = pivot_df.reset_index()
        export_summary = export_summary[["Mitarbeiter", "Intern", "Extern", "Gesamtstunden", "% Intern", "% Extern"]]
        export_summary[["Intern", "Extern", "Gesamtstunden"]] = export_summary[["Intern", "Extern", "Gesamtstunden"]].round(2)
        export_summary[["% Intern", "% Extern"]] = export_summary[["% Intern", "% Extern"]].round(1)

        st.subheader("📊 Balkendiagramm Intern/Extern pro Mitarbeiter")

        # Plot mit matplotlib (für PDF-Export kompatibel)
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(10, 5))
        export_summary.plot(kind="bar", x="Mitarbeiter", y=["Intern", "Extern"], ax=ax)
        ax.set_ylabel("Stunden")
        ax.set_title("Stunden nach Verrechenbarkeit")
        st.pyplot(fig)

        st.subheader("📄 Tabellenansicht")
        st.dataframe(export_summary, use_container_width=True)


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
elif page == "💰 Abrechnungs-Vergleich":
    st.title("💰 Vergleich: Zeitdaten vs Rechnungsstellung")

    upload = st.file_uploader("Lade eine Abrechnungs-Excel hoch", type=["xlsx"])

    if upload:
        abrechnung_df = pd.read_excel(upload, sheet_name="Juni 2025", skiprows=8, usecols="C,F")
        abrechnung_df.columns = ["Kürzel", "Rechnungsstellung_SOLL"]

        # 🔄 Währungswerte bereinigen
        abrechnung_df["Rechnungsstellung_SOLL"] = (
            abrechnung_df["Rechnungsstellung_SOLL"]
            .astype(str)
            .str.replace("€", "", regex=False)
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
            .astype(float)
        )

        # 📊 Summe pro Kürzel
        abrechnung_grouped = (
            abrechnung_df.groupby("Kürzel", as_index=False)
            .agg({"Rechnungsstellung_SOLL": "sum"})
        )

        # 🔄 Mapping aus der Zweck-Kategorisierung-Seite laden
        kuerzel_map = st.session_state.get("kuerzel_map", pd.DataFrame())
        if kuerzel_map.empty or "Kürzel" not in kuerzel_map.columns:
            st.warning("⚠️ Kein Kürzel-Mapping vorhanden. Bitte in der Zweck-Kategorisierung pflegen.")
        else:
            df_ext = df[df["Verrechenbarkeit"] == "Extern"]
            df_ext = df_ext.groupby("Mitarbeiter")["Dauer"].sum().reset_index()
        if "Name" not in kuerzel_map.columns:
            kuerzel_map = kuerzel_map.rename(columns={kuerzel_map.columns[0]: "Name"})

            df_ext = df_ext.merge(kuerzel_map, on="Name", how="left")


            # 🔍 Nur Mappings mit Kürzel
            df_ext = df_ext.dropna(subset=["Kürzel"])

            # 🔄 Verknüpfen
            merged = df_ext.merge(abrechnung_grouped, on="Kürzel", how="left")
            merged["Rechnungsstellung_SOLL"] = merged["Rechnungsstellung_SOLL"].fillna(0)
            merged["Differenz"] = merged["Dauer"] - merged["Rechnungsstellung_SOLL"]

            st.subheader("📊 Vergleichstabelle")
            st.dataframe(merged, use_container_width=True)


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

        # 🔧 Balkendiagramm mit matplotlib für PDF
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas

        fig, ax = plt.subplots(figsize=(10, 5))
        export_summary.plot(kind="bar", x="Mitarbeiter", y=["Intern", "Extern"], ax=ax)
        ax.set_ylabel("Stunden")
        ax.set_title("Stunden nach Verrechenbarkeit")
        fig.tight_layout()

        image_path = "temp_chart.png"
        fig.savefig(image_path)

        # 📄 PDF mit ReportLab
        from reportlab.platypus import SimpleDocTemplate, Image as RLImage, Table, TableStyle, Spacer
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors

        pdf_path = f"history/exports/bericht_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.pdf"
        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        elements = [RLImage(image_path, width=500, height=300), Spacer(1, 12)]

        table_data = [export_summary.columns.tolist()] + export_summary.values.tolist()
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ]))
        elements.append(table)
        doc.build(elements)

        with open(pdf_path, "rb") as f:
            st.download_button(
                "⬇️ PDF-Bericht herunterladen",
                data=f.read(),
                file_name=os.path.basename(pdf_path),
                mime="application/pdf"
            )
    else:
        st.info("Bitte zuerst Daten hochladen und klassifizieren.")
