import streamlit as st
import pandas as pd

st.set_page_config(page_title="Tomaso Pro", layout="centered")

# --- LISTA DE PRECIOS ACTUALIZADA ---
PIZZAS = {
    "Muzzarella": {"precio": 6000, "margen": 2000},
    "Fugazzeta": {"precio": 6450, "margen": 2050},
    "Jamon": {"precio": 6900, "margen": 2100},
    "De Autor": {"precio": 7400, "margen": 2100},
    "Pepperoni": {"precio": 8000, "margen": 2000},
    "Napolitana": {"precio": 5200, "margen": 1800},
}
EMPANADAS_SABORES = ["Carne", "JyQ", "CyQ", "Pollo", "Humita", "Verdura", "Roquefort", "Cheeseburger", "Bondiola BBQ", "Capresse"]
PRECIO_CAJA_8 = 10000
MARGEN_CAJA_8 = 3000
BARRIOS = ["Mi Barrio", "Barrio Al Lado", "Barrio Cercano"]

# Inicializar carrito si no existe
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

# --- INTERFAZ ---
st.title("🚀 Tomaso: Pedidos Sin Límite")

# Sidebar para info general
st.sidebar.header("Configuración")
barrio_venta = st.sidebar.selectbox("📍 Barrio", BARRIOS)

# 1. SECCIÓN DE CARGA
with st.container():
    col_tipo, col_sabor, col_cant = st.columns([2, 3, 2])
    
    with col_tipo:
        prod_tipo = st.selectbox("Producto", ["Pizza", "Caja x8", "Media Caja x4"])
    
    with col_sabor:
        if prod_tipo == "Pizza":
            sabor = st.selectbox("Sabor", list(PIZZAS.keys()))
        else:
            sabor = "Variadas" # Las empanadas las agrupamos por caja para rapidez
            
    with col_cant:
        # Aquí podés poner 1 o 1000, no hay límite
        cantidad = st.number_input("Cant.", min_value=1, step=1, value=1)

    if st.button("➕ AGREGAR AL PEDIDO", use_container_width=True):
        if prod_tipo == "Pizza":
            p = PIZZAS[sabor]
            item = {"Producto": f"Pizza {sabor}", "Cant": cantidad, "Subtotal": p["precio"] * cantidad, "Profit": p["margen"] * cantidad}
        else:
            p_caja = PRECIO_CAJA_8 if "8" in prod_tipo else PRECIO_CAJA_8 / 2
            m_caja = MARGEN_CAJA_8 if "8" in prod_tipo else MARGEN_CAJA_8 / 2
            item = {"Producto": prod_tipo, "Cant": cantidad, "Subtotal": p_caja * cantidad, "Profit": m_caja * cantidad}
        
        st.session_state.carrito.append(item)
        st.toast("Agregado!")

st.divider()

# 2. RESUMEN DE VENTA (EL CARRITO)
if st.session_state.carrito:
    st.subheader(f"🛒 Detalle del Pedido - {barrio_venta}")
    df = pd.DataFrame(st.session_state.carrito)
    
    # Mostramos la tabla de lo que va pidiendo
    st.dataframe(df[["Producto", "Cant", "Subtotal"]], use_container_width=True)
    
    total_vta = df["Subtotal"].sum()
    total_profit = df["Profit"].sum()
    
    # Grandes totales destacados
    st.metric("TOTAL A COBRAR", f"${total_vta:,.0f}")
    
    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        if st.button("✅ CERRAR VENTA", use_container_width=True, type="primary"):
            # AQUÍ ES DONDE SE GUARDARÍA TODO
            st.success(f"Venta registrada por ${total_vta:,.0f}")
            st.session_state.carrito = [] # Limpiar para el próximo cliente
            st.balloons()
    with col_cancel:
        if st.button("🗑️ BORRAR TODO", use_container_width=True):
            st.session_state.carrito = []
            st.rerun()
else:
    st.info("Esperando carga de pedido...")