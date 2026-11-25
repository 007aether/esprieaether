import test from 'node:test';
import assert from 'node:assert/strict';
import http from 'node:http';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';

const ROOT = new URL('..', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const SERVER = join(ROOT, 'esprieaether', 'scripts', 'serve_g0dm0d3.mjs');

function freePort() {
  return new Promise((resolve, reject) => {
    const probe = http.createServer();
    probe.once('error', reject);
    probe.listen(0, '127.0.0.1', () => {
      const port = probe.address().port;
      probe.close(() => resolve(port));
    });
  });
}

async function waitFor(port) {
  for (let i = 0; i < 80; i += 1) {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/v1/health`);
      if (response.status < 500) return;
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  throw new Error('bridge did not start');
}

test('J100: le pont réécrit Origin vers Atulya pour les requêtes qui modifient l’état', async () => {
  const upstreamPort = await freePort();
  const bridgePort = await freePort();
  let seen = null;
  const upstream = http.createServer((req, res) => {
    seen = {
      method: req.method,
      url: req.url,
      host: req.headers.host,
      origin: req.headers.origin,
      site: req.headers['sec-fetch-site'],
    };
    req.resume();
    req.on('end', () => {
      res.writeHead(200, { 'content-type': 'application/json' });
      res.end('{"ok":true}');
    });
  });
  await new Promise((resolve) => upstream.listen(upstreamPort, '127.0.0.1', resolve));
  const child = spawn(process.execPath, [SERVER], {
    env: {
      ...process.env,
      G0DM0D3_HOST: '127.0.0.1',
      G0DM0D3_PORT: String(bridgePort),
      ATULYA_HOST: '127.0.0.1',
      ATULYA_PORT: String(upstreamPort),
    },
    stdio: 'ignore',
  });
  try {
    await waitFor(bridgePort);
    const response = await fetch(`http://127.0.0.1:${bridgePort}/api/chat`, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        origin: `http://127.0.0.1:${bridgePort}`,
        'sec-fetch-site': 'same-origin',
      },
      body: JSON.stringify({ messages: [{ role: 'user', content: 'salam' }] }),
    });
    assert.equal(response.status, 200);
    assert.ok(seen);
    assert.equal(seen.method, 'POST');
    assert.equal(seen.url, '/api/chat');
    assert.equal(seen.host, `127.0.0.1:${upstreamPort}`);
    assert.equal(seen.origin, `http://127.0.0.1:${upstreamPort}`);
    assert.equal(seen.site, 'same-origin');
  } finally {
    child.kill();
    upstream.close();
  }
});
