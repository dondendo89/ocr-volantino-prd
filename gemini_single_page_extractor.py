#!/usr/bin/env python3
"""
Estrattore Gemini AI per SOLO la prima pagina del volantino
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

class GeminiSinglePageExtractor:
    def __init__(self, gemini_api_key="AIzaSyCkk723717D_-bBCL9EuxlF0sV6_Evjis8"):
        logger.info("🤖 Inizializzando estrattore Gemini per PRIMA PAGINA...")
        
        self.gemini_api_key = gemini_api_key
        self.gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_api_key}"
        
        # Crea directory per le immagini dei prodotti
        self.product_images_dir = Path("products")
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
                logger.info(f"🤖 Tentativo {attempt + 1}/{retry_count} - Analizzando PRIMA PAGINA con Gemini")
                
                # Converti immagine in base64
                image_base64 = self.image_to_base64(image_path)
                if not image_base64:
                    return None
                
                # Prompt ottimizzato per la prima pagina del volantino
                prompt = """
Analizza questa PRIMA PAGINA di un volantino di supermercato italiano e estrai TUTTI i prodotti alimentari visibili con la massima precisione.

Rispondi ESCLUSIVAMENTE con un JSON valido nel seguente formato:
{
  "prodotti": [
    {
      "nome": "nome completo e dettagliato del prodotto",
      "marca": "marca del prodotto (es: Barilla, Mulino Bianco, Granarolo, Pepsi, Coca Cola)",
      "categoria": "categoria specifica (pasta, bevande, latticini, dolci, salumi, etc.)",
      "prezzo": "prezzo esatto in euro se visibile (es: 2.49)",
      "descrizione": "descrizione completa incluso peso/quantità",
      "posizione": "posizione nell'immagine (alto, centro, basso, sinistra, destra)"
    }
  ]
}

