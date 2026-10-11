// ESPRIEAETHER — core UI script
(function () {
  // Clock
  function tickClock() {
    const el = document.getElementById("clock");
    if (el) el.textContent = new Date().toLocaleTimeString("en-GB");
  }
  setInterval(tickClock, 1000);
  tickClock();

  // Ollama status dot
  async function refreshOllama() {
    try {
      const r = await fetch("/api/ollama");
      const d = await r.json();
      const dot = document.getElementById("ollama-dot");
      const txt = document.getElementById("ollama-status-text");
      if (!dot || !txt) return;
      const online = d && (d.status === "online" || d.ollama === "online");
      dot.style.background = online ? "#22c55e" : "#ef4444";
      txt.textContent = online ? "JARVIS online" : "JARVIS offline";
    } catch (e) {
      const dot = document.getElementById("ollama-dot");
      if (dot) dot.style.background = "#ef4444";
      const txt = document.getElementById("ollama-status-text");
      if (txt) txt.textContent = "JARVIS offline";
    }
  }
  refreshOllama();
  setInterval(refreshOllama, 15000);
})();
