# 🤖 OCR Volantino - Estrattore Prodotti

Sistema automatico per l'estrazione di prodotti da volantini PDF utilizzando OCR (Optical Character Recognition) e intelligenza artificiale gratuita.

## 🎯 Caratteristiche

- **OCR Avanzato**: Utilizza Tesseract con preprocessing delle immagini
- **AI Gratuita**: Integrazione con Hugging Face Transformers
- **Estrazione Completa**: Nome prodotto, prezzo e immagine
- **Categorizzazione Automatica**: Classifica i prodotti per categoria
- **Export JSON**: Salva tutti i dati in formato strutturato
- **Supporto GPU**: Accelerazione hardware opzionale

## 📋 Requisiti di Sistema

### Software Necessario

1. **Python 3.8+**
2. **Tesseract OCR**
   ```bash
   # macOS
   brew install tesseract tesseract-lang
   
   # Ubuntu/Debian
   sudo apt-get install tesseract-ocr tesseract-ocr-ita
   
   # Windows
   # Scarica da: https://github.com/UB-Mannheim/tesseract/wiki
   ```

3. **Poppler** (per conversione PDF)
   ```bash
   # macOS
   brew install poppler
   
   # Ubuntu/Debian
   sudo apt-get install poppler-utils
   
   # Windows
   # Scarica da: https://poppler.freedesktop.org/
   ```

## 🚀 Installazione

1. **Clona o scarica il progetto**
   ```bash
   cd ocr-volantino
   ```

2. **Crea ambiente virtuale** (raccomandato)
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   # oppure
   venv\Scripts\activate     # Windows
   ```

3. **Installa le dipendenze**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configura l'ambiente** (opzionale)
   ```bash
   cp .env.example .env
   # Modifica .env con le tue configurazioni
   ```

## 💻 Utilizzo

### Utilizzo Base

```bash
# Estrae prodotti dal volantino Top Supermercati
python main.py
```

### Utilizzo Avanzato

```bash
# Specifica URL personalizzato
python main.py --url "https://esempio.com/volantino.pdf"

# Cambia nome file output
python main.py --output "miei_prodotti.json"

# Abilita GPU (se disponibile)
python main.py --gpu

# Modalità debug
python main.py --debug

# Combinazione di opzioni
python main.py --url "https://esempio.com/volantino.pdf" --output "prodotti_custom.json" --gpu --debug
```

### Script Alternativi

```bash
# OCR base (senza AI)
python ocr_volantino.py

# OCR con AI avanzata
python ai_enhanced_ocr.py
```

## 📊 Output

Il sistema genera un file JSON con la seguente struttura:

```json
{
  "metadata": {
    "volantino_url": "https://www.topsupermercati.it/volantino.pdf",
    "data_estrazione": "2024-01-15T10:30:00",
    "numero_prodotti": 45,
    "valore_totale": 234.56,
    "prezzo_medio": 5.21,
    "categorie": {
      "Frutta e Verdura": 12,
      "Carne e Pesce": 8,
      "Latticini": 6
    },
    "metodo_estrazione": "AI Enhanced OCR"
  },
  "prodotti": [
    {
      "nome": "Mele Golden",
      "prezzo": "2.50€",
      "prezzo_numerico": 2.5,
      "immagine_base64": "iVBORw0KGgoAAAANSUhEUgAA...",
      "confidence": 0.85,
      "categoria": "Frutta e Verdura",
      "descrizione": "Mele Golden offerta speciale"
    }
  ]
}
```

## 🔧 Configurazione

### File .env

```env
# GPU Support
USE_GPU=false

# API Keys (opzionali)
OPENAI_API_KEY=your_key_here
HUGGINGFACE_API_KEY=your_key_here

# Debug
DEBUG=false
LOG_LEVEL=INFO
```

### Personalizzazione Categorie

Modifica il file `config.py` per aggiungere nuove categorie:

```python
CATEGORIES = {
    "nuova_categoria": {
        "keywords": ["parola1", "parola2"],
        "display_name": "Nuova Categoria"
    }
}
```

## 🐛 Risoluzione Problemi

### Errori Comuni

1. **Tesseract non trovato**
   ```bash
   # Verifica installazione
   tesseract --version
   
   # Se necessario, specifica il percorso in .env
   TESSERACT_CMD=/usr/local/bin/tesseract
   ```

2. **Errore conversione PDF**
   ```bash
   # Verifica Poppler
   pdftoppm -h
   
   # Installa se mancante
   brew install poppler  # macOS
   ```

3. **Memoria insufficiente**
   ```bash
   # Riduci DPI in config.py
   OCR_DPI = 200  # invece di 300
   ```

4. **Nessun prodotto estratto**
   - Verifica che il PDF contenga testo (non solo immagini)
   - Prova con `--debug` per vedere i dettagli
   - Controlla le immagini di debug in `output/`

### Log e Debug

```bash
# Abilita logging dettagliato
python main.py --debug

# Controlla i log
tail -f ocr_volantino.log

# Verifica immagini di debug
ls output/debug_page_*.png
```

## 📁 Struttura del Progetto

```
ocr-volantino/
├── main.py                 # Script principale
├── ai_enhanced_ocr.py      # OCR con AI avanzata
├── ocr_volantino.py        # OCR base
├── config.py               # Configurazioni
├── requirements.txt        # Dipendenze Python
├── .env.example           # Esempio configurazione
├── README.md              # Questa documentazione
├── output/                # File di output
│   ├── prodotti_*.json    # Risultati JSON
│   └── debug_page_*.png   # Immagini debug
└── temp/                  # File temporanei
```

## 🤝 Contributi

I contributi sono benvenuti! Per contribuire:

1. Fai un fork del progetto
2. Crea un branch per la tua feature
3. Committa le modifiche
4. Apri una Pull Request

## 📄 Licenza

Questo progetto è rilasciato sotto licenza MIT. Vedi il file LICENSE per i dettagli.

## 🆘 Supporto

Per problemi o domande:

1. Controlla la sezione "Risoluzione Problemi"
2. Verifica i log con `--debug`
3. Apri una issue su GitHub

## 🔮 Roadmap

- [ ] Supporto per più formati (DOCX, HTML)
- [ ] Interfaccia web
- [ ] API REST
- [ ] Miglioramento accuratezza AI
- [ ] Supporto per più lingue
- [ ] Integrazione con database

---

**Sviluppato con ❤️ per automatizzare l'estrazione di prodotti da volantini**