import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

def klassifiziere_verrechenbarkeit(zweck: str) -> str:
    prompt = (
        "Entscheide, ob folgender Arbeitszweck extern an den Kunden verrechenbar ist "
        "oder intern durchgeführt wird. Antworte mit genau 'Extern' oder 'Intern'.\n\n"
        f"Zweck: {zweck}"
    )

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Du bist ein professioneller Buchhaltungsassistent."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1
    )
    return response.choices[0].message.content.strip()


