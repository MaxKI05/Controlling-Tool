import os
import re
import io
from pathlib import Path
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
APP_VERSION = "v0.1.4"

os.makedirs("history/exports", exist_ok=True)
os.makedirs("history/uploads", exist_ok=True)
os.makedirs("history/rechnung", exist_ok=True)

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
# --- CSV robust lesen: erkennt Spaltennamen & Zahlformate ---
import io
import re

def lade_rechnung():
    if os.path.exists("Rechnung.xlsx"):
        df = pd.read_excel("Rechnung.xlsx", engine="openpyxl")
        df.columns = df.columns.astype(str).str.strip().str.lower()
        # Kürzel + Umsatz normalisieren
        kuerzel_col = next((c for c in df.columns if "kürzel" in c or "kuerzel" in c), None)
        umsatz_col = next((c for c in df.columns if "umsatz" in c or "euro" in c or "€" in c), None)
        if kuerzel_col and umsatz_col:
            out = df[[kuerzel_col, umsatz_col]].rename(columns={kuerzel_col: "Kürzel", umsatz_col: "Umsatz (€)"})
            out["Kürzel"] = out["Kürzel"].astype(str).str.strip()
            out["Umsatz (€)"] = pd.to_numeric(out["Umsatz (€)"], errors="coerce").fillna(0.0)
            return out
    return pd.DataFrame(columns=["Kürzel", "Umsatz (€)"])

def _norm(s: str) -> str:
    """klein, Leerzeichen raus, nur Buchstaben."""
    return re.sub(r"[^a-z]", "", str(s).lower())
