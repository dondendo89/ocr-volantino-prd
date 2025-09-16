#!/usr/bin/env python3
"""
Migrazione universale per aggiungere la colonna image_path alla tabella extracted_products
Funziona sia con SQLite (locale) che PostgreSQL (produzione)
"""

import os
import sys
sys.path.append('.')

from database import db_manager
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError
from api_config import DATABASE_URL

def detect_database_type():
    """Rileva il tipo di database dalla URL"""
    if DATABASE_URL.startswith("sqlite"):
        return "sqlite"
    elif DATABASE_URL.startswith("postgresql"):
        return "postgresql"
    else:
        return "unknown"

def add_image_path_column_sqlite():
    """Aggiunge la colonna image_path per SQLite"""
    try:
        with db_manager.engine.connect() as conn:
            # Verifica se la colonna esiste già (SQLite syntax)
            result = conn.execute(text("PRAGMA table_info(extracted_products)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'image_path' in columns:
                print("✅ La colonna image_path esiste già")
                return True
            
            # Aggiungi la colonna image_path
            print("🔧 Aggiungendo la colonna image_path...")
            conn.execute(text("ALTER TABLE extracted_products ADD COLUMN image_path TEXT"))
            conn.commit()
            print("✅ Colonna image_path aggiunta con successo")
            
            # Verifica che la colonna sia stata aggiunta
            result = conn.execute(text("PRAGMA table_info(extracted_products)"))
            columns_after = [row[1] for row in result.fetchall()]
            
            if 'image_path' in columns_after:
                print("✅ Migrazione completata con successo")
                return True
            else:
                print("❌ Errore: la colonna non è stata aggiunta")
                return False
                
    except Exception as e:
        print(f"❌ Errore durante la migrazione SQLite: {e}")
        return False

def add_image_path_column_postgresql():
    """Aggiunge la colonna image_path per PostgreSQL"""
    try:
        with db_manager.engine.connect() as conn:
            # Verifica se la colonna esiste già (PostgreSQL syntax)
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'extracted_products' 
                AND column_name = 'image_path'
            """))
            
            existing_column = result.fetchone()
            
            if existing_column:
                print("✅ La colonna image_path esiste già")
                return True
            
            # Aggiungi la colonna image_path
            print("🔧 Aggiungendo la colonna image_path...")
            conn.execute(text("ALTER TABLE extracted_products ADD COLUMN image_path TEXT"))
            conn.commit()
            print("✅ Colonna image_path aggiunta con successo")
            
            # Verifica che la colonna sia stata aggiunta
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'extracted_products' 
                AND column_name = 'image_path'
            """))
            
            if result.fetchone():
                print("✅ Migrazione completata con successo")
                return True
            else:
                print("❌ Errore: la colonna non è stata aggiunta")
                return False
                
    except (OperationalError, ProgrammingError) as e:
        if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
            print("✅ La colonna image_path esiste già")
            return True
        else:
            print(f"❌ Errore durante la migrazione PostgreSQL: {e}")
            return False
    except Exception as e:
        print(f"❌ Errore durante la migrazione PostgreSQL: {e}")
        return False

def check_database_connection():
    """Verifica la connessione al database"""
    try:
        with db_manager.engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
            db_type = detect_database_type()
            print(f"✅ Connessione al database {db_type.upper()} riuscita")
            return True
    except Exception as e:
        print(f"❌ Errore di connessione al database: {e}")
        return False

def check_table_structure():
    """Verifica la struttura della tabella extracted_products"""
    db_type = detect_database_type()
    
    try:
        with db_manager.engine.connect() as conn:
            if db_type == "sqlite":
                result = conn.execute(text("PRAGMA table_info(extracted_products)"))
                columns = result.fetchall()
                print("\n📋 Struttura attuale della tabella extracted_products (SQLite):")
                for col in columns:
                    print(f"  - {col[1]} ({col[2]}) {'NULL' if col[3] == 0 else 'NOT NULL'}")
            
            elif db_type == "postgresql":
                result = conn.execute(text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = 'extracted_products'
                    ORDER BY ordinal_position
                """))
                
                columns = result.fetchall()
                print("\n📋 Struttura attuale della tabella extracted_products (PostgreSQL):")
                for col in columns:
                    print(f"  - {col[0]} ({col[1]}) {'NULL' if col[2] == 'YES' else 'NOT NULL'}")
            
            return True
    except Exception as e:
        print(f"❌ Errore durante verifica struttura tabella: {e}")
        return False

def run_migration():
    """Esegue la migrazione appropriata in base al tipo di database"""
    db_type = detect_database_type()
    
    print(f"🔍 Database rilevato: {db_type.upper()}")
    
    if db_type == "sqlite":
        return add_image_path_column_sqlite()
    elif db_type == "postgresql":
        return add_image_path_column_postgresql()
    else:
        print(f"❌ Tipo di database non supportato: {db_type}")
        return False

if __name__ == "__main__":
    print("🔧 Migrazione Universale - Aggiunta colonna image_path")
    print("=" * 60)
    print(f"📍 Database URL: {DATABASE_URL[:50]}...")
    
    # Verifica connessione
    if not check_database_connection():
        print("💥 Migrazione fallita - Impossibile connettersi al database!")
        sys.exit(1)
    
    # Mostra struttura attuale
    check_table_structure()
    
    # Esegui migrazione
    success = run_migration()
    
    if success:
        print("\n🎉 Migrazione completata con successo!")
        # Mostra struttura aggiornata
        print("\n📋 Struttura aggiornata:")
        check_table_structure()
    else:
        print("\n💥 Migrazione fallita!")
        sys.exit(1)