import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';

const ROOT = new URL('..', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const HUD = join(ROOT, 'esprieaether', 'G0DM0D3', 'out', 'jarvis.html');

test('J102: le HUD offre Atulya en fenêtre flottante déplaçable', async () => {
  const html = await readFile(HUD, 'utf8');
  for (const needed of ['id="atulyaDock"', 'id="atulyaHandle"', 'id="atulyaDockClose"', 'id="atulyaDockStandalone"']) {
    assert.ok(html.includes(needed), `élément manquant : ${needed}`);
  }
  assert.match(html, /addEventListener\("pointerdown"/);
  assert.match(html, /setPointerCapture/);
  assert.match(html, /localStorage\.setItem\("sunnavok\.atulya\.dock"/);
  assert.doesNotMatch(html, /onclick/i);
});

test('J102: fenêtre flottante fermable au clavier et nommée en darija', async () => {
  const html = await readFile(HUD, 'utf8');
  assert.match(html, /id="atulyaHandle"[^>]*aria-label="أتوليا · نافذة عائمة قابلة للسحب"/);
  assert.match(html, /addEventListener\("keydown", function \(e\) \{[\s\S]*?e\.key === "Escape"[\s\S]*?closeAtulyaDock\(\)/);
});

test('J102: une page Atulya complète et autonome reste accessible', async () => {
  const html = await readFile(HUD, 'utf8');
  assert.match(html, /id="atulyaStandalone"[^>]*target="_blank"|target="_blank"[^>]*id="atulyaStandalone"/);
  assert.match(html, /href="\/atulya\/"/);
  assert.equal((html.match(/frame\.src\s*=\s*"\/atulya\/"/g) || []).length, 1);
});
