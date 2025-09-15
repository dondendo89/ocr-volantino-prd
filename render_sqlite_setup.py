#!/usr/bin/env python3
"""
Script per configurare SQLite su Render con disco persistente
"""

import os
import sys
sys.path.append('.')

from pathlib import Path
from database import db_manager
from sqlalchemy import text

def setup_render_sqlite():
    """Configura SQLite per Render con disco persistente"""
    print("🚀 Configurazione SQLite per Render...")
    
    # Path del database su disco persistente Render
    render_db_path = "/var/lib/sqlite/ocr_volantino.db"
    local_db_path = "./ocr_volantino.db"
    
    # Verifica se siamo su Render (presenza del mount path)
    is_render = os.path.exists("/var/lib/sqlite")
    
    if is_render:
        print("✅ Ambiente Render rilevato")
        db_path = render_db_path
        # Assicurati che la directory esista
        os.makedirs("/var/lib/sqlite", exist_ok=True)
    else:
        print("🏠 Ambiente locale rilevato")
        db_path = local_db_path
    
    print(f"📁 Database path: {db_path}")
    
    # Aggiorna la variabile d'ambiente DATABASE_URL
    database_url = f"sqlite:///{db_path}"
    os.environ["DATABASE_URL"] = database_url
    
    print(f"🔧 DATABASE_URL impostato: {database_url}")
    
    return db_path, is_render

def create_render_yaml():
    """Crea il file render.yaml con configurazione SQLite"""
    render_yaml_content = """services:
  - type: web
    name: ocr-volantino-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python3 api_main.py
    envVars:
      - key: ENVIRONMENT
        value: production
      - key: DATABASE_URL
        value: sqlite:///var/lib/sqlite/ocr_volantino.db
      - key: GEMINI_API_KEY
        sync: false
      - key: GEMINI_API_KEY_2
        sync: false
    disk:
      name: sqlite-disk
      mountPath: /var/lib/sqlite
      sizeGB: 1
"""
    
    with open("render.yaml", "w") as f:
        f.write(render_yaml_content)
    
    print("✅ File render.yaml creato con configurazione SQLite")

def update_api_config():
    """Aggiorna api_config.py per supportare SQLite su Render"""
    config_update = """
# Configurazione specifica per Render SQLite
if os.path.exists("/var/lib/sqlite"):
    # Siamo su Render, usa il disco persistente
    DATABASE_URL = "sqlite:///var/lib/sqlite/ocr_volantino.db"
else:
    # Ambiente locale o altra configurazione
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ocr_volantino.db")
"""
    
    print("📝 Aggiornamento suggerito per api_config.py:")
    print(config_update)
    
    return config_update

def test_sqlite_connection(db_path):
    """Testa la connessione SQLite"""
    try:
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        conn.close()
        
        if result:
            print("✅ Connessione SQLite funzionante")
            return True
        else:
            print("❌ Problema con la connessione SQLite")
            return False
            
    except Exception as e:
        print(f"❌ Errore connessione SQLite: {e}")
        return False

def create_tables_sqlite(db_path):
    """Crea le tabelle nel database SQLite"""
    try:
        # Usa SQLAlchemy per creare le tabelle
        from database import Base
        from sqlalchemy import create_engine
        
        engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(engine)
        
        print("✅ Tabelle SQLite create con successo")
        return True
        
    except Exception as e:
        print(f"❌ Errore creazione tabelle: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Setup SQLite per Render")
    print("=" * 50)
    
    # Setup del database
    db_path, is_render = setup_render_sqlite()
    
    # Test connessione
    if test_sqlite_connection(db_path):
        print("✅ Database SQLite configurato correttamente")
    else:
        print("❌ Problema con la configurazione SQLite")
        sys.exit(1)
    
    # Crea tabelle se necessario
    create_tables_sqlite(db_path)
    
    # Crea render.yaml
    create_render_yaml()
    
    # Mostra aggiornamento per api_config.py
    update_api_config()
    
    print("\n🎉 Setup completato!")
    print("\n📋 Prossimi passi:")
    print("1. Aggiorna api_config.py con il codice suggerito sopra")
    print("2. Committa le modifiche")
    print("3. Su Render, crea un disco chiamato 'sqlite-disk' da 1GB")
    print("4. Redeploy il servizio")
    print("\n💡 Vantaggi SQLite su Render:")
    print("- Nessun costo aggiuntivo per il database")
    print("- Dati persistenti con il disco")
    print("- Nessun problema di SSL/connessione")
    print("- Backup semplice del file .db")