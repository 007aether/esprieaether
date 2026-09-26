// ═══════════════════════════════════════
//   ESPRIEAETHER - Shared JS
// ═══════════════════════════════════════

// الساعة الحية
function tick() {
  const el = document.getElementById('clock');
  if (el) {
    el.textContent = new Date().toLocaleTimeString('ar-EG');
  }
}
setInterval(tick, 1000); tick();

// فحص حالة Ollama كل 10 ثوان
async function checkOllama() {
  try {
    const r = await fetch('/api/ollama');
    const d = await r.json();
    const dot = document.getElementById('ollama-dot');
    const txt = document.getElementById('ollama-status-text');
    if (dot && txt) {
      if (d.status === 'online') {
        dot.className = 'status-dot online';
        txt.textContent = 'JARVIS متصل';
      } else {
        dot.className = 'status-dot offline';
        txt.textContent = 'JARVIS غير متصل';
      }
    }
  } catch(e) {}
}
checkOllama();
setInterval(checkOllama, 10000);
