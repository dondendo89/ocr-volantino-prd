from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
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
import requests
import tempfile

# Carica le variabili d'ambiente dal file .env
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ File .env caricato con successo")
except ImportError:
    print("⚠️ python-dotenv non installato. Installare con: pip install python-dotenv")
except Exception as e:
    print(f"⚠️ Errore nel caricamento .env: {e}")

# Import delle configurazioni
from api_config import (
    API_CONFIG, FILE_LIMITS, WORK_DIRS, PROCESSING_CONFIG, 
    CORS_CONFIG, RESPONSE_MESSAGES, is_allowed_file_type, 
    get_response_message, get_max_file_size_mb, get_job_url,
    get_results_url, get_products_url, BASE_URL, IS_PRODUCTION
)

# Import del nostro modulo OCR
from simplified_gemini_extractor import SimplifiedGeminiExtractor

# Import del database
from database import db_manager, ProcessingJob
print(f"✅ Database importato con successo. URL: {os.getenv('DATABASE_URL', 'NON_CONFIGURATA')}")
print(f"🌍 Ambiente: {'PRODUZIONE' if IS_PRODUCTION else 'SVILUPPO'} - Base URL: {BASE_URL}")
print(f"🔗 CORS Origins: {CORS_CONFIG['allow_origins']}")

# Esegui migrazione automatica all'avvio
try:
    from auto_migration import run_auto_migration
    print("🔧 Eseguendo migrazione automatica del database...")
    migration_success = run_auto_migration()
    if migration_success:
        print("✅ Migrazione automatica completata con successo")
    else:
        print("⚠️ Migrazione automatica completata con alcuni avvertimenti")
except Exception as e:
    print(f"❌ Errore durante migrazione automatica: {e}")
    print("⚠️ L'applicazione continuerà comunque l'avvio...")

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

# Mount dei file statici
app.mount("/static", StaticFiles(directory="static"), name="static")

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
    image_url: Optional[str] = None  # URL dell'immagine del prodotto
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
    supermercato_nome: str
    progress: Optional[int] = None
    message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

class URLProcessRequest(BaseModel):
    url: str
    supermercato_nome: str  # Nome del supermercato (obbligatorio)
    job_name: Optional[str] = None

class ProductUpdateRequest(BaseModel):
    nome: Optional[str] = None
    prezzo: Optional[float] = None
    marca: Optional[str] = None
    categoria: Optional[str] = None
    quantita: Optional[str] = None
    image_url: Optional[str] = None  # URL dell'immagine del prodotto
    hidden: Optional[bool] = None

class SupermercatoCreate(BaseModel):
    nome: str
    descrizione: Optional[str] = None
    logo_url: Optional[str] = None
    sito_web: Optional[str] = None
    colore_tema: Optional[str] = "#3498db"

class SupermercatoUpdate(BaseModel):
    nome: Optional[str] = None
    descrizione: Optional[str] = None
    logo_url: Optional[str] = None
    sito_web: Optional[str] = None
    colore_tema: Optional[str] = None

class SupermercatoResponse(BaseModel):
    id: int
    nome: str
    descrizione: Optional[str] = None
    logo_url: Optional[str] = None
    sito_web: Optional[str] = None
    colore_tema: str
    attivo: str
    created_at: datetime
    updated_at: datetime
    total_jobs: int

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
    except Exception as e:
        return {
            "status": "degraded",
            "timestamp": datetime.now().isoformat(),
            "database": "error",
            "error": str(e)
        }

