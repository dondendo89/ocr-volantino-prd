#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script per identificare e correggere job bloccati
Identifica job in stato 'processing' da più di 15 minuti e li marca come falliti
"""

import os
import sys
from datetime import datetime, timedelta
import logging

# Aggiungi il percorso corrente al PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import db_manager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def find_stuck_jobs(timeout_minutes=15):
    """
    Trova job bloccati in stato 'processing' da più di timeout_minutes
    """
    try:
        # Calcola il timestamp limite (15 minuti fa)
        cutoff_time = datetime.now() - timedelta(minutes=timeout_minutes)
        
        # Query per trovare job bloccati usando SQLAlchemy
        session = db_manager.get_session()
        
        from database import ProcessingJob
        
        stuck_jobs_query = session.query(ProcessingJob).filter(
            ProcessingJob.status == 'processing'
        ).filter(
            (ProcessingJob.started_at < cutoff_time) | 
            ((ProcessingJob.started_at == None) & (ProcessingJob.created_at < cutoff_time))
        ).order_by(ProcessingJob.created_at.desc())
        
        stuck_jobs_objects = stuck_jobs_query.all()
        
        # Converti in tuple per compatibilità
        stuck_jobs = []
        for job in stuck_jobs_objects:
            stuck_jobs.append((
                job.id, job.filename, job.supermercato_nome, 
                job.status, job.progress, job.message,
                job.started_at, job.created_at
            ))
        
        session.close()
                
        return stuck_jobs
        
    except Exception as e:
        logger.error(f"Errore durante la ricerca job bloccati: {e}")
        return []

def fix_stuck_job(job_id, reason="Job bloccato per più di 15 minuti"):
    """
    Marca un job come fallito
    """
    try:
        db_manager.update_job_status(
            job_id=job_id,
            status="failed",
            progress=100,
            message=f"❌ {reason}",
            processing_time=None
        )
        logger.info(f"✅ Job {job_id} marcato come fallito")
        return True
        
    except Exception as e:
        logger.error(f"❌ Errore durante il fix del job {job_id}: {e}")
        return False

def main():
    """
    Funzione principale
    """
    logger.info("🔍 Ricerca job bloccati...")
    
    stuck_jobs = find_stuck_jobs(timeout_minutes=15)
    
    if not stuck_jobs:
        logger.info("✅ Nessun job bloccato trovato")
        return
    
    logger.info(f"⚠️ Trovati {len(stuck_jobs)} job bloccati:")
    
    for job in stuck_jobs:
        job_id, filename, supermercato, status, progress, message, started_at, created_at = job
        
        logger.info(f"📋 Job ID: {job_id}")
        logger.info(f"   📄 File: {filename}")
        logger.info(f"   🏪 Supermercato: {supermercato}")
        logger.info(f"   📊 Progresso: {progress}%")
        logger.info(f"   💬 Messaggio: {message}")
        logger.info(f"   🕐 Creato: {created_at}")
        logger.info(f"   🚀 Avviato: {started_at}")
        
        # Calcola da quanto tempo è bloccato
        if started_at:
            time_stuck = datetime.now() - started_at
        else:
            time_stuck = datetime.now() - created_at
            
        logger.info(f"   ⏰ Bloccato da: {time_stuck}")
        
        # Chiedi conferma per il fix
        response = input(f"\n🔧 Vuoi marcare il job {job_id} come fallito? (y/N): ")
        
        if response.lower() in ['y', 'yes', 's', 'si']:
            if fix_stuck_job(job_id, f"Job bloccato da {time_stuck}"):
                logger.info(f"✅ Job {job_id} corretto con successo")
            else:
                logger.error(f"❌ Errore durante la correzione del job {job_id}")
        else:
            logger.info(f"⏭️ Job {job_id} saltato")
        
        print("-" * 50)
    
    logger.info("🏁 Controllo completato")

if __name__ == "__main__":
    main()