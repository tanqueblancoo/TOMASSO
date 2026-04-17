import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import uuid

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Tomasso - Pedidos Online", layout="centered")

# --- CONEXIÓN ---
try:
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open("TOMASSO")
    sheet_ventas = spreadsheet.worksheet("VENTAS")
    sheet_stock = spreadsheet.worksheet("STOCK")
    sheet_pendientes = spreadsheet.worksheet("PENDIENTES")
except Exception as e:
    st.error(f"Error de conexión: {e}. Revisá que las pestañas VENTAS, STOCK y PENDIENTES existan.")

# --- DATOS (Precios y Márgenes) ---
PIZZAS = {
    "Muzzarella": {"precio": 8000, "margen": 2000},
    "Fugazzeta": {"precio": 8500, "margen": 2050},
    "Jamon": {"precio": 9000, "margen": 2100},
    "De Autor": {"precio": 9500, "margen": 2100},
    "Pepperoni": {"precio": 10000, "margen": 2000},
    "Napolitana": {"precio": 7500, "margen": 1800},
}
EMPANADAS_SABORES = ["Carne", "JyQ", "CyQ", "Pollo", "Humita", "Verdura", "Roquefort", "Cheeseburger", "Bondiola BBQ", "Capresse"]
CRUDDA_SABORES = ["Brownie", "Peanut Caramel", "Arandanos y Nuez", "Coco y Chocolate", "Avellana y chocolate", "Banana Toffee"]
VOLCANES_VOLKANO = {"Chocolate": {"precio": 3500, "margen": 1200}, "Dulce de Leche": {"precio": 3500, "margen": 1200}}
BARRIOS = ["Talar del Lago 1", "Talar del Lago 2", "Barrancas de Santa Maria", "Nordelta", "Santa Barbara", "Otro"]

def obtener_stock_dict():
    data = sheet_stock.get_all_records()
    return {item['PRODUCTO']: int(item['CANTIDAD']) for item in data}

def descontar_stock(pedido_str):
    # Función que procesa el texto del pedido y resta del stock
    stock_dict = obtener_stock_dict()
    items = pedido_str.split("; ")
    for item in items:
        try:
            cantidad = int(item.split("x ")[0])
            nombre_prod = item.split("x ")[1]
            celda = sheet_stock.find(nombre_prod)
            fila = celda.row
            stock_actual = int(sheet_stock.cell(fila, 2).value)
            sheet_stock.update_cell(fila, 2, stock_actual - cantidad)
        except:
            continue

# --- INTERFAZ ---
modo = st.sidebar.radio("Navegación:", ["Tienda (Clientes)", "Panel Admin"])

