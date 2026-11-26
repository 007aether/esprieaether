// Serveur statique + proxy /v1 pour l'export Next.js de G0DM0D3.
// Node stdlib uniquement — aucun npx, aucun réseau externe, loopback seulement.
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..", "G0DM0D3", "out");
const HOST = process.env.G0DM0D3_HOST || "127.0.0.1";
const PORT = Number(process.env.G0DM0D3_PORT || 3860);
const API_HOST = process.env.G0DM0D3_API_HOST || "127.0.0.1";
const API_PORT = Number(process.env.G0DM0D3_API_PORT || 7860);
const DASH_HOST = process.env.DASHBOARD_HOST || "127.0.0.1";
const DASHBOARD_PORT = Number(process.env.DASHBOARD_PORT || 5100);
const SENT_HOST = process.env.ESPRIE_SENTINEL_HOST || "127.0.0.1";
const SENT_PORT = Number(process.env.ESPRIE_SENTINEL_PORT || 8766);
const ATULYA_HOST = process.env.ATULYA_HOST || "127.0.0.1";
const ATULYA_PORT = Number(process.env.ATULYA_PORT || 8501);
const FREELLM_HOST = process.env.FREELLMAPI_HOST || "127.0.0.1";
const FREELLM_PORT = Number(process.env.FREELLMAPI_PORT || 31415);
const FREELLM_KEY_FILE = path.resolve(HERE, "..", "state", "freellmapi.key");
const SHARE_LEDGER = path.resolve(HERE, "..", "state", "model_share.jsonl");
const FRELLM_TRACE = path.resolve(HERE, "..", "state", "freellm_requests.log");

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".svg": "image/svg+xml",
  ".txt": "text/plain; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".ico": "image/x-icon",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".woff2": "font/woff2",
};

function safeTarget(urlPath) {
  let decoded;
  try {
    decoded = decodeURIComponent(urlPath.split("?")[0]);
  } catch {
    return null;
  }
  if (decoded === "/" || decoded === "") decoded = "/index.html";
  const full = path.resolve(ROOT, "." + decoded);
  if (full !== ROOT && !full.startsWith(ROOT + path.sep)) return null;
  return full;
}

function json(res, status, payload) {
  const body = JSON.stringify(payload);
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(body),
    "Cache-Control": "no-store",
  });
  res.end(body);
}

// Le frontend appelle /v1/* sur la même origine : on relaie vers le backend local.
function proxyApi(req, res) {
  const upstream = http.request(
    {
      host: API_HOST,
      port: API_PORT,
      method: req.method,
      path: req.url,
      headers: { ...req.headers, host: `${API_HOST}:${API_PORT}` },
      timeout: 15000,
    },
    (apiRes) => {
      const headers = { ...apiRes.headers };
      delete headers["access-control-allow-origin"];
      delete headers["content-length"];
      res.writeHead(apiRes.statusCode || 502, headers);
      apiRes.pipe(res);
    }
  );
  upstream.on("timeout", () => upstream.destroy(new Error("api_timeout")));
  upstream.on("error", (err) => {
    if (!res.headersSent) {
      json(res, 503, {
        error: "api_unavailable",
        reason: err.message === "api_timeout" ? "timeout" : "connection_refused",
        upstream: `${API_HOST}:${API_PORT}`,
      });
    } else {
      res.end();
    }
  });
  req.pipe(upstream);
}

// Relais local vers FreeLLMAPI : injecte la clé à l'exécution et compte les
// requêtes par consommateur dans un journal sans secret, jamais dans un log.
function loadFreeLLMKey() {
  const configured = process.env.FREELLMAPI_KEY;
  if (configured) return configured;
  try {
    return fs.readFileSync(FREELLM_KEY_FILE, "utf8").trim();
  } catch {
    return "";
  }
}

function recordShare(consumer, ok) {
  if (consumer !== "atulya" && consumer !== "claude_code") return;
  const entry = {
    ts: new Date().toISOString(),
    consumer,
    model: null,
    ok: Boolean(ok),
  };
  try {
    fs.appendFileSync(SHARE_LEDGER, JSON.stringify(entry) + "\n", "utf8");
  } catch {
    /* le journal est best-effort, jamais une raison de casser la requête */
  }
}

function shareStats() {
  const counts = { atulya: 0, claude_code: 0 };
  try {
    for (const line of fs.readFileSync(SHARE_LEDGER, "utf8").split("\n")) {
      if (!line.trim()) continue;
      try {
        const entry = JSON.parse(line);
        if (entry.consumer in counts) counts[entry.consumer] += 1;
      } catch { /* ligne partielle ignorée */ }
    }
  } catch { /* absence de journal = zéro requête */ }
  return { source: "freellm-relay", counts };
}

