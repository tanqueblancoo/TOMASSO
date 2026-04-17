import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import uuid
import urllib.parse

# --- 1. CONFIGURACIÓN (SIEMPRE PRIMERO) ---
st.set_page_config(page_title="Pedidos para Lucas!", layout="centered")

# --- 2. ESTILO "VIEJAS" (Letra Grande y Botones) ---
st.markdown("""
    <style>
    /* Agranda la fuente de toda la página */
    html, body, [class*="css"] {
        font-size: 24px !important;
    }
    /* Agranda los botones */
    .stButton>button {
        width: 100%;
        height: 3.5em;
        font-size: 26px !important;
        font-weight: bold;
    }
    /* Agranda los inputs de texto y números */
    input {
        font-size: 24px !important;
    }
    /* Agranda los títulos de las pestañas */
    .stTabs [data-baseweb="tab"] {
        font-size: 22px !important;
    }
    </style>
    """, unsafe_allow_stdio=True)

# --- 3. CONEXIÓN A GOOGLE SHEETS ---
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

# --- 4. DATOS Y LÓGICA ---
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

# --- 5. INTERFAZ ---
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

modo = st.sidebar.radio("Navegación:", ["Tienda", "Admin"])

if modo == "Tienda":
    st.title("🍕 ¡Pedidos para Lucas!")
    stock_actual = obtener_stock_dict()
    t = st.tabs(["🍕 Pizzas", "🥟 Empanadas", "🍫 Barritas", "🍰 Volcanes"])
    
    with t[0]: # PIZZAS
        piz = st.selectbox("Sabor de Pizza", list(PIZZAS.keys()))
        n_piz = f"Pizza {piz}"
        disp = stock_actual.get(n_piz, 0)
        c_p = st.number_input(f"¿Cuántas? (Stock: {disp})", 0, disp, step=1, key="piz_c")
        if st.button("Sumar al Carrito 🛒", key="btn_piz"):
            if c_p > 0:
                st.session_state.carrito.append({"Cat": "Pizzas", "Prod": n_piz, "Cant": c_p, "Sub": PIZZAS[piz]["precio"]*c_p, "Prof": PIZZAS[piz]["margen"]*c_p})
                st.rerun()

    with t[1]: # EMPANADAS
        emp = st.selectbox("Sabor Empanada", EMPANADAS_SABORES)
        n_emp = f"Empanada {emp}"
        disp_e = stock_actual.get(n_emp, 0)
        opciones_e = [i for i in range(0, disp_e + 1, 4)]
        c_e = st.select_slider(f"Unidades de {emp}", options=opciones_e, value=0)
        if st.button("Sumar Pack x4 🛒", key="btn_emp"):
            if c_e > 0:
                st.session_state.carrito.append({"Cat": "Empanadas", "Prod": n_emp, "Cant": c_e, "Sub": 1625*c_e, "Prof": 375*c_e})
                st.rerun()

    with t[2]: # BARRITAS
        bar = st.selectbox("Sabor Barrita", CRUDDA_SABORES)
        n_bar = f"Crudda {bar}"
        disp_b = stock_actual.get(n_bar, 0)
        c_b = st.number_input(f"¿Cuántas? (Stock: {disp_b})", 0, disp_b, step=1, key="bar_c")
        if st.button("Sumar Barrita 🛒", key="btn_bar"):
            if c_b > 0:
                st.session_state.carrito.append({"Cat": "Barritas", "Prod": n_bar, "Cant": c_b, "Sub": 2200*c_b, "Prof": 868*c_b})
                st.rerun()

    with t[3]: # VOLCANES
        vol = st.selectbox("Sabor Volcán", list(VOLCANES_VOLKANO.keys()))
        n_vol = f"Volkano {vol}"
        if "Dulce de Leche" in n_vol: n_vol = "Volcano Dulce de Leche"
        disp_v = stock_actual.get(n_vol, 0)
        c_v = st.number_input(f"¿Cuántos? (Stock: {disp_v})", 0, disp_v, step=1, key="vol_c")
        if st.button("Sumar Volcán 🛒", key="btn_vol"):
            if c_v > 0:
                st.session_state.carrito.append({"Cat": "Volcanes", "Prod": n_vol, "Cant": c_v, "Sub": 3500*c_v, "Prof": 1200*c_v})
                st.rerun()

    if st.session_state.carrito:
        st.divider()
        st.subheader("Tu Pedido:")
        df_cart = pd.DataFrame(st.session_state.carrito)
        
        # Lógica de Descuento Barritas Surtidas
        total_bar = df_cart[df_cart["Cat"] == "Barritas"]["Cant"].sum() if "Cat" in df_cart.columns else 0
        desc_bar = (total_bar // 10) * 3000 if total_bar >= 10 else 0
        
        st.dataframe(df_cart[["Prod", "Cant", "Sub"]], use_container_width=True)
        if desc_bar > 0:
            st.success(f"🎁 Descuento Pack x10 aplicado: -${desc_bar}")
            
        total_f = df_cart["Sub"].sum() - desc_bar
        st.header(f"Total: ${total_f:,.0f}")
        
        with st.form("confirmar_datos"):
            nom = st.text_input("Nombre Completo")
            tel = st.text_input("WhatsApp (Ej: 1122334455)")
            barr = st.selectbox("Barrio", BARRIOS)
            lot = st.text_input("Lote / Casa")
            urg = st.text_input("¿Cuándo lo necesitás?", placeholder="Ej: Hoy a la tarde / Sábado")
            
            enviar = st.form_submit_button("FINALIZAR PEDIDO")
            if enviar:
                if nom and lot and tel:
                    ped_str = "; ".join([f"{x['Cant']}x {x['Prod']}|{x['Sub']}|{x['Prof']}" for x in st.session_state.carrito])
                    p_tot = df_cart["Prof"].sum() - desc_bar
                    fila = [str(uuid.uuid4())[:8], datetime.now().strftime("%Y-%m-%d %H:%M"), nom, tel, barr, lot, urg, ped_str, float(total_f), float(p_tot)]
                    sheet_pendientes.append_row(fila)
                    
                    texto_wa = f"¡Hola Lucas! Soy {nom}. Acabo de hacer un pedido:\n\n*Detalle:* {ped_str.replace('|', ' - $')}\n\n*Total:* ${total_f}\n*Urgencia:* {urg}"
                    url_wa = f"https://wa.me/5491130501255?text={urllib.parse.quote(texto_wa)}"
                    
                    st.success("✅ ¡Pedido registrado!")
                    st.markdown(f'<a href="{url_wa}" target="_blank"><button style="width:100%; background-color:#25D366; color:white; border:none; padding:20px; border-radius:10px; font-size:24px; font-weight:bold; cursor:pointer;">🟢 ENVIAR WHATSAPP A LUCAS</button></a>', unsafe_allow_stdio=True)
                    st.session_state.carrito = []
                else:
                    st.warning("⚠️ Por favor completá Nombre, WhatsApp y Lote.")

else: # --- PANEL ADMIN ---
    clave = st.text_input("Clave de Acceso", type="password")
    if clave == "lucas2026":
        st.title("👑 Panel de Control")
        data_p = pd.DataFrame(sheet_pendientes.get_all_records())
        if not data_p.empty:
            for i, row in data_p.iterrows():
                with st.expander(f"Pedido de {row['CLIENTE']} ({row['URGENCIA']})"):
                    st.write(f"**Items:** {row['PEDIDO']}")
                    c1, c2 = st.columns(2)
                    if c1.button("✅ ACEPTAR", key=f"ac_{row['ID']}"):
                        try:
                            items = str(row['PEDIDO']).split("; ")
                            filas_v = []
                            for it in items:
                                p_data = it.split("|")
                                if len(p_data) < 3: continue
                                cant = int(p_data[0].split("x ")[0])
                                prod = p_data[0].split("x ")[1]
                                filas_v.append([row['FECHA'], row['BARRIO'], prod, cant, float(p_data[1]), float(p_data[2])])
                                
                                # Stock
                                cell = sheet_stock.find(prod)
                                s_val = int(sheet_stock.cell(cell.row, 2).value)
                                sheet_stock.update_cell(cell.row, 2, s_val - cant)
                            
                            sheet_ventas.append_rows(filas_v)
                            sheet_pendientes.delete_rows(i + 2)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                    if c2.button("❌ RECHAZAR", key=f"re_{row['ID']}"):
                        sheet_pendientes.delete_rows(i + 2)
                        st.rerun()
        else:
            st.info("No hay pedidos pendientes.")
