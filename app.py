import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
import uuid
import urllib.parse
import requests

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
    "Muzzarella estilo Napolitana": {"precio": 7500, "margen": 1800},  # Renombrada
}

PAN_AJO = {
    "Pack x5 Baguettes": {"precio": 5500, "margen": 2300},
}

EMPANADAS_SABORES = [
    "Carne", "JyQ", "QyC", "Pollo", "Humita",
    "Verdura", "Roquefort", "Cheeseburger", "Bondiola BBQ", "Capresse"
]

CRUDDA_SABORES = [
    "Brownie", "Peanut Caramel", "Arandanos y Nuez",
    "Coco y Chocolate", "Avellana y Chocolate", "Banana Toffee"
]
CRUDDA_PRECIO_UNIT  = 2200
CRUDDA_MARGEN_UNIT  = 868
CRUDDA_COSTO_UNIT   = CRUDDA_PRECIO_UNIT - CRUDDA_MARGEN_UNIT   # 1332
CRUDDA_PRECIO_CAJA  = 19000   # 10 unidades
CRUDDA_PRECIO_CAJA_UNIT = CRUDDA_PRECIO_CAJA / 10               # 1900

VOLCANES = {
    "Volkano Chocolate":       {"precio": 3500, "margen": 1200},
    "Volkano Dulce de Leche":  {"precio": 3500, "margen": 1200},
    "Volkano Nutella":         {"precio": 4500, "margen": 900},   # Nuevo
    "Classic Tiramisu":        {"precio": 3000, "margen": 600},   # Nuevo
}

LISTA_BARRIOS = [
    "Talar del Lago 1", "Talar del Lago 2", "Barrancas de Santa Maria",
    "Nordelta", "Santa Barbara", "Otro"
]

# --- 4. HELPERS ---
def obtener_stock_dict():
    try:
        data = sheet_stock.get_all_records()
        return {
            str(item.get('PRODUCTO', '')).strip(): int(item.get('CANTIDAD', 0))
            for item in data if item.get('PRODUCTO')
        }
    except:
        return {}


def notificar_telegram(nom, tel_cliente, barr_elegido, lot, urg, carrito_ajustado, total_f, p_neto):
    """Manda un mensaje al Telegram de Lucas cuando llega un pedido nuevo."""
    try:
        token   = st.secrets["telegram_bot_token"]
        chat_id = st.secrets["telegram_chat_id"]

        lineas_pedido = "\n".join([
            f"  • {x['Cant']}x {x['Prod']}  →  ${x['Sub']:,.0f}"
            for x in carrito_ajustado
        ])

        texto = (
            f"🛒 <b>NUEVO PEDIDO — TOMASSO</b>\n\n"
            f"👤 <b>Cliente:</b> {nom}\n"
            f"📱 <b>WhatsApp:</b> {tel_cliente}\n"
            f"📍 <b>Barrio:</b> {barr_elegido}  |  <b>Lote:</b> {lot}\n"
            f"⏰ <b>Para cuándo:</b> {urg}\n\n"
            f"🧾 <b>Pedido:</b>\n{lineas_pedido}\n\n"
            f"💰 <b>Total:</b> ${total_f:,.0f}\n"
            f"📈 <b>Margen neto:</b> ${p_neto:,.0f}"
        )

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, data={"chat_id": chat_id, "text": texto, "parse_mode": "HTML"}, timeout=5)
    except Exception as e:
        st.warning(f"⚠️ Pedido guardado, pero no se pudo enviar la notificación de Telegram: {e}")


