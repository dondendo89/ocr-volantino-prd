#!/usr/bin/env python3
"""
Script per verificare e correggere i problemi di foreign key constraint
tra processing_jobs e supermercati nel database PostgreSQL.
"""

import os
import sys
sys.path.append('.')

from database import db_manager, ProcessingJob, Supermercato
from sqlalchemy import text
from datetime import datetime

def get_db_session():
    """Ottiene sessione del database"""
    return db_manager.get_session()

def check_orphaned_jobs():
    """Verifica se ci sono job orfani senza supermercato valido"""
    session = get_db_session()
    try:
        # Trova job senza supermercato_id valido
        result = session.execute(text("""
            SELECT pj.id, pj.filename, pj.supermercato_nome, pj.supermercato_id
            FROM processing_jobs pj
            LEFT JOIN supermercati s ON pj.supermercato_id = s.id
            WHERE s.id IS NULL
            ORDER BY pj.created_at DESC
            LIMIT 20
        """))
        
        orphaned_jobs = result.fetchall()
        
        if orphaned_jobs:
            print(f"🚨 Trovati {len(orphaned_jobs)} job orfani:")
            for job in orphaned_jobs:
                print(f"   - Job {job.id}: {job.filename} (supermercato: {job.supermercato_nome}, id: {job.supermercato_id})")
            return orphaned_jobs
        else:
            print("✅ Nessun job orfano trovato")
            return []
            
    finally:
        session.close()

def fix_orphaned_jobs():
    """Corregge i job orfani creando i supermercati mancanti"""
    session = get_db_session()
    try:
        # Trova job orfani
        result = session.execute(text("""
            SELECT DISTINCT pj.supermercato_nome
            FROM processing_jobs pj
            LEFT JOIN supermercati s ON pj.supermercato_id = s.id
            WHERE s.id IS NULL AND pj.supermercato_nome IS NOT NULL
        """))
        
        missing_supermarkets = result.fetchall()
        
        for row in missing_supermarkets:
            supermercato_nome = row.supermercato_nome
            print(f"🔧 Creando supermercato mancante: {supermercato_nome}")
            
            # Crea il supermercato usando SQLAlchemy ORM
            supermercato = Supermercato(
                nome=supermercato_nome,
                descrizione=f"Supermercato {supermercato_nome}",
                colore_tema="#3498db",
                attivo="true"
            )
            session.add(supermercato)
            session.flush()  # Per ottenere l'ID
            
            supermercato_id = supermercato.id
            print(f"   ✅ Creato supermercato {supermercato_nome} con ID {supermercato_id}")
            
            # Aggiorna i job orfani
            result = session.execute(text("""
                UPDATE processing_jobs 
                SET supermercato_id = :supermercato_id 
                WHERE supermercato_nome = :supermercato_nome AND supermercato_id IS NULL
            """), {
                'supermercato_id': supermercato_id,
                'supermercato_nome': supermercato_nome
            })
            
            updated_count = result.rowcount
            print(f"   ✅ Aggiornati {updated_count} job per {supermercato_nome}")
        
        session.commit()
        print("✅ Correzione completata")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Errore durante la correzione: {e}")
        raise
    finally:
        session.close()

def check_database_integrity():
    """Verifica l'integrità del database"""
    session = get_db_session()
    try:
        # Conta totali
        result = session.execute(text("SELECT COUNT(*) as count FROM processing_jobs"))
        total_jobs = result.fetchone().count
        
        result = session.execute(text("SELECT COUNT(*) as count FROM supermercati"))
        total_supermarkets = result.fetchone().count
        
        result = session.execute(text("SELECT COUNT(*) as count FROM extracted_products"))
        total_products = result.fetchone().count
        
        print(f"📊 Statistiche database:")
        print(f"   - Job totali: {total_jobs}")
        print(f"   - Supermercati: {total_supermarkets}")
        print(f"   - Prodotti estratti: {total_products}")
        
        # Verifica foreign keys
        result = session.execute(text("""
            SELECT COUNT(*) as count
            FROM processing_jobs pj
            JOIN supermercati s ON pj.supermercato_id = s.id
        """))
        valid_jobs = result.fetchone().count
        
        print(f"   - Job con foreign key valida: {valid_jobs}")
        
        if valid_jobs != total_jobs:
            print(f"⚠️  {total_jobs - valid_jobs} job hanno foreign key non valida")
        else:
            print("✅ Tutte le foreign key sono valide")
            
    finally:
        session.close()

def main():
    """Funzione principale"""
    print("🔍 Verifica integrità database...")
    
    try:
        # Verifica stato attuale
        check_database_integrity()
        print()
        
        # Cerca job orfani
        orphaned_jobs = check_orphaned_jobs()
        print()
        
        if orphaned_jobs:
            print("🔧 Correzione job orfani...")
            fix_orphaned_jobs()
            print()
            
            # Verifica dopo la correzione
            print("🔍 Verifica post-correzione...")
            check_database_integrity()
            check_orphaned_jobs()
        
        print("✅ Verifica completata")
        
    except Exception as e:
        print(f"❌ Errore: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())