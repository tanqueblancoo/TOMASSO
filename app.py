import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import uuid
import urllib.parse

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="Pedidos para Lucas!", layout="centered")

# --- 2. CONEXIÓN ---
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

# --- 3. DATOS ---
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
LISTA_BARRIOS = ["Talar del Lago 1", "Talar del Lago 2", "Barrancas de Santa Maria", "Nordelta", "Santa Barbara", "Otro"]

def obtener_stock_dict():
    try:
        data = sheet_stock.get_all_records()
        return {str(item.get('PRODUCTO', '')).strip(): int(item.get('CANTIDAD', 0)) for item in data if item.get('PRODUCTO')}
    except: return {}

# --- 4. INTERFAZ ---
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
        total_barritas = df[df["Cat"] == "Barritas"]["Cant"].sum() if "Cat" in df.columns else 0
        descuento_promo = (total_barritas // 10) * 3000
        total_f = df["Sub"].sum() - descuento_promo
        
        st.table(df[["Prod", "Cant", "Sub"]])
        if descuento_promo > 0: st.success(f"🔥 Promo 10 unidades: -${descuento_promo}")
        st.header(f"Total: ${total_f:,.0f}")

        with st.form("datos"):
            nom = st.text_input("Nombre y Apellido")
            tel_cliente = st.text_input("Tu WhatsApp")
            barr_elegido = st.selectbox("Barrio", LISTA_BARRIOS)
            lot = st.text_input("Lote / Casa")
            urg = st.text_input("¿Para cuándo?")
            
            if st.form_submit_button("FINALIZAR PEDIDO"):
                if nom and tel_cliente and lot:
                    ped_db = "; ".join([f"{x['Cant']}x {x['Prod']}|{x['Sub']}|{x['Prof']}" for x in st.session_state.carrito])
                    p_neto = df["Prof"].sum() - descuento_promo
                    
                    fila = [str(uuid.uuid4())[:8], datetime.now().strftime("%Y-%m-%d %H:%M"), nom, tel_cliente, barr_elegido, lot, urg, ped_db, float(total_f), float(p_neto)]
                    sheet_pendientes.append_row(fila)
                    
                    # LINK WHATSAPP SEGURO
                    msg_wa = f"Hola Lucas! Soy {nom}. Acabo de hacer un pedido web por ${total_f:,.0f}. Avisame cuando lo veas!"
                    msg_encoded = urllib.parse.quote(msg_wa)
                    link_final = f"https://api.whatsapp.com/send?phone=5491123306544&text={msg_encoded}"
                    
                    st.success("✅ ¡Pedido registrado!")
                    # BOTÓN CON HTML SEPARADO PARA EVITAR EL TYPEERROR
                    st.markdown(f'<a href="{link_final}" target="_blank" style="text-decoration: none;"><div style="text-align: center; background-color: #25D366; color: white; padding: 15px; border-radius: 10px; font-size: 18px; font-weight: bold;">🟢 AVISAR A LUCAS POR WHATSAPP</div></a>', unsafe_allow_stdio=True)
                    st.session_state.carrito = []
                else: st.warning("Completá los campos obligatorios.")

else: # --- PANEL ADMIN ---
    clave = st.text_input("Clave", type="password")
    if clave == "lucas2026":
        st.title("👑 Panel Admin")
        try:
            data = pd.DataFrame(sheet_pendientes.get_all_records())
            if not data.empty:
                for i, row in data.iterrows():
                    with st.expander(f"Pedido: {row['CLIENTE']} - {row['BARRIO']}"):
                        st.write(f"**Detalle:** {row['PEDIDO']}")
                        c1, c2 = st.columns(2)
                        if c1.button("✅ ACEPTAR", key=f"ok_{row['ID']}"):
                            items = str(row['PEDIDO']).split("; ")
                            filas_v = []
                            for it in items:
                                p_data = it.split("|")
                                if len(p_data) < 3: continue
                                cant = int(p_data[0].split("x ")[0])
                                prod = p_data[0].split("x ")[1].strip()
                                filas_v.append([row['FECHA'], row['BARRIO'], prod, cant, float(p_data[1]), float(p_data[2])])
                                cell = sheet_stock.find(prod)
                                s_act = int(sheet_stock.cell(cell.row, 2).value)
                                sheet_stock.update_cell(cell.row, 2, s_act - cant)
                            sheet_ventas.append_rows(filas_v)
                            sheet_pendientes.delete_rows(i + 2)
                            st.rerun()
                        if c2.button("❌ RECHAZAR", key=f"no_{row['ID']}"):
                            sheet_pendientes.delete_rows(i + 2)
                            st.rerun()
            else: st.info("No hay pendientes.")
        except Exception as e:
            st.error(f"Error en Admin: {e}")