def read_abrechnung(upload) -> pd.DataFrame:
    """
    Liest Abrechnungsdatei (CSV oder XLSX), sucht Kürzel & Einsatztage_SOLL.
    Kopfzeile ab Zeile 7 wird berücksichtigt.
    """
    import os
    ext = os.path.splitext(upload.name)[-1].lower()

    try:
        if ext == ".csv":
            df = pd.read_csv(upload, sep=";", header=7, engine="python", encoding="utf-8")
        else:
            df = pd.read_excel(upload, engine="openpyxl", header=7)
    except Exception as e:
        raise ValueError(f"Datei konnte nicht eingelesen werden: {e}")

    # Spalten normalisieren
    df.columns = df.columns.astype(str).str.strip().str.lower()

    # Kürzel-Spalte finden
    kuerzel_col = next((c for c in df.columns if c in ["pl", "kürzel", "kuerzel", "code"]), None)

    # Tage-Spalte finden (jetzt flexibler!)
    tage_col = next((c for c in df.columns if "einsatztage" in c), None)

    if not kuerzel_col or not tage_col:
        raise ValueError(f"Keine passenden Spalten gefunden. Gefunden: {list(df.columns)}")

    out = df[[kuerzel_col, tage_col]].rename(
        columns={kuerzel_col: "Kürzel", tage_col: "Einsatztage_SOLL"}
    )

    # Zahlen robust konvertieren
    out["Einsatztage_SOLL"] = (
        out["Einsatztage_SOLL"]
        .astype(str)
        .str.replace(r"[^0-9,.\-]", "", regex=True)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    out["Einsatztage_SOLL"] = pd.to_numeric(out["Einsatztage_SOLL"], errors="coerce").fillna(0.0)
    out["Kürzel"] = out["Kürzel"].astype(str).str.strip()

    return out.groupby("Kürzel", as_index=False)["Einsatztage_SOLL"].sum()


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
    st.title("📁 Dateien hochladen")

    # -------------------------
    # Zeitdaten hochladen
    # -------------------------
    st.header("⏱️ Zeitdaten hochladen")
    uploaded_file = st.file_uploader("Lade eine `.xlsx` Datei mit Zeitdaten hoch", type=["xlsx"], key="zeitdaten_upload")

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

            st.success("✅ Zeitdaten erfolgreich geladen.")
            st.subheader("📄 Vorschau der Zeitdaten")
            st.dataframe(df, use_container_width=True)

    st.markdown("## 📂 Hochgeladene Zeitdaten-Dateien")
    upload_files = sorted(os.listdir("history/uploads"), reverse=True)
    for f in upload_files:
        with open(os.path.join("history/uploads", f), "rb") as file:
            st.download_button(label=f"📄 {f}", data=file.read(), file_name=f)

    # -------------------------
    # Umsatzdaten hochladen
    # -------------------------
    st.header("💰 Umsatzdaten hochladen")
    rechnung_file = st.file_uploader("Lade eine Excel-Datei mit Kürzel und Umsatz (€)", type=["xlsx"], key="rechnung_upload")

    if rechnung_file:
        save_path = os.path.join("history/rechnung", "Rechnung.xlsx")
        with open(save_path, "wb") as f:
            f.write(rechnung_file.getvalue())
        st.success("✅ Umsatzdaten gespeichert als Rechnung.xlsx")

        try:
            rechnung_df = pd.read_excel(rechnung_file, engine="openpyxl")
            st.subheader("📄 Vorschau der Umsatzdaten")
            st.dataframe(rechnung_df, use_container_width=True)
        except Exception as e:
            st.error(f"Umsatzdaten konnten nicht geladen werden: {e}")

    # Anzeige vorhandener Umsatzdatei
    if os.path.exists(os.path.join("history/rechnung", "Rechnung.xlsx")):
        with open(os.path.join("history/rechnung", "Rechnung.xlsx"), "rb") as file:
            st.download_button(
                label="📄 Aktuelle Umsatzdaten (Rechnung.xlsx)",
                data=file.read(),
                file_name="Rechnung.xlsx"
            )

elif page == "🧠 Zweck-Kategorisierung":
    st.title("🧠 Zweck-Kategorisierung & Mapping")

    # Mapping immer laden
    mapping_df = st.session_state.get("mapping_df", lade_mapping())
    df = st.session_state.get("df")

    if df is None or "Zweck" not in df.columns:
        st.info("ℹ️ Keine Zeitdaten geladen – du kannst trotzdem das Mapping und Kürzel bearbeiten.")

    else:
        # ---------- 1) Automatisches GPT-Mapping nur für neue Zwecke ----------
        aktuelle_zwecke = set(df["Zweck"].dropna().astype(str).str.strip())
        bekannte_zwecke = set(mapping_df["Zweck"].dropna().astype(str).str.strip())
        neue_zwecke = sorted(aktuelle_zwecke - bekannte_zwecke)

        st.markdown(f"🔍 Neue Zwecke im aktuellen Datensatz: **{len(neue_zwecke)}**")

        if neue_zwecke:
            try:
                from utils.gpt import klassifiziere_verrechenbarkeit
                neue_mapping = []
                with st.spinner(f"🧠 {len(neue_zwecke)} neue Zwecke – KI klassifiziert..."):
                    for zweck in neue_zwecke:
                        kat = klassifiziere_verrechenbarkeit(zweck)
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
            except Exception:
                st.warning("⚠️ KI-Mapping konnte nicht automatisch durchgeführt werden.")

        # Mapping anwenden
        if df is not None:
            df = df.drop(columns=["Verrechenbarkeit"], errors="ignore")
            df = df.merge(mapping_df, on="Zweck", how="left")
            st.session_state["df"] = df

    # ---------- Tabs: Mapping und Kürzel IMMER anzeigen ----------
    tab1, tab2, tab3 = st.tabs(["📋 Aktuelles Mapping", "✍️ Manuell bearbeiten", "👥 Mitarbeiter-Kürzel"])

    with tab1:
        st.caption("Übersicht aller bekannten Zweck→Verrechenbarkeit-Zuordnungen.")
        show_map = mapping_df.copy()
        if not show_map.empty:
            show_map = show_map.sort_values("Zweck")
        st.dataframe(show_map, use_container_width=True)

    with tab2:
        st.caption("Manuelle Korrektur/Ergänzung des Zweck-Mappings.")
        edited_df = st.data_editor(
            mapping_df,
            num_rows="dynamic",
            use_container_width=True,
            key="mapping_editor"
        )
        if st.button("💾 Änderungen speichern", key="save_purpose_mapping"):
            edited_df.drop_duplicates(subset=["Zweck"], keep="last", inplace=True)
            st.session_state["mapping_df"] = edited_df
            speichere_mapping(edited_df)

            if df is not None:
                df_tmp = df.drop(columns=["Verrechenbarkeit"], errors="ignore")
                df_tmp = df_tmp.merge(edited_df, on="Zweck", how="left")
                st.session_state["df"] = df_tmp

            st.success("✅ Mapping gespeichert & angewendet.")

    with tab3:
        st.caption("Mitarbeiter-Kürzel pflegen (persistiert in kuerzel.csv).")

        kuerzel_df = st.session_state.get("kuerzel_map", lade_kuerzel())
        if kuerzel_df.empty:
            kuerzel_df = pd.DataFrame(columns=["Name", "Kürzel"])

        edited_kuerzel_df = st.data_editor(
            kuerzel_df,
            key="kuerzel_editor",
            use_container_width=True,
            num_rows="dynamic"
        )

        if st.button("💾 Kürzel speichern", key="save_initials"):
            edited_kuerzel_df.drop_duplicates(subset=["Name"], keep="last", inplace=True)
            st.session_state["kuerzel_map"] = edited_kuerzel_df
            speichere_kuerzel(edited_kuerzel_df)
            st.success("✅ Kürzel wurden gespeichert und bleiben erhalten.")

elif page == "📊 Analyse & Visualisierung":
    st.title("📊 Verrechenbarkeit Gesamtübersicht")

    df = st.session_state.get("df")
    if not isinstance(df, pd.DataFrame):
        st.warning("Bitte zuerst eine Datei hochladen.")
    else:
        if "Verrechenbarkeit" not in df.columns:
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

            # ---------------------------------------------------
            # Umsatz-Daten einlesen und anhängen
            # ---------------------------------------------------
            rechnung_df = lade_rechnung()
            kuerzel_map = st.session_state.get("kuerzel_map", lade_kuerzel())

            if not rechnung_df.empty and not kuerzel_map.empty:
                # 1) Mitarbeiter -> Kürzel mappen
                export_summary = export_summary.merge(
                    kuerzel_map[["Name", "Kürzel"]],
                    left_on="Mitarbeiter", right_on="Name", how="left"
                ).drop(columns=["Name"])

                # 2) Kürzel -> Umsatz joinen
                export_summary = export_summary.merge(
                    rechnung_df, on="Kürzel", how="left"
                )

                # 3) Kürzel-Spalte wieder entfernen (optional)
                export_summary.drop(columns=["Kürzel"], inplace=True, errors="ignore")

            # ---------------------------------------------------
            # Diagramm
            # ---------------------------------------------------
            st.subheader("📊 Balkendiagramm Intern/Extern pro Mitarbeiter")
            fig, ax = plt.subplots(figsize=(10, 5))
            export_summary.plot(kind="bar", x="Mitarbeiter", y=["Intern", "Extern"], ax=ax)
            ax.set_ylabel("Stunden")
            ax.set_title("Stunden nach Verrechenbarkeit")
            st.pyplot(fig)

            # ---------------------------------------------------
            # Tabelle
            # ---------------------------------------------------
            st.subheader("📄 Tabellenansicht")
            st.dataframe(export_summary, use_container_width=True)

            # ---------------------------------------------------
            # PDF-Export
            # ---------------------------------------------------
            if st.button("⬇️ PDF-Bericht exportieren"):
                fig, ax = plt.subplots(figsize=(10, 5))
                export_summary.plot(kind="bar", x="Mitarbeiter", y=["Intern", "Extern"], ax=ax)
                ax.set_ylabel("Stunden")
                ax.set_title("Stunden nach Verrechenbarkeit")
                fig.tight_layout()

                image_path = "temp_chart.png"
                fig.savefig(image_path)

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


elif page == "💰 Abrechnungs-Vergleich":
    st.title("💰 Vergleich: Zeitdaten vs Rechnungsstellung")

    # Stunden -> Tage
    std_pro_tag = st.number_input(
        "Arbeitsstunden pro Tag (für Umrechnung Stunden → Tage)",
        min_value=1.0, max_value=12.0, value=8.5, step=0.5
    )

    # Datei hochladen
    upload = st.file_uploader("Lade eine Abrechnungs-Datei hoch (XLSX oder CSV)", type=["csv", "xlsx"])
    if not upload:
        st.stop()

    # --- 1) Abrechnungsdatei einlesen ---
    try:
        abr = read_abrechnung(upload)
        st.success(f"Datei erkannt: {len(abr)} Zeilen (Spalten: Kürzel, Einsatztage_SOLL).")
        st.dataframe(abr.head(50), use_container_width=True)
    except Exception as e:
        st.error(f"Abrechnungsdatei konnte nicht gelesen werden: {e}")
        st.stop()

    # --- 2) Zeitdaten (IST) aufbereiten ---
    df_all = st.session_state.get("df")
    kuerzel_map = st.session_state.get("kuerzel_map", lade_kuerzel())

    if (df_all is None) or df_all.empty:
        st.warning("⚠️ Keine Zeitdaten geladen (Seite „📁 Daten hochladen“). Der Vergleich ist erst nach Upload möglich.")
        st.stop()

    if kuerzel_map.empty or not set(["Name", "Kürzel"]).issubset(kuerzel_map.columns):
        st.warning("⚠️ Kein gültiges Kürzel-Mapping gefunden. Bitte in „🧠 Zweck-Kategorisierung“ → Tab „👥 Mitarbeiter-Kürzel“ pflegen.")
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

    # Kürzel joinen
    df_ext_map = df_ext_group.merge(kuerzel_map, left_on="Mitarbeiter", right_on="Name", how="left")
    df_ext_map = df_ext_map.dropna(subset=["Kürzel"])
    df_ext_map["Kürzel"] = df_ext_map["Kürzel"].astype(str).str.strip()

    ist_by_k = df_ext_map.groupby("Kürzel", as_index=False)["Externe_Stunden"].sum()
    ist_by_k["Tage_IST"] = ist_by_k["Externe_Stunden"] / float(std_pro_tag)

    # --- 3) Merge Abrechnung (SOLL) mit IST ---
    merged = abr.merge(ist_by_k, on="Kürzel", how="outer").fillna(0)
    merged["Diff_Tage"] = merged["Tage_IST"] - merged["Einsatztage_SOLL"]

    out = merged.copy()
    if "Externe_Stunden" in out:
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
        f"Logik: Datei liefert „Kürzel“ & „Einsatztage_SOLL“. "
        f"Zeitdaten extern → Externe_Stunden ÷ {std_pro_tag:g} = Tage_IST. "
        f"Diff_Tage = Tage_IST − Einsatztage_SOLL."
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