async def process_flyer_async(job_id: str, file_path: str, supermercato_nome: str = "SUPERMERCATO"):
    """Elaborazione asincrona del volantino con ottimizzazioni"""
    print(f"🔍 DEBUG: process_flyer_async chiamata con job_id={job_id}, file_path={file_path}, supermercato_nome={supermercato_nome}")
    logger.info(f"🔍 DEBUG: process_flyer_async chiamata con job_id={job_id}, file_path={file_path}, supermercato_nome={supermercato_nome}")
    try:
        logger.info(f"🚀 Avvio elaborazione ottimizzata per job {job_id}")
        
        # Aggiorna stato a "processing" nel database
        db_manager.update_job_status(job_id, "processing", progress=10, message="Elaborazione in corso...")
        
        start_time = datetime.now()
        
        # Timeout globale per il job (20 minuti)
        import signal
        def timeout_handler(signum, frame):
            logger.error(f"⏰ Timeout globale raggiunto per job {job_id}")
            db_manager.update_job_status(job_id, "failed", progress=100, message="Timeout: elaborazione interrotta dopo 20 minuti")
            raise TimeoutError("Job timeout dopo 20 minuti")
        
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(1200)  # 20 minuti
        
        # Elabora il volantino usando GeminiOnlyExtractor con ottimizzazioni
        logger.info(f"Inizio elaborazione volantino: {file_path}")
        db_manager.update_job_status(job_id, "processing", progress=30, message="Analisi PDF con Gemini...")
        
        # Inizializza SimpleGeminiExtractor (versione semplificata e stabile)
        gemini_key = os.getenv('GEMINI_API_KEY')
        logger.info(f"🔍 DEBUG: GEMINI_API_KEY caricata: {'Sì' if gemini_key else 'No'}")
        print(f"🔍 DEBUG: GEMINI_API_KEY caricata: {'Sì' if gemini_key else 'No'}")
        
        if not gemini_key:
            error_msg = "GEMINI_API_KEY non configurata"
            logger.error(f"🔍 DEBUG: {error_msg}")
            print(f"🔍 DEBUG: {error_msg}")
            raise ValueError(error_msg)
        
        extractor = SimplifiedGeminiExtractor(
            gemini_api_key=gemini_key,
            job_id=job_id, 
            db_manager=db_manager,
            supermercato_nome=supermercato_nome
        )
        
        logger.info(f"✅ Estrazione con SimplifiedGeminiExtractor per job {job_id}")
        logger.info(f"🔍 DEBUG API: File path: {file_path}")
        logger.info(f"🔍 DEBUG API: Supermercato: {supermercato_nome}")
        logger.info(f"🔍 DEBUG API: Job ID: {job_id}")
        
        # Determina il tipo di sorgente (file o URL)
        source_type = "url" if file_path.startswith("http") else "file"
        
        db_manager.update_job_status(job_id, "processing", progress=50, message="Conversione PDF in immagini...")
        
        # Esegue l'estrazione
        logger.info(f"🔍 DEBUG API: Chiamando extractor.run() con source_type={source_type}")
        extraction_result = extractor.run(pdf_source=file_path, source_type=source_type)
        logger.info(f"🔍 DEBUG API: extractor.run() completato. Risultato: {extraction_result}")
        
        db_manager.update_job_status(job_id, "processing", progress=80, message="Estrazione dati completata...")
        
        # Gestisce il risultato dell'estrazione
        if extraction_result and extraction_result.get("success"):
            products = extraction_result.get("products", [])
            logger.info(f"✅ Estrazione completata: {len(products)} prodotti trovati, {extraction_result.get('products_saved', 0)} salvati nel DB")
        else:
            products = []
            error_msg = extraction_result.get("error", "Errore sconosciuto") if extraction_result else "Nessun risultato"
            logger.error(f"❌ Estrazione fallita: {error_msg}")
            raise Exception(f"Estrazione fallita: {error_msg}")
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        # I prodotti sono già stati salvati nel database da GeminiOnlyExtractor
        # Il job viene aggiornato automaticamente da GeminiOnlyExtractor.run()
        # Aggiorniamo solo il processing_time se non è già stato fatto
        job = db_manager.get_job(job_id)
        if job and job.status != "completed":
            db_manager.update_job_status(
                job_id, 
                "completed", 
                progress=100, 
                message=f"Elaborazione completata. Trovati {len(products)} prodotti",
                processing_time=processing_time,
                total_products=len(products)
            )
        
        logger.info(f"Job {job_id} completato con successo. Trovati {len(products)} prodotti")
        
        # Disattiva il timeout
        signal.alarm(0)
        
    except TimeoutError as e:
        logger.error(f"⏰ Timeout job {job_id}: {str(e)}")
        # Il job è già stato aggiornato nel timeout_handler
        signal.alarm(0)
        
    except Exception as e:
        error_msg = f"Errore durante l'elaborazione: {str(e)}"
        logger.error(f"Errore job {job_id}: {error_msg}")
        logger.error(traceback.format_exc())
        
        # Disattiva il timeout
        signal.alarm(0)
        
        # Segna job come fallito nel database
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
    file: UploadFile = File(...),
    supermercato_nome: str = Form(...)
):
    """Carica e processa un volantino"""
    
    print("🚀 UPLOAD ENDPOINT CHIAMATO!")
    logger.info("🚀 UPLOAD ENDPOINT CHIAMATO!")
    logger.info(f"Ricevuto upload file: {file.filename}, type: {file.content_type}")
    
    # Validazione tipo file
    if not is_allowed_file_type(file.filename or "", file.content_type or ""):
        raise HTTPException(
            status_code=400, 
            detail=get_response_message("invalid_file_type")
        )
    
    # Leggi il contenuto del file per validare la dimensione
    file_content = await file.read()
    file_size = len(file_content)
    
    # Validazione dimensione file
    if file_size > FILE_LIMITS["max_file_size"]:
        raise HTTPException(
            status_code=400,
            detail=get_response_message("file_too_large", max_size=get_max_file_size_mb())
        )
    
    logger.info(f"File size: {file_size} bytes")
    
    # Salva file temporaneo con nome temporaneo
    temp_filename = f"temp_{uuid.uuid4()}_{file.filename}"
    file_extension = os.path.splitext(file.filename)[1] if file.filename else '.jpg'
    temp_file_path = TEMP_DIR / temp_filename
    
    try:
        with open(temp_file_path, "wb") as buffer:
            buffer.write(file_content)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Errore durante il salvataggio del file: {str(e)}"
        )
    
    # Crea job nel database
    job = db_manager.create_job(
        filename=file.filename,
        file_path=str(temp_file_path),
        supermercato_nome=supermercato_nome
    )
    job_id = job.id
    
    # Aggiorna il file path con l'ID del job
    final_filename = f"{job.id}_{file.filename}"
    final_file_path = TEMP_DIR / final_filename
    
    # Rinomina il file con l'ID del job
    os.rename(temp_file_path, final_file_path)
    
    # Aggiorna il path nel database
    db_manager.update_job_status(job.id, "queued", message="File caricato, elaborazione in coda")
    
    # Avvia elaborazione in background
    logger.info(f"🔍 DEBUG: Aggiungendo background task per job {job_id}")
    print(f"🔍 DEBUG: Aggiungendo background task per job {job_id}")
    try:
        background_tasks.add_task(process_flyer_async, job_id, str(final_file_path), supermercato_nome)
        logger.info(f"🔍 DEBUG: Background task aggiunto con successo per job {job_id}")
        print(f"🔍 DEBUG: Background task aggiunto con successo per job {job_id}")
    except Exception as e:
        logger.error(f"🔍 DEBUG: Errore nell'aggiungere background task: {e}")
        print(f"🔍 DEBUG: Errore nell'aggiungere background task: {e}")
    
    logger.info(f"Job {job_id} creato per file {file.filename}")
    
    # Verifica se è disponibile la seconda chiave Gemini
    optimization_status = "dual_key_enabled" if os.getenv('GEMINI_API_KEY_2') else "single_key"
    
    return {
        "success": True,
        "job_id": job_id,
        "status": "queued",
        "message": get_response_message("upload_success"),
        "estimated_time": "30-60 secondi",
        "filename": file.filename,
        "file_size": file_size,
        "optimization": optimization_status,
        "check_status_url": get_job_url(job_id),
        "results_url": get_results_url(job_id),
        "products_url": get_products_url(job_id),
        "environment": "production" if IS_PRODUCTION else "development",
        "base_url": BASE_URL
    }

