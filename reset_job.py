#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script per resettare manualmente un job specifico
"""

import os
import sys
from datetime import datetime
import logging

# Aggiungi il percorso corrente al PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import db_manager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def reset_job(job_id, new_status='failed', reason="Job resettato manualmente"):
    """
    Resetta un job specifico cambiando il suo status
    """
    try:
        session = db_manager.get_session()
        
        from database import ProcessingJob
        
        # Trova il job
        job = session.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        
        if not job:
            logger.error(f"❌ Job {job_id} non trovato")
            return False
            
        logger.info(f"📋 Job trovato: {job.filename} - Status: {job.status} - Progress: {job.progress}%")
        
        # Aggiorna il job
        old_status = job.status
        job.status = new_status
        job.message = reason
        job.completed_at = datetime.now()
        
        session.commit()
        session.close()
        
        logger.info(f"✅ Job {job_id} aggiornato da '{old_status}' a '{new_status}'")
        return True
        
    except Exception as e:
        logger.error(f"❌ Errore durante il reset del job: {e}")
        if 'session' in locals():
            session.rollback()
            session.close()
        return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Reset di un job specifico')
    parser.add_argument('job_id', help='ID del job da resettare')
    parser.add_argument('--status', default='failed', choices=['failed', 'pending'], 
                       help='Nuovo status del job (default: failed)')
    parser.add_argument('--reason', default='Job resettato manualmente', 
                       help='Motivo del reset')
    
    args = parser.parse_args()
    
    logger.info(f"🔄 Resetting job {args.job_id} to status '{args.status}'...")
    
    success = reset_job(args.job_id, args.status, args.reason)
    
    if success:
        logger.info("✅ Reset completato con successo")
    else:
        logger.error("❌ Reset fallito")
        sys.exit(1)

if __name__ == "__main__":
    main()