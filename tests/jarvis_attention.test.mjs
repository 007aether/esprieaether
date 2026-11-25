import test, { before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, writeFile, mkdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { buildAttention, createDashboardServer } from '../api/server.mjs';

let dir;
let reportsDir;
let ledgerPath;
let internetPath;
let server;
let base;

const reports = {
  'quality_guard_report.json': {
    checked_at: '2026-11-23T21:10:00',
    endpoints: 'up=10/10 down=none',
    checks: { python: true, dashboard: true, env: true, endpoints: true, graph: true },
    secret: 'do-not-expose-me',
  },
  'vault_guard_report.json': { checked_at: '2026-11-23T21:10:00', checks: { ok: true, nodes: 259, edges: 493 } },
  'backlog_scout_report.json': { checked_at: '2026-11-23T21:10:00', items: [], missing_sources: ['legal', 'fiscal', 'travail'] },
  'local_brain_verification.json': {
    checked_at: '2026-11-23T21:10:00',
    router_health: { active: 'dolphin3', available: ['dolphin3'], count: 1 },
    gateway_status: { provider: 'local-brain' },
  },
};

const ledger = {
  generatedAt: '2026-11-23T21:10:00Z',
  available: true,
  stats: { succeeded: 8, failed: 1, timed_out: 1, cancelled: 0, running: 0, total: 10 },
  runs: [
    { id: 12, action: 'scan', actor: 'SYS_04', status: 'failed', detail: 'api_key=supersecret host=127.0.0.1', createdAt: '2026-11-23T21:09:00Z' },
    { id: 11, action: 'decompile', actor: 'REA', status: 'succeeded', detail: 'friso.dll', createdAt: '2026-11-23T21:08:00Z' },
    { id: 10, action: 'connect', actor: 'SYS_01', status: 'timed_out', detail: 'timeout local', createdAt: '2026-11-23T21:07:00Z' },
  ],
};

before(async () => {
  dir = await mkdtemp(join(tmpdir(), 'sunnavok-attention-'));
  reportsDir = join(dir, 'reports');
  ledgerPath = join(dir, 'state', 'run_ledger.json');
  internetPath = join(dir, 'state', 'internet_status.json');
  await mkdir(reportsDir, { recursive: true });
  await mkdir(join(dir, 'state'), { recursive: true });
  for (const [name, value] of Object.entries(reports)) {
    await writeFile(join(reportsDir, name), JSON.stringify(value), 'utf8');
  }
  await writeFile(ledgerPath, JSON.stringify(ledger), 'utf8');
  await writeFile(internetPath, JSON.stringify({
    available: true, mode: 'internet', host: 'pypi.org',
    checkedAt: '2026-11-23T21:10:00Z', reason: null,
  }), 'utf8');
  server = createDashboardServer({ reportsDir, ledgerPath, internetPath, log: () => {} });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  base = `http://127.0.0.1:${server.address().port}`;
});

after(async () => {
  if (server) await new Promise((resolve) => server.close(resolve));
  if (dir) await rm(dir, { recursive: true, force: true });
});

test('attention: aucune action requise quand tout est vert', async () => {
  const result = await buildAttention(reportsDir, join(dir, 'state', 'absent.json'));
  assert.equal(result.available, true);
  assert.equal(result.ledger.available, false);
  assert.equal(result.ledger.reason, 'no_data_source');
  assert.equal(result.needsAttention, false);
});

test('attention: failed et timed_out remontent, succès non', async () => {
  const result = await buildAttention(reportsDir, ledgerPath);
  assert.equal(result.needsAttention, true);
  const ids = result.items.map((item) => item.id);
  assert.ok(ids.includes('run-12-failed'));
  assert.ok(ids.includes('run-10-timed_out'));
  assert.ok(!ids.includes('run-11-succeeded'));
  assert.ok(result.items.some((item) => item.id === 'source-legal-fiscal-travail'));
});

test('attention: zéro secret dans la réponse', async () => {
  const result = await buildAttention(reportsDir, ledgerPath);
  const body = JSON.stringify(result);
  assert.ok(!body.includes('do-not-expose-me'));
  assert.ok(!body.includes('supersecret'));
});

test('API: GET /api/jarvis/attention répond 200 et borné', async () => {
  const res = await fetch(`${base}/api/jarvis/attention`);
  assert.equal(res.status, 200);
  const body = await res.json();
  assert.equal(typeof body.needsAttention, 'boolean');
  assert.ok(Array.isArray(body.items));
  assert.ok(body.items.length <= 20);
  assert.ok(body.requestId);
});

test('attention: état vocal public, honnête et sans secret', async () => {
  const inboxPath = join(dir, 'state', 'voice_inbox.jsonl');
  const lockPath = join(dir, 'state', 'voice_daemon.lock');
  await writeFile(inboxPath, JSON.stringify({
    ok: true, heard: 'api_key=supersecret', reply: 'salam',
    spoken: true, ts: '2026-11-24T01:00:00+00:00',
  }) + '\n', 'utf8');
  await writeFile(lockPath, '4242', 'utf8');
  const statusPath = join(dir, 'state', 'voice_status.json');
  await writeFile(statusPath, JSON.stringify({
    stage: 'speaking', level: 0.72, updatedAt: '2026-11-24T01:02:00+00:00',
    reason: null, api_key: 'secret-in-status',
  }) + '\n', 'utf8');

  const result = await buildAttention(reportsDir, ledgerPath, internetPath,
    { inboxPath, lockPath, statusPath });
  assert.equal(result.voice.available, true);
  assert.equal(result.voice.mode, 'always_on_voice');
  assert.equal(result.voice.lastReply, 'salam');
  assert.equal(result.voice.stage, 'speaking');
  assert.equal(result.voice.level, 0.72);
  assert.equal(result.voice.statusAt, '2026-11-24T01:02:00+00:00');
  const body = JSON.stringify(result);
  assert.ok(!body.includes('supersecret'), 'secret vocal exposé');
  assert.ok(!body.includes('secret-in-status'), 'secret de statut exposé');

  const absent = await buildAttention(
    reportsDir, ledgerPath, internetPath,
    {
      inboxPath: join(dir, 'state', 'absent.jsonl'),
      lockPath: join(dir, 'state', 'absent.lock'),
      statusPath: join(dir, 'state', 'absent-status.json'),
    }
  );
  assert.equal(absent.voice.available, false);
  assert.equal(absent.voice.reason, 'no_data_source');
});

test('attention: état Internet public, honnête et sans secret', async () => {
  const result = await buildAttention(reportsDir, ledgerPath, internetPath);
  assert.equal(result.internet.available, true);
  assert.equal(result.internet.mode, 'internet');
  assert.equal(result.internet.host, 'pypi.org');
  const absent = await buildAttention(
    reportsDir, ledgerPath, join(dir, 'state', 'absent-internet.json')
  );
  assert.equal(absent.internet.available, false);
  assert.equal(absent.internet.reason, 'no_data_source');
});
