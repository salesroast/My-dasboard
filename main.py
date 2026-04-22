import os
from groq import Groq

# Esto buscará la llave que pondremos en Render después
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def hablar_con_groq(mensaje):
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": mensaje,
            }
        ],
        model="llama3-8b-8192",
    )
    return chat_completion.choices[0].message.content

print("¡IA de Groq lista!")