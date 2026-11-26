import test, { before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, writeFile, mkdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { buildCapabilities, createDashboardServer } from '../api/server.mjs';

let dir;
let reportsDir;
let learningPath;
let server;
let base;
const now = new Date().toISOString();

before(async () => {
  dir = await mkdtemp(join(tmpdir(), 'sunnavok-learning-'));
  reportsDir = join(dir, 'reports');
  await mkdir(reportsDir, { recursive: true });
  await mkdir(join(dir, 'state'), { recursive: true });
  learningPath = join(dir, 'state', 'learning_selfcheck.json');
  await writeFile(learningPath, JSON.stringify({
    ok: true,
    checkedAt: now,
    status: 'live_verified',
    engine: 'local_only',
    learnedCount: 7,
    sources: ['run_ledger.json', 'action_audit.jsonl'],
    lessons: [{ kind: 'approval', detail: 'token=TOPSECRETLEARN' }],
    topNote: 'preferences.md',
  }), 'utf8');
  server = createDashboardServer({ reportsDir, learningPath, log: () => {} });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  base = `http://127.0.0.1:${server.address().port}`;
});

after(async () => {
  if (server) await new Promise((resolve) => server.close(resolve));
  if (dir) await rm(dir, { recursive: true, force: true });
});

test('J114: /api/jarvis/learning expose uniquement un rapport public', async () => {
  const res = await fetch(`${base}/api/jarvis/learning`);
  assert.equal(res.status, 200);
  const body = await res.json();
  assert.equal(body.available, true);
  assert.equal(body.engine, 'local_only');
  assert.equal(body.learnedCount, 7);
  assert.equal(body.topNote, 'preferences.md');
  assert.equal(typeof body.requestId, 'string');
  const text = JSON.stringify(body);
  assert.ok(!text.includes('TOPSECRETLEARN'));
});

test('J114: sans preuve, le routeur dit no_data_source', async () => {
  const missing = join(dir, 'state', 'missing_learning.json');
  const empty = createDashboardServer({ reportsDir, learningPath: missing, log: () => {} });
  await new Promise((resolve) => empty.listen(0, '127.0.0.1', resolve));
  try {
    const res = await fetch(`http://127.0.0.1:${empty.address().port}/api/jarvis/learning`);
    assert.equal(res.status, 200);
    const body = await res.json();
    assert.equal(body.available, false);
    assert.equal(body.reason, 'no_data_source');
  } finally {
    await new Promise((resolve) => empty.close(resolve));
  }
});

test('J114: la capacité local-learning est honnête et périmée proprement', async () => {
  const fresh = await buildCapabilities(reportsDir, { learningPath });
  const item = fresh.capabilities.find((entry) => entry.id === 'local-learning');
  assert.ok(item, 'local-learning doit exister');
  assert.equal(item.status, 'live_verified');
  assert.ok(item.evidence.length > 0);
  assert.ok(item.next);

  const absent = await buildCapabilities(reportsDir, {
    learningPath: join(dir, 'state', 'absent.json'),
  });
  const missing = absent.capabilities.find((entry) => entry.id === 'local-learning');
  assert.equal(missing.status, 'not_available');
  for (const entry of [...fresh.capabilities, ...absent.capabilities]) {
    assert.ok(['live_verified', 'implemented_unverified', 'not_available',
      'needs_user_data'].includes(entry.status));
  }
});
