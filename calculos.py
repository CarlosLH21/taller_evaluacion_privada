"""
Motor financiero - Evaluación Privada de Proyectos
Construcción del Flujo de Caja
"""

import numpy as np


# ─────────────────────────────────────────────
# MÓDULO 1: INGRESOS
# ─────────────────────────────────────────────

def calcular_ingresos(periodos, productos, igv=0.0, inflacion=0.0):
    """
    productos: lista de dicts con keys:
        - nombre
        - precio_real
        - cantidades: lista por período
    Retorna ingresos sin IGV y con IGV por período
    """
    n = periodos
    ingresos_sin_igv = [0.0] * n
    ingresos_con_igv = [0.0] * n

    for p in productos:
        precio_real = p["precio_real"]
        cantidades = p["cantidades"]  # lista de n elementos
        for t in range(n):
            factor = (1 + inflacion) ** (t + 1) if inflacion > 0 else 1.0
            precio_nominal = precio_real * factor
            ingreso = precio_nominal * cantidades[t]
            ingresos_sin_igv[t] += ingreso
            ingresos_con_igv[t] += ingreso * (1 + igv)

    return ingresos_sin_igv, ingresos_con_igv


def calcular_ingresos_con_credito(periodos, ventas_efectivo, cuentas_por_cobrar):
    """
    Para proyectos con ventas al crédito (IB2).
    ventas_efectivo: lista de n elementos
    cuentas_por_cobrar: lista de n elementos (CC al final de cada período)
    Retorna ingresos efectivos de caja por período
    """
    n = periodos
    ingresos = []
    for t in range(n):
        cc_anterior = cuentas_por_cobrar[t - 1] if t > 0 else 0.0
        ingresos.append(ventas_efectivo[t] + cc_anterior)
    return ingresos


# ─────────────────────────────────────────────
# MÓDULO 2: INVERSIÓN Y CAPITAL DE TRABAJO
# ─────────────────────────────────────────────

def calcular_activos(activos, igv=0.0):
    """
    activos: lista de dicts con keys:
        - nombre
        - valor          (sin IGV)
        - periodo_compra (0 = inversión inicial)
        - deprecia       (bool)
        - vida_util      (años, solo si deprecia)
        - valor_residual (valor de venta en liquidación, None = valor libros)
        - tiene_igv      (bool, si la compra tiene IGV)
    Retorna dict con inversión por período y datos para depreciación/liquidación
    """
    return activos  # se procesa en app.py para mayor flexibilidad


def calcular_depreciacion(activos, periodos):
    """
    Línea recta. Solo activos que deprecian.
    Retorna depreciación total por período y valor en libros al final.
    """
    n = periodos
    dep_por_periodo = [0.0] * n

    for a in activos:
        if not a.get("deprecia", False):
            continue
        # valor_dep permite registrar activos cedidos sin costo (costo oportunidad)
        # cuyo valor de caja es 0 pero tienen base depreciable real
        valor = a.get("valor_dep", a["valor"])
        vida = a.get("vida_util", periodos)
        v_residual_contable = a.get("valor_residual_contable", 0.0)
        dep_anual = (valor - v_residual_contable) / vida
        periodo_compra = a.get("periodo_compra", 0)

        for t in range(n):
            # Solo deprecia desde el período siguiente a la compra
            if t >= periodo_compra:
                dep_por_periodo[t] += dep_anual

    return dep_por_periodo


def calcular_capital_trabajo(periodos, ventas_totales, porcentaje=0.10, recupera_al_final=True):
    """
    Capital de trabajo = porcentaje * incremento en ventas.
    Período 0: porcentaje * ventas_totales[0]
    Períodos siguientes: porcentaje * (ventas[t] - ventas[t-1])
    Retorna lista con cambios en KL (negativos = salida, positivo en liq.)
    """
    n = periodos
    kl = []

    # Período 0
    kl_inicial = -porcentaje * ventas_totales[0]
    kl.append(kl_inicial)

    # Períodos 1..n-1
    for t in range(1, n):
        delta = -porcentaje * (ventas_totales[t] - ventas_totales[t - 1])
        kl.append(delta)

    # Liquidación: recuperación total
    kl_total = abs(sum(kl))
    return kl, kl_total


