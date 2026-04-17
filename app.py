import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import uuid

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Pedidos para Lucas!", layout="centered")

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
    st.error(f"Error de conexión: {e}. Revisá que las pestañas existan en tu Sheets.")

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
CRUDDA_SABORES = ["Brownie", "Peanut Caramel", "Arandanos y Nuez", "Coco y Chocolate", "Avellana y chocolate", "Banana Toffee"]
VOLCANES_VOLKANO = {"Chocolate": {"precio": 3500, "margen": 1200}, "Dulce de Leche": {"precio": 3500, "margen": 1200}}
BARRIOS = ["Talar del Lago 1", "Talar del Lago 2", "Barrancas de Santa Maria", "Nordelta", "Santa Barbara", "Otro"]
URGENCIAS = ["Lo necesito hoy", "Para mañana está bien", "Sin apuro"]

def obtener_stock_dict():
    data = sheet_stock.get_all_records()
    # Limpieza de nombres para evitar errores de mayúsculas
    return {str(item['PRODUCTO']).strip(): int(item['CANTIDAD']) for item in data}

def descontar_stock(pedido_str):
    items = pedido_str.split("; ")
    for item in items:
        try:
            cantidad = int(item.split("x ")[0])
            nombre_prod = item.split("x ")[1].strip()
            celda = sheet_stock.find(nombre_prod)
            fila = celda.row
            stock_actual = int(sheet_stock.cell(fila, 2).value)
            sheet_stock.update_cell(fila, 2, stock_actual - cantidad)
        except Exception as e:
            st.error(f"No se pudo descontar stock de {item}: {e}")
            continue

# --- INTERFAZ ---
modo = st.sidebar.radio("Navegación:", ["Tienda (Clientes)", "Panel Admin"])

if modo == "Tienda (Clientes)":
    st.title("🍕 Pedidos para Lucas!")
    st.markdown("""
    **¡Bienvenido al sistema de pedidos online!** Acá vas a poder hacer tu pedido a Lucas, donde vas a contar con todos los productos y su stock actualizado.  
    Agregá los productos al carrito y cuando tengas listo el pedido, completá tus datos.  
    ¡Se le enviará el pedido a Lucas y él te confirmará por WhatsApp para coordinar la entrega!
    """)
    
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

    # ... (Barritas y Volcanes se mantienen igual que tu código anterior)
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
        if "Dulce de Leche" in n_vol: n_vol = "Volcano Dulce de Leche"
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
            tel = st.text_input("Número de Teléfono (WhatsApp)")
            barr = st.selectbox("Barrio", BARRIOS)
            lot = st.text_input("Lote/Casa")
            urg = st.selectbox("¿Con qué urgencia lo necesitás?", URGENCIAS)
            
            if st.form_submit_button("ENVIAR PEDIDO"):
                if nom and lot and tel:
                    ped = "; ".join([f"{x['Cant']}x {x['Prod']}" for x in st.session_state.carrito])
                    fila_nueva = [
                        str(uuid.uuid4())[:8],              # ID
                        datetime.now().strftime("%Y-%m-%d %H:%M"), # FECHA
                        nom,                                # CLIENTE
                        tel,                                # TELEFONO
                        barr,                               # BARRIO
                        lot,                                # LOTE
                        urg,                                # URGENCIA
                        ped,                                # PEDIDO
                        float(total),                       # TOTAL
                        float(df_cart["Prof"].sum())        # PROFIT
                    ]
                    sheet_pendientes.append_row(fila_nueva)
                    st.success("¡Pedido enviado! Lucas te confirmará por WhatsApp.")
                    st.session_state.carrito = []
                    st.rerun()
                else: st.warning("Por favor, completá nombre, teléfono y lote.")

else: # PANEL ADMIN
    clave = st.text_input("Clave Admin", type="password")
    if clave == "lucas2026":
        st.title("👑 Gestión de Pedidos")
        data_p = pd.DataFrame(sheet_pendientes.get_all_records())
        if not data_p.empty:
            for i, row in data_p.iterrows():
                with st.expander(f"Pedido de {row['CLIENTE']} ({row['URGENCIA']}) - ${row['TOTAL']}"):
                    st.write(f"**Tel:** {row['TELEFONO']}")
                    st.write(f"**Barrio:** {row['BARRIO']} - Lote: {row['LOTE']}")
                    st.write(f"**Items:** {row['PEDIDO']}")
                    col1, col2 = st.columns(2)
                    if col1.button("✅ ACEPTAR", key=f"ac_{row['ID']}"):
                        # 1. Anota la venta
                        sheet_ventas.append_row([row['FECHA'], row['BARRIO'], row['PEDIDO'], 1, row['TOTAL'], row['PROFIT']])
                        # 2. Descuenta el stock
                        descontar_stock(row['PEDIDO'])
                        # 3. Borra de pendientes
                        sheet_pendientes.delete_rows(i + 2)
                        st.success("¡Pedido Aceptado!")
                        st.rerun()
                    if col2.button("❌ RECHAZAR", key=f"re_{row['ID']}"):
                        sheet_pendientes.delete_rows(i + 2)
                        st.info("Pedido Rechazado.")
                        st.rerun()
        else: st.info("No hay pedidos pendientes.")
