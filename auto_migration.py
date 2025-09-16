#!/usr/bin/env python3
"""
Script di migrazione automatica che viene eseguito all'avvio dell'applicazione
per assicurarsi che tutte le colonne necessarie esistano nel database.
"""

import os
import sys
from sqlalchemy import text, inspect
from sqlalchemy.exc import OperationalError, ProgrammingError
import logging

# Configura logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_and_add_image_path_column(engine):
    """
    Verifica se la colonna image_path esiste nella tabella extracted_products
    e la aggiunge se mancante.
    """
    try:
        with engine.connect() as conn:
            # Usa l'inspector per verificare le colonne esistenti
            inspector = inspect(engine)
            columns = inspector.get_columns('extracted_products')
            column_names = [col['name'] for col in columns]
            
            if 'image_path' in column_names:
                logger.info("✅ Colonna image_path già presente")
                return True
            
            # Aggiungi la colonna image_path
            logger.info("🔧 Aggiungendo colonna image_path...")
            
            # Determina il tipo di database
            db_url = str(engine.url)
            if 'postgresql' in db_url:
                sql = "ALTER TABLE extracted_products ADD COLUMN image_path VARCHAR"
            else:
                sql = "ALTER TABLE extracted_products ADD COLUMN image_path TEXT"
            
            conn.execute(text(sql))
            conn.commit()
            
            logger.info("✅ Colonna image_path aggiunta con successo")
            return True
            
    except (OperationalError, ProgrammingError) as e:
        error_msg = str(e).lower()
        if 'already exists' in error_msg or 'duplicate column' in error_msg:
            logger.info("✅ Colonna image_path già presente (rilevata da errore)")
            return True
        else:
            logger.error(f"❌ Errore durante aggiunta colonna: {e}")
            return False
    except Exception as e:
        logger.error(f"❌ Errore imprevisto: {e}")
        return False

def run_auto_migration():
    """
    Esegue tutte le migrazioni automatiche necessarie.
    """
    try:
        # Importa il database manager
        from database import db_manager
        
        logger.info("🚀 Avvio migrazione automatica...")
        
        # Verifica e aggiunge colonna image_path
        success = check_and_add_image_path_column(db_manager.engine)
        
        if success:
            logger.info("🎉 Migrazione automatica completata con successo")
        else:
            logger.warning("⚠️ Migrazione automatica completata con alcuni errori")
            
        return success
        
    except Exception as e:
        logger.error(f"❌ Errore durante migrazione automatica: {e}")
        return False

if __name__ == "__main__":
    run_auto_migration()