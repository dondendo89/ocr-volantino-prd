from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import os
import json
import uuid
from datetime import datetime
import asyncio
from pathlib import Path
import shutil
import logging
import traceback

# Import delle configurazioni
from api_config import (
    API_CONFIG, FILE_LIMITS, WORK_DIRS, PROCESSING_CONFIG, 
    CORS_CONFIG, RESPONSE_MESSAGES, is_allowed_file_type, 
    get_response_message, get_max_file_size_mb
)

# Import del nostro modulo OCR
try:
    from colab_adapted import process_flyer_image
except ImportError:
    print("Attenzione: modulo colab_adapted non trovato. Verrà usata una funzione mock.")
    def process_flyer_image(image_path):
        # Funzione mock per testing
        return {
            'products': [
                {
                    'nome': 'Prodotto Test',
                    'prezzo': 2.99,
                    'marca': 'Test Brand',
                    'categoria': 'Test Category'
                }
            ]
        }

# Import del database (opzionale per deployment semplificato)
try:
    from database import db_manager
except ImportError:
    print("Attenzione: modulo database non disponibile. Funzionalità database disabilitate.")
    db_manager = None

app = FastAPI(
    title=API_CONFIG["title"],
    description=API_CONFIG["description"],
    version=API_CONFIG["version"]
)

# Configurazione CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_CONFIG["allow_origins"],
    allow_credentials=CORS_CONFIG["allow_credentials"],
    allow_methods=CORS_CONFIG["allow_methods"],
    allow_headers=CORS_CONFIG["allow_headers"],
)

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Modelli Pydantic per le risposte
class ProductData(BaseModel):
    nome: str
    prezzo: Optional[float] = None
    prezzo_originale: Optional[float] = None
    sconto_percentuale: Optional[float] = None
    quantita: Optional[str] = None
    marca: Optional[str] = None
    categoria: Optional[str] = None
    posizione: Optional[Dict[str, int]] = None

class ProcessingResult(BaseModel):
    job_id: str
    status: str
    message: str
    timestamp: datetime
    products: Optional[List[ProductData]] = None
    total_products: Optional[int] = None
    processing_time: Optional[float] = None

class JobStatus(BaseModel):
    job_id: str
    status: str
    progress: Optional[int] = None
    message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

# Il database sostituisce lo storage in memoria

# Directory di lavoro
TEMP_DIR = WORK_DIRS["temp_uploads"]
PROCESSED_DIR = WORK_DIRS["processed_images"]
LOGS_DIR = WORK_DIRS["logs"]

@app.get("/")
async def root():
    """Endpoint di benvenuto con informazioni sull'API"""
    return {
        "message": "OCR Volantino API - Servizio di estrazione dati da volantini",
        "version": "1.0.0",
        "endpoints": {
            "/upload": "POST - Carica e processa volantino",
            "/jobs/{job_id}": "GET - Stato elaborazione",
            "/results/{job_id}": "GET - Risultati elaborazione",
            "/health": "GET - Stato del servizio"
        }
    }

@app.get("/health")
async def health_check():
    """Controllo stato del servizio"""
    try:
        if db_manager:
            db_stats = db_manager.get_stats()
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "database": "connected",
                "active_jobs": db_stats["active_jobs"],
                "completed_jobs": db_stats["completed_jobs"],
                "total_jobs": db_stats["total_jobs"],
                "total_products": db_stats["total_products"]
            }
        else:
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "database": "not_configured",
                "message": "Database non configurato, funzionalità limitate"
            }
    except Exception as e:
        return {
            "status": "degraded",
            "timestamp": datetime.now().isoformat(),
            "database": "error",
            "error": str(e)
        }

async def process_flyer_async(job_id: str, file_path: str):
    """Elaborazione asincrona del volantino"""
    try:
        logger.info(f"Avvio elaborazione job {job_id}")
        
        # Aggiorna stato a "processing" nel database (se disponibile)
        if db_manager:
            db_manager.update_job_status(job_id, "processing", progress=10, message="Elaborazione in corso...")
        
        start_time = datetime.now()
        
        # Elabora il volantino usando il nostro script OCR
        logger.info(f"Inizio elaborazione volantino: {file_path}")
        if db_manager:
            db_manager.update_job_status(job_id, "processing", progress=30, message="Analisi immagine...")
        
        # Chiama la funzione OCR principale
        extracted_data = process_flyer_image(file_path)
        
        if db_manager:
            db_manager.update_job_status(job_id, "processing", progress=80, message="Estrazione dati...")
        
        # Converte i risultati nel formato API
        products = []
        if extracted_data and 'products' in extracted_data:
            for product in extracted_data['products']:
                products.append({
                    'nome': product.get('nome', ''),
                    'prezzo': product.get('prezzo'),
                    'prezzo_originale': product.get('prezzo_originale'),
                    'sconto_percentuale': product.get('sconto_percentuale'),
                    'quantita': product.get('quantita'),
                    'marca': product.get('marca'),
                    'categoria': product.get('categoria'),
                    'posizione': product.get('posizione')
                })
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # Salva prodotti nel database (se disponibile)
        if db_manager and products:
            db_manager.save_products(job_id, products)
        
        # Aggiorna job come completato nel database (se disponibile)
        if db_manager:
            db_manager.update_job_status(
                job_id, 
                "completed", 
                progress=100, 
                message=f"Elaborazione completata. Trovati {len(products)} prodotti",
                processing_time=processing_time,
                total_products=len(products)
            )
        
        logger.info(f"Job {job_id} completato con successo. Trovati {len(products)} prodotti")
        
    except Exception as e:
        error_msg = f"Errore durante l'elaborazione: {str(e)}"
        logger.error(f"Errore job {job_id}: {error_msg}")
        logger.error(traceback.format_exc())
        
        # Segna job come fallito nel database (se disponibile)
        if db_manager:
            db_manager.update_job_status(
                job_id, 
                "failed", 
                progress=0, 
                message=error_msg
            )
    
    finally:
        # Cleanup del file temporaneo se configurato
        if PROCESSING_CONFIG["cleanup_temp_files"]:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"File temporaneo rimosso: {file_path}")
            except Exception as cleanup_error:
                logger.warning(f"Errore durante cleanup file {file_path}: {str(cleanup_error)}")

