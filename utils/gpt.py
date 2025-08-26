# utils/gpt.py
import os
import time
import pandas as pd
from openai import OpenAI

# API-Key: zuerst ENV, optional Streamlit-Secrets als Fallback
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    try:
        import streamlit as st
        api_key = st.secrets.get("OPENAI_API_KEY")
    except Exception:
        api_key = None

if not api_key:
    raise RuntimeError(
        "Kein OpenAI-API-Key gefunden. Setze OPENAI_API_KEY oder st.secrets['OPENAI_API_KEY']."
    )

client = OpenAI(api_key=api_key)

SYSTEM_MSG = "Du bist ein Klassifizierungs- und Extraktions-Experte für Zeitdaten und Abrechnungs-Excel."

# ──────────────────────────────
# Verrechenbarkeit (Intern/Extern)
# ──────────────────────────────
def klassifiziere_verrechenbarkeit(zweck: str) -> str:
    """
    Gibt 'Intern' oder 'Extern' zurück. Fehler werden nach wenigen Retries hochgereicht.
    """
    prompt = f"""
Der folgende Zweck stammt aus einer Zeitbuchung eines Ingenieurbüros für Nachhaltigkeitsberatung.

Klassifiziere als:
- Extern: projektbezogene Kundenleistung (z.B. Berechnung, DGNB, LCA/LCC, Zertifizierung, Planung, Audit, Ausführung).
- Intern: firmeninterne Tätigkeit (z.B. Akquise, interne Besprechung, Verwaltung, Personal).

Wenn nicht klar intern, dann Extern.

Zweck: "{zweck}"

Antworte nur mit: Intern oder Extern.
""".strip()

    last_err = None
    for attempt in range(3):
        try:
            r = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0,
                messages=[
                    {"role": "system", "content": SYSTEM_MSG},
                    {"role": "user", "content": prompt},
                ],
            )
            ans = (r.choices[0].message.content or "").strip().lower()
            if ans.startswith("intern"):
                return "Intern"
            if ans.startswith("extern"):
                return "Extern"
            return "Unbekannt"
        except Exception as e:
            last_err = str(e)
            time.sleep(1.5 ** attempt)

    raise RuntimeError(f"GPT-Klassifizierung fehlgeschlagen: {last_err}")


# ──────────────────────────────
# Abrechnungs-Zusammenfassung aus Excel
# ──────────────────────────────
def extrahiere_abrechnungsblock(df: pd.DataFrame) -> pd.DataFrame:
    """
    Nimmt ein rohes Excel-DataFrame (ohne Header), schickt es an GPT
    und bekommt zurück, welche Kürzel + Einsatztage SOLL relevant sind.

    Rückgabe: DataFrame mit ["Kürzel", "Einsatztage_SOLL"]
    """
    # Textuelles Preview der unteren ~30 Zeilen
    preview = df.tail(40).to_string(index=False)

    prompt = f"""
Du erhältst einen Ausschnitt einer Excel-Tabelle mit Abrechnungsdaten.
Die Tabelle enthält in einer Zusammenfassung Kürzel (z.B. "SS", "PK", "IT") 
und die zugehörigen Einsatztage SOLL (meist numerische Werte in der Nachbarspalte).

Deine Aufgabe:
- Identifiziere die relevanten Zeilen, die Kürzel enthalten (meist 1–3 Buchstaben, großgeschrieben).
- Nimm die passende Zahl daneben als "Einsatztage_SOLL".
- Gib mir ein CSV mit zwei Spalten zurück: Kürzel,Einsatztage_SOLL

Falls nichts gefunden: gib ein leeres CSV zurück.

Hier ist der Tabellenausschnitt (als Text):

{preview}
"""

    last_err = None
    for attempt in range(3):
        try:
            r = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0,
                messages=[
                    {"role": "system", "content": SYSTEM_MSG},
                    {"role": "user", "content": prompt},
                ],
            )
            ans = (r.choices[0].message.content or "").strip()

            # CSV-Parsing in DataFrame
            from io import StringIO
            try:
                parsed = pd.read_csv(StringIO(ans))
                if "Kürzel" in parsed.columns and "Einsatztage_SOLL" in parsed.columns:
                    parsed["Kürzel"] = parsed["Kürzel"].astype(str).str.strip()
                    parsed["Einsatztage_SOLL"] = pd.to_numeric(parsed["Einsatztage_SOLL"], errors="coerce").fillna(0.0)
                    return parsed
            except Exception:
                pass

            # Falls nicht parsebar → zurückgeben als leeres DF
            return pd.DataFrame(columns=["Kürzel", "Einsatztage_SOLL"])

        except Exception as e:
            last_err = str(e)
            time.sleep(1.5 ** attempt)

    raise RuntimeError(f"GPT-Extraktion fehlgeschlagen: {last_err}")


# ──────────────────────────────
# Manuell testen
# ──────────────────────────────
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "zweck":
        text = " ".join(sys.argv[2:]) or "DGNB Nachweis"
        print(klassifiziere_verrechenbarkeit(text))
    else:
        # Dummy-Test mit Fake-Daten
        test_df = pd.DataFrame({
            0: ["SS", "PK", "Summe"],
            1: [7.25, 3.5, 10.75]
        })
        print(extrahiere_abrechnungsblock(test_df))
