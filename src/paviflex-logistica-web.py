#!/usr/bin/env python3
"""
Paviflex Logistics Calculator — Web App (Streamlit)
====================================================
Arrancar con: streamlit run paviflex-logistica-web.py
"""

import streamlit as st
import sys
import os
import re
import tempfile
import json
from pathlib import Path

# Importar el motor de logistica
PROJECT_DIR = Path.home() / 'Documents' / 'hermes' / 'paviflex-logistica'
sys.path.insert(0, str(PROJECT_DIR / 'src'))

from paviflex_logistica import (
    load_products_from_csv,
    extract_text_from_pdf,
    parse_pdf_products,
    calcular_logistica,
)

load_products = load_products_from_csv
extract_text = extract_text_from_pdf
parse_products = parse_pdf_products
calc_logistica = calcular_logistica


# ── Configuración de página ──
st.set_page_config(
    page_title="Paviflex Logistics",
    page_icon="🚛",
    layout="centered",
)

# ── CSS personalizado ──
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
    }
    .result-table {
        font-size: 14px;
    }
    .metric-card {
        background: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
    }
    .metric-value {
        font-size: 28px;
        font-weight: bold;
        color: #1f77b4;
    }
    .metric-label {
        font-size: 12px;
        color: #666;
        text-transform: uppercase;
    }
    .product-line {
        padding: 8px 0;
        border-bottom: 1px solid #eee;
    }
    .pallet-line {
        font-family: monospace;
        font-size: 13px;
    }
    .success-badge {
        color: #0f5132;
        background: #d1e7dd;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 12px;
    }
    .warning-badge {
        color: #664d03;
        background: #fff3cd;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 12px;
    }
    .footer {
        text-align: center;
        color: #888;
        font-size: 12px;
        padding: 20px 0;
    }
