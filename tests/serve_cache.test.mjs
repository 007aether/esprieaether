import test from "node:test";
import assert from "node:assert/strict";
import http from "node:http";
import { spawn } from "node:child_process";
import { rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const SERVER = path.join(ROOT, "esprieaether", "scripts", "serve_g0dm0d3.mjs");
const OUT = path.join(ROOT, "esprieaether", "G0DM0D3", "out");
const COUNTER = fileURLToPath(new URL("./fixtures/fs-counter.cjs", import.meta.url));
const CHUNK = "/_next/static/chunks/30-d25f42e794b06b2c.js";

const usedPorts = new Set();
function freePort() {
  return new Promise((resolve, reject) => {
    const probe = http.createServer();
    probe.once("error", reject);
    probe.listen(0, "127.0.0.1", () => {
      const port = probe.address().port;
      probe.close(() => {
        if (usedPorts.has(port)) return freePort().then(resolve, reject);
        usedPorts.add(port);
        resolve(port);
      });
    });
  });
}

function get(url) {
  return new Promise((resolve, reject) => {
    http.get(url, (response) => {
      const chunks = [];
      response.on("data", (chunk) => chunks.push(chunk));
      response.on("end", () => resolve({
        status: response.statusCode,
        headers: response.headers,
        body: Buffer.concat(chunks).toString("utf8"),
      }));
    }).once("error", reject);
  });
}

async function waitFor(url, attempts = 60) {
  let lastError;
  for (let index = 0; index < attempts; index += 1) {
    try {
      const response = await get(url);
      if (response.ok || response.status < 500) return response;
      lastError = new Error(`HTTP ${response.status}`);
    } catch (error) { lastError = error; }
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error(`serveur non prêt: ${url} (${lastError?.message})`);
}

async function startServer() {
  const uiPort = await freePort();
  const idle = await freePort();
  const child = spawn(process.execPath, ["--require", COUNTER, SERVER], {
    cwd: ROOT,
    env: {
      ...process.env,
      G0DM0D3_PORT: String(uiPort),
      G0DM0D3_API_PORT: String(idle),
      DASHBOARD_PORT: String(idle),
      ATULYA_PORT: String(idle),
      ESPRIE_SENTINEL_PORT: String(idle),
    },
    stdio: ["ignore", "pipe", "pipe"],
  });
  let log = "";
  child.stdout.on("data", (chunk) => { log += chunk.toString("utf8"); });
  child.stderr.on("data", (chunk) => { log += chunk.toString("utf8"); });
  await waitFor(`http://127.0.0.1:${uiPort}/jarvis.html`);
  return {
    base: `http://127.0.0.1:${uiPort}`,
    reads: (needle) => log.split("\n").filter((line) => line.startsWith("READ ") && line.includes(needle)).length,
    close: () => child.kill(),
  };
}

test("HUD: un gros chunk statique n'est lu qu'une fois", async () => {
  const server = await startServer();
  try {
    const first = await get(server.base + CHUNK);
    const second = await get(server.base + CHUNK);
    assert.equal(first.status, 200);
    assert.equal(second.body, first.body);
    assert.match(first.headers["content-type"], /javascript/);
    assert.equal(first.headers["cache-control"], "no-store");
    assert.equal(first.headers["x-content-type-options"], "nosniff");
    assert.match(first.headers["permissions-policy"], /camera=\(self\), microphone=\(self\)/);
    assert.equal(server.reads("30-d25f42e794b06b2c.js"), 1);
  } finally { server.close(); }
});

test("HUD: les requêtes parallèles partagent le même fichier en cache", async () => {
  const server = await startServer();
  try {
    const responses = await Promise.all(Array.from({ length: 12 }, () => get(server.base + CHUNK)));
    assert.equal(new Set(responses.map((item) => item.body)).size, 1);
    assert.equal(server.reads("30-d25f42e794b06b2c.js"), 1);
  } finally { server.close(); }
});

test("HUD: le cache détecte une modification réelle du fichier", async () => {
  const server = await startServer();
  const probe = path.join(OUT, `__cache_probe_${process.pid}.js`);
  const urlPath = "/" + path.basename(probe);
  try {
    await writeFile(probe, "var value = 'short';\n", "utf8");
    assert.equal((await get(server.base + urlPath)).body, "var value = 'short';\n");
    await writeFile(probe, "var value = 'a noticeably longer value';\n", "utf8");
    assert.equal((await get(server.base + urlPath)).body, "var value = 'a noticeably longer value';\n");
    assert.equal(server.reads(path.basename(probe)), 2);
  } finally {
    server.close();
    await rm(probe, { force: true });
  }
});

test("HUD: le cache ne contourne ni le 403 ni le 404 ni le HTML", async () => {
  const server = await startServer();
  try {
    const root = await get(server.base + "/");
    assert.equal(root.status, 200);
    assert.match(root.body, /<html[\s>]/);
    assert.ok(root.body.length > 1000);
    assert.equal(server.reads("index.html"), 1);
    const missing = await get(server.base + "/__missing_test_file__");
    assert.equal(missing.status, 404);
    assert.ok(missing.body.length > 100);
    const traversal = await get(server.base + "/%2e%2e%2fpackage.json");
    assert.equal(traversal.status, 403);
    assert.equal(traversal.body, "forbidden");
    assert.equal(server.reads("package.json"), 0);
  } finally { server.close(); }
});
