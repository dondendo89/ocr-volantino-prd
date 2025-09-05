#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configurazione ottimizzazioni per sistema Multi-AI
Gestisce chiavi API multiple e parametri di performance
"""

import os
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class OptimizationConfig:
    """
    Configurazione centralizzata per ottimizzazioni
    """
    
    def __init__(self):
        # Chiavi API Gemini
        self.gemini_key_1 = os.getenv('GEMINI_API_KEY')
        self.gemini_key_2 = os.getenv('GEMINI_API_KEY_2')
        
        # Parametri rate limiting
        self.max_retry_attempts = 3
        self.base_wait_time = 5  # secondi
        self.max_wait_time = 30  # secondi (ridotto da 60)
        self.exponential_base = 2
        
        # Parametri timeout
        self.api_timeout = 60  # secondi per chiamata API
        self.total_timeout = 300  # secondi per job completo
        
        # Configurazione fallback
        self.enable_moondream_fallback = True
        self.enable_qwen_fallback = True
        self.fallback_on_rate_limit = True
        
        # Parametri performance
        self.concurrent_requests = 2 if self.gemini_key_2 else 1
        self.batch_size = 5  # immagini per batch
        
        # Log configurazione
        self._log_configuration()
    
    def _log_configuration(self):
        """Log della configurazione corrente"""
        logger.info("🔧 Configurazione Ottimizzazioni:")
        logger.info(f"   📊 Chiavi Gemini: {self.get_key_count()}")
        logger.info(f"   ⚡ Richieste concorrenti: {self.concurrent_requests}")
        logger.info(f"   ⏱️ Timeout API: {self.api_timeout}s")
        logger.info(f"   🔄 Max retry: {self.max_retry_attempts}")
        logger.info(f"   🛡️ Fallback abilitato: {self.enable_moondream_fallback}")
    
    def get_key_count(self) -> int:
        """Restituisce il numero di chiavi API disponibili"""
        count = 1 if self.gemini_key_1 else 0
        count += 1 if self.gemini_key_2 else 0
        return count
    
    def get_api_keys(self) -> list:
        """Restituisce lista delle chiavi API disponibili"""
        keys = []
        if self.gemini_key_1:
            keys.append(self.gemini_key_1)
        if self.gemini_key_2:
            keys.append(self.gemini_key_2)
        return keys
    
    def get_wait_time(self, attempt: int) -> int:
        """Calcola tempo di attesa per retry con exponential backoff"""
        wait_time = self.base_wait_time * (self.exponential_base ** attempt)
        return min(wait_time, self.max_wait_time)
    
    def should_use_fallback(self, error_type: str) -> bool:
        """Determina se usare fallback basato sul tipo di errore"""
        if error_type == "rate_limit":
            return self.fallback_on_rate_limit and self.get_key_count() == 1
        elif error_type == "api_error":
            return self.enable_moondream_fallback
        elif error_type == "timeout":
            return self.enable_moondream_fallback
        return False
    
    def get_extractor_config(self) -> Dict[str, Any]:
        """Restituisce configurazione per MultiAIExtractor"""
        return {
            'gemini_api_key': self.gemini_key_1,
            'gemini_api_key_2': self.gemini_key_2,
            'enable_fallback': self.enable_moondream_fallback,
            'max_retry_attempts': self.max_retry_attempts,
            'api_timeout': self.api_timeout
        }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Restituisce statistiche di performance attese"""
        base_time = 60  # secondi base per estrazione
        
        if self.get_key_count() >= 2:
            estimated_time = base_time * 0.6  # 40% miglioramento
            success_rate = 0.95
        else:
            estimated_time = base_time
            success_rate = 0.85
        
        return {
            'estimated_time_seconds': estimated_time,
            'success_rate': success_rate,
            'optimization_level': 'high' if self.get_key_count() >= 2 else 'standard',
            'concurrent_requests': self.concurrent_requests,
            'fallback_available': self.enable_moondream_fallback
        }
    
    def validate_configuration(self) -> Dict[str, bool]:
        """Valida la configurazione corrente"""
        validation = {
            'has_primary_key': bool(self.gemini_key_1),
            'has_secondary_key': bool(self.gemini_key_2),
            'fallback_enabled': self.enable_moondream_fallback,
            'timeouts_reasonable': self.api_timeout <= 120,
            'retry_count_reasonable': 1 <= self.max_retry_attempts <= 5
        }
        
        all_valid = all(validation.values())
        
        if all_valid:
            logger.info("✅ Configurazione validata con successo")
        else:
            logger.warning("⚠️ Problemi nella configurazione rilevati")
            for key, valid in validation.items():
                if not valid:
                    logger.warning(f"   ❌ {key}: {valid}")
        
        return validation
    
    @classmethod
    def create_optimized_config(cls, gemini_key_2: Optional[str] = None) -> 'OptimizationConfig':
        """Crea configurazione ottimizzata con chiave secondaria"""
        if gemini_key_2:
            os.environ['GEMINI_API_KEY_2'] = gemini_key_2
        
        config = cls()
        config.validate_configuration()
        return config
    
    def export_env_template(self) -> str:
        """Esporta template per file .env"""
        template = f"""
# Configurazione ottimizzazioni Multi-AI
# Copia questo contenuto in un file .env

# Chiavi API Gemini (richiesta almeno la prima)
GEMINI_API_KEY={self.gemini_key_1}
GEMINI_API_KEY_2=  # Inserisci qui la seconda chiave per ottimizzazioni

# Parametri performance (opzionali)
API_TIMEOUT={self.api_timeout}
MAX_RETRY_ATTEMPTS={self.max_retry_attempts}
MAX_WAIT_TIME={self.max_wait_time}

# Fallback (opzionali)
ENABLE_MOONDREAM_FALLBACK={self.enable_moondream_fallback}
ENABLE_QWEN_FALLBACK={self.enable_qwen_fallback}
"""
        return template.strip()

# Istanza globale di configurazione
optimization_config = OptimizationConfig()

def get_optimization_config() -> OptimizationConfig:
    """Restituisce l'istanza di configurazione globale"""
    return optimization_config

def set_second_gemini_key(key: str) -> bool:
    """Imposta la seconda chiave Gemini"""
    try:
        os.environ['GEMINI_API_KEY_2'] = key
        global optimization_config
        optimization_config = OptimizationConfig()
        logger.info("✅ Seconda chiave Gemini configurata")
        return True
    except Exception as e:
        logger.error(f"❌ Errore configurazione seconda chiave: {e}")
        return False

if __name__ == "__main__":
    # Test configurazione
    print("🔧 Test Configurazione Ottimizzazioni")
    print("=" * 50)
    
    config = OptimizationConfig()
    
    print("\n📊 Statistiche Performance:")
    stats = config.get_performance_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    print("\n🔍 Validazione:")
    validation = config.validate_configuration()
    
    print("\n📝 Template .env:")
    print(config.export_env_template())