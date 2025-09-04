from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import os
from typing import List, Optional
from api_config import DATABASE_CONFIG

# Base per i modelli
Base = declarative_base()

# Modello per i Job di elaborazione
class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    status = Column(String, nullable=False, default="queued")  # queued, processing, completed, failed
    progress = Column(Integer, default=0)
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    processing_time = Column(Float)  # in secondi
    total_products = Column(Integer, default=0)
    
    # Relazione con i prodotti estratti
    products = relationship("ExtractedProduct", back_populates="job", cascade="all, delete-orphan")
    
    def to_dict(self):
        return {
            "job_id": self.id,
            "filename": self.filename,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "processing_time": self.processing_time,
            "total_products": self.total_products
        }

# Modello per i prodotti estratti
class ExtractedProduct(Base):
    __tablename__ = "extracted_products"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey("processing_jobs.id"), nullable=False)
    
    # Dati del prodotto
    nome = Column(String, nullable=False)
    prezzo = Column(Float)
    prezzo_originale = Column(Float)
    sconto_percentuale = Column(Float)
    quantita = Column(String)
    marca = Column(String)
    categoria = Column(String)
    
    # Posizione nell'immagine
    posizione_x = Column(Integer)
    posizione_y = Column(Integer)
    posizione_width = Column(Integer)
    posizione_height = Column(Integer)
    
    # Metadati
    confidence_score = Column(Float)  # Livello di confidenza dell'estrazione
    extracted_at = Column(DateTime, default=datetime.utcnow)
    
    # Relazione con il job
    job = relationship("ProcessingJob", back_populates="products")
    
    def to_dict(self):
        posizione = None
        if all([self.posizione_x is not None, self.posizione_y is not None, 
                self.posizione_width is not None, self.posizione_height is not None]):
            posizione = {
                "x": self.posizione_x,
                "y": self.posizione_y,
                "width": self.posizione_width,
                "height": self.posizione_height
            }
        
        return {
            "nome": self.nome,
            "prezzo": self.prezzo,
            "prezzo_originale": self.prezzo_originale,
            "sconto_percentuale": self.sconto_percentuale,
            "quantita": self.quantita,
            "marca": self.marca,
            "categoria": self.categoria,
            "posizione": posizione,
            "confidence_score": self.confidence_score,
            "extracted_at": self.extracted_at.isoformat() if self.extracted_at else None
        }

