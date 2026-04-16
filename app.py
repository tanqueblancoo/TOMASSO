import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Lucas Business Pro", layout="centered")

# --- CONEXIÓN A GOOGLE SHEETS ---
try:
    # Usamos los dos permisos (Sheets y Drive) para evitar el error 403
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    
    # Abrimos el archivo TOMASSO
    spreadsheet = client.open("TOMASSO")
    sheet_ventas = spreadsheet.worksheet("VENTAS")
    sheet_stock = spreadsheet.worksheet("STOCK")
except Exception as e:
    st.error(f"Error de conexión: {e}. Revisá que el archivo se llame TOMASSO y las pestañas VENTAS y STOCK.")

# --- BASE DE DATOS ACTUALIZADA ---
PIZZAS = {
    "Muzzarella": {"precio": 8000, "margen": 2000},
    "Fugazzeta": {"precio": 8500, "margen": 2050},
    "Jamon": {"precio": 9000, "margen": 2100},
    "De Autor": {"precio": 9500, "margen": 2100},
    "Pepperoni": {"precio": 10000, "margen": 2000},
    "Napolitana": {"precio": 7500, "margen": 1800},
}

PRECIO_CAJA_4 = 6500
MARGEN_CAJA_4 = 1500

CRUDDA_SABORES = ["Brownie", "Peanut Caramel", "Arandanos y Nuez", "Coco y Chocolate", "Avellana y chocolate", "Banana Toffee"]
PRECIO_UNIT_BAR = 2200
MARGEN_UNIT_BAR = 868   
PRECIO_PACK_10 = 19000  
MARGEN_PACK_10 = 5680   

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
        cant_e = st.number_input("Cajas de 4", min_value=1, step=1, key="emp")
        if st.button("Agregar Empanadas"):
            st.session_state.carrito.append({
                "Cat": "Empanadas", "Prod": "Empanadas (Pack x4)", "Cant": cant_e,
                "Subtotal": PRECIO_CAJA_4 * cant_e, "Profit": MARGEN_CAJA_4 * cant_e
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
        tipo_v = st.selectbox("Sabor Volcán", list(VOLCANES_VOLKANO.keys()))
        cant_v = st.number_input("Cant.", min_value=1, step=1, key="vol")
        if st.button("Agregar Volcán"):
            st.session_state.carrito.append({
                "Cat": "Volcanes", "Prod": f"Volkano {tipo_v}", "Cant": cant_v,
                "Subtotal": VOLCANES_VOLKANO[tipo_v]["precio"] * cant_v, "Profit": VOLCANES_VOLKANO[tipo_v]["margen"] * cant_v
            })

# --- RESUMEN DE VENTA ---
if st.session_state.carrito:
    st.divider()
    df = pd.DataFrame(st.session_state.carrito)
    
    # Lógica de Descuento Pack x10 Barritas
    total_bar = df[df["Cat"] == "Barritas"]["Cant"].sum()
    desc_vta = (total_bar // 10) * 3000 if total_bar >= 10 else 0

    st.table(df[["Prod", "Cant", "Subtotal"]])
    total_final = df["Subtotal"].sum() - desc_vta
    st.metric("TOTAL A COBRAR", f"${total_final:,.0f}")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ CERRAR VENTA", use_container_width=True, type="primary"):
            try:
                filas = []
                # Ajuste de ratio para el profit de barritas si hay descuento
                total_sub_bar = df[df["Cat"]=="Barritas"]["Subtotal"].sum()
                ratio = (total_sub_bar - desc_vta) / total_sub_bar if total_bar >= 10 else 1
                
                for item in st.session_state.carrito:
                    sub_r = item["Subtotal"] * ratio if item["Cat"] == "Barritas" else item["Subtotal"]
                    prof_r = item["Profit"] * ratio if item["Cat"] == "Barritas" else item["Profit"]
                    
                    filas.append([datetime.now().strftime("%Y-%m-%d %H:%M"), barrio_venta, item["Prod"], item["Cant"], sub_r, prof_r])
                    descontar_stock(item["Prod"], item["Cant"])
                
                sheet_ventas.append_rows(filas)
                st.success("¡Venta guardada!")
                st.session_state.carrito = []
                st.rerun()
            except Exception as e:
                st.error(f"Error al guardar: {e}")
    with col2:
        if st.button("🗑️ VACIAR", use_container_width=True):
            st.session_state.carrito = []
            st.rerun()