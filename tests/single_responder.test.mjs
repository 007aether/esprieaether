import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';

const ROOT = new URL('..', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const KEEPER = join(ROOT, 'esprieaether', 'scripts', 'keep_alive.ps1');
const PERSONA = join(ROOT, 'GITHUB_IMPORT', 'Atulya-Tantra', 'atulya', 'persona.py');
const HUD = join(ROOT, 'esprieaether', 'G0DM0D3', 'out', 'jarvis.html');

test('J98: une seule voix répond — le daemon JARVIS hérité est désactivé par défaut', async () => {
  const source = await readFile(KEEPER, 'utf8');
  assert.match(source, /\$legacyVoice\s*=\s*\$env:ESPRIE_LEGACY_VOICE\s*-eq\s*'1'/);
  assert.match(source, /if \(\$legacyVoice\) \{[\s\S]*voice_daemon\.py/);
  assert.match(source, /Stop-Process[\s\S]*voice_daemon\.py/);
  assert.match(source, /atulya-only/);
});

test('J98: Atulya ne se présente pas comme JARVIS', async () => {
  const persona = await readFile(PERSONA, 'utf8');
  assert.doesNotMatch(persona, /in the style of Jarvis/i);
  assert.match(persona, /You are \{name\}/);
  assert.match(persona, /الدارجة المغربية/);
});

test('J98: le HUD reste un panneau de lecture, sans champ de chat propre', async () => {
  const html = await readFile(HUD, 'utf8');
  assert.equal((html.match(/frame\.src\s*=\s*"\/atulya\/"/g) || []).length, 1);
  assert.doesNotMatch(html, /id="chat-(form|input)"/i);
  assert.doesNotMatch(html, /onclick/i);
  assert.doesNotMatch(html, /\bPOST\b/);
});
