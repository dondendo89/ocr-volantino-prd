import sqlite3

def check_job():
    conn = sqlite3.connect('ocr_volantino.db')
    cursor = conn.cursor()
    
    job_id = 'c78ebdc8-dc21-4f77-a92e-98916c032cb0'
    
    # Controlla il job
    cursor.execute('SELECT * FROM processing_jobs WHERE id = ?', (job_id,))
    job = cursor.fetchone()
    print(f"Job trovato: {job is not None}")
    if job:
        print(f"Job details: {job}")
    
    # Controlla i prodotti
    cursor.execute('SELECT * FROM extracted_products WHERE job_id = ?', (job_id,))
    products = cursor.fetchall()
    print(f"Prodotti trovati: {len(products)}")
    
    if products:
        print("\nDettagli prodotti:")
        for i, product in enumerate(products, 1):
            print(f"Prodotto {i}: {product}")
    else:
        print("Nessun prodotto trovato nel database per questo job_id")
    
    # Controlla se ci sono directory di processing temporanee
    import os
    temp_dir = f"temp_processing_{job_id}"
    if os.path.exists(temp_dir):
        print(f"\nDirectory temporanea trovata: {temp_dir}")
        files = os.listdir(temp_dir)
        print(f"File nella directory: {files}")
    else:
        print(f"\nDirectory temporanea non trovata: {temp_dir}")
    
    conn.close()

if __name__ == "__main__":
    check_job()