</style>
""", unsafe_allow_html=True)


# ── Cabecera ──
st.markdown('<div class="main-header">', unsafe_allow_html=True)
st.image("https://paviflex.es/wp-content/uploads/2022/07/logo-paviflex-1.png",
         width=250)
st.title("🚛 Calculadora Logística")
st.markdown("Sube un presupuesto PDF y obtén la logística completa")
st.markdown('</div>', unsafe_allow_html=True)


# ── Sidebar con información ──
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
    st.caption("36 productos en base de datos:")
    st.caption("• FITNESS (5-30mm)")
    st.caption("• CONFORTSONIC (10-30mm)")
    st.caption("• TURFLEX, BASICFLEX")
    st.caption("• EVA MATS, TATAMI, ACTION")
    st.caption("• Y más...")

    st.markdown("---")
    st.markdown("### 📤 Para bildu.com")
    st.caption("Usa el botón **Copiar resultado** para pegar la logística en bildu.com")

    # Cargar BD en sidebar
    with st.spinner("Cargando base de datos..."):
        products_db = load_products()
    st.caption(f"✅ {len(products_db)} productos cargados")


# ── Subida de archivo ──
uploaded_file = st.file_uploader(
    "Selecciona un presupuesto PDF",
    type=['pdf'],
    help="Arrastra o selecciona un archivo PDF de Paviflex"
)


# ── Procesamiento ──
if uploaded_file is not None:
    # Mostrar nombre del archivo
    st.info(f"📄 Procesando: **{uploaded_file.name}**")

    # Guardar a temporal
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    try:
        # Extraer texto
        with st.status("🔍 Analizando presupuesto...") as status:
            status.update(label="📄 Extrayendo texto del PDF...")
            text = extract_text(tmp_path)

            status.update(label="🔎 Identificando productos...")
            parsed = parse_products(text, products_db)

            if not parsed:
                st.error("""
                ❌ No se pudieron identificar productos en el PDF.
                
                El formato del PDF puede no ser el esperado. Asegúrate de que sea
                un presupuesto de Paviflex con el formato estándar.
                """)
                st.stop()

            status.update(label="🧮 Calculando logística...")
            logistica = calc_logistica(parsed)
            status.update(label="✅ ¡Cálculo completado!", state="complete")

        # ── Resultados ──
        st.markdown("---")
        st.markdown("## 📊 Resultado logístico")

        # Tarjetas de métricas principales
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{logistica['total_pallets']}</div>
                <div class="metric-label">BULKS (pallets)</div>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{logistica['peso_neto_total']:,} kg</div>
                <div class="metric-label">NET WEIGHT</div>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{logistica['peso_bruto']:,} kg</div>
                <div class="metric-label">GROSS WEIGHT</div>
            </div>
            """, unsafe_allow_html=True)
        with col4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{logistica['volumen_total']} m³</div>
                <div class="metric-label">VOLUMEN</div>
            </div>
            """, unsafe_allow_html=True)

        # Productos no reconocidos
        if logistica['productos_sin_referencia']:
            st.warning("⚠️ **Productos no reconocidos** (revisar manualmente):")
            for p in logistica['productos_sin_referencia']:
                st.caption(f"• {p}")

        # Detalle por producto
        st.markdown("### 📋 Detalle por producto")
        product_data = []
        for r in logistica['resultados']:
            unidad = r['unidad']
            cant = f"{r['cantidad']:.0f}" if r['cantidad'] == int(r['cantidad']) else f"{r['cantidad']:.1f}"
            product_data.append({
                'Producto': r['producto'],
                'Cantidad': f"{cant} {unidad}",
                'Planchas': r['num_planchas'],
                'Peso (kg)': f"{r['peso_neto_kg']:,.1f}",
                'Pallets': r['pallets'],
            })

        st.dataframe(product_data, use_container_width=True, hide_index=True)

        # Pallets
        st.markdown("### 📦 Distribución de pallets")
        for p in logistica['pallets_detalle']:
            st.markdown(f'<div class="pallet-line">📦 {p}</div>',
                       unsafe_allow_html=True)

        # ── Texto para copiar ──
        st.markdown("### 📋 Resultado para bildu.com")
        copy_text = f"""BULKS:             {logistica['total_pallets']}"""
        for p in logistica['pallets_detalle']:
            copy_text += f"\n  * {p}"
        copy_text += f"""
NET WEIGHT:        {logistica['peso_neto_total']} kg
GROSS WEIGHT:      {logistica['peso_bruto']} kg
VOLUME:            {logistica['volumen_total']} m³"""

        if logistica['productos_sin_referencia']:
            copy_text += "\n\n⚠️ Productos sin referencia:"
            for p in logistica['productos_sin_referencia']:
                copy_text += f"\n  • {p}"

        st.code(copy_text, language="text")

        st.button(
            "📋 Copiar resultado",
            on_click=lambda: st.write("Copiado!"),  # fallback
            help="Selecciona el texto de arriba y Copia (Cmd+C / Ctrl+C)",
            type="primary",
        )

        st.info(
            "💡 **Tip**: Selecciona el texto del recuadro gris de arriba "
            "y cópialo (Cmd+C / Ctrl+C) para pegarlo directamente en bildu.com"
        )

    except Exception as e:
        st.error(f"❌ Error al procesar el PDF: {e}")
        st.exception(e)

    finally:
        # Limpiar archivo temporal
        try:
            os.unlink(tmp_path)
        except:
            pass

else:
    # Estado inicial
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("#### 1️⃣")
        st.markdown("Sube un PDF")
        st.caption("Presupuesto de Paviflex")
    with col2:
        st.markdown("#### 2️⃣")
        st.markdown("Calculamos")
        st.caption("Pesos, pallets, volumen")
    with col3:
        st.markdown("#### 3️⃣")
        st.markdown("Copia el resultado")
        st.caption("Directo a bildu.com")

    st.markdown("---")
    st.markdown(
        "<div class='footer'>"
        "Paviflex Logistics Calculator v1.0 — "
        "Powered by Hermes Agent & Streamlit"
        "</div>",
        unsafe_allow_html=True
    )