def calcular_crudda_pricing(carrito):
    """
    Recalcula Sub y Prof de cada item Crudda según lógica de cajas:
      - Cada grupo de 10 barritas (de cualquier sabor) = $19.000 (1.900/u)
      - Unidades sueltas (resto) = $2.200/u
    Los valores se distribuyen proporcionalmente entre los distintos sabores.
    Devuelve: (carrito_ajustado, cantidad_de_cajas, ahorro_display)
    """
    barrita_items   = [x for x in carrito if x['Cat'] == 'Barritas']
    total_barritas  = sum(x['Cant'] for x in barrita_items)

    if total_barritas == 0:
        return [x.copy() for x in carrito], 0, 0

    cajas = total_barritas // 10
    resto = total_barritas % 10

    precio_total = cajas * CRUDDA_PRECIO_CAJA + resto * CRUDDA_PRECIO_UNIT
    costo_total  = total_barritas * CRUDDA_COSTO_UNIT
    margen_total = precio_total - costo_total

    # Cuánto ahorra el cliente vs precio individual
    ahorro = total_barritas * CRUDDA_PRECIO_UNIT - precio_total

    carrito_ajustado = []
    for item in carrito:
        item_copy = item.copy()
        if item['Cat'] == 'Barritas':
            proporcion              = item['Cant'] / total_barritas
            item_copy['Sub']        = round(precio_total * proporcion)
            item_copy['Prof']       = round(margen_total * proporcion)
        carrito_ajustado.append(item_copy)

    return carrito_ajustado, cajas, ahorro


# --- 5. INTERFAZ ---
if 'carrito' not in st.session_state:
    st.session_state.carrito = []

modo = st.sidebar.radio("Ir a:", ["Tienda", "Admin"])

