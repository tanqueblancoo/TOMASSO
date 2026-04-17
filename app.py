import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import uuid
import urllib.parse

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Pedidos para Lucas!", layout="centered")

# --- 2. ESTILO "VIEJAS" ---
st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 20px !important; }
    .stButton>button { width: 100%; height: 3em; font-size: 22px !important; font-weight: bold; border-radius: 10px; background-color: #FF4B4B; color: white; }
    .stTabs [data-baseweb="tab"] { font-size: 18px !important; font-weight: bold; }
    input { font-size: 20px !important; }
    </style>
    """, unsafe_allow_stdio=True)

# --- 3. CONEXIÓN ---
try:
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open("TOMASSO")
    sheet_ventas = spreadsheet.worksheet("VENTAS")
    sheet_stock = spreadsheet.worksheet("STOCK")
    sheet_pendientes = spreadsheet.worksheet("PENDIENTES")
except Exception as e:
    st.error(f"Error Crítico: {e}")

# --- 4. DATOS ---
PIZZAS = {
    "Muzzarella": {"precio": 8000, "margen": 2000},
    "Fugazzeta": {"precio": 8500, "margen": 2050},
    "Jamon": {"precio": 9000, "margen": 2100},
    "De Autor": {"precio": 9500, "margen": 2100},
    "Pepperoni": {"precio": 10000, "margen": 2000},
    "Napolitana": {"precio": 7500, "margen": 1800},
}
EMPANADAS_SABORES = ["Carne", "JyQ", "QyC", "Pollo", "Humita", "Verdura", "Roquefort", "Cheeseburger", "Bondiola BBQ", "Capresse"]
CRUDDA_SABORES = ["Brownie", "Peanut Caramel", "Arandanos y Nuez", "Coco y Chocolate", "Avellana y Chocolate", "Banana Toffee"]
VOLCANES = {"Volkano Chocolate": 3500, "Volcano Dulce de Leche": 3500}

def obtener_stock_dict():
    try:
        data = sheet_stock.get_all_records()
        return {str(item.get('PRODUCTO', '')).strip(): int(item.get('CANTIDAD', 0)) for item in data if item.get('PRODUCTO')}
    except: return {}

# --- 5. INTERFAZ ---
if 'carrito' not in st.session_state: st.session_state.carrito = []

modo = st.sidebar.radio("Ir a:", ["Tienda", "Admin"])

if modo == "Tienda":
    st.title("🍕 ¡Pedidos para Lucas!")
    stock_actual = obtener_stock_dict()
    t = st.tabs(["🍕 Pizzas", "🥟 Empas", "🍫 Crudda", "🍰 Postres"])
    
    with t[0]:
        piz = st.selectbox("Elegí Pizza", list(PIZZAS.keys()))
        n_piz = f"Pizza {piz}"
        disp = stock_actual.get(n_piz, 0)
        c_p = st.number_input(f"Cantidad ({disp} disp.)", 0, disp, step=1, key="p_c")
        if st.button("Sumar Pizza 🛒") and c_p > 0:
            st.session_state.carrito.append({"Cat": "Pizzas", "Prod": n_piz, "Cant": c_p, "Sub": PIZZAS[piz]["precio"]*c_p, "Prof": PIZZAS[piz]["margen"]*c_p})
            st.rerun()

    with t[1]:
        emp = st.selectbox("Sabor Empanada", EMPANADAS_SABORES)
        n_emp = f"Empanada {emp}"
        disp_e = stock_actual.get(n_emp, 0)
        op_e = [i for i in range(0, disp_e + 1, 4)]
        c_e = st.select_slider(f"Unidades {emp}", options=op_e, value=0)
        if st.button("Sumar Empas 🛒") and c_e > 0:
            st.session_state.carrito.append({"Cat": "Empanadas", "Prod": n_emp, "Cant": c_e, "Sub": 1625*c_e, "Prof": 375*c_e})
            st.rerun()

    with t[2]:
        bar = st.selectbox("Sabor Barrita", CRUDDA_SABORES)
        n_bar = f"Crudda {bar}"
        disp_b = stock_actual.get(n_bar, 0)
        c_b = st.number_input(f"Cantidad ({disp_b} disp.)", 0, disp_b, step=1, key="b_c")
        if st.button("Sumar Barrita 🛒") and c_b > 0:
            st.session_state.carrito.append({"Cat": "Barritas", "Prod": n_bar, "Cant": c_b, "Sub": 2200*c_b, "Prof": 868*c_b})
            st.rerun()

    with t[3]:
        vol = st.selectbox("Sabor Volcán", list(VOLCANES.keys()))
        disp_v = stock_actual.get(vol, 0)
        c_v = st.number_input(f"Cantidad ({disp_v} disp.)", 0, disp_v, step=1, key="v_c")
        if st.button("Sumar Volcán 🛒") and c_v > 0:
            st.session_state.carrito.append({"Cat": "Volcanes", "Prod": vol, "Cant": c_v, "Sub": 3500*c_v, "Prof": 1200*c_v})
            st.rerun()

    if st.session_state.carrito:
        df = pd.DataFrame(st.session_state.carrito)
        total_bar = df[df["Cat"] == "Barritas"]["Cant"].sum() if "Cat" in df.columns else 0
        desc = (total_bar // 10) * 3000
        total_f = df["Sub"].sum() - desc
        
        st.table(df[["Prod", "Cant", "Sub"]])
        st.header(f"Total: ${total_f:,.0f}")

        with st.form("datos"):
            nom = st.text_input("Nombre")
            tel = st.text_input("WhatsApp")
            lot = st.text_input("Lote / Casa")
            urg = st.text_input("¿Cuándo?")
            if st.form_submit_button("FINALIZAR"):
                if nom and tel and lot:
                    ped = "; ".join([f"{x['Cant']}x {x['Prod']}|{x['Sub']}|{x['Prof']}" for x in st.session_state.carrito])
                    p_neto = df["Prof"].sum() - desc
                    fila = [str(uuid.uuid4())[:8], datetime.now().strftime("%Y-%m-%d %H:%M"), nom, tel, "Otro", lot, urg, ped, float(total_f), float(p_neto)]
                    sheet_pendientes.append_row(fila)
                    msg = urllib.parse.quote(f"Lucas! Pedido de {nom}:\n{ped.replace('|', ' -$')}\nTotal: ${total_f}")
                    st.success("✅ Enviado!")
                    st.markdown(f'<a href="https://wa.me/5491130501255?text={msg}" target="_blank"><button style="width:100%; background-color:#25D366; color:white; border:none; padding:15px; border-radius:10px; font-size:20px;">🟢 AVISAR POR WHATSAPP</button></a>', unsafe_allow_stdio=True)
                    st.session_state.carrito = []
                else: st.warning("Faltan datos")

else: # --- ADMIN ---
    clave = st.text_input("Clave", type="password")
    if clave == "lucas2026":
        st.title("👑 Panel")
        try:
            data = pd.DataFrame(sheet_pendientes.get_all_records())
            if not data.empty:
                for i, row in data.iterrows():
                    cliente = row.get('CLIENTE', 'N/A')
                    urgencia = row.get('URGENCIA', 'N/A')
                    with st.expander(f"Pedido: {cliente} ({urgencia})"):
                        st.write(f"Detalle: {row.get('PEDIDO', '')}")
                        c1, c2 = st.columns(2)
                        if c1.button("✅ OK", key=f"a_{i}"):
                            # Lógica simplificada para evitar errores de parseo
                            sheet_ventas.append_row([row.get('FECHA',''), "Otro", row.get('PEDIDO',''), 1, row.get('TOTAL',0), row.get('PROFIT',0)])
                            sheet_pendientes.delete_rows(i + 2)
                            st.rerun()
                        if c2.button("❌ NO", key=f"r_{i}"):
                            sheet_pendientes.delete_rows(i + 2)
                            st.rerun()
            else: st.info("Nada pendiente")
        except: st.error("Error leyendo Pendientes. Borrá filas vacías en el Sheets.")
