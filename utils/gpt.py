# utils/gpt.py
import os
import time
from openai import OpenAI

# --- API-Key laden: zuerst ENV, fallback auf st.secrets (wenn vorhanden) ---
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    try:
        import streamlit as st  # optional
        api_key = st.secrets.get("OPENAI_API_KEY")
    except Exception:
        api_key = None

if not api_key:
    raise RuntimeError(
        "Kein OpenAI-API-Key gefunden. Setze OPENAI_API_KEY als Umgebungsvariable "
        "oder lege ihn in st.secrets['OPENAI_API_KEY'] ab."
    )

client = OpenAI(api_key=api_key)

SYSTEM_MSG = "Du bist ein Klassifizierungs-Experte für Zeitdaten."

def klassifiziere_verrechenbarkeit(zweck: str) -> str:
    """
    Gibt 'Intern' oder 'Extern' zurück. Hebt Fehler nach Retries an den Aufrufer weiter.
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
    for attempt in range(3):  # kleiner Retry bei Netz/Ratelimit
        try:
            r = client.chat.completions.create(
                model="gpt-4o-mini",  # ggf. auf "gpt-4o" oder dein Wunschmodell ändern
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


# Optionaler Schnelltest: `python -m utils.gpt "zweck-text"`
if __name__ == "__main__":
    import sys
    text = " ".join(sys.argv[1:]) or "DGNB Nachweis"
    print(klassifiziere_verrechenbarkeit(text))