function proxyFreeLLM(req, res) {
  const raw = req.url || "/";
  const upstreamPath = raw.replace(/^\/freellm/, "") || "/";
  try {
    const headerNames = Object.keys(req.headers).sort().join(",");
    fs.appendFileSync(
      FRELLM_TRACE,
      `${new Date().toISOString()} ${req.method} ${upstreamPath.split("?")[0]} ` +
      `headers=${headerNames}\n`,
      "utf8"
    );
  } catch { /* trace best-effort, sans valeurs ni secrets */ }
  if (upstreamPath === "/health") {
    json(res, 200, {
      status: "ok", source: "freellm-relay",
      upstream: `${FREELLM_HOST}:${FREELLM_PORT}`,
    });
    return;
  }
  if (upstreamPath === "/stats") {
    json(res, 200, shareStats());
    return;
  }
  const explicit = req.headers["x-esprie-consumer"];
  const consumer = (explicit === "atulya" || explicit === "claude_code")
    ? explicit
    : (upstreamPath.startsWith("/v1/messages") ? "claude_code" : "atulya");
  const countable = upstreamPath.startsWith("/v1/messages")
    || upstreamPath.startsWith("/v1/chat/completions");
  const chunks = [];
  req.on("data", (chunk) => chunks.push(chunk));
  req.on("end", () => {
    let body = Buffer.concat(chunks);
    try {
      const meta = JSON.parse(body.toString("utf8"));
      fs.appendFileSync(
        FRELLM_TRACE,
        `${new Date().toISOString()} body keys=${Object.keys(meta).sort().join(",")} ` +
        `stream=${meta.stream} model=${meta.model}\n`,
        "utf8"
      );
      if (upstreamPath.startsWith("/v1/messages") && meta && typeof meta === "object") {
        // Certains champs Claude Code ne sont pas pris en charge par la passerelle
        // locale et bloquent la réponse : on les retire sans toucher au prompt.
        delete meta.thinking;
        delete meta.context_management;
        delete meta.tools;
        meta.stream = false;
        body = Buffer.from(JSON.stringify(meta), "utf8");
        fs.appendFileSync(
          FRELLM_TRACE,
          `${new Date().toISOString()} body normalized keys=${Object.keys(meta).sort().join(",")} ` +
          `stream=${meta.stream}\n`,
          "utf8"
        );
      }
    } catch { /* corps non-JSON ou trace indisponible : on continue */ }
    const key = loadFreeLLMKey();
    // En-têtes minimaux : Claude Code ajoute des en-têtes expérimentaux qui
    // font échouer la passerelle locale. Rien n'est transmis en clair.
    const headers = {
      host: `${FREELLM_HOST}:${FREELLM_PORT}`,
      "content-type": req.headers["content-type"] || "application/json",
      "anthropic-version": req.headers["anthropic-version"] || "2023-06-01",
      accept: req.headers.accept || "application/json",
    };
    headers["content-length"] = String(body.length);
    if (key) {
      headers["x-api-key"] = key;
      headers.authorization = `Bearer ${key}`;
    }
    const upstream = http.request(
      {
        host: FREELLM_HOST,
        port: FREELLM_PORT,
        method: req.method,
        path: upstreamPath,
        headers,
        timeout: 120000,
      },
      (upRes) => {
        const out = { ...upRes.headers };
        delete out["access-control-allow-origin"];
        delete out["content-length"];
        try {
          fs.appendFileSync(
            FRELLM_TRACE,
            `${new Date().toISOString()} upstream_status=${upRes.statusCode} ` +
            `type=${out["content-type"] || "-"}\n`,
            "utf8"
          );
        } catch { /* trace best-effort */ }
        res.writeHead(upRes.statusCode || 502, out);
        upRes.pipe(res);
        upRes.on("end", () => {
          if (countable) recordShare(consumer, (upRes.statusCode || 502) < 400);
        });
      }
    );
    upstream.on("timeout", () => upstream.destroy(new Error("freellm_timeout")));
    upstream.on("error", (err) => {
      if (countable) recordShare(consumer, false);
      if (!res.headersSent) {
        json(res, 503, {
          error: "freellm_unavailable",
          reason: err.message === "freellm_timeout" ? "timeout" : "connection_refused",
          upstream: `${FREELLM_HOST}:${FREELLM_PORT}`,
        });
      } else {
        res.end();
      }
    });
    upstream.end(body);
  });
}

