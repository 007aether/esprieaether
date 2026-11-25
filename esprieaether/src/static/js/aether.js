// ESPRIEAETHER — core UI script
(function () {
  // Clock
  function tickClock() {
    const el = document.getElementById("clock");
    if (el) el.textContent = new Date().toLocaleTimeString("en-GB");
  }
  setInterval(tickClock, 1000);
  tickClock();

  // Local-first status dot: lit when the robot reports are readable and a brain is active.
  async function refreshLocalStatus() {
    const dot = document.getElementById("ollama-dot");
    const txt = document.getElementById("ollama-status-text");
    if (!dot || !txt) return;
    try {
      const r = await fetch("/api/local/status");
      const d = await r.json();
      const online = Boolean(d && d.available && d.brains && d.brains.count > 0);
      dot.style.background = online ? "#22c55e" : "#ef4444";
      txt.textContent = online
        ? `Local Brain ${d.brains.count} · ${d.brains.active || d.brains.provider || "actif"}`
        : "Local Brain indisponible";
    } catch (e) {
      dot.style.background = "#ef4444";
      txt.textContent = "Rapports indisponibles";
    }
  }
  refreshLocalStatus();
  setInterval(refreshLocalStatus, 15000);
})();
