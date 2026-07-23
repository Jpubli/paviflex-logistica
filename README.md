# 🚛 Paviflex Logistics Calculator

Toma un presupuesto PDF de Paviflex y calcula automáticamente la logística:
peso total, distribución en pallets y volumen.

## Cómo usarlo

1. Sube un PDF de presupuesto
2. Obtienes al instante: BULKS, NET/GROSS WEIGHT, VOLUMEN
3. Copia el resultado a bildu.com

## Stack

- **Frontend/Backend**: [Streamlit](https://streamlit.io)
- **PDF parsing**: pypdf
- **Hosting**: Streamlit Community Cloud

## Desarrollo local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Despliegue en Streamlit Cloud

1. Sube este repo a GitHub
2. Ve a https://share.streamlit.io
3. Conecta tu GitHub y selecciona el repo
4. Listo — URL pública al instante