// Le HUD /jarvis.html lit l'API SUNNAVOK (:5100) via ce relais local.
// Le préfixe est retiré : /jarvis/api/... -> /api/... sur le dashboard.
function proxyDashboard(req, res) {
  const upstream = http.request(
    {
      host: DASH_HOST,
      port: DASHBOARD_PORT,
      method: req.method,
      path: (req.url || "/").replace(/^\/jarvis/, "") || "/",
      headers: { ...req.headers, host: `${DASH_HOST}:${DASHBOARD_PORT}` },
      timeout: 15000,
    },
    (dashRes) => {
      const headers = { ...dashRes.headers };
      delete headers["access-control-allow-origin"];
      delete headers["content-length"];
      res.writeHead(dashRes.statusCode || 502, headers);
      dashRes.pipe(res);
    }
  );
  upstream.on("timeout", () => upstream.destroy(new Error("dashboard_timeout")));
  upstream.on("error", (err) => {
    if (!res.headersSent) {
      json(res, 503, {
        error: "dashboard_unavailable",
        reason: err.message === "dashboard_timeout" ? "timeout" : "connection_refused",
        upstream: `${DASH_HOST}:${DASHBOARD_PORT}`,
      });
    } else {
      res.end();
    }
  });
  req.pipe(upstream);
}

// Flux SSE de la sentinelle locale : même origine pour le HUD, aucun appel externe.
// Le préfixe est retiré : /sentinel/events -> /events sur :8766. Pas de timeout :
// un flux événementiel reste ouvert par définition.
function proxySentinel(req, res) {
  const upstream = http.request(
    {
      host: SENT_HOST,
      port: SENT_PORT,
      method: req.method,
      path: (req.url || "/").replace(/^\/sentinel/, "") || "/",
      headers: { ...req.headers, host: `${SENT_HOST}:${SENT_PORT}` },
      timeout: 0,
    },
    (sentRes) => {
      const headers = { ...sentRes.headers };
      delete headers["access-control-allow-origin"];
      delete headers["content-length"];
      headers["cache-control"] = "no-cache";
      headers["x-accel-buffering"] = "no";
      if ((req.url || "").startsWith("/sentinel/events")) {
        headers["content-type"] = "text/event-stream; charset=utf-8";
      }
      res.writeHead(sentRes.statusCode || 502, headers);
      sentRes.pipe(res);
    }
  );
  upstream.on("error", (err) => {
    if (!res.headersSent) {
      json(res, 503, {
        error: "sentinel_unavailable",
        reason: err.message || "connection_refused",
        upstream: `${SENT_HOST}:${SENT_PORT}`,
      });
    } else {
      res.end();
    }
  });
  res.on("close", () => upstream.destroy());
  req.pipe(upstream);
}

// Atulya est servi sous la même origine: /atulya/* -> /sur 8501, /api/* -> /api/* sur 8501.
// On retire les en-têtes qui interdisent l'iframe et tout script CDN du HTML reçu.
function proxyAtulya(req, res, stripPrefix = "") {
  const rawPath = req.url || "/";
  const stream = rawPath.includes("/api/events");
  let upstreamPath = rawPath;
  if (stripPrefix && rawPath.startsWith(stripPrefix)) {
    const rest = rawPath.slice(stripPrefix.length);
    // Le HUD ouvre /atulya/ : servir /index.html plutôt que / qui redirigerait vers le HUD.
    upstreamPath = !rest || rest === "/" ? "/index.html" : rest;
  }
  const method = String(req.method || "GET").toUpperCase();
  const requestHeaders = { ...req.headers, host: `${ATULYA_HOST}:${ATULYA_PORT}` };
  if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
    // Le HUD et l'iframe partagent l'origine :3860 ; Atulya n'accepte les
    // mutations que depuis sa propre origine loopback. Réécriture locale only.
    const authority = ATULYA_HOST.includes(":") ? `[${ATULYA_HOST}]` : ATULYA_HOST;
    requestHeaders.origin = `http://${authority}:${ATULYA_PORT}`;
    requestHeaders["sec-fetch-site"] = "same-origin";
    delete requestHeaders.referer;
  }
  const upstream = http.request(
    {
      host: ATULYA_HOST,
      port: ATULYA_PORT,
      method: req.method,
      path: upstreamPath,
      headers: requestHeaders,
      timeout: stream ? 0 : 120000,
    },
    (atuRes) => {
      const headers = { ...atuRes.headers };
      delete headers["access-control-allow-origin"];
      delete headers["content-length"];
      delete headers["x-frame-options"];
      headers["content-security-policy"] =
        "default-src 'self' data: blob:; script-src 'self' 'wasm-unsafe-eval'; " +
        "style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; " +
        "media-src 'self' blob: data:; connect-src 'self'; font-src 'self' data:; " +
        "worker-src 'self' blob:; object-src 'none'; base-uri 'none'; " +
        "frame-ancestors 'self'; form-action 'self'";
      headers["x-content-type-options"] = "nosniff";
      headers["permissions-policy"] =
        "camera=(self), microphone=(self), geolocation=(self)";
      headers["cache-control"] = "no-store";

      if (stream) {
        res.writeHead(atuRes.statusCode || 502, headers);
        atuRes.pipe(res);
        return;
      }

      const chunks = [];
      atuRes.on("data", (chunk) => chunks.push(chunk));
      atuRes.on("end", () => {
        let body = Buffer.concat(chunks);
        const type = String(atuRes.headers["content-type"] || "");
        if (type.includes("text/html")) {
          let html = body.toString("utf8");
          html = html.replace(
            /<script[^>]*\bsrc=["']https:\/\/telegram\.org\/js\/telegram-web-app\.js["'][^>]*>\s*<\/script>/gi,
            ""
          );
          body = Buffer.from(html, "utf8");
        }
        delete headers["transfer-encoding"];
        headers["content-length"] = body.length;
        res.writeHead(atuRes.statusCode || 502, headers);
        res.end(body);
      });
    }
  );
  upstream.on("timeout", () => upstream.destroy(new Error("atulya_timeout")));
  upstream.on("error", (err) => {
    if (!res.headersSent) {
      json(res, 503, {
        error: "atulya_unavailable",
        reason: err.message === "atulya_timeout" ? "timeout" : "connection_refused",
        upstream: `${ATULYA_HOST}:${ATULYA_PORT}`,
      });
    } else {
      res.end();
    }
  });
  res.on("close", () => {
    if (stream) upstream.destroy();
  });
  req.pipe(upstream);
}

