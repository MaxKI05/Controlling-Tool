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
APP_VERSION = "v0.0.7"

os.makedirs("history/exports", exist_ok=True)
os.makedirs("history/uploads", exist_ok=True)

# ──────────────────────────────────────────────────────────────────────────────
# Helper-Funktionen
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data
def load_excel(file):
    return pd.read_excel(file)

def extrahiere_zweck(text: str):
    if isinstance(text, str) and "-" in text:
        zweck_raw = text.split("-")[-1].strip()
        return re.sub(r"^\d+_?", "", zweck_raw)
    return None

def lade_mapping():
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

def speichere_mapping(df):
    out = df.copy()
    out["Zweck"] = out["Zweck"].astype(str).str.strip()
    out["Verrechenbarkeit"] = out["Verrechenbarkeit"].fillna("Unbekannt")
    out.drop_duplicates(subset=["Zweck"], inplace=True)
    out.to_csv("mapping.csv", index=False)

def lade_kuerzel():
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

def speichere_kuerzel(df):
    out = df.copy()
    out["Name"] = out["Name"].astype(str).str.strip()
    out["Kürzel"] = out["Kürzel"].astype(str).str.strip()
    out.dropna(subset=["Name"], inplace=True)
    out.drop_duplicates(subset=["Name"], inplace=True)
    out.to_csv("kuerzel.csv", index=False)

def get_state_df(key, loader):
    if key not in st.session_state or not isinstance(st.session_state[key], pd.DataFrame):
        st.session_state[key] = loader()
    return st.session_state[key]

# ──────────────────────────────────────────────────────────────────────────────
# Session-State initialisieren
# ──────────────────────────────────────────────────────────────────────────────
if "df" not in st.session_state:
    st.session_state["df"] = None
if "mapping_df" not in st.session_state:
    st.session_state["mapping_df"] = lade_mapping()
if "kuerzel_map" not in st.session_state:
    st.session_state["kuerzel_map"] = lade_kuerzel()

# ──────────────────────────────────────────────────────────────────────────────
# Sidebar Navigation
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
# STARTSEITE
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

