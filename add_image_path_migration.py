#!/usr/bin/env python3
"""
Migrazione per aggiungere la colonna image_path alla tabella extracted_products
"""

import sqlite3
import os
from pathlib import Path

def add_image_path_column():
    """Aggiunge la colonna image_path alla tabella extracted_products se non esiste"""
    db_path = 'ocr_volantino.db'
    
    if not os.path.exists(db_path):
        print(f"❌ Database {db_path} non trovato")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verifica se la colonna esiste già
        cursor.execute("PRAGMA table_info(extracted_products)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'image_path' in columns:
            print("✅ La colonna image_path esiste già")
            return True
        
        # Aggiungi la colonna image_path
        print("🔧 Aggiungendo la colonna image_path...")
        cursor.execute("ALTER TABLE extracted_products ADD COLUMN image_path TEXT")
        
        # Commit delle modifiche
        conn.commit()
        print("✅ Colonna image_path aggiunta con successo")
        
        # Verifica che la colonna sia stata aggiunta
        cursor.execute("PRAGMA table_info(extracted_products)")
        columns_after = [column[1] for column in cursor.fetchall()]
        
        if 'image_path' in columns_after:
            print("✅ Migrazione completata con successo")
            return True
        else:
            print("❌ Errore: la colonna non è stata aggiunta")
            return False
            
    except Exception as e:
        print(f"❌ Errore durante la migrazione: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("🚀 Avvio migrazione database...")
    success = add_image_path_column()
    
    if success:
        print("🎉 Migrazione completata con successo!")
    else:
        print("💥 Migrazione fallita!")
        exit(1)