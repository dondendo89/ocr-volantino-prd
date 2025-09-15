#!/usr/bin/env python3
"""
Script per configurare PostgreSQL locale per l'applicazione OCR Volantino
"""

import os
import subprocess
import sys
from pathlib import Path

def run_command(cmd, check=True):
    """Esegue un comando shell e restituisce il risultato"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
        return result.stdout.strip(), result.stderr.strip()
    except subprocess.CalledProcessError as e:
        print(f"❌ Errore nell'eseguire: {cmd}")
        print(f"   Stdout: {e.stdout}")
        print(f"   Stderr: {e.stderr}")
        return None, e.stderr

def check_postgresql_running():
    """Verifica se PostgreSQL è in esecuzione"""
    stdout, stderr = run_command("brew services list | grep postgresql@15", check=False)
    if stdout and "started" in stdout:
        print("✅ PostgreSQL è già in esecuzione")
        return True
    return False

def start_postgresql():
    """Avvia PostgreSQL"""
    print("🚀 Avvio PostgreSQL...")
    stdout, stderr = run_command("brew services start postgresql@15")
    if "Successfully started" in stdout:
        print("✅ PostgreSQL avviato con successo")
        return True
    else:
        print(f"❌ Errore nell'avviare PostgreSQL: {stderr}")
        return False

def create_database_and_user():
    """Crea il database e l'utente se non esistono"""
    print("🔧 Configurazione database e utente...")
    
    # Verifica se il database esiste
    stdout, stderr = run_command(
        "/usr/local/opt/postgresql@15/bin/psql -d postgres -tAc \"SELECT 1 FROM pg_database WHERE datname='ocr_volantino'\"",
        check=False
    )
    
    if "1" not in stdout:
        print("📦 Creazione database ocr_volantino...")
        run_command('/usr/local/opt/postgresql@15/bin/psql -d postgres -c "CREATE DATABASE ocr_volantino;"')
    else:
        print("✅ Database ocr_volantino già esistente")
    
    # Verifica se l'utente esiste
    stdout, stderr = run_command(
        "/usr/local/opt/postgresql@15/bin/psql -d postgres -tAc \"SELECT 1 FROM pg_roles WHERE rolname='ocr_user'\"",
        check=False
    )
    
    if "1" not in stdout:
        print("👤 Creazione utente ocr_user...")
        run_command('/usr/local/opt/postgresql@15/bin/psql -d postgres -c "CREATE USER ocr_user WITH PASSWORD \'ocr_password\';"')
        run_command('/usr/local/opt/postgresql@15/bin/psql -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE ocr_volantino TO ocr_user;"')
    else:
        print("✅ Utente ocr_user già esistente")

def test_connection():
    """Testa la connessione al database"""
    print("🔍 Test connessione database...")
    
    # Test con psycopg2
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="localhost",
            database="ocr_volantino",
            user="ocr_user",
            password="ocr_password",
            sslmode="disable"
        )
        conn.close()
        print("✅ Connessione psycopg2 riuscita")
        return True
    except Exception as e:
        print(f"❌ Errore connessione psycopg2: {e}")
        return False

def create_env_file():
    """Crea il file .env.local con la configurazione PostgreSQL corretta"""
    print("📝 Creazione file .env.local...")
    
    env_content = """# Configurazione locale per PostgreSQL
DATABASE_URL=postgresql+psycopg2://ocr_user:ocr_password@localhost/ocr_volantino
ENVIRONMENT=development
"""
    
    with open(".env.local", "w") as f:
        f.write(env_content)
    
    print("✅ File .env.local creato")

def main():
    """Funzione principale"""
    print("🐘 Setup PostgreSQL Locale per OCR Volantino")
    print("=" * 50)
    
    # Verifica se PostgreSQL è installato
    if not Path("/usr/local/opt/postgresql@15/bin/psql").exists():
        print("❌ PostgreSQL@15 non trovato. Installalo con: brew install postgresql@15")
        sys.exit(1)
    
    # Verifica se PostgreSQL è in esecuzione
    if not check_postgresql_running():
        if not start_postgresql():
            sys.exit(1)
    
    # Crea database e utente
    create_database_and_user()
    
    # Testa la connessione
    if test_connection():
        create_env_file()
        print("\n🎉 Setup completato con successo!")
        print("\n📋 Prossimi passi:")
        print("   1. Riavvia l'applicazione API")
        print("   2. Il database PostgreSQL locale è ora configurato")
        print("   3. L'URL di connessione è: postgresql+psycopg2://ocr_user:ocr_password@localhost/ocr_volantino")
    else:
        print("\n❌ Setup fallito. Controlla i log sopra per i dettagli.")
        sys.exit(1)

if __name__ == "__main__":
    main()