#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script per controllare il contenuto di un PDF
"""

import fitz  # PyMuPDF
import os
from PIL import Image
import io

def check_pdf_content(pdf_path):
    """
    Controlla il contenuto di un PDF
    """
    if not os.path.exists(pdf_path):
        print(f"❌ File non trovato: {pdf_path}")
        return
    
    try:
        print(f"🔍 Analizzando: {pdf_path}")
        print(f"📏 Dimensione file: {os.path.getsize(pdf_path)} bytes")
        print("=" * 60)
        
        # Apri il PDF
        doc = fitz.open(pdf_path)
        
        print(f"📄 Numero di pagine: {len(doc)}")
        
        if len(doc) == 0:
            print("❌ PDF vuoto - nessuna pagina trovata")
            doc.close()
            return
        
        # Analizza ogni pagina
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            print(f"\n📖 Pagina {page_num + 1}:")
            
            # Dimensioni della pagina
            rect = page.rect
            print(f"   📐 Dimensioni: {rect.width} x {rect.height}")
            
            # Testo nella pagina
            text = page.get_text()
            text_length = len(text.strip())
            print(f"   📝 Testo: {text_length} caratteri")
            
            if text_length > 0:
                # Mostra i primi 200 caratteri
                preview = text.strip()[:200]
                print(f"   👀 Preview: {repr(preview)}")
                
                # Conta parole che potrebbero essere prodotti
                words = text.lower().split()
                price_indicators = sum(1 for word in words if any(indicator in word for indicator in ['€', '$', 'euro', 'prezzo', 'sconto']))
                print(f"   💰 Indicatori di prezzo trovati: {price_indicators}")
            else:
                print("   ❌ Nessun testo trovato")
            
            # Controlla le immagini
            image_list = page.get_images()
            print(f"   🖼️ Immagini: {len(image_list)}")
            
            # Prova a convertire in immagine per vedere se ha contenuto visivo
            try:
                mat = fitz.Matrix(1.0, 1.0)  # Scala normale
                pix = page.get_pixmap(matrix=mat)
                img_bytes = pix.tobytes("png")
                
                # Analizza l'immagine
                image = Image.open(io.BytesIO(img_bytes))
                
                # Controlla se l'immagine è principalmente bianca (vuota)
                # Converti in scala di grigi e calcola la media
                gray_image = image.convert('L')
                pixels = list(gray_image.getdata())
                avg_brightness = sum(pixels) / len(pixels)
                
                print(f"   🎨 Luminosità media: {avg_brightness:.1f}/255 ({'vuota' if avg_brightness > 240 else 'con contenuto'})")
                
            except Exception as e:
                print(f"   ❌ Errore nell'analisi visiva: {e}")
        
        doc.close()
        
    except Exception as e:
        print(f"❌ Errore durante l'analisi: {e}")

def main():
    """Funzione principale"""
    print("🔍 Analisi PDF Files")
    print("=" * 60)
    
    # Controlla entrambi i file
    files_to_check = ["test_volantino.pdf", "volantino.pdf"]
    
    for pdf_file in files_to_check:
        if os.path.exists(pdf_file):
            check_pdf_content(pdf_file)
            print("\n" + "=" * 60 + "\n")
        else:
            print(f"⚠️ File non trovato: {pdf_file}")

if __name__ == "__main__":
    main()