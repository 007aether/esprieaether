import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';

const ROOT = new URL('..', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const HUD = join(ROOT, 'esprieaether', 'G0DM0D3', 'out', 'jarvis.html');
const SERVE = join(ROOT, 'esprieaether', 'scripts', 'serve_g0dm0d3.mjs');
const KEEP = join(ROOT, 'esprieaether', 'scripts', 'keep_alive.ps1');
const SENTINEL = join(ROOT, 'esprieaether', 'scripts', 'local_sentinel.py');
const LAUNCHER = join(ROOT, 'esprieaether', 'scripts', 'start_claude_code_local.ps1');

test('J84: sentinelle locale loopback, SSE, sans dependance externe', async () => {
  const src = await readFile(SENTINEL, 'utf8');
  assert.ok(src.includes('127.0.0.1'));
  assert.ok(src.includes('/events'));
  assert.ok(src.includes('/health'));
  assert.ok(src.includes('atulya'));
  assert.ok(src.includes('opencode'));
  assert.ok(src.includes('freellmapi'));
  assert.ok(src.includes('claude-code'));
  assert.ok(src.includes('--restarted-by-app'));
  assert.ok(src.includes('model_share.jsonl'));
  assert.ok(src.includes('shareLabel'));
  assert.ok(!/urllib\.request|requests|httpx|webbrowser|Open-Meteo/.test(src));
});

test('J111: relais FreeLLMAPI local, clé lue à l execution, parts journalisées', async () => {
  const src = await readFile(SERVE, 'utf8');
  assert.ok(src.includes('/freellm/'));
  assert.ok(src.includes('proxyFreeLLM'));
  assert.ok(src.includes('loadFreeLLMKey'));
  assert.ok(src.includes('recordShare'));
  assert.ok(src.includes('x-esprie-consumer'));
  assert.ok(src.includes('const countable ='));
  assert.ok(src.includes('const chunks = []'));
  assert.ok(src.includes('headers["content-length"] = String(body.length)'));
  assert.ok(src.includes('upstream.end(body)'));
  assert.ok(src.includes('delete meta.thinking'));
  assert.ok(src.includes('delete meta.context_management'));
  assert.ok(src.includes('meta.stream = false'));
  assert.ok(src.includes('En-têtes minimaux'));
  assert.ok(src.includes('FREELLM_KEY_FILE'));
  assert.ok(src.includes('SHARE_LEDGER'));
  assert.ok(!/writeFileSync\([^)]*key/i.test(src));
});

test('J111: lanceur Claude Code local sans secret ecrit dans un fichier', async () => {
  const src = await readFile(LAUNCHER, 'utf8');
  assert.ok(src.includes('Get-Content $keyFile -Raw'));
  assert.ok(src.includes('ANTHROPIC_AUTH_TOKEN = $key'));
  assert.ok(src.includes('http://127.0.0.1:3860/freellm'));
  assert.ok(src.includes('--no-session-persistence'));
  assert.ok(src.includes('DISABLE_TELEMETRY'));
  assert.ok(!/free[A-Za-z0-9]{20,}/i.test(src));
  assert.ok(!/https:\/\//.test(src));
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
  assert.ok(html.includes('"freellmapi"'));
  assert.ok(html.includes('t.shareLabel'));
  assert.ok(!html.includes('https://'));
  assert.ok(!/<script[^>]+src=/.test(html));
  assert.ok(!/onclick|\bPOST\b/.test(html));
});
