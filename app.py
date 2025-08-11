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
APP_VERSION = "v0.0.6"

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

# ──────────────────────────────────────────────────────────────────────────────
# ZWECK-KATEGORISIERUNG – inkl. Kürzelpflege
# ──────────────────────────────────────────────────────────────────────────────
elif page == "🧠 Zweck-Kategorisierung":
    st.title("🧠 Zweck-Kategorisierung & Mapping")
    mapping_df = get_state_df("mapping_df", lade_mapping)
    kuerzel_df = get_state_df("kuerzel_map", lade_kuerzel)

    # Zweck-Mapping
    st.subheader("📋 Aktuelles Zweck-Mapping (persistiert)")
    edited_mapping = st.data_editor(
        mapping_df.sort_values("Zweck"),
        num_rows="dynamic",
        use_container_width=True,
        key="mapping_editor",
    )
    if st.button("💾 Mapping speichern"):
        st.session_state["mapping_df"] = edited_mapping.copy()
        speichere_mapping(st.session_state["mapping_df"])
        st.success("✅ Mapping gespeichert.")

    # Kürzel-Mapping
    st.markdown("---")
    st.subheader("👥 Mitarbeiter-Kürzel (persistiert)")
    edited_kuerzel = st.data_editor(
        kuerzel_df.sort_values("Name"),
        num_rows="dynamic",
        use_container_width=True,
        key="kuerzel_editor",
        column_config={
            "Name": st.column_config.TextColumn("Name", disabled=True),
            "Kürzel": st.column_config.TextColumn("Kürzel"),
        },
    )
    if st.button("💾 Kürzel speichern"):
        updated = edited_kuerzel[["Name", "Kürzel"]].copy()
        base = get_state_df("kuerzel_map", lade_kuerzel).copy()
        base = base.drop(columns=["Kürzel"], errors="ignore").merge(updated, on="Name", how="left")
        base["Kürzel"] = base["Kürzel"].fillna("")
        st.session_state["kuerzel_map"] = base.drop_duplicates(subset=["Name"])
        speichere_kuerzel(st.session_state["kuerzel_map"])
        st.success("✅ Kürzel gespeichert.")


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

    # Parameter: wie viele Stunden gelten als 1 Einsatztag?
    std_pro_tag = st.number_input("Arbeitsstunden pro Tag (für Umrechnung Stunden → Tage)", min_value=1.0, max_value=12.0, value=8.0, step=0.5)

    if upload:
        # 1) Rohdaten ohne Header einlesen, um die Headerzeile zu finden
        df0 = pd.read_excel(upload, sheet_name=0, header=None)

        # Heuristik: erste Zeile, die "einsatztage" oder "rechnung" erwähnt, als Header verwenden
        header_row = None
        kws = ("einsatztage", "rechnung", "kürzel", "kuerzel", "eur", "€")
        for i, row in df0.iterrows():
            row_text = " ".join(row.astype(str).str.lower().tolist())
            if any(k in row_text for k in kws):
                header_row = i
                break

        if header_row is None:
            # Fallback: nimm die erste nicht-leere Zeile
            for i, row in df0.iterrows():
                if row.notna().sum() >= 3:
                    header_row = i
                    break

        # Mit gefundener Headerzeile neu einlesen
        df_abrechnung = pd.read_excel(upload, sheet_name=0, header=header_row)
        # Leerspalten raus
        df_abrechnung = df_abrechnung.loc[:, df_abrechnung.columns.notna()]
        df_abrechnung = df_abrechnung.dropna(how="all", axis=1)

        # 2) Spalten automatisch erkennen (und per UI änderbar machen)
        def find_col(cands):
            for c in df_abrechnung.columns:
                name = str(c).strip().lower()
                if any(x in name for x in cands):
                    return c
            return None

        # mögliche Kandidaten
        col_kuerzel_auto = find_col(("kürzel", "kuerzel", "ks", "initial", "zeichen"))
        col_tage_soll_auto = find_col(("einsatztage", "tage", "soll"))
        col_betrag_soll_auto = find_col(("rechnung", "betrag", "€", "eur"))

        st.subheader("🧾 Spaltenzuordnung")
        col1, col2, col3 = st.columns(3)
        col_kuerzel = col1.selectbox("Spalte: Kürzel", options=list(df_abrechnung.columns), index=(list(df_abrechnung.columns).index(col_kuerzel_auto) if col_kuerzel_auto in df_abrechnung.columns else 0))
        col_tage_soll = col2.selectbox("Spalte: Einsatztage SOLL", options=list(df_abrechnung.columns), index=(list(df_abrechnung.columns).index(col_tage_soll_auto) if col_tage_soll_auto in df_abrechnung.columns else 0))
        col_betrag_soll = col3.selectbox("Spalte: Rechnungsstellung SOLL (€)", options=[None] + list(df_abrechnung.columns), index=(1 + list(df_abrechnung.columns).index(col_betrag_soll_auto) if col_betrag_soll_auto in df_abrechnung.columns else 0))

        # 3) Cleanen & aufbereiten (nur relevante Spalten)
        abr = df_abrechnung[[col_kuerzel, col_tage_soll] + ([col_betrag_soll] if col_betrag_soll else [])].copy()
        abr.columns = ["Kürzel", "Einsatztage_SOLL"] + (["Rechnungsstellung_SOLL"] if col_betrag_soll else [])

        # Zahlen normalisieren (Komma/€/Punkte)
        def to_float(x):
            s = str(x)
            s = s.replace("€", "").replace(".", "").replace(" ", "").replace("\xa0", "")
            s = s.replace(",", ".")
            s = s.replace("-", "0")
            try:
                return float(s)
            except:
                return 0.0

        abr["Einsatztage_SOLL"] = abr["Einsatztage_SOLL"].apply(to_float)
        if "Rechnungsstellung_SOLL" in abr.columns:
            abr["Rechnungsstellung_SOLL"] = abr["Rechnungsstellung_SOLL"].apply(to_float)

        # ggf. Dubletten je Kürzel aufsummieren
        abr = abr.groupby("Kürzel", as_index=False).sum(numeric_only=True)

        # 4) Zeitdaten (Extern) → Tage_IST je Kürzel
        df_all = st.session_state.get("df")
        kuerzel_map = st.session_state.get("kuerzel_map", pd.DataFrame())

        if not isinstance(df_all, pd.DataFrame) or df_all.empty:
            st.warning("⚠️ Keine Zeitdaten geladen (Seite '📁 Daten hochladen').")
        elif kuerzel_map.empty or "Kürzel" not in kuerzel_map.columns:
            st.warning("⚠️ Kein Kürzel-Mapping gefunden. Bitte zuerst in '🧠 Zweck-Kategorisierung' pflegen.")
        else:
            # sicherstellen, dass Mapping Spalten heißen wie erwartet
            if "Name" not in kuerzel_map.columns:
                # falls jemand CSV umbenannt hat
                kuerzel_map.columns = ["Name", "Kürzel"]

            # Extern-Daten aggregieren
            df_ext = df_all[df_all.get("Verrechenbarkeit").isin(["Extern"])]
            df_ext = df_ext.groupby("Mitarbeiter", as_index=False)["Dauer"].sum()

            # Mitarbeiter → Kürzel mappen
            df_ext = df_ext.merge(kuerzel_map, left_on="Mitarbeiter", right_on="Name", how="left")
            df_ext = df_ext.dropna(subset=["Kürzel"])

            # Stunden → Tage
            df_ext["Tage_IST"] = df_ext["Dauer"] / float(std_pro_tag)
            ist_by_k = df_ext.groupby("Kürzel", as_index=False)["Tage_IST"].sum()

            # 5) Zusammenführen
            merged = abr.merge(ist_by_k, on="Kürzel", how="outer").fillna(0)
            merged["Diff_Tage"] = merged["Tage_IST"] - merged["Einsatztage_SOLL"]

            # Optionale Controlling-Summe
            if "Rechnungsstellung_SOLL" in merged.columns:
                sum_betrag = merged["Rechnungsstellung_SOLL"].sum()
                st.metric("∑ Rechnungsstellung SOLL (€)", f"{sum_betrag:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

            st.subheader("📊 Vergleichstabelle")
            # Optional: schöne Spaltenreihenfolge
            cols = ["Kürzel", "Tage_IST", "Einsatztage_SOLL", "Diff_Tage"]
            if "Rechnungsstellung_SOLL" in merged.columns:
                cols.append("Rechnungsstellung_SOLL")
            # für Kontext auch die (anonymisierten) Mitarbeitenden dazulegen:
            merged = merged[cols]
            st.dataframe(merged, use_container_width=True)

            # Kurze Hinweise
            st.caption(f"Umrechnung: 1 Tag = {std_pro_tag:g} Stunden. 'Tage_IST' basieren ausschließlich auf Zeitdaten mit Verrechenbarkeit = Extern.")


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

