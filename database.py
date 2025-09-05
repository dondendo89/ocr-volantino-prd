from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timedelta
import uuid
import os
import traceback
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
    supermercato_id = Column(Integer, ForeignKey("supermercati.id"), nullable=False)  # Foreign key verso supermercati
    supermercato_nome = Column(String, nullable=False)  # Nome del supermercato (mantenuto per compatibilità)
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
    
    # Relazione con il supermercato
    supermercato = relationship("Supermercato", back_populates="jobs")
    
    def to_dict(self):
        return {
            "job_id": self.id,
            "filename": self.filename,
            "supermercato_nome": self.supermercato_nome,
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
    image_url = Column(String)  # URL dell'immagine del prodotto
    
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
            "id": self.id,
            "nome": self.nome,
            "prezzo": self.prezzo,
            "prezzo_originale": self.prezzo_originale,
            "sconto_percentuale": self.sconto_percentuale,
            "quantita": self.quantita,
            "marca": self.marca,
            "categoria": self.categoria,
            "image_url": self.image_url,
            "posizione": posizione,
            "confidence_score": self.confidence_score,
            "extracted_at": self.extracted_at.isoformat() if self.extracted_at else None,
            "job_id": self.job_id
        }

# Modello per i Supermercati
class Supermercato(Base):
    __tablename__ = "supermercati"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    nome = Column(String, nullable=False, unique=True)  # Nome univoco del supermercato
    descrizione = Column(Text)  # Descrizione del supermercato
    logo_url = Column(String)  # URL del logo
    sito_web = Column(String)  # Sito web ufficiale
    colore_tema = Column(String, default="#3498db")  # Colore tema per l'interfaccia
    attivo = Column(String, default="true")  # Se il supermercato è attivo
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relazione con i job di elaborazione
    jobs = relationship("ProcessingJob", back_populates="supermercato", cascade="all, delete-orphan")
    
    def to_dict(self, total_jobs=0):
        return {
            "id": self.id,
            "nome": self.nome,
            "descrizione": self.descrizione,
            "logo_url": self.logo_url,
            "sito_web": self.sito_web,
            "colore_tema": self.colore_tema,
            "attivo": self.attivo,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "total_jobs": total_jobs
        }

