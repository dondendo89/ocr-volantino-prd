#!/usr/bin/env python3
import sqlite3

def check_missing_data():
    try:
        conn = sqlite3.connect('ocr_volantino.db')
        cursor = conn.cursor()
        
        # Verifica prodotti con dati mancanti
        query = """
        SELECT id, nome, prezzo, categoria, marca, quantita, confidence_score 
        FROM extracted_products 
        WHERE nome IS NULL OR nome = '' 
           OR prezzo IS NULL 
           OR categoria IS NULL OR categoria = ''
        LIMIT 20
        """
        
        cursor.execute(query)
        results = cursor.fetchall()
        
        print("🔍 VERIFICA DATI MANCANTI NEL DATABASE")
        print("=" * 50)
        
        if results:
            print(f"❌ Trovati {len(results)} prodotti con dati mancanti:")
            print()
            for row in results:
                print(f"ID: {row[0]}")
                print(f"  Nome: '{row[1]}' {'❌ VUOTO' if not row[1] else '✅'}")
                print(f"  Prezzo: {row[2]} {'❌ NULL' if row[2] is None else '✅'}")
                print(f"  Categoria: '{row[3]}' {'❌ VUOTO' if not row[3] else '✅'}")
                print(f"  Marca: '{row[4]}'")
                print(f"  Quantità: '{row[5]}'")
                print(f"  Confidence: {row[6]}")
                print("-" * 30)
        else:
            print("✅ Nessun prodotto con dati mancanti trovato!")
        
        # Statistiche generali
        cursor.execute("SELECT COUNT(*) FROM extracted_products")
        total_products = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM extracted_products WHERE nome IS NOT NULL AND nome != '' AND prezzo IS NOT NULL AND categoria IS NOT NULL AND categoria != ''")
        complete_products = cursor.fetchone()[0]
        
        print(f"\n📊 STATISTICHE:")
        print(f"  Totale prodotti: {total_products}")
        print(f"  Prodotti completi: {complete_products}")
        print(f"  Prodotti incompleti: {total_products - complete_products}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Errore durante la verifica: {e}")

if __name__ == "__main__":
    check_missing_data()