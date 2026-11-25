import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';

const ROOT = new URL('..', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const HUD = join(ROOT, 'esprieaether', 'G0DM0D3', 'out', 'jarvis.html');
const SERVE = join(ROOT, 'esprieaether', 'scripts', 'serve_g0dm0d3.mjs');
const KEEP = join(ROOT, 'esprieaether', 'scripts', 'keep_alive.ps1');
const SENTINEL = join(ROOT, 'esprieaether', 'scripts', 'local_sentinel.py');

test('J84: sentinelle locale loopback, SSE, sans dependance externe', async () => {
  const src = await readFile(SENTINEL, 'utf8');
  assert.ok(src.includes('127.0.0.1'));
  assert.ok(src.includes('/events'));
  assert.ok(src.includes('/health'));
  assert.ok(src.includes('atulya'));
  assert.ok(src.includes('opencode'));
  assert.ok(!/urllib\.request|requests|httpx|webbrowser|Open-Meteo/.test(src));
});

test('J84: relais /sentinel same-origin, flux non mis en memoire tampon', async () => {
  const src = await readFile(SERVE, 'utf8');
  assert.ok(src.includes('/sentinel/'));
  assert.ok(src.includes('proxySentinel'));
  assert.ok(src.includes("ESPRIE_SENTINEL_HOST || \"127.0.0.1\""));
  assert.ok(src.includes('x-accel-buffering'));
  assert.ok(src.includes('/jarvis/'));
  assert.ok(src.includes('/v1/'));
});

test('J84: superviseur redemarre la sentinelle et verifie /health', async () => {
  const src = await readFile(KEEP, 'utf8');
  assert.ok(src.includes("Name='sentinel'"));
  assert.ok(src.includes('Port=8766'));
  assert.ok(src.includes("8766 = '/health'"));
});

test('J84: HUD lit le flux en lecture seule, sans POST ni ressource externe', async () => {
  const html = await readFile(HUD, 'utf8');
  for (const id of ['sentinelCanvas', 'sentinelAgents', 'sentinelWave', 'sentinelState']) {
    assert.ok(html.includes(`id="${id}"`), `panneau ${id} manquant`);
  }
  assert.ok(html.includes('new EventSource(SEN)'));
  assert.ok(!html.includes('https://'));
  assert.ok(!/<script[^>]+src=/.test(html));
  assert.ok(!/onclick|\bPOST\b/.test(html));
});
