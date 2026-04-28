import os
import streamlit as st
from groq import Groq
from dotenv import load_dotenv
import requests

load_dotenv()

# ==============================
# CONFIG
# ==============================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
SHOPIFY_SHOP_DOMAIN = os.environ.get("SHOPIFY_SHOP_DOMAIN")
SHOPIFY_ACCESS_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN")

st.set_page_config(page_title="Safi AI Sales", layout="centered", page_icon="☕")
st.title("☕ Safi Coffee — Asesor de Ventas")

client = Groq(api_key=GROQ_API_KEY)

# ==============================
# SHOPIFY
# ==============================
@st.cache_data(ttl=300)
def get_products():
    headers = {"X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN}
    url = f"https://{SHOPIFY_SHOP_DOMAIN}/admin/api/2024-01/products.json?limit=250"
    r = requests.get(url, headers=headers)
    return r.json().get("products", []) if r.status_code == 200 else []

# ==============================
# FILTRAR SOLO STOCK DISPONIBLE
# ==============================
def build_product_context(products):
    context = []
    links = {}

    for p in products:
        handle = p.get("handle")

        for v in p["variants"]:
            stock = v.get("inventory_quantity", 0)

            # 🔥 SOLO STOCK POSITIVO
            if stock <= 0:
                continue

            sku = v.get("sku", "")
            price = v.get("price")

            texto = f"{p['title']} - {v['title']} | ${price} | Stock: {stock} | SKU: {sku}"
            context.append(texto)

            if sku:
                links[sku] = f"https://{SHOPIFY_SHOP_DOMAIN}/products/{handle}"

    return "\n".join(context[:25]), links


# ==============================
# UI
# ==============================
products = get_products()
product_context, product_links = build_product_context(products)

# ==============================
# PROMPT VENDEDOR PRO
# ==============================
system_prompt = f"""
Eres el asesor comercial de Safi Coffee Roasters.

OBJETIVO: vender café y cerrar pedidos.

REGLAS:
- Solo puedes vender productos disponibles en inventario
- Respuestas cortas (máx 3 líneas)
- Siempre hacer pregunta para cerrar venta
- Recomendar máximo 2 productos
- No inventar productos

PRODUCTOS DISPONIBLES:
{product_context}

FLUJO:
1. Identificar necesidad
2. Recomendar (máx 2)
3. Cerrar con acción

CIERRE:
- "¿Cuántas bolsas quieres?"
- "Te paso el link para comprar 👇"
"""

# ==============================
# CHAT
# ==============================
if "chat" not in st.session_state:
    st.session_state.chat = []

for msg in st.session_state.chat:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

user_input = st.chat_input("Escribe como cliente...")

if user_input:
    st.session_state.chat.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.write(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Asesorando..."):

            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    *st.session_state.chat
                ]
            )

            reply = response.choices[0].message.content

            # 🔥 INSERTAR LINK AUTOMÁTICO
            for sku, link in product_links.items():
                if sku and sku in reply:
                    reply += f"\n👉 Compra aquí: {link}"
                    break

            st.write(reply)

    st.session_state.chat.append({"role": "assistant", "content": reply})

# ==============================
# RESET
# ==============================
if st.button("🗑️ Limpiar conversación"):
    st.session_state.chat = []
    st.rerun()