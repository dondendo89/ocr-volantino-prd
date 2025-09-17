import sys
import os
from pathlib import Path

# Add parent directory to path to import modules
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import uuid
from datetime import datetime
import logging
import traceback

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Environment variables loaded")
except ImportError:
    print("⚠️ python-dotenv not installed")
except Exception as e:
    print(f"⚠️ Error loading .env: {e}")

# Import configurations
from api_config import (
    API_CONFIG, FILE_LIMITS, WORK_DIRS, PROCESSING_CONFIG, 
    CORS_CONFIG, RESPONSE_MESSAGES, is_allowed_file_type, 
    get_response_message, get_max_file_size_mb, BASE_URL, IS_PRODUCTION
)

# Import database
from database import db_manager, ProcessingJob
print(f"✅ Database imported. URL: {os.getenv('DATABASE_URL', 'NOT_CONFIGURED')}")
print(f"🌍 Environment: {'PRODUCTION' if IS_PRODUCTION else 'DEVELOPMENT'} - Base URL: {BASE_URL}")

# Run automatic migration on startup
try:
    from auto_migration import run_auto_migration
    print("🔧 Running automatic database migration...")
    migration_success = run_auto_migration()
    if migration_success:
        print("✅ Automatic migration completed successfully")
    else:
        print("⚠️ Automatic migration completed with warnings")
except ImportError:
    print("⚠️ auto_migration module not found, skipping automatic migration")
except Exception as e:
    print(f"❌ Error during automatic migration: {e}")
    print("⚠️ Application will continue startup...")

app = FastAPI(
    title=API_CONFIG["title"],
    description=API_CONFIG["description"],
    version=API_CONFIG["version"]
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_CONFIG["allow_origins"],
    allow_credentials=CORS_CONFIG["allow_credentials"],
    allow_methods=CORS_CONFIG["allow_methods"],
    allow_headers=CORS_CONFIG["allow_headers"],
)

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Pydantic models
class ProductData(BaseModel):
    nome: str
    prezzo: Optional[float] = None
    prezzo_originale: Optional[float] = None
    sconto_percentuale: Optional[float] = None
    quantita: Optional[str] = None
    marca: Optional[str] = None
    categoria: Optional[str] = None
    image_url: Optional[str] = None
    posizione: Optional[Dict[str, int]] = None

