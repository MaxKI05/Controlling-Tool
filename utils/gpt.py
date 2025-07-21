import openai
import os

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def klassifiziere_verrechenbarkeit(zweck: str) -> str:
    prompt = (
        "Entscheide, ob folgender Arbeitszweck extern an den Kunden verrechenbar ist "
        "oder intern durchgeführt wird. Antworte mit genau 'Extern' oder 'Intern'.\n\n"
        f"Zweck: {zweck}"
    )

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Du bist ein professioneller Buchhaltungsassistent."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1
    )
    return response.choices[0].message.content.strip()
