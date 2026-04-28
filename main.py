import os
import streamlit as st
from groq import Groq
from dotenv import load_dotenv
import requests
import pandas as pd
import plotly.express as px

load_dotenv()

# ==============================
# CONFIG
# ==============================
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
SHOPIFY_SHOP_DOMAIN = os.environ.get("SHOPIFY_SHOP_DOMAIN")
SHOPIFY_ACCESS_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN")

st.set_page_config(page_title="Safi Coffee Roasters", layout="wide", page_icon="☕")
st.title("☕ SAFI — Dashboard & AI Sales Agent")

client = Groq(api_key=GROQ_API_KEY)

# ==============================
# SHOPIFY FUNCTIONS
# ==============================
@st.cache_data(ttl=300)
def get_all_orders():
    headers = {"X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN}
    url = f"https://{SHOPIFY_SHOP_DOMAIN}/admin/api/2024-01/orders.json?limit=250&status=any"
    orders = []

    while url:
        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            break

        data = r.json().get("orders", [])
        orders.extend(data)

        links = r.headers.get("Link", "")
        next_url = None
        for part in links.split(","):
            if 'rel="next"' in part:
                next_url = part.split(";")[0].strip().strip("<>")
        url = next_url

    return orders


@st.cache_data(ttl=300)
def get_products():
    headers = {"X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN}
    url = f"https://{SHOPIFY_SHOP_DOMAIN}/admin/api/2024-01/products.json?limit=250"
    r = requests.get(url, headers=headers)
    return r.json().get("products", []) if r.status_code == 200 else []


# ==============================
# PREPARAR CONTEXTO PARA IA
# ==============================
def build_product_context(products):
    context = []
    for p in products:
        for v in p["variants"]:
            if v.get("inventory_quantity", 0) > 0:
                context.append(
                    f"{p['title']} - {v['title']} | ${v['price']} | Stock: {v['inventory_quantity']} | SKU: {v.get('sku','')}"
                )
    return "\n".join(context[:20])  # limitamos para performance


def generate_product_links(products):
    links = {}
    for p in products:
        handle = p.get("handle")
        for v in p["variants"]:
            sku = v.get("sku")
            if sku:
                links[sku] = f"https://{SHOPIFY_SHOP_DOMAIN}/products/{handle}"
    return links


# ==============================
# TABS
# ==============================
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 KPIs",
    "📈 Ventas",
    "📦 Inventario",
    "🤖 Vendedor IA"
])

# ==============================
# TAB 1 — KPIs
# ==============================
with tab1:
    orders = get_all_orders()

    if orders:
        df = pd.DataFrame([{
            "fecha": pd.to_datetime(o["created_at"]).tz_convert(None),
            "total": float(o["total_price"]),
        } for o in orders])

        col1, col2, col3 = st.columns(3)
        col1.metric("💰 Ingresos", f"${df['total'].sum():,.0f}")
        col2.metric("🛒 Pedidos", len(df))
        col3.metric("🎯 Ticket Promedio", f"${df['total'].mean():,.0f}")

# ==============================
# TAB 2 — VENTAS
# ==============================
with tab2:
    orders = get_all_orders()

    if orders:
        df = pd.DataFrame([{
            "fecha": pd.to_datetime(o["created_at"]).tz_convert(None),
            "total": float(o["total_price"]),
        } for o in orders])

        df["dia"] = df["fecha"].dt.date
        df_group = df.groupby("dia")["total"].sum().reset_index()

        fig = px.line(df_group, x="dia", y="total", title="Ventas diarias")
        st.plotly_chart(fig, use_container_width=True)

# ==============================
# TAB 3 — INVENTARIO
# ==============================
with tab3:
    products = get_products()

    filas = []
    for p in products:
        for v in p["variants"]:
            filas.append({
                "Producto": p["title"],
                "Variante": v["title"],
                "Precio": float(v["price"]),
                "Stock": v.get("inventory_quantity", 0),
                "SKU": v.get("sku", "")
            })

    df = pd.DataFrame(filas)
    st.dataframe(df.sort_values("Stock"))

# ==============================
# TAB 4 — IA VENDEDOR
# ==============================
with tab4:
    st.subheader("🤖 Asesor Comercial IA")

    products = get_products()
    product_context = build_product_context(products)
    product_links = generate_product_links(products)

    # PROMPT PRO
    system_prompt = f"""
Eres el asesor comercial de Safi Coffee Roasters.

OBJETIVO: vender y cerrar pedidos.

Reglas:
- Respuestas cortas (máx 3 líneas)
- Siempre hacer pregunta para cerrar venta
- Recomendar máximo 2 productos
- Usar info real de productos

Productos disponibles:
{product_context}

Flujo:
1. Preguntar necesidad
2. Recomendar
3. Cerrar con acción (link o cantidad)

Si cliente quiere comprar:
- Usa SKU para dar link
"""

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
            with st.spinner("Vendiendo..."):
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        *st.session_state.chat
                    ]
                )

                reply = response.choices[0].message.content

                # 🔥 INYECTAR LINK AUTOMÁTICO
                for sku, link in product_links.items():
                    if sku in reply:
                        reply += f"\n👉 Compra aquí: {link}"
                        break

                st.write(reply)

        st.session_state.chat.append({"role": "assistant", "content": reply})

    if st.button("🗑️ Limpiar chat"):
        st.session_state.chat = []
        st.rerun()