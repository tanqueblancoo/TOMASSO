import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Lucas Business Pro", layout="centered")

# --- CONEXIÓN ---
try:
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open("TOMASSO")
    sheet_ventas = spreadsheet.worksheet("VENTAS")
    sheet_stock = spreadsheet.worksheet("STOCK")
except Exception as e:
    st.error(f"Error de conexión: {e}")

# --- DATOS ---
PIZZAS = {
    "Muzzarella": {"precio": 8000, "margen": 2000},
    "Fugazzeta": {"precio": 8500, "margen": 2050},
    "Jamon": {"precio": 9000, "margen": 2100},
    "De Autor": {"precio": 9500, "margen": 2100},
    "Pepperoni": {"precio": 10000, "margen": 2000},
    "Napolitana": {"precio": 7500, "margen": 1800},
}

EMPANADAS_SABORES = ["Carne", "JyQ", "CyQ", "Pollo", "Humita", "Verdura", "Roquefort", "Cheeseburger", "Bondiola BBQ", "Capresse"]
PRECIO_UNIT_EMP = 1625 
MARGEN_UNIT_EMP = 375

CRUDDA_SABORES = ["Brownie", "Peanut Caramel", "Arandanos y Nuez", "Coco y Chocolate", "Avellana y chocolate", "Banana Toffee"]
PRECIO_UNIT_BAR = 2200
MARGEN_UNIT_BAR = 868

VOLCANES_VOLKANO = {
    "Chocolate": {"precio": 3500, "margen": 1200},
    "Dulce de Leche": {"precio": 3500, "margen": 1200}
}

BARRIOS = ["Talar del Lago 1", "Talar del lago 2","Barrancas de Santa Maria","Nordelta","Santa Barbara","Otro"]

# --- LÓGICA DE STOCK ---
def descontar_stock(producto_nombre, cantidad):
    try:
        celda = sheet_stock.find(producto_nombre)
        fila = celda.row
        stock_actual = int(sheet_stock.cell(fila, 2).value)
        sheet_stock.update_cell(fila, 2, stock_actual - cantidad)
    except:
        pass

# --- INTERFAZ ---
st.title("🍕 Sistema Lucas Pro")

if 'carrito' not in st.session_state:
    st.session_state.carrito = []

barrio_venta = st.sidebar.selectbox("📍 Barrio", BARRIOS)

with st.expander("➕ Cargar Productos", expanded=True):
    categoria = st.radio("Categoría:", ["Pizzas", "Empanadas", "Barritas Crudda", "Volcanes"], horizontal=True)
    
    if categoria == "Pizzas":
        sabor = st.selectbox("Sabor Pizza", list(PIZZAS.keys()))
        cant = st.number_input("Cantidad", min_value=1, step=1, key="piz")
        if st.button("Agregar Pizza"):
            st.session_state.carrito.append({
                "Cat": "Pizzas", "Prod": f"Pizza {sabor}", "Cant": cant,
                "Subtotal": PIZZAS[sabor]["precio"] * cant, "Profit": PIZZAS[sabor]["margen"] * cant
            })

    elif categoria == "Empanadas":
        sabor_e = st.selectbox("Sabor de Empanada", EMPANADAS_SABORES)
        cant_e = st.number_input("¿Cuántas unidades?", min_value=1, step=1, key="emp_u")
        if st.button("Sumar Empanadas"):
            st.session_state.carrito.append({
                "Cat": "Empanadas", "Prod": f"Empanada {sabor_e}", "Cant": cant_e,
                "Subtotal": PRECIO_UNIT_EMP * cant_e, "Profit": MARGEN_UNIT_EMP * cant_e
            })

    elif categoria == "Barritas Crudda":
        sabor_c = st.selectbox("Sabor", CRUDDA_SABORES)
        cant_b = st.number_input("Unidades", min_value=1, step=1, key="bar")
        if st.button("Sumar Barritas"):
            st.session_state.carrito.append({
                "Cat": "Barritas", "Prod": f"Crudda {sabor_c}", "Cant": cant_b,
                "Subtotal": PRECIO_UNIT_BAR * cant_b, "Profit": MARGEN_UNIT_BAR * cant_b 
            })

    elif categoria == "Volcanes":
        sabor_v = st.selectbox("Sabor del Volcán", list(VOLCANES_VOLKANO.keys()))
        cant_v = st.number_input("Unidades", min_value=1, step=1, key="vol")
        if st.button("Sumar Volcanes"):
            st.session_state.carrito.append({
                "Cat": "Volcanes", "Prod": f"Volkano {sabor_v}", "Cant": cant_v,
                "Subtotal": VOLCANES_VOLKANO[sabor_v]["precio"] * cant_v, 
                "Profit": VOLCANES_VOLKANO[sabor_v]["margen"] * cant_v
            })

# --- RESUMEN Y CIERRE ---
if st.session_state.carrito:
    st.divider()
    df = pd.DataFrame(st.session_state.carrito)
    
    # Descuento Barritas (Promo 10)
    total_bar = df[df["Cat"] == "Barritas"]["Cant"].sum()
    desc_bar = (total_bar // 10) * 3000 if total_bar >= 10 else 0

    st.table(df[["Prod", "Cant", "Subtotal"]])
    
    total_final = df["Subtotal"].sum() - desc_bar
    st.metric("TOTAL A COBRAR", f"${total_final:,.0f}")
    
    if st.button("✅ CERRAR VENTA", type="primary", use_container_width=True):
        try:
            filas = []
            for item in st.session_state.carrito:
                filas.append([datetime.now().strftime("%Y-%m-%d %H:%M"), barrio_venta, item["Prod"], item["Cant"], item["Subtotal"], item["Profit"]])
                descontar_stock(item["Prod"], item["Cant"])
            
            sheet_ventas.append_rows(filas)
            st.success("¡Venta y Stock actualizados!")
            st.session_state.carrito = []
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
