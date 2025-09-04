#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema OCR Avanzato per Volantini
Basato su colab.py con miglioramenti per il progetto locale
"""

import pytesseract
from pdf2image import convert_from_path
import cv2
import numpy as np
import os
import re
import json
import requests
from transformers import pipeline
from PIL import Image
import logging
from datetime import datetime

# Configurazione Tesseract per ambiente Linux (Render)
if os.name == 'posix':  # Linux/Unix
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('colab_adapted.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Lista marche italiane comuni
# Database esteso delle marche italiane e internazionali
MARCHE = [
    # Pasta e cereali
    "Barilla", "De Cecco", "Voiello", "Buitoni", "La Molisana", "Divella", "Rummo", 
    "Garofalo", "Pasta Zara", "Agnesi", "Riso Scotti", "Granoro", "Delverde", 
    "Colavita", "Molisana", "Rana", "Tortellini", "Cappelletti", "Gnocchi",
    
    # Prodotti da forno
    "Mulino Bianco", "Pavesi", "Gentilini", "Grissin Bon", "Saiwa", "Oro Saiwa",
    "Ringo", "Macine", "Baiocchi", "Pan di Stelle", "Plasmon", "Mellin",
    
    # Latticini e formaggi
    "Parmalat", "Granarolo", "Centrale del Latte", "Mukki", "Latteria Sociale",
    "Galbani", "Bel Paese", "Sottilette", "Philadelphia", "Bresso", "Nonno Nanni",
    "Valtaleggio", "Caseificio", "Santa Lucia", "Tre Valli", "Sterilgarda",
    "Parmigiano", "Reggiano", "Gorgonzola", "Taleggio", "Asiago", "Fontina",
    "Pecorino", "Ricotta", "Mascarpone", "Stracchino", "Robiola", "Mozzarella",
    
    # Yogurt e dessert
    "Danone", "Yomo", "Müller", "Activia", "Vipiteno", "Mila", "Yogurt Greco",
    "Parmareggio", "Valtaleggio", "Centrale", "Latteria",
    
    # Carne e salumi
    "Beretta", "Parmacotto", "Negroni", "Citterio", "Rovagnati", "Fiorucci",
    "Prosciutto", "Salame", "Mortadella", "Bresaola", "Speck", "Pancetta",
    "Aia", "Amadori", "Fileni", "Tacchino", "Pollo", "Wudy", "Würstel",
    
    # Pesce e conserve
    "Rio Mare", "Nostromo", "Palmera", "Mareblu", "Callipo", "Ortiz", "Tonno",
    "Salmone", "Sardine", "Acciughe", "Sgombro", "Polpo", "Vongole",
    
    # Conserve e sughi
    "Mutti", "Cirio", "Valfrutta", "Pomi", "Star", "Barilla", "Knorr", "Maggi",
    "Pomodoro", "Passata", "Pelati", "Concentrato", "Sugo", "Pesto", "Ragù",
    
    # Olio e condimenti
    "Bertolli", "Monini", "Carapelli", "Sagra", "Sasso", "Colavita", "Filippo Berio",
    "De Sanctis", "Dante", "Oleificio", "Olio", "Extra", "Vergine", "Extravergine",
    "Italiano", "Toscano", "Pugliese", "Siciliano", "Calabrese", "Ligure",
    
    # Bevande
    "Coca-Cola", "Pepsi", "Fanta", "Sprite", "Aranciata", "Limonata", "Chinotto",
    "San Pellegrino", "Acqua Panna", "Levissima", "Ferrarelle", "Uliveto",
    "Lavazza", "Illy", "Segafredo", "Kimbo", "Caffè", "Espresso", "Cappuccino",
    
    # Dolci e snack
    "Ferrero", "Kinder", "Nutella", "Rocher", "Mon Chéri", "Pocket Coffee",
    "San Carlo", "Amica Chips", "Pringles", "Lay's", "Doritos", "Fonzies",
    "Haribo", "Mentos", "Tic Tac", "Polo", "Goleador", "Chupa Chups",
    
    # Gelati
    "Sammontana", "Algida", "Magnum", "Cornetto", "Ben & Jerry's", "Häagen-Dazs",
    "Carte d'Or", "Viennetta", "Calippo", "Solero", "Twister",
    
    # Surgelati
    "Findus", "Buitoni", "Orogel", "Valfrutta", "Bonduelle", "Sofficini",
    "Bastoncini", "Spinaci", "Piselli", "Minestrone", "Verdure", "Pesce",
    
    # Supermercati e private label
    "Conad", "Coop", "Esselunga", "Carrefour", "Lidl", "Eurospin", "MD", "Penny",
    "Aldi", "Bennet", "Iper", "Simply", "Tigros", "Pam", "Sigma", "Despar",
    
    # Prodotti per l'infanzia
    "Plasmon", "Mellin", "Nipiol", "Humana", "Aptamil", "Nestlé", "Hipp",
    "Omogeneizzato", "Biscotto", "Pastina", "Latte", "Formula",
    
    # Prodotti biologici
    "Alce Nero", "Ecor", "Probios", "La Terra e il Cielo", "Biologico", "Bio",
    "Organic", "Naturale", "Integrale", "Senza Glutine",
    
    # Marche regionali
    "Iorio", "Mareblu", "Consilia", "Casamodena", "Igor", "Leonardi", "Rigcontina",
    "Santa Maria", "Convivio", "Fonte", "Domenica", "Velletri", "Frascati",
    "Ciampino", "Seghetti", "Francesco", "Assisi", "Galbani"
]

# Inizializzazione modelli AI
print("🤖 Caricamento modelli AI...")
try:
    image_classifier = pipeline(
        "image-classification",
        model="google/vit-base-patch16-224"
    )
    print("✅ Modello di classificazione immagini caricato")
except Exception as e:
    print(f"⚠️ Errore caricamento classificatore immagini: {e}")
    image_classifier = None

try:
    text_corrector = pipeline("text2text-generation", model="google/mt5-small")
    print("✅ Modello di correzione testo caricato")
except Exception as e:
    print(f"⚠️ Errore caricamento correttore testo: {e}")
    text_corrector = None

def correggi_testo(text):
    """Corregge il testo OCR usando AI"""
    if not text or not text_corrector:
        return text
    
    try:
        # Pulisci il testo prima della correzione
        text = re.sub(r'[^a-zA-ZàèéìòùÀÈÉÌÒÙ0-9\s.,€]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        if len(text) < 2:
            return text
            
        prompt = f"Correggi questo testo OCR di un prodotto alimentare: {text}"
        result = text_corrector(prompt, max_length=50, num_return_sequences=1)
        
        if result and len(result) > 0:
            corrected = result[0]['generated_text']
            # Rimuovi il prompt dalla risposta se presente
            corrected = corrected.replace(prompt, "").strip()
            return corrected if corrected else text
        return text
    except Exception as e:
        logger.warning(f"Errore correzione testo: {e}")
        return text

def download_pdf(url, filename="volantino.pdf"):
    """Scarica il PDF dal URL"""
    try:
        print(f"📥 Scaricamento PDF da: {url}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        os.makedirs("temp", exist_ok=True)
        filepath = os.path.join("temp", filename)
        
        with open(filepath, "wb") as f:
            f.write(response.content)
        
        print(f"✅ PDF scaricato: {filepath}")
        return filepath
    except Exception as e:
        logger.error(f"Errore download PDF: {e}")
        raise

def ocr_pdf_images(pdf_path, image_folder="output", dpi=300, scale_factor=2):
    """Converte PDF in immagini per OCR"""
    try:
        print(f"🖼️ Conversione PDF in immagini...")
        if not os.path.exists(image_folder):
            os.makedirs(image_folder)
            
        pages = convert_from_path(pdf_path, dpi=dpi)
        image_paths = []
        
        for i, page in enumerate(pages):
            path = os.path.join(image_folder, f"page_{i+1}.png")
            page.save(path, "PNG")
            
            # Migliora qualità immagine
            img = cv2.imread(path)
            img = cv2.resize(img, (img.shape[1]*scale_factor, img.shape[0]*scale_factor), 
                           interpolation=cv2.INTER_CUBIC)
            cv2.imwrite(path, img)
            image_paths.append(path)
            
        print(f"📄 {len(image_paths)} pagine convertite")
        return image_paths
    except Exception as e:
        logger.error(f"Errore conversione PDF: {e}")
        raise

def extract_quantity(text):
    """Estrae e valida quantità dal testo con correzione automatica"""
    if not text:
        return None
    
    text_clean = text.lower().strip()
    
    # Dizionario per correzioni OCR comuni nelle unità di misura
    unit_corrections = {
        'gr': 'g', 'gm': 'g', 'qr': 'g', 'q': 'g',
        'kq': 'kg', 'ko': 'kg', 'kp': 'kg',
        'mi': 'ml', 'mI': 'ml', 'rn': 'ml', 'rnl': 'ml',
        'lt': 'l', 'lf': 'l', 'It': 'l',
        'pezzi': 'pz', 'pezzo': 'pz', 'pc': 'pz', 'pcs': 'pz',
        'bustina': 'bust', 'bustine': 'bust', 'busta': 'bust',
        'bottiglia': 'bott', 'bottiglie': 'bott', 'bot': 'bott',
        'confezioni': 'confezione', 'conf': 'confezione', 'pack': 'confezione',
        'etto': '100g', 'hg': '100g', 'ettogrammi': '100g',
        'litro': 'l', 'litri': 'l',
        'grammi': 'g', 'grammo': 'g',
        'chilogrammi': 'kg', 'chilogrammo': 'kg', 'chili': 'kg', 'chilo': 'kg',
        'millilitri': 'ml', 'millilitro': 'ml'
    }
    
    # Pattern più complessi per catturare diverse varianti
    patterns = [
        # Pattern standard: numero + unità
        r'(\d+(?:[,.]\d+)?\s*(?:gr?|kg|ml|l|lt|pz|bust|bott|confezione|etto|hg)s?)\b',
        # Pattern con x (es: 6x330ml)
        r'(\d+\s*x\s*\d+(?:[,.]\d+)?\s*(?:gr?|kg|ml|l|lt|pz|bust|bott|confezione)s?)\b',
        # Pattern con da (es: da 500g)
        r'da\s+(\d+(?:[,.]\d+)?\s*(?:gr?|kg|ml|l|lt|pz|bust|bott|confezione)s?)\b',
        # Pattern con peso/volume isolato
        r'(\d+(?:[,.]\d+)?\s*(?:grammi?|chilogrammi?|chili?|litri?|millilitri?)s?)\b',
        # Pattern per errori OCR comuni
        r'(\d+(?:[,.]\d+)?\s*(?:qr?|kq|ko|mi|mI|rn|rnl|lf|It|pc|pcs)s?)\b'
    ]
    
    found_quantities = []
    
    for pattern in patterns:
        matches = re.findall(pattern, text_clean, re.IGNORECASE)
        found_quantities.extend(matches)
    
    if not found_quantities:
        return None
    
    # Prende la prima quantità trovata e la normalizza
    quantity = found_quantities[0].strip()
    
    # Correzione OCR per unità di misura
    for wrong_unit, correct_unit in unit_corrections.items():
        quantity = re.sub(r'\b' + re.escape(wrong_unit) + r's?\b', correct_unit, quantity, flags=re.IGNORECASE)
    
    # Normalizzazione formato numerico
    quantity = re.sub(r'(\d),(?=\d{3}\b)', r'\1', quantity)  # Rimuove virgole come separatori migliaia
    quantity = re.sub(r'(\d),(?=\d{1,2}\b)', r'\1.', quantity)  # Converte virgole decimali in punti
    
    # Validazione e correzione logica
    quantity_validated = validate_and_correct_quantity(quantity)
    
    return quantity_validated if quantity_validated else quantity

def validate_and_correct_quantity(quantity):
    """Valida e corregge logicamente le quantità estratte"""
    if not quantity:
        return None
    
    # Estrae numero e unità
    match = re.search(r'(\d+(?:\.\d+)?)\s*([a-zA-Z]+)', quantity)
    if not match:
        return quantity
    
    number_str, unit = match.groups()
    try:
        number = float(number_str)
    except ValueError:
        return quantity
    
    unit = unit.lower()
    
    # Regole di validazione e correzione
    corrections = []
    
    # Correzioni per valori implausibili
    if unit in ['g', 'gr'] and number > 5000:  # Troppo pesante per un singolo prodotto
        if number >= 10000:
            corrections.append(f"{number/1000}kg")
        else:
            corrections.append(f"{int(number)}g")
    
    elif unit in ['kg'] and number > 50:  # Troppo pesante
        corrections.append(f"{int(number)}g")
    
    elif unit in ['ml'] and number > 10000:  # Troppo voluminoso
        corrections.append(f"{number/1000}l")
    
    elif unit in ['l', 'lt'] and number > 20:  # Troppo voluminoso per un singolo prodotto
        corrections.append(f"{int(number*1000)}ml")
    
    elif unit in ['pz'] and number > 100:  # Troppi pezzi
        corrections.append(f"{int(number)}pz")
    
    # Correzioni per valori troppo piccoli
    elif unit in ['kg'] and number < 0.01:
        corrections.append(f"{int(number*1000)}g")
    
    elif unit in ['l', 'lt'] and number < 0.01:
        corrections.append(f"{int(number*1000)}ml")
    
    # Standardizzazione unità
    unit_standards = {
        'gr': 'g',
        'lt': 'l',
        'pezzi': 'pz',
        'pezzo': 'pz'
    }
    
    if unit in unit_standards:
        corrections.append(f"{number_str}{unit_standards[unit]}")
    
    # Conversioni automatiche per migliorare leggibilità
    if unit == 'g' and number >= 1000 and number <= 5000:
        corrections.append(f"{number/1000:.1f}kg")
    elif unit == 'ml' and number >= 1000 and number <= 10000:
        corrections.append(f"{number/1000:.1f}l")
    elif unit == 'kg' and number < 1 and number >= 0.01:
        corrections.append(f"{int(number*1000)}g")
    elif unit == 'l' and number < 1 and number >= 0.01:
        corrections.append(f"{int(number*1000)}ml")
    
    # Validazioni per range tipici (solo per valori fuori range)
    valid_ranges = {
        'g': (1, 5000),
        'kg': (0.01, 50),
        'ml': (1, 10000),
        'l': (0.01, 20),
        'pz': (1, 100)
    }
    
    if unit in valid_ranges:
        min_val, max_val = valid_ranges[unit]
        if not (min_val <= number <= max_val):
            # Se fuori range, forza conversioni
            if unit == 'g' and number > 5000:
                corrections.append(f"{number/1000:.1f}kg")
            elif unit == 'ml' and number > 10000:
                corrections.append(f"{number/1000:.1f}l")
            elif unit == 'kg' and number < 0.01:
                corrections.append(f"{int(number*1000)}g")
            elif unit == 'l' and number < 0.01:
                corrections.append(f"{int(number*1000)}ml")
    
    # Restituisce la correzione se disponibile, altrimenti la quantità originale
    return corrections[0] if corrections else quantity

def clean_product_name(raw_name):
    """Pulisce il nome del prodotto con post-processing avanzato"""
    if not raw_name:
        return None
    
    name = raw_name.strip()
    
    # Dizionario di correzioni OCR comuni
    ocr_corrections = {
        r'\bAl Kg\b': '',
        r'\bEtto Hg\b': '',
        r'\bLetto Hg\b': '',
        r'\bLetto\b': '',
        r'\bHg\b': '',
        r'\bTti Presenti In Volantino Non Sono.*': '',
        r'\bIo Ho Re Ca Over Ecc Salvo Er Ni\b': '',
        r'\bOzuslunai\b': 'Originali',
        r'\bQuizudioa\b': '',
        r'\bUi Ruisai\b': '',
        r'\bMpk\b': '',
        r'\bIduua\b': '',
        r'\bRfait\b': 'Parfait',
        r'\bSurg\b': 'Surgelati',
        r'\bNat\b': 'Naturale',
        r'\bCl Al\b': 'cl',
        r'\bGi Di Ta Gg\b': '',
        r'\bRimavera\b': 'Primavera',
        r'\bEstero\b': '',
        r'\bAng Vi\b': '',
        r'\bSnc\b': '',
        r'\bGe Ratuito\b': '',
        r'\bTel Dal\b': '',
        r'\bParcheggio Coperto\b': '',
        r'\bGratuite\b': '',
        r'\bEs Ip\b': '',
        r'\bPunt\b': '',
        r'\bIni\b': '',
        r'\bSeghe\b': '',
        r'\bAncesco Assisi\b': '',
        r'\bGall\b': '',
        r'\bFon\b': '',
        r'\bCetta Social Carl\b': '',
        r'\bCial Card\b': '',
        r'\bTutt\b': '',
        r'\bVe\b': '',
        r'\bQqnd\b': ''
    }
    
    # Applica correzioni OCR
    for pattern, replacement in ocr_corrections.items():
        name = re.sub(pattern, replacement, name, flags=re.IGNORECASE)
    
    # Rimuovi caratteri speciali mantenendo lettere accentate e numeri
    name = re.sub(r'[^a-zA-ZàèéìòùÀÈÉÌÒÙ0-9\s]', ' ', name)
    
    # Rimuovi spazi multipli
    name = re.sub(r'\s{2,}', ' ', name)
    
    # Rimuovi parole di una sola lettera (eccetto 'A' e 'E')
    words = name.split()
    meaningful_words = []
    for word in words:
        if len(word) > 1 or word.upper() in ['A', 'E']:
            meaningful_words.append(word)
    
    if not meaningful_words:
        return None
    
    # Capitalizza correttamente
    result = ' '.join(meaningful_words).strip()
    
    # Capitalizza la prima lettera di ogni parola
    result = ' '.join(word.capitalize() for word in result.split())
    
    return result if len(result) > 2 else None

def detect_brand(text):
    """Rileva la marca nel testo con algoritmo avanzato di matching"""
    if not text:
        return ""
    
    text_upper = text.upper().strip()
    
    # Preprocessing del testo per migliorare il matching
    # Rimuovi caratteri speciali e normalizza spazi
    clean_text = re.sub(r'[^A-ZÀÈÉÌÒÙ\s]', ' ', text_upper)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    # 1. Cerca corrispondenze esatte (priorità massima)
    for marca in MARCHE:
        marca_upper = marca.upper()
        if marca_upper == clean_text or marca_upper in clean_text.split():
            return marca
    
    # 2. Cerca corrispondenze esatte con tolleranza per caratteri speciali
    for marca in MARCHE:
        marca_clean = re.sub(r'[^A-ZÀÈÉÌÒÙ\s]', ' ', marca.upper())
        marca_clean = re.sub(r'\s+', ' ', marca_clean).strip()
        if marca_clean in clean_text:
            return marca
    
    # 3. Matching fuzzy per marche composte
    for marca in MARCHE:
        if len(marca.split()) > 1:
            words = marca.upper().split()
            matches = 0
            for word in words:
                if len(word) > 2 and word in clean_text:
                    matches += 1
            # Se almeno la metà delle parole della marca sono presenti
            if matches >= len(words) / 2 and matches > 0:
                return marca
    
    # 4. Matching parziale per parole significative (>3 caratteri)
    for marca in MARCHE:
        marca_words = marca.upper().split()
        for word in marca_words:
            if len(word) > 3 and word in clean_text:
                # Verifica che non sia una parola troppo comune
                common_words = ['LATTE', 'PASTA', 'SUGO', 'ACQUA', 'VINO']
                if word not in common_words:
                    return marca
    
    # 5. Logica speciale per categorie specifiche
    category_brands = {
        'OLIO': ['Bertolli', 'Monini', 'Carapelli', 'Sagra', 'Sasso', 'Colavita', 'Filippo Berio'],
        'PASTA': ['Barilla', 'De Cecco', 'Voiello', 'Buitoni', 'La Molisana'],
        'LATTE': ['Parmalat', 'Granarolo', 'Centrale del Latte', 'Mukki'],
        'TONNO': ['Rio Mare', 'Nostromo', 'Palmera', 'Mareblu'],
        'YOGURT': ['Danone', 'Yomo', 'Müller', 'Activia'],
        'CAFFE': ['Lavazza', 'Illy', 'Segafredo', 'Kimbo']
    }
    
    for category, brands in category_brands.items():
        if category in clean_text:
            for brand in brands:
                if brand.upper() in clean_text:
                    return brand
            # Se la categoria è presente ma non trova una marca specifica
            if category == 'OLIO':
                return 'Olio'
    
    # 6. Matching con edit distance per errori OCR comuni
    def levenshtein_distance(s1, s2):
        if len(s1) < len(s2):
            return levenshtein_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]
    
    # Cerca marche con piccole differenze (max 2 caratteri)
    for marca in MARCHE:
        if len(marca) > 4:  # Solo per marche abbastanza lunghe
            marca_upper = marca.upper()
            for word in clean_text.split():
                if len(word) > 3 and abs(len(word) - len(marca_upper)) <= 2:
                    if levenshtein_distance(word, marca_upper) <= 2:
                        return marca
    
    return ""

def categorize_product(name):
    """Categorizza il prodotto con logica avanzata e gerarchica"""
    if not name:
        return "altro"
    
    name_lower = name.lower().strip()
    
    # Dizionario delle categorie con parole chiave prioritarie
    categories = {
        "latticini": {
            "keywords": ["latte", "formaggio", "yogurt", "panna", "burro", "ricotta", "mascarpone", 
                        "mozzarella", "parmigiano", "gorgonzola", "taleggio", "asiago", "fontina", 
                        "pecorino", "stracchino", "robiola", "bel paese", "sottilette", "philadelphia", 
                        "bresso", "nonno nanni", "centrale", "granarolo", "parmalat", "mukki"],
            "brands": ["danone", "yomo", "müller", "activia", "galbani", "valtaleggio"]
        },
        "carne_salumi": {
            "keywords": ["prosciutto", "salame", "mortadella", "bresaola", "speck", "pancetta", 
                        "würstel", "wudy", "pollo", "tacchino", "manzo", "maiale", "vitello", "agnello"],
            "brands": ["beretta", "parmacotto", "negroni", "citterio", "rovagnati", "fiorucci", "aia", "amadori"]
        },
        "pesce": {
            "keywords": ["tonno", "salmone", "sardine", "acciughe", "sgombro", "polpo", "vongole", 
                        "merluzzo", "baccalà", "pesce", "frutti mare", "gamberi", "calamari"],
            "brands": ["rio mare", "nostromo", "palmera", "mareblu", "callipo", "ortiz"]
        },
        "pasta_riso": {
            "keywords": ["pasta", "spaghetti", "penne", "fusilli", "rigatoni", "farfalle", "linguine", 
                        "tagliatelle", "tortellini", "cappelletti", "gnocchi", "riso", "risotto"],
            "brands": ["barilla", "de cecco", "voiello", "buitoni", "la molisana", "divella", "rummo"]
        },
        "pane_dolci": {
            "keywords": ["pane", "biscotti", "crackers", "grissini", "fette biscottate", "cornetto", 
                        "brioche", "croissant", "torta", "dolce", "merendine", "snack dolci"],
            "brands": ["mulino bianco", "pavesi", "gentilini", "grissin bon", "saiwa", "ringo", "pan di stelle"]
        },
        "conserve_sughi": {
            "keywords": ["pomodoro", "passata", "pelati", "concentrato", "sugo", "pesto", "ragù", 
                        "conserve", "sottaceti", "olive", "capperi", "funghi"],
            "brands": ["mutti", "cirio", "valfrutta", "pomi", "star", "knorr", "maggi"]
        },
        "oli_condimenti": {
            "keywords": ["olio", "extravergine", "vergine", "aceto", "balsamico", "sale", "pepe", 
                        "spezie", "condimento", "salsa", "maionese", "ketchup"],
            "brands": ["bertolli", "monini", "carapelli", "sagra", "sasso", "colavita", "filippo berio"]
        },
        "bevande": {
            "keywords": ["acqua", "bevanda", "succo", "spremuta", "nettare", "tè", "tisana", 
                        "energy drink", "bibita", "gassata"],
            "brands": ["coca-cola", "pepsi", "fanta", "sprite", "san pellegrino", "levissima", "ferrarelle"]
        },
        "alcolici": {
            "keywords": ["vino", "birra", "prosecco", "champagne", "spumante", "liquore", "grappa", 
                        "whisky", "vodka", "gin", "rum", "cognac", "amaro", "aperitivo"],
            "brands": ["sangiovese", "chianti", "barolo", "brunello", "lambrusco"]
        },
        "caffe_te": {
            "keywords": ["caffè", "espresso", "cappuccino", "macchiato", "americano", "decaffeinato", 
                        "cialde", "capsule", "moka", "solubile"],
            "brands": ["lavazza", "illy", "segafredo", "kimbo", "bialetti"]
        },
        "dolciumi": {
            "keywords": ["cioccolato", "caramelle", "gomme", "mentine", "chewing gum", "lecca lecca", 
                        "nutella", "crema spalmabile", "miele", "marmellata", "confettura"],
            "brands": ["ferrero", "kinder", "haribo", "mentos", "tic tac", "chupa chups"]
        },
        "snack_salati": {
            "keywords": ["patatine", "chips", "salatini", "noccioline", "arachidi", "pistacchi", 
                        "mandorle", "noci", "frutta secca", "pop corn"],
            "brands": ["san carlo", "amica chips", "pringles", "lay's", "doritos", "fonzies"]
        },
        "gelati": {
            "keywords": ["gelato", "sorbetto", "ghiacciolo", "cornetto", "magnum", "coppa", "vaschetta"],
            "brands": ["sammontana", "algida", "ben & jerry's", "häagen-dazs", "carte d'or", "viennetta"]
        },
        "surgelati": {
            "keywords": ["surgelato", "congelato", "frozen", "bastoncini", "sofficini", "spinaci", 
                        "piselli", "minestrone", "verdure", "pizza", "lasagne"],
            "brands": ["findus", "orogel", "bonduelle", "quattro salti"]
        },
        "frutta_verdura": {
            "keywords": ["frutta", "verdura", "insalata", "pomodori", "carote", "patate", "cipolle", 
                        "zucchine", "melanzane", "peperoni", "mele", "pere", "banane", "arance"],
            "brands": ["valfrutta", "orogel", "bonduelle"]
        },
        "prodotti_bambini": {
            "keywords": ["omogeneizzato", "biscotto bambini", "pastina", "latte formula", "pannolini", 
                        "baby food", "prima infanzia"],
            "brands": ["plasmon", "mellin", "nipiol", "humana", "aptamil", "nestlé"]
        },
        "prodotti_bio": {
            "keywords": ["biologico", "bio", "organic", "naturale", "integrale", "senza glutine", 
                        "vegan", "vegetariano", "km zero"],
            "brands": ["alce nero", "ecor", "probios", "la terra e il cielo"]
        },
        "pulizia_casa": {
            "keywords": ["detersivo", "detergente", "sapone", "shampoo", "bagnoschiuma", "dentifricio", 
                        "spazzolino", "carta igienica", "fazzoletti", "tovaglioli"],
            "brands": ["dash", "dixan", "omino bianco", "scottex", "regina"]
        }
    }
    
    # Punteggi per ogni categoria
    category_scores = {}
    
    for category, data in categories.items():
        score = 0
        
        # Controllo parole chiave (peso maggiore)
        for keyword in data["keywords"]:
            if keyword in name_lower:
                # Parole più lunghe hanno peso maggiore
                score += len(keyword) * 2
                # Bonus se la parola è all'inizio del nome
                if name_lower.startswith(keyword):
                    score += 5
        
        # Controllo marche (peso medio)
        for brand in data.get("brands", []):
            if brand in name_lower:
                score += len(brand) * 1.5
        
        if score > 0:
            category_scores[category] = score
    
    # Restituisce la categoria con il punteggio più alto
    if category_scores:
        best_category = max(category_scores, key=category_scores.get)
        # Soglia minima per evitare categorizzazioni troppo deboli
        if category_scores[best_category] >= 3:
            return best_category
    
    # Fallback per categorie generiche
    generic_food_keywords = ["gr", "kg", "ml", "lt", "pz", "pezzi", "confezione"]
    if any(keyword in name_lower for keyword in generic_food_keywords):
        return "alimentari"
    
    return "altro"

def riconosci_prodotto_da_immagine(image_path):
    """Riconosce prodotto dall'immagine usando AI"""
    if not image_classifier:
        return "Sconosciuto"
    
    try:
        img = Image.open(image_path).convert("RGB")
        risultati = image_classifier(img)
        if risultati and len(risultati) > 0:
            return risultati[0]['label']
    except Exception as e:
        logger.warning(f"Errore riconoscimento immagine: {e}")
    
    return "Sconosciuto"

