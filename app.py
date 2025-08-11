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

    # Umrechnung Stunden -> Tage
    std_pro_tag = st.number_input(
        "Arbeitsstunden pro Tag (für Umrechnung Stunden → Tage)",
        min_value=1.0, max_value=12.0, value=8.5, step=0.5
    )

    upload = st.file_uploader("Lade eine Abrechnungs-Excel hoch", type=["xlsx"])
    if not upload:
        st.stop()

    # ── Datei roh einlesen (ohne Header), weil das Sheet eine Matrix ist
    try:
        raw = pd.read_excel(upload, sheet_name=0, header=None)
    except Exception as e:
        st.error(f"Abrechnung konnte nicht gelesen werden: {e}")
        st.stop()

    # Helper fürs Zahl-Parsen (€, Punkt/Komma, Leerzeichen etc.)
    def to_float(x):
        s = str(x)
        s = s.replace("€", "").replace("\u20ac", "")
        s = s.replace("'", "")  # Tausendertrenner, falls CH-Format
        s = s.replace(".", "").replace("\xa0", "").replace(" ", "")
        s = s.replace(",", ".")
        s = s.replace("-", "0")
        try:
            return float(s)
        except:
            return None

    # ── 1) Euro-Spalte automatisch finden und Summe bilden
    euro_col_idx = None
    for j in range(min(40, raw.shape[1])):                # nur die ersten ~40 Spalten scannen
        col_text = " ".join(raw[j].dropna().astype(str).str.lower().tolist())
        if ("rechnungsstellung" in col_text) and (("€" in col_text) or ("eur" in col_text)):
            euro_col_idx = j
            break

    euro_sum = 0.0
    if euro_col_idx is not None:
        euro_vals = raw[euro_col_idx].apply(to_float)
        euro_sum = pd.Series([v for v in euro_vals if v is not None]).sum()

    # ── 2) Zeile mit Kürzel-Header erkennen (viele 1–3 Buchstaben in Großschrift)
    def is_kuerzel_token(s):
        s = str(s).strip()
        return s.isupper() and (1 <= len(s) <= 3) and s.isalpha()

    header_row = None
    header_candidates = []
    for i in range(min(80, raw.shape[0])):               # obere ~80 Zeilen durchsuchen
        row = raw.iloc[i]
        tokens = [str(x).strip() for x in row if is_kuerzel_token(x)]
        if len(tokens) >= 5:                              # Heuristik: mind. 5 Kürzel in der Zeile
            header_candidates.append((i, tokens))
    if header_candidates:
        header_row = header_candidates[0][0]

    if header_row is None:
        st.error("Konnte keine Kürzel-Header-Zeile finden (Matrix-Layout). Bitte prüfe das Sheet.")
        st.stop()

    # Alle Spalten (Indices) sammeln, die in dieser Zeile wie Kürzel aussehen – zusammenhängenden Block nehmen
    kuerzel_cols = []
    for j, val in raw.iloc[header_row].items():
        if is_kuerzel_token(val):
            kuerzel_cols.append(j)

    # zusammenhängenden Block extrahieren (falls links/rechts "Müll" steht)
    kuerzel_cols = sorted(kuerzel_cols)
    # Falls Lücken drin sind, nehmen wir den längsten zusammenhängenden Bereich
    blocks, cur = [], [kuerzel_cols[0]]
    for a, b in zip(kuerzel_cols, kuerzel_cols[1:]):
        if b == a + 1:
            cur.append(b)
        else:
            blocks.append(cur)
            cur = [b]
    blocks.append(cur)
    kuerzel_block = max(blocks, key=len)                 # längster Block
    kuerzel_cols = kuerzel_block

    # Kürzel-Namen aus der Headerzeile lesen
    kuerzel_names = [str(raw.iat[header_row, j]).strip() for j in kuerzel_cols]

    # ── 3) Datenbereich nach unten bestimmen: bis "Team Gesamt" / "Monatsübersicht" / leerer Bereich
    end_row = raw.shape[0] - 1
    stop_keywords = ("team gesamt", "monatsübersicht", "platzhalter")
    for i in range(header_row + 1, raw.shape[0]):
        left_text = str(raw.iat[i, 0]).strip().lower()
        full_text = " ".join(raw.iloc[i].astype(str).tolist()).lower()
        if any(k in left_text for k in stop_keywords) or any(k in full_text for k in stop_keywords):
            end_row = i - 1
            break

    # ── 4) Einsatztage_SOLL je Kürzel summieren (nur Zahlen in diesem Bereich)
    soll_summen = []
    for j, name in zip(kuerzel_cols, kuerzel_names):
        col_vals = raw.iloc[header_row + 1:end_row + 1, j].apply(to_float)
        val = pd.Series([v for v in col_vals if v is not None]).sum()
        soll_summen.append({"Kürzel": name, "Einsatztage_SOLL": float(val)})

    abr = pd.DataFrame(soll_summen)
    abr = abr.groupby("Kürzel", as_index=False).sum(numeric_only=True)

    # ── 5) Zeitdaten aus Session: Externe Stunden je Mitarbeiter -> über Kürzel mappen -> Tage_IST
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

    df_ext_group = df_ext.groupby("Mitarbeiter", as_index=False)["Dauer"].sum().rename(columns={"Dauer": "Externe_Stunden"})
    df_ext_map = df_ext_group.merge(kuerzel_map, left_on="Mitarbeiter", right_on="Name", how="left")
    df_ext_map = df_ext_map.dropna(subset=["Kürzel"])
    df_ext_map["Kürzel"] = df_ext_map["Kürzel"].astype(str).str.strip()
    ist_by_k = df_ext_map.groupby("Kürzel", as_index=False)["Externe_Stunden"].sum()
    ist_by_k["Tage_IST"] = ist_by_k["Externe_Stunden"] / float(std_pro_tag)

    # ── 6) Zusammenführen & Ausgabe
    merged = abr.merge(ist_by_k, on="Kürzel", how="outer").fillna(0)
    merged["Diff_Tage"] = merged["Tage_IST"] - merged["Einsatztage_SOLL"]

    # Summe Euro anzeigen (aus kompletter Spalte "Rechnungsstellung [€]")
    if euro_col_idx is not None:
        st.metric(
            "∑ Rechnungsstellung SOLL (€)",
            f"{euro_sum:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        )

    st.subheader("📊 Vergleichstabelle")
    out = merged.copy()
    if "Externe_Stunden" in out:
        out["Externe_Stunden"] = out["Externe_Stunden"].round(2)
    out["Tage_IST"] = out["Tage_IST"].round(2)
    out["Einsatztage_SOLL"] = out["Einsatztage_SOLL"].round(2)
    out["Diff_Tage"] = out["Diff_Tage"].round(2)

    cols_out = ["Kürzel", "Externe_Stunden", "Tage_IST", "Einsatztage_SOLL", "Diff_Tage"]
    # (Euro nur gesamt relevant; wenn du pro Kürzel auch Euro hast, könnten wir das später ergänzen)
    st.dataframe(out[cols_out].sort_values("Kürzel"), use_container_width=True)

    st.caption(
        f"Vergleichslogik: Externe_Stunden (Zeitdaten) ÷ {std_pro_tag:g} = Tage_IST. "
        "Verglichen mit Einsatztage_SOLL (Summe der Kürzel-Spalten in der Abrechnungsdatei). "
        "Die Euro-Summe wird 1:1 als Gesamtwert aus der Abrechnungsdatei übernommen."
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

