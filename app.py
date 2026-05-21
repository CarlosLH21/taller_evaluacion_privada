"""
App Streamlit - Construcción del Flujo de Caja de Proyectos
Evaluación Privada de Proyectos
"""

import streamlit as st
import pandas as pd
import io
import json
from calculos import (
    calcular_depreciacion, calcular_capital_trabajo,
    calcular_ir_fce, calcular_escudo_tributario,
    calcular_ffn, calcular_pyg, calcular_van, calcular_tir,
    calcular_modulo_igv
)

# ─────────────────────────────────────────────
st.set_page_config(page_title="Flujo de Caja", layout="wide")
st.title("📊 Constructor de Flujo de Caja")
st.caption("Evaluación Privada de Proyectos — Motor automático")

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Configuración del proyecto")
    nombre_proyecto  = st.text_input("Nombre del proyecto", "Mi Proyecto", key="_meta_nombre")
    periodos         = st.number_input("Vida útil (años)", min_value=1, max_value=20, value=4, key="_meta_periodos_w")
    tasa_ir          = st.number_input("Impuesto a la renta (%)", value=30.0, key="_meta_tasa_ir_w") / 100
    tasa_descuento   = st.number_input("Tasa de descuento / COK (%)", value=10.0, key="_meta_tasa_descuento_w") / 100

    st.divider()
    st.subheader("Opciones del modelo")
    hay_igv           = st.toggle("¿Hay IGV?",                    value=False, key="_meta_hay_igv")
    hay_isc           = st.toggle("¿Hay ISC?",                    value=False, key="_meta_hay_isc")
    hay_financiamiento= st.toggle("¿Hay financiamiento / deuda?", value=False, key="_meta_hay_financiamiento")
    hay_inflacion     = st.toggle("¿Hay inflación?",              value=False, key="_meta_hay_inflacion")
    hay_credito_ventas= st.toggle("¿Ventas al crédito (CC)?",     value=False, key="_meta_hay_credito")
    permite_perdidas  = st.toggle("¿Se acumulan pérdidas tributarias?", value=True, key="_meta_permite_perdidas")

    tasa_igv      = st.number_input("Tasa IGV (%)",        value=19.0, key="_meta_tasa_igv_w") / 100 if hay_igv else 0.0
    igv_diferido  = st.toggle("¿IGV diferido un año?", value=False, key="_meta_igv_diferido",
                              help="El crédito fiscal de egresos se reconoce un año después del pago") if hay_igv else False
    tasa_isc   = st.number_input("Tasa ISC (%)",        value=20.0, key="_meta_tasa_isc_w") / 100 if hay_isc   else 0.0
    inflacion  = st.number_input("Inflación anual (%)", value=40.0, key="_meta_inflacion_w") / 100 if hay_inflacion else 0.0

    # Guardar / Cargar
    st.divider()
    st.subheader("Guardar / Cargar")

    archivo_cargado = st.file_uploader("Cargar configuracion (.json)", type=["json"])
    if archivo_cargado is not None:
        try:
            datos = json.load(archivo_cargado)
            for k, v in datos.items():
                if k in st.session_state:
                    st.session_state[k] = v
            st.success("Configuracion cargada. Recarga la pagina para aplicar cambios.")
        except Exception as e:
            st.error(f"Error: {e}")

    if st.button("Guardar configuracion actual"):
        prefijos = ("prod_", "act_", "cost_", "cc_", "_meta_")
        config = {}
        for k, v in st.session_state.items():
            if any(k.startswith(p) for p in prefijos) and isinstance(v, (int, float, str, bool)):
                config[k] = v
        buf_j = io.BytesIO(json.dumps(config, ensure_ascii=False, indent=2).encode())
        st.download_button("Descargar .json", data=buf_j,
                           file_name=f"{nombre_proyecto.replace(' ','_')}_config.json",
                           mime="application/json", key="dl_config")
# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────
tab1, tab2, tab_igv, tab3, tab5, tab4 = st.tabs([
    "💰 Ingresos", "🏗️ Inversión & Costos", "🧾 IGV",
    "🏦 Financiamiento", "📋 PyG", "📈 Resultados"
])