def extract_products_from_image(image_path, output_crop_folder="products"):
    """Estrae prodotti da una singola immagine"""
    if not os.path.exists(output_crop_folder):
        os.makedirs(output_crop_folder)
    
    img = cv2.imread(image_path)
    if img is None:
        logger.warning(f"Immagine non trovata: {image_path}")
        return []

    height, width = img.shape[:2]
    
    # Preprocessing avanzato migliorato
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Riduzione del rumore con filtro bilaterale
    gray = cv2.bilateralFilter(gray, 9, 75, 75)
    
    # Miglioramento del contrasto con CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    gray = clahe.apply(gray)
    
    # Sharpening per migliorare la nitidezza del testo
    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    gray = cv2.filter2D(gray, -1, kernel)
    
    # Morphological operations per pulire il testo
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1,1))
    gray = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
    
    # Threshold adattivo ottimizzato
    gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                 cv2.THRESH_BINARY, 15, 4)

    # OCR con dati dettagliati - metodo migliorato per estrazione prezzi
    data = pytesseract.image_to_data(gray, lang='ita', config='--psm 6', output_type=pytesseract.Output.DICT)
    n_boxes = len(data['level'])
    products = []
    
    # Estrai tutto il testo per analisi completa
    all_texts = []
    for i in range(n_boxes):
        text = data['text'][i].strip()
        if text:
            all_texts.append((text, data['left'][i], data['top'][i], data['width'][i], data['height'][i]))
    
    # Combina testo per ricerca prezzi più accurata
    full_text = " ".join([t[0] for t in all_texts])
    
    # Funzione migliorata per estrazione prezzo
    def extract_price_advanced(text):
        price = None
        method = "not_found"
        
        # Prima cerca prezzi con simbolo euro (€)
        euro_match = re.search(r"€\s*(\d{1,2}[,.]\d{1,2})|(\d{1,2}[,.]\d{1,2})\s*€", text)
        if euro_match:
            try:
                price_str = euro_match.group(1) or euro_match.group(2)
                price = float(price_str.replace(",", "."))
                method = "euro_symbol"
            except:
                pass
        
        # Se non trova prezzi con €, cerca prezzi generici ma con validazione più rigorosa
        if price is None:
            # Pattern più flessibili per catturare prezzi mal riconosciuti dall'OCR
            patterns = [
                r"(\d{1,2}[,.]\d{1,2})",  # Pattern standard
                r"alkg(\d{1,2}[,.]\d{1,2})",  # Pattern con prefisso OCR errato
                r"(\d{1,2}[,.]\d{1,2})\)i",  # Pattern con suffisso OCR errato
            ]
            
            for pattern in patterns:
                generic_match = re.search(pattern, text)
                if generic_match:
                    try:
                        potential_price = float(generic_match.group(1).replace(",", "."))
                        # Accetta solo prezzi ragionevoli per prodotti alimentari (0.10€ - 99.99€)
                        if 0.10 <= potential_price <= 99.99:
                            price = potential_price
                            method = "generic"
                            break
                    except:
                        continue
        
        return price, method
    
    # Cerca prezzi nel testo completo e nei singoli elementi
    found_prices = []
    
    # Analizza testo completo
    price, method = extract_price_advanced(full_text)
    if price:
        found_prices.append((price, method, "full_text"))
    
    # Analizza singoli elementi di testo
    for text, x, y, w, h in all_texts:
        price, method = extract_price_advanced(text)
        if price:
            found_prices.append((price, method, text, x, y, w, h))
    
    if not found_prices:
        return []
    
    # Priorità ai prezzi con simbolo euro, poi prendi il primo trovato
    euro_prices = [p for p in found_prices if p[1] == "euro_symbol"]
    selected_price_info = euro_prices[0] if euro_prices else found_prices[0]
    
    # Se il prezzo è stato trovato nel testo completo, usa il primo elemento per le coordinate
    if len(selected_price_info) == 3:  # full_text case
        price = selected_price_info[0]
        if all_texts:
            x, y, w, h = all_texts[0][1], all_texts[0][2], all_texts[0][3], all_texts[0][4]
        else:
            return []
    else:
        price, method, text, x, y, w, h = selected_price_info
    
    if price is None or price <= 0:
        return []

        # Ritaglio immagine prodotto con parametri adattivi ottimizzati
        # Usa le coordinate del prezzo trovato
        
        # Calcola dimensioni adattive basate su posizione e contenuto
        # Margini base ottimizzati
        margin_left = 400
        margin_right = 450
        margin_top = 350
        margin_bottom = 400
        
        # Adattamento basato sulla posizione del prezzo nell'immagine
        relative_x = x / width
        relative_y = y / height
        
        # Se il prezzo è vicino ai bordi, aumenta i margini verso il centro
        if relative_x < 0.2:  # Vicino al bordo sinistro
            margin_right += 100
        elif relative_x > 0.8:  # Vicino al bordo destro
            margin_left += 100
            
        if relative_y < 0.2:  # Vicino al bordo superiore
            margin_bottom += 100
        elif relative_y > 0.8:  # Vicino al bordo inferiore
            margin_top += 100
        
        # Adattamento basato sulle dimensioni del box del prezzo
        if w > 100:  # Box prezzo largo, probabilmente prodotto grande
            margin_left += 50
            margin_right += 50
            margin_top += 50
            margin_bottom += 50
        
        if h > 50:  # Box prezzo alto, potrebbe essere multi-linea
            margin_top += 100
            margin_bottom += 50
        
        # Calcola coordinate finali con controlli di bounds
        x1 = max(0, x - margin_left)
        y1 = max(0, y - margin_top)
        x2 = min(width, x + w + margin_right)
        y2 = min(height, y + h + margin_bottom)
        
        # Assicura dimensioni minime del crop
        min_crop_width = 300
        min_crop_height = 200
        
        if x2 - x1 < min_crop_width:
            center_x = (x1 + x2) // 2
            x1 = max(0, center_x - min_crop_width // 2)
            x2 = min(width, x1 + min_crop_width)
        
        if y2 - y1 < min_crop_height:
            center_y = (y1 + y2) // 2
            y1 = max(0, center_y - min_crop_height // 2)
            y2 = min(height, y1 + min_crop_height)
        
        # Ritaglia l'immagine del prodotto
        product_img = img[y1:y2, x1:x2]
        
        if product_img.size == 0:
            return []
        
        # Salva l'immagine ritagliata
        page_name = os.path.basename(image_path)
        crop_filename = f"{page_name}_{x}_{y}.png"
        crop_path = os.path.join(output_crop_folder, crop_filename)
        cv2.imwrite(crop_path, product_img)
    
        # OCR sul ritaglio per estrarre informazioni dettagliate
        try:
            crop_gray = cv2.cvtColor(product_img, cv2.COLOR_BGR2GRAY)
            
            # Preprocessing migliorato per il ritaglio
            crop_gray = cv2.bilateralFilter(crop_gray, 9, 75, 75)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            crop_gray = clahe.apply(crop_gray)
            
            # OCR con configurazione ottimizzata
            crop_text = pytesseract.image_to_string(crop_gray, lang='ita', config='--psm 6')
            
            # Correzione del testo estratto
            corrected_text = correggi_testo(crop_text)
            
            # Estrazione informazioni
            quantity = extract_quantity(corrected_text)
            if quantity:
                quantity = validate_and_correct_quantity(quantity)
            
            brand = detect_brand(corrected_text)
            product_name = clean_product_name(corrected_text)
            
            # Se il nome del prodotto non è chiaro, usa il riconoscimento immagini
            if len(product_name) < 3 or len(product_name.split()) < 2:
                try:
                    ai_product_name = riconosci_prodotto_da_immagine(crop_path)
                    if ai_product_name and len(ai_product_name) > len(product_name):
                        product_name = ai_product_name
                except Exception as e:
                    logger.warning(f"Errore riconoscimento AI: {e}")
            
            category = categorize_product(product_name + " " + (brand or ""))
            
            # Crea oggetto prodotto
            product = {
                "prodotto": product_name,
                "marca": brand,
                "quantita": quantity,
                "prezzo": price,
                "valuta": "EUR",
                "categoria": category,
                "immagine": crop_filename,
                "pagina": page_name
            }
            
            products.append(product)
            logger.info(f"Prodotto estratto: {product_name} - €{price:.2f}")
            
        except Exception as e:
            logger.error(f"Errore nell'elaborazione del ritaglio: {e}")
    
    return products

def deduplicate_products(products):
    """Rimuove prodotti duplicati"""
    unique = {}
    for p in products:
        key = (p["prodotto"], p["marca"], p["quantita"])
        if key in unique:
            # Mantieni il prezzo più basso
            unique[key]["prezzo"] = min(unique[key]["prezzo"], p["prezzo"])
        else:
            unique[key] = p
    return list(unique.values())

def main():
    """Funzione principale"""
    try:
        print("🚀 Avvio sistema OCR avanzato...")
        
        # URL del volantino
        pdf_url = "https://www.topsupermercati.it/volantino.pdf"
        
        # Download PDF
        pdf_path = download_pdf(pdf_url)
        
        # Conversione in immagini
        image_paths = ocr_pdf_images(pdf_path, "output", dpi=300, scale_factor=2)
        
        # Estrazione prodotti
        print("🔍 Estrazione prodotti in corso...")
        all_products = []
        
        for i, img_path in enumerate(image_paths, 1):
            print(f"📄 Elaborazione pagina {i}/{len(image_paths)}...")
            products = extract_products_from_image(img_path, "products")
            all_products.extend(products)
            print(f"   Trovati {len(products)} prodotti")
        
        # Deduplicazione
        print("🔄 Rimozione duplicati...")
        all_products = deduplicate_products([p for p in all_products if p["prezzo"] > 0])
        
        # Salvataggio risultati
        output_file = "output/prodotti_colab_adapted.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "metadati": {
                    "timestamp": datetime.now().isoformat(),
                    "sistema": "OCR Avanzato (Colab Adapted)",
                    "totale_prodotti": len(all_products),
                    "pagine_elaborate": len(image_paths),
                    "prezzo_medio": round(sum(p["prezzo"] for p in all_products) / len(all_products), 2) if all_products else 0
                },
                "prodotti": all_products
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Estrazione completata!")
        print(f"📊 Risultati:")
        print(f"   • Prodotti estratti: {len(all_products)}")
        print(f"   • Pagine elaborate: {len(image_paths)}")
        print(f"   • File salvato: {output_file}")
        
        if all_products:
            print(f"   • Prezzo medio: €{sum(p['prezzo'] for p in all_products) / len(all_products):.2f}")
            print(f"\n🔍 Anteprima primi 5 prodotti:")
            for i, prod in enumerate(all_products[:5], 1):
                print(f"   {i}. {prod['prodotto']} ({prod['marca']}) {prod['quantita']} - €{prod['prezzo']}")
        
        return output_file
        
    except Exception as e:
        logger.error(f"Errore durante l'esecuzione: {e}")
        raise

if __name__ == "__main__":
    main()