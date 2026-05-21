# 📊 Constructor de Flujo de Caja

Motor automático para construcción de flujos de caja en Evaluación Privada de Proyectos.

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

```bash
streamlit run app.py
```

## Módulos incluidos

1. **Ingresos** — precio × cantidad, con/sin inflación, ventas al crédito (CC)
2. **Inversión & Costos** — activos, depreciación línea recta, capital de trabajo
3. **IGV** — crédito tributario, diferencia ingresos/egresos, liquidación
4. **Financiamiento** — amortización fija, intereses al rebatir, escudo tributario
5. **FCE y FCF** — con deflactación si hay inflación
6. **PyG** — con depreciación e intereses reales
7. **Indicadores** — VAN y TIR para FCE y FCF

## Opciones configurables

- ✅ IGV (tasa configurable)
- ✅ Inflación (corrección FFN automática)
- ✅ Financiamiento con deuda
- ✅ Ventas al crédito (cuentas por cobrar)
- ✅ Pérdidas tributarias acumulables o no
- ✅ Múltiples productos y activos
- ✅ Inversiones en períodos > 0
