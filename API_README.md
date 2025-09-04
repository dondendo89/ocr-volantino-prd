# OCR Volantino API

🚀 **API REST per l'estrazione automatica di dati da volantini italiani usando OCR e AI**

## 📋 Panoramica

Questa API permette di:
- Caricare immagini di volantini
- Estrarre automaticamente informazioni sui prodotti (nome, prezzo, marca, categoria)
- Ottenere risultati strutturati in formato JSON
- Monitorare lo stato dell'elaborazione

## 🛠️ Installazione e Avvio

### 1. Installazione Dipendenze
```bash
pip install -r requirements.txt
```

### 2. Avvio del Servizio
```bash
# Avvio standard
python api_main.py

# Oppure con uvicorn direttamente
uvicorn api_main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Verifica Funzionamento
```bash
# Test rapido
curl http://localhost:8000/health

# Oppure usa lo script di test
python test_api.py --quick
```

## 📡 Endpoints API

### 🏠 Root Endpoint
```http
GET /
```
Restituisce informazioni generali sull'API.

**Risposta:**
```json
{
  "message": "OCR Volantino API - Servizio di estrazione dati da volantini",
  "version": "1.0.0",
  "endpoints": {
    "/upload": "POST - Carica e processa volantino",
    "/jobs/{job_id}": "GET - Stato elaborazione",
    "/results/{job_id}": "GET - Risultati elaborazione",
    "/health": "GET - Stato del servizio"
  }
}
```

### 💚 Health Check
```http
GET /health
```
Controlla lo stato del servizio.

**Risposta:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00",
  "active_jobs": 2,
  "completed_jobs": 15
}
```

### 📤 Upload Volantino
```http
POST /upload
```
Carica e avvia l'elaborazione di un volantino.

**Parametri:**
- `file`: File immagine (JPEG, PNG, BMP, TIFF, WebP)
- Dimensione massima: 10MB

**Esempio con curl:**
```bash
curl -X POST "http://localhost:8000/upload" \
     -H "accept: application/json" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@volantino.jpg"
```

**Risposta:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "File caricato con successo. Elaborazione avviata.",
  "estimated_time": "30-60 secondi",
  "filename": "volantino.jpg"
}
```

### 📊 Stato Elaborazione
```http
GET /jobs/{job_id}
```
Ottiene lo stato di elaborazione di un job.

**Risposta:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": 75,
  "message": "Elaborazione in corso...",
  "created_at": "2024-01-15T10:30:00",
  "completed_at": null
}
```

**Stati possibili:**
- `queued`: In coda per elaborazione
- `processing`: Elaborazione in corso
- `completed`: Elaborazione completata
- `failed`: Elaborazione fallita

### 📋 Risultati Completi
```http
GET /results/{job_id}
```
Ottiene i risultati completi dell'elaborazione.

**Risposta:**
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "message": "Elaborazione completata con successo",
  "timestamp": "2024-01-15T10:32:30",
  "total_products": 12,
  "processing_time": 45.2,
  "products": [
    {
      "nome": "Pasta Barilla Spaghetti 500g",
      "prezzo": 1.99,
      "prezzo_originale": 2.49,
      "sconto_percentuale": 20.0,
      "quantita": "500g",
      "marca": "Barilla",
      "categoria": "Pasta",
      "posizione": {"x": 150, "y": 200, "width": 200, "height": 100}
    }
  ]
}
```

### 🛍️ Solo Prodotti
```http
GET /products/{job_id}
```
Ottiene solo la lista dei prodotti estratti.

**Risposta:**
```json
[
  {
    "nome": "Pasta Barilla Spaghetti 500g",
    "prezzo": 1.99,
    "prezzo_originale": 2.49,
    "sconto_percentuale": 20.0,
    "quantita": "500g",
    "marca": "Barilla",
    "categoria": "Pasta",
    "posizione": {"x": 150, "y": 200, "width": 200, "height": 100}
  }
]
```

## 🧪 Testing

### Script di Test Automatico
```bash
# Test completo
python test_api.py

# Test rapido
python test_api.py --quick

# Test con immagine specifica
python test_api.py --image /path/to/volantino.jpg

# Test casi di errore
python test_api.py --errors

# Test su URL diverso
python test_api.py --url http://api.example.com:8000
```

### Test Manuale con curl

1. **Health Check:**
```bash
curl http://localhost:8000/health
```

2. **Upload File:**
```bash
curl -X POST "http://localhost:8000/upload" \
     -F "file=@test_volantino.jpg"
```

3. **Controlla Stato:**
```bash
curl http://localhost:8000/jobs/YOUR_JOB_ID
```

4. **Ottieni Risultati:**
```bash
curl http://localhost:8000/results/YOUR_JOB_ID
```

## 🔧 Configurazione

### File di Configurazione
Le configurazioni sono in `api_config.py`:

```python
# Limiti file
FILE_LIMITS = {
    "max_file_size": 10 * 1024 * 1024,  # 10MB
    "allowed_extensions": [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"]
}

# Configurazione API
API_CONFIG = {
    "host": "0.0.0.0",
    "port": 8000,
    "reload": True
}
```

### Variabili Ambiente
```bash
# Opzionali
export ENVIRONMENT=production
export DATABASE_URL=sqlite:///./ocr_volantino.db
export REDIS_URL=redis://localhost:6379/0
export SECRET_KEY=your-secret-key
```

## 📊 Monitoraggio

### Logs
I log sono salvati in:
- Console: Output in tempo reale
- File: `logs/api.log`

### Metriche
L'endpoint `/health` fornisce:
- Stato del servizio
- Numero di job attivi
- Numero di job completati
- Timestamp ultimo controllo

## 🚀 Deployment

### Docker (Futuro)
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "api_main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Produzione
```bash
# Con Gunicorn
gunicorn api_main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# Con systemd service
sudo systemctl enable ocr-volantino-api
sudo systemctl start ocr-volantino-api
```

## 🔒 Sicurezza

### Validazioni Implementate
- ✅ Controllo tipo file (solo immagini)
- ✅ Limite dimensione file (10MB)
- ✅ Validazione estensioni file
- ✅ Sanitizzazione input
- ✅ Gestione errori

### Future Implementazioni
- 🔄 Autenticazione API Key
- 🔄 Rate limiting
- 🔄 HTTPS obbligatorio
- 🔄 Logging sicurezza

## 🐛 Troubleshooting

### Problemi Comuni

1. **API non si avvia:**
```bash
# Controlla dipendenze
pip install -r requirements.txt

# Controlla porta
lsof -i :8000
```

2. **Errore OCR:**
```bash
# Installa Tesseract
brew install tesseract  # macOS
sudo apt-get install tesseract-ocr  # Ubuntu
```

3. **File troppo grande:**
- Riduci dimensione immagine
- Comprimi JPEG
- Modifica `FILE_LIMITS` in `api_config.py`

4. **Elaborazione lenta:**
- Usa immagini più piccole
- Aumenta `max_concurrent_jobs`
- Considera GPU per AI

### Debug
```bash
# Abilita debug logging
export LOG_LEVEL=DEBUG
python api_main.py

# Test con verbose
python test_api.py --verbose
```

## 📚 Documentazione API

Una volta avviata l'API, la documentazione interattiva è disponibile su:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🤝 Contributi

Per contribuire al progetto:
1. Fork del repository
2. Crea branch feature
3. Implementa modifiche
4. Aggiungi test
5. Crea Pull Request

## 📄 Licenza

Questo progetto è rilasciato sotto licenza MIT.

---

**🎯 Pronto per l'uso!** Avvia l'API e inizia a estrarre dati dai tuoi volantini! 🛍️