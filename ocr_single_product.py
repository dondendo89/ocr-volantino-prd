#!/usr/bin/env python3
"""
Script OCR per processare un singolo prodotto
Versione semplificata di colab_adapted.py per test rapidi
"""

import os
import sys
import json
from datetime import datetime
from PIL import Image
import pytesseract
import cv2
import numpy as np
import re
from transformers import pipeline
import logging

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ocr_single_product.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configurazione Tesseract per diversi sistemi operativi
if os.name == 'posix':
    # Per macOS con Homebrew
    if os.path.exists('/opt/homebrew/bin/tesseract'):
        pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'
    elif os.path.exists('/usr/local/bin/tesseract'):
        pytesseract.pytesseract.tesseract_cmd = '/usr/local/bin/tesseract'
    # Per Linux (Render)
    elif os.path.exists('/usr/bin/tesseract'):
        pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

class SingleProductOCR:
    def __init__(self):
        self.classifier = None
        self.load_models()
    
    def load_models(self):
        """Carica i modelli AI necessari"""
        try:
            print("🤖 Caricamento modello di classificazione...")
            self.classifier = pipeline(
                "image-classification",
                model="google/vit-base-patch16-224",
                device=-1  # CPU
            )
            print("✅ Modello caricato con successo")
        except Exception as e:
            print(f"⚠️ Errore caricamento modello: {e}")
            self.classifier = None
    
    def preprocess_image(self, image_path):
        """Preprocessa l'immagine per migliorare l'OCR"""
        try:
            # Carica l'immagine
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Impossibile caricare l'immagine: {image_path}")
            
            # Converti in scala di grigi
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # Applica filtro per ridurre il rumore
            denoised = cv2.medianBlur(gray, 3)
            
            # Migliora il contrasto
            enhanced = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8)).apply(denoised)
            
            # Binarizzazione adattiva
            binary = cv2.adaptiveThreshold(
                enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            
            return binary
        except Exception as e:
            logger.error(f"Errore preprocessing: {e}")
            return None
    
    def extract_text_from_image(self, image_path):
        """Estrae il testo dall'immagine usando OCR"""
        try:
            # Preprocessa l'immagine
            processed_img = self.preprocess_image(image_path)
            if processed_img is None:
                return ""
            
            # Esegui OCR
            custom_config = r'--oem 3 --psm 6 -l ita'
            text = pytesseract.image_to_string(processed_img, config=custom_config)
            
            return text.strip()
        except Exception as e:
            logger.error(f"Errore OCR: {e}")
            return ""
    
    def extract_price(self, text):
        """Estrae il prezzo dal testo"""
        # Pattern per prezzi in formato europeo
        price_patterns = [
            r'€\s*([0-9]+[,.]?[0-9]*)',
            r'([0-9]+[,.]?[0-9]*)\s*€',
            r'([0-9]+[,.]?[0-9]*)\s*euro',
            r'prezzo[:\s]*([0-9]+[,.]?[0-9]*)',
            r'([0-9]+[,.]?[0-9]*)\s*eur'
        ]
        
        for pattern in price_patterns:
            matches = re.findall(pattern, text.lower())
            if matches:
                price_str = matches[0]
                # Normalizza il formato del prezzo
                price_str = price_str.replace(',', '.')
                try:
                    return float(price_str)
                except ValueError:
                    continue
        
        return None
    
    def extract_product_info(self, text):
        """Estrae informazioni del prodotto dal testo"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        product_info = {
            'nome': '',
            'marca': '',
            'prezzo': None,
            'quantita': '',
            'categoria': '',
            'testo_completo': text
        }
        
        # Estrai prezzo
        product_info['prezzo'] = self.extract_price(text)
        
        # Cerca nome prodotto (di solito nelle prime righe)
        if lines:
            product_info['nome'] = lines[0]
        
        # Cerca quantità
        quantity_patterns = [
            r'([0-9]+\s*[gkml]+)',
            r'([0-9]+\s*pz)',
            r'([0-9]+\s*pezzi)',
            r'([0-9]+\s*lt)',
            r'([0-9]+\s*kg)'
        ]
        
        for pattern in quantity_patterns:
            matches = re.findall(pattern, text.lower())
            if matches:
                product_info['quantita'] = matches[0]
                break
        
        # Cerca marca (parole in maiuscolo)
        brand_matches = re.findall(r'\b[A-Z]{2,}\b', text)
        if brand_matches:
            product_info['marca'] = brand_matches[0]
        
        return product_info
    
    def classify_product(self, image_path):
        """Classifica il prodotto usando AI"""
        if not self.classifier:
            return "Non classificato"
        
        try:
            image = Image.open(image_path)
            results = self.classifier(image)
            if results:
                return results[0]['label']
        except Exception as e:
            logger.error(f"Errore classificazione: {e}")
        
        return "Non classificato"
    
    def process_single_product(self, image_path):
        """Processa una singola immagine di prodotto"""
        print(f"\n🔍 Analisi prodotto: {image_path}")
        print("=" * 50)
        
        if not os.path.exists(image_path):
            print(f"❌ File non trovato: {image_path}")
            return None
        
        # Estrai testo con OCR
        print("📝 Estrazione testo con OCR...")
        text = self.extract_text_from_image(image_path)
        
        if not text:
            print("❌ Nessun testo estratto dall'immagine")
            return None
        
        print(f"📄 Testo estratto:\n{text}\n")
        
        # Estrai informazioni prodotto
        print("🔍 Analisi informazioni prodotto...")
        product_info = self.extract_product_info(text)
        
        # Classifica prodotto
        print("🤖 Classificazione AI...")
        category = self.classify_product(image_path)
        product_info['categoria_ai'] = category
        
        # Aggiungi metadati
        product_info['timestamp'] = datetime.now().isoformat()
        product_info['file_immagine'] = os.path.basename(image_path)
        
        return product_info

def main():
    print("🚀 OCR Singolo Prodotto")
    print("=" * 40)
    
    # Inizializza OCR
    ocr = SingleProductOCR()
    
    # Chiedi percorso immagine
    image_path = input("📁 Inserisci il percorso dell'immagine (o premi Enter per usare un'immagine di esempio): ").strip()
    
    if not image_path:
        # Cerca immagini di esempio nella directory corrente
        example_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
        example_files = []
        
        for file in os.listdir('.'):
            if any(file.lower().endswith(ext) for ext in example_extensions):
                example_files.append(file)
        
        if example_files:
            print(f"\n📋 Immagini disponibili:")
            for i, file in enumerate(example_files, 1):
                print(f"  {i}. {file}")
            
            try:
                choice = int(input("\n🔢 Scegli un numero (o 0 per inserire percorso manuale): "))
                if 1 <= choice <= len(example_files):
                    image_path = example_files[choice - 1]
                elif choice == 0:
                    image_path = input("📁 Inserisci il percorso dell'immagine: ").strip()
            except ValueError:
                print("❌ Scelta non valida")
                return
        else:
            print("❌ Nessuna immagine di esempio trovata nella directory corrente")
            print("💡 Suggerimento: metti un'immagine di prodotto nella directory e riprova")
            return
    
    if not image_path:
        print("❌ Nessun percorso immagine specificato")
        return
    
    # Processa il prodotto
    result = ocr.process_single_product(image_path)
    
    if result:
        print("\n✅ RISULTATI ANALISI")
        print("=" * 30)
        print(f"📦 Nome: {result.get('nome', 'N/A')}")
        print(f"🏷️ Marca: {result.get('marca', 'N/A')}")
        print(f"💰 Prezzo: €{result.get('prezzo', 'N/A')}")
        print(f"📏 Quantità: {result.get('quantita', 'N/A')}")
        print(f"🗂️ Categoria: {result.get('categoria', 'N/A')}")
        print(f"🤖 Categoria AI: {result.get('categoria_ai', 'N/A')}")
        
        # Salva risultati
        output_file = f"prodotto_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Risultati salvati in: {output_file}")
    else:
        print("❌ Impossibile analizzare il prodotto")

if __name__ == "__main__":
    main()