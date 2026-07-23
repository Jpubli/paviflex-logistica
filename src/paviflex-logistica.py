#!/usr/bin/env python3
"""
Paviflex Logistics Calculator - Motor de calculo logistico

Lee un presupuesto PDF, lo cruza con los datos de producto
(Pesos m2.csv + TABLA PRECIOS Y KGS.docx) y devuelve
la logistica completa: pesos, pallets, volumen.

Uso:
  python3 paviflex-logistica.py <ruta_del_pdf.pdf>

Requiere: pypdf (pip3 install pypdf)
"""

import sys
import os
import re
import csv
import json
from math import ceil
from pathlib import Path

# ---------------------------------------------------------------
# 1. CARGA DE DATOS DE PRODUCTO
# ---------------------------------------------------------------

PROJECT_DIRS = [
    os.path.dirname(os.path.abspath(__file__)),
    str(Path.home() / 'Documents' / 'hermes' / 'paviflex-logistica' / 'data'),
    os.path.expanduser("~/Documents/hermes/paviflex-logistica/data"),
]

def find_project_dir():
    for d in PROJECT_DIRS:
        csv_path = os.path.join(d, "Pesos m2.csv")
        if os.path.exists(csv_path):
            return d
    return os.getcwd()

PROJECT_DIR = find_project_dir()


class Product:
    """Representa un producto con sus datos logisticos."""
    __slots__ = ('name', 'thickness', 'weight_m2', 'width_cm', 'height_cm',
                 'pallet_terrestre', 'pallet_container',
                 'box_w', 'box_h', 'box_d', 'units_per_box',
                 'sheet_area_m2', 'thickness_mm')

    def __init__(self, name, thickness, weight_m2, width_cm, height_cm,
                 pallet_terrestre=0, pallet_container=0,
                 box_w=0, box_h=0, box_d=0, units_per_box=0):
        self.name = name.strip().upper()
        self.thickness_mm = thickness
        self.weight_m2 = weight_m2
        self.width_cm = width_cm
        self.height_cm = height_cm
        self.sheet_area_m2 = (width_cm * height_cm) / 10000 if width_cm and height_cm else 0
        self.pallet_terrestre = pallet_terrestre
        self.pallet_container = pallet_container
        self.box_w = box_w
        self.box_h = box_h
        self.box_d = box_d
        self.units_per_box = units_per_box

    def __repr__(self):
        return f"<Product {self.name} {self.thickness_mm}mm {self.weight_m2}kg/m2>"


def load_products_from_csv():
    """Carga la base de datos de productos desde Pesos m2.csv"""
    products = []
    csv_path = os.path.join(PROJECT_DIR, "Pesos m2.csv")
    if not os.path.exists(csv_path):
        print(f"Aviso: No se encuentra {csv_path}", file=sys.stderr)
        return products

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f, delimiter=';')
        next(reader)
        for row in reader:
            if len(row) < 6:
                continue
            name = row[0].strip()
            thickness_str = row[1].strip()
            weight_str = row[2].strip().replace(',', '.')
            measures = row[3].strip()
            pallet_t = row[4].strip()
            pallet_c = row[5].strip()
            box_size = row[6].strip() if len(row) > 6 else ''
            units_box = row[7].strip() if len(row) > 7 else ''

            if not name or not thickness_str:
                continue

            thickness = float(re.sub(r'[^0-9.,]', '', thickness_str).replace(',', '.'))

            # El peso puede venir como "3,3 kg" -> extraer solo el numero
            try:
                weight_clean = re.sub(r'[^0-9.,]', '', weight_str).replace(',', '.')
                weight = float(weight_clean) if weight_clean else 0
            except ValueError:
                weight = 0

            w, h = 0, 0
            if 'x' in measures.lower():
                parts = re.findall(r'[\d.]+', measures.lower().replace(',', '.'))
                if len(parts) >= 2:
                    w = float(parts[0])
                    h = float(parts[1])

            try:
                pt = int(pallet_t) if pallet_t else 0
            except ValueError:
                pt = 0
            try:
                pc = int(pallet_c) if pallet_c else 0
            except ValueError:
                pc = 0

            bw, bh, bd = 0, 0, 0
            if box_size:
                parts = re.findall(r'[\d.]+', box_size.replace(',', '.'))
                if len(parts) >= 3:
                    bw, bh, bd = float(parts[0]), float(parts[1]), float(parts[2])
            try:
                ub = int(units_box) if units_box else 0
            except ValueError:
                ub = 0

            p = Product(name, thickness, weight, w, h, pt, pc,
                        bw, bh, bd, ub)
            products.append(p)
    return products


# Pesos alternativos desde TABLA PRECIOS Y KGS.docx
EXTRA_WEIGHTS = {
    ("FITNESS XTREME", 10): 14.5,
    ("FITNESS PRO", 7): 10,
    ("FITNESS", 5): 7.5,
    ("FITNESS MONSTER", 14): 20,
    ("BEAST", 20): 20,
    ("BEAST", 30): 29,
    ("BASICFLEX", 20): 17.5,
    ("BASICFLEX", 30): 26.5,
    ("TATAMI", 20): 2.5,
    ("TATAMI", 30): 3.5,
    ("ACTION", 7): 2,
    # Pesos de la seccion de PRECIOS del DOCX (difieren del CSV)
    ("CONFORTSONIC", 20): 8.0,
    ("BASICFLEX", 20): 15.7,
    ("BASICFLEX", 30): 23.5,
}

# ---------------------------------------------------------------
# 2. PARSER DE PRODUCTOS DESDE PDF
# ---------------------------------------------------------------

def extract_text_from_pdf(pdf_path):
    """Extrae texto de un PDF usando pypdf"""
    try:
        from pypdf import PdfReader
    except ImportError:
        print("Error: Necesito pypdf. Instalalo con: pip3 install pypdf")
        sys.exit(1)

    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text


def normalize_name(name):
    """Normaliza un nombre de producto para busqueda difusa."""
    n = name.upper().strip()
    n = re.sub(r'[-]', ' ', n)
    n = re.sub(r'\s+', ' ', n)
    n = re.sub(r'\b(M\s*\.?\s*PEARL|PEARL|WHITE|BLACK|STANDARD|PREMIUM)\b', '', n)
    n = re.sub(r'\b(CMS|CM|4\s*SIDES\s*PUZZLE|PUZZLE|SIDES)\b', '', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n


def find_product(products, search_name, search_thickness):
    """Busca un producto por nombre normalizado y grosor."""
    search_name = normalize_name(search_name)
    search_thickness = float(search_thickness)

    best_match = None
    best_score = 0

    for p in products:
        p_name = normalize_name(p.name)
        words_s = set(search_name.split())
        words_p = set(p_name.split())
        common = words_s & words_p
        if not common:
            continue

        score = len(common) / max(len(words_s), len(words_p))

        thickness_ok = abs(p.thickness_mm - search_thickness) < 2
        if thickness_ok:
            score += 0.3

        if len(words_p) > len(words_s) * 1.5:
            score *= 0.7

        if score > best_score:
            best_score = score
            best_match = p

    if best_score >= 0.3:
        return best_match
    return None


def parse_pdf_products(text, products_db):
    """Parsea los productos del texto extraido del PDF.

    El formato tipico es:
      Fitness XTREME 10 mm - M. Pearl
      100x100 cms 4 sides puzzle
      148
      m2
      91,40
      25,00
      10.145,40

    Devuelve tambien las dimensiones de plancha declaradas en el PDF.
    """
    lines_raw = text.split('\n')

    # Encontrar la seccion de productos
    in_products = False
    product_lines = []

    for line in lines_raw:
        ls = line.strip()
        if 'DESCRIPTION' in ls.upper():
            in_products = True
            continue
        if in_products:
            if ('PAYMENT TERMS' in ls.upper() or
                'SUBTOTAL' in ls.upper() or
                'BULK' in ls.upper() or
                'INCOTERMS' in ls.upper()):
                break
            if ls:
                product_lines.append(ls)

    results = []
    i = 0
    while i < len(product_lines):
        line = product_lines[i].strip()

        # Detectar si esta linea es una unidad (m2, ud)
        is_unit_line = line.lower() in ('m2', 'm2', 'ud', 'unidad')

        if is_unit_line and i > 0:
            qty_line = product_lines[i - 1].strip()
            qty_match = re.match(r'^(\d+[.,]?\d*)$', qty_line.replace(',', '.'))

            if qty_match:
                quantity = float(qty_match.group(1).replace(',', '.'))
                unit = 'm2' if line.lower().startswith('m') else 'ud'

                # Recolectar lineas de descripcion
                desc_lines = []
                j = i - 2
                while j >= 0:
                    test = product_lines[j].strip()
                    if test.lower() in ('m2', 'm2', 'ud', 'unidad'):
                        j += 1
                        break
                    if re.match(r'^[\d.,]+$', test.replace(',', '.')):
                        if j < len(product_lines) - 1:
                            next_l = product_lines[j + 1].strip().lower()
                            if next_l not in ('m2', 'm2', 'ud', 'unidad'):
                                break
                    desc_lines.insert(0, test)
                    j -= 1
                    if len(desc_lines) >= 5:
                        break

                if not desc_lines:
                    for k in range(max(0, i - 4), i - 1):
                        desc_lines.append(product_lines[k].strip())

                full_desc = ' '.join(desc_lines)

                # Extraer dimensiones de plancha del PDF (ej: "100x100 cms")
                size_match = re.search(r'(\d+)\s*[xX]\s*(\d+)\s*(?:cms|cm)?', full_desc)
                pdf_w, pdf_h = 0, 0
                if size_match:
                    pdf_w = float(size_match.group(1))
                    pdf_h = float(size_match.group(2))

                # Extraer grosor
                thick_match = re.search(r'(\d+)\s*(?:mm|MM)', full_desc)
                thickness = float(thick_match.group(1)) if thick_match else 0

                name_part = full_desc
                if thick_match:
                    name_part = full_desc[:thick_match.start()].strip()
                name_part = re.sub(r'\d+\s*[xX]\s*\d+.*', '', name_part).strip()

                product = find_product(products_db, name_part, thickness)

                results.append({
                    'raw_name': full_desc,
                    'parsed_name': name_part,
                    'thickness_mm': thickness,
                    'quantity_m2': quantity if unit == 'm2' else 0,
                    'quantity_ud': quantity if unit == 'ud' else 0,
                    'unit': unit,
                    'product': product,
                    'pdf_width_cm': pdf_w,
                    'pdf_height_cm': pdf_h,
                })

                i += 1
                continue

        i += 1

    return results


# ---------------------------------------------------------------
# 3. CALCULOS LOGISTICOS
# ---------------------------------------------------------------

def calcular_logistica(products_data):
    """Calcula la logistica completa a partir de los productos parseados.

    Paso 1: Fusionar "Markings" con sus productos base.
    Paso 2: Calcular pesos, pallets y volumen.
    """
    # ---------------------------------------------------------------
    # Paso 1: Fusionar productos con sus sub-items (Markings)
    # ---------------------------------------------------------------
    # Agrupar por producto base
    base_map = {}  # (product_db_id, thickness) -> merged entry

    for pd_item in products_data:
        product = pd_item['product']
        qty = pd_item['quantity_m2'] or pd_item['quantity_ud']

        if not product:
            continue

        # Determinar si es un Marking
        raw = pd_item.get('raw_name', '').upper()
        is_marking = 'MARKING' in raw

        key = (id(product), product.thickness_mm)

        if key not in base_map:
            base_map[key] = {
                'product': product,
                'quantity_m2': 0,
                'quantity_ud': 0,
                'is_marking': False,
                'pdf_width_cm': 0,
                'pdf_height_cm': 0,
            }

        if pd_item['unit'] == 'm2':
            base_map[key]['quantity_m2'] += pd_item['quantity_m2']
        else:
            base_map[key]['quantity_ud'] += pd_item['quantity_ud']

        # Guardar dimensiones del PDF si estan disponibles
        pdf_w = pd_item.get('pdf_width_cm', 0)
        pdf_h = pd_item.get('pdf_height_cm', 0)
        if pdf_w > 0 and pdf_h > 0:
            base_map[key]['pdf_width_cm'] = pdf_w
            base_map[key]['pdf_height_cm'] = pdf_h

        if is_marking:
            base_map[key]['is_marking'] = True

    # ---------------------------------------------------------------
    # Paso 2: Calculos por producto
    # ---------------------------------------------------------------
    resultados = []
    peso_total_neto = 0
    volumen_total = 0
    productos_sin_referencia = []

    for pd_item in products_data:
        if not pd_item['product']:
            productos_sin_referencia.append(pd_item.get('raw_name', '?'))
            # No eliminar, solo reportar

    for key, entry in base_map.items():
        product = entry['product']
        qty_m2 = entry['quantity_m2']
        qty_ud = entry['quantity_ud']
        qty = qty_m2 or qty_ud

        # Dimensiones de plancha: preferir las del PDF si estan disponibles
        pdf_w = entry.get('pdf_width_cm', 0)
        pdf_h = entry.get('pdf_height_cm', 0)
        if pdf_w > 0 and pdf_h > 0:
            sheet_area = (pdf_w * pdf_h) / 10000
        else:
            sheet_area = product.sheet_area_m2

        # Sheet count
        if qty_m2 > 0 and sheet_area > 0:
            num_sheets = ceil(qty_m2 / sheet_area)
        else:
            num_sheets = int(qty_ud) if qty_ud > 0 else 0

        # Weight
        weight_key = (product.name, int(product.thickness_mm))
        weight_m2 = EXTRA_WEIGHTS.get(weight_key, product.weight_m2)

        if qty_m2 > 0:
            net_weight = round(qty_m2 * weight_m2, 1)
        else:
            if sheet_area > 0:
                net_weight = round(num_sheets * weight_m2 * sheet_area, 1)
            else:
                net_weight = 0

        # Pallets -- logica ajustada para coincidir con calculos manuales
        pallets = 0
        pallet_dim = ""

        if product.name == "TURFLEX":
            pallets = 1
            pallet_dim = "102x200x75"
        elif product.name == "CONFORTSONIC":
            # Capacidad efectiva segun grosor (el CSV dice 50 pero
            # en la practica se usa menos por altura de apilado)
            cap_map = {10: 50, 15: 40, 20: 30, 30: 20}
            cap = cap_map.get(int(product.thickness_mm), 50)
            pallets = ceil(num_sheets / cap) if num_sheets > 0 else 1
            pallet_height = {10: 80, 15: 95, 20: 115, 30: 130}
            ph = pallet_height.get(int(product.thickness_mm), 115)
            pallet_dim = f"200x102x{ph}"
        elif product.pallet_terrestre > 0 and num_sheets > 0:
            # Para planchas finas (<=10mm) se usa capacidad container
            # Para planchas gruesas (>10mm) se usa capacidad terrestre
            if product.thickness_mm <= 10 and product.pallet_container > 0:
                cap = product.pallet_container
            else:
                cap = product.pallet_terrestre
            pallets = ceil(num_sheets / cap)
            est_height = int(product.thickness_mm * (num_sheets / max(pallets, 1)) / 10 + 15)
            pallet_dim = f"102x102x{max(est_height, 50)}"
        else:
            pallets = max(1, ceil(num_sheets / 50))
            pallet_dim = "102x102x100"

        # Volume
        if pallet_dim:
            dims = re.findall(r'[\d.]+', pallet_dim)
            if len(dims) >= 3:
                vol_m3 = (float(dims[0]) * float(dims[1]) * float(dims[2])) / 1_000_000
                vol_total = round(vol_m3 * pallets, 1)
            else:
                vol_total = 0
        else:
            vol_total = 0

        volumen_total += vol_total
        peso_total_neto += net_weight

        entry_res = {
            'producto': f"{product.name} {int(product.thickness_mm)}mm",
            'cantidad': qty_m2 or qty_ud,
            'unidad': 'm2' if qty_m2 > 0 else 'ud',
            'num_planchas': num_sheets,
            'peso_neto_kg': net_weight,
            'peso_m2': weight_m2,
            'pallets': pallets,
            'pallet_dim': pallet_dim,
            'volumen_m3': vol_total,
        }
        resultados.append(entry_res)

    peso_bruto = round(peso_total_neto * 1.035)

    # Generar detalle de pallets
    pallets_detalle = []
    for r in resultados:
        suff = 's' if r['pallets'] > 1 else ''
        pallets_detalle.append(f"{r['pallets']} Pallet{suff} {r['pallet_dim']} ({r['producto']})")

    return {
        'resultados': resultados,
        'peso_neto_total': round(peso_total_neto),
        'peso_bruto': peso_bruto,
        'volumen_total': round(volumen_total, 1),
        'total_pallets': sum(r['pallets'] for r in resultados),
        'pallets_detalle': pallets_detalle,
        'productos_sin_referencia': productos_sin_referencia,
    }


# ---------------------------------------------------------------
# 4. FORMATO DE SALIDA
# ---------------------------------------------------------------

def format_output(logistica, pdf_path):
    """Formatea la salida para copiar a bildu.com"""
    lines = []
    lines.append("=" * 60)
    lines.append(f"LOGISTICA PAVIFLEX - {os.path.basename(pdf_path)}")
    lines.append("=" * 60)
    lines.append("")

    if logistica['productos_sin_referencia']:
        lines.append("PRODUCTOS NO RECONOCIDOS (revisar):")
        for p in logistica['productos_sin_referencia']:
            lines.append(f"  * {p}")
        lines.append("")

    lines.append("DETALLE POR PRODUCTO:")
    lines.append("-" * 60)
    lines.append(f"{'Producto':30s} {'Cant.':>8s} {'Planchas':>9s} {'Peso kg':>8s} {'Pallets':>7s}")
    lines.append("-" * 60)

    for r in logistica['resultados']:
        unidad = r['unidad']
        cant = f"{r['cantidad']:.0f}{unidad}" if r['cantidad'] == int(r['cantidad']) else f"{r['cantidad']:.1f}{unidad}"
        lines.append(f"{r['producto']:30s} {cant:>8s} {r['num_planchas']:>9d} {r['peso_neto_kg']:>8.1f} {r['pallets']:>7d}")

    lines.append("-" * 60)
    lines.append("")
    lines.append("RESUMEN LOGISTICO:")
    lines.append(f"   BULKS:             {logistica['total_pallets']}")
    for p in logistica['pallets_detalle']:
        lines.append(f"   * {p}")
    lines.append(f"   NET WEIGHT:        {logistica['peso_neto_total']} kg")
    lines.append(f"   GROSS WEIGHT:      {logistica['peso_bruto']} kg")
    lines.append(f"   VOLUME:            {logistica['volumen_total']} m3")
    lines.append("")
    lines.append("=" * 60)

    return '\n'.join(lines)


# ---------------------------------------------------------------
# 5. MAIN
# ---------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 paviflex-logistica.py <ruta_del_pdf.pdf>")
        print("   o: python3 paviflex-logistica.py --json <ruta_del_pdf.pdf>")
        sys.exit(1)

    json_mode = sys.argv[1] == '--json'
    pdf_path = sys.argv[2] if json_mode else sys.argv[1]

    if not os.path.exists(pdf_path):
        print(f"Error: No se encuentra el PDF: {pdf_path}")
        sys.exit(1)

    products_db = load_products_from_csv()
    print(f"Productos en BD: {len(products_db)}", file=sys.stderr)

    print(f"Leyendo PDF: {pdf_path}", file=sys.stderr)
    text = extract_text_from_pdf(pdf_path)

    parsed = parse_pdf_products(text, products_db)
    print(f"Productos detectados: {len(parsed)}", file=sys.stderr)

    if not parsed:
        print("Error: No se pudieron detectar productos en el PDF.")
        print("Texto extraido:")
        print(text[:2000])
        sys.exit(1)

    logistica = calcular_logistica(parsed)

    if json_mode:
        print(format_json(logistica))
    else:
        print(format_output(logistica, pdf_path))

    if logistica['productos_sin_referencia']:
        print(f"\nQuedaron {len(logistica['productos_sin_referencia'])} producto(s) sin referencia.", file=sys.stderr)


def format_json(logistica):
    return json.dumps(logistica, indent=2, ensure_ascii=False)


if __name__ == '__main__':
    main()
