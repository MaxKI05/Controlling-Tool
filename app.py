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


# --- Persistenz: Mapping + Kürzel ---
def lade_kuerzel():
    path = "kuerzel.csv"
    if os.path.exists(path):
        dfk = pd.read_csv(path)
        # Spalten-Absicherung
        if "Name" not in dfk.columns: dfk["Name"] = ""
        if "Kürzel" not in dfk.columns: dfk["Kürzel"] = ""
        return dfk[["Name", "Kürzel"]]
    return pd.DataFrame(columns=["Name", "Kürzel"])

def speichere_kuerzel(dfk):
    dfk = dfk.copy()
    dfk["Name"] = dfk["Name"].astype(str).str.strip()
    dfk["Kürzel"] = dfk["Kürzel"].astype(str).str.strip()
    dfk.dropna(subset=["Name"], inplace=True)
    dfk.drop_duplicates(subset=["Name"], inplace=True)
    dfk.to_csv("kuerzel.csv", index=False)


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
    if "kuerzel_map" not in st.session_state:
        st.session_state["kuerzel_map"] = lade_kuerzel()


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

    # --- Laden aus Session (persistente CSVs) ---
    mapping_df = st.session_state["mapping_df"]
    kuerzel_df = st.session_state["kuerzel_map"]

    # --------- ZWECK-MAPPING ----------
    st.subheader("📋 Aktuelles Zweck-Mapping (persistiert)")
    edited_mapping = st.data_editor(
        mapping_df.sort_values("Zweck"),
        num_rows="dynamic",
        use_container_width=True,
        key="mapping_editor",
    )

    c1, c2, c3 = st.columns([1,1,2])
    if c1.button("💾 Mapping speichern"):
        st.session_state["mapping_df"] = edited_mapping.copy()
        speichere_mapping(st.session_state["mapping_df"])
        st.success("✅ Mapping gespeichert.")

    # Optionale Komfort-Buttons, nur wenn eine Datei geladen ist
    has_df = st.session_state.get("df") is not None
    if c2.button("➕ Neue Zwecke aus aktuellem Datensatz hinzufügen", disabled=not has_df):
        df_now = st.session_state["df"]
        aktuelle_zwecke = set(df_now["Zweck"].dropna().astype(str).str.strip())
        bekannte_zwecke = set(st.session_state["mapping_df"]["Zweck"].astype(str).str.strip())
        neue_zwecke = sorted(list(aktuelle_zwecke - bekannte_zwecke))
        if not neue_zwecke:
            st.info("Keine neuen Zwecke gefunden.")
        else:
            # Nur leere Platzhalter hinzufügen (noch ohne Klassifizierung)
            addon = pd.DataFrame({"Zweck": neue_zwecke, "Verrechenbarkeit": "Unbekannt"})
            st.session_state["mapping_df"] = pd.concat([st.session_state["mapping_df"], addon], ignore_index=True)
            speichere_mapping(st.session_state["mapping_df"])
            st.success(f"➕ {len(neue_zwecke)} neue Zwecke hinzugefügt (als 'Unbekannt').")

    st.markdown("---")

    # GPT-Update nur auf ausdrücklichen Klick – niemals automatisch
    st.subheader("🤖 Klassifizieren (nur neue/Unbekannt)")
    left, right = st.columns([1,3])

    if left.button("🧠 'Unbekannt' klassifizieren"):
        from utils.gpt import klassifiziere_verrechenbarkeit
        mdf = st.session_state["mapping_df"].copy()
        mask = mdf["Verrechenbarkeit"].fillna("Unbekannt").str.lower().eq("unbekannt")
        kandidat_zecke = mdf.loc[mask, "Zweck"].dropna().astype(str).str.strip().unique().tolist()

        if not kandidat_zecke:
            st.info("Nichts zu klassifizieren – es gibt keine 'Unbekannt'-Einträge.")
        else:
            mapped = []
            with st.spinner(f"Klassifiziere {len(kandidat_zecke)} Zwecke..."):
                for zweck in kandidat_zecke:
                    try:
                        kat = klassifiziere_verrechenbarkeit(zweck)
                    except Exception as e:
                        st.error(f"Fehler bei '{zweck}': {e}")
                        kat = "Unbekannt"
                    mapped.append((zweck, kat))

            # Ergebnisse zurückschreiben, aber bestehendes nicht überschreiben
            kat_map = dict(mapped)
            mdf.loc[mask, "Verrechenbarkeit"] = mdf.loc[mask, "Zweck"].map(kat_map).fillna("Unbekannt")
            st.session_state["mapping_df"] = mdf.drop_duplicates(subset=["Zweck"])
            speichere_mapping(st.session_state["mapping_df"])
            st.success("✅ Klassifizierung aktualisiert.")

    st.info("Hinweis: Es wird **nie automatisch** klassifiziert. Änderungen werden nur per Button gespeichert oder aktualisiert.")

    st.markdown("---")

    # --------- KÜRZEL-MAPPING ----------
    st.subheader("👥 Mitarbeiter-Kürzel (persistiert)")
    edited_kuerzel = st.data_editor(
        kuerzel_df.sort_values("Name"),
        num_rows="dynamic",
        use_container_width=True,
        key="kuerzel_editor",
    )

    k1, k2 = st.columns([1,1])
    if k1.button("💾 Kürzel speichern"):
        st.session_state["kuerzel_map"] = edited_kuerzel.copy()
        speichere_kuerzel(st.session_state["kuerzel_map"])
        st.success("✅ Kürzel gespeichert.")

    if k2.button("➕ Neue Mitarbeitende aus aktuellem Datensatz", disabled=not has_df):
        df_now = st.session_state["df"]
        aktuelle_namen = set(df_now["Mitarbeiter"].dropna().astype(str).str.strip())
        bekannte_namen = set(st.session_state["kuerzel_map"]["Name"].astype(str).str.strip())
        neu = sorted(list(aktuelle_namen - bekannte_namen))
        if not neu:
            st.info("Keine neuen Namen gefunden.")
        else:
            addon = pd.DataFrame({"Name": neu, "Kürzel": ""})
            st.session_state["kuerzel_map"] = pd.concat([st.session_state["kuerzel_map"], addon], ignore_index=True)
            speichere_kuerzel(st.session_state["kuerzel_map"])
            st.success(f"➕ {len(neu)} neue Mitarbeitende hinzugefügt.")


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


