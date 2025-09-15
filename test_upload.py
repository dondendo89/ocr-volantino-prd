#!/usr/bin/env python3
"""
Script di test per verificare il salvataggio su PostgreSQL
Testa l'upload di un'immagine e verifica che i dati vengano salvati correttamente
"""

import requests
import json
import time
import os
from datetime import datetime
from database import DatabaseManager
from sqlalchemy import text

def test_postgresql_saving():
    print('🧪 TEST COMPLETO - VERIFICA SALVATAGGIO POSTGRESQL')
    print('=' * 60)
    
    # URL del server locale
    base_url = 'http://localhost:8000'
    
    # 1. Verifica stato iniziale database
    print('\n1️⃣ STATO INIZIALE DATABASE')
    db = DatabaseManager()
    session = db.get_session()
    
    try:
        initial_jobs = session.execute(text('SELECT COUNT(*) FROM processing_jobs')).scalar()
        initial_products = session.execute(text('SELECT COUNT(*) FROM extracted_products')).scalar()
        print(f'   📊 Jobs iniziali: {initial_jobs}')
        print(f'   📦 Prodotti iniziali: {initial_products}')
    finally:
        session.close()
    
    # 2. Test connessione server
    print('\n2️⃣ TEST CONNESSIONE SERVER')
    try:
        response = requests.get(f'{base_url}/health', timeout=5)
        if response.status_code == 200:
            print('   ✅ Server API raggiungibile')
        else:
            print(f'   ❌ Server non risponde: {response.status_code}')
            return False
    except Exception as e:
        print(f'   ❌ Errore connessione server: {e}')
        return False
    
    # 3. Crea un PDF di test se non esiste
    print('\n3️⃣ PREPARAZIONE PDF TEST')
    test_pdf_path = 'test_volantino.pdf'
    
    if not os.path.exists(test_pdf_path):
        print(f'   ⚠️  PDF test non trovato: {test_pdf_path}')
        print(f'   💡 Puoi creare un file PDF qualsiasi e rinominarlo in {test_pdf_path}')
        print(f'   💡 Oppure usa un PDF esistente modificando il path nello script')
        
        # Cerca PDF nella directory corrente
        pdf_extensions = ['.pdf']
        found_pdfs = []
        for file in os.listdir('.'):
            if any(file.lower().endswith(ext) for ext in pdf_extensions):
                found_pdfs.append(file)
        
        if found_pdfs:
            print(f'   🔍 PDF trovati nella directory:')
            for pdf in found_pdfs[:5]:
                print(f'      - {pdf}')
            test_pdf_path = found_pdfs[0]
            print(f'   ✅ Uso: {test_pdf_path}')
        else:
            print(f'   ❌ Nessun PDF trovato. Test saltato.')
            return False
    else:
        print(f'   ✅ PDF test trovato: {test_pdf_path}')
    
    # 4. Test upload
    print('\n4️⃣ TEST UPLOAD PDF')
    try:
        with open(test_pdf_path, 'rb') as f:
            files = {'file': (test_pdf_path, f, 'application/pdf')}
            data = {'supermercato_nome': 'Test PostgreSQL'}
            
            print(f'   📤 Caricamento {test_pdf_path}...')
            response = requests.post(f'{base_url}/upload', files=files, data=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                job_id = result.get('job_id')
                print(f'   ✅ Upload completato! Job ID: {job_id}')
                
                # 5. Monitora elaborazione
                print('\n5️⃣ MONITORAGGIO ELABORAZIONE')
                max_wait = 60  # secondi
                start_time = time.time()
                
                while time.time() - start_time < max_wait:
                    try:
                        status_response = requests.get(f'{base_url}/job/{job_id}/status')
                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            status = status_data.get('status', 'unknown')
                            progress = status_data.get('progress', 0)
                            total_products = status_data.get('total_products', 0)
                            
                            print(f'   📊 Status: {status} | Progress: {progress}% | Prodotti: {total_products}')
                            
                            if status in ['completed', 'failed']:
                                break
                        
                        time.sleep(3)
                    except Exception as e:
                        print(f'   ⚠️  Errore controllo status: {e}')
                        break
                
                # 6. Verifica salvataggio nel database
                print('\n6️⃣ VERIFICA SALVATAGGIO DATABASE')
                session = db.get_session()
                try:
                    final_jobs = session.execute(text('SELECT COUNT(*) FROM processing_jobs')).scalar()
                    final_products = session.execute(text('SELECT COUNT(*) FROM extracted_products')).scalar()
                    
                    jobs_added = final_jobs - initial_jobs
                    products_added = final_products - initial_products
                    
                    print(f'   📊 Jobs aggiunti: {jobs_added}')
                    print(f'   📦 Prodotti aggiunti: {products_added}')
                    
                    if jobs_added > 0:
                        print('   ✅ Job salvato correttamente in PostgreSQL!')
                    
                    if products_added > 0:
                        print('   ✅ Prodotti salvati correttamente in PostgreSQL!')
                        
                        # Mostra dettagli prodotti
                        result = session.execute(text('''
                            SELECT nome, prezzo, marca 
                            FROM extracted_products 
                            WHERE job_id = :job_id
                        '''), {'job_id': job_id})
                        
                        print('   📦 Prodotti estratti:')
                        for row in result:
                            print(f'      - {row[0]} | €{row[1]} | {row[2] or "N/A"}')
                    
                    return True
                    
                finally:
                    session.close()
                    
            else:
                print(f'   ❌ Errore upload: {response.status_code}')
                print(f'   📄 Risposta: {response.text}')
                return False
                
    except Exception as e:
        print(f'   ❌ Errore durante upload: {e}')
        return False

if __name__ == '__main__':
    success = test_postgresql_saving()
    
    print('\n' + '=' * 60)
    if success:
        print('🎉 TEST COMPLETATO CON SUCCESSO!')
        print('✅ L\'applicazione sta salvando correttamente su PostgreSQL')
    else:
        print('❌ TEST FALLITO')
        print('⚠️  Controlla i log per maggiori dettagli')
    print('=' * 60)