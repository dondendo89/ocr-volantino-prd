#!/usr/bin/env python3
"""
Estrattore SOLO Gemini AI per volantini
"""

import cv2
import numpy as np
from PIL import Image
import json
from pathlib import Path
import os
import shutil
from datetime import datetime
import logging
import base64
import requests
from io import BytesIO
import time

# Configurazione logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GeminiOnlyExtractor:
    def __init__(self, gemini_api_key=""):
        logger.info("🤖 Inizializzando estrattore SOLO Gemini AI...")
        
        self.gemini_api_key = gemini_api_key
        self.gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_api_key}"
        
        # Crea directory per le immagini dei prodotti
        self.product_images_dir = Path("gemini_only_product_images")
        if self.product_images_dir.exists():
            shutil.rmtree(self.product_images_dir)
        self.product_images_dir.mkdir(exist_ok=True)
    
    def image_to_base64(self, image_path):
        """Converte immagine in base64 per Gemini"""
        try:
            # Ridimensiona l'immagine per ridurre i tempi di upload
            with Image.open(image_path) as img:
                # Ridimensiona se troppo grande
                if img.width > 1024 or img.height > 1024:
                    img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
                
                # Converti in RGB se necessario
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Salva in memoria come JPEG
                buffer = BytesIO()
                img.save(buffer, format='JPEG', quality=85)
                buffer.seek(0)
                
                return base64.b64encode(buffer.getvalue()).decode('utf-8')
        except Exception as e:
            logger.error(f"❌ Errore conversione base64: {e}")
            return None
    
    def analyze_with_gemini(self, image_path, retry_count=3):
        """Analizza immagine con Gemini AI con retry"""
        for attempt in range(retry_count):
            try:
                logger.info(f"🤖 Tentativo {attempt + 1}/{retry_count} - Analizzando con Gemini: {Path(image_path).name}")
                
                # Converti immagine in base64
                image_base64 = self.image_to_base64(image_path)
                if not image_base64:
                    return None
                
                # Prompt ottimizzato per volantini supermercato
                prompt = """
Analizza questa immagine di un volantino di supermercato italiano e estrai SOLO le informazioni sui prodotti alimentari visibili.

Rispondi ESCLUSIVAMENTE con un JSON valido nel seguente formato:
{
  "prodotti": [
    {
      "nome": "nome completo del prodotto",
      "marca": "marca del prodotto (es: Barilla, Mulino Bianco, Granarolo)",
      "categoria": "categoria (latticini, pasta, bevande, dolci, etc.)",
      "prezzo": "prezzo in euro se visibile (es: 2.49)",
      "descrizione": "breve descrizione del prodotto"
    }
  ]
}

Regole importanti:
- Estrai SOLO prodotti alimentari chiaramente visibili
- Se non vedi un prezzo, scrivi "Non visibile"
- Se non riconosci una marca, scrivi "Non identificata"
- Concentrati sui prodotti più evidenti e leggibili
- Massimo 10 prodotti per immagine
"""
                
                # Payload per Gemini
                payload = {
                    "contents": [{
                        "parts": [
                            {"text": prompt},
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": image_base64
                                }
                            }
                        ]
                    }],
                    "generationConfig": {
                        "temperature": 0.1,
                        "topK": 1,
                        "topP": 1,
                        "maxOutputTokens": 2048
                    }
                }
                
                # Chiamata API con timeout più lungo
                headers = {'Content-Type': 'application/json'}
                response = requests.post(
                    self.gemini_url, 
                    json=payload, 
                    headers=headers, 
                    timeout=120  # 2 minuti di timeout
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if 'candidates' in result and len(result['candidates']) > 0:
                        text_response = result['candidates'][0]['content']['parts'][0]['text']
                        
                        # Estrai JSON dalla risposta
                        try:
                            # Pulisci la risposta
                            text_response = text_response.strip()
                            if text_response.startswith('```json'):
                                text_response = text_response[7:]
                            if text_response.endswith('```'):
                                text_response = text_response[:-3]
                            
                            # Trova il JSON nella risposta
                            json_start = text_response.find('{')
                            json_end = text_response.rfind('}') + 1
                            if json_start != -1 and json_end != -1:
                                json_str = text_response[json_start:json_end]
                                parsed_json = json.loads(json_str)
                                logger.info(f"✅ Gemini ha analizzato con successo l'immagine")
                                return parsed_json
                        except json.JSONDecodeError as e:
                            logger.warning(f"⚠️ Errore parsing JSON da Gemini: {e}")
                            logger.info(f"Risposta Gemini: {text_response[:300]}...")
                            if attempt == retry_count - 1:
                                return None
                            continue
                elif response.status_code == 429:
                    # Rate limit - aspetta prima di riprovare
                    wait_time = (attempt + 1) * 10
                    logger.warning(f"⏳ Rate limit raggiunto, aspetto {wait_time} secondi...")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"❌ Errore API Gemini: {response.status_code} - {response.text[:200]}")
                    if attempt == retry_count - 1:
                        return None
                    time.sleep(5)
                    continue
                    
            except requests.exceptions.Timeout:
                logger.warning(f"⏰ Timeout tentativo {attempt + 1}, riprovo...")
                if attempt == retry_count - 1:
                    logger.error("❌ Tutti i tentativi falliti per timeout")
                    return None
                time.sleep(10)
                continue
            except Exception as e:
                logger.error(f"❌ Errore chiamata Gemini tentativo {attempt + 1}: {e}")
                if attempt == retry_count - 1:
                    return None
                time.sleep(5)
                continue
        
        return None
    
    def save_product_image(self, image_path, product_info, image_name, region_id):
        """Salva immagine del prodotto (copia dell'originale ridimensionata)"""
        try:
            product_name = product_info.get('nome', 'prodotto_sconosciuto')
            # Pulisci il nome per il filesystem
            import re
            product_name = re.sub(r'[^\w\s-]', '', product_name).strip()
            product_name = re.sub(r'[-\s]+', '_', product_name)
            
            filename = f"{image_name}_{product_name}_region_{region_id}.jpg"
            filepath = self.product_images_dir / filename
            
            # Carica e ridimensiona l'immagine originale
            with Image.open(image_path) as img:
                # Converti in RGB se necessario
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Ridimensiona mantenendo le proporzioni
                img.thumbnail((600, 400), Image.Resampling.LANCZOS)
                
                # Salva con qualità ottimizzata
                img.save(filepath, 'JPEG', quality=85, optimize=True)
            
            logger.info(f"💾 Salvata: {filename}")
            return str(filepath)
        except Exception as e:
            logger.warning(f"⚠️ Errore salvataggio: {e}")
            return None
    
    def process_image(self, image_path):
        """Elabora una singola immagine con SOLO Gemini"""
        logger.info(f"📸 Elaborando: {Path(image_path).name}")
        
        try:
            image_name = Path(image_path).stem
            results = []
            
            # Analisi con Gemini AI
            gemini_result = self.analyze_with_gemini(image_path)
            
            if gemini_result and 'prodotti' in gemini_result:
                logger.info(f"🤖 Gemini ha trovato {len(gemini_result['prodotti'])} prodotti")
                
                for i, prodotto in enumerate(gemini_result['prodotti']):
                    # Pulisci e valida i dati
                    nome = prodotto.get('nome', 'Prodotto sconosciuto')
                    marca = prodotto.get('marca', 'Non identificata')
                    categoria = prodotto.get('categoria', 'Non specificata')
                    prezzo_str = prodotto.get('prezzo', 'Non visibile')
                    descrizione = prodotto.get('descrizione', '')
                    
                    # Estrai prezzo numerico
                    prezzo = None
                    if prezzo_str and prezzo_str != 'Non visibile':
                        import re
                        price_match = re.search(r'(\d+[.,]\d{1,2}|\d+)', str(prezzo_str))
                        if price_match:
                            try:
                                prezzo = float(price_match.group(1).replace(',', '.'))
                            except ValueError:
                                prezzo = None
                    
                    # Salva immagine del prodotto
                    image_path_saved = self.save_product_image(image_path, prodotto, image_name, i)
                    
                    result = {
                        'nome': nome,
                        'marca': marca,
                        'categoria': categoria,
                        'tipo_prodotto': nome.split()[-1] if nome else 'Sconosciuto',
                        'prezzo': prezzo,
                        'prezzo_originale': prezzo_str,
                        'descrizione': descrizione,
                        'fonte': 'Gemini AI',
                        'immagine_prodotto': image_path_saved or 'Non disponibile',
                        'immagine_originale': str(image_path)
                    }
                    
                    results.append(result)
            else:
                logger.warning(f"⚠️ Gemini non ha trovato prodotti in {Path(image_path).name}")
            
            logger.info(f"🛒 Totale prodotti estratti: {len(results)}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Errore elaborazione {image_path}: {e}")
            return []
    
    def run(self):
        """Esegue l'estrazione su tutte le immagini"""
        logger.info("🚀 Avvio estrazione SOLO Gemini AI...")
        
        # Trova immagini
        image_dir = Path('output')
        image_files = list(image_dir.glob('page_*.png'))[:2]  # Prime 2 immagini per test
        
        if not image_files:
            logger.error("❌ Nessuna immagine trovata")
            return
        
        logger.info(f"📁 Trovate {len(image_files)} immagini da elaborare")
        
        all_results = []
        
        for i, image_file in enumerate(image_files):
            logger.info(f"📊 Progresso: {i+1}/{len(image_files)}")
            results = self.process_image(image_file)
            all_results.extend(results)
            
            # Pausa tra le immagini per evitare rate limiting
            if i < len(image_files) - 1:
                logger.info("⏳ Pausa di 5 secondi tra le immagini...")
                time.sleep(5)
        
        # Salva risultati
        output_file = 'gemini_only_results.json'
        results_data = {
            'timestamp': datetime.now().isoformat(),
            'method': 'Gemini AI Only Extractor',
            'total_products': len(all_results),
            'images_processed': len(image_files),
            'products': all_results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Risultati salvati in {output_file}")
        logger.info(f"📊 Totale prodotti estratti: {len(all_results)}")
        logger.info(f"📁 Immagini prodotti salvate in: {self.product_images_dir}")
        
        # Mostra riepilogo
        brands = set(r['marca'] for r in all_results if r['marca'] != 'Non identificata')
        categories = set(r['categoria'] for r in all_results)
        
        logger.info(f"🏷️ Marche identificate: {len(brands)} - {list(brands)[:5]}")
        logger.info(f"📦 Categorie trovate: {len(categories)} - {list(categories)[:5]}")
        
        # Mostra alcuni prodotti estratti
        if all_results:
            logger.info("🛒 Esempi di prodotti estratti:")
            for result in all_results[:3]:
                logger.info(f"   - {result['nome']} ({result['marca']}) - {result.get('prezzo_originale', 'N/A')}")
        
if __name__ == "__main__":
    extractor = GeminiOnlyExtractor()
    extractor.run()