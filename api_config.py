import os
from pathlib import Path
from typing import Dict, Any

# Configurazione API
API_CONFIG = {
    "title": "OCR Volantino API",
    "description": "API per l'estrazione automatica di dati da volantini italiani usando OCR e AI",
    "version": "1.0.0",
    "host": "0.0.0.0",
    "port": 8000,
    "reload": True,
    "log_level": "info"
}

# Limiti file upload
FILE_LIMITS = {
    "max_file_size": 10 * 1024 * 1024,  # 10MB
    "allowed_extensions": [".pdf"],
    "allowed_mime_types": [
        "application/pdf"
    ]
}

# Directory di lavoro
WORK_DIRS = {
    "temp_uploads": Path("temp_uploads"),
    "processed_images": Path("processed_images"),
    "logs": Path("logs")
}

# Crea le directory se non esistono
for dir_path in WORK_DIRS.values():
    dir_path.mkdir(exist_ok=True)

# Configurazione elaborazione
PROCESSING_CONFIG = {
    "max_concurrent_jobs": 5,
    "job_timeout_seconds": 300,  # 5 minuti
    "cleanup_temp_files": True,
    "save_processed_images": False,
    "enable_detailed_logging": True
}

# Configurazione CORS
CORS_CONFIG = {
    "allow_origins": ["*"],
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"]
}

# Messaggi di risposta
RESPONSE_MESSAGES = {
    "upload_success": "File caricato con successo. Elaborazione avviata.",
    "processing_complete": "Elaborazione completata con successo",
    "processing_failed": "Errore durante l'elaborazione",
    "file_too_large": "Il file è troppo grande. Dimensione massima: {max_size}MB",
    "invalid_file_type": "Il file deve essere un PDF",
    "job_not_found": "Job non trovato",
    "results_not_ready": "Elaborazione ancora in corso. Riprova tra qualche secondo.",
    "no_products_found": "Nessun prodotto trovato per questo job"
}

# Configurazione logging
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s",
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "formatter": "detailed",
            "class": "logging.FileHandler",
            "filename": "logs/api.log",
            "mode": "a",
        },
    },
    "root": {
        "level": "INFO",
        "handlers": ["default", "file"],
    },
}

# Funzioni di utilità
def get_max_file_size_mb() -> int:
    """Restituisce la dimensione massima del file in MB"""
    return FILE_LIMITS["max_file_size"] // (1024 * 1024)

def is_allowed_file_type(filename: str, content_type: str) -> bool:
    """Verifica se il tipo di file è consentito"""
    if not filename or not content_type:
        return False
    
    # Controlla estensione
    file_ext = Path(filename).suffix.lower()
    if file_ext not in FILE_LIMITS["allowed_extensions"]:
        return False
    
    # Controlla MIME type
    if content_type not in FILE_LIMITS["allowed_mime_types"]:
        return False
    
    return True

def get_response_message(key: str, **kwargs) -> str:
    """Ottiene un messaggio di risposta formattato"""
    message = RESPONSE_MESSAGES.get(key, "Messaggio non trovato")
    return message.format(**kwargs)

# Configurazione ambiente
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = ENVIRONMENT == "development"

# Configurazione database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ocr_volantino.db")

# Railway PostgreSQL URL fix (rimuove postgresql:// e aggiunge postgresql+psycopg2://)
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

DATABASE_CONFIG = {
    "url": DATABASE_URL,
    "echo": DEBUG,
    "pool_size": 10,
    "max_overflow": 20
}

# Configurazione Redis (per future implementazioni)
REDIS_CONFIG = {
    "url": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    "decode_responses": True,
    "socket_timeout": 5,
    "socket_connect_timeout": 5
}

# Configurazione autenticazione (per future implementazioni)
AUTH_CONFIG = {
    "secret_key": os.getenv("SECRET_KEY", "your-secret-key-here"),
    "algorithm": "HS256",
    "access_token_expire_minutes": 30,
    "enable_auth": os.getenv("ENABLE_AUTH", "false").lower() == "true"
}

# Rate limiting (per future implementazioni)
RATE_LIMIT_CONFIG = {
    "requests_per_minute": 60,
    "requests_per_hour": 1000,
    "enable_rate_limiting": os.getenv("ENABLE_RATE_LIMITING", "false").lower() == "true"
}