@app.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Ottieni lo stato di elaborazione di un job"""
    
    job = db_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job non trovato")
    
    return JobStatus(
        job_id=job.id,
        status=job.status,
        supermercato_nome=job.supermercato_nome,
        progress=job.progress,
        message=job.message,
        created_at=job.created_at,
        completed_at=job.completed_at
    )

@app.get("/results/{job_id}", response_model=Dict[str, Any])
async def get_results(job_id: str):
    """Ottieni i risultati dell'elaborazione"""
    try:
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
        products = db_manager.get_products(job_id)
        
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
        products = db_manager.get_products(job_id)
        
        return [p.to_dict() for p in products]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore durante recupero prodotti job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=get_response_message("products_error")
        )

@app.post("/process-url", response_model=Dict[str, Any])
async def process_url(
    background_tasks: BackgroundTasks,
    request: URLProcessRequest
):
    """
    Elabora un PDF da URL
    """
    try:
        # Genera job ID
        job_id = str(uuid.uuid4())
        
        # Crea job nel database
        db_manager.create_job_with_id(
            job_id=job_id,
            filename=request.url,
            supermercato_nome=request.supermercato_nome,
            status="queued"
        )
        
        # Avvia elaborazione in background
        background_tasks.add_task(process_url_async, job_id, request.url, request.supermercato_nome, request.job_name)
        
        logger.info(f"Job {job_id} creato per URL: {request.url}")
        
        return {
            "success": True,
            "job_id": job_id,
            "status": "queued",
            "message": "Elaborazione avviata",
            "url": request.url,
            "timestamp": datetime.now().isoformat(),
            "check_status_url": get_job_url(job_id),
            "results_url": get_results_url(job_id),
            "products_url": get_products_url(job_id),
            "supermercato": request.supermercato_nome,
            "estimated_processing_time": "2-5 minuti",
            "environment": "production" if IS_PRODUCTION else "development",
            "base_url": BASE_URL
        }
        
    except Exception as e:
        logger.error(f"Errore durante creazione job per URL {request.url}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore durante avvio elaborazione: {str(e)}"
        )