# ─────────────────────────────────────────────
# MÓDULO 3: IGV
# ─────────────────────────────────────────────

def calcular_modulo_igv(periodos, ingresos_sin_igv, ingresos_con_igv,
                         costos_sin_igv, costos_con_igv,
                         inversion_sin_igv_p0, inversion_con_igv_p0,
                         liquidacion_sin_igv, liquidacion_con_igv,
                         igv_tasa, igv_diferido=False):
    """
    Retorna (pago_igv, detalle) donde:
      pago_igv : lista n+2 [año0, p1..pn, liq] pago efectivo al fisco (negativo)
      detalle  : dict V, W, RC, Z para tabla formato oficial

    igv_diferido=True: el crédito fiscal de egresos se reconoce un año después
    del pago (como en ejercicio Cervezas de Puno).
    """
    n = periodos

    # V. IGV ingresos = débito fiscal (negativo) [año0=0, p1..pn, liq]
    igv_ingresos  = [-(ingresos_con_igv[t] - ingresos_sin_igv[t]) for t in range(n)]
    igv_liq_monto =  liquidacion_con_igv - liquidacion_sin_igv
    V = [0.0] + igv_ingresos + [-igv_liq_monto]

    # W. IGV egresos pagados (crédito fiscal generado) [año0, p1..pn, liq=0]
    igv_inversion_p0 = inversion_con_igv_p0 - inversion_sin_igv_p0
    igv_egresos_op   = [(abs(costos_con_igv[t]) - abs(costos_sin_igv[t])) for t in range(n)]
    W = [igv_inversion_p0] + igv_egresos_op + [0.0]

    if not igv_diferido:
        # Comportamiento estándar: crédito se aplica en el mismo período
        X = [V[i] + W[i] for i in range(n + 2)]
        Y = [0.0] * (n + 2)
        Z = [0.0] * (n + 2)
        credito_acumulado = 0.0
        for i in range(n + 2):
            if X[i] > 0:
                credito_acumulado += X[i]
                Y[i] = credito_acumulado
            else:
                debe = abs(X[i])
                if credito_acumulado >= debe:
                    credito_acumulado -= debe
                else:
                    Z[i] = -(debe - credito_acumulado)
                    credito_acumulado = 0.0
        detalle = {"V": V, "W": W, "X": X, "Y": Y, "Z": Z, "RC": None}
        return Z, detalle

    else:
        # IGV diferido: crédito fiscal de egresos reconocido un año después
        # RC[i] = W[i-1]  (lo generado el período anterior se reconoce ahora)
        RC = [0.0] * (n + 2)
        for i in range(1, n + 2):
            RC[i] = W[i - 1]

        # Pago IGV = V[i] + RC[i]  (débito - crédito reconocido este período)
        Z = [0.0] * (n + 2)
        for i in range(n + 2):
            neto = V[i] + RC[i]   # V es negativo (débito), RC es positivo (crédito)
            Z[i] = neto if neto < 0 else 0.0  # solo pago si debe al fisco

        detalle = {"V": V, "W": W, "RC": RC, "Z": Z, "X": None, "Y": None}
        return Z, detalle


# ─────────────────────────────────────────────
# MÓDULO 4: IMPUESTO A LA RENTA
# ─────────────────────────────────────────────

def calcular_ir_fce(periodos, ingresos_sin_igv, costos_operativos_sin_igv,
                    depreciacion, tasa_ir=0.30, permite_perdidas=True):
    """
    IR para el FCE (sin intereses).
    Retorna IR por período (negativo) y base imponible.
    """
    n = periodos
    base = []
    ir = []
    perdida_acumulada = 0.0

    for t in range(n):
        utilidad = ingresos_sin_igv[t] - costos_operativos_sin_igv[t] - depreciacion[t]

        if not permite_perdidas:
            # No se pueden acumular pérdidas tributarias
            utilidad = max(utilidad, 0.0)
        else:
            utilidad -= perdida_acumulada
            if utilidad < 0:
                perdida_acumulada = abs(utilidad)
                utilidad = 0.0
            else:
                perdida_acumulada = 0.0

        base.append(utilidad)
        ir.append(-tasa_ir * utilidad)

    return ir, base


