import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import uuid
import urllib.parse # Para el link de WhatsApp

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Pedidos para Lucas!", layout="centered")

# --- ESTILO PARA "VIEJAS" (Letra Grande) ---
st.markdown("""
    <style>
    html, body, [class*="css"]  {
        font-size: 22px !important; /* Agranda toda la letra */
    }
    .stButton>button {
        width: 100%;
        height: 3em;
        font-size: 25px !important; /* Botones grandes */
    }
    .stMetric {
        font-size: 30px !important; /* El precio total gigante */
    }
    input {
        font-size: 22px !important;
    }
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
    st.error(f"Error: {e}")

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
    st.write("Elegí lo que quieras y confirmá abajo.")
    
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
        st.info("💡 Solo múltiplos de 4.")
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
        c_b = st.number_input(f"¿Cuántas barritas? (Hay {disp_b})", 0, disp_b, step=1, key="bar_c")
        if st.button("Sumar Barrita") and c_b > 0:
            st.session_state.carrito.append({"Cat": "Barritas", "Prod": n_bar, "Cant": c_b, "Sub": 2200*c_b, "Prof": 868*c_b})

    with t[3]:
        vol = st.selectbox("Sabor Volcán", list(VOLCANES_VOLKANO.keys()))
        n_vol = f"Volkano {vol}"
        if "Dulce de Leche" in n_vol: n_vol = "Volcano Dulce de Leche"
        disp_v = stock_actual.get(n_vol, 0)
        c_v = st.number_input(f"¿Cuántos volcanes? (Hay {disp_v})", 0, disp_v, step=1, key="vol_c")
        if st.button("Sumar Volcán") and c_v > 0:
            st.session_state.carrito.append({"Cat": "Volcanes", "Prod": n_vol, "Cant": c_v, "Sub": 3500*c_v, "Prof": 1200*c_v})

    if st.session_state.carrito:
        st.divider()
        st.subheader("🛒 Tu Carrito")
        df_cart = pd.DataFrame(st.session_state.carrito)
        
        # --- LÓGICA DE PROMO SURTIDA ---
        total_bar = df_cart[df_cart["Cat"] == "Barritas"]["Cant"].sum()
        desc_bar = (total_bar // 10) * 3000 if total_bar >= 10 else 0
        if desc_bar > 0:
            st.success(f"🔥 ¡Promo Pack x10 aplicada! Descuento: -${desc_bar}")

        st.table(df_cart[["Prod", "Cant", "Sub"]])
        total_final = df_cart["Sub"].sum() - desc_bar
        st.metric("TOTAL A PAGAR", f"${total_final:,.0f}")
        
        with st.form("confirm"):
            nom = st.text_input("Nombre y Apellido")
            tel = st.text_input("Tu WhatsApp (sin el +)")
            barr = st.selectbox("Barrio", BARRIOS)
            lot = st.text_input("Lote / Casa")
            urg = st.text_input("¿Cuándo lo necesitás?", placeholder="Ej: Sábado a la noche")
            
            if st.form_submit_button("¡ENVIAR PEDIDO A LUCAS!"):
                if nom and lot and tel:
                    ped_str = "; ".join([f"{x['Cant']}x {x['Prod']}|{x['Sub']}|{x['Prof']}" for x in st.session_state.carrito])
                    
                    # Guardamos el ratio de descuento para el profit real en el Admin
                    total_p_bar = df_cart[df_cart["Cat"] == "Barritas"]["Prof"].sum()
                    ratio_p = (total_p_bar - desc_bar) / total_p_bar if (total_bar >= 10 and total_p_bar > 0) else 1

                    fila_nueva = [str(uuid.uuid4())[:8], datetime.now().strftime("%Y-%m-%d %H:%M"), nom, tel, barr, lot, urg, ped_str, float(total_final), float(df_cart["Prof"].sum() * ratio_p)]
                    sheet_pendientes.append_row(fila_nueva)
                    
                    # --- MENSAJE DE WHATSAPP ---
                    texto_wa = f"¡Hola Lucas! Soy {nom}. Acabo de hacer un pedido por la web:\n\n*Detalle:* {ped_str.replace('|', ' - $')}\n\n*Total:* ${total_final}\n*Barrio:* {barr} - Lote {lot}\n*Urgencia:* {urg}"
                    url_wa = f"https://wa.me/54911XXXXXXXX?text={urllib.parse.quote(texto_wa)}" # REEMPLAZÁ LAS X POR TU CELULAR
                    
                    st.success("✅ Pedido guardado.")
                    st.markdown(f'<a href="{url_wa}" target="_blank"><button style="width:100%; background-color:#25D366; color:white; border:none; padding:15px; border-radius:10px; font-size:20px; cursor:pointer;">🟢 AVISAR A LUCAS POR WHATSAPP</button></a>', unsafe_allow_stdio=True)
                    st.session_state.carrito = []
                else: st.warning("Por favor, completá los datos.")

else: # ADMIN
    clave = st.text_input("Clave", type="password")
    if clave == "lucas2026":
        st.title("👑 Gestión")
        # (Acá va el mismo bloque de Aceptar/Rechazar item por item que te pasé antes)
