# app.py
import os
import re
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Image as RLImage, SimpleDocTemplate, Spacer, Table, TableStyle

# ──────────────────────────────────────────────────────────────────────────────
# Layout & App-Setup
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Zeitdatenanalyse Dashboard", page_icon="🧠", layout="wide")

APP_VERSION = "v0.0.4"

os.makedirs("history/exports", exist_ok=True)
os.makedirs("history/uploads", exist_ok=True)

# ──────────────────────────────────────────────────────────────────────────────
# Helper
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data
def load_excel(file):
    return pd.read_excel(file)

def extrahiere_zweck(text: str):
    if isinstance(text, str) and "-" in text:
        zweck_raw = text.split("-")[-1].strip()
        return re.sub(r"^\d+_?", "", zweck_raw)
    return None

# Persistenz: Zweck-Mapping
def lade_mapping() -> pd.DataFrame:
    if os.path.exists("mapping.csv"):
        dfm = pd.read_csv("mapping.csv")
        if "Zweck" not in dfm.columns:
            dfm["Zweck"] = ""
        if "Verrechenbarkeit" not in dfm.columns:
            dfm["Verrechenbarkeit"] = "Unbekannt"
        out = dfm[["Zweck", "Verrechenbarkeit"]].copy()
        out["Zweck"] = out["Zweck"].astype(str).str.strip()
        out["Verrechenbarkeit"] = out["Verrechenbarkeit"].fillna("Unbekannt")
        out.drop_duplicates(subset=["Zweck"], inplace=True)
        return out
    return pd.DataFrame(columns=["Zweck", "Verrechenbarkeit"])

def speichere_mapping(df: pd.DataFrame):
    out = df.copy()
    out["Zweck"] = out["Zweck"].astype(str).str.strip()
    out["Verrechenbarkeit"] = out["Verrechenbarkeit"].fillna("Unbekannt")
    out.drop_duplicates(subset=["Zweck"], inplace=True)
    out.to_csv("mapping.csv", index=False)

# Persistenz: Kürzel
def lade_kuerzel() -> pd.DataFrame:
    if os.path.exists("kuerzel.csv"):
        dfk = pd.read_csv("kuerzel.csv")
        if "Name" not in dfk.columns:
            dfk["Name"] = ""
        if "Kürzel" not in dfk.columns:
            dfk["Kürzel"] = ""
        out = dfk[["Name", "Kürzel"]].copy()
        out["Name"] = out["Name"].astype(str).str.strip()
        out["Kürzel"] = out["Kürzel"].astype(str).str.strip()
        out.drop_duplicates(subset=["Name"], inplace=True)
        return out
    return pd.DataFrame(columns=["Name", "Kürzel"])

def speichere_kuerzel(df: pd.DataFrame):
    out = df.copy()
    out["Name"] = out["Name"].astype(str).str.strip()
    out["Kürzel"] = out["Kürzel"].astype(str).str.strip()
    out.dropna(subset=["Name"], inplace=True)
    out.drop_duplicates(subset=["Name"], inplace=True)
    out.to_csv("kuerzel.csv", index=False)

# Convenience-Getter (vermeidet KeyError)
def get_state_df(key: str, loader):
    if key not in st.session_state or not isinstance(st.session_state[key], pd.DataFrame):
        st.session_state[key] = loader()
    return st.session_state[key]

# ──────────────────────────────────────────────────────────────────────────────
# Session-State initialisieren (einmalig & früh!)
# ──────────────────────────────────────────────────────────────────────────────
if "df" not in st.session_state:
    st.session_state["df"] = None
if "mapping_df" not in st.session_state:
    st.session_state["mapping_df"] = lade_mapping()
if "kuerzel_map" not in st.session_state:
    st.session_state["kuerzel_map"] = lade_kuerzel()

# ──────────────────────────────────────────────────────────────────────────────
# Sidebar
# ──────────────────────────────────────────────────────────────────────────────
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
            "📤 Export",
        ],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.markdown(f"🧠 Max KI Dashboard – {APP_VERSION}")