def calcular_escudo_tributario(intereses, tasa_ir=0.30):
    """
    Escudo tributario = tasa_ir * intereses (positivo, ahorro fiscal)
    """
    return [tasa_ir * abs(i) for i in intereses]


# ─────────────────────────────────────────────
# MÓDULO 5: FINANCIAMIENTO NETO
# ─────────────────────────────────────────────

def calcular_ffn(prestamo, tasa_interes, periodos, tasa_ir=0.30,
                 inflacion=0.0, tipo_amortizacion="fija", anos_gracia=0):
    """
    Retorna dict con:
        - principal: entrada en período 0
        - amortizacion: lista por período
        - intereses_nominales: lista por período
        - escudo_tributario: lista por período
        - ffn_nominal: lista (incluye período 0)
        - ffn_real: lista deflactada (si hay inflación)

    anos_gracia: períodos iniciales sin amortización ni intereses.
    """
    n = periodos
    g = int(anos_gracia)

    # Durante años de gracia: amort=0, interés=0
    # Después: amortización fija sobre el total de períodos de repago
    n_repago = n - g
    amort_val = prestamo / n_repago if n_repago > 0 else 0.0

    amort_lista = [0.0] * g + [-amort_val] * n_repago

    # Saldo al inicio de cada período
    saldos = []
    saldo = prestamo
    for t in range(n):
        saldos.append(saldo)
        saldo += amort_lista[t]  # amort es negativo, reduce saldo

    # Intereses: 0 durante gracia, normal después
    intereses_nom = []
    for t in range(n):
        if t < g:
            intereses_nom.append(0.0)
        else:
            intereses_nom.append(-tasa_interes * saldos[t])

    escudo = calcular_escudo_tributario(intereses_nom, tasa_ir)

    ffn_nom = [prestamo] + [
        amort_lista[t] + intereses_nom[t] + escudo[t] for t in range(n)
    ]

    # Deflactar si hay inflación
    if inflacion > 0:
        factores = [1.0] + [(1 + inflacion) ** (t + 1) for t in range(n)]
        ffn_real = [ffn_nom[t] / factores[t] for t in range(n + 1)]
        intereses_reales = [intereses_nom[t] / factores[t + 1] for t in range(n)]
        escudo_real = [escudo[t] / factores[t + 1] for t in range(n)]
    else:
        ffn_real = ffn_nom
        intereses_reales = intereses_nom
        escudo_real = escudo

    return {
        "prestamo": prestamo,
        "amortizacion": amort_lista,
        "intereses_nominales": intereses_nom,
        "intereses_reales": intereses_reales,
        "escudo_nominal": escudo,
        "escudo_real": escudo_real,
        "ffn_nominal": ffn_nom,
        "ffn_real": ffn_real,
        "factores": [1.0] + [(1 + inflacion) ** (t + 1) for t in range(n)] if inflacion > 0 else [1.0] * (n + 1),
    }


# ─────────────────────────────────────────────
# MÓDULO 6: FCE y FCF
# ─────────────────────────────────────────────

