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

# Crea la directory per salvare le immagini
def setup_image_directory():
    dir_name = "immagini_prodotti"
    # Rimuovi la directory e ricreala per evitare errori "File exists"
    if os.path.exists(dir_name):
        shutil.rmtree(dir_name)
    os.makedirs(dir_name)
    return dir_name

def get_page_image(pdf_path, page_num):
    """
    Estrae una singola pagina da un PDF come immagine.
    """
    try:
        doc = fitz.open(pdf_path)
        page = doc.load_page(page_num)
        pix = page.get_pixmap()
        img_bytes = pix.tobytes("png")
        doc.close()
        image = Image.open(io.BytesIO(img_bytes))
        return image
    except Exception as e:
        log_message(f"❌ Errore durante l'estrazione dell'immagine della pagina {page_num + 1}: {e}")
        return None

def log_message(message):
    """
    Funzione ausiliaria per stampare messaggi con timestamp.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def crop_and_save_product_image(page_image, bounding_box, image_dir, page_number, product_index):
    """
    Ritaglia e salva l'immagine di un singolo prodotto, includendo un'area più ampia
    per catturare prezzo e dettagli.
    """
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
        image_path = os.path.join(image_dir, image_name)
        cropped_image.save(image_path)
        log_message(f"✅ Immagine del prodotto salvata in: {image_path}")
        return image_path
    except Exception as e:
        log_message(f"❌ Errore durante il ritaglio o il salvataggio dell'immagine del prodotto: {e}")
        return None

def process_single_page(pdf_path, page_number, prompt, image_dir):
    """
    Funzione che esegue l'intera logica (estrazione e analisi Gemini) per una singola pagina.
    """
    log_message(f"🚀 Pagina {page_number}: Inizio estrazione immagine...")
    page_image = get_page_image(pdf_path, page_number - 1)

    if not page_image:
        return {"page": page_number, "products": [], "success": False, "error": "Impossibile estrarre l'immagine."}

    log_message(f"✅ Pagina {page_number}: Immagine estratta, {page_image.width}x{page_image.height} pixel.")
    log_message(f"🤖 Pagina {page_number}: Invio a Gemini per l'analisi...")

    genai.configure(api_key="AIzaSyDglA1cwH8lMkGc0GLKNKLv5ulCWL1omag")
    model = genai.GenerativeModel('gemini-1.5-flash-latest')

    buffered = io.BytesIO()
    page_image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

    try:
        raw_response = model.generate_content([prompt, {"mime_type": "image/png", "data": img_str}]).text
        log_message(f"📄 Pagina {page_number}: Risposta grezza di Gemini:\n{raw_response}")

        match = re.search(r'\[.*\]', raw_response, re.DOTALL)
        if match:
            json_str = match.group(0)
            products_on_page = json.loads(json_str)

            # Process and save product images
            for i, product in enumerate(products_on_page):
                # Ensure date fields are present, even if null
                product.setdefault("data_inizio_offerta", None)
                product.setdefault("data_fine_offerta", None)

                if "bounding_box" in product and product["bounding_box"]:
                    image_path = crop_and_save_product_image(page_image, product["bounding_box"], image_dir, page_number, i + 1)
                    product["immagine_prodotto"] = image_path
                    del product["bounding_box"]  # Rimuovi il campo bounding_box
                else:
                    product["immagine_prodotto"] = None

            return {"page": page_number, "products": products_on_page, "success": True, "error": None}
        else:
            return {"page": page_number, "products": [], "success": False, "error": "Nessun blocco JSON valido trovato."}
    except ResourceExhausted:
        return {"page": page_number, "products": [], "success": False, "error": "Quota di token esaurita. Attendi e riprova più tardi."}
    except Exception as e:
        return {"page": page_number, "products": [], "success": False, "error": str(e)}

# --- Esempio di Utilizzo ---
pdf_path = "volantino.pdf"
try:
    doc = fitz.open(pdf_path)
    total_pages = doc.page_count
    doc.close()
except Exception as e:
    log_message(f"❌ Errore durante l' apertura del PDF: {e}")
    total_pages = 0

all_products = []
prompt_text = """
Analizza attentamente questa immagine di un volantino di supermercato.
Estrai un elenco completo di tutti i prodotti in offerta. Per ogni prodotto, fornisci:
- **nome_prodotto**: Il nome completo del prodotto.
- **prezzo**: Il prezzo di vendita del prodotto.
- **prezzo_al_kg/l**: Il prezzo al chilo o al litro, se disponibile.
- **quantità**: La quantità del prodotto (peso o unità, es. "500g", "6x70g", "1L").
- **marca**: La marca del prodotto, se visibile.
- **data_inizio_offerta**: La data di inizio dell'offerta, se specificata. Formato YYYY-MM-DD.
- **data_fine_offerta**: La data di fine dell'offerta, se specificata. Formato YYYY-MM-DD.
- **bounding_box**: Le coordinate del riquadro del prodotto nell'immagine, in formato [x_min, y_min, x_max, y_max] con valori normalizzati tra 0 e 1.

Formatta il risultato come un array di oggetti JSON. Se non trovi prodotti, restituisci un array vuoto [].
Assicurati di non tralasciare nessun prodotto visibile.
"""

if total_pages > 0:
    log_message(f"Inizio elaborazione. Trovate {total_pages} pagine nel PDF.")
    image_directory = setup_image_directory()

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(process_single_page, pdf_path, page_num, prompt_text, image_directory) for page_num in range(1, total_pages + 1)}

        for future in as_completed(futures):
            result = future.result()
            if result["success"]:
                all_products.extend(result["products"])
                log_message(f"✅ Pagina {result['page']}: Trovati {len(result['products'])} prodotti.")
            else:
                log_message(f"❌ Pagina {result['page']}: Errore - {result['error']}")

    log_message("\n--- Processo completato ---")
    log_message(f"Totale prodotti estratti: {len(all_products)}")
    print("\n--- Risultato Combinato (JSON Finale) ---")
    print(json.dumps(all_products, indent=2))

    # Salva tutti i prodotti in un file JSON
    output_filename = "prodotti_volantino.json"
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(all_products, f, indent=2, ensure_ascii=False)
    log_message(f"✅ Tutti i prodotti salvati in: {output_filename}")

else:
    log_message("Nessuna pagina trovata nel PDF. Controlla il percorso del file.")