import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';

const ROOT = new URL('..', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const HTML = join(ROOT, 'esprieaether', 'G0DM0D3', 'out', 'jarvis.html');

test('J75 — profil biométrique local supprimable par l’utilisateur', async () => {
  const html = await readFile(HTML, 'utf8');
  assert.ok(html.includes('id="resetProfileBtn"'), 'bouton de suppression absent');
  assert.ok(/localStorage\.removeItem\(PROF_KEY\)/.test(html), 'suppression du profil absent');
  assert.ok(html.includes('profil local supprimé'), 'confirmation absente');
  assert.ok(!/onclick|POST/.test(html), 'aucune commande depuis le HUD');
  assert.ok(!html.includes('https://'), 'ressource externe');
});
