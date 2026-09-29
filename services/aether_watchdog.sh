#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 🤖 AETHER Watchdog — مراقب يعمل 24/24
# يفحص المشروع كل ساعة ويُصلح المشاكل تلقائيًا
# ═══════════════════════════════════════════════════════════════

PROJECT_DIR="$HOME/AETHER_V8/integrations/generic_agent"
VENV_DIR="$HOME/AETHER_V8/.venv"
LOG_DIR="$HOME/AETHER_V8/logs"
LOG_FILE="$LOG_DIR/watchdog_$(date +%Y%m%d).log"

mkdir -p "$LOG_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "═══════════════════════════════════════════════"
log "🤖 AETHER Watchdog بدأ"
log "═══════════════════════════════════════════════"

# تفعيل البيئة
cd "$PROJECT_DIR" || exit 1
source "$VENV_DIR/bin/activate" || exit 1

# ═══════════════════════════════════════════════
# 1) تشغيل روبوت التشخيص
# ═══════════════════════════════════════════════
log "▶ تشغيل روبوت التشخيص..."
python diagnose_robot.py 2>&1 | tee -a "$LOG_FILE"

# ═══════════════════════════════════════════════
# 2) إصلاحات تلقائية
# ═══════════════════════════════════════════════

# إصلاح hub.pyw إذا لزم
if grep -q "SystemButtonFace" hub.pyw 2>/dev/null; then
    log "🔧 إصلاح hub.pyw..."
    sed -i "s/SystemButtonFace/#f0f0f0/g" hub.pyw
fi

# التحقق من mykey.py
if diff -q mykey.py mykey_template.py > /dev/null 2>&1; then
    log "⚠️  mykey.py لم يُعدّل — يحتاج مفاتيح API"
fi

# ═══════════════════════════════════════════════
# 3) فحص الحزم المفقودة
# ═══════════════════════════════════════════════
log "▶ فحص الحزم..."
pip check 2>&1 | tee -a "$LOG_FILE" || log "⚠️  بعض الحزم بها تعارضات"

log "✅ انتهت الدورة"
log ""
python diagnose_robot.py >> "$LOG_FILE" 2>&1
pip check >> "$LOG_FILE" 2>&1