# ──────────────────────────────────────────────────────────────────────────────
# Seiten
# ──────────────────────────────────────────────────────────────────────────────
if page == "🏠 Start":
    st.title("Willkommen im Zeitdatenanalyse-Dashboard")
    st.markdown(
        """
**Was kann dieses Tool?**

- 📁 Excel-Zeitdaten hochladen
- 🤖 Klassifizierung (Intern/Extern) per Button
- 📊 Interaktive Diagramme
- 📤 Export der Ergebnisse
- 📚 Verlauf vergangener Exporte
"""
    )

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

            # Dauer ermitteln
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
            st.dataframe(df, use_container_width=True)

    st.markdown("## 📂 Hochgeladene Dateien")
    upload_files = sorted(os.listdir("history/uploads"), reverse=True)
    for f in upload_files:
        with open(os.path.join("history/uploads", f), "rb") as file:
            st.download_button(label=f"📄 {f}", data=file.read(), file_name=f)

elif page == "🧠 Zweck-Kategorisierung":
    st.title("🧠 Zweck-Kategorisierung & Mapping")

    # Immer verfügbar aus Persistenz/State (kein Upload nötig)
    mapping_df = get_state_df("mapping_df", lade_mapping)
    kuerzel_df = get_state_df("kuerzel_map", lade_kuerzel)

    # ── Zweck-Mapping
    st.subheader("📋 Aktuelles Zweck-Mapping (persistiert)")
    edited_mapping = st.data_editor(
        mapping_df.sort_values("Zweck"),
        num_rows="dynamic",
        use_container_width=True,
        key="mapping_editor",
    )

    c1, c2, c3 = st.columns([1, 1, 2])
    if c1.button("💾 Mapping speichern"):
        st.session_state["mapping_df"] = edited_mapping.copy()
        speichere_mapping(st.session_state["mapping_df"])
        st.success("✅ Mapping gespeichert.")

        # df (falls vorhanden) mit aktualisiertem Mapping mergen
        if isinstance(st.session_state.get("df"), pd.DataFrame):
            df = st.session_state["df"].drop(columns=["Verrechenbarkeit"], errors="ignore")
            st.session_state["df"] = df.merge(st.session_state["mapping_df"], on="Zweck", how="left")

    has_df = isinstance(st.session_state.get("df"), pd.DataFrame)
    if c2.button("➕ Neue Zwecke aus aktuellem Datensatz hinzufügen", disabled=not has_df):
        df_now = st.session_state["df"]
        if "Zweck" in df_now.columns:
            aktuelle = set(df_now["Zweck"].dropna().astype(str).str.strip())
            bekannte = set(st.session_state["mapping_df"]["Zweck"].astype(str).str.strip())
            neue = sorted(list(aktuelle - bekannte))
            if neue:
                addon = pd.DataFrame({"Zweck": neue, "Verrechenbarkeit": "Unbekannt"})
                st.session_state["mapping_df"] = pd.concat([st.session_state["mapping_df"], addon], ignore_index=True)
                speichere_mapping(st.session_state["mapping_df"])
                st.success(f"➕ {len(neue)} neue Zwecke hinzugefügt (als 'Unbekannt').")
            else:
                st.info("Keine neuen Zwecke gefunden.")

    st.markdown("---")
    st.subheader("🤖 Klassifizieren (nur Einträge mit 'Unbekannt')")
    if st.button("🧠 'Unbekannt' klassifizieren"):
        try:
            from utils.gpt import klassifiziere_verrechenbarkeit
        except Exception as e:
            st.error(f"GPT-Modul konnte nicht importiert werden: {e}")
        else:
            mdf = st.session_state["mapping_df"].copy()
            mask = mdf["Verrechenbarkeit"].fillna("Unbekannt").str.lower().eq("unbekannt")
            kandidaten = mdf.loc[mask, "Zweck"].dropna().astype(str).str.strip().unique().tolist()
            if not kandidaten:
                st.info("Nichts zu klassifizieren – es gibt keine 'Unbekannt'-Einträge.")
            else:
                results = {}
                with st.spinner(f"Klassifiziere {len(kandidaten)} Zwecke..."):
                    for zweck in kandidaten:
                        try:
                            results[zweck] = klassifiziere_verrechenbarkeit(zweck)
                        except Exception as e:
                            st.error(f"Fehler bei '{zweck}': {e}")
                            results[zweck] = "Unbekannt"

                mdf.loc[mask, "Verrechenbarkeit"] = mdf.loc[mask, "Zweck"].map(results).fillna("Unbekannt")
                st.session_state["mapping_df"] = mdf.drop_duplicates(subset=["Zweck"])
                speichere_mapping(st.session_state["mapping_df"])
                st.success("✅ Klassifizierung aktualisiert.")

                # df neu mergen, falls vorhanden
                if isinstance(st.session_state.get("df"), pd.DataFrame):
                    df = st.session_state["df"].drop(columns=["Verrechenbarkeit"], errors="ignore")
                    st.session_state["df"] = df.merge(st.session_state["mapping_df"], on="Zweck", how="left")

    st.info("Hinweis: Es wird **nie automatisch** klassifiziert. Änderungen passieren nur per Button.")

    st.markdown("---")

    # ── Kürzel-Mapping
    st.subheader("👥 Mitarbeiter-Kürzel (persistiert)")
    edited_kuerzel = st.data_editor(
        kuerzel_df.sort_values("Name"),
        num_rows="dynamic",
        use_container_width=True,
        key="kuerzel_editor",
    )

    k1, k2 = st.columns([1, 1])
    if k1.button("💾 Kürzel speichern"):
        st.session_state["kuerzel_map"] = edited_kuerzel.copy()
        speichere_kuerzel(st.session_state["kuerzel_map"])
        st.success("✅ Kürzel gespeichert.")

    if k2.button("➕ Neue Mitarbeitende aus aktuellem Datensatz", disabled=not has_df):
        df_now = st.session_state["df"]
        if "Mitarbeiter" in df_now.columns:
            aktuelle = set(df_now["Mitarbeiter"].dropna().astype(str).str.strip())
            bekannte = set(st.session_state["kuerzel_map"]["Name"].astype(str).str.strip())
            neu = sorted(list(aktuelle - bekannte))
            if neu:
                addon = pd.DataFrame({"Name": neu, "Kürzel": ""})
                st.session_state["kuerzel_map"] = pd.concat([st.session_state["kuerzel_map"], addon], ignore_index=True)
                speichere_kuerzel(st.session_state["kuerzel_map"])
                st.success(f"➕ {len(neu)} neue Mitarbeitende hinzugefügt.")
            else:
                st.info("Keine neuen Namen gefunden.")

