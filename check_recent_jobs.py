#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script per controllare i job più recenti nel database
"""

import sqlite3
import os
from datetime import datetime

def check_recent_jobs():
    """
    Controlla i job più recenti nel database
    """
    db_path = "ocr_volantino.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database non trovato: {db_path}")
        return
    
    try:
        # Connessione al database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🕒 Ultimi 10 job nel database:")
        print("=" * 80)
        
        # Ultimi job
        cursor.execute("""
            SELECT id, filename, supermercato_nome, status, progress, message, 
                   created_at, completed_at, total_products
            FROM processing_jobs 
            ORDER BY created_at DESC
            LIMIT 10
        """)
        
        jobs = cursor.fetchall()
        
        if not jobs:
            print("❌ Nessun job trovato nel database")
            return
        
        for job in jobs:
            job_id, filename, supermercato_nome, status, progress, message, created_at, completed_at, total_products = job
            
            print(f"🆔 ID: {job_id}")
            print(f"📄 File: {filename}")
            print(f"🏪 Supermercato: {supermercato_nome}")
            print(f"📊 Status: {status} ({progress}%)")
            print(f"💬 Message: {message}")
            print(f"🕐 Created: {created_at}")
            print(f"✅ Completed: {completed_at}")
            print(f"🛍️ Products: {total_products}")
            print("-" * 80)
        
        # Controlla se ci sono job con ID simile a c74898e6
        print("\n🔍 Ricerca job con ID simile a 'c74898e6':")
        cursor.execute("""
            SELECT id, filename, supermercato_nome, status, message, created_at
            FROM processing_jobs 
            WHERE id LIKE 'c74898e6%'
            ORDER BY created_at DESC
        """)
        
        similar_jobs = cursor.fetchall()
        
        if similar_jobs:
            for job in similar_jobs:
                job_id, filename, supermercato_nome, status, message, created_at = job
                print(f"   ✅ Trovato: {job_id} | {filename} | {supermercato_nome} | {status} | {created_at}")
        else:
            print("   ❌ Nessun job trovato con ID simile")
        
        conn.close()
        
    except sqlite3.Error as e:
        print(f"❌ Errore database: {e}")
    except Exception as e:
        print(f"❌ Errore: {e}")

if __name__ == "__main__":
    check_recent_jobs()