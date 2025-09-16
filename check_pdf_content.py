#!/usr/bin/env python3
import fitz

def check_pdf_content(pdf_path):
    try:
        doc = fitz.open(pdf_path)
        print(f"📄 PDF: {pdf_path}")
        print(f"📊 Pagine totali: {doc.page_count}")
        
        for i in range(doc.page_count):
            page = doc[i]
            text = page.get_text()
            print(f"\n📖 Pagina {i+1}:")
            print(f"   Caratteri di testo: {len(text)}")
            if text.strip():
                print(f"   Primi 300 caratteri: {text[:300]}...")
            else:
                print("   ⚠️ Nessun testo estratto (potrebbe essere solo immagini)")
                
            # Controlla se ci sono immagini
            image_list = page.get_images()
            print(f"   🖼️ Immagini trovate: {len(image_list)}")
            
        doc.close()
        
    except Exception as e:
        print(f"❌ Errore nell'analisi del PDF: {e}")

if __name__ == "__main__":
    check_pdf_content("test.pdf")