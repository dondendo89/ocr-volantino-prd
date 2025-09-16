import sqlite3
from datetime import datetime

def check_all_jobs():
    conn = sqlite3.connect('ocr_volantino.db')
    cursor = conn.cursor()
    
    # Controlla tutti i job
    cursor.execute('SELECT id, status, created_at FROM processing_jobs ORDER BY created_at DESC LIMIT 10')
    jobs = cursor.fetchall()
    
    print(f"Totale job nel database locale: {len(jobs)}")
    print("\nUltimi 10 job:")
    for job in jobs:
        print(f"ID: {job[0]}, Status: {job[1]}, Created: {job[2]}")
    
    # Controlla il totale dei prodotti
    cursor.execute('SELECT COUNT(*) FROM extracted_products')
    total_products = cursor.fetchone()[0]
    print(f"\nTotale prodotti nel database: {total_products}")
    
    # Controlla i job con prodotti
    cursor.execute('''
        SELECT j.id, j.status, COUNT(p.id) as product_count 
        FROM processing_jobs j 
        LEFT JOIN extracted_products p ON j.id = p.job_id 
        GROUP BY j.id, j.status 
        ORDER BY j.created_at DESC
    ''')
    jobs_with_products = cursor.fetchall()
    
    print("\nJob con conteggio prodotti:")
    for job in jobs_with_products:
        print(f"Job {job[0]}: Status {job[1]}, Prodotti: {job[2]}")
    
    conn.close()

if __name__ == "__main__":
    check_all_jobs()