# ══════════════════════════════════════════════
# TAB 1 — INGRESOS
# ══════════════════════════════════════════════
with tab1:
    st.subheader("Módulo de Ingresos")
    num_productos = st.number_input("Nº de productos/servicios", min_value=1, max_value=10, value=1, key="_meta_num_productos")

    ingresos_sin_igv    = [0.0] * n   # sin IGV, sin ISC  → base para PyG e IR
    ingresos_con_igv    = [0.0] * n   # con IGV, sin ISC  → base para módulo IGV
    ingresos_con_isc    = [0.0] * n   # con ISC, sin IGV  → para FC ingresos si hay ISC
    ingresos_fc         = [0.0] * n   # lo que entra a caja = sin ISC * (1+IGV+ISC)

    for i in range(int(num_productos)):
        with st.expander(f"Producto {i+1}", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                # El precio ingresado es CON ISC si hay ISC, SIN IGV siempre
                label_precio = "Precio unitario (con ISC, sin IGV)" if hay_isc else "Precio unitario (sin IGV)"
                precio_con_isc = st.number_input(label_precio, key=f"prod_precio_{i}", value=0.0)
            with col2:
                tiene_igv_prod = st.checkbox("¿Grava IGV?", key=f"prod_igv_{i}", value=hay_igv)
            with col3:
                tiene_isc_prod = st.checkbox("¿Grava ISC?", key=f"prod_isc_{i}", value=hay_isc) if hay_isc else False

            # Precio sin ISC: precio_con_isc / (1 + tasa_isc)
            precio_sin_isc = precio_con_isc / (1 + tasa_isc) if (tiene_isc_prod and hay_isc and tasa_isc > 0) else precio_con_isc

            st.markdown("**Cantidades por período:**")
            cols = st.columns(n)
            for t in range(n):
                with cols[t]:
                    q = st.number_input(f"Per. {t+1}", key=f"prod_cant_{i}_{t}", value=0.0, min_value=0.0)
                    factor_inf = (1 + inflacion) ** (t + 1) if inflacion > 0 else 1.0

                    # Base sin ISC y sin IGV (para PyG e IR)
                    ing_sin_isc = precio_sin_isc * factor_inf * q
                    ingresos_sin_igv[t] += ing_sin_isc

                    # Con IGV sin ISC (para módulo IGV)
                    ingresos_con_igv[t] += ing_sin_isc * (1 + tasa_igv) if (tiene_igv_prod and hay_igv) else ing_sin_isc

                    # FC ingresos: precio sin ISC * (1 + IGV + ISC)
                    factor_fc = 1.0
                    if tiene_igv_prod and hay_igv:   factor_fc += tasa_igv
                    if tiene_isc_prod and hay_isc:   factor_fc += tasa_isc
                    ingresos_fc[t]     += ing_sin_isc * factor_fc
                    ingresos_con_isc[t]+= ing_sin_isc * tasa_isc if (tiene_isc_prod and hay_isc) else 0.0

    if hay_credito_ventas:
        st.subheader("Cuentas por cobrar")
        cols = st.columns(n)
        cc = []
        for t in range(n):
            with cols[t]:
                cc.append(st.number_input(f"CC Per. {t+1}", key=f"cc_{t}", value=0.0, min_value=0.0))
        ingresos_sin_igv_efectivos = [ingresos_sin_igv[t] + (cc[t-1] if t > 0 else 0.0) for t in range(n)]
        ingresos_pyg = [ingresos_sin_igv[t] + cc[t] for t in range(n)]
    else:
        ingresos_sin_igv_efectivos = ingresos_sin_igv[:]
        ingresos_pyg = ingresos_sin_igv[:]

    df_ing = pd.DataFrame({"Período": etiquetas_periodos,
        "Sin ISC, sin IGV": [f"{x:,.2f}" for x in ingresos_sin_igv_efectivos],
        "Con IGV, sin ISC": [f"{x:,.2f}" for x in ingresos_con_igv],
    })
    if hay_isc:
        df_ing["ISC cobrado"] = [f"{x:,.2f}" for x in ingresos_con_isc]
        df_ing["FC Ingresos (IGV+ISC)"] = [f"{x:,.2f}" for x in ingresos_fc]
    st.dataframe(df_ing, use_container_width=True)

# ══════════════════════════════════════════════
# TAB 2 — INVERSIÓN & COSTOS
# (todos los widgets y cálculos de inversión/costos/KL aquí)
# ══════════════════════════════════════════════
with tab2:
    st.subheader("Inversión inicial y activos")
    num_activos = st.number_input("Nº de activos", min_value=0, max_value=20, value=2, key="_meta_num_activos")

    activos = []
    inv_sin_igv_p0 = 0.0
    inv_con_igv_p0 = 0.0
    inv_adicional  = {t: 0.0 for t in range(n)}
    liq_sin_igv    = 0.0
    liq_con_igv    = 0.0

    for i in range(int(num_activos)):
        with st.expander(f"Activo {i+1}", expanded=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                nombre_act    = st.text_input("Nombre", key=f"act_nom_{i}", value=f"Activo {i+1}")
                valor_adq     = st.number_input("Valor adquisición (sin IGV)", key=f"act_val_{i}", value=0.0,
                                                help="Salida real de caja. Usar 0 si el activo es cedido sin desembolso.")
                valor_dep_base= st.number_input("Valor base para depreciación", key=f"act_valdep_{i}", value=valor_adq,
                                                help="Usar el valor de tasación si el activo fue cedido (ej: camión del tío).")
                periodo_compra= st.number_input("Período de compra (0=inicial)", key=f"act_per_{i}", value=0, min_value=0, max_value=n)
            with c2:
                deprecia       = st.checkbox("¿Deprecia?",          key=f"act_dep_{i}", value=True)
                vida_util      = st.number_input("Vida útil (años)", key=f"act_vu_{i}",  value=n, min_value=1) if deprecia else n
                val_res_contable = st.number_input("Valor residual contable", key=f"act_vrc_{i}", value=0.0) if deprecia else 0.0
            with c3:
                tiene_igv_act = st.checkbox("¿Compra grava IGV?",        key=f"act_igv_{i}",    value=False)
                se_vende_liq  = st.checkbox("¿Se vende en liquidación?", key=f"act_liq_{i}",    value=False)
                usar_val_libros = False
                val_venta_liq   = 0.0
                igv_venta_liq   = False
                if se_vende_liq:
                    usar_val_libros = st.checkbox("¿Valor libros en liq.?",   key=f"act_vl_{i}",     value=deprecia)
                    if not usar_val_libros:
                        val_venta_liq = st.number_input("Valor venta liq. (sin IGV)", key=f"act_vliq_{i}", value=0.0)
                    igv_venta_liq = st.checkbox("¿Venta liq. grava IGV?", key=f"act_igvliq_{i}", value=False)

            # Acumular inversión
            if int(periodo_compra) == 0:
                inv_sin_igv_p0 += valor_adq
                inv_con_igv_p0 += valor_adq * (1 + tasa_igv) if tiene_igv_act else valor_adq
            else:
                t_c = int(periodo_compra) - 1
                inv_adicional[t_c] = inv_adicional.get(t_c, 0.0) + valor_adq

            # Valor en libros para liquidación
            v_liq_final = 0.0
            if se_vende_liq:
                if deprecia and usar_val_libros:
                    dep_a = (valor_dep_base - val_res_contable) / vida_util
                    v_liq_final = max(valor_dep_base - dep_a * n, 0.0)
                else:
                    v_liq_final = val_venta_liq
                liq_sin_igv += v_liq_final
                liq_con_igv += v_liq_final * (1 + tasa_igv) if igv_venta_liq else v_liq_final

            activos.append({
                "nombre": nombre_act, "valor": valor_adq, "valor_dep": valor_dep_base,
                "periodo_compra": int(periodo_compra), "deprecia": deprecia,
                "vida_util": int(vida_util), "valor_residual_contable": val_res_contable,
                "tiene_igv": tiene_igv_act,
            })

    dep_por_periodo = calcular_depreciacion(activos, n)

    # Capital de trabajo
    st.subheader("Capital de trabajo")
    col_kt1, col_kt2 = st.columns(2)
    with col_kt1:
        pct_kt = st.number_input("% sobre incremento de ventas", value=10.0) / 100
    with col_kt2:
        base_kt = st.selectbox("Base para KT", ["Ventas sin IGV", "Ventas con IGV"])
    base_ventas_kt = ingresos_sin_igv if base_kt == "Ventas sin IGV" else ingresos_con_igv
    cambios_kl_lista, kl_recuperado = calcular_capital_trabajo(n, base_ventas_kt, pct_kt)

    # Costos operativos
    st.subheader("Costos operativos")
    num_costos = st.number_input("Nº de partidas de costo", min_value=1, max_value=15, value=3, key="_meta_num_costos")
    costos_sin_igv = [0.0] * n
    costos_con_igv = [0.0] * n

    for i in range(int(num_costos)):
        with st.expander(f"Costo {i+1}", expanded=i < 3):
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                st.text_input("Nombre", key=f"cost_nom_{i}", value=f"Costo {i+1}")
            with c2:
                igv_costo = st.checkbox("¿Grava IGV?", key=f"cost_igv_{i}", value=False)
            with c3:
                inf_costo = st.checkbox("¿Crece con inflación?", key=f"cost_inf_{i}", value=False,
                                        help="Si activo, ingresa el valor del Per.1 y los demás se calculan con el factor de inflación") if inflacion > 0 else False

            cols_c = st.columns(n)
            for t in range(n):
                with cols_c[t]:
                    if inf_costo and t > 0:
                        # Calcula automáticamente desde el valor del Per.1
                        val_base = abs(st.session_state.get(f"cost_val_{i}_0", 0.0))
                        factor_t = (1 + inflacion) ** t  # relativo al Per.1 que ya tiene factor^1
                        val_c = val_base * factor_t
                        st.number_input(f"Per. {t+1}", key=f"cost_val_{i}_{t}",
                                        value=round(val_c, 2), disabled=True)
                    else:
                        val_c = st.number_input(f"Per. {t+1}", key=f"cost_val_{i}_{t}", value=0.0)
                    costos_sin_igv[t] -= abs(val_c)
                    costos_con_igv[t] -= abs(val_c) * (1 + tasa_igv) if (igv_costo and hay_igv) else abs(val_c)

    # ── TABLA FORMATO OFICIAL ─────────────────────────────────────
    st.divider()
    st.subheader("📊 Módulo de Costos, Inversión y Liquidación")

    col_headers = ["Concepto", "0"] + [str(t+1) for t in range(n)] + ["Liq."]

    def fmt_val(v):
        if isinstance(v, str):
            return v
        return f"{v:,.0f}" if abs(v) > 0.001 else ""

    def fila(concepto, vals):
        return [concepto] + [fmt_val(v) for v in vals]

    kl_año0 = cambios_kl_lista[0]
    kl_liq  = kl_recuperado
    nombre_activo_liq = next((a["nombre"] for a in activos if liq_sin_igv > 0), "Activo")

    # BLOQUE SIN IGV
    rows = []
    rows.append(fila("COSTOS SIN IGV",          [""] * (n+2)))
    rows.append(fila("H. Inversión y liquidación",
        [-inv_sin_igv_p0 + kl_año0] + [0.0]*n + [liq_sin_igv + kl_liq]))
    rows.append(fila(f"  {nombre_activo_liq}",
        [-inv_sin_igv_p0]            + [0.0]*n + [liq_sin_igv]))
    rows.append(fila("  Cambio en KL",
        [kl_año0]                    + [0.0]*n + [kl_liq]))
    rows.append(fila("I. Costos",
        [0.0] + costos_sin_igv + [0.0]))
    for i in range(int(num_costos)):
        nom     = st.session_state.get(f"cost_nom_{i}", f"Costo {i+1}")
        inf_c   = st.session_state.get(f"cost_inf_{i}", False)
        val_base = abs(st.session_state.get(f"cost_val_{i}_0", 0.0))
        vc = []
        for t in range(n):
            if inf_c and t > 0 and inflacion > 0:
                vc.append(-val_base * (1 + inflacion) ** t)
            else:
                vc.append(-abs(st.session_state.get(f"cost_val_{i}_{t}", 0.0)))
        rows.append(fila(f"  {nom}", [0.0] + vc + [0.0]))
    rows.append(fila("N. Total sin IGV (H+I)",
        [-inv_sin_igv_p0 + kl_año0] + costos_sin_igv + [liq_sin_igv + kl_liq]))

    # SEPARADOR
    rows.append([""] * len(col_headers))

    # BLOQUE CON IGV
    rows.append(fila("COSTOS CON IGV",              [""] * (n+2)))
    rows.append(fila("O. Inversión y liquidación (×1.19)",
        [-inv_con_igv_p0 + kl_año0] + [0.0]*n + [liq_con_igv + kl_liq]))
    rows.append(fila(f"  {nombre_activo_liq}",
        [-inv_con_igv_p0]            + [0.0]*n + [liq_con_igv]))
    rows.append(fila("  Cambio en KL",
        [kl_año0]                    + [0.0]*n + [kl_liq]))
    rows.append(fila("P. Costos",
        [0.0] + costos_con_igv + [0.0]))
    for i in range(int(num_costos)):
        nom      = st.session_state.get(f"cost_nom_{i}", f"Costo {i+1}")
        igv_c    = st.session_state.get(f"cost_igv_{i}", False)
        inf_c    = st.session_state.get(f"cost_inf_{i}", False)
        val_base = abs(st.session_state.get(f"cost_val_{i}_0", 0.0))
        vc_con = []
        for t in range(n):
            if inf_c and t > 0 and inflacion > 0:
                v = val_base * (1 + inflacion) ** t
            else:
                v = abs(st.session_state.get(f"cost_val_{i}_{t}", 0.0))
            vc_con.append(-v * (1 + tasa_igv) if (igv_c and hay_igv) else -v)
        rows.append(fila(f"  {nom}", [0.0] + vc_con + [0.0]))
    rows.append(fila("U. Total con IGV (O+P)",
        [-inv_con_igv_p0 + kl_año0] + costos_con_igv + [liq_con_igv + kl_liq]))

    df_mod2 = pd.DataFrame(rows, columns=col_headers)
    st.dataframe(df_mod2, use_container_width=True, hide_index=True)

    try:
        buf_xl = io.BytesIO()
        with pd.ExcelWriter(buf_xl, engine="openpyxl") as writer:
            df_mod2.to_excel(writer, sheet_name="Módulo 2", index=False)
        buf_xl.seek(0)
        st.download_button("⬇️ Descargar Módulo 2 en Excel", data=buf_xl,
                           file_name="modulo2_inversion_costos.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except ImportError:
        st.warning("Agrega openpyxl>=3.1.0 al requirements.txt para exportar a Excel.")

# ══════════════════════════════════════════════
# TAB IGV — MÓDULO DE IGV
# ══════════════════════════════════════════════
with tab_igv:
    if hay_igv:
        st.subheader("3. Módulo de IGV")
        pago_igv, igv_detalle = calcular_modulo_igv(
            n, ingresos_sin_igv_efectivos, ingresos_con_igv,
            costos_sin_igv, costos_con_igv,
            inv_sin_igv_p0, inv_con_igv_p0,
            liq_sin_igv, liq_con_igv, tasa_igv,
            igv_diferido=igv_diferido
        )
        col_igv = ["Concepto", "0"] + [str(t+1) for t in range(n)] + ["Liq."]
        V = igv_detalle["V"]
        W = igv_detalle["W"]
        X = igv_detalle["X"]
        Y = igv_detalle["Y"]
        Z = igv_detalle["Z"]

        def fv(v):
            return f"{v:,.0f}" if abs(v) > 0.001 else ""

        RC = igv_detalle.get("RC")
        if igv_diferido and RC is not None:
            rows_igv = [
                ["V. IGV ingresos (débito fiscal)"]         + [fv(v) for v in V],
                ["W. IGV egresos pagados"]                  + [fv(v) for v in W],
                ["Reconocimiento crédito tributario (t-1)"] + [fv(v) for v in RC],
                ["Z. Pago de IGV"]                          + [fv(v) for v in Z],
            ]
            st.dataframe(pd.DataFrame(rows_igv, columns=col_igv),
                         use_container_width=True, hide_index=True)
            st.caption("V = débito fiscal. W = crédito generado en el período. "
                       "RC = crédito reconocido (generado el período anterior). "
                       "Z = V + RC (pago efectivo al fisco).")
        else:
            rows_igv = [
                ["V. IGV ingresos (débito fiscal)"]  + [fv(v) for v in V],
                ["W. IGV egresos (crédito fiscal)"]  + [fv(v) for v in W],
                ["X. Diferencia"]                    + [fv(v) for v in X],
                ["Y. Crédito tributario acumulado"]  + [fv(v) for v in Y],
                ["Z. Pago de IGV"]                   + [fv(v) for v in Z],
            ]
            st.dataframe(pd.DataFrame(rows_igv, columns=col_igv),
                         use_container_width=True, hide_index=True)
            st.caption("V = débito fiscal (IGV cobrado). W = crédito fiscal (IGV pagado en compras). "
                       "X = V + W. Y = crédito acumulado cuando X > 0. Z = pago efectivo al fisco.")
    else:
        pago_igv    = [0.0] * (n + 2)
        igv_detalle = None
        st.info("El IGV no está activado en este proyecto. Actívalo desde el sidebar.")

# ══════════════════════════════════════════════
# TAB 3 — FINANCIAMIENTO
# ══════════════════════════════════════════════
with tab3:
    if hay_financiamiento:
        st.subheader("Módulo de Financiamiento Neto")
        c1, c2, c3, c4 = st.columns(4)
        with c1: prestamo         = st.number_input("Monto del préstamo",        value=0.0, min_value=0.0, key="_meta_prestamo")
        with c2: tasa_prestamo    = st.number_input("Tasa de interés anual (%)", value=12.0, key="_meta_tasa_prestamo_w") / 100
        with c3: periodos_prestamo= st.number_input("Períodos de amortización",  value=n, min_value=1, max_value=n, key="_meta_periodos_prestamo")
        with c4: anos_gracia      = st.number_input("Años de gracia",            value=0, min_value=0, max_value=n-1, key="_meta_anos_gracia",
                                                    help="Períodos iniciales sin amortización ni intereses")

        ffn_data = calcular_ffn(prestamo, tasa_prestamo, int(periodos_prestamo), tasa_ir, inflacion, anos_gracia=int(anos_gracia))

        # ── Tabla transpuesta estilo libro de texto ───────────────
        def fmt_ffn(v, vacio_si_cero=True):
            if vacio_si_cero and abs(v) < 0.005:
                return ""
            return f"{v:,.0f}"

        per_cols = [""] + ["0"] + [str(t+1) for t in range(n)]

        # Construir valores por fila: [concepto, per0, per1, …, pern]
        amort  = ffn_data["amortizacion"]
        int_n  = ffn_data["intereses_nominales"]
        esc_n  = ffn_data["escudo_nominal"]
        ffn_r  = ffn_data["ffn_real"]

        filas_ffn = [
            ["AA. Principal"]             + [fmt_ffn(prestamo, False)] + [""] * n,
            ["AB. Amortización"]          + [""] + [fmt_ffn(-abs(v)) for v in amort],
            ["AC. Intereses"]             + [""] + [fmt_ffn(-abs(v)) for v in int_n],
            ["AD. Escudo tributario"]     + [""] + [fmt_ffn(v)       for v in esc_n],
            ["**AE. Financiamiento neto**"] + [fmt_ffn(ffn_r[t], False) for t in range(n+1)],
        ]

        df_ffn = pd.DataFrame(filas_ffn, columns=per_cols)

        def estilo_ffn(df):
            styles = pd.DataFrame("", index=df.index, columns=df.columns)
            styles.iloc[4, :] = "font-weight: bold"
            return styles

        st.dataframe(
            df_ffn.style.apply(estilo_ffn, axis=None),
            use_container_width=True,
            hide_index=True,
        )

        # ── Notas al pie ──────────────────────────────────────────
        st.divider()
        per_amort = int(periodos_prestamo)
        n_repago = per_amort - int(anos_gracia)
        st.caption(f"(B) AB = {prestamo:,.0f} / {n_repago} (períodos de repago)." +
                   (f"  *{int(anos_gracia)} año(s) de gracia sin amortización ni intereses.*" if int(anos_gracia) > 0 else ""))
        st.caption(f"(C) AC = -{tasa_prestamo:.0%} × Remanente deuda (0 durante gracia).")
        st.caption(f"(D) AD = -{int(tasa_ir*100)/100:.1f} × AC.")
        st.caption("(E) AE = AA + AB + AC + AD.")
        intereses_reales = ffn_data["intereses_reales"]
        escudo_real      = ffn_data["escudo_real"]
        ffn_real         = ffn_data["ffn_real"]
    else:
        prestamo          = 0.0
        intereses_reales  = [0.0] * n
        escudo_real       = [0.0] * n
        ffn_real          = [0.0] * (n + 1)
        st.info("No hay financiamiento externo en este proyecto.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — RESULTADOS (Flujo de Caja) - VERSIÓN CORREGIDA
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("6. Flujo de Caja")
    
    # =========================================================================
    # 1. ASEGURAR QUE TODAS LAS VARIABLES EXISTEN
    # =========================================================================
    
    # Asegurar que ingresos_con_isc existe
    if 'ingresos_con_isc' not in dir():
        ingresos_con_isc = [0.0] * n
    
    # Asegurar que pago_igv existe
    if hay_igv and 'pago_igv' not in dir():
        pago_igv = [0.0] * (n + 2)
    elif not hay_igv:
        pago_igv = [0.0] * (n + 2)
    
    # Asegurar que ffn_real existe
    if hay_financiamiento and 'ffn_real' not in dir():
        ffn_real = [0.0] * (n + 1)
    elif not hay_financiamiento:
        ffn_real = [0.0] * (n + 1)
    
    # Asegurar que escudo_real existe
    if hay_financiamiento and 'escudo_real' not in dir():
        escudo_real = [0.0] * n
    elif not hay_financiamiento:
        escudo_real = [0.0] * n
    
    # Asegurar que intereses_reales existe
    if hay_financiamiento and 'intereses_reales' not in dir():
        intereses_reales = [0.0] * n
    elif not hay_financiamiento:
        intereses_reales = [0.0] * n
    
    # =========================================================================
    # 2. CALCULAR IR DEL FCE
    # =========================================================================
    
    if hay_isc:
        ir_fce, base_fce = calcular_ir_fce(
            n, 
            ingresos_sin_igv_efectivos,
            costos_sin_igv,
            dep_por_periodo, 
            tasa_ir, 
            permite_perdidas=False
        )
    else:
        ir_fce, base_fce = calcular_ir_fce(
            n, ingresos_sin_igv_efectivos, costos_sin_igv,
            dep_por_periodo, tasa_ir, permite_perdidas
        )
    
    # Ajuste por escudo tributario si hay financiamiento
    if hay_financiamiento:
        pyg_data = calcular_pyg(
            n, ingresos_sin_igv_efectivos, costos_sin_igv,
            dep_por_periodo, intereses_reales, tasa_ir, permite_perdidas
        )
        ir_pyg = [pyg_data[t]["ir"] for t in range(n)]
        ir_fce = [ir_pyg[t] - escudo_real[t] for t in range(n)]
    
    # =========================================================================
    # 3. FUNCIÓN DE FORMATEO
    # =========================================================================
    
    def fmt(v):
        if abs(v) < 0.5:
            return ""
        return f"{v:,.0f}"
    
    # =========================================================================
    # 4. CONSTRUIR FILA A: FC INGRESOS
    # =========================================================================
    
    if hay_isc:
        A = ingresos_fc[:n]
    elif hay_igv:
        A = ingresos_con_igv[:n]
    else:
        A = ingresos_sin_igv_efectivos[:n]
    
    # Asegurar longitud n
    while len(A) < n:
        A.append(0.0)
    
    # IGV de la venta de maquinaria en liquidación
    A_liq = -(liq_con_igv - liq_sin_igv) if hay_igv else 0.0
    
    # =========================================================================
    # 5. CONSTRUIR FILA B: INVERSIÓN Y LIQUIDACIÓN (CON DESGLOSE)
    # =========================================================================
    
    # B1. Maquinaria
    maq_inv_0 = -(inv_con_igv_p0 if hay_igv else inv_sin_igv_p0)
    maq_liq = (liq_con_igv if hay_igv else liq_sin_igv)
    
    # B2. Instalación (inversiones adicionales en años operativos)
    instalacion = []
    for t in range(n):
        val = -inv_adicional.get(t, 0.0)
        instalacion.append(val)
    
    # B3. Capital de trabajo
    KL_0 = cambios_kl_lista[0] if len(cambios_kl_lista) > 0 else 0.0
    KL_operativos = []
    for t in range(n):
        val = cambios_kl_lista[t+1] if t+1 < len(cambios_kl_lista) else 0.0
        KL_operativos.append(val)
    KL_liq = kl_recuperado
    
    # Total B
    B_0 = maq_inv_0 + KL_0
    B_operativos = []
    for t in range(n):
        B_operativos.append(instalacion[t] + KL_operativos[t])
    B_liq = maq_liq + KL_liq
    
    # =========================================================================
    # 6. CONSTRUIR FILA C: FC COSTOS
    # =========================================================================
    
    if hay_igv:
        C = costos_con_igv[:n]
    else:
        C = costos_sin_igv[:n]
    
    while len(C) < n:
        C.append(0.0)
    
    # =========================================================================
    # 7. CONSTRUIR FILA D: PAGO IGV
    # =========================================================================
    
    if hay_igv:
        D_0 = pago_igv[0] if len(pago_igv) > 0 else 0.0
        D_operativos = []
        for t in range(n):
            val = pago_igv[t+1] if t+1 < len(pago_igv) else 0.0
            D_operativos.append(val)
        D_liq = pago_igv[-1] if len(pago_igv) > n+1 else 0.0
    else:
        D_0 = 0.0
        D_operativos = [0.0] * n
        D_liq = 0.0
    
    # =========================================================================
    # 8. CONSTRUIR FILA E: PAGO ISC
    # =========================================================================
    
    if hay_isc:
        E_0 = 0.0
        E_operativos = []
        for t in range(n):
            val = -ingresos_con_isc[t] if t < len(ingresos_con_isc) else 0.0
            E_operativos.append(val)
        E_liq = 0.0
    else:
        E_0 = 0.0
        E_operativos = [0.0] * n
        E_liq = 0.0
    
    # =========================================================================
    # 9. CONSTRUIR FILA F: IMPUESTO A LA RENTA
    # =========================================================================
    
    F_0 = 0.0
    F_operativos = []
    for t in range(n):
        val = ir_fce[t] if t < len(ir_fce) else 0.0
        F_operativos.append(val)
    
    # IR por venta de activo en liquidación
    utilidad_liq = liq_sin_igv
    for a in activos:
        if a.get("deprecia", False):
            valor_libros = a.get("valor_dep", a.get("valor", 0))
            utilidad_liq -= valor_libros
    F_liq = -tasa_ir * max(utilidad_liq, 0.0) if utilidad_liq > 0 else 0.0
    
    # =========================================================================
    # 10. CONSTRUIR FILA G: FCE
    # =========================================================================
    
    G_0 = B_0 + D_0 + E_0 + F_0
    G_operativos = []
    for t in range(n):
        g = A[t] + B_operativos[t] + C[t] + D_operativos[t] + E_operativos[t] + F_operativos[t]
        G_operativos.append(g)
    G_liq = A_liq + B_liq + D_liq + E_liq + F_liq
    
    # =========================================================================
    # 11. CONSTRUIR FILA H: FC FINANCIAMIENTO NETO
    # =========================================================================
    
    if hay_financiamiento:
        H_0 = ffn_real[0] if len(ffn_real) > 0 else 0.0
        H_operativos = []
        for t in range(n):
            val = ffn_real[t+1] if t+1 < len(ffn_real) else 0.0
            H_operativos.append(val)
        H_liq = 0.0
    else:
        H_0 = 0.0
        H_operativos = [0.0] * n
        H_liq = 0.0
    
    # =========================================================================
    # 12. CONSTRUIR FILA I: FCF
    # =========================================================================
    
    I_0 = G_0 + H_0
    I_operativos = []
    for t in range(n):
        I_operativos.append(G_operativos[t] + H_operativos[t])
    I_liq = G_liq + H_liq
    
    # =========================================================================
    # 13. ARMAR TABLA
    # =========================================================================
    
    # Definir columnas
    if n == 3:
        col_names = ["", "0", "1", "2", "3", "Liq."]
    else:
        col_names = ["", "0"] + [str(i+1) for i in range(n)] + ["Liq."]
    
    def col_row(val_0, val_list, val_liq):
        row = [fmt(val_0)]
        for i in range(n):
            row.append(fmt(val_list[i] if i < len(val_list) else 0.0))
        row.append(fmt(val_liq))
        return row
    
    # Construir filas
    filas = []
    
    # A
    filas.append(["A. FC ingresos (12)"] + col_row(0.0, A, A_liq))
    
    # B con desglose
    filas.append(["B. FC de inversión y liquidación"] + col_row(B_0, B_operativos, B_liq))
    filas.append(["  Maquinaria (13)"] + col_row(maq_inv_0, [0.0]*n, maq_liq))
    filas.append(["  Instalación de maquinaria (13)"] + col_row(0.0, instalacion, 0.0))
    filas.append(["  Cambio en capital de trabajo"] + col_row(KL_0, KL_operativos, KL_liq))
    
    # C
    filas.append(["C. FC de costos"] + col_row(0.0, C, 0.0))
    
    # D
    if hay_igv:
        filas.append(["D. Pago de IGV"] + col_row(D_0, D_operativos, D_liq))
    
    # E
    if hay_isc:
        filas.append(["E. Pago de ISC"] + col_row(E_0, E_operativos, E_liq))
    
    # F
    filas.append(["F. Impuesto a la renta (14)"] + col_row(F_0, F_operativos, F_liq))
    
    # G
    filas.append(["G. Flujo de caja económico (15)"] + col_row(G_0, G_operativos, G_liq))
    
    # H
    if hay_financiamiento:
        filas.append(["H. FC financiamiento neto"] + col_row(H_0, H_operativos, H_liq))
    
    # I
    filas.append(["I. Flujo de caja financiero (16)"] + col_row(I_0, I_operativos, I_liq))
    
    # Mostrar tabla
    df_fc = pd.DataFrame(filas, columns=col_names[:len(filas[0])])
    st.dataframe(df_fc, use_container_width=True, hide_index=True)
    
    # =========================================================================
    # 14. NOTAS AL PIE
    # =========================================================================
    st.divider()
    st.caption("(12) Incluye IGV e ISC.")
    if hay_igv:
        st.caption("(13) Incluye IGV.")
    if hay_isc:
        st.caption("(14) F = (A/1.39 + Planillas + Insumos/1.19 - Depreciación) * 0.3. Impuesto (FCE) + Escudo tributario = Impuesto (P y G).")
    st.caption("(15) G = A + B + C + D" + (" + E" if hay_isc else "") + " + F.")
    st.caption("(16) I = G + H.")
    
    # =========================================================================
    # 15. INDICADORES
    # =========================================================================
    st.divider()
    st.subheader("📌 Indicadores")
    
    fce_total = [G_0] + G_operativos + [G_liq]
    fcf_total = [I_0] + I_operativos + [I_liq]
    
    van_fce = calcular_van(fce_total, tasa_descuento)
    van_fcf = calcular_van(fcf_total, tasa_descuento)
    
    try:
        tir_fce = calcular_tir(fce_total) * 100
    except:
        tir_fce = float("nan")
    try:
        tir_fcf = calcular_tir(fcf_total) * 100
    except:
        tir_fcf = float("nan")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("VAN (FCE)", f"{van_fce:,.2f}")
    with col2: st.metric("TIR (FCE)", f"{tir_fce:.2f}%")
    with col3: st.metric("VAN (FCF)", f"{van_fcf:,.2f}")
    with col4: st.metric("TIR (FCF)", f"{tir_fcf:.2f}%")
    # =========================================================================
    # 5. INDICADORES VAN / TIR
    # =========================================================================
    st.divider()
    st.subheader("📌 Indicadores")
    
    fce_total = [G_0] + G_operativos + [G_liq]
    fcf_total = [I_0] + I_operativos + [I_liq]
    
    van_fce = calcular_van(fce_total, tasa_descuento)
    van_fcf = calcular_van(fcf_total, tasa_descuento)
    
    try:
        tir_fce = calcular_tir(fce_total) * 100
    except:
        tir_fce = float("nan")
    try:
        tir_fcf = calcular_tir(fcf_total) * 100
    except:
        tir_fcf = float("nan")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1: st.metric("VAN (FCE)", f"{van_fce:,.2f}")
    with col2: st.metric("TIR (FCE)", f"{tir_fce:.2f}%")
    with col3: st.metric("VAN (FCF)", f"{van_fcf:,.2f}")
    with col4: st.metric("TIR (FCF)", f"{tir_fcf:.2f}%")
# ══════════════════════════════════════════════
# TAB 5 — PyG  (va entre Financiamiento y Resultados)
# ══════════════════════════════════════════════
with tab5:
    st.subheader("5. Estado de Pérdidas y Ganancias")

    pyg = calcular_pyg(n, ingresos_pyg, costos_sin_igv, dep_por_periodo,
                       intereses_reales, tasa_ir, permite_perdidas)

    # ── Etiquetas de referencia ───────────────────────────────────
    # Las letras de referencia siguen la convención del libro (AF, AG, …)
    ref_ing   = "AF"
    ref_cos   = "AG"
    ref_dep   = "AH"
    ref_int   = "AI"
    ref_ub    = "AJ"
    ref_ir    = "AK"
    ref_un    = "AL"

    def fmt_pyg(v):
        """Formatea número: positivos sin signo, negativos con signo."""
        if abs(v) < 0.005:
            return ""
        return f"{v:,.0f}"

    # ── Construcción de la tabla transpuesta ─────────────────────
    # Columnas: Concepto | 1 | 2 | … | n
    cols_pyg = [""] + [str(r["periodo"]) for r in pyg]

    filas_pyg = [
        [f"{ref_ing}. Ingresos"]            + [fmt_pyg(r["ventas"])            for r in pyg],
        [f"{ref_cos}. Costos de operación"] + [fmt_pyg(r["costos_operativos"]) for r in pyg],
        [f"{ref_dep}. Depreciación"]        + [fmt_pyg(r["depreciacion"])       for r in pyg],
        [f"{ref_int}. Intereses"]           + [fmt_pyg(r["intereses"])          for r in pyg],
        [f"**{ref_ub}. Utilidad bruta**"]   + [fmt_pyg(r["utilidad_bruta"])     for r in pyg],
        [f"**{ref_ir}. Impuesto a la renta ({int(tasa_ir*100)}%)**"]
                                            + [fmt_pyg(r["ir"])                 for r in pyg],
        [f"**{ref_un}. Utilidad neta**"]    + [fmt_pyg(r["utilidad_neta"])      for r in pyg],
    ]

    df_pyg = pd.DataFrame(filas_pyg, columns=cols_pyg)

    # Estilo: negrita en filas de totales
    def estilo_pyg(df):
        bold_rows = {4, 5, 6}   # índices 0-based de AJ, AK, AL
        styles = pd.DataFrame("", index=df.index, columns=df.columns)
        for idx in bold_rows:
            styles.iloc[idx, :] = "font-weight: bold"
        return styles

    st.dataframe(
        df_pyg.style.apply(estilo_pyg, axis=None),
        use_container_width=True,
        hide_index=True,
    )

    # ── Notas al pie (estilo libro de texto) ─────────────────────
    st.divider()

    # Detectar fórmula de depreciación del primer activo que deprecia
    act_dep = next((a for a in activos if a.get("deprecia", False)), None)
    if act_dep:
        v_dep  = act_dep["valor_dep"]
        vrc    = act_dep["valor_residual_contable"]
        vu     = act_dep["vida_util"]
        dep_anual = (v_dep - vrc) / vu
        nota_dep = (
            f"({ref_dep[1]}) {ref_dep} = "
            f"({v_dep:,.0f} - {vrc:,.0f}) / {vu} = {dep_anual:,.0f}."
        )
    else:
        nota_dep = f"({ref_dep[1]}) {ref_dep} = depreciación lineal de los activos."

    notas = [
        f"({ref_ing[1]}) {ref_ing} = F.   *(Ingresos del módulo de ingresos)*",
        f"({ref_cos[1]}) {ref_cos} = I.   *(Costos operativos sin IGV)*",
        nota_dep,
        f"({ref_int[1]}) {ref_int} = AC.  *(Intereses del módulo de financiamiento)*",
        f"({ref_ub[1]}) {ref_ub} = {ref_ing} + {ref_cos} + {ref_dep} + {ref_int}.",
        f"({ref_ir[1]}) {ref_ir} = -{int(tasa_ir*100)/100} × {ref_ub}.",
        f"({ref_un[1]}) {ref_un} = {ref_ub} + {ref_ir}.",
    ]
    for nota in notas:
        st.caption(nota)

    st.info("💡 El IR del PyG difiere del IR del FCE cuando hay financiamiento (escudo tributario).")
