#!/usr/bin/env python3
"""
Estrattore Multi-AI per volantini con fallback
Supporta Gemini (primario), Moondream2 e Qwen2.5-VL come backup
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
import fitz  # PyMuPDF per conversione PDF
from urllib.parse import urlparse
from urllib.request import urlretrieve
from product_card_generator import ProductCardGenerator

# Configurazione logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Importazioni per AI fallback
try:
    from moondream_extractor import MoondreamExtractor
    MOONDREAM_AVAILABLE = True
except ImportError:
    MOONDREAM_AVAILABLE = False
    logger.warning("⚠️ Moondream non disponibile")

try:
    from qwen_extractor import QwenExtractor
    QWEN_AVAILABLE = True
except ImportError:
    QWEN_AVAILABLE = False
    logger.warning("⚠️ Qwen2.5-VL non disponibile")

class MultiAIExtractor:
    def __init__(self, gemini_api_key="", gemini_api_key_2=None, job_id=None, db_manager=None, enable_fallback=True, supermercato_nome="SUPERMERCATO"):
        logger.info("🤖 Inizializzando estrattore Multi-AI con fallback...")
        
        self.gemini_api_key = gemini_api_key
        self.gemini_api_key_2 = gemini_api_key_2 or os.getenv('GEMINI_API_KEY_2')
        self.gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={gemini_api_key}"
        self.gemini_url_2 = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_api_key_2}" if self.gemini_api_key_2 else None
        self.job_id = job_id
        self.db_manager = db_manager
        self.enable_fallback = enable_fallback
        self.current_key_index = 0  # Per alternare tra le chiavi
        self.api_keys = [self.gemini_api_key]
        self.api_urls = [self.gemini_url]
        
        if self.gemini_api_key_2:
            self.api_keys.append(self.gemini_api_key_2)
            self.api_urls.append(self.gemini_url_2)
            logger.info("✅ Configurate 2 chiavi API Gemini per ottimizzazione rate limiting")
        else:
            logger.info("✅ Configurata 1 chiave API Gemini")
        
        # Inizializza estrattori di fallback
        self.moondream_extractor = None
        self.qwen_extractor = None
        
        if enable_fallback:
            if MOONDREAM_AVAILABLE:
                try:
                    self.moondream_extractor = MoondreamExtractor(job_id=job_id, db_manager=db_manager)
                    logger.info("✅ Moondream2 inizializzato come fallback")
                except Exception as e:
                    logger.warning(f"⚠️ Errore inizializzazione Moondream: {e}")
            
            if QWEN_AVAILABLE:
                try:
                    self.qwen_extractor = QwenExtractor(job_id=job_id, db_manager=db_manager)
                    logger.info("✅ Qwen2.5-VL inizializzato come fallback")
                except Exception as e:
                    logger.warning(f"⚠️ Errore inizializzazione Qwen: {e}")
        
        # Crea directory per le immagini temporanee
        self.temp_dir = Path(f"temp_processing_{job_id}" if job_id else "temp_processing")
        # Non eliminare la directory se esiste già per evitare di perdere le immagini
        self.temp_dir.mkdir(exist_ok=True)
        
        # Crea directory per le immagini dei prodotti
        self.product_images_dir = Path("multi_ai_product_images")
        self.product_images_dir.mkdir(exist_ok=True)
        
        # Inizializza il generatore di card prodotto
        self.card_generator = ProductCardGenerator()
        
        # Salva il nome del supermercato
        self.supermercato_nome = supermercato_nome
    
    def download_pdf_from_url(self, url):
        """Scarica PDF da URL"""
        try:
            logger.info(f"📥 Scaricando PDF da URL: {url}")
            parsed_url = urlparse(url)
            filename = f"downloaded_pdf_{self.job_id}.pdf"
            pdf_path = self.temp_dir / filename
            
            urlretrieve(url, pdf_path)
            logger.info(f"✅ PDF scaricato: {pdf_path}")
            return str(pdf_path)
        except Exception as e:
            logger.error(f"❌ Errore download PDF: {e}")
            return None
    
    def convert_pdf_to_images(self, pdf_path):
        """Converte PDF in immagini PNG"""
        try:
            logger.info(f"📄 Convertendo PDF in immagini: {pdf_path}")
            doc = fitz.open(pdf_path)
            image_paths = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                # Aumenta la risoluzione per migliore qualità
                mat = fitz.Matrix(2.0, 2.0)  # 2x zoom
                pix = page.get_pixmap(matrix=mat)
                
                image_filename = f"page_{page_num + 1}.png"
                image_path = self.temp_dir / image_filename
                pix.save(str(image_path))
                image_paths.append(str(image_path))
                
                logger.info(f"📸 Convertita pagina {page_num + 1}: {image_filename}")
            
            doc.close()
            logger.info(f"✅ PDF convertito in {len(image_paths)} immagini")
            return image_paths
        except Exception as e:
            logger.error(f"❌ Errore conversione PDF: {e}")
            return []
    
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
    
    def get_next_api_config(self):
        """Ottiene la prossima configurazione API per bilanciare il carico"""
        if len(self.api_keys) > 1:
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        
        current_key = self.api_keys[self.current_key_index]
        current_url = self.api_urls[self.current_key_index]
        
        logger.info(f"🔄 Usando chiave API {self.current_key_index + 1}/{len(self.api_keys)}")
        return current_key, current_url
    
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
                
                # Ottieni configurazione API corrente
                current_key, current_url = self.get_next_api_config()
                
                # Chiamata API con timeout ottimizzato
                headers = {'Content-Type': 'application/json'}
                response = requests.post(
                    current_url, 
                    json=payload, 
                    headers=headers, 
                    timeout=45  # 45 secondi di timeout per evitare blocchi
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
                    # Rate limit - gestione intelligente con più chiavi
                    if len(self.api_keys) > 1:
                        # Se abbiamo più chiavi, prova con la prossima invece di aspettare
                        logger.warning(f"⏳ Rate limit su chiave {self.current_key_index + 1}, cambio chiave...")
                        current_key, current_url = self.get_next_api_config()
                        continue
                    else:
                        # Se abbiamo solo una chiave, usa exponential backoff
                        wait_time = min(5 * (2 ** attempt), 30)  # Ridotto: max 30s invece di 60s
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
    
    def save_product_image(self, image_path, product_info, image_name, region_id, supermercato_nome="SUPERMERCATO"):
        """Salva immagine del prodotto come card strutturata"""
        try:
            # Genera e salva la card prodotto professionale
            card_path = self.card_generator.save_product_card(
                product_info=product_info,
                original_image_path=image_path,
                output_dir=self.product_images_dir,
                image_name=image_name,
                region_id=region_id,
                supermercato_nome=supermercato_nome
            )
            
            if card_path:
                logger.info(f"💾 Card prodotto salvata: {Path(card_path).name}")
                return card_path
            else:
                # Fallback al metodo originale se la card fallisce
                return self._save_original_image_fallback(image_path, product_info, image_name, region_id)
                
        except Exception as e:
            logger.warning(f"⚠️ Errore generazione card, uso fallback: {e}")
            return self._save_original_image_fallback(image_path, product_info, image_name, region_id)
    
    def _save_original_image_fallback(self, image_path, product_info, image_name, region_id):
        """Metodo fallback per salvare l'immagine originale ridimensionata"""
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
            
            logger.info(f"💾 Salvata (fallback): {filename}")
            return str(filepath)
        except Exception as e:
            logger.warning(f"⚠️ Errore salvataggio fallback: {e}")
            return None
    
    def convert_price_to_float(self, price_value):
        """Converte un prezzo dal formato italiano al float"""
        if price_value is None:
            return None
        if isinstance(price_value, (int, float)):
            return float(price_value)
        if isinstance(price_value, str):
            # Rimuovi spazi e sostituisci virgola con punto
            price_str = price_value.strip().replace(',', '.')
            try:
                return float(price_str)
            except ValueError:
                logger.warning(f"Impossibile convertire prezzo: {price_value}")
                return None
        return None

    def save_product_to_db(self, product_data):
        """Salva prodotto nel database"""
        logger.info(f"🔍 DEBUG: save_product_to_db chiamato per: {product_data.get('nome', 'NOME_MANCANTE')}")
        logger.info(f"🔍 DEBUG: db_manager presente: {self.db_manager is not None}")
        logger.info(f"🔍 DEBUG: job_id presente: {self.job_id}")
        
        try:
            logger.info(f"🔍 DEBUG: Preparando dati per il database...")
            # Converte i prezzi dal formato italiano
            prezzo_originale_float = self.convert_price_to_float(product_data.get('prezzo_originale'))
            
            # Prepara i dati nel formato richiesto dal database
            db_product_data = {
                'nome': product_data.get('nome', ''),
                'prezzo': product_data.get('prezzo'),
                'prezzo_originale': prezzo_originale_float,  # Ora è un float
                'marca': product_data.get('marca', ''),
                'categoria': product_data.get('categoria', ''),
                'quantita': product_data.get('tipo_prodotto', ''),  # Usa tipo_prodotto come quantità
                'confidence_score': 0.95  # Score di default
            }
            logger.info(f"🔍 DEBUG: Dati preparati: {db_product_data}")
            
            # Usa save_products che si aspetta una lista
            logger.info(f"🔍 DEBUG: Chiamando db_manager.save_products...")
            products = self.db_manager.save_products(self.job_id, [db_product_data])
            logger.info(f"🔍 DEBUG: Risultato save_products: {len(products) if products else 0} prodotti")
            
            if products:
                logger.info(f"💾 Prodotto salvato nel DB: {product_data['nome']}")
                logger.info(f"✅ DEBUG: Prodotto salvato con successo")
                return True
            else:
                logger.info(f"❌ DEBUG: save_products ha restituito lista vuota")
        except Exception as e:
            logger.error(f"❌ Errore salvataggio DB: {e}")
            logger.error(f"❌ DEBUG: Eccezione durante salvataggio: {e}")
        
        logger.info(f"❌ DEBUG: save_product_to_db restituisce False")
        return False
    
    def process_image(self, image_path):
        """Elabora una singola immagine con Multi-AI e fallback"""
        logger.info(f"📸 Elaborando: {Path(image_path).name}")
        
        try:
            image_name = Path(image_path).stem
            results = []
            
            # Tentativo 1: Analisi con Gemini AI (primario)
            logger.info("🤖 Tentativo con Gemini AI (primario)...")
            gemini_result = self.analyze_with_gemini(image_path)
            
            if gemini_result and 'prodotti' in gemini_result and len(gemini_result['prodotti']) > 0:
                logger.info(f"✅ Gemini ha trovato {len(gemini_result['prodotti'])} prodotti")
                return self._process_ai_result(gemini_result, image_path, image_name, 'Gemini AI')
            
            # Fallback 1: Moondream2 se Gemini fallisce
            if self.enable_fallback and self.moondream_extractor:
                logger.warning("⚠️ Gemini non ha trovato prodotti, tentativo con Moondream2...")
                try:
                    moondream_results = self.moondream_extractor.process_image(image_path)
                    if moondream_results and len(moondream_results) > 0:
                        logger.info(f"✅ Moondream2 ha trovato {len(moondream_results)} prodotti")
                        return moondream_results
                except Exception as e:
                    logger.error(f"❌ Errore Moondream2: {e}")
            
            # Fallback 2: Qwen2.5-VL se anche Moondream fallisce
            if self.enable_fallback and self.qwen_extractor:
                logger.warning("⚠️ Moondream2 non disponibile/fallito, tentativo con Qwen2.5-VL...")
                try:
                    qwen_results = self.qwen_extractor.process_image(image_path)
                    if qwen_results and len(qwen_results) > 0:
                        logger.info(f"✅ Qwen2.5-VL ha trovato {len(qwen_results)} prodotti")
                        return qwen_results
                except Exception as e:
                    logger.error(f"❌ Errore Qwen2.5-VL: {e}")
            
            # Se tutti i metodi falliscono
            logger.error(f"❌ Tutti i metodi AI hanno fallito per {Path(image_path).name}")
            return []
            
        except Exception as e:
            logger.error(f"❌ Errore elaborazione {image_path}: {e}")
            return []
    
    def _process_ai_result(self, ai_result, image_path, image_name, ai_source):
        """Processa il risultato di un'AI e restituisce la lista di prodotti"""
        results = []
        
        if ai_result and 'prodotti' in ai_result:
            logger.info(f"🤖 {ai_source} ha trovato {len(ai_result['prodotti'])} prodotti")
            
            for i, prodotto in enumerate(ai_result['prodotti']):
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
                image_path_saved = self.save_product_image(image_path, prodotto, image_name, i, self.supermercato_nome)
                
                result = {
                    'nome': nome,
                    'marca': marca,
                    'categoria': categoria,
                    'tipo_prodotto': nome.split()[-1] if nome else 'Sconosciuto',
                    'prezzo': prezzo,
                    'prezzo_originale': prezzo_str,
                    'descrizione': descrizione,
                    'fonte': ai_source,
                    'immagine_prodotto': image_path_saved or 'Non disponibile',
                    'immagine_originale': str(image_path)
                }
                
                results.append(result)
        
        logger.info(f"🛒 Totale prodotti estratti da {ai_source}: {len(results)}")
        return results
    
    def run(self, pdf_source=None, source_type="file"):
        """Esegue l'estrazione completa con Multi-AI e fallback
        
        Args:
            pdf_source: Path del file PDF o URL del PDF
            source_type: "file" per file locale, "url" per URL
        """
        logger.info("🚀 Avvio estrazione Multi-AI con fallback...")
        
        image_paths = []
        
        if pdf_source:
            # Gestione PDF da URL o file
            if source_type == "url":
                logger.info(f"📥 Elaborando PDF da URL: {pdf_source}")
                pdf_path = self.download_pdf_from_url(pdf_source)
                if not pdf_path:
                    logger.error("❌ Impossibile scaricare PDF da URL")
                    return []
            else:
                logger.info(f"📄 Elaborando PDF da file: {pdf_source}")
                pdf_path = pdf_source
            
            # Converte PDF in immagini
            image_paths = self.convert_pdf_to_images(pdf_path)
            if not image_paths:
                logger.error("❌ Impossibile convertire PDF in immagini")
                return []
        else:
            # Modalità legacy: cerca immagini PNG nella directory
            image_dir = Path('output')
            image_files = list(image_dir.glob('page_*.png'))
            
            if not image_files:
                logger.error("❌ Nessuna immagine trovata")
                return []
            
            image_paths = [str(img) for img in image_files]
        
        logger.info(f"📁 Trovate {len(image_paths)} immagini da elaborare")
        
        all_results = []
        
        for i, image_path in enumerate(image_paths):
            logger.info(f"📊 Progresso: {i+1}/{len(image_paths)}")
            results = self.process_image(image_path)
            if results:
                # Salva prodotti nel database se disponibile
                for result in results:
                    if self.save_product_to_db(result):
                        logger.info(f"✅ Prodotto salvato: {result['nome']}")
                
                all_results.extend(results)
            
            # Pausa tra le immagini per evitare rate limiting
            if i < len(image_paths) - 1:
                logger.info("⏳ Pausa di 5 secondi tra le immagini...")
                time.sleep(5)
        
        # Salva risultati
        output_file = f'gemini_results_{self.job_id}.json' if self.job_id else 'gemini_only_results.json'
        results_data = {
            'timestamp': datetime.now().isoformat(),
            'method': 'Gemini AI Only Extractor',
            'total_products': len(all_results),
            'images_processed': len(image_paths),
            'products': all_results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results_data, f, indent=2, ensure_ascii=False)
        
        # Cleanup directory temporanea
        if self.temp_dir.exists() and self.job_id:
            try:
                shutil.rmtree(self.temp_dir)
                logger.info(f"🧹 Cleanup completato: {self.temp_dir}")
            except Exception as e:
                logger.warning(f"⚠️ Errore cleanup: {e}")
        
        logger.info(f"💾 Risultati salvati in {output_file}")
        logger.info(f"📊 Totale prodotti estratti: {len(all_results)}")
        logger.info(f"📁 Immagini prodotti salvate in: {self.product_images_dir}")
        
        # Aggiorna il job con il numero totale di prodotti estratti
        try:
            self.db_manager.update_job_status(
                self.job_id, 
                "completed", 
                progress=100,
                total_products=len(all_results),
                message=f"Estrazione completata: {len(all_results)} prodotti trovati"
            )
            logger.info(f"✅ Job {self.job_id} aggiornato con {len(all_results)} prodotti")
        except Exception as e:
            logger.error(f"❌ Errore aggiornamento job: {e}")
        
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
        
        return all_results
        
# Alias per compatibilità con codice esistente
GeminiOnlyExtractor = MultiAIExtractor

if __name__ == "__main__":
    # Test del modello
    extractor = MultiAIExtractor()
    extractor.run()