#!/usr/bin/env python3
"""
Migrazione PostgreSQL per aggiungere la colonna image_path alla tabella extracted_products
"""

import os
import psycopg2
from psycopg2 import sql
import traceback

def add_image_path_column_postgresql():
    """Aggiunge la colonna image_path alla tabella extracted_products se non esiste"""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL non configurata")
        return False
    
    try:
        # Connessione al database PostgreSQL
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("🔍 Verificando se la colonna image_path esiste...")
        
        # Verifica se la colonna esiste già
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'extracted_products' 
            AND column_name = 'image_path'
        """)
        
        result = cursor.fetchone()
        
        if result:
            print("✅ La colonna image_path esiste già")
            return True
        
        # Aggiungi la colonna image_path
        print("🔧 Aggiungendo la colonna image_path...")
        cursor.execute("""
            ALTER TABLE extracted_products 
            ADD COLUMN image_path VARCHAR(500)
        """)
        
        # Commit delle modifiche
        conn.commit()
        print("✅ Colonna image_path aggiunta con successo")
        
        # Verifica che la colonna sia stata aggiunta
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'extracted_products' 
            AND column_name = 'image_path'
        """)
        
        result_after = cursor.fetchone()
        
        if result_after:
            print("✅ Migrazione completata con successo")
            return True
        else:
            print("❌ Errore: la colonna non è stata aggiunta")
            return False
            
    except Exception as e:
        print(f"❌ Errore durante la migrazione: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("🚀 Avvio migrazione PostgreSQL...")
    success = add_image_path_column_postgresql()
    
    if success:
        print("🎉 Migrazione PostgreSQL completata con successo!")
    else:
        print("💥 Migrazione PostgreSQL fallita!")
        exit(1)