#!/bin/bash
# Script per configurare il cleanup automatico come cron job

# Ottieni il percorso assoluto della directory corrente
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLEANUP_SCRIPT="$SCRIPT_DIR/auto_cleanup_jobs.py"

echo "🔧 Configurazione cleanup automatico per OCR Volantino..."
echo "📁 Directory: $SCRIPT_DIR"
echo "🐍 Script: $CLEANUP_SCRIPT"

# Verifica che lo script esista
if [ ! -f "$CLEANUP_SCRIPT" ]; then
    echo "❌ Errore: Script auto_cleanup_jobs.py non trovato!"
    exit 1
fi

# Rendi eseguibile lo script
chmod +x "$CLEANUP_SCRIPT"

# Crea il comando cron
CRON_COMMAND="*/10 * * * * cd $SCRIPT_DIR && /usr/bin/python3 $CLEANUP_SCRIPT >> $SCRIPT_DIR/auto_cleanup.log 2>&1"

echo ""
echo "📋 Comando cron da aggiungere:"
echo "$CRON_COMMAND"
echo ""

# Controlla se il cron job esiste già
if crontab -l 2>/dev/null | grep -q "auto_cleanup_jobs.py"; then
    echo "⚠️ Cron job già configurato. Rimuovo quello esistente..."
    crontab -l 2>/dev/null | grep -v "auto_cleanup_jobs.py" | crontab -
fi

# Aggiungi il nuovo cron job
echo "➕ Aggiunta cron job..."
(crontab -l 2>/dev/null; echo "$CRON_COMMAND") | crontab -

# Verifica che sia stato aggiunto
if crontab -l 2>/dev/null | grep -q "auto_cleanup_jobs.py"; then
    echo "✅ Cron job configurato con successo!"
    echo ""
    echo "🕐 Il cleanup automatico verrà eseguito ogni 10 minuti"
    echo "📝 I log saranno salvati in: $SCRIPT_DIR/auto_cleanup.log"
    echo ""
    echo "📋 Per vedere i cron job attivi:"
    echo "   crontab -l"
    echo ""
    echo "📋 Per rimuovere il cron job:"
    echo "   crontab -l | grep -v auto_cleanup_jobs.py | crontab -"
    echo ""
    echo "🧪 Per testare manualmente:"
    echo "   cd $SCRIPT_DIR && python3 auto_cleanup_jobs.py"
else
    echo "❌ Errore nella configurazione del cron job!"
    exit 1
fi

echo ""
echo "🎉 Configurazione completata!"