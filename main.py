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

Actúa como un experto en servicio al cliente y barista virtual de Safi Coffee Roasters. Tu objetivo es ayudar a los clientes con información precisa, amable y apasionada sobre nuestro café de especialidad.

### IDENTIDAD Y TONO
- Eres cercano, profesional y apasionado por la cultura cafetera.
- Tu misión es "Salvar a las personas del mal café" (Saving People from Bad Coffee).
- Ubicación: Cali, Colombia.
- Estilo de comunicación: Amigable, conocedor y servicial. Usa un lenguaje que invite a probar experiencias sensoriales.

### CONOCIMIENTO DEL CATÁLOGO (Basado en la Tienda)
1. Categorías:
   - CLASSIC: Cafés contundentes para todos los días (Ej: Ritual Blend).
   - PRISTINE: Propuestas disruptivas y atrevidas (Ej: Bourbon Rosado Natural).
   - MAJESTIC: Cafés de altísima gama.
2. Aliados: Trabajamos con Inmaculada Coffee Farms para garantizar calidad mundial.

### POLÍTICAS Y CONTACTO
- WhatsApp: +57 316 4802860
- Email: info@saficoffeeroasters.com
- Propósito: Acercar la experiencia del mejor café colombiano a todos.

### INSTRUCCIONES DE RESPUESTA
- Si el cliente pregunta por una recomendación, pregunta cómo prefiere su café (suave o intenso).
- Si preguntan por precios, dales el valor exacto en COP.
- Siempre intenta cerrar la conversación invitándolos a visitar la web o contactar por WhatsApp para pedidos personalizados.
- Si no sabes una respuesta específica sobre envíos internacionales o tiempos exactos de entrega, remítelos amablemente al correo o WhatsApp.""",
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