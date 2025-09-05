#!/usr/bin/env python3
"""
Estrattore Moondream2 AI per volantini
"""

import json
from pathlib import Path
import os
import shutil
from datetime import datetime
import logging
import time
import fitz  # PyMuPDF per conversione PDF
from urllib.parse import urlparse
from urllib.request import urlretrieve
from PIL import Image
import re

# Configurazione logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MoondreamExtractor:
    def __init__(self, moondream_api_key=None, job_id=None, db_manager=None):
        logger.info("🌙 Inizializzando estrattore Moondream2 AI...")
        
        self.moondream_api_key = moondream_api_key
        self.job_id = job_id
        self.db_manager = db_manager
        
        # Inizializza Moondream
        try:
            import moondream as md
            if moondream_api_key:
                # Usa Moondream Cloud
                self.model = md.vl(api_key=moondream_api_key)
                logger.info("✅ Moondream Cloud inizializzato")
            else:
                # Usa modello locale (se disponibile)
                try:
                    self.model = md.vl(endpoint="http://localhost:2020/v1")
                    logger.info("✅ Moondream Server locale inizializzato")
                except:
                    # Fallback: usa transformers direttamente
                    from transformers import AutoModelForCausalLM, AutoTokenizer
                    model_id = "vikhyatk/moondream2"
                    revision = "2025-06-21"
                    
                    self.model = AutoModelForCausalLM.from_pretrained(
                        model_id,
                        trust_remote_code=True,
                        revision=revision
                    )
                    self.tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
                    self.use_transformers = True
                    logger.info("✅ Moondream locale (transformers) inizializzato")
        except Exception as e:
            logger.error(f"❌ Errore inizializzazione Moondream: {e}")
            raise
        
        # Crea directory per le immagini temporanee
        self.temp_dir = Path(f"temp_processing_{job_id}" if job_id else "temp_processing_moondream")
        self.temp_dir.mkdir(exist_ok=True)
        
        # Crea directory per le immagini dei prodotti
        self.product_images_dir = Path("moondream_product_images")
        self.product_images_dir.mkdir(exist_ok=True)
    
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
    
    def analyze_with_moondream(self, image_path, retry_count=3):
        """Analizza immagine con Moondream2 AI"""
        for attempt in range(retry_count):
            try:
                logger.info(f"🌙 Tentativo {attempt + 1}/{retry_count} - Analizzando con Moondream: {Path(image_path).name}")
                
                # Carica immagine
                image = Image.open(image_path)
                
                # Prompt per estrazione prodotti
                prompt = """Analizza questa immagine di un volantino di supermercato italiano e estrai le informazioni sui prodotti alimentari visibili.
                
Per ogni prodotto che vedi, fornisci:
- Nome completo del prodotto
- Marca (se visibile)
- Categoria (latticini, pasta, bevande, dolci, etc.)
- Prezzo in euro (se visibile)
- Breve descrizione
                
Rispondi in formato JSON con questa struttura:
{
  "prodotti": [
    {
      "nome": "nome del prodotto",
      "marca": "marca del prodotto",
      "categoria": "categoria",
      "prezzo": "prezzo in euro",
      "descrizione": "descrizione"
    }
  ]
}
                
Estrai solo prodotti alimentari chiaramente visibili. Se non vedi un prezzo, scrivi 'Non visibile'. Se non riconosci una marca, scrivi 'Non identificata'."""
                
                # Analisi con Moondream
                if hasattr(self, 'use_transformers') and self.use_transformers:
                    # Usa transformers direttamente
                    encoded_image = self.model.encode_image(image)
                    response = self.model.answer_question(encoded_image, prompt, self.tokenizer)
                else:
                    # Usa API Moondream
                    response = self.model.query(image, prompt)["answer"]
                
                logger.info(f"🌙 Risposta Moondream ricevuta")
                
                # Estrai JSON dalla risposta
                try:
                    # Pulisci la risposta
                    response = response.strip()
                    if response.startswith('```json'):
                        response = response[7:]
                    if response.endswith('```'):
                        response = response[:-3]
                    
                    # Trova il JSON nella risposta
                    json_start = response.find('{')
                    json_end = response.rfind('}') + 1
                    if json_start != -1 and json_end != -1:
                        json_str = response[json_start:json_end]
                        parsed_json = json.loads(json_str)
                        logger.info(f"✅ Moondream ha analizzato con successo l'immagine")
                        return parsed_json
                    else:
                        # Se non trova JSON, prova a crearlo dalla risposta testuale
                        logger.warning("⚠️ JSON non trovato, tentativo di parsing testuale")
                        return self.parse_text_response(response)
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️ Errore parsing JSON da Moondream: {e}")
                    logger.info(f"Risposta Moondream: {response[:300]}...")
                    # Prova parsing testuale
                    return self.parse_text_response(response)
                    
            except Exception as e:
                logger.error(f"❌ Errore chiamata Moondream tentativo {attempt + 1}: {e}")
                if attempt == retry_count - 1:
                    return None
                time.sleep(5)
                continue
        
        return None
    
    def parse_text_response(self, text_response):
        """Prova a estrarre prodotti da una risposta testuale"""
        try:
            # Implementazione semplificata per parsing testuale
            products = []
            lines = text_response.split('\n')
            
            current_product = {}
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Cerca pattern comuni
                if 'nome:' in line.lower() or 'prodotto:' in line.lower():
                    if current_product:
                        products.append(current_product)
                        current_product = {}
                    current_product['nome'] = line.split(':', 1)[1].strip()
                elif 'marca:' in line.lower():
                    current_product['marca'] = line.split(':', 1)[1].strip()
                elif 'categoria:' in line.lower():
                    current_product['categoria'] = line.split(':', 1)[1].strip()
                elif 'prezzo:' in line.lower():
                    current_product['prezzo'] = line.split(':', 1)[1].strip()
                elif 'descrizione:' in line.lower():
                    current_product['descrizione'] = line.split(':', 1)[1].strip()
            
            if current_product:
                products.append(current_product)
            
            return {'prodotti': products} if products else None
            
        except Exception as e:
            logger.error(f"❌ Errore parsing testuale: {e}")
            return None
    
    def save_product_image(self, image_path, product_info, image_name, region_id):
        """Salva immagine del prodotto"""
        try:
            product_name = product_info.get('nome', 'prodotto_sconosciuto')
            # Pulisci il nome per il filesystem
            product_name = re.sub(r'[^\w\s-]', '', product_name).strip()
            product_name = re.sub(r'[-\s]+', '_', product_name)
            
            filename = f"{image_name}_{product_name}_region_{region_id}.jpg"
            filepath = self.product_images_dir / filename
            
            # Carica e ridimensiona l'immagine originale
            with Image.open(image_path) as img:
                # Converti in RGB se necessario
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Ridimensiona per risparmiare spazio
                img.thumbnail((800, 600), Image.Resampling.LANCZOS)
                img.save(filepath, 'JPEG', quality=85)
            
            logger.info(f"💾 Immagine prodotto salvata: {filename}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"❌ Errore salvataggio immagine prodotto: {e}")
            return None
    
    def save_product_to_db(self, product_data):
        """Salva prodotto nel database"""
        if not self.db_manager:
            logger.warning("⚠️ Database manager non disponibile")
            return False
        
        try:
            # Prepara i dati per il database
            db_data = {
                'job_id': self.job_id,
                'nome': product_data.get('nome', ''),
                'marca': product_data.get('marca', ''),
                'categoria': product_data.get('categoria', ''),
                'tipo_prodotto': product_data.get('tipo_prodotto', ''),
                'prezzo': product_data.get('prezzo'),
                'prezzo_originale': product_data.get('prezzo_originale', ''),
                'descrizione': product_data.get('descrizione', ''),
                'fonte_estrazione': 'Moondream2 AI',
                'image_url': product_data.get('immagine_prodotto', ''),
                'immagine_originale': product_data.get('immagine_originale', '')
            }
            
            success = self.db_manager.save_extracted_product(db_data)
            if success:
                logger.info(f"✅ Prodotto salvato nel DB: {product_data['nome']}")
            return success
            
        except Exception as e:
            logger.error(f"❌ Errore salvataggio DB: {e}")
            return False
    
    def process_image(self, image_path):
        """Elabora una singola immagine con Moondream"""
        logger.info(f"📸 Elaborando: {Path(image_path).name}")
        
        try:
            image_name = Path(image_path).stem
            results = []
            
            # Analisi con Moondream AI
            moondream_result = self.analyze_with_moondream(image_path)
            
            if moondream_result and 'prodotti' in moondream_result:
                logger.info(f"🌙 Moondream ha trovato {len(moondream_result['prodotti'])} prodotti")
                
                for i, prodotto in enumerate(moondream_result['prodotti']):
                    # Pulisci e valida i dati
                    nome = prodotto.get('nome', 'Prodotto sconosciuto')
                    marca = prodotto.get('marca', 'Non identificata')
                    categoria = prodotto.get('categoria', 'Non specificata')
                    prezzo_str = prodotto.get('prezzo', 'Non visibile')
                    descrizione = prodotto.get('descrizione', '')
                    
                    # Estrai prezzo numerico
                    prezzo = None
                    if prezzo_str and prezzo_str != 'Non visibile':
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
                        'fonte': 'Moondream2 AI',
                        'immagine_prodotto': image_path_saved or 'Non disponibile',
                        'immagine_originale': str(image_path)
                    }
                    
                    results.append(result)
            else:
                logger.warning(f"⚠️ Moondream non ha trovato prodotti in {Path(image_path).name}")
            
            logger.info(f"🛒 Totale prodotti estratti: {len(results)}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Errore elaborazione {image_path}: {e}")
            return []
    
    def run(self, pdf_source=None, source_type="file"):
        """Esegue l'estrazione completa con Moondream"""
        logger.info("🚀 Avvio estrazione Moondream2 AI...")
        
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
                logger.info("⏳ Pausa di 3 secondi tra le immagini...")
                time.sleep(3)
        
        # Salva risultati
        output_file = f'moondream_results_{self.job_id}.json' if self.job_id else 'moondream_results.json'
        results_data = {
            'timestamp': datetime.now().isoformat(),
            'method': 'Moondream2 AI Extractor',
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

if __name__ == "__main__":
    # Test con API key (sostituisci con la tua)
    extractor = MoondreamExtractor(moondream_api_key="your-api-key-here")
    extractor.run()