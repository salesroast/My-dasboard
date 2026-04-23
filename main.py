import os
import streamlit as st
from groq import Groq
from dotenv import load_dotenv
import requests

load_dotenv()

# Credenciales
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
SHOPIFY_SHOP_DOMAIN = os.environ.get("SHOPIFY_SHOP_DOMAIN")
SHOPIFY_CLIENT_ID = os.environ.get("SHOPIFY_CLIENT_ID")
SHOPIFY_CLIENT_SECRET = os.environ.get("SHOPIFY_CLIENT_SECRET")

st.set_page_config(page_title="Safi Coffee Roasters", layout="wide")
st.title("☕ Safi Coffee Roasters — Dashboard")

if not GROQ_API_KEY:
    st.error("⚠️ GROQ_API_KEY no configurada.")
    st.stop()

client = Groq(api_key=GROQ_API_KEY)

# --- Funciones Shopify ---
@st.cache_data(ttl=300)
def get_shopify_token():
    url = f"https://{SHOPIFY_SHOP_DOMAIN}/admin/oauth/access_token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": SHOPIFY_CLIENT_ID,
        "client_secret": SHOPIFY_CLIENT_SECRET,
    }
    r = requests.post(url, data=payload)
    if r.status_code == 200:
        return r.json().get("access_token")
    return None

@st.cache_data(ttl=300)
def get_products():
    token = get_shopify_token()
    if not token:
        return []
    url = f"https://{SHOPIFY_SHOP_DOMAIN}/admin/api/2024-01/products.json?limit=50"
    r = requests.get(url, headers={"X-Shopify-Access-Token": token})
    return r.json().get("products", []) if r.status_code == 200 else []

@st.cache_data(ttl=300)
def get_orders():
    token = get_shopify_token()
    if not token:
        return []
    url = f"https://{SHOPIFY_SHOP_DOMAIN}/admin/api/2024-01/orders.json?limit=50&status=any"
    r = requests.get(url, headers={"X-Shopify-Access-Token": token})
    return r.json().get("orders", []) if r.status_code == 200 else []

# --- Tabs del dashboard ---
tab1, tab2, tab3 = st.tabs(["📦 Inventario", "🛒 Pedidos", "🤖 Asistente IA"])

with tab1:
    st.subheader("Productos e Inventario")
    if not SHOPIFY_SHOP_DOMAIN:
        st.warning("Shopify no configurado.")
    else:
        products = get_products()
        if products:
            for p in products:
                with st.expander(f"{p['title']} — {len(p['variants'])} variantes"):
                    for v in p["variants"]:
                        st.write(f"• {v['title']} | Precio: ${v['price']} | Stock: {v.get('inventory_quantity', 'N/A')}")
        else:
            st.info("No se pudieron cargar productos. Verifica la conexión con Shopify.")

with tab2:
    st.subheader("Pedidos Recientes")
    if not SHOPIFY_SHOP_DOMAIN:
        st.warning("Shopify no configurado.")
    else:
        orders = get_orders()
        if orders:
            total_ventas = sum(float(o["total_price"]) for o in orders)
            st.metric("Total ventas (últimos 50 pedidos)", f"${total_ventas:,.2f}")
            for o in orders[:10]:
                st.write(f"• #{o['order_number']} | {o['email']} | ${o['total_price']} | {o['financial_status']}")
        else:
            st.info("No se pudieron cargar pedidos. Verifica la conexión con Shopify.")

with tab3:
    st.subheader("Asistente Virtual")
    with st.expander("⚙️ Configurar personalidad del asistente", expanded=False):
        system_prompt = st.text_area(
            "System Prompt:",
            value="""Eres el asistente virtual oficial de Inmaculada Coffee Farms / Safi Coffee Roasters.
Respondes mensajes de clientes de Instagram de forma amable, profesional y concisa.

PRODUCTOS: Café de especialidad en grano entero y molido. Exportamos internacionalmente.
[AGREGA: precios, tamaños, link tienda, WhatsApp]

PREGUNTAS FRECUENTES:
[AGREGA tus 3 preguntas más comunes]

TONO: Cálido, apasionado por el café. Máximo 3-4 oraciones. Responde en el idioma del cliente.""",
            height=250,
        )

    if "mensajes" not in st.session_state:
        st.session_state.mensajes = []

    for msg in st.session_state.mensajes:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    mensaje_usuario = st.chat_input("Escribe un mensaje como cliente...")

    if mensaje_usuario:
        st.session_state.mensajes.append({"role": "user", "content": mensaje_usuario})
        with st.chat_message("user"):
            st.write(mensaje_usuario)
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
        st.session_state.mensajes.append({"role": "assistant", "content": contenido})

    if st.session_state.mensajes:
        if st.button("🗑️ Limpiar conversación"):
            st.session_state.mensajes = []
            st.rerun()