Regole IMPORTANTI:
- Estrai TUTTI i prodotti alimentari visibili nella prima pagina
- Sii molto preciso con nomi e marche
- Se vedi un prezzo, riportalo esattamente
- Se non vedi un prezzo, scrivi "Non visibile"
- Se non riconosci una marca, scrivi "Non identificata"
- Includi anche prodotti parzialmente visibili
- Concentrati su prodotti di marca italiana e internazionale
- Massimo 15 prodotti per evitare sovraccarico
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
                        "maxOutputTokens": 3048
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
                                logger.info(f"✅ Gemini ha analizzato con successo la PRIMA PAGINA")
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
    
    def get_crop_coordinates(self, posizione, img_width, img_height):
        """Calcola le coordinate di ritaglio basate sulla posizione del prodotto"""
        # Dimensioni del ritaglio più grandi (percentuale dell'immagine)
        crop_width_pct = 0.45  # Aumentato da 0.3 a 0.45
        crop_height_pct = 0.55  # Aumentato da 0.4 a 0.55
        
        # Calcola le coordinate basate sulla posizione con margini ridotti
        if 'sinistra' in posizione.lower():
            x_start = 0.02  # Più vicino al bordo
        elif 'destra' in posizione.lower():
            x_start = 0.53  # Aggiustato per il ritaglio più grande
        else:  # centro
            x_start = 0.275  # Centrato meglio
            
        if 'alto' in posizione.lower():
            y_start = 0.02  # Più vicino al bordo superiore
        elif 'basso' in posizione.lower():
            y_start = 0.43  # Aggiustato per il ritaglio più grande
        else:  # centro
            y_start = 0.225  # Centrato meglio
            
        # Converti in coordinate pixel
        x1 = int(x_start * img_width)
        y1 = int(y_start * img_height)
        x2 = int((x_start + crop_width_pct) * img_width)
        y2 = int((y_start + crop_height_pct) * img_height)
        
        # Assicurati che le coordinate siano dentro i limiti
        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(img_width, x2)
        y2 = min(img_height, y2)
        
        return (x1, y1, x2, y2)
    
    def save_product_image(self, image_path, product_info, region_id):
        """Salva solo la parte dell'immagine dove si trova il prodotto"""
        try:
            product_name = product_info.get('nome', 'prodotto_sconosciuto')
            posizione = product_info.get('posizione', 'centro')
            
            # Pulisci il nome per il filesystem
            import re
            product_name = re.sub(r'[^\w\s-]', '', product_name).strip()
            product_name = re.sub(r'[-\s]+', '_', product_name)
            
            # Nome file per l'immagine ritagliata del prodotto
            filename = f"prodotto_{product_name}_{region_id}.jpg"
            filepath = self.product_images_dir / filename
            
            # Carica l'immagine originale
            with Image.open(image_path) as img:
                # Converti in RGB se necessario
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Calcola le coordinate di ritaglio basate sulla posizione
                crop_coords = self.get_crop_coordinates(posizione, img.width, img.height)
                
                # Ritaglia la parte specifica dove si trova il prodotto
                cropped_img = img.crop(crop_coords)
                
                # Ridimensiona il ritaglio per una dimensione più grande
                cropped_img.thumbnail((500, 400), Image.Resampling.LANCZOS)
                
                # Salva l'immagine ritagliata del prodotto
                cropped_img.save(filepath, 'JPEG', quality=95, optimize=True)
            
            logger.info(f"✂️ Immagine prodotto ritagliata salvata: {filename} (posizione: {posizione})")
            return str(filepath)
        except Exception as e:
            logger.warning(f"⚠️ Errore salvataggio immagine ritagliata: {e}")
            return None
    
    def process_first_page(self):
        """Elabora SOLO la prima pagina del volantino"""
        logger.info("📸 Elaborando PRIMA PAGINA del volantino...")
        
        try:
            # Cerca la prima pagina
            image_dir = Path('output')
            first_page = image_dir / 'page_1.png'
            
            if not first_page.exists():
                logger.error("❌ Prima pagina non trovata: page_1.png")
                return []
            
            results = []
            
            # Analisi con Gemini AI
            gemini_result = self.analyze_with_gemini(first_page)
            
            if gemini_result and 'prodotti' in gemini_result:
                logger.info(f"🤖 Gemini ha trovato {len(gemini_result['prodotti'])} prodotti nella PRIMA PAGINA")
                
                for i, prodotto in enumerate(gemini_result['prodotti']):
                    # Pulisci e valida i dati
                    nome = prodotto.get('nome', 'Prodotto sconosciuto')
                    marca = prodotto.get('marca', 'Non identificata')
                    categoria = prodotto.get('categoria', 'Non specificata')
                    prezzo_str = prodotto.get('prezzo', 'Non visibile')
                    descrizione = prodotto.get('descrizione', '')
                    posizione = prodotto.get('posizione', 'Non specificata')
                    
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
                    
                    # Salva immagine singola del prodotto
                    image_path_saved = self.save_product_image(first_page, prodotto, i)
                    
                    result = {
                        'nome': nome,
                        'marca': marca,
                        'categoria': categoria,
                        'tipo_prodotto': nome.split()[-1] if nome else 'Sconosciuto',
                        'prezzo': prezzo,
                        'prezzo_originale': prezzo_str,
                        'descrizione': descrizione,
                        'posizione': posizione,
                        'fonte': 'Gemini AI - Prima Pagina',
                        'immagine_singola_prodotto': str(Path('products') / Path(image_path_saved).name) if image_path_saved else 'Non disponibile',
                        'immagine_originale': str(first_page)
                    }
                    
                    results.append(result)
            else:
                logger.warning("⚠️ Gemini non ha trovato prodotti nella prima pagina")
            
            logger.info(f"🛒 Totale prodotti estratti dalla PRIMA PAGINA: {len(results)}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Errore elaborazione prima pagina: {e}")
            return []
    
    def run(self):
        """Esegue l'estrazione sulla PRIMA PAGINA"""
        logger.info("🚀 Avvio estrazione Gemini AI - SOLO PRIMA PAGINA...")
        
        # Elabora solo la prima pagina
        all_results = self.process_first_page()
        
        # Salva risultati
        output_file = 'page_1_gemini_results.json'
        results_data = {
            'timestamp': datetime.now().isoformat(),
            'method': 'Gemini AI - Prima Pagina Only',
            'page_analyzed': 'page_1.png',
            'total_products': len(all_results),
            'products': all_results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Risultati salvati in {output_file}")
        logger.info(f"📊 Totale prodotti estratti: {len(all_results)}")
        logger.info(f"📁 Immagini prodotti salvate in: {self.product_images_dir}")
        
        # Mostra riepilogo dettagliato
        if all_results:
            brands = set(r['marca'] for r in all_results if r['marca'] != 'Non identificata')
            categories = set(r['categoria'] for r in all_results)
            
            logger.info(f"🏷️ Marche identificate: {len(brands)} - {list(brands)[:10]}")
            logger.info(f"📦 Categorie trovate: {len(categories)} - {list(categories)[:10]}")
            
            # Mostra tutti i prodotti estratti
            logger.info("🛒 TUTTI i prodotti estratti dalla PRIMA PAGINA:")
            for i, result in enumerate(all_results, 1):
                prezzo_display = result.get('prezzo_originale', 'N/A')
                logger.info(f"   {i:2d}. {result['nome']} ({result['marca']}) - {prezzo_display} - {result['posizione']}")
        else:
            logger.warning("⚠️ Nessun prodotto estratto dalla prima pagina")
        
if __name__ == "__main__":
    extractor = GeminiSinglePageExtractor()
    extractor.run()