async def process_url_async(job_id: str, url: str, supermercato_nome: str, job_name: Optional[str] = None):
    """
    Elabora un PDF da URL in modo asincrono
    """
    try:
        # Aggiorna status a processing
        db_manager.update_job_status(job_id, "processing", "Download del file in corso...")
        
        # Download del file
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Salva file temporaneo
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(response.content)
            temp_path = temp_file.name
        
        # Elabora il file (riusa la logica esistente)
        await process_flyer_async(job_id, temp_path, supermercato_nome)
        
        # Pulisci file temporaneo
        os.unlink(temp_path)
        
    except Exception as e:
        logger.error(f"Errore durante elaborazione URL {url} per job {job_id}: {str(e)}")
        db_manager.update_job_status(job_id, "failed", f"Errore: {str(e)}")

@app.put("/products/{product_id}", response_model=Dict[str, Any])
async def update_product(product_id: int, request: ProductUpdateRequest):
    """
    Aggiorna un prodotto
    """
    try:
        # Recupera prodotto esistente
        product = db_manager.get_product_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=404,
                detail="Prodotto non trovato"
            )
        
        # Aggiorna campi forniti
        update_data = {}
        if request.nome is not None:
            update_data['nome'] = request.nome
        if request.prezzo is not None:
            update_data['prezzo'] = request.prezzo
        if request.marca is not None:
            update_data['marca'] = request.marca
        if request.categoria is not None:
            update_data['categoria'] = request.categoria
        if request.quantita is not None:
            update_data['quantita'] = request.quantita
        if request.image_url is not None:
            update_data['image_url'] = request.image_url
        if request.hidden is not None:
            update_data['hidden'] = request.hidden
        
        # Esegui aggiornamento
        success = db_manager.update_product(product_id, update_data)
        
        if success:
            return {
                "success": True,
                "message": "Prodotto aggiornato con successo",
                "product_id": product_id
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Errore durante aggiornamento prodotto"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore durante aggiornamento prodotto {product_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore interno: {str(e)}"
        )

