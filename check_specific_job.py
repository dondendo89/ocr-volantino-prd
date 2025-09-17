#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script per controllare un job specifico nel database
"""

import sqlite3
import os
from datetime import datetime

def check_specific_job(job_id):
    """
    Controlla un job specifico nel database
    """
    db_path = "ocr_volantino.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database non trovato: {db_path}")
        return
    
    try:
        # Connessione al database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"🔍 Dettagli Job ID: {job_id}")
        print("=" * 60)
        
        # Trova il job
        cursor.execute("""
            SELECT id, filename, supermercato_nome, status, progress, message, 
                   created_at, started_at, completed_at, processing_time, total_products
            FROM processing_jobs 
            WHERE id = ? OR id LIKE ?
        """, (job_id, f"{job_id}%"))
        
        job = cursor.fetchone()
        
        if not job:
            print(f"❌ Job non trovato: {job_id}")
            return
        
        job_id_full, filename, supermercato_nome, status, progress, message, created_at, started_at, completed_at, processing_time, total_products = job
        
        print(f"📋 Job ID completo: {job_id_full}")
        print(f"📄 Filename: {filename}")
        print(f"🏪 Supermercato: {supermercato_nome}")
        print(f"📊 Status: {status}")
        print(f"📈 Progress: {progress}%")
        print(f"💬 Message: {message}")
        print(f"🕐 Created: {created_at}")
        print(f"▶️ Started: {started_at}")
        print(f"✅ Completed: {completed_at}")
        print(f"⏱️ Processing time: {processing_time}s" if processing_time else "⏱️ Processing time: N/A")
        print(f"🛍️ Total products: {total_products}")
        
        # Controlla i prodotti per questo job
        cursor.execute("""
            SELECT COUNT(*) FROM extracted_products WHERE job_id = ?
        """, (job_id_full,))
        
        actual_products = cursor.fetchone()[0]
        print(f"🔍 Prodotti effettivamente salvati: {actual_products}")
        
        if actual_products > 0:
            print("\n📦 Prodotti trovati:")
            cursor.execute("""
                SELECT nome, prezzo, marca, categoria, extracted_at
                FROM extracted_products 
                WHERE job_id = ?
                LIMIT 10
            """, (job_id_full,))
            
            products = cursor.fetchall()
            for nome, prezzo, marca, categoria, extracted_at in products:
                print(f"   - {nome} (€{prezzo}) - {marca or 'N/A'} - {categoria or 'N/A'} - {extracted_at}")
        
        # Controlla se ci sono altri job simili per questo supermercato
        print(f"\n🏪 Altri job per supermercato '{supermercato_nome}':")
        cursor.execute("""
            SELECT id, filename, status, total_products, completed_at
            FROM processing_jobs 
            WHERE supermercato_nome = ? AND id != ?
            ORDER BY created_at DESC
            LIMIT 5
        """, (supermercato_nome, job_id_full))
        
        other_jobs = cursor.fetchall()
        for other_id, other_filename, other_status, other_total, other_completed in other_jobs:
            print(f"   - {other_id[:8]}... | {other_filename} | {other_status} | {other_total} prodotti | {other_completed}")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ Errore database: {e}")
    except Exception as e:
        print(f"❌ Errore: {e}")

if __name__ == "__main__":
    # Cerca per il job ID parziale
    job_id = "c74898e6"
    check_specific_job(job_id)