@app.post("/upload", response_model=Dict[str, Any])
async def upload_flyer(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """Carica e processa un volantino"""
    
    logger.info(f"Ricevuto upload file: {file.filename}, size: {file.size}, type: {file.content_type}")
    
    # Validazione tipo file
    if not is_allowed_file_type(file.filename or "", file.content_type or ""):
        raise HTTPException(
            status_code=400, 
            detail=get_response_message("invalid_file_type")
        )
    
    # Validazione dimensione file
    if file.size and file.size > FILE_LIMITS["max_file_size"]:
        raise HTTPException(
            status_code=400,
            detail=get_response_message("file_too_large", max_size=get_max_file_size_mb())
        )
    
    # Salva file temporaneo con nome temporaneo
    temp_filename = f"temp_{uuid.uuid4()}_{file.filename}"
    file_extension = os.path.splitext(file.filename)[1] if file.filename else '.jpg'
    temp_file_path = TEMP_DIR / temp_filename
    
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Errore durante il salvataggio del file: {str(e)}"
        )
    
    # Crea job nel database (se disponibile)
    if db_manager:
        job = db_manager.create_job(
            filename=file.filename,
            file_path=str(temp_file_path)
        )
        job_id = job.id
        
        # Aggiorna il file path con l'ID del job
        final_filename = f"{job.id}_{file.filename}"
        final_file_path = TEMP_DIR / final_filename
        
        # Rinomina il file con l'ID del job
        os.rename(temp_file_path, final_file_path)
        
        # Aggiorna il path nel database
        db_manager.update_job_status(job.id, "queued", message="File caricato, elaborazione in coda")
    else:
        # Genera un job_id semplice se il database non è disponibile
        job_id = str(uuid.uuid4())
        final_file_path = temp_file_path
        logger.info(f"Creato job temporaneo {job_id} per file {file.filename} (database non disponibile)")
    
    # Avvia elaborazione in background
    background_tasks.add_task(process_flyer_async, job_id, str(final_file_path))
    
    logger.info(f"Job {job_id} creato per file {file.filename}")
    
    return {
        "success": True,
        "job_id": job_id,
        "status": "queued",
        "message": get_response_message("upload_success"),
        "estimated_time": "30-60 secondi",
        "filename": file.filename,
        "file_size": file.size
    }

@app.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Ottieni lo stato di elaborazione di un job"""
    
    if not db_manager:
        raise HTTPException(
            status_code=503,
            detail="Database non disponibile. Funzionalità di tracking job disabilitata."
        )
    
    job = db_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job non trovato")
    
    return JobStatus(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        message=job.message,
        created_at=job.created_at,
        completed_at=job.completed_at
    )

@app.get("/results/{job_id}", response_model=Dict[str, Any])
async def get_results(job_id: str):
    """Ottieni i risultati dell'elaborazione"""
    try:
        if not db_manager:
            raise HTTPException(
                status_code=503,
                detail="Database non disponibile. Funzionalità di recupero risultati disabilitata."
            )
        
        job = db_manager.get_job(job_id)
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail=get_response_message("job_not_found")
            )
        
        if job.status in ["queued", "processing"]:
            raise HTTPException(
                status_code=202,
                detail=get_response_message("processing_in_progress")
            )
        
        if job.status == "failed":
            return {
                "success": False,
                "job_id": job_id,
                "status": job.status,
                "message": job.message,
                "timestamp": job.completed_at or job.created_at,
                "products": [],
                "total_products": 0,
                "processing_time": job.processing_time or 0
            }
        
        # Recupera i prodotti dal database
        products = db_manager.get_products(job_id) if db_manager else []
        
        return {
            "success": True,
            "job_id": job_id,
            "status": job.status,
            "message": job.message,
            "timestamp": job.completed_at or job.created_at,
            "products": [p.to_dict() for p in products],
            "total_products": len(products),
            "processing_time": job.processing_time or 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore durante recupero risultati job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=get_response_message("results_error")
        )

@app.get("/products/{job_id}", response_model=List[Dict[str, Any]])
async def get_products(job_id: str):
    """Ottieni solo i prodotti estratti da un job"""
    try:
        if not db_manager:
            raise HTTPException(
                status_code=503,
                detail="Database non disponibile. Funzionalità di recupero prodotti disabilitata."
            )
        
        job = db_manager.get_job(job_id)
        
        if not job:
            raise HTTPException(
                status_code=404,
                detail=get_response_message("job_not_found")
            )
        
        if job.status in ["queued", "processing"]:
            raise HTTPException(
                status_code=202,
                detail=get_response_message("processing_in_progress")
            )
        
        if job.status != "completed":
            return []
        
        # Recupera i prodotti dal database
        products = db_manager.get_products(job_id) if db_manager else []
        
        return [p.to_dict() for p in products]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore durante recupero prodotti job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=get_response_message("products_error")
        )

if __name__ == "__main__":
    uvicorn.run(
        "api_main:app",
        host=API_CONFIG["host"],
        port=API_CONFIG["port"],
        reload=API_CONFIG["reload"],
        log_level=API_CONFIG["log_level"]
    )