def calcular_fce(periodos, ingresos, inversion_p0, cambios_kl, kl_recuperado,
                 costos_operativos, depreciacion, ir, pago_igv=None,
                 liquidacion_neta=0.0, inflacion=0.0):
    """
    FCE = Ingresos + Inversión + ΔKL + Costos operativos + IR + Depreciación* + IGV
    *La depreciación se suma de vuelta porque no es salida de caja.
    Retorna FCE por período (lista de n+2: período 0, períodos 1..n, liquidación)
    """
    n = periodos
    fce = []

    # Período 0
    fce_0 = inversion_p0 + cambios_kl[0]
    fce.append(fce_0)

    # Períodos operativos
    for t in range(n):
        igv_t = pago_igv[t + 1] if pago_igv else 0.0
        fce_t = (ingresos[t]
                 + (cambios_kl[t + 1] if t + 1 < len(cambios_kl) else 0.0)
                 + costos_operativos[t]
                 + ir[t])
        # No sumamos depreciación aquí — ya está fuera de los costos operativos
        fce.append(fce_t + igv_t)

    # Liquidación
    igv_liq = pago_igv[-1] if pago_igv else 0.0
    fce_liq = liquidacion_neta + kl_recuperado + igv_liq
    fce.append(fce_liq)

    # Deflactar si hay inflación
    if inflacion > 0:
        factores = [1.0] + [(1 + inflacion) ** (t + 1) for t in range(n)] + [(1 + inflacion) ** (n + 1)]
        fce = [fce[t] / factores[t] for t in range(len(fce))]

    return fce


def calcular_fcf(fce, ffn_real):
    """
    FCF = FCE + FFN (ambos en términos reales)
    """
    # fce tiene n+2 elementos (p0, p1..pn, liq), ffn_real tiene n+1 (p0..pn)
    fcf = []
    for t in range(len(fce)):
        ffn_t = ffn_real[t] if t < len(ffn_real) else 0.0
        fcf.append(fce[t] + ffn_t)
    return fcf


# ─────────────────────────────────────────────
# MÓDULO 7: ESTADO DE PÉRDIDAS Y GANANCIAS
# ─────────────────────────────────────────────

def calcular_pyg(periodos, ingresos_sin_igv, costos_operativos_sin_igv,
                 depreciacion, intereses_reales, tasa_ir=0.30,
                 permite_perdidas=True):
    """
    PyG estándar con intereses (si hay financiamiento).
    Retorna dict con ventas, costos, depreciación, intereses,
    utilidad bruta, IR, utilidad neta por período.
    """
    n = periodos
    resultados = []
    perdida_acumulada = 0.0

    for t in range(n):
        ventas = ingresos_sin_igv[t]
        costos = costos_operativos_sin_igv[t]
        dep = depreciacion[t]
        intereses = intereses_reales[t] if intereses_reales else 0.0

        utilidad_bruta = ventas + costos - dep + intereses  # costos e intereses son negativos

        if not permite_perdidas:
            base = max(utilidad_bruta, 0.0)
        else:
            base = utilidad_bruta - perdida_acumulada
            if base < 0:
                perdida_acumulada = abs(base)
                base = 0.0
            else:
                perdida_acumulada = 0.0

        ir = -tasa_ir * base
        utilidad_neta = base + ir

        resultados.append({
            "periodo": t + 1,
            "ventas": ventas,
            "costos_operativos": costos,
            "depreciacion": -dep,
            "intereses": intereses,
            "utilidad_bruta": utilidad_bruta,
            "ir": ir,
            "utilidad_neta": utilidad_neta,
        })

    return resultados


# ─────────────────────────────────────────────
# INDICADORES: VAN y TIR
# ─────────────────────────────────────────────

def calcular_van(flujo, tasa_descuento):
    """VAN del flujo (lista que incluye período 0)"""
    van = 0.0
    for t, f in enumerate(flujo):
        van += f / (1 + tasa_descuento) ** t
    return van


def calcular_tir(flujo, guess=0.1):
    """TIR por método de Newton-Raphson"""
    tasa = guess
    for _ in range(1000):
        van = sum(f / (1 + tasa) ** t for t, f in enumerate(flujo))
        d_van = sum(-t * f / (1 + tasa) ** (t + 1) for t, f in enumerate(flujo))
        if abs(d_van) < 1e-12:
            break
        tasa_nueva = tasa - van / d_van
        if abs(tasa_nueva - tasa) < 1e-8:
            tasa = tasa_nueva
            break
        tasa = tasa_nueva
    return tasa
