import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { homedir } from 'node:os';
import { join } from 'node:path';

const ROOT = new URL('..', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const CFG = join(homedir(), '.config', 'opencode', 'opencode.json');

test('OPCODE: modèle par défaut non censuré et réellement serve', async () => {
  const cfg = JSON.parse(await readFile(CFG, 'utf8'));
  assert.equal(cfg.model, 'esprieather/dolphin3');
  const local = cfg.provider?.esprieather;
  assert.ok(local, 'fournisseur local absent');
  assert.equal(local.options?.baseURL, 'http://127.0.0.1:31416/v1');
  assert.ok(local.models?.dolphin3, 'dolphin3 absent');
  assert.ok(!local.options?.apiKey, 'aucune clé pour le routeur local');
  const router = cfg.provider?.freellmapi;
  assert.equal(router?.models?.esprieather?.modelID, 'mistral-small-3.2-24b');
});

test('OPCODE: مشغّل الجلسة غير المراقَبة موجود', async () => {
  const launcher = await readFile(join(ROOT, 'START_ESPRIEATHER_UNCENSORED.cmd'), 'utf8');
  assert.ok(launcher.includes('--model esprieather/dolphin3'));
  assert.ok(launcher.includes('--session ses_e04a74871ffexFHvNy4uGt1knu'));
});
