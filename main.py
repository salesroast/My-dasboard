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

st.set_page_config(page_title="Safi AI Sales", layout="centered")
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
# BUILD CONTEXT + MAP
# ==============================
def build_context(products):
    context = []
    sku_map = {}

    for p in products:
        handle = p.get("handle")

        for v in p["variants"]:
            stock = v.get("inventory_quantity", 0)

            if stock <= 0:
                continue

            sku = v.get("sku")
            variant_id = v.get("id")

            context.append(
                f"{p['title']} - {v['title']} | ${v['price']} | Stock:{stock} | SKU:{sku}"
            )

            if sku:
                sku_map[sku] = {
                    "variant_id": variant_id,
                    "handle": handle
                }

    return "\n".join(context[:25]), sku_map


products = get_products()
product_context, sku_map = build_context(products)

# ==============================
# IA PROMPT
# ==============================
system_prompt = f"""
Eres asesor de ventas de Safi Coffee.

Vendes café disponible.

REGLAS:
- Máx 3 líneas
- Siempre cerrar venta
- Recomendar máx 2 productos
- Usar SKU en respuesta si cliente quiere comprar

PRODUCTOS:
{product_context}
"""

# ==============================
# SESSION STATE
# ==============================
if "chat" not in st.session_state:
    st.session_state.chat = []

if "checkout" not in st.session_state:
    st.session_state.checkout = {
        "step": "idle",
        "data": {},
        "cart": []
    }

# ==============================
# INTENT
# ==============================
def detect_intent(text):
    keywords = ["quiero", "comprar", "dame", "llevar"]
    return any(k in text.lower() for k in keywords)

# ==============================
# SHOPIFY FUNCTIONS
# ==============================
def create_customer(data):
    url = f"https://{SHOPIFY_SHOP_DOMAIN}/admin/api/2024-01/customers.json"
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    payload = {
        "customer": {
            "first_name": data["nombre"].split()[0],
            "last_name": " ".join(data["nombre"].split()[1:]),
            "email": data["email"],
            "phone": data["telefono"],
            "note": f"ID: {data['id']}",
            "addresses": [{"address1": data["direccion"]}]
        }
    }

    r = requests.post(url, json=payload, headers=headers)
    return r.json()


def create_draft_order(customer_id, cart):
    url = f"https://{SHOPIFY_SHOP_DOMAIN}/admin/api/2024-01/draft_orders.json"

    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }

    payload = {
        "draft_order": {
            "line_items": cart,
            "customer": {"id": customer_id},
            "use_customer_default_address": True
        }
    }

    r = requests.post(url, json=payload, headers=headers)
    return r.json()

# ==============================
# CHAT UI
# ==============================
for msg in st.session_state.chat:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

user_input = st.chat_input("Escribe como cliente...")

if user_input:
    st.session_state.chat.append({"role": "user", "content": user_input})
    checkout = st.session_state.checkout

    # ==============================
    # CHECKOUT FLOW
    # ==============================
    if detect_intent(user_input) and checkout["step"] == "idle":
        checkout["step"] = "ask_name"
        st.session_state.chat.append({
            "role": "assistant",
            "content": "Perfecto 🙌 Para crear tu pedido, ¿me confirmas tu nombre completo?"
        })
        st.rerun()

    elif checkout["step"] == "ask_name":
        checkout["data"]["nombre"] = user_input
        checkout["step"] = "ask_id"
        st.session_state.chat.append({"role": "assistant", "content": "Número de identificación:"})
        st.rerun()

    elif checkout["step"] == "ask_id":
        checkout["data"]["id"] = user_input
        checkout["step"] = "ask_email"
        st.session_state.chat.append({"role": "assistant", "content": "Correo electrónico:"})
        st.rerun()

    elif checkout["step"] == "ask_email":
        checkout["data"]["email"] = user_input
        checkout["step"] = "ask_phone"
        st.session_state.chat.append({"role": "assistant", "content": "Teléfono:"})
        st.rerun()

    elif checkout["step"] == "ask_phone":
        checkout["data"]["telefono"] = user_input
        checkout["step"] = "ask_address"
        st.session_state.chat.append({"role": "assistant", "content": "Dirección:"})
        st.rerun()

    elif checkout["step"] == "ask_address":
        checkout["data"]["direccion"] = user_input
        checkout["step"] = "create_order"

    # ==============================
    # CREATE ORDER
    # ==============================
    if checkout["step"] == "create_order":
        customer = create_customer(checkout["data"])
        customer_id = customer["customer"]["id"]

        order = create_draft_order(customer_id, checkout["cart"])
        invoice_url = order["draft_order"]["invoice_url"]

        st.session_state.chat.append({
            "role": "assistant",
            "content": f"Perfecto 🙌 Aquí puedes completar tu pago:\n{invoice_url}"
        })

        st.session_state.checkout = {"step": "idle", "data": {}, "cart": []}
        st.rerun()

    # ==============================
    # IA RESPONSE (NORMAL CHAT)
    # ==============================
    else:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                *st.session_state.chat
            ]
        )

        reply = response.choices[0].message.content

        # Detectar SKU en respuesta y agregar carrito
        for sku, data in sku_map.items():
            if sku and sku in reply:
                checkout["cart"].append({
                    "variant_id": data["variant_id"],
                    "quantity": 1
                })
                reply += f"\n👉 Agregado al carrito"
                break

        st.session_state.chat.append({"role": "assistant", "content": reply})

# ==============================
# RESET
# ==============================
if st.button("Reset"):
    st.session_state.chat = []
    st.session_state.checkout = {"step": "idle", "data": {}, "cart": []}
    st.rerun()