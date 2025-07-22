from openai import OpenAI

client = OpenAI()

def klassifiziere_verrechenbarkeit(zweck: str) -> str:
    prompt = f"""
Der folgende Zweck stammt aus einer Zeitbuchung eines Ingenieurbüros für Nachhaltigkeitsberatung.

Bitte klassifiziere diesen Zweck als:
- **Extern**, wenn es sich um eine Leistung handelt, die im Rahmen eines Projekts für Kunden erbracht wird (z. B. Berechnung, Einreichung, DGNB, LCA, LCC, Zertifizierung, Planung, Ausarbeitung, Audit, Ausführung).
- **Intern**, wenn es sich um eine Tätigkeit handelt, von der primär die Firma selbst profitiert (z. B. Akquise, Besprechung, interne Entwicklung, Verwaltung, Personal, Meetings ohne Kundenbezug).

**Wenn der Zweck nicht explizit auf eine interne Firmenleistung hinweist, sondern nach projektbezogener Leistung aussieht, wähle "Extern".**

Zweck: "{zweck}"

Antworte **nur mit einem einzigen Wort**: `Intern` oder `Extern`.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Du bist ein Klassifizierungs-Experte für Zeitdaten."},
                {"role": "user", "content": prompt.strip()}
            ],
            temperature=0.1,
        )
        return response.choices[0].message.content.strip().capitalize()
    except Exception as e:
        return "Unbekannt"
