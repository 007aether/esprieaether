import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';

const ROOT = new URL('..', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const BRAIN = join(ROOT, 'esprieaether', 'src', 'local_brain.py');
const KEEPER = join(ROOT, 'esprieaether', 'scripts', 'keep_alive.ps1');

test('J128: la file du routeur local attend assez longtemps pour le slot unique', async () => {
  const brain = await readFile(BRAIN, 'utf8');
  const queue = /LOCAL_BRAIN_QUEUE_TIMEOUT",\s*"(\d+)"/.exec(brain);
  const chat = /LOCAL_BRAIN_CHAT_TIMEOUT",\s*"(\d+)"/.exec(brain);
  assert.ok(queue, 'default LOCAL_BRAIN_QUEUE_TIMEOUT introuvable');
  assert.ok(chat, 'default LOCAL_BRAIN_CHAT_TIMEOUT introuvable');
  assert.ok(Number(queue[1]) >= 90, `file trop courte: ${queue[1]}s`);
  assert.ok(Number(queue[1]) < Number(chat[1]), 'la file doit rester sous le timeout client');
});

test('J128: le superviseur aligne la file du routeur sur le timeout client', async () => {
  const keeper = await readFile(KEEPER, 'utf8');
  assert.match(keeper, /\$queueTimeout\s*=\s*\[int\]\(\$env:LOCAL_BRAIN_QUEUE_TIMEOUT/);
  assert.match(keeper, /if \(\$queueTimeout -lt 30\) \{ \$queueTimeout = \$localTimeout - 20 \}/);
  assert.match(keeper, /Name='local-brain';\s+Port=31416;[\s\S]*?LOCAL_BRAIN_QUEUE_TIMEOUT="\$queueTimeout"/);
  assert.match(keeper, /ATULYA_MODEL_TIMEOUT="\$localTimeout"/);
});