# Configurazione del database
class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self.setup_database()
    
    def setup_database(self):
        """Configura la connessione al database"""
        database_url = DATABASE_CONFIG["url"]
        
        # Per SQLite, assicuriamoci che la directory esista
        if database_url.startswith("sqlite"):
            db_path = database_url.replace("sqlite:///", "")
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
        
        self.engine = create_engine(
            database_url,
            echo=DATABASE_CONFIG["echo"],
            pool_size=DATABASE_CONFIG.get("pool_size", 10),
            max_overflow=DATABASE_CONFIG.get("max_overflow", 20)
        )
        
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Crea le tabelle
        Base.metadata.create_all(bind=self.engine)
    
    def get_session(self):
        """Ottiene una sessione del database"""
        return self.SessionLocal()
    
    def create_job(self, filename: str, file_path: str) -> ProcessingJob:
        """Crea un nuovo job di elaborazione"""
        session = self.get_session()
        try:
            job = ProcessingJob(
                filename=filename,
                file_path=file_path,
                status="queued"
            )
            session.add(job)
            session.commit()
            session.refresh(job)
            return job
        finally:
            session.close()
    
    def update_job_status(self, job_id: str, status: str, progress: int = None, 
                         message: str = None, processing_time: float = None,
                         total_products: int = None) -> Optional[ProcessingJob]:
        """Aggiorna lo stato di un job"""
        session = self.get_session()
        try:
            job = session.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
            if job:
                job.status = status
                if progress is not None:
                    job.progress = progress
                if message is not None:
                    job.message = message
                if processing_time is not None:
                    job.processing_time = processing_time
                if total_products is not None:
                    job.total_products = total_products
                
                # Aggiorna i timestamp
                if status == "processing" and not job.started_at:
                    job.started_at = datetime.utcnow()
                elif status in ["completed", "failed"] and not job.completed_at:
                    job.completed_at = datetime.utcnow()
                
                session.commit()
                session.refresh(job)
                return job
            return None
        finally:
            session.close()
    
    def get_job(self, job_id: str) -> Optional[ProcessingJob]:
        """Ottiene un job per ID"""
        session = self.get_session()
        try:
            return session.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        finally:
            session.close()
    
    def save_products(self, job_id: str, products_data: List[dict]) -> List[ExtractedProduct]:
        """Salva i prodotti estratti per un job"""
        session = self.get_session()
        try:
            products = []
            for product_data in products_data:
                # Estrai posizione se presente
                posizione = product_data.get("posizione", {})
                
                product = ExtractedProduct(
                    job_id=job_id,
                    nome=product_data.get("nome", ""),
                    prezzo=product_data.get("prezzo"),
                    prezzo_originale=product_data.get("prezzo_originale"),
                    sconto_percentuale=product_data.get("sconto_percentuale"),
                    quantita=product_data.get("quantita"),
                    marca=product_data.get("marca"),
                    categoria=product_data.get("categoria"),
                    posizione_x=posizione.get("x") if posizione else None,
                    posizione_y=posizione.get("y") if posizione else None,
                    posizione_width=posizione.get("width") if posizione else None,
                    posizione_height=posizione.get("height") if posizione else None,
                    confidence_score=product_data.get("confidence_score")
                )
                products.append(product)
                session.add(product)
            
            session.commit()
            for product in products:
                session.refresh(product)
            return products
        finally:
            session.close()
    
    def get_products(self, job_id: str) -> List[ExtractedProduct]:
        """Ottiene tutti i prodotti per un job"""
        session = self.get_session()
        try:
            return session.query(ExtractedProduct).filter(ExtractedProduct.job_id == job_id).all()
        finally:
            session.close()
    
    def get_job_with_products(self, job_id: str) -> Optional[ProcessingJob]:
        """Ottiene un job con tutti i suoi prodotti"""
        session = self.get_session()
        try:
            return session.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        finally:
            session.close()
    
    def get_recent_jobs(self, limit: int = 50) -> List[ProcessingJob]:
        """Ottiene i job più recenti"""
        session = self.get_session()
        try:
            return session.query(ProcessingJob).order_by(ProcessingJob.created_at.desc()).limit(limit).all()
        finally:
            session.close()
    
    def cleanup_old_jobs(self, days: int = 30) -> int:
        """Rimuove job più vecchi di X giorni"""
        from datetime import timedelta
        
        session = self.get_session()
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            deleted_count = session.query(ProcessingJob).filter(
                ProcessingJob.created_at < cutoff_date
            ).delete()
            session.commit()
            return deleted_count
        finally:
            session.close()
    
    def get_stats(self) -> dict:
        """Ottiene statistiche del database"""
        session = self.get_session()
        try:
            total_jobs = session.query(ProcessingJob).count()
            completed_jobs = session.query(ProcessingJob).filter(ProcessingJob.status == "completed").count()
            failed_jobs = session.query(ProcessingJob).filter(ProcessingJob.status == "failed").count()
            active_jobs = session.query(ProcessingJob).filter(ProcessingJob.status.in_(["queued", "processing"])).count()
            total_products = session.query(ExtractedProduct).count()
            
            return {
                "total_jobs": total_jobs,
                "completed_jobs": completed_jobs,
                "failed_jobs": failed_jobs,
                "active_jobs": active_jobs,
                "total_products": total_products
            }
        finally:
            session.close()

# Istanza globale del database manager
db_manager = DatabaseManager()

# Funzioni di utilità per l'API
def get_db_session():
    """Dependency per FastAPI"""
    session = db_manager.get_session()
    try:
        yield session
    finally:
        session.close()