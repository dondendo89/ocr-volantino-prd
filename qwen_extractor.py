#!/usr/bin/env python3
"""
Estrattore Qwen2.5-VL AI per volantini
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

class QwenExtractor:
    def __init__(self, job_id=None, db_manager=None):
        logger.info("🔮 Inizializzando estrattore Qwen2.5-VL AI...")
        
        self.job_id = job_id
        self.db_manager = db_manager
        
        # Inizializza Qwen2.5-VL
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            
            model_id = "Qwen/Qwen2.5-VL-7B-Instruct"
            
            # Carica il modello e tokenizer
            self.model = AutoModelForCausalLM.from_pretrained(
                model_id,
                torch_dtype="auto",
                device_map="auto",
                trust_remote_code=True
            )
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_id,
                trust_remote_code=True
            )
            
            logger.info("✅ Qwen2.5-VL inizializzato con successo")
            
        except Exception as e:
            logger.error(f"❌ Errore inizializzazione Qwen2.5-VL: {e}")
            logger.info("💡 Suggerimento: Assicurati di avere torch installato e memoria sufficiente")
            raise
        
        # Crea directory per le immagini temporanee
        self.temp_dir = Path(f"temp_processing_{job_id}" if job_id else "temp_processing_qwen")
        self.temp_dir.mkdir(exist_ok=True)
        
        # Crea directory per le immagini dei prodotti
        self.product_images_dir = Path("qwen_product_images")
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
    
    def analyze_with_qwen(self, image_path, retry_count=3):
        """Analizza immagine con Qwen2.5-VL AI"""
        for attempt in range(retry_count):
            try:
                logger.info(f"🔮 Tentativo {attempt + 1}/{retry_count} - Analizzando con Qwen: {Path(image_path).name}")
                
                # Carica immagine
                image = Image.open(image_path)
                
                # Prompt per estrazione prodotti
                prompt = """Analizza questa immagine di un volantino di supermercato italiano e estrai le informazioni sui prodotti alimentari visibili.

Per ogni prodotto che vedi chiaramente, fornisci:
- Nome completo del prodotto
- Marca (se visibile)
- Categoria (latticini, pasta, bevande, dolci, carne, pesce, frutta, verdura, etc.)
- Prezzo in euro (se visibile)
- Breve descrizione

Rispondi ESCLUSIVAMENTE in formato JSON valido con questa struttura:
{
  "prodotti": [
    {
      "nome": "nome completo del prodotto",
      "marca": "marca del prodotto",
      "categoria": "categoria del prodotto",
      "prezzo": "prezzo in euro se visibile",
      "descrizione": "breve descrizione"
    }
  ]
}

