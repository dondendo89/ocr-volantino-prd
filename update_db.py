#!/usr/bin/env python3

from database import db_manager
from sqlalchemy import text

def update_database():
    """Aggiunge le colonne supermercato_nome e supermercato_id alla tabella processing_jobs"""
    try:
        with db_manager.engine.connect() as conn:
            # Verifica se le colonne esistono già
            result = conn.execute(text("PRAGMA table_info(processing_jobs)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'supermercato_nome' not in columns:
                print("Aggiungendo colonna supermercato_nome...")
                conn.execute(text("ALTER TABLE processing_jobs ADD COLUMN supermercato_nome TEXT"))
                conn.commit()
                print("✅ Colonna supermercato_nome aggiunta con successo!")
            else:
                print("✅ Colonna supermercato_nome già presente.")
                
            if 'supermercato_id' not in columns:
                print("Aggiungendo colonna supermercato_id...")
                conn.execute(text("ALTER TABLE processing_jobs ADD COLUMN supermercato_id INTEGER"))
                conn.commit()
                print("✅ Colonna supermercato_id aggiunta con successo!")
            else:
                print("✅ Colonna supermercato_id già presente.")
                
    except Exception as e:
        print(f"❌ Errore durante aggiornamento database: {e}")
        raise

if __name__ == "__main__":
    update_database()