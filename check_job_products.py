#!/usr/bin/env python3
"""
Script per verificare i prodotti di un job specifico nel database
"""

import sqlite3
import sys

def check_job_products(job_id):
    """Verifica i prodotti di un job specifico"""
    try:
        conn = sqlite3.connect('ocr_volantino.db')
        cursor = conn.cursor()
        
        # Verifica se il job esiste
        cursor.execute('SELECT * FROM processing_jobs WHERE id = ?', (job_id,))
        job = cursor.fetchone()
        
        if not job:
            print(f"❌ Job {job_id} non trovato")
            return
        
        print(f"✅ Job trovato: {job}")
        
        # Verifica i prodotti del job
        cursor.execute('SELECT id, nome, image_url, image_path FROM extracted_products WHERE job_id = ?', (job_id,))
        products = cursor.fetchall()
        
        print(f"\n📦 Prodotti trovati per job {job_id}: {len(products)}")
        
        for product in products:
            print(f"  ID: {product[0]}, Nome: {product[1]}, Image URL: {product[2]}, Image Path: {product[3]}")
        
        # Verifica tutti i prodotti nel database
        cursor.execute('SELECT COUNT(*) FROM extracted_products')
        total_products = cursor.fetchone()[0]
        print(f"\n📊 Totale prodotti nel database: {total_products}")
        
        # Mostra tutti i job_id presenti
        cursor.execute('SELECT DISTINCT job_id FROM extracted_products')
        job_ids = cursor.fetchall()
        print(f"\n🔍 Job IDs con prodotti nel database:")
        for jid in job_ids:
            print(f"  - {jid[0]}")
        
    except Exception as e:
        print(f"❌ Errore: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python3 check_job_products.py <job_id>")
        sys.exit(1)
    
    job_id = sys.argv[1]
    check_job_products(job_id)