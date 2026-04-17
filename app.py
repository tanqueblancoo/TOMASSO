import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import uuid  # <--- ESTA ERA LA QUE FALTABA Y CAUSABA EL ERROR
import urllib.parse

# --- 1. CONFIGURACIÓN (SIEMPRE PRIMERO) ---
st.set_page_config(page_title="Pedidos para Lucas!", layout="centered")

# --- 2. ESTILO "VIEJAS" MEJORADO ---
st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 20px !important; }
    .stButton>button { 
        width: 100%; 
        height: 3em; 
        font-size: 22px !important; 
        font-weight: bold; 
        border-radius: 10px;
        background-color: #FF4B4B;
        color: white;
    }
    .stTabs [data-baseweb="tab"] { font-size: 20px !important; font-weight: bold; }
    input { font-size: 20px !important; }
    .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
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
    st.error(f"Error de conexión: {e}")

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
VOLCANES = {"Volkano Chocolate": 3500, "Volcano Dulce de Leche": 3500} # Nombres exactos de tu stock

def obtener_stock_dict():
    data = sheet_stock.get_all_records()
    return {str(item['PRODUCTO']).strip(): int(item['CANTIDAD']) for item in data}

# --- 5. LÓGICA DE INTERFAZ ---
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

modo = st.sidebar.radio("Navegación:", ["Tienda", "Admin"])

if modo == "Tienda":
    st.title("🍕 ¡Pedidos para Lucas!")
    st.info("Agregá tus productos y completá los datos abajo.")
    
    stock_actual = obtener_stock_dict()
    t = st.tabs(["🍕 Pizzas", "🥟 Empanadas", "🍫 Barritas", "🍰 Volcanes"])
    
    with t[0]:
        piz = st.selectbox("Sabor de Pizza", list(PIZZAS.keys()))
        n_piz = f"Pizza {piz}"
        disp = stock_actual.get(n_piz, 0)
        c_p = st.number_input(f"¿Cuántas? (Stock: {disp})", 0, disp, step=1, key="p_c")
        if st.button("Sumar Pizza 🛒") and c_p > 0:
            st.session_state.carrito.append({"Cat": "Pizzas", "Prod": n_piz, "Cant": c_p, "Sub": PIZZAS[piz]["precio"]*c_p, "Prof": PIZZAS[piz]["margen"]*c_p})
            st.rerun()

    with t[1]:
        emp = st.selectbox("Sabor Empanada", EMPANADAS_SABORES)
        n_emp = f"Empanada {emp}"
        disp_e = stock_actual.get(n_emp, 0)
        opciones_e = [i for i in range(0, disp_e + 1, 4)]
        c_e = st.select_slider(f"Unidades de {emp} (Pack x4)", options=opciones_e, value=0)
        if st.button("Sumar Empanadas 🛒") and c_e > 0:
            st.session_state.carrito.append({"Cat": "Empanadas", "Prod": n_emp, "Cant": c_e, "Sub": 1625*c_e, "Prof": 375*c_e})
            st.rerun()

    with t[2]:
        bar = st.selectbox("Sabor Barrita", CRUDDA_SABORES)
        n_bar = f"Crudda {bar}"
        disp_b = stock_actual.get(n_bar, 0)
        c_b = st.number_input(f"¿Cuántas? (Stock: {disp_b})", 0, disp_b, step=1, key="b_c")
        if st.button("Sumar Barrita 🛒") and c_b > 0:
            st.session_state.carrito.append({"Cat": "Barritas", "Prod": n_bar, "Cant": c_b, "Sub": 2200*c_b, "Prof": 868*c_b})
            st.rerun()

    with t[3]:
        vol = st.selectbox("Sabor Volcán", list(VOLCANES.keys()))
        disp_v = stock_actual.get(vol, 0)
        c_v = st.number_input(f"¿Cuántos? (Stock: {disp_v})", 0, disp_v, step=1, key="v_c")
        if st.button("Sumar Volcán 🛒") and c_v > 0:
            st.session_state.carrito.append({"Cat": "Volcanes", "Prod": vol, "Cant": c_v, "Sub": 3500*c_v, "Prof": 1200*c_v})
            st.rerun()

    if st.session_state.carrito:
        st.divider()
        st.subheader("📋 Tu Carrito")
        df_c = pd.DataFrame(st.session_state.carrito)
        
        # Descuento 10 barritas surtidas
        t_bar = df_c[df_c["Cat"] == "Barritas"]["Cant"].sum()
        desc = (t_bar // 10) * 3000
        
        st.table(df_c[["Prod", "Cant", "Sub"]])
        if desc > 0: st.success(f"✅ ¡Descuento Pack x10 aplicado: -${desc}!")
        
        total_f = df_c["Sub"].sum() - desc
        st.metric("TOTAL A PAGAR", f"${total_f:,.0f}")

        if st.button("🗑️ Vaciar Carrito"):
            st.session_state.carrito = []
            st.rerun()

        with st.form("datos"):
            nom = st.text_input("Nombre y Apellido")
            tel = st.text_input("WhatsApp (Ej: 1122334455)")
            barr = st.selectbox("Barrio", ["Talar 1", "Talar 2", "Barrancas", "Nordelta", "Santa Barbara", "Otro"])
            lot = st.text_input("Lote / Casa")
            urg = st.text_input("¿Para cuándo lo necesitás?")
            
            if st.form_submit_button("FINALIZAR PEDIDO"):
                if nom and tel and lot:
                    ped_str = "; ".join([f"{x['Cant']}x {x['Prod']}|{x['Sub']}|{x['Prof']}" for x in st.session_state.carrito])
                    p_tot = df_c["Prof"].sum() - desc
                    fila = [str(uuid.uuid4())[:8], datetime.now().strftime("%Y-%m-%d %H:%M"), nom, tel, barr, lot, urg, ped_str, float(total_f), float(p_tot)]
                    sheet_pendientes.append_row(fila)
                    
                    msg = urllib.parse.quote(f"¡Hola Lucas! Soy {nom}. Pedido web:\n{ped_str.replace('|', ' -$')}\nTotal: ${total_f}")
                    st.success("✅ ¡Pedido enviado!")
                    st.markdown(f'<a href="https://wa.me/5491130501255?text={msg}" target="_blank"><button style="width:100%; background-color:#25D366; color:white; border:none; padding:20px; border-radius:10px; font-size:22px; font-weight:bold;">🟢 AVISAR POR WHATSAPP</button></a>', unsafe_allow_stdio=True)
                    st.session_state.carrito = []
                else: st.warning("Completá Nombre, WhatsApp y Lote.")

else: # ADMIN
    pass # (Aquí iría el bloque de Admin con clave lucas2026 si lo necesitas usar)