elif page == "📊 Analyse & Visualisierung":
    st.title("📊 Verrechenbarkeit Gesamtübersicht")

    df = st.session_state.get("df")
    if not isinstance(df, pd.DataFrame):
        st.warning("Bitte zuerst eine Datei hochladen.")
    else:
        if "Verrechenbarkeit" not in df.columns:
            # Mapping nur mergen (kein Auto-Klassifizieren)
            df = df.drop(columns=["Verrechenbarkeit"], errors="ignore")
            df = df.merge(st.session_state["mapping_df"], on="Zweck", how="left")
            st.session_state["df"] = df

        export_df = df[df["Verrechenbarkeit"].isin(["Intern", "Extern"])].copy()
        if export_df.empty:
            st.info("Keine Daten mit 'Intern'/'Extern' vorhanden.")
        else:
            pivot_df = export_df.groupby(["Mitarbeiter", "Verrechenbarkeit"])["Dauer"].sum().unstack(fill_value=0)
            pivot_df["Gesamtstunden"] = pivot_df.sum(axis=1)
            pivot_df["% Intern"] = (pivot_df.get("Intern", 0) / pivot_df["Gesamtstunden"]) * 100
            pivot_df["% Extern"] = (pivot_df.get("Extern", 0) / pivot_df["Gesamtstunden"]) * 100

            export_summary = pivot_df.reset_index()
            export_summary = export_summary[["Mitarbeiter", "Intern", "Extern", "Gesamtstunden", "% Intern", "% Extern"]]
            export_summary[["Intern", "Extern", "Gesamtstunden"]] = export_summary[["Intern", "Extern", "Gesamtstunden"]].round(2)
            export_summary[["% Intern", "% Extern"]] = export_summary[["% Intern", "% Extern"]].round(1)

            st.subheader("📊 Balkendiagramm Intern/Extern pro Mitarbeiter")
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
        df_abrechnung = pd.read_excel(upload, sheet_name=0, header=None)

        zielzeile = None
        for i, row in df_abrechnung.iterrows():
            if row.astype(str).str.contains("Rechnungsstellung [€]", case=False).any():
                zielzeile = i
                break

        if zielzeile is None:
            st.warning("⚠️ Keine Zeile mit 'Rechnungsstellung [€]' gefunden.")
        else:
            kuerzel_row = df_abrechnung.iloc[zielzeile - 1]
            werte_row = df_abrechnung.iloc[zielzeile + 1]
            gueltige_spalten = kuerzel_row[kuerzel_row.notna()].index

            df_clean = pd.DataFrame({
                "Kürzel": kuerzel_row[gueltige_spalten].values,
                "Rechnungsstellung_SOLL": werte_row[gueltige_spalten].values
            })

            df_clean["Rechnungsstellung_SOLL"] = (
                df_clean["Rechnungsstellung_SOLL"]
                .astype(str)
                .str.replace("€", "", regex=False)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
                .str.replace("-", "0", regex=False)
                .astype(float)
            )

            abrechnung_grouped = df_clean.groupby("Kürzel", as_index=False).sum()

            kuerzel_map = st.session_state.get("kuerzel_map", pd.DataFrame())
            if kuerzel_map.empty or "Kürzel" not in kuerzel_map.columns:
                st.warning("⚠️ Kein Kürzel-Mapping gefunden. Bitte zuerst in der Zweck-Kategorisierung pflegen.")
            else:
                if "Name" not in kuerzel_map.columns:
                    kuerzel_map.columns = ["Name", "Kürzel"]

                df_all = st.session_state.get("df")
                if not isinstance(df_all, pd.DataFrame):
                    st.warning("⚠️ Keine Zeitdaten geladen.")
                else:
                    df_ext = df_all[df_all["Verrechenbarkeit"] == "Extern"]
                    df_ext = df_ext.groupby("Mitarbeiter")["Dauer"].sum().reset_index()

                    df_ext = df_ext.merge(kuerzel_map, left_on="Mitarbeiter", right_on="Name", how="left")
                    df_ext = df_ext.dropna(subset=["Kürzel"])

                    merged = df_ext.merge(abrechnung_grouped, on="Kürzel", how="left")
                    merged["Rechnungsstellung_SOLL"] = merged["Rechnungsstellung_SOLL"].fillna(0)
                    merged["Differenz"] = merged["Dauer"] - merged["Rechnungsstellung_SOLL"]

                    st.subheader("📊 Vergleichstabelle")
                    st.dataframe(merged, use_container_width=True)

