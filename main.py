import os
import streamlit as st
from groq import Groq
from dotenv import load_dotenv
import requests
import pandas as pd
import plotly.express as px
from datetime import datetime

load_dotenv()

# Credenciales
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
SHOPIFY_SHOP_DOMAIN = os.environ.get("SHOPIFY_SHOP_DOMAIN")
SHOPIFY_ACCESS_TOKEN = os.environ.get("SHOPIFY_ACCESS_TOKEN")

st.set_page_config(page_title="Safi Coffee Roasters", layout="wide", page_icon="☕")
st.title("☕ Safi Coffee Roasters — Dashboard")

if not GROQ_API_KEY:
    st.error("⚠️ GROQ_API_KEY no configurada.")
    st.stop()

client = Groq(api_key=GROQ_API_KEY)

# --- Funciones Shopify ---
@st.cache_data(ttl=300)
def get_shopify_token():
    # Si tienes un token permanente (shpat_...), úsalo directamente.
    return SHOPIFY_ACCESS_TOKEN

@st.cache_data(ttl=3600)
def get_all_orders():
    token = get_shopify_token()
    if not token:
        return []
    headers = {"X-Shopify-Access-Token": token}
    all_orders = []
    url = f"https://{SHOPIFY_SHOP_DOMAIN}/admin/api/2024-01/orders.json?limit=250&status=any"
    while url:
        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            break
        data = r.json().get("orders", [])
        all_orders.extend(data)
        links = r.headers.get("Link", "")
        next_url = None
        for part in links.split(","):
            if 'rel="next"' in part:
                next_url = part.split(";")[0].strip().strip("<>")
        url = next_url
    return all_orders

@st.cache_data(ttl=3600)
def get_products():
    token = get_shopify_token()
    if not token:
        return []
    headers = {"X-Shopify-Access-Token": token}
    url = f"https://{SHOPIFY_SHOP_DOMAIN}/admin/api/2024-01/products.json?limit=250"
    r = requests.get(url, headers=headers)
    return r.json().get("products", []) if r.status_code == 200 else []

# --- Tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["📊 KPIs", "📈 Ventas", "📦 Inventario", "🤖 Asistente IA"])

# ============================================================
# TAB 1 — KPIs
# ============================================================
with tab1:
    st.subheader("Métricas clave")
    orders = get_all_orders()

    if orders:
        df = pd.DataFrame([{
            "fecha": pd.to_datetime(o["created_at"]).tz_localize(None) if pd.to_datetime(o["created_at"]).tzinfo is None else pd.to_datetime(o["created_at"]).tz_convert(None),
            "total": float(o["total_price"]),
            "estado_pago": o["financial_status"],
            "estado_envio": o.get("fulfillment_status") or "pendiente",
            "email": o.get("email", ""),
            "numero": o["order_number"],
        } for o in orders])

        total_ingresos = df["total"].sum()
        total_pedidos = len(df)
        ticket_promedio = df["total"].mean()
        pedidos_pendientes = len(df[df["estado_envio"] == "pendiente"])

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("💰 Ingresos totales", f"${total_ingresos:,.2f}")
        col2.metric("🛒 Total pedidos", f"{total_pedidos:,}")
        col3.metric("🎯 Ticket promedio", f"${ticket_promedio:,.2f}")
        col4.metric("⏳ Pedidos pendientes", f"{pedidos_pendientes:,}")

        st.divider()

        # Pedidos por estado
        col5, col6 = st.columns(2)
        with col5:
            estado_counts = df["estado_pago"].value_counts().reset_index()
            estado_counts.columns = ["Estado", "Cantidad"]
            fig = px.pie(estado_counts, values="Cantidad", names="Estado",
                        title="Pedidos por estado de pago",
                        color_discrete_sequence=px.colors.sequential.Greens)
            st.plotly_chart(fig, use_container_width=True)

        with col6:
            envio_counts = df["estado_envio"].value_counts().reset_index()
            envio_counts.columns = ["Estado", "Cantidad"]
            fig2 = px.pie(envio_counts, values="Cantidad", names="Estado",
                         title="Pedidos por estado de envío",
                         color_discrete_sequence=px.colors.sequential.Blues)
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No se pudieron cargar los pedidos.")

