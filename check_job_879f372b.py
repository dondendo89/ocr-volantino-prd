import sqlite3
import os

def check_job():
    conn = sqlite3.connect('ocr_volantino.db')
    cursor = conn.cursor()
    
    job_id = '879f372b-3de4-4941-928d-ce8333ad6a85'
    
    # Controlla il job
    cursor.execute('SELECT * FROM processing_jobs WHERE id = ?', (job_id,))
    job = cursor.fetchone()
    print(f"Job trovato: {job is not None}")
    if job:
        print(f"Job details: {job}")
    
    # Controlla i prodotti
    cursor.execute('SELECT * FROM extracted_products WHERE job_id = ?', (job_id,))
    products = cursor.fetchall()
    print(f"Prodotti trovati nel database: {len(products)}")
    
    if products:
        print("\nDettagli prodotti:")
        for i, product in enumerate(products, 1):
            print(f"Prodotto {i}: {product}")
    
    # Controlla directory temporanea
    temp_dir = f"temp_processing_{job_id}"
    if os.path.exists(temp_dir):
        print(f"\nDirectory temporanea: {temp_dir}")
        files = os.listdir(temp_dir)
        print(f"File nella directory: {files}")
    
    # Controlla immagini prodotti
    images_dir = f"simplified_gemini_product_images"
    if os.path.exists(images_dir):
        job_images = [f for f in os.listdir(images_dir) if job_id in f]
        print(f"\nImmagini prodotti trovate: {len(job_images)}")
        for img in job_images:
            print(f"  - {img}")
    
    conn.close()

if __name__ == "__main__":
    check_job()