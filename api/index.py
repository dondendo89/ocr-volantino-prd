from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import os
from datetime import datetime

# Configurazione semplificata per Vercel
app = FastAPI(
    title="OCR Volantino API",
    description="API semplificata per OCR di volantini",
    version="1.0.0"
)

# Configurazione CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class HealthResponse(BaseModel):
    status: str
    message: str
    timestamp: datetime
    environment: str

@app.get("/")
async def root():
    return {
        "message": "OCR Volantino API - Versione Vercel",
        "status": "active",
        "timestamp": datetime.now().isoformat(),
        "docs": "/docs"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        message="API funzionante correttamente",
        timestamp=datetime.now(),
        environment="vercel"
    )

@app.get("/api/status")
async def api_status():
    return {
        "api_version": "1.0.0",
        "platform": "vercel",
        "status": "operational",
        "timestamp": datetime.now().isoformat()
    }

# Handler per Vercel - deve essere una funzione ASGI
def handler(scope, receive, send):
    return app(scope, receive, send)