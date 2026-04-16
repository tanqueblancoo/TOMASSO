import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Lucas Business Pro", layout="wide")

# --- CONEXIÓN A GOOGLE SHEETS ---
try:
    scope = ["https://www.googleapis.com/auth/spreadsheets","https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open("TOMASSO")
    sheet_ventas = spreadsheet.worksheet("VENTAS")
    sheet_stock = spreadsheet.worksheet("STOCK")
except Exception as e:
    st.error(f"Error de conexión: {e}")

# --- BASE DE DATOS ---
PIZZAS = {
    "Muzzarella": {"precio": 8000, "margen": 2000},
    "Fugazzeta": {"precio": 8500, "margen": 2050},
    "Jamon": {"precio": 9000, "margen": 2100},
    "De Autor": {"precio": 9500, "margen": 2100},
    "Pepperoni": {"precio": 10000, "margen": 2000},
    "Napolitana": {"precio": 7500, "margen": 1800},
}

# --- CAMBIO AQUÍ: AHORA LA UNIDAD ES LA CAJA DE 4 ---
EMPANADAS_SABORES = ["Carne", "JyQ", "CyQ", "Pollo", "Humita", "Verdura", "Roquefort", "Cheeseburger", "Bondiola BBQ", "Capresse"]
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
st.title("🚀 Sistema Lucas Pro V3")

if 'carrito' not in st.session_state:
    st.session_state.carrito = []

tab1, tab2 = st.tabs(["🛒 Nueva Venta", "📊 Análisis de Negocio"])

with tab1:
    barrio_venta = st.sidebar.selectbox("📍 Barrio de la Venta", BARRIOS)

    with st.expander("➕ Cargar Productos", expanded=True):
        categoria = st.radio("Categoría:", ["Pizzas", "Empanadas", "Barritas Crudda", "Volcanes Volkano"], horizontal=True)
        
        if categoria == "Pizzas":
            sabor = st.selectbox("Sabor Pizza", list(PIZZAS.keys()))
            cant = st.number_input("Cantidad", min_value=1, step=1, key="piz")
            if st.button("Agregar Pizza"):
                st.session_state.carrito.append({
                    "Categoría": "Pizzas",
                    "Producto": f"Pizza {sabor}",
                    "Cant": cant,
                    "Subtotal": PIZZAS[sabor]["precio"] * cant,
                    "Profit": PIZZAS[sabor]["margen"] * cant
                })

        elif categoria == "Empanadas":
            st.info("Venta por Media Caja (4 unidades)")
            cant_e = st.number_input("¿Cuántas cajas de 4 querés?", min_value=1, step=1, key="emp")
            if st.button("Agregar Empanadas"):
                st.session_state.carrito.append({
                    "Categoría": "Empanadas",
                    "Producto": "Empanadas (Pack x4)",
                    "Cant": cant_e,
                    "Subtotal": PRECIO_CAJA_4 * cant_e,
                    "Profit": MARGEN_CAJA_4 * cant_e
                })
                st.toast(f"{cant_e} packs de empanadas sumados")

        elif categoria == "Barritas Crudda":
            sabor_c = st.selectbox("Elegir Sabor", CRUDDA_SABORES)
            cant_b = st.number_input("Cantidad de este sabor", min_value=1, step=1, key="bar")
            if st.button("Sumar al Carrito"):
                st.session_state.carrito.append({
                    "Categoría": "Barritas",
                    "Producto": f"Crudda {sabor_c}",
                    "Cant": cant_b,
                    "Subtotal": PRECIO_UNIT_BAR * cant_b,
                    "Profit": MARGEN_UNIT_BAR * cant_b 
                })

        elif categoria == "Volcanes Volkano":
            tipo_v = st.selectbox("Sabor Volcán", list(VOLCANES_VOLKANO.keys()))
            cant_v = st.number_input("Cantidad", min_value=1, step=1, key="vol")
            if st.button("Agregar Volcán"):
                st.session_state.carrito.append({
                    "Categoría": "Volcanes",
                    "Producto": f"Volkano {tipo_v}",
                    "Cant": cant_v,
                    "Subtotal": VOLCANES_VOLKANO[tipo_v]["precio"] * cant_v,
                    "Profit": VOLCANES_VOLKANO[tipo_v]["margen"] * cant_v
                })

    if st.session_state.carrito:
        st.divider()
        df = pd.DataFrame(st.session_state.carrito)
        
        # Lógica de Descuento Barritas
        total_barritas = df[df["Categoría"] == "Barritas"]["Cant"].sum()
        desc_vta = 0
        desc_profit = 0
        
        if total_barritas >= 10:
            packs = total_barritas // 10
            desc_vta = packs * 2000
            desc_profit = packs * 2000
            st.info(f"🔥 ¡Promo Pack x10 Aplicada! ({packs} pack/s)")

        st.subheader("Resumen del Pedido")
        st.table(df[["Producto", "Cant", "Subtotal"]])
        
        total_final = df["Subtotal"].sum() - desc_vta
        profit_final = df["Profit"].sum() - desc_profit
        
        st.metric("TOTAL A COBRAR", f"${total_final:,.0f}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ FINALIZAR VENTA", use_container_width=True, type="primary"):
                try:
                    filas_ventas = []
                    # Ratio para ajustar el margen de las barritas si hubo descuento
                    ratio_desc = (df[df["Categoría"]=="Barritas"]["Profit"].sum() - desc_profit) / df[df["Categoría"]=="Barritas"]["Profit"].sum() if total_barritas >= 10 else 1
                    
                    for item in st.session_state.carrito:
                        margen_real = item["Profit"] * ratio_desc if item["Categoría"] == "Barritas" else item["Profit"]
                        subtotal_real = item["Subtotal"] * ratio_desc if item["Categoría"] == "Barritas" else item["Subtotal"]
                        
                        filas_ventas.append([
                            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            barrio_venta,
                            item["Producto"],
                            item["Cant"],
                            subtotal_real,
                            margen_real
                        ])
                        descontar_stock(item["Producto"], item["Cant"])
                    
                    sheet_ventas.append_rows(filas_ventas)
                    st.success("¡Venta registrada!")
                    st.session_state.carrito = []
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        with col2:
            if st.button("🗑️ Vaciar Carrito", use_container_width=True):
                st.session_state.carrito = []
                st.rerun()

with tab2:
    st.header("Análisis de Negocio")
    try:
        data = pd.DataFrame(sheet_ventas.get_all_records())
        if not data.empty:
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(px.pie(data, names='Barrio', values='Subtotal', title="Ventas por Barrio"), use_container_width=True)
            with c2:
                prof_p = data.groupby('Producto')['Profit'].sum().reset_index()
                st.plotly_chart(px.bar(prof_p, x='Profit', y='Producto', orientation='h', title="Ganancia Real por Producto"), use_container_width=True)
    except:
        st.info("No hay datos suficientes en VENTAS para mostrar gráficos.")