@app.delete("/products/{product_id}", response_model=Dict[str, Any])
async def delete_product(product_id: int):
    """
    Elimina un prodotto
    """
    try:
        # Verifica esistenza prodotto
        product = db_manager.get_product_by_id(product_id)
        if not product:
            raise HTTPException(
                status_code=404,
                detail="Prodotto non trovato"
            )
        
        # Elimina prodotto
        success = db_manager.delete_product(product_id)
        
        if success:
            return {
                "success": True,
                "message": "Prodotto eliminato con successo",
                "product_id": product_id
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Errore durante eliminazione prodotto"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore durante eliminazione prodotto {product_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore interno: {str(e)}"
        )

@app.delete("/products/all", response_model=Dict[str, Any])
async def delete_all_products():
    """
    Elimina tutti i prodotti dal database
    """
    try:
        # Elimina tutti i prodotti
        result = db_manager.delete_all_products()
        
        if result["success"]:
            return {
                "success": True,
                "message": result["message"],
                "deleted_count": result["deleted_count"]
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=result["message"]
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore durante eliminazione di tutti i prodotti: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore interno: {str(e)}"
        )

@app.get("/products-by-supermarket", response_model=Dict[str, Any])
async def get_products_by_supermarket():
    """
    Ottieni tutti i prodotti organizzati per supermercato
    """
    try:
        # Recupera tutti i job completati
        jobs = db_manager.get_all_jobs(limit=1000)
        
        # Organizza per supermercato
        supermarkets = {}
        
        for job in jobs:
            if job["status"] == "completed" and job["supermercato_nome"]:
                supermercato = job["supermercato_nome"]
                
                if supermercato not in supermarkets:
                    supermarkets[supermercato] = {
                        "nome": supermercato,
                        "jobs": [],
                        "total_products": 0,
                        "products": []
                    }
                
                # Recupera prodotti per questo job
                products = db_manager.get_products(job["id"])
                
                job_data = {
                    "job_id": job["id"],
                    "filename": job["filename"],
                    "created_at": job["created_at"],
                    "total_products": len(products)
                }
                
                supermarkets[supermercato]["jobs"].append(job_data)
                supermarkets[supermercato]["total_products"] += len(products)
                
                # Aggiungi prodotti con info del job
                for product in products:
                    product_dict = product.to_dict()
                    product_dict["job_filename"] = job["filename"]
                    product_dict["job_created_at"] = job["created_at"]
                    supermarkets[supermercato]["products"].append(product_dict)
        
        return {
            "success": True,
            "supermarkets": list(supermarkets.values()),
            "total_supermarkets": len(supermarkets)
        }
        
    except Exception as e:
        logger.error(f"Errore durante recupero prodotti per supermercato: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore interno: {str(e)}"
        )

@app.get("/jobs", response_model=List[Dict[str, Any]])
async def get_all_jobs(limit: int = 50, offset: int = 0):
    """
    Recupera lista di tutti i jobs
    """
    try:
        jobs = db_manager.get_all_jobs(limit=limit, offset=offset)
        return jobs  # Ora get_all_jobs restituisce già una lista di dizionari
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore durante recupero jobs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore interno: {str(e)}"
        )

# Endpoint per gestione supermercati
@app.post("/supermercati", response_model=SupermercatoResponse)
async def create_supermercato(request: SupermercatoCreate):
    """Crea un nuovo supermercato"""
    try:
        # Verifica se esiste già un supermercato con lo stesso nome
        existing = db_manager.get_supermercato_by_nome(request.nome)
        if existing:
            raise HTTPException(status_code=400, detail="Supermercato con questo nome già esistente")
        
        supermercato = db_manager.create_supermercato(
            nome=request.nome,
            descrizione=request.descrizione,
            logo_url=request.logo_url,
            sito_web=request.sito_web,
            colore_tema=request.colore_tema
        )
        
        return SupermercatoResponse(**supermercato.to_dict(total_jobs=0))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore durante creazione supermercato: {e}")
        raise HTTPException(status_code=500, detail="Errore interno del server")

@app.get("/supermercati", response_model=List[SupermercatoResponse])
async def get_supermercati():
    """Ottiene tutti i supermercati attivi"""
    
    try:
        supermercati = db_manager.get_all_supermercati()
        return [SupermercatoResponse(**s.to_dict()) for s in supermercati]
    except Exception as e:
        logger.error(f"Errore durante recupero supermercati: {e}")
        raise HTTPException(status_code=500, detail="Errore interno del server")

