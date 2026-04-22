import os
import streamlit as st
from groq import Groq
from dotenv import load_dotenv

load_dotenv()  # Carga el .env solo en local; en Render usa las vars de entorno reales

st.set_page_config(page_title="Mi Dashboard IA", layout="centered")
st.title("🤖 Mi Dashboard con Groq")

api_key = os.environ.get("GROQ_API_KEY")

if not api_key:
    st.error("⚠️ La API Key de Groq no está configurada.")
    st.stop()  # Detiene la app aquí para que el error sea obvio
else:
    client = Groq(api_key=api_key)
    
    mensaje_usuario = st.text_input("Escríbele algo a la Inteligencia Artificial:")
    
    if st.button("Enviar mensaje"):
        with st.spinner("La IA está pensando..."):
            chat_completion = client.chat.completions.create(
                messages=[{"role": "user", "content": mensaje_usuario}],
                model="llama-3.3-70b-versatile",
            )
            st.success(chat_completion.choices[0].message.content)