// Cache paresseux des fichiers statiques : une seule lecture tant que taille/mtime/ctime
// ne changent pas. Les en-têtes restent no-store, donc aucun cache côté navigateur.
const STATIC_CACHE = new Map();
const NOT_FOUND = path.join(ROOT, "404.html");

function cachedRead(file, info = fs.statSync(file)) {
  if (!info.isFile()) return null;
  const cached = STATIC_CACHE.get(file);
  if (cached && cached.size === info.size && cached.mtimeMs === info.mtimeMs
      && cached.ctimeMs === info.ctimeMs) return cached.body;
  const body = fs.readFileSync(file);
  STATIC_CACHE.set(file, { size: info.size, mtimeMs: info.mtimeMs, ctimeMs: info.ctimeMs, body });
  return body;
}

const server = http.createServer((req, res) => {
  const url = req.url || "/";
  if (url === "/sentinel/events" || url === "/sentinel/health") {
    proxySentinel(req, res);
    return;
  }
  if (url === "/freellm/health" || url.startsWith("/freellm/")) {
    proxyFreeLLM(req, res);
    return;
  }
  if (url === "/v1/health" || url.startsWith("/v1/")) {
    proxyApi(req, res);
    return;
  }
  if (url.startsWith("/jarvis/")) {
    proxyDashboard(req, res);
    return;
  }
  if (url === "/atulya" || url.startsWith("/atulya/")) {
    proxyAtulya(req, res, "/atulya");
    return;
  }
  if (url === "/api" || url.startsWith("/api/")) {
    proxyAtulya(req, res);
    return;
  }
  const target = safeTarget(url);
  if (!target) {
    res.writeHead(403, { "Content-Type": "text/plain; charset=utf-8" });
    res.end("forbidden");
    return;
  }
  let file = target;
  try {
    const info = fs.statSync(file);
    if (info.isDirectory()) {
      file = path.join(file, "index.html");
    }
    const body = cachedRead(file);
    if (!body) throw new Error("not a regular file");
    res.writeHead(200, {
      "Content-Type": MIME[path.extname(file).toLowerCase()] || "application/octet-stream",
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
      // Caméra et micro uniquement pour cette origine loopback ; aucun tiers ne peut les demander.
      "Permissions-Policy": "camera=(self), microphone=(self)",
    });
    res.end(body);
  } catch {
    if (fs.existsSync(NOT_FOUND)) {
      const body = cachedRead(NOT_FOUND);
      res.writeHead(404, { "Content-Type": "text/html; charset=utf-8" });
      res.end(body || "not found");
    } else {
      res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      res.end("not found");
    }
  }
});

server.listen(PORT, HOST, () => {
  console.log(`G0DM0D3 static UI - http://${HOST}:${PORT}/ - API /v1 -> ${API_HOST}:${API_PORT} - sentinel -> ${SENT_HOST}:${SENT_PORT}`);
});