# =============================================================
#  TIENDA
# =============================================================
if modo == "Tienda":
    st.title("🍕 ¡Pedidos para Lucas!")
    st.markdown("#### ¡Bienvenido! Elegí lo que más te guste y hacé tu pedido online de forma rápida.")
    st.info("🔥 **PROMO CRUDDA:** ¡Llevando 10 barritas o más pagás solo **$1.900 c/u** en vez de $2.200!")

    stock_actual = obtener_stock_dict()
    t = st.tabs(["🍕 Pizzas", "🥟 Empas", "🍫 Crudda", "🍞 Pan de Ajo", "🍰 Postres"])

    # ---- PIZZAS ----
    with t[0]:
        opciones_piz = [f"{p}  —  ${PIZZAS[p]['precio']:,}" for p in PIZZAS]
        piz_sel = st.selectbox("Elegí tu pizza", opciones_piz)
        piz     = piz_sel.split("  —  $")[0]
        n_piz   = f"Pizza {piz}"
        disp    = stock_actual.get(n_piz, 0)
        c_p     = st.number_input(f"Cantidad  ({disp} disp.)", min_value=0, max_value=max(disp, 0), step=1, key="p_c")
        if st.button("Sumar Pizza 🛒") and c_p > 0:
            st.session_state.carrito.append({
                "Cat": "Pizzas", "Prod": n_piz, "Cant": c_p,
                "Sub": PIZZAS[piz]["precio"] * c_p,
                "Prof": PIZZAS[piz]["margen"] * c_p
            })
            st.rerun()

    # ---- EMPANADAS ----
    with t[1]:
        emp   = st.selectbox("Sabor Empanada  ($1.625 c/u)", EMPANADAS_SABORES)
        n_emp = f"Empanada {emp}"
        disp_e = stock_actual.get(n_emp, 0)
        max_e  = (disp_e // 4) * 4   # redondeamos al múltiplo de 4 hacia abajo

        if max_e > 0:
            c_e = st.number_input(
                f"Cantidad  ({disp_e} disp.)  —  de a 4 unidades",
                min_value=0, max_value=max_e, step=4, key="e_c"
            )
        else:
            st.warning("Sin stock disponible para este sabor.")
            c_e = 0

        if st.button("Sumar Empas 🛒") and c_e > 0:
            st.session_state.carrito.append({
                "Cat": "Empanadas", "Prod": n_emp, "Cant": c_e,
                "Sub": 1625 * c_e, "Prof": 375 * c_e
            })
            st.rerun()

    # ---- CRUDDA ----
    with t[2]:
        bar   = st.selectbox("Sabor Barrita  ($2.200 c/u — caja de 10: $19.000)", CRUDDA_SABORES)
        n_bar = f"Crudda {bar}"
        disp_b = stock_actual.get(n_bar, 0)
        c_b    = st.number_input(f"Cantidad  ({disp_b} disp.)", min_value=0, max_value=max(disp_b, 0), step=1, key="b_c")

        # Preview de precio si el total llega a caja
        if c_b > 0:
            ya_en_carrito = sum(x['Cant'] for x in st.session_state.carrito if x['Cat'] == 'Barritas')
            total_prev    = ya_en_carrito + c_b
            if total_prev >= 10:
                cajas_prev = total_prev // 10
                st.success(f"🔥 Con esto sumás {total_prev} barritas → {cajas_prev} caja/s a $19.000 (ahorrás ${(total_prev // 10) * 3000:,}!)")

        if st.button("Sumar Barrita 🛒") and c_b > 0:
            st.session_state.carrito.append({
                "Cat": "Barritas", "Prod": n_bar, "Cant": c_b,
                "Sub": CRUDDA_PRECIO_UNIT * c_b,
                "Prof": CRUDDA_MARGEN_UNIT * c_b
            })
            st.rerun()

    # ---- PAN DE AJO ----
    with t[3]:
        opciones_pan = [f"{p}  —  ${PAN_AJO[p]['precio']:,}" for p in PAN_AJO]
        pan_sel = st.selectbox("Elegí tu pan de ajo", opciones_pan)
        pan     = pan_sel.split("  —  $")[0]
        disp_pan = stock_actual.get(pan, 0)
        c_pan    = st.number_input(f"Cantidad  ({disp_pan} disp.)", min_value=0, max_value=max(disp_pan, 0), step=1, key="pan_c")
        if st.button("Sumar Pan de Ajo 🛒") and c_pan > 0:
            st.session_state.carrito.append({
                "Cat": "Pan de Ajo", "Prod": pan, "Cant": c_pan,
                "Sub": PAN_AJO[pan]["precio"] * c_pan,
                "Prof": PAN_AJO[pan]["margen"] * c_pan
            })
            st.rerun()

    # ---- POSTRES ----
    with t[4]:
        opciones_vol = [f"{v}  —  ${VOLCANES[v]['precio']:,}" for v in VOLCANES]
        vol_sel = st.selectbox("Elegí tu postre", opciones_vol)
        vol     = vol_sel.split("  —  $")[0]
        disp_v  = stock_actual.get(vol, 0)
        c_v     = st.number_input(f"Cantidad  ({disp_v} disp.)", min_value=0, max_value=max(disp_v, 0), step=1, key="v_c")
        if st.button("Sumar Postre 🛒") and c_v > 0:
            st.session_state.carrito.append({
                "Cat": "Postres", "Prod": vol, "Cant": c_v,
                "Sub": VOLCANES[vol]["precio"] * c_v,
                "Prof": VOLCANES[vol]["margen"] * c_v
            })
            st.rerun()

    # ---- CARRITO ----
    if st.session_state.carrito:
        st.divider()
        st.subheader("🛒 Tu Pedido:")

        # Aplicar lógica de caja a Crudda
        carrito_ajustado, cajas_crudda, ahorro_crudda = calcular_crudda_pricing(st.session_state.carrito)
        df      = pd.DataFrame(carrito_ajustado)
        total_f = df["Sub"].sum()

        st.table(df[["Prod", "Cant", "Sub"]].rename(columns={"Prod": "Producto", "Cant": "Cant.", "Sub": "Subtotal ($)"}))

        if st.button("🗑️ VACIAR CARRITO", use_container_width=True):
            st.session_state.carrito = []
            st.rerun()

        if cajas_crudda > 0:
            st.success(f"🔥 ¡PROMO CAJA ACTIVADA! {cajas_crudda} caja/s de Crudda → ahorrás ${ahorro_crudda:,}")

        st.header(f"Total: ${total_f:,.0f}")

        with st.form("datos"):
            nom         = st.text_input("Nombre y Apellido")
            tel_cliente = st.text_input("Tu WhatsApp")
            barr_elegido= st.selectbox("Barrio", LISTA_BARRIOS)
            lot         = st.text_input("Lote / Casa")
            urg         = st.text_input("¿Para cuándo?")

            if st.form_submit_button("FINALIZAR PEDIDO ✅"):
                if nom and tel_cliente and lot:
                    # Guardar con precios y márgenes CORRECTOS (post-ajuste de caja)
                    ped_db  = "; ".join([
                        f"{x['Cant']}x {x['Prod']}|{x['Sub']}|{x['Prof']}"
                        for x in carrito_ajustado
                    ])
                    p_neto  = df["Prof"].sum()
                    fila    = [
                        str(uuid.uuid4())[:8],
                        datetime.now().strftime("%Y-%m-%d %H:%M"),
                        nom, tel_cliente, barr_elegido, lot, urg,
                        ped_db, float(total_f), float(p_neto)
                    ]
                    sheet_pendientes.append_row(fila)

                    # Notificación automática a Telegram
                    notificar_telegram(nom, tel_cliente, barr_elegido, lot, urg, carrito_ajustado, total_f, p_neto)

                    msg_wa      = f"Hola Lucas! Soy {nom}. Acabo de hacer un pedido web por ${total_f:,.0f}. Confirmame cuando lo veas!"
                    msg_encoded = urllib.parse.quote(msg_wa)
                    link_final  = f"https://wa.me/5491123306544?text={msg_encoded}"

                    st.success("✅ ¡Pedido registrado!")
                    st.markdown(f"### 👉 [HACÉ CLIC ACÁ PARA AVISARME POR WHATSAPP]({link_final})")
                    st.session_state.carrito = []
                else:
                    st.warning("Por favor, completá Nombre, WhatsApp y Lote.")

# =============================================================
#  PANEL ADMIN
# =============================================================
else:
    clave = st.text_input("Clave", type="password")
    if clave == "lucas2026":
        st.title("👑 Panel Admin")
        try:
            data = pd.DataFrame(sheet_pendientes.get_all_records())
            if not data.empty:
                st.error(f"🚨 TENÉS {len(data)} PEDIDOS PENDIENTES")
                for i, row in data.iterrows():
                    with st.expander(f"📦 {row['CLIENTE']}  —  {row['BARRIO']}  |  Total: ${float(row.get('TOTAL', 0)):,.0f}"):
                        st.write(f"**Items:** {row['PEDIDO']}")
                        st.write(f"**Lote:** {row['LOTE']}  |  **Urgencia:** {row['URGENCIA']}")
                        st.write(f"**WhatsApp cliente:** {row.get('WHATSAPP', '—')}")
                        c1, c2 = st.columns(2)

                        if c1.button("✅ ACEPTAR", key=f"ok_{row['ID']}"):
                            items = str(row['PEDIDO']).split("; ")
                            filas_v = []
                            for it in items:
                                p_data = it.split("|")
                                if len(p_data) < 3:
                                    continue
                                cant = int(p_data[0].split("x ")[0].strip())
                                prod = p_data[0].split("x ")[1].strip()
                                filas_v.append([
                                    row['FECHA'], row['BARRIO'], prod,
                                    cant, float(p_data[1]), float(p_data[2])
                                ])
                                # Descontar stock
                                try:
                                    cell  = sheet_stock.find(prod)
                                    s_act = int(sheet_stock.cell(cell.row, 2).value)
                                    sheet_stock.update_cell(cell.row, 2, s_act - cant)
                                except:
                                    pass
                            sheet_ventas.append_rows(filas_v)
                            sheet_pendientes.delete_rows(i + 2)
                            st.rerun()

                        if c2.button("❌ RECHAZAR", key=f"no_{row['ID']}"):
                            sheet_pendientes.delete_rows(i + 2)
                            st.rerun()
            else:
                st.info("No hay pedidos pendientes. 🎉")
        except Exception as e:
            st.error(f"Error en Admin: {e}")