@app.get("/supermercati/{supermercato_id}", response_model=SupermercatoResponse)
async def get_supermercato(supermercato_id: int):
    """Ottiene un supermercato per ID"""
    try:
        supermercato = db_manager.get_supermercato_by_id(supermercato_id)
        if not supermercato:
            raise HTTPException(status_code=404, detail="Supermercato non trovato")
        
        return SupermercatoResponse(**supermercato.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore durante recupero supermercato {supermercato_id}: {e}")
        raise HTTPException(status_code=500, detail="Errore interno del server")

@app.put("/supermercati/{supermercato_id}", response_model=SupermercatoResponse)
async def update_supermercato(supermercato_id: int, request: SupermercatoUpdate):
    """Aggiorna un supermercato"""
    try:
        # Verifica se il supermercato esiste
        supermercato = db_manager.get_supermercato_by_id(supermercato_id)
        if not supermercato:
            raise HTTPException(status_code=404, detail="Supermercato non trovato")
        
        # Verifica se il nuovo nome è già in uso (se fornito)
        if request.nome and request.nome != supermercato.nome:
            existing = db_manager.get_supermercato_by_nome(request.nome)
            if existing:
                raise HTTPException(status_code=400, detail="Nome supermercato già in uso")
        
        # Prepara i dati per l'aggiornamento
        update_data = {k: v for k, v in request.dict().items() if v is not None}
        
        success = db_manager.update_supermercato(supermercato_id, update_data)
        if not success:
            raise HTTPException(status_code=500, detail="Errore durante aggiornamento")
        
        # Recupera il supermercato aggiornato con conteggio job
        updated_supermercato = db_manager.get_supermercato_by_id(supermercato_id)
        
        # Conta i job per questo supermercato
        session = db_manager.get_session()
        try:
            job_count = session.query(ProcessingJob).filter(ProcessingJob.supermercato_id == supermercato_id).count()
        finally:
            session.close()
            
        return SupermercatoResponse(**updated_supermercato.to_dict(total_jobs=job_count))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore durante aggiornamento supermercato {supermercato_id}: {e}")
        raise HTTPException(status_code=500, detail="Errore interno del server")

@app.delete("/supermercati/{supermercato_id}", response_model=Dict[str, Any])
async def delete_supermercato(supermercato_id: int):
    """Elimina (disattiva) un supermercato"""
    try:
        supermercato = db_manager.get_supermercato_by_id(supermercato_id)
        if not supermercato:
            raise HTTPException(status_code=404, detail="Supermercato non trovato")
        
        success = db_manager.delete_supermercato(supermercato_id)
        if not success:
            raise HTTPException(status_code=500, detail="Errore durante eliminazione")
        
        return {
            "success": True,
            "message": f"Supermercato '{supermercato.nome}' disattivato con successo"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore durante eliminazione supermercato {supermercato_id}: {e}")
        raise HTTPException(status_code=500, detail="Errore interno del server")

if __name__ == "__main__":
    uvicorn.run(
        "api_main:app",
        host=API_CONFIG["host"],
        port=API_CONFIG["port"],
        reload=API_CONFIG["reload"],
        log_level=API_CONFIG["log_level"]
    )

# Endpoint ottimizzazioni token
@app.get("/optimization-stats")
async def get_optimization_stats():
    """Statistiche ottimizzazioni token"""
    try:
        from gemini_optimized_extractor import create_optimized_extractor
        extractor = create_optimized_extractor()
        stats = extractor.get_optimization_report()
        return {
            "status": "success",
            "optimization_stats": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.post("/optimization/clean-cache")
async def clean_optimization_cache():
    """Pulisce cache ottimizzazioni"""
    try:
        from gemini_optimized_extractor import create_optimized_extractor
        extractor = create_optimized_extractor()
        extractor.clean_cache()
        return {
            "status": "success",
            "message": "Cache pulita con successo",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }