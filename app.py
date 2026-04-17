import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import uuid
import urllib.parse

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Pedidos para Lucas!", layout="centered")

# --- ESTILO "VIEJAS" (Letra Grande) ---
st.markdown("""
    <style>
    html, body, [class*="css"] { font-size: 22px !important; }
    .stButton>button { width: 100%; height: 3em; font-size: 25px !important; }
    .stMetric { font-size: 30px !important; }
    input { font-size: 22px !important; }
    </style>
    """, unsafe_allow_stdio=True)

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
CRUDDA_SABORES = ["Brownie", "Peanut Caramel", "Arandanos y Nuez", "Coco y Chocolate", "Avellana y chocolate", "Banana Toffee"]
VOLCANES_VOLKANO = {"Chocolate": {"precio": 3500, "margen": 1200}, "Dulce de Leche": {"precio": 3500, "margen": 1200}}
BARRIOS = ["Talar del Lago 1", "Talar del Lago 2", "Barrancas de Santa Maria", "Nordelta", "Santa Barbara", "Otro"]

def obtener_stock_dict():
    data = sheet_stock.get_all_records()
    return {str(item['PRODUCTO']).strip(): int(item['CANTIDAD']) for item in data}

# --- INTERFAZ ---
modo = st.sidebar.radio("Navegación:", ["Tienda", "Admin"])

if modo == "Tienda":
    st.title("🍕 ¡Pedidos para Lucas!")
    if 'carrito' not in st.session_state: st.session_state.carrito = []
    stock_actual = obtener_stock_dict()
    t = st.tabs(["🍕 Pizzas", "🥟 Empanadas", "🍫 Barritas", "🍰 Volcanes"])
    
    with t[0]:
        piz = st.selectbox("Sabor de Pizza", list(PIZZAS.keys()))
        n_piz = f"Pizza {piz}"
        disp = stock_actual.get(n_piz, 0)
        c_p = st.number_input(f"¿Cuántas? (Hay {disp})", 0, disp, step=1, key="piz_c")
        if st.button("Sumar Pizza") and c_p > 0:
            st.session_state.carrito.append({"Cat": "Pizzas", "Prod": n_piz, "Cant": c_p, "Sub": PIZZAS[piz]["precio"]*c_p, "Prof": PIZZAS[piz]["margen"]*c_p})

    with t[1]:
        emp = st.selectbox("Sabor Empanada", EMPANADAS_SABORES)
        n_emp = f"Empanada {emp}"
        disp_e = stock_actual.get(n_emp, 0)
        opciones_e = [i for i in range(0, disp_e + 1, 4)]
        c_e = st.select_slider(f"Cantidad {emp}", options=opciones_e, value=0)
        if st.button("Sumar Pack x4") and c_e > 0:
            st.session_state.carrito.append({"Cat": "Empanadas", "Prod": n_emp, "Cant": c_e, "Sub": 1625*c_e, "Prof": 375*c_e})

    with t[2]:
        bar = st.selectbox("Sabor Barrita Crudda", CRUDDA_SABORES)
        n_bar = f"Crudda {bar}"
        disp_b = stock_actual.get(n_bar, 0)
        c_b = st.number_input(f"¿Cuántas? (Hay {disp_b})", 0, disp_b, step=1, key="bar_c")
        if st.button("Sumar Barrita") and c_b > 0:
            st.session_state.carrito.append({"Cat": "Barritas", "Prod": n_bar, "Cant": c_b, "Sub": 2200*c_b, "Prof": 868*c_b})

    with t[3]:
        vol = st.selectbox("Sabor Volcán", list(VOLCANES_VOLKANO.keys()))
        n_vol = f"Volkano {vol}"
        if "Dulce de Leche" in n_vol: n_vol = "Volcano Dulce de Leche"
        disp_v = stock_actual.get(n_vol, 0)
        c_v = st.number_input(f"¿Cuántos? (Hay {disp_v})", 0, disp_v, step=1, key="vol_c")
        if st.button("Sumar Volcán") and c_v > 0:
            st.session_state.carrito.append({"Cat": "Volcanes", "Prod": n_vol, "Cant": c_v, "Sub": 3500*c_v, "Prof": 1200*c_v})

    if st.session_state.carrito:
        st.divider()
        df_cart = pd.DataFrame(st.session_state.carrito)
        total_bar = df_cart[df_cart["Cat"] == "Barritas"]["Cant"].sum()
        desc_bar = (total_bar // 10) * 3000 if total_bar >= 10 else 0
        
        st.table(df_cart[["Prod", "Cant", "Sub"]])
        total_f = df_cart["Sub"].sum() - desc_bar
        st.metric("TOTAL", f"${total_f:,.0f}")
        
        with st.form("confirm"):
            nom = st.text_input("Nombre y Apellido")
            tel = st.text_input("Tu WhatsApp (Ej: 1122334455)")
            barr = st.selectbox("Barrio", BARRIOS)
            lot = st.text_input("Lote / Casa")
            urg = st.text_input("¿Cuándo lo necesitás?")
            
            if st.form_submit_button("CONFIRMAR PEDIDO"):
                if nom and lot and tel:
                    ped_str = "; ".join([f"{x['Cant']}x {x['Prod']}|{x['Sub']}|{x['Prof']}" for x in st.session_state.carrito])
                    p_tot = df_cart["Prof"].sum() - desc_bar
                    fila = [str(uuid.uuid4())[:8], datetime.now().strftime("%Y-%m-%d %H:%M"), nom, tel, barr, lot, urg, ped_str, float(total_f), float(p_tot)]
                    sheet_pendientes.append_row(fila)
                    
                    texto_wa = f"¡Hola Lucas! Soy {nom}. Pedido:\n{ped_str.replace('|', ' - $')}\nTotal: ${total_f}"
                    url_wa = f"https://wa.me/5491130501255?text={urllib.parse.quote(texto_wa)}" # Reemplacé por tu nro si es ese
                    
                    st.success("✅ Pedido enviado.")
                    st.markdown(f'<a href="{url_wa}" target="_blank"><button style="width:100%; background-color:#25D366; color:white; border:none; padding:15px; border-radius:10px; font-size:20px;">🟢 AVISAR POR WHATSAPP</button></a>', unsafe_allow_stdio=True)
                    st.session_state.carrito = []
                else: st.warning("Faltan datos.")

else: # --- MODO ADMIN ---
    clave = st.text_input("Clave", type="password")
    if clave == "lucas2026":
        st.title("👑 Panel Admin")
        data_p = pd.DataFrame(sheet_pendientes.get_all_records())
        if not data_p.empty:
            for i, row in data_p.iterrows():
                with st.expander(f"Pedido de {row['CLIENTE']} - {row['URGENCIA']}"):
                    st.write(f"**Items:** {row['PEDIDO']}")
                    col1, col2 = st.columns(2)
                    
                    if col1.button("✅ ACEPTAR", key=f"ac_{row['ID']}"):
                        try:
                            items = str(row['PEDIDO']).split("; ")
                            filas_v = []
                            for it in items:
                                p_data = it.split("|")
                                if len(p_data) < 3: continue # Saltea si el formato es viejo
                                
                                cant = int(p_data[0].split("x ")[0])
                                prod = p_data[0].split("x ")[1]
                                filas_v.append([row['FECHA'], row['BARRIO'], prod, cant, float(p_data[1]), float(p_data[2])])
                                
                                # Descontar stock
                                c = sheet_stock.find(prod)
                                s_act = int(sheet_stock.cell(c.row, 2).value)
                                sheet_stock.update_cell(c.row, 2, s_act - cant)
                            
                            sheet_ventas.append_rows(filas_v)
                            sheet_pendientes.delete_rows(i + 2)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error procesando items: {e}. Borrá el pedido de Pendientes manualmente.")

                    if col2.button("❌ RECHAZAR", key=f"re_{row['ID']}"):
                        sheet_pendientes.delete_rows(i + 2)
                        st.rerun()
        else: st.info("Sin pedidos.")