# Configurazione del database
class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        try:
            print("🔧 Inizializzazione DatabaseManager...")
            self.setup_database()
            print("✅ DatabaseManager inizializzato con successo")
        except Exception as e:
            print(f"❌ Errore durante inizializzazione DatabaseManager: {e}")
            print(f"❌ Traceback: {traceback.format_exc()}")
            raise
    
    def setup_database(self):
        """Configura la connessione al database"""
        database_url = DATABASE_CONFIG["url"]
        print(f"🔧 Configurando database con URL: {database_url[:50]}...")
        
        # Per SQLite, assicuriamoci che la directory esista
        if database_url.startswith("sqlite"):
            db_path = database_url.replace("sqlite:///", "")
            db_dir = os.path.dirname(db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            print(f"📁 Database SQLite configurato: {db_path}")
        elif database_url.startswith("postgresql"):
            print(f"🐘 Database PostgreSQL configurato")
        
        try:
            # Parametri aggiuntivi per PostgreSQL SSL
            engine_kwargs = {
                "echo": DATABASE_CONFIG["echo"],
                "pool_size": DATABASE_CONFIG.get("pool_size", 10),
                "max_overflow": DATABASE_CONFIG.get("max_overflow", 20)
            }
            
            # Aggiungi parametri SSL per PostgreSQL
            if database_url.startswith("postgresql"):
                engine_kwargs.update({
                    "connect_args": {
                        "sslmode": "require",
                        "connect_timeout": 30,
                        "application_name": "ocr-volantino-api"
                    },
                    "pool_pre_ping": True,
                    "pool_recycle": 3600  # Ricrea connessioni ogni ora
                })
            
            self.engine = create_engine(database_url, **engine_kwargs)
            print(f"✅ Engine database creato con successo")
            
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            print(f"✅ SessionLocal configurato")
            
            # Crea le tabelle
            Base.metadata.create_all(bind=self.engine)
            print(f"✅ Tabelle database create/verificate")
        except Exception as e:
            print(f"❌ Errore durante setup database: {e}")
            raise
    
    def get_session(self):
        """Ottiene una sessione del database"""
        return self.SessionLocal()
    
    def create_job(self, filename: str, file_path: str, supermercato_nome: str) -> ProcessingJob:
        """Crea un nuovo job di elaborazione"""
        session = self.get_session()
        try:
            # Trova o crea il supermercato
            supermercato = session.query(Supermercato).filter(Supermercato.nome == supermercato_nome).first()
            if not supermercato:
                # Crea automaticamente il supermercato se non esiste
                supermercato = Supermercato(
                    nome=supermercato_nome,
                    descrizione=f"Supermercato {supermercato_nome}",
                    colore_tema="#3498db"
                )
                session.add(supermercato)
                session.flush()  # Per ottenere l'ID
            
            job = ProcessingJob(
                filename=filename,
                file_path=file_path,
                supermercato_id=supermercato.id,
                supermercato_nome=supermercato_nome,
                status="queued"
            )
            session.add(job)
            session.commit()
            session.refresh(job)
            return job
        except Exception as e:
            session.rollback()
            print(f"Errore durante creazione job: {e}")
            raise
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
            print(f"🔍 DEBUG: Tentativo di salvare {len(products_data)} prodotti per job {job_id}")
            products = []
            for i, product_data in enumerate(products_data):
                print(f"🔍 DEBUG: Elaborando prodotto {i+1}: {product_data.get('nome', 'NOME_MANCANTE')}")
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
                    image_url=product_data.get("image_url"),
                    posizione_x=posizione.get("x") if posizione else None,
                    posizione_y=posizione.get("y") if posizione else None,
                    posizione_width=posizione.get("width") if posizione else None,
                    posizione_height=posizione.get("height") if posizione else None,
                    confidence_score=product_data.get("confidence_score")
                )
                products.append(product)
                session.add(product)
                print(f"✅ DEBUG: Prodotto {i+1} aggiunto alla sessione")
            
            print(f"🔍 DEBUG: Eseguendo commit di {len(products)} prodotti...")
            session.commit()
            print(f"✅ DEBUG: Commit completato con successo")
            
            for product in products:
                session.refresh(product)
            print(f"✅ DEBUG: Tutti i prodotti salvati e refreshed")
            return products
        except Exception as e:
            print(f"❌ DEBUG: Errore durante salvataggio prodotti: {e}")
            session.rollback()
            raise e
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
    
    def get_all_jobs(self, limit: int = 50, offset: int = 0) -> List[dict]:
        """Recupera tutti i jobs con paginazione e li restituisce come dizionari"""
        session = self.get_session()
        try:
            jobs = session.query(ProcessingJob).order_by(
                ProcessingJob.created_at.desc()
            ).offset(offset).limit(limit).all()
            
            # Converti in dizionari mentre la sessione è ancora attiva
            jobs_data = []
            for job in jobs:
                job_dict = {
                    'id': job.id,
                    'filename': job.filename,
                    'file_path': job.file_path,
                    'supermercato_id': job.supermercato_id,
                    'supermercato_nome': job.supermercato_nome,
                    'status': job.status,
                    'progress': job.progress,
                    'message': job.message,
                    'created_at': job.created_at.isoformat() if job.created_at else None,
                    'started_at': job.started_at.isoformat() if job.started_at else None,
                    'completed_at': job.completed_at.isoformat() if job.completed_at else None,
                    'processing_time': job.processing_time,
                    'total_products': job.total_products
                }
                jobs_data.append(job_dict)
            
            session.commit()  # Commit esplicito per evitare ROLLBACK
            return jobs_data
        except Exception as e:
            session.rollback()
            print(f"Errore in get_all_jobs: {e}")
            raise
        finally:
            session.close()
    
    def get_product_by_id(self, product_id: int) -> Optional[ExtractedProduct]:
        """Recupera un prodotto per ID"""
        session = self.get_session()
        try:
            return session.query(ExtractedProduct).filter(
                ExtractedProduct.id == product_id
            ).first()
        finally:
            session.close()
    
    def update_product(self, product_id: int, update_data: dict) -> bool:
        """Aggiorna un prodotto"""
        session = self.get_session()
        try:
            product = session.query(ExtractedProduct).filter(
                ExtractedProduct.id == product_id
            ).first()
            
            if not product:
                return False
            
            # Aggiorna i campi forniti
            for field, value in update_data.items():
                if hasattr(product, field):
                    setattr(product, field, value)
            
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Errore durante aggiornamento prodotto {product_id}: {e}")
            return False
        finally:
            session.close()
    
    def delete_product(self, product_id: int) -> bool:
        """Elimina un prodotto"""
        session = self.get_session()
        try:
            product = session.query(ExtractedProduct).filter(
                ExtractedProduct.id == product_id
            ).first()
            
            if not product:
                return False
            
            session.delete(product)
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Errore durante eliminazione prodotto {product_id}: {e}")
            return False
        finally:
            session.close()
    
    def delete_all_products(self) -> dict:
        """Elimina tutti i prodotti dal database"""
        session = self.get_session()
        try:
            # Conta i prodotti prima dell'eliminazione
            count = session.query(ExtractedProduct).count()
            
            # Elimina tutti i prodotti
            deleted = session.query(ExtractedProduct).delete()
            session.commit()
            
            return {
                "success": True,
                "deleted_count": deleted,
                "message": f"Eliminati {deleted} prodotti dal database"
            }
        except Exception as e:
            session.rollback()
            print(f"Errore durante eliminazione di tutti i prodotti: {e}")
            return {
                "success": False,
                "deleted_count": 0,
                "message": f"Errore: {str(e)}"
            }
        finally:
            session.close()
    
    def create_job_with_id(self, job_id: str, filename: str, supermercato_nome: str, status: str = "queued") -> ProcessingJob:
        """Crea un nuovo job con job_id personalizzato"""
        session = self.get_session()
        try:
            # Trova o crea il supermercato
            supermercato = session.query(Supermercato).filter(Supermercato.nome == supermercato_nome).first()
            if not supermercato:
                # Crea automaticamente il supermercato se non esiste
                supermercato = Supermercato(
                    nome=supermercato_nome,
                    descrizione=f"Supermercato {supermercato_nome}",
                    colore_tema="#3498db"
                )
                session.add(supermercato)
                session.flush()  # Per ottenere l'ID
            
            job = ProcessingJob(
                id=job_id,
                filename=filename,
                file_path="",  # Sarà aggiornato dopo
                supermercato_id=supermercato.id,
                supermercato_nome=supermercato_nome,
                status=status
            )
            session.add(job)
            session.commit()
            session.refresh(job)
            return job
        except Exception as e:
            session.rollback()
            print(f"Errore durante creazione job {job_id}: {e}")
            raise
        finally:
            session.close()
    
    # Metodi CRUD per Supermercati
    def create_supermercato(self, nome: str, descrizione: str = None, logo_url: str = None, 
                           sito_web: str = None, colore_tema: str = "#3498db") -> Supermercato:
        """Crea un nuovo supermercato"""
        session = self.get_session()
        try:
            supermercato = Supermercato(
                nome=nome,
                descrizione=descrizione,
                logo_url=logo_url,
                sito_web=sito_web,
                colore_tema=colore_tema
            )
            session.add(supermercato)
            session.commit()
            session.refresh(supermercato)
            
            # Crea una copia detached per evitare lazy loading errors
            supermercato_dict = {
                'id': supermercato.id,
                'nome': supermercato.nome,
                'descrizione': supermercato.descrizione,
                'logo_url': supermercato.logo_url,
                'sito_web': supermercato.sito_web,
                'colore_tema': supermercato.colore_tema,
                'attivo': supermercato.attivo,
                'created_at': supermercato.created_at,
                'updated_at': supermercato.updated_at
            }
            
            # Crea un nuovo oggetto detached
            detached_supermercato = Supermercato(**supermercato_dict)
            detached_supermercato.id = supermercato.id
            
            return detached_supermercato
        except Exception as e:
            session.rollback()
            print(f"Errore durante creazione supermercato {nome}: {e}")
            raise
        finally:
            session.close()
    
    def get_all_supermercati(self) -> List[Supermercato]:
        """Ottiene tutti i supermercati con il conteggio dei job"""
        session = self.get_session()
        try:
            supermercati = session.query(Supermercato).filter(Supermercato.attivo == "true").order_by(Supermercato.nome).all()
            result = []
            for s in supermercati:
                # Conta i job per questo supermercato
                job_count = session.query(ProcessingJob).filter(ProcessingJob.supermercato_id == s.id).count()
                # Crea oggetto detached con total_jobs
                supermercato_dict = {
                    'id': s.id,
                    'nome': s.nome,
                    'descrizione': s.descrizione,
                    'logo_url': s.logo_url,
                    'sito_web': s.sito_web,
                    'colore_tema': s.colore_tema,
                    'attivo': s.attivo,
                    'created_at': s.created_at,
                    'updated_at': s.updated_at
                }
                detached_s = Supermercato(**supermercato_dict)
                detached_s.id = s.id
                detached_s._total_jobs = job_count  # Salva il conteggio
                result.append(detached_s)
            return result
        finally:
            session.close()
    
    def get_supermercato_by_id(self, supermercato_id: int) -> Optional[Supermercato]:
        """Ottiene un supermercato per ID"""
        session = self.get_session()
        try:
            return session.query(Supermercato).filter(Supermercato.id == supermercato_id).first()
        finally:
            session.close()
    
    def get_supermercato_by_nome(self, nome: str) -> Optional[Supermercato]:
        """Ottiene un supermercato per nome"""
        session = self.get_session()
        try:
            return session.query(Supermercato).filter(Supermercato.nome == nome).first()
        finally:
            session.close()
    
    def update_supermercato(self, supermercato_id: int, update_data: dict) -> bool:
        """Aggiorna un supermercato"""
        session = self.get_session()
        try:
            supermercato = session.query(Supermercato).filter(Supermercato.id == supermercato_id).first()
            if not supermercato:
                return False
            
            for key, value in update_data.items():
                if hasattr(supermercato, key):
                    setattr(supermercato, key, value)
            
            supermercato.updated_at = datetime.utcnow()
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Errore durante aggiornamento supermercato {supermercato_id}: {e}")
            return False
        finally:
            session.close()
    
    def delete_supermercato(self, supermercato_id: int) -> bool:
        """Elimina (disattiva) un supermercato"""
        session = self.get_session()
        try:
            supermercato = session.query(Supermercato).filter(Supermercato.id == supermercato_id).first()
            if not supermercato:
                return False
            
            # Disattiva invece di eliminare per mantenere l'integrità referenziale
            supermercato.attivo = "false"
            supermercato.updated_at = datetime.utcnow()
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            print(f"Errore durante eliminazione supermercato {supermercato_id}: {e}")
            return False
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