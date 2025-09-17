#!/usr/bin/env python3
"""
Script per il recupero automatico dei job bloccati a causa di errori SSL
Può essere eseguito manualmente o schedulato come cron job
"""

import sys
import os
import time
from datetime import datetime, timedelta
from database import db_manager

def check_and_recover_stuck_jobs(max_age_minutes=30, dry_run=False):
    """
    Controlla e recupera job bloccati
    
    Args:
        max_age_minutes: Età massima in minuti per considerare un job bloccato
        dry_run: Se True, mostra solo cosa farebbe senza eseguire modifiche
    """
    print(f"🔍 Controllo job bloccati (età > {max_age_minutes} minuti)...")
    print(f"📅 Timestamp controllo: {datetime.utcnow().isoformat()}")
    
    if dry_run:
        print("🧪 MODALITÀ DRY RUN - Nessuna modifica verrà effettuata")
    
    try:
        # Trova job bloccati
        session = db_manager.get_session()
        cutoff_time = datetime.utcnow() - timedelta(minutes=max_age_minutes)
        
        from database import ProcessingJob
        stuck_jobs = session.query(ProcessingJob).filter(
            ProcessingJob.status == 'processing',
            ProcessingJob.started_at < cutoff_time,
            ProcessingJob.progress.between(40, 60)  # Job bloccati intorno al 50%
        ).all()
        
        session.close()
        
        if not stuck_jobs:
            print("✅ Nessun job bloccato trovato")
            return []
        
        print(f"⚠️ Trovati {len(stuck_jobs)} job bloccati:")
        
        recovered_jobs = []
        
        for job in stuck_jobs:
            age_minutes = (datetime.utcnow() - job.started_at).total_seconds() / 60
            print(f"  📋 Job {job.id}:")
            print(f"     - Stato: {job.status}")
            print(f"     - Progresso: {job.progress}%")
            print(f"     - Messaggio: {job.message}")
            print(f"     - Avviato: {job.started_at}")
            print(f"     - Età: {age_minutes:.1f} minuti")
            print(f"     - File: {job.filename}")
            
            if not dry_run:
                # Tenta il recupero
                success = db_manager.mark_job_for_retry(
                    job.id, 
                    f"SSL error recovery - bloccato per {age_minutes:.1f} minuti"
                )
                
                if success:
                    recovered_jobs.append(job.id)
                    print(f"     ✅ Job riavviato con successo")
                else:
                    print(f"     ❌ Errore nel riavvio del job")
            else:
                print(f"     🧪 [DRY RUN] Job verrebbe riavviato")
                recovered_jobs.append(job.id)
            
            print()
        
        if not dry_run:
            print(f"🔄 Recuperati {len(recovered_jobs)} job su {len(stuck_jobs)}")
        else:
            print(f"🧪 [DRY RUN] Verrebbero recuperati {len(recovered_jobs)} job su {len(stuck_jobs)}")
        
        return recovered_jobs
        
    except Exception as e:
        print(f"❌ Errore durante il controllo: {e}")
        import traceback
        traceback.print_exc()
        return []

def recover_specific_job(job_id, reason="Manual recovery"):
    """
    Recupera un job specifico
    """
    print(f"🔄 Tentativo di recupero job specifico: {job_id}")
    print(f"📝 Motivo: {reason}")
    
    try:
        # Controlla lo stato attuale del job
        job = db_manager.get_job(job_id)
        if not job:
            print(f"❌ Job {job_id} non trovato")
            return False
        
        print(f"📋 Stato attuale del job:")
        print(f"   - Stato: {job.status}")
        print(f"   - Progresso: {job.progress}%")
        print(f"   - Messaggio: {job.message}")
        print(f"   - Avviato: {job.started_at}")
        
        if job.status not in ['processing', 'failed']:
            print(f"⚠️ Job non è in stato processing o failed (stato: {job.status})")
            return False
        
        # Esegui il recupero
        success = db_manager.mark_job_for_retry(job_id, reason)
        
        if success:
            print(f"✅ Job {job_id} recuperato con successo")
            return True
        else:
            print(f"❌ Errore nel recupero del job {job_id}")
            return False
            
    except Exception as e:
        print(f"❌ Errore durante il recupero: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Funzione principale dello script"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Recupero automatico job bloccati SSL')
    parser.add_argument('--max-age', type=int, default=30, 
                       help='Età massima in minuti per considerare un job bloccato (default: 30)')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Modalità dry run - mostra cosa farebbe senza modificare')
    parser.add_argument('--job-id', type=str, 
                       help='Recupera un job specifico per ID')
    parser.add_argument('--reason', type=str, default='Manual recovery',
                       help='Motivo del recupero (per job specifico)')
    parser.add_argument('--continuous', action='store_true',
                       help='Esecuzione continua ogni 5 minuti')
    
    args = parser.parse_args()
    
    print("🚀 SSL Job Recovery Script")
    print("=" * 50)
    
    if args.job_id:
        # Recupero di un job specifico
        recover_specific_job(args.job_id, args.reason)
    elif args.continuous:
        # Esecuzione continua
        print(f"🔄 Modalità continua attivata (controllo ogni 5 minuti)")
        print(f"⏹️ Premi Ctrl+C per fermare")
        
        try:
            while True:
                print(f"\n{'='*50}")
                print(f"🕐 Controllo alle {datetime.now().strftime('%H:%M:%S')}")
                check_and_recover_stuck_jobs(args.max_age, args.dry_run)
                print(f"⏳ Attesa 5 minuti prima del prossimo controllo...")
                time.sleep(300)  # 5 minuti
        except KeyboardInterrupt:
            print(f"\n⏹️ Script interrotto dall'utente")
    else:
        # Esecuzione singola
        check_and_recover_stuck_jobs(args.max_age, args.dry_run)

if __name__ == "__main__":
    main()