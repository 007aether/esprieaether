import test from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import { spawn } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SERVER = path.join(ROOT, "esprieaether", "scripts", "serve_g0dm0d3.mjs");

const usedPorts = new Set();
function freePort() {
  return new Promise((resolve, reject) => {
    const probe = http.createServer();
    probe.once("error", reject);
    probe.listen(0, "127.0.0.1", () => {
      const port = probe.address().port;
      probe.close(() => {
        if (usedPorts.has(port)) {
          freePort().then(resolve, reject);
          return;
        }
        usedPorts.add(port);
        resolve(port);
      });
    });
  });
}

function get(url) {
  return new Promise((resolve, reject) => {
    http
      .get(url, (response) => {
        const chunks = [];
        response.on("data", (chunk) => chunks.push(chunk));
        response.on("end", () => {
          resolve({
            ok: response.statusCode >= 200 && response.statusCode < 300,
            status: response.statusCode,
            headers: response.headers,
            body: Buffer.concat(chunks).toString("utf8"),
          });
        });
      })
      .once("error", reject);
  });
}

async function waitFor(url, attempts = 60) {
  let lastError;
  for (let index = 0; index < attempts; index += 1) {
    try {
      const response = await get(url);
      if (response.ok) return response;
      lastError = new Error(`HTTP ${response.status}`);
    } catch (error) {
      lastError = error;
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error(`serveur non prêt: ${url} (${lastError?.message})`);
}

test("HUD: pont loopback vers Atulya, même origine, sans script externe", async () => {
  const atulyaPort = await freePort();
  const dashboardPort = await freePort();
  const uiPort = await freePort();

  const seenPaths = [];
  const upstream = http.createServer((req, res) => {
    seenPaths.push(req.url);
    const headers = {
      "content-type": "application/json; charset=utf-8",
      "x-frame-options": "DENY",
      "content-security-policy":
        "default-src 'self'; frame-ancestors 'self' https://web.telegram.org",
    };
    if (["/api/health", "/api/status", "/api/jarvis/capabilities"].includes(req.url)) {
      res.writeHead(200, headers);
      res.end(JSON.stringify({ ok: true, path: req.url }));
      return;
    }
    res.writeHead(200, {
      "content-type": "text/html; charset=utf-8",
      "x-frame-options": "DENY",
      "content-security-policy":
        "default-src 'self'; frame-ancestors 'self' https://web.telegram.org",
    });
    res.end(
      '<!doctype html><script src="https://telegram.org/js/telegram-web-app.js"></script><div>Atulya local</div>'
    );
  });
  await new Promise((resolve) => upstream.listen(atulyaPort, "127.0.0.1", resolve));

  const dashboard = http.createServer((req, res) => {
    res.writeHead(200, { "content-type": "application/json; charset=utf-8" });
    res.end(JSON.stringify({ ok: true, path: req.url }));
  });
  await new Promise((resolve) => dashboard.listen(dashboardPort, "127.0.0.1", resolve));

  const child = spawn(process.execPath, [SERVER], {
    cwd: ROOT,
    env: {
      ...process.env,
      G0DM0D3_PORT: String(uiPort),
      G0DM0D3_API_PORT: String(dashboardPort),
      DASHBOARD_PORT: String(dashboardPort),
      ATULYA_PORT: String(atulyaPort),
    },
    stdio: ["ignore", "pipe", "pipe"],
  });
  let childError = "";
  child.stderr?.on("data", (chunk) => {
    childError += chunk.toString("utf8");
  });
  child.stdout?.on("data", (chunk) => {
    childError += chunk.toString("utf8");
  });
  child.once("exit", (code, signal) => {
    childError += `\nexit=${code} signal=${signal}`;
  });

  try {
    const base = `http://127.0.0.1:${uiPort}`;
    let page;
    try {
      page = await waitFor(`${base}/atulya/`);
    } catch (error) {
      throw new Error(`${error.message}\nchild stderr: ${childError}`);
    }
    assert.equal(page.headers["x-frame-options"], undefined);
    assert.match(page.headers["content-security-policy"] || "", /frame-ancestors 'self'/);
    assert.equal(page.body.includes("https://telegram.org/js/telegram-web-app.js"), false);
    // Le HUD demande /atulya/ : le pont doit viser /index.html, pas / qui redirige vers le HUD.
    assert.ok(seenPaths.includes("/index.html"), `upstream paths: ${seenPaths.join(", ")}`);

    const status = JSON.parse((await get(`${base}/atulya/api/status`)).body);
    assert.deepEqual(status, { ok: true, path: "/api/status" });

    const health = JSON.parse((await get(`${base}/api/health`)).body);
    assert.deepEqual(health, { ok: true, path: "/api/health" });

    const capabilities = JSON.parse(
      (await get(`${base}/jarvis/api/jarvis/capabilities`)).body
    );
    assert.deepEqual(capabilities, { ok: true, path: "/api/jarvis/capabilities" });
  } finally {
    child.kill();
    await new Promise((resolve) => upstream.close(resolve));
    await new Promise((resolve) => dashboard.close(resolve));
  }
});
