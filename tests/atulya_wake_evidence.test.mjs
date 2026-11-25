import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { buildAtulya } from '../api/server.mjs';

const ROOT = new URL('..', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const CLI = join(ROOT, 'GITHUB_IMPORT', 'Atulya-Tantra', 'tools', 'voice_loop', '__main__.py');
const TTL = 8 * 24 * 60 * 60 * 1000;

async function fixture() {
  const dir = await mkdtemp(join(tmpdir(), 'atulya-wake-'));
  const paths = {
    actionRequestsPath: join(dir, 'action_requests.json'),
    actionAuditPath: join(dir, 'action_audit.jsonl'),
    voiceStatusPath: join(dir, 'voice_status.json'),
    voiceInboxPath: join(dir, 'voice_inbox.jsonl'),
    egressPath: join(dir, 'egress_selfcheck.json'),
    bargeReviewPath: join(dir, 'barge_in_review.json'),
    wakeEvidencePath: join(dir, 'wake_selfcheck.json'),
  };
  await writeFile(paths.actionRequestsPath, '[]\n', 'utf8');
  return { dir, paths };
}

function wakeOf(result) {
  return result.features.find((item) => item.id === 'atulya-wake');
}

function atulya(dir, paths) {
  return buildAtulya(
    join(ROOT, 'GITHUB_IMPORT', 'Atulya-Tantra'),
    async () => null,
    join(dir, 'vision_selfcheck.json'),
    join(dir, 'mcp_selfcheck.json'),
    join(dir, 'vault_memory_selfcheck.json'),
    paths.wakeEvidencePath,
  );
}

test('J103: le test de réveil peut écrire une preuve locale datée', async () => {
  const source = await readFile(CLI, 'utf8');
  assert.match(source, /--evidence/);
  assert.match(source, /"ok":\s*hits\s*>\s*0/);
  assert.match(source, /"hits":\s*hits/);
  assert.match(source, /"ts":/);
  assert.match(source, /"model":/);
});

test('J103: une détection récente rend atulya-wake live_verified', async () => {
  const { dir, paths } = await fixture();
  try {
    const evidence = {
      ok: true, hits: 2, peak: 0.31, model: 'hey_jarvis_v0.1.onnx',
      ts: new Date().toISOString(),
    };
    await writeFile(paths.wakeEvidencePath, `${JSON.stringify(evidence)}\n`, 'utf8');
    const result = await atulya(dir, paths);
    const wake = wakeOf(result);
    assert.equal(wake.status, 'live_verified');
    assert.ok(wake.evidence.some((item) => item.source === 'wake_selfcheck.json' && item.field === 'hits'));
    assert.ok(wake.verifiedAt);
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
});

test('J103: une preuve absente ou périmée reste implemented_unverified', async () => {
  const { dir, paths } = await fixture();
  try {
    await writeFile(paths.wakeEvidencePath, `${JSON.stringify({
      ok: true, hits: 1, ts: new Date(Date.now() - TTL).toISOString(),
    })}\n`, 'utf8');
    const result = await atulya(dir, paths);
    const wake = wakeOf(result);
    assert.equal(wake.status, 'implemented_unverified');
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
});
