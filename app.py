import streamlit as st
from datetime import datetime

# Seiten-Titel & Konfiguration
st.set_page_config(page_title="Zeitdatenanalyse", layout="wide")

# Sidebar Navigation
st.sidebar.title("🔧 Navigation")
page = st.sidebar.radio("Wähle eine Ansicht", [
    "📁 Daten hochladen",
    "🧠 Zweck-Kategorisierung",
    "📊 Analyse & Visualisierung",
    "⬇️ Export"
])

# Dummy-Info-Box
st.sidebar.markdown("---")
st.sidebar.info("Baustatus: UI bereit\n\nLogik folgt.")

# Seiteninhalt
if page == "📁 Daten hochladen":
    st.title("📁 Excel-Datei hochladen")
    st.write("Hier kannst du deine Excel-Zeitdaten hochladen.")
    uploaded_file = st.file_uploader("Lade eine `.xlsx` Datei hoch", type=["xlsx"])
    if uploaded_file:
        st.success("Datei erfolgreich hochgeladen! (Logik folgt)")

elif page == "🧠 Zweck-Kategorisierung":
    st.title("🧠 Zweck-Kategorisierung")
    st.write("Hier kannst du Zwecke klassifizieren – entweder automatisch per KI oder manuell.")
    st.warning("Funktion noch in Arbeit...")

elif page == "📊 Analyse & Visualisierung":
    st.title("📊 Analyse & Visualisierung")
    st.write("Hier erscheinen später interaktive Auswertungen deiner Zeitdaten.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.selectbox("🔎 Wähle Mitarbeiter", options=["Alle", "Anna", "Ben", "Clara"])
    with col2:
        st.selectbox("📅 Zeitraum", options=["Alle", "2024-01", "2024-02", "2024-03"])

    st.info("Diagramm-Platzhalter")
    st.plotly_chart({}, use_container_width=True)

elif page == "⬇️ Export":
    st.title("⬇️ Export")
    st.write("Hier kannst du die verarbeiteten Daten herunterladen.")
    st.download_button("Download Excel", data=b"", file_name="zeitdaten.xlsx", disabled=True)