# ============================================================
# TAB 2 — VENTAS
# ============================================================
with tab2:
    st.subheader("Análisis de ventas")
    orders = get_all_orders()

    if orders:
        df = pd.DataFrame([{
            "fecha": pd.to_datetime(o["created_at"]).tz_convert(None),
            "total": float(o["total_price"]),
        } for o in orders])

        df["mes"] = df["fecha"].dt.to_period("M").astype(str)
        df["semana"] = df["fecha"].dt.to_period("W").astype(str)
        df["dia"] = df["fecha"].dt.date

        agrupacion = st.selectbox("Agrupar por:", ["Día", "Semana", "Mes"])

        if agrupacion == "Mes":
            df_grupo = df.groupby("mes")["total"].sum().reset_index()
            df_grupo.columns = ["Período", "Ventas"]
        elif agrupacion == "Semana":
            df_grupo = df.groupby("semana")["total"].sum().reset_index()
            df_grupo.columns = ["Período", "Ventas"]
        else:
            df_grupo = df.groupby("dia")["total"].sum().reset_index()
            df_grupo.columns = ["Período", "Ventas"]

        fig = px.bar(df_grupo, x="Período", y="Ventas",
                    title=f"Ventas por {agrupacion.lower()}",
                    color="Ventas",
                    color_continuous_scale="Greens")
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

        # Línea de tendencia
        df_dia = df.groupby("dia")["total"].sum().reset_index()
        df_dia.columns = ["Fecha", "Ventas"]
        fig2 = px.line(df_dia, x="Fecha", y="Ventas",
                      title="Tendencia de ventas diarias",
                      color_discrete_sequence=["#2e7d32"])
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No se pudieron cargar las ventas.")

# ============================================================
# TAB 3 — INVENTARIO
# ============================================================
with tab3:
    st.subheader("Productos e Inventario")
    products = get_products()

    if products:
        filas = []
        for p in products:
            for v in p["variants"]:
                filas.append({
                    "Producto": p["title"],
                    "Variante": v["title"],
                    "Precio": float(v["price"]),
                    "Stock": v.get("inventory_quantity", 0),
                    "SKU": v.get("sku", "—"),
                })

        df_prod = pd.DataFrame(filas)

        # Alerta stock bajo
        stock_bajo = df_prod[df_prod["Stock"] <= 5]
        if not stock_bajo.empty:
            st.warning(f"⚠️ {len(stock_bajo)} variante(s) con stock bajo (≤ 5 unidades)")
            st.dataframe(stock_bajo, use_container_width=True)
            st.divider()

        # Tabla completa
        st.dataframe(
            df_prod.sort_values("Stock"),
            use_container_width=True,
            column_config={
                "Precio": st.column_config.NumberColumn("Precio", format="$%.2f"),
                "Stock": st.column_config.NumberColumn("Stock", format="%d"),
            }
        )

        # Gráfica top productos por precio
        fig = px.bar(df_prod.sort_values("Precio", ascending=False).head(15),
                    x="Variante", y="Precio",
                    title="Top productos por precio",
                    color="Precio",
                    color_continuous_scale="Greens")
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No se pudieron cargar los productos.")

# ============================================================
# TAB 4 — ASISTENTE IA
# ============================================================
with tab4:
    st.subheader("Asistente Virtual")
    with st.expander("⚙️ Configurar personalidad del asistente", expanded=False):
        system_prompt = st.text_area(
            "System Prompt:",
            value="""Eres el asistente virtual oficial de Safi Coffee Roasters / Inmaculada Coffee Farms.
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

    mensaje_usuario = st.chat_input("Escribe un mensaje como cliente de Instagram...")

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