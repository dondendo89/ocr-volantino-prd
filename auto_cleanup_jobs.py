#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sistema di cleanup automatico per job orfani bloccati
Può essere eseguito come cron job ogni 5-10 minuti
"""

import os
import sys
import time
import logging
from datetime import datetime, timedelta

# Aggiungi il percorso corrente al PYTHONPATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import db_manager
from fix_stuck_jobs import find_stuck_jobs, fix_stuck_job

# Configurazione logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('auto_cleanup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class AutoCleanupManager:
    def __init__(self, timeout_minutes=10, max_retries=3):
        """
        Inizializza il manager di cleanup automatico
        
        Args:
            timeout_minutes: Minuti dopo i quali un job è considerato bloccato
            max_retries: Numero massimo di tentativi prima di marcare come fallito
        """
        self.timeout_minutes = timeout_minutes
        self.max_retries = max_retries
        
    def cleanup_stuck_jobs(self):
        """
        Esegue il cleanup dei job bloccati
        """
        try:
            logger.info("🧹 Avvio cleanup automatico job bloccati...")
            
            # Trova job bloccati
            stuck_jobs = find_stuck_jobs(timeout_minutes=self.timeout_minutes)
            
            if not stuck_jobs:
                logger.info("✅ Nessun job bloccato trovato")
                return {"cleaned": 0, "errors": 0}
            
            cleaned_count = 0
            error_count = 0
            
            for job in stuck_jobs:
                job_id, filename, supermercato, status, progress, message, started_at, created_at = job
                
                try:
                    # Calcola da quanto tempo è bloccato
                    if started_at:
                        stuck_duration = datetime.now() - started_at
                    else:
                        stuck_duration = datetime.now() - created_at
                    
                    logger.info(f"🔧 Fixing job {job_id} ({filename}) bloccato da {stuck_duration}")
                    
                    # Determina il motivo del fallimento
                    reason = f"Job automaticamente marcato come fallito dopo {stuck_duration} di blocco"
                    
                    # Fixa il job
                    success = fix_stuck_job(job_id, reason)
                    
                    if success:
                        cleaned_count += 1
                        logger.info(f"✅ Job {job_id} risolto con successo")
                    else:
                        error_count += 1
                        logger.error(f"❌ Errore nel risolvere job {job_id}")
                        
                except Exception as e:
                    error_count += 1
                    logger.error(f"❌ Errore nel processare job {job_id}: {str(e)}")
            
            logger.info(f"🧹 Cleanup completato: {cleaned_count} job risolti, {error_count} errori")
            return {"cleaned": cleaned_count, "errors": error_count}
            
        except Exception as e:
            logger.error(f"❌ Errore durante il cleanup: {str(e)}")
            return {"cleaned": 0, "errors": 1}
    
    def cleanup_old_temp_directories(self):
        """
        Pulisce le directory temporanee vecchie
        """
        try:
            logger.info("🗂️ Pulizia directory temporanee...")
            
            current_dir = os.path.dirname(os.path.abspath(__file__))
            cleaned_dirs = 0
            
            # Cerca directory temp_processing_*
            for item in os.listdir(current_dir):
                if item.startswith("temp_processing_") and os.path.isdir(os.path.join(current_dir, item)):
                    dir_path = os.path.join(current_dir, item)
                    
                    # Controlla se la directory è più vecchia di 1 ora
                    dir_mtime = datetime.fromtimestamp(os.path.getmtime(dir_path))
                    if datetime.now() - dir_mtime > timedelta(hours=1):
                        try:
                            import shutil
                            shutil.rmtree(dir_path)
                            cleaned_dirs += 1
                            logger.info(f"🗑️ Rimossa directory temporanea: {item}")
                        except Exception as e:
                            logger.error(f"❌ Errore nel rimuovere {item}: {str(e)}")
            
            logger.info(f"🗂️ Pulizia directory completata: {cleaned_dirs} directory rimosse")
            return cleaned_dirs
            
        except Exception as e:
            logger.error(f"❌ Errore durante pulizia directory: {str(e)}")
            return 0
    
    def run_full_cleanup(self):
        """
        Esegue un cleanup completo
        """
        logger.info("🚀 Avvio cleanup completo...")
        
        # Cleanup job bloccati
        job_results = self.cleanup_stuck_jobs()
        
        # Cleanup directory temporanee
        dir_count = self.cleanup_old_temp_directories()
        
        # Risultato finale
        total_cleaned = job_results["cleaned"] + dir_count
        total_errors = job_results["errors"]
        
        logger.info(f"✅ Cleanup completo terminato: {total_cleaned} elementi puliti, {total_errors} errori")
        
        return {
            "jobs_cleaned": job_results["cleaned"],
            "jobs_errors": job_results["errors"],
            "dirs_cleaned": dir_count,
            "total_cleaned": total_cleaned,
            "total_errors": total_errors
        }

def main():
    """
    Funzione principale per esecuzione da cron
    """
    try:
        # Crea il manager di cleanup
        cleanup_manager = AutoCleanupManager(timeout_minutes=10)
        
        # Esegui cleanup completo
        results = cleanup_manager.run_full_cleanup()
        
        # Log risultati finali
        if results["total_errors"] == 0:
            logger.info("🎉 Cleanup automatico completato con successo!")
        else:
            logger.warning(f"⚠️ Cleanup completato con {results['total_errors']} errori")
        
        return results["total_errors"] == 0
        
    except Exception as e:
        logger.error(f"💥 Errore critico durante cleanup automatico: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)