import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';

const ROOT = new URL('..', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const HUD = join(ROOT, 'esprieaether', 'G0DM0D3', 'out', 'jarvis.html');
const SERVE = join(ROOT, 'esprieaether', 'scripts', 'serve_g0dm0d3.mjs');

test('HUD: fichier local présent et sans ressource externe', async () => {
  const html = await readFile(HUD, 'utf8');
  assert.ok(html.length > 1000);
  assert.ok(!html.includes('https://'), 'aucune ressource externe');
  assert.ok(!html.includes('cdn.'), 'aucun CDN');
  assert.ok(!/<script[^>]+src=/.test(html), 'aucun script externe');
});

test('HUD: panneaux reactor / services / robots / attention / internet', async () => {
  const html = await readFile(HUD, 'utf8');
  for (const id of ['reactor', 'services', 'robots', 'attention', 'ledger', 'internet']) {
    assert.ok(html.includes(`id="${id}"`), `panneau ${id} manquant`);
  }
  assert.ok(html.includes('/jarvis/api/jarvis/attention'));
  assert.ok(html.includes('/jarvis/api/system/status'));
});

test('HUD: panneau vocal branché à l’API, sans secret ni contrôle', async () => {
  const html = await readFile(HUD, 'utf8');
  assert.ok(html.includes('id="voice"'), 'panneau voice manquant');
  assert.ok(/function\s+renderVoice/.test(html), 'renderVoice absent');
  assert.ok(/renderVoice\(d\.voice\)/.test(html), 'voice non branché à l’API');
  assert.ok(!/onclick|POST/.test(html), 'aucune commande depuis le HUD');
});

test('HUD: état Internet honnête, sans secret et sans contrôle d’exécution', async () => {
  const html = await readFile(HUD, 'utf8');
  assert.ok(/function\s+renderInternet/.test(html), 'render Internet absent');
  assert.ok(/renderInternet\(d\.internet\)/.test(html), 'Internet non branché à l’API');
  assert.ok(/no_data_source/.test(html), 'statut honnête absent');
  for (const secret of ['api_key', 'token', 'password', 'HF_TOKEN']) {
    assert.ok(!html.includes(secret), `secret ${secret} exposé`);
  }
  assert.ok(!/onclick|fetch\([^)]*\{[^}]*method\s*:\s*["']POST/.test(html), 'aucune commande depuis le HUD');
});

test('HUD: le relais reste loopback et ne remplace pas /v1', async () => {
  const source = await readFile(SERVE, 'utf8');
  assert.ok(source.includes('127.0.0.1'));
  assert.ok(source.includes('/jarvis/'), 'relais HUD absent');
  assert.ok(source.includes('/v1/'), 'relais G0DM0D3 conservé');
  assert.ok(source.includes('127.0.0.1:5100') || source.includes('DASHBOARD_PORT'));
});
