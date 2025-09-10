#!/usr/bin/env python3
"""
Estrattore Gemini Semplificato basato su new-ocr.py
Versione ottimizzata che funziona su Colab e in produzione
"""

import google.generativeai as genai
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
import logging
from pathlib import Path
from product_card_generator import ProductCardGenerator

# Configurazione logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SimpleGeminiExtractor:
    def __init__(self, gemini_api_key, job_id=None, db_manager=None, supermercato_nome="SUPERMERCATO"):
        self.gemini_api_key = gemini_api_key
        self.job_id = job_id
        self.db_manager = db_manager
        self.supermercato_nome = supermercato_nome
        
        # Configura Gemini
        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        # Crea directory per le immagini temporanee
        self.temp_dir = Path(f"temp_processing_{job_id}" if job_id else "temp_processing")
        self.temp_dir.mkdir(exist_ok=True)
        
        # Crea directory per le immagini dei prodotti
        self.product_images_dir = Path("simple_gemini_product_images")
        self.product_images_dir.mkdir(exist_ok=True)
        
        # Inizializza il generatore di card prodotto
        self.card_generator = ProductCardGenerator()
        
        logger.info(f"✅ SimpleGeminiExtractor inizializzato per job {job_id}")
    
    def log_message(self, message):
        """Funzione ausiliaria per stampare messaggi con timestamp."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"[{timestamp}] {message}")
    
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

            image_name = f"pagina_{page_number}_prodotto_{product_index}.png"
            image_path = self.product_images_dir / image_name
            cropped_image.save(image_path)
            self.log_message(f"✅ Immagine del prodotto salvata in: {image_path}")
            return str(image_path)
        except Exception as e:
            self.log_message(f"❌ Errore durante il ritaglio o il salvataggio dell'immagine del prodotto: {e}")
            return None
    
    def convert_price_to_float(self, price_value):
        """Converte il prezzo in float gestendo vari formati."""
        if not price_value:
            return None
        
        try:
            # Rimuovi simboli di valuta e spazi
            price_str = str(price_value).replace('€', '').replace('$', '').replace(',', '.').strip()
            
            # Estrai solo numeri e punto decimale
            price_match = re.search(r'\d+(?:\.\d+)?', price_str)
            if price_match:
                return float(price_match.group())
            return None
        except (ValueError, AttributeError):
            return None
    
    def save_product_to_db(self, product_data):
        """Salva il prodotto nel database se disponibile."""
        if not self.db_manager:
            return None
        
        try:
            # Prepara i dati per il database
            db_product = {
                'nome': product_data.get('nome_prodotto', ''),
                'marca': product_data.get('marca', ''),
                'prezzo': self.convert_price_to_float(product_data.get('prezzo')),
                'prezzo_al_kg': self.convert_price_to_float(product_data.get('prezzo_al_kg/l')),
                'quantita': product_data.get('quantità', ''),
                'categoria': product_data.get('categoria', 'Alimentari'),
                'descrizione': product_data.get('descrizione', ''),
                'immagine_path': product_data.get('immagine_prodotto'),
                'data_inizio_offerta': product_data.get('data_inizio_offerta'),
                'data_fine_offerta': product_data.get('data_fine_offerta'),
                'supermercato': self.supermercato_nome,
                'job_id': self.job_id
            }
            
            product_id = self.db_manager.save_product(db_product)
            self.log_message(f"✅ Prodotto salvato nel database con ID: {product_id}")
            return product_id
        except Exception as e:
            self.log_message(f"❌ Errore salvataggio prodotto nel database: {e}")
            return None
    
    def process_single_page(self, pdf_path, page_number):
        """Funzione che esegue l'intera logica per una singola pagina."""
        self.log_message(f"🚀 Pagina {page_number}: Inizio estrazione immagine...")
        page_image = self.get_page_image(pdf_path, page_number - 1)

        if not page_image:
            return {"page": page_number, "products": [], "success": False, "error": "Impossibile estrarre l'immagine."}

        self.log_message(f"✅ Pagina {page_number}: Immagine estratta, {page_image.width}x{page_image.height} pixel.")
        self.log_message(f"🤖 Pagina {page_number}: Invio a Gemini per l'analisi...")

        # Prompt ottimizzato
        prompt = """
Analizza attentamente questa immagine di un volantino di supermercato.
Estrai un elenco completo di tutti i prodotti in offerta. Per ogni prodotto, fornisci:
- **nome_prodotto**: Il nome completo del prodotto.
- **prezzo**: Il prezzo di vendita del prodotto.
- **prezzo_al_kg/l**: Il prezzo al chilo o al litro, se disponibile.
- **quantità**: La quantità del prodotto (peso o unità, es. "500g", "6x70g", "1L").
- **marca**: La marca del prodotto, se visibile.
- **categoria**: La categoria del prodotto (es: "Latticini", "Pasta", "Bevande").
- **descrizione**: Una breve descrizione del prodotto.
- **data_inizio_offerta**: La data di inizio dell'offerta, se specificata. Formato YYYY-MM-DD.
- **data_fine_offerta**: La data di fine dell'offerta, se specificata. Formato YYYY-MM-DD.
- **bounding_box**: Le coordinate del riquadro del prodotto nell'immagine, in formato [x_min, y_min, x_max, y_max] con valori normalizzati tra 0 e 1.

Formatta il risultato come un array di oggetti JSON. Se non trovi prodotti, restituisci un array vuoto [].
Assicurati di non tralasciare nessun prodotto visibile.
"""

        buffered = io.BytesIO()
        page_image.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        try:
            raw_response = self.model.generate_content([prompt, {"mime_type": "image/png", "data": img_str}]).text
            self.log_message(f"📄 Pagina {page_number}: Risposta grezza di Gemini:\n{raw_response}")

            match = re.search(r'\[.*\]', raw_response, re.DOTALL)
            if match:
                json_str = match.group(0)
                products_on_page = json.loads(json_str)

                # Process and save product images
                saved_products = []
                for i, product in enumerate(products_on_page):
                    # Ensure date fields are present, even if null
                    product.setdefault("data_inizio_offerta", None)
                    product.setdefault("data_fine_offerta", None)
                    product.setdefault("categoria", "Alimentari")
                    product.setdefault("descrizione", "")

                    if "bounding_box" in product and product["bounding_box"]:
                        image_path = self.crop_and_save_product_image(page_image, product["bounding_box"], page_number, i + 1)
                        product["immagine_prodotto"] = image_path
                        del product["bounding_box"]  # Rimuovi il campo bounding_box
                    else:
                        product["immagine_prodotto"] = None
                    
                    # Salva nel database se disponibile
                    product_id = self.save_product_to_db(product)
                    if product_id:
                        product["database_id"] = product_id
                    
                    saved_products.append(product)

                return {"page": page_number, "products": saved_products, "success": True, "error": None}
            else:
                return {"page": page_number, "products": [], "success": False, "error": "Nessun blocco JSON valido trovato."}
        except ResourceExhausted:
            return {"page": page_number, "products": [], "success": False, "error": "Quota di token esaurita. Attendi e riprova più tardi."}
        except Exception as e:
            return {"page": page_number, "products": [], "success": False, "error": str(e)}
    
    def run(self, pdf_source, source_type="file"):
        """Esegue l'estrazione completa dal PDF."""
        try:
            # Gestisci il PDF
            if source_type == "url":
                # Implementa download da URL se necessario
                pdf_path = pdf_source
            else:
                pdf_path = pdf_source
            
            # Apri il PDF e conta le pagine
            doc = fitz.open(pdf_path)
            total_pages = doc.page_count
            doc.close()
            
            if total_pages == 0:
                self.log_message("Nessuna pagina trovata nel PDF. Controlla il percorso del file.")
                return []
            
            self.log_message(f"Inizio elaborazione. Trovate {total_pages} pagine nel PDF.")
            
            all_products = []
            
            # Processa le pagine in parallelo (limitato per evitare rate limiting)
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = {executor.submit(self.process_single_page, pdf_path, page_num) for page_num in range(1, total_pages + 1)}

                for future in as_completed(futures):
                    result = future.result()
                    if result["success"]:
                        all_products.extend(result["products"])
                        self.log_message(f"✅ Pagina {result['page']}: Trovati {len(result['products'])} prodotti.")
                    else:
                        self.log_message(f"❌ Pagina {result['page']}: Errore - {result['error']}")

            self.log_message("\n--- Processo completato ---")
            self.log_message(f"Totale prodotti estratti: {len(all_products)}")
            
            # Aggiorna il job nel database se disponibile
            if self.db_manager and self.job_id:
                try:
                    self.db_manager.update_job_status(self.job_id, 'completed', len(all_products))
                    self.log_message(f"✅ Job {self.job_id} aggiornato nel database")
                except Exception as e:
                    self.log_message(f"❌ Errore aggiornamento job: {e}")
            
            return all_products
            
        except Exception as e:
            self.log_message(f"❌ Errore durante l'elaborazione: {e}")
            if self.db_manager and self.job_id:
                try:
                    self.db_manager.update_job_status(self.job_id, 'failed', 0)
                except:
                    pass
            return []
    
    def cleanup(self):
        """Pulisce i file temporanei."""
        try:
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                self.log_message(f"✅ Directory temporanea rimossa: {self.temp_dir}")
        except Exception as e:
            self.log_message(f"⚠️ Errore durante la pulizia: {e}")

# Funzione di compatibilità per l'uso come MultiAIExtractor
def create_simple_extractor(gemini_api_key, job_id=None, db_manager=None, supermercato_nome="SUPERMERCATO"):
    """Crea un'istanza di SimpleGeminiExtractor con interfaccia compatibile."""
    return SimpleGeminiExtractor(gemini_api_key, job_id, db_manager, supermercato_nome)