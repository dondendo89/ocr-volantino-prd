#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script per controllare le immagini dei prodotti nel database
"""

import sqlite3
import os
from datetime import datetime

def check_product_images():
    """
    Controlla le immagini dei prodotti nel database
    """
    db_path = "ocr_volantino.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database non trovato: {db_path}")
        return
    
    try:
        # Connessione al database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🖼️ Controllo Immagini Prodotti")
        print("=" * 60)
        
        # Conta prodotti con e senza immagini
        cursor.execute("SELECT COUNT(*) FROM extracted_products")
        total_products = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM extracted_products WHERE image_url IS NOT NULL AND image_url != ''")
        products_with_url = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM extracted_products WHERE image_path IS NOT NULL AND image_path != ''")
        products_with_path = cursor.fetchone()[0]
        
        print(f"📊 Statistiche Immagini:")
        print(f"   Prodotti totali: {total_products}")
        print(f"   Con image_url: {products_with_url}")
        print(f"   Con image_path: {products_with_path}")
        print()
        
        # Mostra gli ultimi 10 prodotti con dettagli immagini
        print("🔍 Ultimi 10 prodotti:")
        cursor.execute("""
            SELECT nome, image_url, image_path, job_id, extracted_at
            FROM extracted_products
            ORDER BY extracted_at DESC
            LIMIT 10
        """)
        
        products = cursor.fetchall()
        
        for i, (nome, image_url, image_path, job_id, extracted_at) in enumerate(products, 1):
            print(f"{i:2d}. {nome[:40]}...")
            print(f"     🔗 URL: {image_url or '❌ Non presente'}")
            print(f"     📁 Path: {image_path or '❌ Non presente'}")
            print(f"     🆔 Job: {job_id[:8]}...")
            print(f"     📅 Data: {extracted_at}")
            
            # Controlla se il file esiste fisicamente
            if image_path and os.path.exists(image_path):
                file_size = os.path.getsize(image_path)
                print(f"     ✅ File esiste ({file_size} bytes)")
            elif image_path:
                print(f"     ❌ File non trovato")
            
            print()
        
        # Controlla le directory delle immagini
        print("📁 Directory Immagini:")
        image_dirs = [
            "static/product_images",
            "simplified_gemini_product_images", 
            "processed_images",
            "temp_processing"
        ]
        
        for dir_path in image_dirs:
            if os.path.exists(dir_path):
                files = os.listdir(dir_path)
                print(f"   {dir_path}: {len(files)} files")
                if files:
                    # Mostra i primi 3 file
                    for f in files[:3]:
                        print(f"     - {f}")
                    if len(files) > 3:
                        print(f"     ... e altri {len(files) - 3} file")
            else:
                print(f"   {dir_path}: ❌ Non esiste")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ Errore database: {e}")
    except Exception as e:
        print(f"❌ Errore: {e}")

if __name__ == "__main__":
    check_product_images()