elif page == "📤 Export":
    st.title("📤 Datenexport")

    df = st.session_state.get("df")
    if not isinstance(df, pd.DataFrame):
        st.info("Bitte zuerst Daten hochladen und klassifizieren.")
    else:
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

        # Diagramm für PDF speichern
        fig, ax = plt.subplots(figsize=(10, 5))
        export_summary.plot(kind="bar", x="Mitarbeiter", y=["Intern", "Extern"], ax=ax)
        ax.set_ylabel("Stunden")
        ax.set_title("Stunden nach Verrechenbarkeit")
        fig.tight_layout()

        image_path = "temp_chart.png"
        fig.savefig(image_path)

        # PDF bauen
        pdf_path = f"history/exports/bericht_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.pdf"
        doc = SimpleDocTemplate(pdf_path, pagesize=A4)
        elements = [RLImage(image_path, width=500, height=300), Spacer(1, 12)]

        table_data = [export_summary.columns.tolist()] + export_summary.values.tolist()
        table = Table(table_data)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ]
            )
        )
        elements.append(table)
        doc.build(elements)

        with open(pdf_path, "rb") as f:
            st.download_button(
                "⬇️ PDF-Bericht herunterladen",
                data=f.read(),
                file_name=os.path.basename(pdf_path),
                mime="application/pdf",
            )

