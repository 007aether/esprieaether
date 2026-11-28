import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, writeFile, readFile, mkdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { publicVoice } from '../api/server.mjs';

const ROOT = new URL('..', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const HUD = join(ROOT, 'esprieaether', 'G0DM0D3', 'out', 'jarvis.html');

test('publicVoice expose le dernier résultat PC sans secret', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'sunnavok-pc-hud-'));
  try {
    await mkdir(join(dir, 'state'), { recursive: true });
    const pcActionPath = join(dir, 'state', 'pc_action_last.json');
    await writeFile(pcActionPath, JSON.stringify({
      id: 'act-abc', kind: 'run_command', status: 'executed', executed: true,
      text: 'نفّذت الأمر: token=secret123 todo', checkedAt: '2026-11-28T00:00:00+00:00',
    }), 'utf8');
    const voice = await publicVoice({
      inboxPath: join(dir, 'state', 'voice_inbox.jsonl'),
      lockPath: join(dir, 'state', 'voice_daemon.lock'),
      statusPath: join(dir, 'state', 'voice_status.json'),
      pcActionPath,
    });
    assert.equal(voice.lastAction.id, 'act-abc');
    assert.equal(voice.lastAction.executed, true);
    assert.match(voice.lastAction.text, /<redacted>/);
    assert.doesNotMatch(voice.lastAction.text, /secret123/);
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
});

test('HUD affiche le résultat et le fait parler sans POST ni onclick', async () => {
  const html = await readFile(HUD, 'utf8');
  assert.match(html, /id="pcAction"/);
  assert.match(html, /id="pcSpeakBtn"/);
  assert.match(html, /speakPcAction/);
  assert.match(html, /lastAction/);
  assert.match(html, /\$\("pcSpeakBtn"\)\.addEventListener\("click"/);
  assert.match(html, /\/local-voice\/say\?text=/);
  assert.doesNotMatch(html, /onclick/i);
  assert.doesNotMatch(html, /\bPOST\b/);
});
