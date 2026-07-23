#!/bin/bash
# Paviflex Logistics Calculator — Arranque rápido
# Úsalo desde la carpeta del proyecto:
#   cd ~/Documents/hermes/paviflex-logistica
#   bash run.sh

cd "$(dirname "$0")"
echo "🚛 Paviflex Logistics Calculator"
echo "================================"
echo ""

# Usar virtualenv si existe, si no crear uno
if [ ! -d "venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -q -r requirements.txt
else
    source venv/bin/activate
fi

echo "🌐 Abriendo Streamlit..."
echo ""
streamlit run src/paviflex-logistica-web.py