# ──────────────────────────────────────────────────────────────────────────────
# DATEN HOCHLADEN – mit automatischem Kürzelimport
# ──────────────────────────────────────────────────────────────────────────────
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

            # ➕ Automatischer Import neuer Mitarbeitenden in kuerzel.csv
            try:
                kuerzel_df = get_state_df("kuerzel_map", lade_kuerzel)
                aktuelle_namen = set(df["Mitarbeiter"].dropna().astype(str).str.strip())
                bekannte_namen = set(kuerzel_df["Name"].astype(str).str.strip())
                neu = sorted(list(aktuelle_namen - bekannte_namen))
                if neu:
                    addon = pd.DataFrame({"Name": neu, "Kürzel": ""})
                    st.session_state["kuerzel_map"] = (
                        pd.concat([kuerzel_df, addon], ignore_index=True)
                          .drop_duplicates(subset=["Name"])
                    )
                    speichere_kuerzel(st.session_state["kuerzel_map"])
                    st.info(f"👥 {len(neu)} neue Mitarbeitende wurden zur Kürzel-Tabelle hinzugefügt.")
            except Exception as e:
                st.warning(f"Konnte neue Mitarbeitende nicht übernehmen: {e}")

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
    df = st.session_state.get("df")
    if df is None or "Zweck" not in df.columns:
        st.warning("⚠️ Bitte zuerst eine Excel-Datei hochladen.")
    else:
        # ---------- 1) Automatisches GPT-Mapping NUR für neue Zwecke ----------
        # Aktuelle & bekannte Zwecke robust ermitteln
        mapping_df = st.session_state.get("mapping_df", lade_mapping())
        aktuelle_zwecke = set(
            df["Zweck"].dropna().astype(str).str.strip()
        )
        bekannte_zwecke = set()
        if not mapping_df.empty and "Zweck" in mapping_df.columns:
            bekannte_zwecke = set(mapping_df["Zweck"].dropna().astype(str).str.strip())

        neue_zwecke = sorted(aktuelle_zwecke - bekannte_zwecke)

        st.markdown(f"🔍 Neue Zwecke im aktuellen Datensatz: **{len(neue_zwecke)}**")

        if neue_zwecke:
            try:
                from utils.gpt import klassifiziere_verrechenbarkeit
                neue_mapping = []
                with st.spinner(f"🧠 {len(neue_zwecke)} neue Zwecke – KI klassifiziert..."):
                    for zweck in neue_zwecke:
                        kat = klassifiziere_verrechenbarkeit(zweck)  # erwartetes Ergebnis: "Intern" oder "Extern"
                        # Falls die KI etwas Unerwartetes zurückgibt, leer lassen -> manuell nachpflegen
                        if kat not in ("Intern", "Extern"):
                            kat = None
                        neue_mapping.append({"Zweck": zweck, "Verrechenbarkeit": kat})

                if neue_mapping:
                    new_df = pd.DataFrame(neue_mapping)
                    mapping_df = pd.concat([mapping_df, new_df], ignore_index=True)
                    mapping_df.drop_duplicates(subset=["Zweck"], keep="last", inplace=True)
                    st.session_state["mapping_df"] = mapping_df
                    speichere_mapping(mapping_df)
                    st.success("✅ Neues Mapping gespeichert.")
            except Exception as e:
                st.warning("⚠️ KI-Mapping konnte nicht automatisch durchgeführt werden. Bitte manuell nachpflegen.")
                # kein st.stop(); wir erlauben manuelle Bearbeitung

        # ---------- 2) Mapping anwenden (merge) ----------
        df = df.drop(columns=["Verrechenbarkeit"], errors="ignore")
        df = df.merge(st.session_state["mapping_df"], on="Zweck", how="left")
        st.session_state["df"] = df

        # ---------- 3) Tabs: aktuelles Mapping & manuell bearbeiten ----------
        tab1, tab2, tab3 = st.tabs(["📋 Aktuelles Mapping", "✍️ Manuell bearbeiten", "👥 Mitarbeiter-Kürzel"])

        with tab1:
            st.caption("Übersicht aller bekannten Zweck→Verrechenbarkeit-Zuordnungen.")
            show_map = st.session_state["mapping_df"].copy()
            if not show_map.empty:
                show_map = show_map.sort_values("Zweck")
            st.dataframe(show_map, use_container_width=True)

        with tab2:
            st.caption("Manuelle Korrektur/Ergänzung des Zweck-Mappings.")
            edited_df = st.data_editor(
                st.session_state["mapping_df"],
                num_rows="dynamic",
                use_container_width=True,
                key="mapping_editor"
            )
            if st.button("💾 Änderungen speichern", key="save_purpose_mapping"):
                # Persistenz + erneutes Anwenden
                edited_df.drop_duplicates(subset=["Zweck"], keep="last", inplace=True)
                st.session_state["mapping_df"] = edited_df
                speichere_mapping(edited_df)

                df_tmp = st.session_state["df"].drop(columns=["Verrechenbarkeit"], errors="ignore")
                df_tmp = df_tmp.merge(edited_df, on="Zweck", how="left")
                st.session_state["df"] = df_tmp

                st.success("✅ Mapping gespeichert & angewendet.")

        # ---------- 4) Mitarbeiter-Kürzel direkt hier pflegen (Session-Only, keine CSV) ----------
        with tab3:
            st.caption("Trage hier manuell die Kürzel zu den Mitarbeitenden ein. Diese werden im Abrechnungs-Vergleich verwendet.")
            # Basis: alle Namen aus den Zeitdaten
            alle_namen = sorted(set(df["Mitarbeiter"].dropna().astype(str)))

            # Bisheriges Mapping aus Session laden (falls vorhanden)
            existing = st.session_state.get("kuerzel_map")
            if existing is None or existing.empty or "Name" not in existing.columns or "Kürzel" not in existing.columns:
                kuerzel_df = pd.DataFrame({"Name": alle_namen, "Kürzel": [""] * len(alle_namen)})
            else:
                # Union aus vorhandenen Namen + neuen Namen, Kürzel wenn vorhanden beibehalten
                kuerzel_df = pd.DataFrame({"Name": alle_namen})
                kuerzel_df = kuerzel_df.merge(existing[["Name", "Kürzel"]], on="Name", how="left").fillna({"Kürzel": ""})

            edited_kuerzel_df = st.data_editor(
                kuerzel_df,
                key="kuerzel_editor",
                use_container_width=True,
                num_rows="dynamic"
            )
            if st.button("💾 Kürzel speichern", key="save_initials"):
                # nur eindeutige Namen, leere Kürzel erlaubt (dann werden diese Personen im Vergleich ignoriert)
                edited_kuerzel_df.drop_duplicates(subset=["Name"], keep="last", inplace=True)
                st.session_state["kuerzel_map"] = edited_kuerzel_df
                st.success("✅ Kürzel wurden gespeichert.")



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

    # Umrechnung Stunden -> Tage (IST-Seite)
    std_pro_tag = st.number_input(
        "Arbeitsstunden pro Tag (für Umrechnung Stunden → Tage)",
        min_value=1.0, max_value=12.0, value=8.5, step=0.5
    )

    upload = st.file_uploader("Lade eine Abrechnungs-Excel hoch", type=["xlsx"])
    if not upload:
        st.stop()

    # --- Roh einlesen (ohne Header)
    try:
        raw = pd.read_excel(upload, sheet_name=0, header=None)
    except Exception as e:
        st.error(f"Abrechnung konnte nicht gelesen werden: {e}")
        st.stop()

    # -------- Helper zum Bereinigen von Zahlen
    def to_float(x):
        if pd.isna(x):
            return 0.0
        s = str(x)
        s = s.replace("€", "").replace("\u20ac", "")
        s = s.replace("'", "")
        s = s.replace("\xa0", "").replace(" ", "")
        s = s.replace(",", ".")
        try:
            return float(s)
        except:
            return 0.0

    # -------- Fix: Zeilen 125–136 nutzen (Index 124–135 in Pandas)
    try:
        abr = pd.DataFrame({
            "Kürzel": raw.iloc[124:136, 2].astype(str).str.strip(),     # Spalte C (Index 2)
            "Einsatztage_SOLL": raw.iloc[124:136, 3].apply(to_float)   # Spalte D (Index 3)
        })
    except Exception as e:
        st.error(f"Fehler beim Extrahieren der Soll-Einsatztage: {e}")
        st.stop()

    abr = abr.dropna(subset=["Kürzel"])
    abr["Kürzel"] = abr["Kürzel"].astype(str).str.strip()
    abr["Einsatztage_SOLL"] = abr["Einsatztage_SOLL"].fillna(0.0)

    # -------- Zeitdaten-IST (extern) per Kürzel
    df_all = st.session_state.get("df")
    kuerzel_map = st.session_state.get("kuerzel_map", pd.DataFrame())

    if not isinstance(df_all, pd.DataFrame) or df_all.empty:
        st.warning("⚠️ Keine Zeitdaten geladen (Seite '📁 Daten hochladen').")
        st.stop()
    if kuerzel_map.empty or not set(["Name", "Kürzel"]).issubset(kuerzel_map.columns):
        st.warning("⚠️ Kein gültiges Kürzel-Mapping gefunden. Bitte zuerst in '🧠 Zweck-Kategorisierung' pflegen.")
        st.stop()

    df_ext = df_all[df_all.get("Verrechenbarkeit").isin(["Extern"])].copy()
    if df_ext.empty:
        st.info("Keine externen Zeitdaten vorhanden.")
        st.stop()

    df_ext_group = (
        df_ext.groupby("Mitarbeiter", as_index=False)["Dauer"]
        .sum()
        .rename(columns={"Dauer": "Externe_Stunden"})
    )
    df_ext_map = df_ext_group.merge(kuerzel_map, left_on="Mitarbeiter", right_on="Name", how="left")
    df_ext_map = df_ext_map.dropna(subset=["Kürzel"])
    df_ext_map["Kürzel"] = df_ext_map["Kürzel"].astype(str).str.strip()

    ist_by_k = df_ext_map.groupby("Kürzel", as_index=False)["Externe_Stunden"].sum()
    ist_by_k["Tage_IST"] = ist_by_k["Externe_Stunden"] / float(std_pro_tag)

    # -------- Mergen & Anzeige
    merged = abr.merge(ist_by_k, on="Kürzel", how="outer").fillna(0)
    merged["Diff_Tage"] = merged["Tage_IST"] - merged["Einsatztage_SOLL"]

    out = merged.copy()
    out["Externe_Stunden"] = out["Externe_Stunden"].round(2)
    out["Tage_IST"] = out["Tage_IST"].round(2)
    out["Einsatztage_SOLL"] = out["Einsatztage_SOLL"].round(2)
    out["Diff_Tage"] = out["Diff_Tage"].round(2)

    st.subheader("📊 Vergleichstabelle")
    st.dataframe(
        out[["Kürzel", "Externe_Stunden", "Tage_IST", "Einsatztage_SOLL", "Diff_Tage"]].sort_values("Kürzel"),
        use_container_width=True
    )

    st.caption(
        "Fix: Zeilen 125–136 der Abrechnung werden genutzt. "
        "Zeitdaten extern → Externe_Stunden ÷ Arbeitsstunden/Tag = Tage_IST. "
        "Diff_Tage = Tage_IST − Einsatztage_SOLL."
    )



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

