import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';

const ROOT = dirname(dirname(fileURLToPath(import.meta.url)));
const UI = join(ROOT, 'GITHUB_IMPORT', 'Atulya-Tantra', 'webui', 'assistant.js');
const source = await readFile(UI, 'utf8');

test('J159: le son local est débloqué au premier geste, pas avant', () => {
  assert.match(source, /let soundUnlocked = false/);
  assert.match(source, /function unlockSound\(/);
  assert.match(source, /addEventListener\(\s*["']pointerdown["']/);
  assert.match(source, /addEventListener\(\s*["']keydown["']/);
  assert.match(source, /if \(!soundUnlocked\) \{[\s\S]{0,120}pendingSpeech/);
});

test('J159: la lecture ne dépend plus d’un AudioContext suspendu', () => {
  const start = source.indexOf('const playBlob =');
  const end = source.indexOf('const done =', start);
  assert.ok(start > 0 && end > start, 'bloc playBlob introuvable');
  const block = source.slice(start, end);
  assert.match(block, /(?:activeAudio|audio)\.play\(\)/);
  assert.doesNotMatch(block, /resume\(\)\.then/);
  assert.doesNotMatch(block, /createMediaElementSource/);
});

test('J159: voix de secours réelle quand ar-MA est absente', () => {
  const start = source.indexOf('function preferMaleVoice(');
  const end = source.indexOf('function greet(', start);
  const block = source.slice(start, end);
  assert.match(block, /matching\[0\] \|\| voices\[0\]/);
  assert.match(block, /utterance\.lang =/);
});

test('J159: la synthèse reste loopback, sans URL externe ni clé', () => {
  const start = source.indexOf('const synthesize = (text) => fetch(');
  const end = source.indexOf('const playBlob =', start);
  const block = source.slice(start, end);
  assert.match(block, /\/api\/voice\/synthesize/);
  assert.doesNotMatch(block, /https?:\/\//);
  assert.doesNotMatch(block, /api[_-]?key/i);
});

const HUD = join(ROOT, 'esprieaether', 'G0DM0D3', 'out', 'jarvis.html');
const SERVE = join(ROOT, 'esprieaether', 'scripts', 'serve_g0dm0d3.mjs');
const KEEPALIVE = join(ROOT, 'esprieaether', 'scripts', 'keep_alive.ps1');

test('J159: le HUD propose un test de voix locale sur un clic explicite', async () => {
  const hud = await readFile(HUD, 'utf8');
  assert.match(hud, /id="voiceTestBtn"/);
  assert.match(hud, /\$\("voiceTestBtn"\)\.addEventListener\("click", testLocalVoice\)/);
  assert.match(hud, /fetch\("\/local-voice\/say"/);
  assert.match(hud, /new Audio\(url\)/);
  assert.doesNotMatch(hud, /https?:\/\/(?!127\.0\.0\.1|localhost)/);
});

test('J159: le relais HUD reste loopback et le service est supervisé', async () => {
  const serve = await readFile(SERVE, 'utf8');
  assert.match(serve, /function proxyLocalVoice\(/);
  assert.match(serve, /ATULYA_VOICE_PORT \|\| 5105/);
  assert.match(serve, /url\.startsWith\("\/local-voice\/"\)/);
  const keepalive = await readFile(KEEPALIVE, 'utf8');
  assert.match(keepalive, /Name='atulya-voice';\s+Port=5105/);
  assert.match(keepalive, /5105 = '\/health'/);
});
