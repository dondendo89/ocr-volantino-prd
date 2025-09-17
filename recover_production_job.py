#!/usr/bin/env python3
"""
Script per recuperare job bloccati in produzione
Questo script può essere eseguito direttamente sul server di produzione
"""

import os
import sys
import requests
import time
from datetime import datetime

def recover_job_via_api(job_id, base_url="https://ocr-volantino-api.onrender.com"):
    """
    Recupera un job tramite API di produzione
    """
    print(f"🔄 Tentativo di recupero job {job_id} tramite API...")
    
    try:
        # Prima controlla lo stato attuale
        response = requests.get(f"{base_url}/jobs/{job_id}")
        
        if response.status_code != 200:
            print(f"❌ Errore nel recupero stato job: {response.status_code}")
            return False
        
        job_data = response.json()
        print(f"📋 Stato attuale del job:")
        print(f"   - Stato: {job_data.get('status')}")
        print(f"   - Progresso: {job_data.get('progress')}%")
        print(f"   - Messaggio: {job_data.get('message')}")
        print(f"   - Creato: {job_data.get('created_at')}")
        
        if job_data.get('status') != 'processing':
            print(f"⚠️ Job non è in stato processing (stato: {job_data.get('status')})")
            return False
        
        # Simula il riavvio del job creando un nuovo job con lo stesso file
        # Questo è un workaround dato che non abbiamo un endpoint di recovery diretto
        print(f"💡 Suggerimento: Per recuperare questo job, è necessario:")
        print(f"   1. Accedere al server di produzione")
        print(f"   2. Eseguire il comando SQL di reset del job")
        print(f"   3. Oppure riprocessare il file originale")
        
        return True
        
    except Exception as e:
        print(f"❌ Errore durante il recupero: {e}")
        return False

def generate_sql_recovery_command(job_id):
    """
    Genera il comando SQL per recuperare il job
    """
    sql_command = f"""
-- Comando SQL per recuperare il job {job_id}
UPDATE processing_jobs 
SET 
    status = 'queued',
    progress = 0,
    message = 'Job riavviato automaticamente dopo errore SSL',
    started_at = NULL
WHERE id = '{job_id}' AND status = 'processing';

-- Verifica il risultato
SELECT id, status, progress, message, started_at 
FROM processing_jobs 
WHERE id = '{job_id}';
"""
    
    print("📝 Comando SQL per il recupero:")
    print("=" * 50)
    print(sql_command)
    print("=" * 50)
    
    return sql_command

def monitor_job_progress(job_id, base_url="https://ocr-volantino-api.onrender.com", timeout_minutes=30):
    """
    Monitora il progresso di un job
    """
    print(f"👀 Monitoraggio progresso job {job_id}...")
    print(f"⏱️ Timeout: {timeout_minutes} minuti")
    
    start_time = time.time()
    last_progress = -1
    
    try:
        while True:
            elapsed_minutes = (time.time() - start_time) / 60
            
            if elapsed_minutes > timeout_minutes:
                print(f"⏰ Timeout raggiunto ({timeout_minutes} minuti)")
                break
            
            try:
                response = requests.get(f"{base_url}/jobs/{job_id}")
                
                if response.status_code == 200:
                    job_data = response.json()
                    current_progress = job_data.get('progress', 0)
                    status = job_data.get('status')
                    message = job_data.get('message', '')
                    
                    if current_progress != last_progress or status != 'processing':
                        timestamp = datetime.now().strftime('%H:%M:%S')
                        print(f"[{timestamp}] 📊 Stato: {status} | Progresso: {current_progress}% | {message}")
                        last_progress = current_progress
                    
                    if status in ['completed', 'failed']:
                        print(f"🏁 Job terminato con stato: {status}")
                        break
                        
                else:
                    print(f"⚠️ Errore API: {response.status_code}")
                
            except Exception as e:
                print(f"⚠️ Errore durante il monitoraggio: {e}")
            
            time.sleep(10)  # Controlla ogni 10 secondi
            
    except KeyboardInterrupt:
        print(f"\n⏹️ Monitoraggio interrotto dall'utente")

def main():
    """Funzione principale"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Recupero job bloccati in produzione')
    parser.add_argument('--job-id', type=str, required=True,
                       help='ID del job da recuperare')
    parser.add_argument('--base-url', type=str, 
                       default='https://ocr-volantino-api.onrender.com',
                       help='URL base dell\'API')
    parser.add_argument('--monitor', action='store_true',
                       help='Monitora il progresso del job dopo il recupero')
    parser.add_argument('--sql-only', action='store_true',
                       help='Genera solo il comando SQL senza eseguire il recupero')
    
    args = parser.parse_args()
    
    print("🚀 Production Job Recovery Script")
    print("=" * 50)
    print(f"🎯 Job ID: {args.job_id}")
    print(f"🌐 API URL: {args.base_url}")
    print()
    
    if args.sql_only:
        # Genera solo il comando SQL
        generate_sql_recovery_command(args.job_id)
        print("\n💡 Per eseguire il recupero:")
        print("1. Copia il comando SQL sopra")
        print("2. Accedi al database di produzione:")
        print("   render psql ocr-volantino-db")
        print("3. Incolla ed esegui il comando SQL")
        return
    
    # Tenta il recupero tramite API
    success = recover_job_via_api(args.job_id, args.base_url)
    
    if success:
        print("\n📝 Per completare il recupero, esegui il comando SQL generato:")
        generate_sql_recovery_command(args.job_id)
        
        if args.monitor:
            print("\n" + "="*50)
            monitor_job_progress(args.job_id, args.base_url)
    else:
        print("❌ Recupero fallito")

if __name__ == "__main__":
    main()