class JobStatus(BaseModel):
    job_id: str
    status: str
    supermercato_nome: str
    progress: Optional[int] = None
    message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

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

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "OCR Volantino API - Servizio di estrazione dati da volantini",
        "version": API_CONFIG["version"],
        "environment": "vercel" if IS_PRODUCTION else "development",
        "endpoints": {
            "/": "GET - Informazioni API",
            "/health": "GET - Stato del servizio",
            "/api/status": "GET - Stato dell'API",
            "/upload": "POST - Carica e processa volantino",
            "/jobs/{job_id}": "GET - Stato elaborazione",
            "/results/{job_id}": "GET - Risultati elaborazione",
            "/prodotti": "GET - Lista tutti i prodotti",
            "/supermercati": "GET - Lista tutti i supermercati",
            "/supermercati/{id}": "GET - Dettagli supermercato",
            "/supermercati": "POST - Crea nuovo supermercato"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint with database statistics"""
    try:
        # Try to get database statistics
        stats = db_manager.get_stats()
        return {
            "status": "healthy",
            "message": "API funzionante correttamente",
            "timestamp": datetime.now().isoformat(),
            "environment": "vercel" if IS_PRODUCTION else "development",
            "database": {
                "active_jobs": stats.get("active_jobs", 0),
                "completed_jobs": stats.get("completed_jobs", 0),
                "total_products": stats.get("total_products", 0)
            }
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return {
            "status": "healthy",
            "message": "API funzionante correttamente",
            "timestamp": datetime.now().isoformat(),
            "environment": "vercel" if IS_PRODUCTION else "development"
        }

@app.get("/api/status")
async def api_status():
    """API status endpoint"""
    return {
        "api_version": API_CONFIG["version"],
        "platform": "vercel" if IS_PRODUCTION else "local",
        "status": "operational",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/upload", response_model=Dict[str, Any])
async def upload_flyer(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    supermercato_nome: str = Form(...)
):
    """Upload and process flyer endpoint"""
    try:
        # Validate file type
        if not is_allowed_file_type(file.filename):
            raise HTTPException(
                status_code=400,
                detail=get_response_message("invalid_file_type")
            )
        
        # Validate file size
        file_size = 0
        content = await file.read()
        file_size = len(content)
        
        max_size = FILE_LIMITS["max_file_size"]
        if file_size > max_size:
            raise HTTPException(
                status_code=413,
                detail=get_response_message("file_too_large").format(
                    max_size=get_max_file_size_mb()
                )
            )
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Create job in database
        job = db_manager.create_job(
            job_id=job_id,
            filename=file.filename,
            supermercato_nome=supermercato_nome,
            status="pending"
        )
        
        # For now, return success without actual processing
        # In a full implementation, you would add background processing here
        
        return {
            "success": True,
            "job_id": job_id,
            "message": get_response_message("upload_success"),
            "status_url": f"/jobs/{job_id}",
            "results_url": f"/results/{job_id}",
            "file_info": {
                "filename": file.filename,
                "size_mb": round(file_size / (1024 * 1024), 2),
                "supermercato": supermercato_nome
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"Errore interno del server: {str(e)}"
        )

@app.get("/jobs/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get job status"""
    try:
        job = db_manager.get_job(job_id)
        if not job:
            raise HTTPException(
                status_code=404,
                detail=get_response_message("job_not_found")
            )
        
        return JobStatus(
            job_id=job.job_id,
            status=job.status,
            supermercato_nome=job.supermercato_nome,
            progress=job.progress,
            message=job.message,
            created_at=job.created_at,
            completed_at=job.completed_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get job status error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore interno del server: {str(e)}"
        )

@app.get("/results/{job_id}", response_model=Dict[str, Any])
async def get_results(job_id: str):
    """Get job results"""
    try:
        job = db_manager.get_job(job_id)
        if not job:
            raise HTTPException(
                status_code=404,
                detail=get_response_message("job_not_found")
            )
        
        if job.status != "completed":
            return {
                "job_id": job_id,
                "status": job.status,
                "message": get_response_message("results_not_ready")
            }
        
        # Get products for this job
        products = db_manager.get_products_by_job(job_id)
        
        return {
            "job_id": job_id,
            "status": job.status,
            "supermercato_nome": job.supermercato_nome,
            "total_products": len(products),
            "products": [
                {
                    "id": p.id,
                    "nome": p.nome,
                    "prezzo": p.prezzo,
                    "prezzo_originale": p.prezzo_originale,
                    "sconto_percentuale": p.sconto_percentuale,
                    "quantita": p.quantita,
                    "marca": p.marca,
                    "categoria": p.categoria,
                    "image_url": p.image_path
                }
                for p in products
            ],
            "completed_at": job.completed_at.isoformat() if job.completed_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get results error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Errore interno del server: {str(e)}"
        )

# For Vercel, we need to export the app
# Supermercati endpoints
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

@app.get("/prodotti", response_model=List[Dict[str, Any]])
async def get_all_products():
    """Ottieni tutti i prodotti dal database"""
    try:
        # Recupera tutti i prodotti dal database
        products = db_manager.get_all_products()
        
        if not products:
            return []
        
        return [p.to_dict() for p in products]
        
    except Exception as e:
        logger.error(f"Errore durante recupero di tutti i prodotti: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Errore durante il recupero dei prodotti"
        )

@app.post("/supermercati", response_model=SupermercatoResponse)
async def create_supermercato(request: SupermercatoCreate):
    """Crea un nuovo supermercato"""
    try:
        # Verifica se il nome è già in uso
        existing = db_manager.get_supermercato_by_nome(request.nome)
        if existing:
            raise HTTPException(status_code=400, detail="Nome supermercato già in uso")
        
        supermercato_id = db_manager.create_supermercato(
            nome=request.nome,
            descrizione=request.descrizione,
            logo_url=request.logo_url,
            sito_web=request.sito_web,
            colore_tema=request.colore_tema
        )
        
        supermercato = db_manager.get_supermercato_by_id(supermercato_id)
        return SupermercatoResponse(**supermercato.to_dict())
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Errore durante creazione supermercato: {e}")
        raise HTTPException(status_code=500, detail="Errore interno del server")

def handler(request):
    """Vercel handler function"""
    return app

# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api_main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )