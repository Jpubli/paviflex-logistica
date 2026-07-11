"""
Paviflex Logistics Calculator — Motor de cálculo logístico
===========================================================
Lee un presupuesto PDF, lo cruza con los datos de producto
y devuelve la logística completa: pesos, pallets, volumen.
"""

import os
import re
import csv
import json
from math import ceil

# ── Ruta de datos (relativa a este archivo) ──
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

# ── Product class ──
class Product:
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


# ── Carga de productos ──
def load_products():
    products = []
    csv_path = os.path.join(DATA_DIR, 'Pesos m2.csv')
    if not os.path.exists(csv_path):
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

            products.append(Product(name, thickness, weight, w, h, pt, pc,
                                    bw, bh, bd, ub))
    return products


# Pesos alternativos (de TABLA PRECIOS Y KGS.docx)
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
    ("CONFORTSONIC", 20): 8.0,
    ("BASICFLEX", 20): 15.7,
    ("BASICFLEX", 30): 23.5,
}


# ── PDF parsing ──
def extract_text(pdf_path):
    from pypdf import PdfReader
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() + "\n"
    return text


def normalize_name(name):
    n = name.upper().strip()
    n = re.sub(r'[-]', ' ', n)
    n = re.sub(r'\s+', ' ', n)
    n = re.sub(r'\b(M\s*\.?\s*PEARL|PEARL|WHITE|BLACK|STANDARD|PREMIUM)\b', '', n)
    n = re.sub(r'\b(CMS|CM|4\s*SIDES\s*PUZZLE|PUZZLE|SIDES)\b', '', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n


def find_product(products, search_name, search_thickness):
    search_name = normalize_name(search_name)
    search_thickness = float(search_thickness)
    best_match, best_score = None, 0
    for p in products:
        p_name = normalize_name(p.name)
        words_s = set(search_name.split())
        words_p = set(p_name.split())
        common = words_s & words_p
        if not common:
            continue
        score = len(common) / max(len(words_s), len(words_p))
        if abs(p.thickness_mm - search_thickness) < 2:
            score += 0.3
        if len(words_p) > len(words_s) * 1.5:
            score *= 0.7
        if score > best_score:
            best_score = score
            best_match = p
    return best_match if best_score >= 0.3 else None


def parse_products(text, products_db):
    lines_raw = text.split('\n')
    in_products = False
    product_lines = []
    for line in lines_raw:
        ls = line.strip()
        if 'DESCRIPTION' in ls.upper():
            in_products = True
            continue
        if in_products:
            if ('PAYMENT TERMS' in ls.upper() or 'SUBTOTAL' in ls.upper()
                    or 'BULK' in ls.upper() or 'INCOTERMS' in ls.upper()):
                break
            if ls:
                product_lines.append(ls)

    results, i = [], 0
    while i < len(product_lines):
        line = product_lines[i].strip()
        is_unit_line = line.lower() in ('m2', 'm2', 'ud', 'unidad')
        if is_unit_line and i > 0:
            qty_line = product_lines[i - 1].strip()
            qty_match = re.match(r'^(\d+[.,]?\d*)$', qty_line.replace(',', '.'))
            if qty_match:
                quantity = float(qty_match.group(1).replace(',', '.'))
                unit = 'm2' if line.lower().startswith('m') else 'ud'
                desc_lines, j = [], i - 2
                while j >= 0:
                    test = product_lines[j].strip()
                    if test.lower() in ('m2', 'm2', 'ud', 'unidad'):
                        j += 1; break
                    if re.match(r'^[\d.,]+$', test.replace(',', '.')):
                        if j < len(product_lines) - 1:
                            next_l = product_lines[j + 1].strip().lower()
                            if next_l not in ('m2', 'm2', 'ud', 'unidad'):
                                break
                    desc_lines.insert(0, test)
                    j -= 1
                    if len(desc_lines) >= 5: break
                if not desc_lines:
                    for k in range(max(0, i - 4), i - 1):
                        desc_lines.append(product_lines[k].strip())
                full_desc = ' '.join(desc_lines)
                size_match = re.search(r'(\d+)\s*[xX]\s*(\d+)\s*(?:cms|cm)?', full_desc)
                pdf_w = float(size_match.group(1)) if size_match else 0
                pdf_h = float(size_match.group(2)) if size_match else 0
                thick_match = re.search(r'(\d+)\s*(?:mm|MM)', full_desc)
                thickness = float(thick_match.group(1)) if thick_match else 0
                name_part = full_desc
                if thick_match:
                    name_part = full_desc[:thick_match.start()].strip()
                name_part = re.sub(r'\d+\s*[xX]\s*\d+.*', '', name_part).strip()
                product = find_product(products_db, name_part, thickness)
                results.append({
                    'raw_name': full_desc, 'parsed_name': name_part,
                    'thickness_mm': thickness,
                    'quantity_m2': quantity if unit == 'm2' else 0,
                    'quantity_ud': quantity if unit == 'ud' else 0,
                    'unit': unit, 'product': product,
                    'pdf_width_cm': pdf_w, 'pdf_height_cm': pdf_h,
                })
                i += 1; continue
        i += 1
    return results


# ── Cálculos logísticos ──
def calcular(products_data):
    base_map = {}
    for pd_item in products_data:
        product = pd_item['product']
        if not product:
            continue
        is_marking = 'MARKING' in pd_item.get('raw_name', '').upper()
        key = (id(product), product.thickness_mm)
        if key not in base_map:
            base_map[key] = {'product': product, 'quantity_m2': 0, 'quantity_ud': 0,
                             'is_marking': False, 'pdf_width_cm': 0, 'pdf_height_cm': 0}
        if pd_item['unit'] == 'm2':
            base_map[key]['quantity_m2'] += pd_item['quantity_m2']
        else:
            base_map[key]['quantity_ud'] += pd_item['quantity_ud']
        if pd_item.get('pdf_width_cm', 0) > 0 and pd_item.get('pdf_height_cm', 0) > 0:
            base_map[key]['pdf_width_cm'] = pd_item['pdf_width_cm']
            base_map[key]['pdf_height_cm'] = pd_item['pdf_height_cm']
        if is_marking:
            base_map[key]['is_marking'] = True

    resultados, peso_total, volumen_total, sin_ref = [], 0, 0, []
    for pd_item in products_data:
        if not pd_item['product']:
            sin_ref.append(pd_item.get('raw_name', '?'))

    for key, entry in base_map.items():
        product = entry['product']
        qty_m2, qty_ud = entry['quantity_m2'], entry['quantity_ud']

        pdf_w, pdf_h = entry['pdf_width_cm'], entry['pdf_height_cm']
        sheet_area = (pdf_w * pdf_h) / 10000 if pdf_w > 0 and pdf_h > 0 else product.sheet_area_m2

        num_sheets = ceil(qty_m2 / sheet_area) if qty_m2 > 0 and sheet_area > 0 else int(qty_ud) if qty_ud > 0 else 0

        wkey = (product.name, int(product.thickness_mm))
        weight_m2 = EXTRA_WEIGHTS.get(wkey, product.weight_m2)
        net_weight = round(qty_m2 * weight_m2, 1) if qty_m2 > 0 else (
            round(num_sheets * weight_m2 * sheet_area, 1) if sheet_area > 0 else 0)

        # Pallets
        if product.name == "TURFLEX":
            pallets, pallet_dim = 1, "102x200x75"
        elif product.name == "CONFORTSONIC":
            cap_map = {10: 50, 15: 40, 20: 30, 30: 20}
            cap = cap_map.get(int(product.thickness_mm), 50)
            pallets = ceil(num_sheets / cap) if num_sheets > 0 else 1
            ph = {10: 80, 15: 95, 20: 115, 30: 130}.get(int(product.thickness_mm), 115)
            pallet_dim = f"200x102x{ph}"
        elif product.pallet_terrestre > 0 and num_sheets > 0:
            cap = product.pallet_container if (product.thickness_mm <= 10 and product.pallet_container > 0) else product.pallet_terrestre
            pallets = ceil(num_sheets / cap)
            est_height = int(product.thickness_mm * (num_sheets / max(pallets, 1)) / 10 + 15)
            pallet_dim = f"102x102x{max(est_height, 50)}"
        else:
            pallets = max(1, ceil(num_sheets / 50))
            pallet_dim = "102x102x100"

        dims = re.findall(r'[\d.]+', pallet_dim)
        vol_total = round((float(dims[0]) * float(dims[1]) * float(dims[2])) / 1_000_000 * pallets, 1) if len(dims) >= 3 else 0

        volumen_total += vol_total
        peso_total += net_weight

        resultados.append({
            'producto': f"{product.name} {int(product.thickness_mm)}mm",
            'cantidad': qty_m2 or qty_ud,
            'unidad': 'm2' if qty_m2 > 0 else 'ud',
            'num_planchas': num_sheets,
            'peso_neto_kg': net_weight,
            'peso_m2': weight_m2,
            'pallets': pallets,
            'pallet_dim': pallet_dim,
            'volumen_m3': vol_total,
        })

    peso_bruto = round(peso_total * 1.035)
    pallets_detalle = [f"{r['pallets']} Pallet{'s' if r['pallets'] > 1 else ''} {r['pallet_dim']} ({r['producto']})" for r in resultados]

    return {
        'resultados': resultados,
        'peso_neto_total': round(peso_total),
        'peso_bruto': peso_bruto,
        'volumen_total': round(volumen_total, 1),
        'total_pallets': sum(r['pallets'] for r in resultados),
        'pallets_detalle': pallets_detalle,
        'productos_sin_referencia': sin_ref,
    }
