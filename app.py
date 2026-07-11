"""
Paviflex Logistics Calculator — Web App
========================================
Sube un presupuesto PDF y obtén la logística completa.
"""

import streamlit as st
import tempfile
import os

from engine.logistica import load_products, extract_text, parse_products, calcular


st.set_page_config(page_title="Paviflex Logistics", page_icon="🚛", layout="centered")

st.markdown("""
<style>
    .main-header { text-align: center; padding: 1rem 0; }
    .metric-card { background: #f0f2f6; border-radius: 10px; padding: 15px; text-align: center; }
    .metric-value { font-size: 28px; font-weight: bold; color: #1f77b4; }
    .metric-label { font-size: 12px; color: #666; text-transform: uppercase; }
    .pallet-line { font-family: monospace; font-size: 13px; }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">', unsafe_allow_html=True)
st.image("https://paviflex.es/wp-content/uploads/2022/07/logo-paviflex-1.png", width=250)
st.title("🚛 Calculadora Logística")
st.markdown("Sube un presupuesto PDF y obtén la logística completa: **pallets, pesos, volumen**")
st.markdown('</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### ℹ️ Cómo funciona")
    st.markdown("""
    1. Sube un **PDF de presupuesto** de Paviflex
    2. El sistema extrae los productos y cantidades
    3. Cruza los datos con la base de producto
    4. Calcula: pallets, pesos, volumen
    """)
    st.markdown("---")
    st.markdown("### 📁 Productos soportados")
    st.caption("36 productos en base de datos")
    st.caption("FITNESS · CONFORTSONIC · TURFLEX")
    st.caption("BASICFLEX · EVA MATS · TATAMI · ACTION")
    st.markdown("---")
    with st.spinner("Cargando base de datos..."):
        products_db = load_products()
    st.caption(f"✅ {len(products_db)} productos cargados")

# Upload
uploaded = st.file_uploader("Selecciona un presupuesto PDF", type=['pdf'])

if uploaded is not None:
    st.info(f"📄 Procesando: **{uploaded.name}**")

    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        tmp.write(uploaded.getvalue())
        tmp_path = tmp.name

    try:
        with st.status("🔍 Analizando presupuesto...") as status:
            status.update(label="📄 Extrayendo texto...")
            text = extract_text(tmp_path)
            status.update(label="🔎 Identificando productos...")
            parsed = parse_products(text, products_db)
            if not parsed:
                st.error("❌ No se pudieron identificar productos en el PDF.")
                st.stop()
            status.update(label="🧮 Calculando logística...")
            logistica = calcular(parsed)
            status.update(label="✅ ¡Completado!", state="complete")

        st.markdown("---")

        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{logistica["total_pallets"]}</div><div class="metric-label">BULKS</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{logistica["peso_neto_total"]:,} kg</div><div class="metric-label">NET WEIGHT</div></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{logistica["peso_bruto"]:,} kg</div><div class="metric-label">GROSS WEIGHT</div></div>', unsafe_allow_html=True)
        with col4:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{logistica["volumen_total"]} m³</div><div class="metric-label">VOLUMEN</div></div>', unsafe_allow_html=True)

        # Productos no reconocidos
        if logistica['productos_sin_referencia']:
            st.warning("⚠️ **Productos no reconocidos** (revisar manualmente):")
            for p in logistica['productos_sin_referencia']:
                st.caption(f"• {p}")

        # Tabla de productos
        st.markdown("### 📋 Detalle por producto")
        import pandas as pd
        df = pd.DataFrame([{
            'Producto': r['producto'],
            'Cantidad': f"{r['cantidad']:.0f} {r['unidad']}",
            'Planchas': r['num_planchas'],
            'Peso (kg)': f"{r['peso_neto_kg']:,.1f}",
            'Pallets': r['pallets'],
        } for r in logistica['resultados']])
        st.dataframe(df, width='stretch', hide_index=True)

        # Pallets
        st.markdown("### 📦 Distribución de pallets")
        for p in logistica['pallets_detalle']:
            st.markdown(f'📦 {p}')

        # Código para copiar
        st.markdown("### 📋 Para bildu.com")
        copy_text = f"BULKS:             {logistica['total_pallets']}"
        for p in logistica['pallets_detalle']:
            copy_text += f"\n  * {p}"
        copy_text += f"\nNET WEIGHT:        {logistica['peso_neto_total']} kg"
        copy_text += f"\nGROSS WEIGHT:      {logistica['peso_bruto']} kg"
        copy_text += f"\nVOLUME:            {logistica['volumen_total']} m³"
        if logistica['productos_sin_referencia']:
            copy_text += "\n\n⚠️ Productos sin referencia:"
            for p in logistica['productos_sin_referencia']:
                copy_text += f"\n  • {p}"

        st.code(copy_text, language="text")
        st.info("💡 Selecciona el texto gris de arriba y cópialo (Cmd+C / Ctrl+C) para pegarlo en bildu.com")

    except Exception as e:
        st.error(f"❌ Error: {e}")
        st.exception(e)
    finally:
        try: os.unlink(tmp_path)
        except: pass

else:
    st.markdown("---")
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown("#### 1️⃣\nSube un PDF\n\nPresupuesto de Paviflex")
    with c2: st.markdown("#### 2️⃣\nCalculamos\n\nPesos, pallets, volumen")
    with c3: st.markdown("#### 3️⃣\nCopia el resultado\n\nDirecto a bildu.com")
    st.markdown("---")
    st.caption("Paviflex Logistics Calculator v1.0")