elif page == "💰 Abrechnungs-Vergleich":
    st.title("💰 Vergleich: Zeitdaten vs Rechnungsstellung")

    upload = st.file_uploader("Lade eine Abrechnungs-Excel hoch", type=["xlsx"])

    if upload:
        # 🔄 Gesamte Tabelle einlesen, ohne Header
        df_abrechnung = pd.read_excel(upload, sheet_name=0, header=None)

        # 🔍 Zeile mit "Rechnungsstellung [€]" suchen
        zielzeile = None
        for i, row in df_abrechnung.iterrows():
            if row.astype(str).str.contains("Rechnungsstellung [€]", case=False).any():
                zielzeile = i
                break

        if zielzeile is None:
            st.warning("⚠️ Keine Zeile mit 'Rechnungsstellung [€]' gefunden.")
        else:
            # 📌 Kürzel stehen direkt oberhalb, Werte direkt unterhalb
            kuerzel_row = df_abrechnung.iloc[zielzeile - 1]
            werte_row = df_abrechnung.iloc[zielzeile + 1]
            gueltige_spalten = kuerzel_row[kuerzel_row.notna()].index

            df_clean = pd.DataFrame({
                "Kürzel": kuerzel_row[gueltige_spalten].values,
                "Rechnungsstellung_SOLL": werte_row[gueltige_spalten].values
            })

            # 🔧 Format bereinigen
            df_clean["Rechnungsstellung_SOLL"] = (
                df_clean["Rechnungsstellung_SOLL"]
                .astype(str)
                .str.replace("€", "", regex=False)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
                .str.replace("-", "0", regex=False)
                .astype(float)
            )

            # 🔁 Gruppieren (für den Fall, dass ein Kürzel mehrfach auftaucht)
            abrechnung_grouped = df_clean.groupby("Kürzel", as_index=False).sum()

            # 👥 Kürzel-Mapping laden
            kuerzel_map = st.session_state.get("kuerzel_map", pd.DataFrame())
            if kuerzel_map.empty or "Kürzel" not in kuerzel_map.columns:
                st.warning("⚠️ Kein Kürzel-Mapping gefunden. Bitte zuerst in der Zweck-Kategorisierung pflegen.")
            else:
                if "Name" not in kuerzel_map.columns:
                    kuerzel_map.columns = ["Name", "Kürzel"]

                # 📊 Zeitdaten filtern & summieren
                df_ext = df[df["Verrechenbarkeit"] == "Extern"]
                df_ext = df_ext.groupby("Mitarbeiter")["Dauer"].sum().reset_index()

                # 🔗 Mapping anwenden
                df_ext = df_ext.merge(kuerzel_map, left_on="Mitarbeiter", right_on="Name", how="left")
                df_ext = df_ext.dropna(subset=["Kürzel"])

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
