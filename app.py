import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Tomaso + Crudda + Volkano", layout="centered")

# --- CONEXIÓN A GOOGLE SHEETS ---
# Esto usa los "Secrets" que cargaste en Streamlit Cloud
try:
    # --- CONEXIÓN A GOOGLE SHEETS ---
    scope = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    
    # Abrimos el archivo (asegurate que se llame así en tu Drive)
    spreadsheet = client.open("TOMASSO")
    sheet_ventas = spreadsheet.worksheet("VENTAS")
    sheet_stock = spreadsheet.worksheet("STOCK")
except Exception as e:
    st.error(f"Error de conexión con Google Sheets: {e}")

# --- BASE DE DATOS DE PRODUCTOS ---
PIZZAS = {
    "Muzzarella": {"precio": 6000, "margen": 2000},
    "Fugazzeta": {"precio": 6450, "margen": 2050},
    "Jamon": {"precio": 6900, "margen": 2100},
    "De Autor": {"precio": 7400, "margen": 2100},
    "Pepperoni": {"precio": 8000, "margen": 2000},
    "Napolitana": {"precio": 5200, "margen": 1800},
}
BARRITAS_CRUDDA = {
    "Individual": {"precio": 2500, "margen": 800},
    "Pack x10": {"precio": 22000, "margen": 7000}
}
VOLCANES_VOLKANO = {
    "Chocolate": {"precio": 3500, "margen": 1200},
    "Dulce de Leche": {"precio": 3500, "margen": 1200}
}
EMPANADAS_SABORES = ["Carne", "JyQ", "CyQ", "Pollo", "Humita", "Verdura", "Roquefort", "Cheeseburger", "Bondiola BBQ", "Capresse"]
PRECIO_CAJA_8 = 10000
MARGEN_CAJA_8 = 3000
BARRIOS = ["Mi Barrio", "Barrio Al Lado", "Barrio Cercano"]

# --- LÓGICA DE STOCK ---
def descontar_stock(producto_nombre, cantidad):
    try:
        celda = sheet_stock.find(producto_nombre)
        fila = celda.row
        col_cantidad = 2 # Columna B
        stock_actual = int(sheet_stock.cell(fila, col_cantidad).value)
        sheet_stock.update_cell(fila, col_cantidad, stock_actual - cantidad)
    except:
        pass # Si no encuentra el producto, no hace nada para no trabar la venta

# --- INTERFAZ ---
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

st.title("🍕 Sistema Lucas: Multi-Marca")

barrio_venta = st.sidebar.selectbox("📍 Barrio de la Venta", BARRIOS)

with st.expander("➕ Cargar Productos", expanded=True):
    categoria = st.radio("Categoría:", ["Pizzas", "Empanadas", "Barritas Crudda", "Volcanes Volkano"])
    
    if categoria == "Pizzas":
        sabor = st.selectbox("Sabor Pizza", list(PIZZAS.keys()))
        cant = st.number_input("Cantidad", min_value=1, step=1, key="piz")
        if st.button("Agregar Pizza"):
            nombre_full = f"Pizza {sabor}"
            st.session_state.carrito.append({"Producto": nombre_full, "Cant": cant, "Subtotal": PIZZAS[sabor]["precio"] * cant, "Profit": PIZZAS[sabor]["margen"] * cant})
            st.toast(f"{nombre_full} agregada")

    elif categoria == "Empanadas":
        tipo_e = st.selectbox("Formato", ["Caja de 8", "Media Caja (4)"])
        cant_e = st.number_input("Cantidad Cajas", min_value=1, step=1, key="emp")
        precio_u = PRECIO_CAJA_8 if "8" in tipo_e else PRECIO_CAJA_8 / 2
        margen_u = MARGEN_CAJA_8 if "8" in tipo_e else MARGEN_CAJA_8 / 2
        if st.button("Agregar Empanadas"):
            nombre_full = f"Emp. {tipo_e}"
            st.session_state.carrito.append({"Producto": nombre_full, "Cant": cant_e, "Subtotal": precio_u * cant_e, "Profit": margen_u * cant_e})
            st.toast("Empanadas sumadas")

    elif categoria == "Barritas Crudda":
        tipo_b = st.selectbox("Presentación", list(BARRITAS_CRUDDA.keys()))
        cant_b = st.number_input("Cantidad", min_value=1, step=1, key="bar")
        if st.button("Agregar Barrita"):
            nombre_full = f"Crudda {tipo_b}"
            st.session_state.carrito.append({"Producto": nombre_full, "Cant": cant_b, "Subtotal": BARRITAS_CRUDDA[tipo_b]["precio"] * cant_b, "Profit": BARRITAS_CRUDDA[tipo_b]["margen"] * cant_b})
            st.toast("Barrita sumada")

    elif categoria == "Volcanes Volkano":
        tipo_v = st.selectbox("Sabor Volcán", list(VOLCANES_VOLKANO.keys()))
        cant_v = st.number_input("Cantidad", min_value=1, step=1, key="vol")
        if st.button("Agregar Volcán"):
            nombre_full = f"Volkano {tipo_v}"
            st.session_state.carrito.append({"Producto": nombre_full, "Cant": cant_v, "Subtotal": VOLCANES_VOLKANO[tipo_v]["precio"] * cant_v, "Profit": VOLCANES_VOLKANO[tipo_v]["margen"] * cant_v})
            st.toast("Volcán sumado")

# --- RESUMEN Y CIERRE ---
st.divider()
if st.session_state.carrito:
    df = pd.DataFrame(st.session_state.carrito)
    st.table(df[["Producto", "Cant", "Subtotal"]])
    
    total_v = df["Subtotal"].sum()
    st.metric("TOTAL PEDIDO", f"${total_v:,.0f}")
    
    if st.button("✅ FINALIZAR VENTA Y DESCONTAR STOCK", use_container_width=True, type="primary"):
        try:
            filas_ventas = []
            for item in st.session_state.carrito:
                filas_ventas.append([
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    barrio_venta,
                    item["Producto"],
                    item["Cant"],
                    item["Subtotal"],
                    item["Profit"]
                ])
                # Llamamos a la función de stock
                descontar_stock(item["Producto"], item["Cant"])
            
            sheet_ventas.append_rows(filas_ventas)
            st.success(f"Venta cerrada por ${total_v:,.0f}. ¡Stock actualizado!")
            st.session_state.carrito = []
            st.balloons()
        except Exception as e:
            st.error(f"Error al guardar: {e}")