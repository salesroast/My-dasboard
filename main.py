import os
import streamlit as st
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="SAFI - Asistente", layout="centered")
st.title("☕ Asistente SAFI")

api_key = os.environ.get("GROQ_API_KEY")

if not api_key:
    st.error("⚠️ La API Key de Groq no está configurada.")
    st.stop()

client = Groq(api_key=api_key)

# --- System prompt editable desde el dashboard ---
with st.expander("⚙️ Configurar personalidad del asistente", expanded=False):
    system_prompt = st.text_area(
        "System Prompt (instrucciones para la IA):",
        value="""Eres el asistente virtual oficial de Safi Coffee Roasters, 
una tostadora de cafe de especialidad en cali, Colombia. Tu trabajo es responder 
mensajes de clientes por Instagram de forma amable, profesional y concisa siempre con el objetivo de vender.

INFORMACIÓN DEL NEGOCIO:
- Vendemos café de especialidad en grano entero y molido
- Exportamos a nivel internacional y vendemos en Colombia
- [AGREGA AQUÍ: precios, tamaños, link de tienda, WhatsApp de pedidos]

PREGUNTAS FRECUENTES:
- [AGREGA AQUÍ tus 3 preguntas más comunes y sus respuestas]

TONO: Cálido, profesional y apasionado por el café.
Responde siempre en el mismo idioma en que te escriban.
Sé breve — máximo 3-4 oraciones por respuesta.""",
        height=300,
    )

st.divider()

# --- Historial de conversación ---
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

# Mostrar historial
for msg in st.session_state.mensajes:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Input del usuario
mensaje_usuario = st.chat_input("Escribe un mensaje como si fueras un cliente de Instagram...")

if mensaje_usuario:
    # Agregar mensaje del usuario al historial
    st.session_state.mensajes.append({"role": "user", "content": mensaje_usuario})
    with st.chat_message("user"):
        st.write(mensaje_usuario)

    # Llamar a Groq con el system prompt
    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            respuesta = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    *st.session_state.mensajes
                ],
                model="llama-3.3-70b-versatile",
            )
            contenido = respuesta.choices[0].message.content
            st.write(contenido)

    # Guardar respuesta en historial
    st.session_state.mensajes.append({"role": "assistant", "content": contenido})

# Botón para limpiar conversación
if st.session_state.mensajes:
    if st.button("🗑️ Limpiar conversación"):
        st.session_state.mensajes = []
        st.rerun()