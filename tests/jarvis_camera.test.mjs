import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';

const ROOT = new URL('..', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const OUT = join(ROOT, 'esprieaether', 'G0DM0D3', 'out');

test('J69 — caméra PC locale, empreintelocale, nom ESPRIEATHER', async () => {
  const html = await readFile(join(OUT, 'jarvis.html'), 'utf8');
  assert.ok(html.includes('id="camVideo"'), 'élément vidéo caméra absent');
  assert.ok(html.includes('getUserMedia'), 'accès caméra absent');
  assert.ok(html.includes('id="camToggle"'), 'bouton caméra absent');
  assert.ok(html.includes('id="enrollBtn"'), 'bouton enrollement absent');
  assert.ok(html.includes('sunnavok-esprieather-profile-v1'), 'profil local absent');
  assert.ok(/AudioContext|AnalyserNode/.test(html), 'signature vocale locale absente');
  assert.ok(html.includes('ESPRIEATHER'), 'nom du système absent');
  assert.ok(!html.includes('https://'), 'ressource externe');
  assert.ok(!/onclick|POST/.test(html), 'aucune commande depuis le HUD');
});

test('J69 — page système porte le même nom et reste sans contrôle', async () => {
  const html = await readFile(join(OUT, 'system.html'), 'utf8');
  assert.ok(html.includes('ESPRIEATHER'), 'nom du système absent');
  assert.ok(!html.includes('https://'), 'ressource externe');
  assert.ok(!/onclick|POST/.test(html), 'aucune commande depuis la page système');
});

test('J69 — serveur statique autorise caméra/micro uniquement en local', async () => {
  const src = await readFile(join(ROOT, 'esprieaether', 'scripts', 'serve_g0dm0d3.mjs'), 'utf8');
  assert.ok(src.includes('Permissions-Policy'), 'politique de permissions absente');
  assert.ok(/camera=\(self\)/.test(src), 'caméra non limitée à self');
  assert.ok(/microphone=\(self\)/.test(src), 'micro non limité à self');
});
