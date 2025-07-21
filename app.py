import streamlit as st
import pandas as pd
from datetime import datetime

# 📐 Seiten-Layout definieren
st.set_page_config(
    page_title="Zeitdatenanalyse Dashboard",
    page_icon="📊",
    layout="wide"
)

# 🧱 Dummy-Daten für Vorschau
@st.cache_data
def load_dummy_data():
    return pd.DataFrame({
        "Mitarbeiter": ["Anna", "Ben", "Anna", "Clara", "Ben"],
        "Projekt": ["Projekt X", "Projekt Y", "Projekt X", "Projekt Z", "Projekt Y"],
        "Zweck": ["Analyse", "Meeting", "Workshop", "Analyse", "Schulung"],
        "Datum": pd.to_datetime(["2024-01-10", "2024-01-15", "2024-02-05", "2024-02-20", "2024-03-10"]),
        "Stunden": [3.5, 2.0, 5.0, 4.0, 6.0]
    })

df = load_dummy_data()

# 🎛️ Sidebar mit Navigation
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
        label_visibility="collapsed",
        index=0
    )

    st.markdown("---")
    st.markdown("### ℹ️ Info")
    st.markdown("Baustatus: **UI-Prototyp**")
    st.caption("Funktionen werden schrittweise aktiviert.")

    st.markdown("---")
    st.markdown("👤 **Max KI Dashboard**  \nVersion 0.1 – Juli 2025")

# 🏠 Startseite
if page == "🏠 Start":
    st.title("👋 Willkommen im Zeitdatenanalyse-Dashboard")
    
    st.markdown("""
    Dieses Tool unterstützt dich bei der Auswertung und Visualisierung von Zeitdaten aus Excel-Dateien.

    **Funktionen:**
    - 📁 Excel-Dateien hochladen & analysieren
    - 🧠 Automatische Zweck-Kategorisierung (auch per KI)
    - 📊 Interaktive Visualisierungen und Auswertungen
    - ⬇️ Export fertiger Ergebnisse

    ---
    """)

    st.subheader("📊 Beispielhafte Analyse (Demo-Daten)")

    st.write("Stunden pro Zweck (Demo):")
    demo_agg = df.groupby("Zweck")["Stunden"].sum().reset_index()
    st.bar_chart(demo_agg.set_index("Zweck"))

    st.markdown("---")
    st.info("Navigiere mit der Sidebar durch die App.")

# 📁 Upload-Seite
elif page == "📁 Daten hochladen":
    st.title("📁 Excel-Datei hochladen")
    st.markdown("Hier kannst du deine Excel-Zeitdaten hochladen und validieren.")
    
    uploaded_file = st.file_uploader("Wähle eine `.xlsx` Datei", type=["xlsx"])
    if uploaded_file:
        st.success("✅ Datei erfolgreich hochgeladen (Verarbeitung folgt).")
        # TODO: parse Excel
    else:
        st.info("Beispieldaten werden verwendet.")
        st.dataframe(df)

# 🧠 Zweck-Kategorisierung
elif page == "🧠 Zweck-Kategorisierung":
    st.title("🧠 Zweck-Kategorisierung")
    st.markdown("Bekannte Zwecke werden automatisch zugeordnet. Unbekannte Zwecke kannst du später per KI analysieren lassen.")
    st.warning("⚠️ Funktion noch nicht implementiert.")
    st.dataframe(df[["Zweck"]].drop_duplicates())

# 📊 Visualisierung
elif page == "📊 Analyse & Visualisierung":
    st.title("📊 Analyse & Visualisierung")
    st.markdown("Hier erscheinen später interaktive Diagramme zu Zeitaufwand, Kategorien und Projekten.")

    col1, col2 = st.columns(2)
    with col1:
        st.selectbox("🔎 Wähle Mitarbeiter", options=["Alle", "Anna", "Ben", "Clara"])
    with col2:
        st.selectbox("📅 Zeitraum", options=["Alle", "2024-01", "2024-02", "2024-03"])

    st.info("📉 Diagramm-Platzhalter (Plot folgt)")

# ⬇️ Export
elif page == "⬇️ Export":
    st.title("⬇️ Export der aggregierten Daten")
    st.markdown("Hier kannst du deine Auswertung als Excel-Datei herunterladen.")
    st.download_button("Download Excel-Datei", data=b"", file_name="zeitdaten_auswertung.xlsx", disabled=True)
