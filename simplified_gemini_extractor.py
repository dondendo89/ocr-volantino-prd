#!/usr/bin/env python3
"""
Estrattore Gemini Semplificato
Basato su new-ocr.py che funziona su Colab
Integra salvataggio database e gestione dual token
"""

import google.generativeai as genai
import requests
import io
import fitz  # PyMuPDF
from PIL import Image
import base64
import json
import re
import datetime
import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from google.api_core.exceptions import ResourceExhausted
from pathlib import Path
import logging
from product_card_generator import ProductCardGenerator

# Configurazione logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimplifiedGeminiExtractor:
    def __init__(self, gemini_api_key="", gemini_api_key_2=None, job_id=None, db_manager=None, supermercato_nome="SUPERMERCATO"):
        logger.info("🤖 Inizializzando estrattore Gemini semplificato...")
        
        self.gemini_api_key = gemini_api_key
        self.gemini_api_key_2 = gemini_api_key_2 or os.getenv('GEMINI_API_KEY_2')
        self.job_id = job_id
        self.db_manager = db_manager
        self.supermercato_nome = supermercato_nome
        self.current_key_index = 0
        
        # Configura le chiavi API
        self.api_keys = [self.gemini_api_key]
        if self.gemini_api_key_2:
            self.api_keys.append(self.gemini_api_key_2)
            logger.info("✅ Configurate 2 chiavi API Gemini per ottimizzazione rate limiting")
        else:
            logger.info("✅ Configurata 1 chiave API Gemini")
        
        # Crea directory per le immagini
        self.temp_dir = Path(f"temp_processing_{job_id}" if job_id else "temp_processing")
        self.temp_dir.mkdir(exist_ok=True)
        
        self.product_images_dir = Path("simplified_gemini_product_images")
        self.product_images_dir.mkdir(exist_ok=True)
        
        # Inizializza il generatore di card prodotto
        self.card_generator = ProductCardGenerator()
        
        # Contatori per statistiche
        self.total_products_found = 0
        self.total_products_saved = 0
    
    def log_message(self, message):
        """Funzione ausiliaria per stampare messaggi con timestamp."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"[{timestamp}] {message}")
        print(f"[{timestamp}] {message}")  # Mantieni anche print per debug
    
    def get_next_api_key(self):
        """Ottiene la prossima chiave API per bilanciare il carico"""
        if len(self.api_keys) > 1:
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        
        current_key = self.api_keys[self.current_key_index]
        logger.info(f"🔄 Usando chiave API {self.current_key_index + 1}/{len(self.api_keys)}")
        return current_key
    
    def get_page_image(self, pdf_path, page_num):
        """Estrae una singola pagina da un PDF come immagine."""
        try:
            doc = fitz.open(pdf_path)
            page = doc.load_page(page_num)
            # Aumenta la risoluzione per migliore qualità
            mat = fitz.Matrix(2.0, 2.0)  # 2x zoom
            pix = page.get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            doc.close()
            image = Image.open(io.BytesIO(img_bytes))
            return image
        except Exception as e:
            self.log_message(f"❌ Errore durante l'estrazione dell'immagine della pagina {page_num + 1}: {e}")
            return None
    
    def crop_and_save_product_image(self, page_image, bounding_box, page_number, product_index):
        """Ritaglia e salva l'immagine di un singolo prodotto."""
        try:
            img_width, img_height = page_image.size
            # Coordinate del bounding box normalizzate [x_min, y_min, x_max, y_max]
            x_min, y_min, x_max, y_max = [coord * dim for coord, dim in zip(bounding_box, [img_width, img_height, img_width, img_height])]
            
            # Aggiungi un padding per allargare l'area di ritaglio
            padding_x = 0.05  # 5% della larghezza del prodotto su ogni lato
            padding_y_top = 0.05 # 5% dell'altezza del prodotto sopra
            padding_y_bottom = 0.20 # 20% dell'altezza del prodotto sotto per il prezzo e descrizione
            
            # Calcola le dimensioni del bounding box originale
            box_width = x_max - x_min
            box_height = y_max - y_min
            
            # Applica il padding
            x_min_padded = max(0, x_min - (box_width * padding_x))
            y_min_padded = max(0, y_min - (box_height * padding_y_top))
            x_max_padded = min(img_width, x_max + (box_width * padding_x))
            y_max_padded = min(img_height, y_max + (box_height * padding_y_bottom))
            
            # Converte a interi
            x_min_final, y_min_final, x_max_final, y_max_final = map(int, [x_min_padded, y_min_padded, x_max_padded, y_max_padded])
            
            cropped_image = page_image.crop((x_min_final, y_min_final, x_max_final, y_max_final))
            
            # Crea nome file unico con job_id per evitare conflitti
            image_name = f"{self.job_id}_pagina_{page_number}_prodotto_{product_index}.png"
            
            # Salva nell'archivio principale
            image_path = self.product_images_dir / image_name
            cropped_image.save(image_path)
            
            # Copia anche nella directory static/images per l'accesso web
            static_images_dir = Path("static/images")
            static_images_dir.mkdir(exist_ok=True)
            static_image_path = static_images_dir / image_name
            cropped_image.save(static_image_path)
            
            self.log_message(f"✅ Immagine del prodotto salvata in: {image_path}")
            self.log_message(f"✅ Immagine copiata per accesso web: {static_image_path}")
            return str(image_path)
        except Exception as e:
            self.log_message(f"❌ Errore durante il ritaglio o il salvataggio dell'immagine del prodotto: {e}")
            return None
    
    def convert_price_to_float(self, price_value):
        """Converte il prezzo in float gestendo diversi formati"""
        if not price_value:
            return None
        
        try:
            # Rimuovi simboli di valuta e spazi
            price_str = str(price_value).replace('€', '').replace('$', '').replace(',', '.').strip()
            # Estrai solo numeri e punto decimale
            price_match = re.search(r'\d+(?:\.\d+)?', price_str)
            if price_match:
                return float(price_match.group())
        except (ValueError, AttributeError):
            pass
        
        return None
    
    def save_product_to_db(self, product_data):
        """Salva il prodotto nel database"""
        if not self.db_manager:
            self.log_message("⚠️ Database manager non disponibile")
            return False
        
        try:
            # Prepara i dati per il database nel formato corretto per save_products
            db_product = {
                'nome': product_data.get('nome', product_data.get('nome_prodotto', '')),
                'marca': product_data.get('marca', ''),
                'categoria': product_data.get('categoria', ''),
                'prezzo': self.convert_price_to_float(product_data.get('prezzo')),
                'prezzo_originale': self.convert_price_to_float(product_data.get('prezzo_al_kg/l')),
                'quantita': product_data.get('quantità', product_data.get('quantita', '')),
                'image_url': product_data.get('image_url'),
                'image_path': product_data.get('image_path'),
                'confidence_score': 0.95  # Score di default
            }
            
            # Usa save_products che si aspetta una lista
            self.log_message(f"🔍 DEBUG: Chiamando save_products per job_id={self.job_id}")
            self.log_message(f"🔍 DEBUG: Supermercato: {self.supermercato_nome}")
            self.log_message(f"🔍 DEBUG: Dati prodotto da salvare: {db_product}")
            products = self.db_manager.save_products(self.job_id, [db_product])
            self.log_message(f"🔍 DEBUG: save_products ha restituito: {products}")
            self.log_message(f"🔍 DEBUG: Numero prodotti restituiti: {len(products) if products else 0}")
            if products and len(products) > 0:
                self.total_products_saved += 1
                self.log_message(f"✅ Prodotto salvato nel database: {db_product['nome']}")
                return True
            else:
                self.log_message(f"❌ Errore salvataggio prodotto nel database: {db_product['nome']}")
                return False
                
        except Exception as e:
            self.log_message(f"❌ Errore durante il salvataggio nel database: {e}")
            return False
    
    def process_single_page(self, pdf_path, page_number, prompt):
        """Funzione che esegue l'intera logica per una singola pagina."""
        self.log_message(f"🚀 Pagina {page_number}: Inizio estrazione immagine...")
        page_image = self.get_page_image(pdf_path, page_number - 1)
        
        if not page_image:
            return {"page": page_number, "products": [], "success": False, "error": "Impossibile estrarre l'immagine."}
        
        self.log_message(f"✅ Pagina {page_number}: Immagine estratta, {page_image.width}x{page_image.height} pixel.")
        self.log_message(f"🤖 Pagina {page_number}: Invio a Gemini per l'analisi...")
        
        # Usa la chiave API corrente
        current_api_key = self.get_next_api_key()
        genai.configure(api_key=current_api_key)
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        buffered = io.BytesIO()
        page_image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        try:
            # Configura timeout per evitare blocchi infiniti
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("Timeout nella chiamata a Gemini")
            
            # Imposta timeout di 90 secondi per la chiamata a Gemini
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(90)
            
            try:
                raw_response = model.generate_content([prompt, {"mime_type": "image/png", "data": img_str}]).text
            finally:
                signal.alarm(0)  # Disabilita il timeout
            self.log_message(f"📄 Pagina {page_number}: Risposta grezza di Gemini:\n{raw_response}")
            
            match = re.search(r'\[.*\]', raw_response, re.DOTALL)
            if match:
                json_str = match.group(0)
                products_on_page = json.loads(json_str)
                
                # Process and save product images
                processed_products = []
                for i, product in enumerate(products_on_page):
                    # Ensure date fields are present, even if null
                    product.setdefault("data_inizio_offerta", None)
                    product.setdefault("data_fine_offerta", None)
                    
                    if "bounding_box" in product and product["bounding_box"]:
                        image_path = self.crop_and_save_product_image(page_image, product["bounding_box"], page_number, i + 1)
                        product["immagine_prodotto"] = image_path
                        # Aggiungi anche il path relativo per l'API
                        if image_path:
                            # Il path è già relativo alla directory corrente
                            product["image_path"] = image_path
                            product["image_url"] = f"/static/images/{Path(image_path).name}"
                        del product["bounding_box"]  # Rimuovi il campo bounding_box
                    else:
                        product["immagine_prodotto"] = None
                        product["image_path"] = None
                        product["image_url"] = None
                    
                    # Salva nel database
                    self.log_message(f"🔍 DEBUG: Struttura completa prodotto: {product}")
                    self.log_message(f"🔍 DEBUG: Tentativo salvataggio prodotto: {product.get('nome', product.get('nome_prodotto', 'NOME_MANCANTE'))}")
                    save_result = self.save_product_to_db(product)
                    self.log_message(f"🔍 DEBUG: Risultato salvataggio: {save_result}")
                    if save_result:
                        processed_products.append(product)
                        self.total_products_found += 1
                        self.log_message(f"✅ DEBUG: Prodotto aggiunto a processed_products")
                    else:
                        self.log_message(f"❌ DEBUG: Prodotto NON aggiunto a processed_products")
                
                return {"page": page_number, "products": processed_products, "success": True, "error": None}
            else:
                return {"page": page_number, "products": [], "success": False, "error": "Nessun blocco JSON valido trovato."}
        except ResourceExhausted:
            return {"page": page_number, "products": [], "success": False, "error": "Quota di token esaurita. Attendi e riprova più tardi."}
        except TimeoutError:
            return {"page": page_number, "products": [], "success": False, "error": "Timeout nella chiamata a Gemini (90 secondi). La pagina verrà saltata."}
        except Exception as e:
            return {"page": page_number, "products": [], "success": False, "error": str(e)}
    
    def run(self, pdf_source=None, source_type="file", progress_callback=None):
        """Metodo principale per eseguire l'estrazione"""
        try:
            self.log_message("🚀 Avvio estrattore Gemini semplificato...")
            
            # Determina il percorso del PDF
            if source_type == "url":
                pdf_path = self.download_pdf_from_url(pdf_source)
                if not pdf_path:
                    return {"success": False, "error": "Impossibile scaricare il PDF"}
            else:
                pdf_path = pdf_source
            
            if not pdf_path or not os.path.exists(pdf_path):
                return {"success": False, "error": "File PDF non trovato"}
            
            # Conta le pagine del PDF
            try:
                doc = fitz.open(pdf_path)
                total_pages = doc.page_count
                doc.close()
            except Exception as e:
                self.log_message(f"❌ Errore durante l'apertura del PDF: {e}")
                return {"success": False, "error": f"Errore apertura PDF: {e}"}
            
            if total_pages == 0:
                return {"success": False, "error": "Nessuna pagina trovata nel PDF"}
            
            self.log_message(f"Inizio elaborazione. Trovate {total_pages} pagine nel PDF.")
            
            # Aggiorna progresso iniziale
            if progress_callback:
                progress_callback(55, f"Elaborazione {total_pages} pagine...")
            
            # Prompt ottimizzato
            prompt_text = """
Analizza attentamente questa immagine di un volantino di supermercato.
Estrai un elenco completo di tutti i prodotti in offerta. Per ogni prodotto, fornisci:
- **nome_prodotto**: Il nome completo del prodotto.
- **prezzo**: Il prezzo di vendita del prodotto.
- **prezzo_al_kg/l**: Il prezzo al chilo o al litro, se disponibile.
- **quantità**: La quantità del prodotto (peso o unità, es. "500g", "6x70g", "1L").
- **marca**: La marca del prodotto, se visibile.
- **categoria**: La categoria del prodotto (es. "pasta", "latticini", "bevande").
- **descrizione**: Breve descrizione del prodotto.
- **data_inizio_offerta**: La data di inizio dell'offerta, se specificata. Formato YYYY-MM-DD.
- **data_fine_offerta**: La data di fine dell'offerta, se specificata. Formato YYYY-MM-DD.
- **bounding_box**: Le coordinate del riquadro del prodotto nell'immagine, in formato [x_min, y_min, x_max, y_max] con valori normalizzati tra 0 e 1.

Formatta il risultato come un array di oggetti JSON. Se non trovi prodotti, restituisci un array vuoto [].
Assicurati di non tralasciare nessun prodotto visibile.
"""
            
            all_products = []
            completed_pages = 0
            
            # Elabora le pagine in parallelo
            with ThreadPoolExecutor(max_workers=2) as executor:  # Ridotto a 2 per evitare rate limiting
                futures = {executor.submit(self.process_single_page, pdf_path, page_num, prompt_text) for page_num in range(1, total_pages + 1)}
                
                for future in as_completed(futures):
                    result = future.result()
                    completed_pages += 1
                    
                    # Calcola progresso: da 55% a 90% durante l'elaborazione delle pagine
                    progress = 55 + int((completed_pages / total_pages) * 35)
                    
                    if result["success"]:
                        all_products.extend(result["products"])
                        self.log_message(f"✅ Pagina {result['page']}: Trovati {len(result['products'])} prodotti.")
                        if progress_callback:
                            progress_callback(progress, f"Pagina {result['page']}/{total_pages} completata - {len(result['products'])} prodotti trovati")
                    else:
                        self.log_message(f"❌ Pagina {result['page']}: Errore - {result['error']}")
                        if progress_callback:
                            progress_callback(progress, f"Pagina {result['page']}/{total_pages} - Errore: {result['error']}")
            
            # Aggiorna progresso finale
            if progress_callback:
                progress_callback(95, f"Finalizzazione... {self.total_products_found} prodotti estratti")
            
            # Aggiorna il job nel database se disponibile
            if self.db_manager and self.job_id:
                try:
                    self.db_manager.update_job_status(self.job_id, 'completed', progress=100, total_products=self.total_products_found, message=f"Completato! {self.total_products_found} prodotti estratti")
                    self.log_message(f"✅ Job {self.job_id} aggiornato con {self.total_products_found} prodotti")
                except Exception as e:
                    self.log_message(f"❌ Errore aggiornamento job: {e}")
            
            self.log_message("\n--- Processo completato ---")
            self.log_message(f"Totale prodotti estratti: {self.total_products_found}")
            self.log_message(f"Totale prodotti salvati nel database: {self.total_products_saved}")
            
            return {
                "success": True,
                "total_products": self.total_products_found,
                "products_saved": self.total_products_saved,
                "products": all_products
            }
            
        except Exception as e:
            self.log_message(f"❌ Errore generale durante l'elaborazione: {e}")
            return {"success": False, "error": str(e)}
    
    def download_pdf_from_url(self, url):
        """Scarica PDF da URL"""
        try:
            self.log_message(f"📥 Scaricando PDF da URL: {url}")
            import urllib.request
            filename = f"downloaded_pdf_{self.job_id}.pdf"
            pdf_path = self.temp_dir / filename
            
            urllib.request.urlretrieve(url, pdf_path)
            self.log_message(f"✅ PDF scaricato: {pdf_path}")
            return str(pdf_path)
        except Exception as e:
            self.log_message(f"❌ Errore download PDF: {e}")
            return None

# Funzione di test per uso standalone
if __name__ == "__main__":
    # Test con PDF locale
    extractor = SimplifiedGeminiExtractor(
        gemini_api_key="AIzaSyDglA1cwH8lMkGc0GLKNKLv5ulCWL1omag",
        job_id="test_local"
    )
    
    result = extractor.run("volantino.pdf", "file")
    print(f"\nRisultato finale: {result}")