import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';

const ROOT = new URL('..', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const OUT = join(ROOT, 'esprieaether', 'G0DM0D3', 'out');

test('visage: HUD local avec les deux modes et animation pilotée par la voix', async () => {
  const html = await readFile(join(OUT, 'jarvis.html'), 'utf8');
  assert.ok(html.includes('id="face"'), 'conteneur du visage absent');
  assert.ok(html.includes('id="faceCanvas"'), 'canvas hologramme absent');
  assert.ok(html.includes('id="facePortrait"'), 'portrait stylisé absent');
  assert.ok(html.includes('id="faceMode"'), 'bouton de bascule absent');
  assert.ok(/function\s+drawFace/.test(html), 'dessin du visage absent');
  assert.ok(/voice\.stage/.test(html), 'état vocal non branché au visage');
  assert.ok(html.includes('system.html'), 'lien vers la page système absent');
  assert.ok(!html.includes('https://'), 'ressource externe');
  assert.ok(!/onclick|POST/.test(html), 'aucune commande depuis le HUD');
});

test('page système: tuiles réelles, API locale, aucun contrôle d’exécution', async () => {
  const html = await readFile(join(OUT, 'system.html'), 'utf8');
  for (const id of ['reactor', 'services', 'robots', 'attention', 'ledger', 'internet', 'voice']) {
    assert.ok(html.includes(`id="${id}"`), `tuile ${id} manquante`);
  }
  assert.ok(html.includes('/jarvis/api/jarvis/attention'), 'API non branchée');
  assert.ok(!html.includes('https://'), 'ressource externe');
  assert.ok(!/<script[^>]+src=/.test(html), 'script externe');
  assert.ok(!/onclick|POST/.test(html), 'aucune commande depuis la page système');
  assert.ok(!/demo|mock|fake/i.test(html), 'aucune donnée de démonstration');
});
