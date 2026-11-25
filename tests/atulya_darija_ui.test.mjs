import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';

const ROOT = new URL('..', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const UI = join(ROOT, 'GITHUB_IMPORT', 'Atulya-Tantra', 'webui', 'assistant.js');

test('J99: la bulle d’accueil d’Atulya est toujours en darija, jamais en anglais', async () => {
  const source = await readFile(UI, 'utf8');
  for (const english of ['Good morning.', 'Good afternoon.', 'Good evening.', 'Welcome back.']) {
    assert.ok(!source.includes(english), `salutation anglaise restante : ${english}`);
  }
  for (const darija of ['صباح الخير.', 'مساء الخير.', 'مرحبا بعودتك.']) {
    assert.ok(source.includes(darija), `salutation darija manquante : ${darija}`);
  }
});

test('J99: la voix du navigateur choisit l’arabe pour un texte en lettres arabes', async () => {
  const source = await readFile(UI, 'utf8');
  assert.match(source, /\\p\{Script=Arabic\}/u);
  assert.match(source, /ar-MA/);
  assert.doesNotMatch(source, /Hindi\/English voice/);
});