Regole importanti:
- Estrai SOLO prodotti alimentari chiaramente visibili e leggibili
- Se non vedi un prezzo, scrivi "Non visibile"
- Se non riconosci una marca, scrivi "Non identificata"
- Concentrati sui prodotti più evidenti
- Massimo 10 prodotti per immagine
- Rispondi SOLO con il JSON, senza altro testo"""
                
                # Prepara input per il modello
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "image", "image": image},
                            {"type": "text", "text": prompt}
                        ]
                    }
                ]
                
                # Applica chat template
                text = self.tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )
                
                # Prepara input per il modello
                model_inputs = self.tokenizer(
                    text, return_tensors="pt"
                ).to(self.model.device)
                
                # Genera risposta
                with torch.no_grad():
                    generated_ids = self.model.generate(
                        **model_inputs,
                        max_new_tokens=1024,
                        temperature=0.1,
                        do_sample=True,
                        pad_token_id=self.tokenizer.eos_token_id
                    )
                
                # Decodifica risposta
                generated_ids = [
                    output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
                ]
                response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
                
                logger.info(f"🔮 Risposta Qwen ricevuta")
                
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
                        logger.info(f"✅ Qwen ha analizzato con successo l'immagine")
                        return parsed_json
                    else:
                        # Se non trova JSON, prova a crearlo dalla risposta testuale
                        logger.warning("⚠️ JSON non trovato, tentativo di parsing testuale")
                        return self.parse_text_response(response)
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"⚠️ Errore parsing JSON da Qwen: {e}")
                    logger.info(f"Risposta Qwen: {response[:300]}...")
                    # Prova parsing testuale
                    return self.parse_text_response(response)
                    
            except Exception as e:
                logger.error(f"❌ Errore chiamata Qwen tentativo {attempt + 1}: {e}")
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
                if any(keyword in line.lower() for keyword in ['nome:', 'prodotto:', '1.', '2.', '3.', '4.', '5.']):
                    if current_product and 'nome' in current_product:
                        products.append(current_product)
                        current_product = {}
                    
                    # Estrai nome del prodotto
                    if ':' in line:
                        current_product['nome'] = line.split(':', 1)[1].strip()
                    else:
                        # Rimuovi numerazione
                        nome = re.sub(r'^\d+\.\s*', '', line).strip()
                        if nome:
                            current_product['nome'] = nome
                            
                elif 'marca:' in line.lower():
                    current_product['marca'] = line.split(':', 1)[1].strip()
                elif 'categoria:' in line.lower():
                    current_product['categoria'] = line.split(':', 1)[1].strip()
                elif 'prezzo:' in line.lower():
                    current_product['prezzo'] = line.split(':', 1)[1].strip()
                elif 'descrizione:' in line.lower():
                    current_product['descrizione'] = line.split(':', 1)[1].strip()
                elif '€' in line or 'euro' in line.lower():
                    # Prova a estrarre prezzo dalla linea
                    price_match = re.search(r'(\d+[.,]\d{1,2}|\d+)\s*€?', line)
                    if price_match and 'prezzo' not in current_product:
                        current_product['prezzo'] = price_match.group(1)
            
            if current_product and 'nome' in current_product:
                products.append(current_product)
            
            # Aggiungi valori di default per campi mancanti
            for product in products:
                if 'marca' not in product:
                    product['marca'] = 'Non identificata'
                if 'categoria' not in product:
                    product['categoria'] = 'Non specificata'
                if 'prezzo' not in product:
                    product['prezzo'] = 'Non visibile'
                if 'descrizione' not in product:
                    product['descrizione'] = ''
            
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
                'fonte_estrazione': 'Qwen2.5-VL AI',
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
        """Elabora una singola immagine con Qwen"""
        logger.info(f"📸 Elaborando: {Path(image_path).name}")
        
        try:
            image_name = Path(image_path).stem
            results = []
            
            # Analisi con Qwen AI
            qwen_result = self.analyze_with_qwen(image_path)
            
            if qwen_result and 'prodotti' in qwen_result:
                logger.info(f"🔮 Qwen ha trovato {len(qwen_result['prodotti'])} prodotti")
                
                for i, prodotto in enumerate(qwen_result['prodotti']):
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
                        'fonte': 'Qwen2.5-VL AI',
                        'immagine_prodotto': image_path_saved or 'Non disponibile',
                        'immagine_originale': str(image_path)
                    }
                    
                    results.append(result)
            else:
                logger.warning(f"⚠️ Qwen non ha trovato prodotti in {Path(image_path).name}")
            
            logger.info(f"🛒 Totale prodotti estratti: {len(results)}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Errore elaborazione {image_path}: {e}")
            return []
    
    def run(self, pdf_source=None, source_type="file"):
        """Esegue l'estrazione completa con Qwen"""
        logger.info("🚀 Avvio estrazione Qwen2.5-VL AI...")
        
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
            
            # Pausa tra le immagini per evitare sovraccarico
            if i < len(image_paths) - 1:
                logger.info("⏳ Pausa di 2 secondi tra le immagini...")
                time.sleep(2)
        
        # Salva risultati
        output_file = f'qwen_results_{self.job_id}.json' if self.job_id else 'qwen_results.json'
        results_data = {
            'timestamp': datetime.now().isoformat(),
            'method': 'Qwen2.5-VL AI Extractor',
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
    # Test del modello
    extractor = QwenExtractor()
    extractor.run()