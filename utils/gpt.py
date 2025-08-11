# utils/gpt.py
import os
import time
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

SYSTEM_MSG = "Du bist ein Klassifizierungs-Experte für Zeitdaten."

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
                model="gpt-4o-mini",  # ggf. auf "gpt-4o" umstellen
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

if __name__ == "__main__":
    import sys
    text = " ".join(sys.argv[1:]) or "DGNB Nachweis"
    print(klassifiziere_verrechenbarkeit(text))
