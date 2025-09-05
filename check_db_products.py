#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script per controllare il numero di prodotti nel database
"""

import sqlite3
import os
from datetime import datetime

def check_database_products():
    """
    Controlla il numero di prodotti nel database
    """
    db_path = "ocr_volantino.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database non trovato: {db_path}")
        return
    
    try:
        # Connessione al database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("📊 Statistiche Database OCR Volantino")
        print("=" * 40)
        
        # Conta prodotti totali
        cursor.execute("SELECT COUNT(*) FROM extracted_products")
        total_products = cursor.fetchone()[0]
        print(f"🛍️ Prodotti totali: {total_products}")
        
        # Conta prodotti per supermercato
        cursor.execute("""
            SELECT s.nome, COUNT(ep.id) as count
            FROM supermercati s
            LEFT JOIN processing_jobs pj ON s.id = pj.supermercato_id
            LEFT JOIN extracted_products ep ON pj.id = ep.job_id
            GROUP BY s.id, s.nome
            ORDER BY count DESC
        """)
        
        supermercati_stats = cursor.fetchall()
        if supermercati_stats:
            print("\n🏪 Prodotti per supermercato:")
            for nome, count in supermercati_stats:
                print(f"   - {nome}: {count} prodotti")
        
        # Ultimi prodotti aggiunti
        cursor.execute("""
            SELECT nome, prezzo, extracted_at
            FROM extracted_products
            ORDER BY extracted_at DESC
            LIMIT 5
        """)
        
        recent_products = cursor.fetchall()
        if recent_products:
            print("\n🕒 Ultimi 5 prodotti aggiunti:")
            for nome, prezzo, extracted_at in recent_products:
                print(f"   - {nome} (€{prezzo}) - {extracted_at}")
        
        # Statistiche processing jobs
        cursor.execute("SELECT COUNT(*) FROM processing_jobs")
        total_jobs = cursor.fetchone()[0]
        print(f"\n📋 Job di elaborazione totali: {total_jobs}")
        
        # Jobs per stato
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM processing_jobs
            GROUP BY status
        """)
        
        job_stats = cursor.fetchall()
        if job_stats:
            print("\n📈 Job per stato:")
            for status, count in job_stats:
                print(f"   - {status}: {count}")
        
        # Statistiche supermercati
        cursor.execute("SELECT COUNT(*) FROM supermercati")
        total_supermarkets = cursor.fetchone()[0]
        print(f"\n🏬 Supermercati registrati: {total_supermarkets}")
        
        if total_supermarkets > 0:
            cursor.execute("SELECT nome, descrizione FROM supermercati")
            supermarkets = cursor.fetchall()
            print("\n📝 Lista supermercati:")
            for nome, descrizione in supermarkets:
                desc = descrizione[:50] + "..." if descrizione and len(descrizione) > 50 else descrizione or "N/A"
                print(f"   - {nome}: {desc}")
        
        conn.close()
        
        print("\n" + "=" * 40)
        print(f"✅ Controllo completato - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except sqlite3.Error as e:
        print(f"❌ Errore database: {e}")
    except Exception as e:
        print(f"❌ Errore: {e}")

if __name__ == "__main__":
    check_database_products()