if modo == "Tienda (Clientes)":
    st.title("🍕 Tomasso - Pedidos Online")
    if 'carrito' not in st.session_state: st.session_state.carrito = []
    
    stock_actual = obtener_stock_dict()
    t = st.tabs(["Pizzas", "Empanadas", "Barritas", "Volcanes"])
    
    with t[0]: # PIZZAS
        piz = st.selectbox("Elegí tu Pizza", list(PIZZAS.keys()))
        n_piz = f"Pizza {piz}"
        disp = stock_actual.get(n_piz, 0)
        c_p = st.number_input(f"Unidades ({disp} disp.)", 0, disp, step=1, key="piz_c")
        if st.button("Agregar Pizza") and c_p > 0:
            st.session_state.carrito.append({"Prod": n_piz, "Cant": c_p, "Sub": PIZZAS[piz]["precio"]*c_p, "Prof": PIZZAS[piz]["margen"]*c_p})

    with t[1]: # EMPANADAS
        st.info("💡 Mínimo 4 unidades por sabor.")
        emp = st.selectbox("Sabor", EMPANADAS_SABORES)
        n_emp = f"Empanada {emp}"
        disp_e = stock_actual.get(n_emp, 0)
        opciones_cuatro = [i for i in range(0, disp_e + 1, 4)]
        c_e = st.select_slider(f"Cantidad {emp} (Múltiplos de 4)", options=opciones_cuatro, value=0)
        if st.button("Agregar Pack") and c_e > 0:
            st.session_state.carrito.append({"Prod": n_emp, "Cant": c_e, "Sub": 1625*c_e, "Prof": 375*c_e})

    with t[2]: # BARRITAS
        bar = st.selectbox("Sabor Barrita", CRUDDA_SABORES)
        n_bar = f"Crudda {bar}"
        disp_b = stock_actual.get(n_bar, 0)
        c_b = st.number_input(f"Unidades ({disp_b} disp.)", 0, disp_b, step=1, key="bar_c")
        if st.button("Agregar Barrita") and c_b > 0:
            st.session_state.carrito.append({"Prod": n_bar, "Cant": c_b, "Sub": 2200*c_b, "Prof": 868*c_b})

    with t[3]: # VOLCANES
        vol = st.selectbox("Sabor Volcán", list(VOLCANES_VOLKANO.keys()))
        n_vol = f"Volkano {vol}"
        if "Dulce de Leche" in n_vol: n_vol = "Volcano Dulce de Leche" # Match con tu stock CSV
        disp_v = stock_actual.get(n_vol, 0)
        c_v = st.number_input(f"Unidades ({disp_v} disp.)", 0, disp_v, step=1, key="vol_c")
        if st.button("Agregar Volcán") and c_v > 0:
            st.session_state.carrito.append({"Prod": n_vol, "Cant": c_v, "Sub": 3500*c_v, "Prof": 1200*c_v})

    if st.session_state.carrito:
        st.divider()
        df_cart = pd.DataFrame(st.session_state.carrito)
        st.table(df_cart[["Prod", "Cant", "Sub"]])
        total = df_cart["Sub"].sum()
        st.header(f"Total: ${total:,.0f}")
        
        with st.form("confirm"):
            nom = st.text_input("Tu Nombre")
            barr = st.selectbox("Barrio", BARRIOS)
            lot = st.text_input("Lote/Casa")
            if st.form_submit_button("ENVIAR PEDIDO"):
                if nom and lot:
                    ped = "; ".join([f"{x['Cant']}x {x['Prod']}" for x in st.session_state.carrito])
                    # Armamos la lista con los 8 datos exactos para las 8 columnas
                    fila_nueva = [
                        str(uuid.uuid4())[:8],              # ID (Col A)
                        datetime.now().strftime("%Y-%m-%d %H:%M"), # FECHA (Col B)
                        nom,                                # CLIENTE (Col C)
                        barr,                               # BARRIO (Col D)
                        lot,                                # LOTE (Col E)
                        ped,                                # PEDIDO (Col F)
                        float(total),                       # TOTAL (Col G)
                        float(df_cart["Prof"].sum())        # PROFIT (Col H)
                    ]
                    
                    sheet_pendientes.append_row(fila_nueva)
                    st.success("¡Pedido enviado! Lucas te confirmará por WhatsApp.")
                    st.session_state.carrito = []
                    st.rerun()
                else:
                    st.warning("Faltan datos de envío.")

else: # PANEL ADMIN
    clave = st.text_input("Clave Admin", type="password")
    if clave == "lucas2026":
        st.title("👑 Gestión de Pedidos")
        data_p = pd.DataFrame(sheet_pendientes.get_all_records())
        if not data_p.empty:
            for i, row in data_p.iterrows():
                with st.expander(f"Pedido de {row['CLIENTE']} - {row['BARRIO']} (${row['TOTAL']})"):
                    st.write(f"**Items:** {row['PEDIDO']}")
                    col1, col2 = st.columns(2)
                    if col1.button("✅ ACEPTAR", key=f"ac_{row['ID']}"):
                        sheet_ventas.append_row([row['FECHA'], row['BARRIO'], row['PEDIDO'], 1, row['TOTAL'], row['PROFIT']])
                        descontar_stock(row['PEDIDO'])
                        sheet_pendientes.delete_rows(i + 2)
                        st.rerun()
                    if col2.button("❌ RECHAZAR", key=f"re_{row['ID']}"):
                        sheet_pendientes.delete_rows(i + 2)
                        st.rerun()
        else: st.info("No hay pedidos pendientes.")
