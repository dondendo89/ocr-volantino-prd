# Guida al Servizio API OCR Volantino

## Panoramica
Il servizio API utilizza `SimplifiedGeminiExtractor` per l'estrazione automatica di prodotti da volantini PDF. Il servizio è ottimizzato per prestazioni e affidabilità.

## Endpoint Principali

### Configurazione Ambiente
Il servizio API supporta due ambienti:
- **Sviluppo**: `http://localhost:8000`
- **Produzione**: `https://ocr-volantino-api.onrender.com`

Tutti gli URL nelle risposte sono automaticamente adattati all'ambiente corrente.

### 1. Health Check
```bash
GET http://localhost:8000/health
```
Verifica lo stato del servizio.

### 2. Upload File PDF
```bash
POST http://localhost:8000/upload
Content-Type: multipart/form-data

Parametri:
- file: File PDF del volantino (max 10MB)
- supermercato_nome: Nome del supermercato
```

**Risposta:**
```json
{
  "success": true,
  "job_id": "uuid-del-job",
  "status": "processing",
  "check_status_url": "https://ocr-volantino-api.onrender.com/jobs/{job_id}",
  "results_url": "https://ocr-volantino-api.onrender.com/results/{job_id}",
  "products_url": "https://ocr-volantino-api.onrender.com/products/{job_id}",
  "environment": "production",
  "base_url": "https://ocr-volantino-api.onrender.com"
}
```

**Esempio con curl:**
```bash
curl -X POST "http://localhost:8000/upload" \
  -F "file=@volantino.pdf" \
  -F "supermercato_nome=CONAD"
```

### 3. Elaborazione da URL
```bash
POST http://localhost:8000/process-url
Content-Type: application/json

{
  "url": "https://example.com/volantino.pdf",
  "supermercato_nome": "CONAD",
  "job_name": "Volantino Gennaio 2024"
}
```

**Risposta:**
```json
{
  "success": true,
  "job_id": "uuid-del-job",
  "status": "processing",
  "check_status_url": "https://ocr-volantino-api.onrender.com/jobs/{job_id}",
  "results_url": "https://ocr-volantino-api.onrender.com/results/{job_id}",
  "products_url": "https://ocr-volantino-api.onrender.com/products/{job_id}",
  "environment": "production",
  "base_url": "https://ocr-volantino-api.onrender.com",
  "estimated_processing_time": "2-5 minuti"
}
```

**Esempio con curl:**
```bash
curl -X POST "http://localhost:8000/process-url" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/volantino.pdf",
    "supermercato_nome": "CONAD"
  }'
```

### 4. Stato del Job
```bash
GET http://localhost:8000/jobs/{job_id}
```
Restituisce lo stato di elaborazione del job.

### 5. Risultati dell'Elaborazione
```bash
GET http://localhost:8000/results/{job_id}
```
Restituisce i risultati completi dell'elaborazione.

### 6. Prodotti Estratti
```bash
GET http://localhost:8000/products/{job_id}
```
Restituisce solo i prodotti estratti per un job specifico.

### 7. Lista di Tutti i Job
```bash
GET http://localhost:8000/jobs?limit=50&offset=0
```
Restituisce la lista di tutti i job di elaborazione.

## Gestione Supermercati

### Creare un Supermercato
```bash
POST http://localhost:8000/supermercati
Content-Type: application/json

{
  "nome": "CONAD",
  "descrizione": "Supermercato CONAD",
  "logo_url": "https://example.com/logo.png",
  "sito_web": "https://www.conad.it",
  "colore_tema": "#ff6b35"
}
```

### Lista Supermercati
```bash
GET http://localhost:8000/supermercati
```

## Gestione Prodotti

### Aggiornare un Prodotto
```bash
PUT http://localhost:8000/products/{product_id}
Content-Type: application/json

{
  "nome": "Pasta Barilla",
  "prezzo": 1.29,
  "categoria": "Alimentari",
  "marca": "Barilla"
}
```

### Eliminare un Prodotto
```bash
DELETE http://localhost:8000/products/{product_id}
```

### Eliminare Tutti i Prodotti
```bash
DELETE http://localhost:8000/products/all
```

## Interfacce Web

### Interfaccia Utente
- **URL**: http://localhost:8000/static/index.html
- **Funzionalità**: Upload file, visualizzazione risultati

### Pannello Admin
- **URL**: http://localhost:8000/static/admin.html
- **Funzionalità**: Gestione completa di job, prodotti e supermercati

### Documentazione API
- **URL**: http://localhost:8000/docs
- **Funzionalità**: Documentazione interattiva Swagger

## Caratteristiche del SimplifiedGeminiExtractor

### Vantaggi
- ✅ **Affidabilità**: Riduce i timeout e gli errori
- ✅ **Efficienza**: Ottimizzato per l'uso dei token Gemini
- ✅ **Dual Token**: Supporta due chiavi API per maggiore throughput
- ✅ **Salvataggio Garantito**: I prodotti vengono sempre salvati nel database
- ✅ **Gestione Errori**: Recupero automatico da errori temporanei

### Configurazione
L'estrattore richiede:
- `GEMINI_API_KEY`: Chiave API principale
- `GEMINI_API_KEY_2`: Chiave API secondaria (opzionale)
- Database configurato (SQLite o PostgreSQL)

## Esempi di Risposta

### Risposta Upload Successful
```json
{
  "job_id": "abc123-def456",
  "status": "queued",
  "message": "File caricato con successo",
  "filename": "volantino.pdf",
  "supermercato_nome": "CONAD"
}
```

### Risposta Job Status
```json
{
  "job_id": "abc123-def456",
  "status": "completed",
  "supermercato_nome": "CONAD",
  "progress": 100,
  "message": "Elaborazione completata con successo",
  "created_at": "2024-01-15T10:30:00",
  "completed_at": "2024-01-15T10:35:00"
}
```

### Risposta Prodotti
```json
[
  {
    "id": 1,
    "nome": "Pasta Barilla",
    "prezzo": 1.29,
    "prezzo_originale": 1.49,
    "sconto_percentuale": 13.4,
    "quantita": "500g",
    "marca": "Barilla",
    "categoria": "Alimentari",
    "confidence_score": 0.95
  }
]
```

## Monitoraggio e Debug

### Log del Server
I log sono disponibili nel terminale dove è in esecuzione il server:
```bash
python3 api_main.py
```

### Statistiche Database
```bash
GET http://localhost:8000/optimization-stats
```

### Pulizia Cache
```bash
POST http://localhost:8000/optimization/clean-cache
```

## Note Tecniche

- **Timeout**: 10 minuti per job
- **Formati Supportati**: PDF
- **Database**: SQLite (locale) o PostgreSQL (produzione)
- **CORS**: Configurato per sviluppo locale
- **Rate Limiting**: Gestito automaticamente per Gemini API

## Troubleshooting

### Errori Comuni
1. **Timeout**: Verificare la dimensione del PDF e la connessione internet
2. **API Key**: Controllare che `GEMINI_API_KEY` sia configurata
3. **Database**: Verificare la connessione al database
4. **File Upload**: Controllare che il file sia un PDF valido

### Supporto
Per problemi tecnici, controllare i log del server e la documentazione API su `/docs`.