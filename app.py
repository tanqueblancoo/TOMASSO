import streamlit as st
import pandas as pd

st.set_page_config(page_title="Tomaso + Crudda + Volkano", layout="centered")

# --- BASE DE DATOS AMPLIADA ---
PIZZAS = {
    "Muzzarella": {"precio": 6000, "margen": 2000},
    "Fugazzeta": {"precio": 6450, "margen": 2050},
    "Jamon": {"precio": 6900, "margen": 2100},
    "De Autor": {"precio": 7400, "margen": 2100},
    "Pepperoni": {"precio": 8000, "margen": 2000},
    "Napolitana": {"precio": 5200, "margen": 1800},
}

# Agregué los nuevos productos aquí
BARRITAS_CRUDDA = {
    "Individual": {"precio": 1332, "margen": 868},
    "Pack x10": {"precio": 13320, "margen": 5680}
}

VOLCANES_VOLKANO = {
    "Chocolate": {"precio": 2800, "margen": 700},
    "Dulce de Leche": {"precio": 2800, "margen": 700}
}

EMPANADAS_SABORES = ["Carne", "JyQ", "CyQ", "Pollo", "Humita", "Verdura", "Roquefort", "Cheeseburger", "Bondiola BBQ", "Capresse"]
PRECIO_CAJA_8 = 10000
MARGEN_CAJA_8 = 3000
BARRIOS = ["Mi Barrio", "Barrio Al Lado", "Barrio Cercano"]

if 'carrito' not in st.session_state:
    st.session_state.carrito = []

st.title("🚀 Sistema Multi-Marca: Lucas")

barrio_venta = st.sidebar.selectbox("📍 Barrio de la Venta", BARRIOS)

# --- CARGA DE PRODUCTOS ---
with st.expander("➕ Cargar Productos al Pedido", expanded=True):
    # Agregamos las nuevas categorías al radio button
    categoria = st.radio("Categoría:", ["Pizzas", "Empanadas", "Barritas Crudda", "Volcanes Volkano"])
    
    if categoria == "Pizzas":
        sabor = st.selectbox("Sabor Pizza", list(PIZZAS.keys()))
        cant = st.number_input("Cantidad", min_value=1, step=1, key="piz")
        if st.button("Agregar Pizza"):
            st.session_state.carrito.append({"Producto": f"Pizza {sabor}", "Cant": cant, "Subtotal": PIZZAS[sabor]["precio"] * cant, "Profit": PIZZAS[sabor]["margen"] * cant})
            st.toast("Pizza sumada")

    elif categoria == "Empanadas":
        tipo_e = st.selectbox("Formato", ["Caja de 8", "Media Caja (4)"])
        cant_e = st.number_input("Cantidad Cajas", min_value=1, step=1, key="emp")
        precio_u = PRECIO_CAJA_8 if "8" in tipo_e else PRECIO_CAJA_8 / 2
        margen_u = MARGEN_CAJA_8 if "8" in tipo_e else MARGEN_CAJA_8 / 2
        if st.button("Agregar Empanadas"):
            st.session_state.carrito.append({"Producto": f"Emp. {tipo_e}", "Cant": cant_e, "Subtotal": precio_u * cant_e, "Profit": margen_u * cant_e})
            st.toast("Empanadas sumadas")

    elif categoria == "Barritas Crudda":
        tipo_b = st.selectbox("Presentación", list(BARRITAS_CRUDDA.keys()))
        cant_b = st.number_input("Cantidad", min_value=1, step=1, key="bar")
        if st.button("Agregar Barrita"):
            st.session_state.carrito.append({"Producto": f"Crudda {tipo_b}", "Cant": cant_b, "Subtotal": BARRITAS_CRUDDA[tipo_b]["precio"] * cant_b, "Profit": BARRITAS_CRUDDA[tipo_b]["margen"] * cant_b})
            st.toast("Barrita sumada")

    elif categoria == "Volcanes Volkano":
        tipo_v = st.selectbox("Sabor Volcán", list(VOLCANES_VOLKANO.keys()))
        cant_v = st.number_input("Cantidad", min_value=1, step=1, key="vol")
        if st.button("Agregar Volcán"):
            st.session_state.carrito.append({"Producto": f"Volkano {tipo_v}", "Cant": cant_v, "Subtotal": VOLCANES_VOLKANO[tipo_v]["precio"] * cant_v, "Profit": VOLCANES_VOLKANO[tipo_v]["margen"] * cant_v})
            st.toast("Volcán sumado")

# --- RESUMEN Y CIERRE ---
st.divider()
if st.session_state.carrito:
    df = pd.DataFrame(st.session_state.carrito)
    st.dataframe(df[["Producto", "Cant", "Subtotal"]], use_container_width=True)
    
    total_v = df["Subtotal"].sum()
    st.metric("TOTAL PEDIDO", f"${total_v:,.0f}")
    
    if st.button("✅ FINALIZAR VENTA", use_container_width=True, type="primary"):
        st.success(f"Venta registrada en {barrio_venta}")
        st.session_state.carrito = []