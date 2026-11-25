import test, { before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, writeFile, mkdir, readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { buildCapabilities, createDashboardServer } from '../api/server.mjs';

const ROOT = new URL('..', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const HUD = join(ROOT, 'esprieaether', 'G0DM0D3', 'out', 'jarvis.html');

let dir;
let reportsDir;
let metricsPath;
let actionsPath;
let voiceInboxPath;
let actionAuditPath;
let server;
let base;
let now;

const ALLOWED = new Set([
  'live_verified', 'implemented_unverified', 'not_available', 'needs_user_data',
]);

before(async () => {
  now = new Date().toISOString();
  dir = await mkdtemp(join(tmpdir(), 'sunnavok-capabilities-'));
  reportsDir = join(dir, 'reports');
  metricsPath = join(dir, 'state', 'brain_metrics.json');
  actionsPath = join(dir, 'state', 'action_requests.json');
  voiceInboxPath = join(dir, 'state', 'voice_inbox.jsonl');
  actionAuditPath = join(dir, 'state', 'action_audit.jsonl');
  await mkdir(reportsDir, { recursive: true });
  await mkdir(join(dir, 'state'), { recursive: true });
  await writeFile(join(reportsDir, 'quality_guard_report.json'), JSON.stringify({
    checked_at: now,
    checks: { python: true, dashboard: true, env: true, endpoints: true, graph: true },
    graph: { nodes: 259, edges: 493, graph_no_cdn: true },
    endpoints: 'up=10/10 down=none',
  }), 'utf8');
  await writeFile(join(reportsDir, 'local_brain_verification.json'), JSON.stringify({
    checked_at: now,
    router_health: { active: 'dolphin3', count: 3, available: ['dolphin3', 'hermes3', 'llama32uncensored'] },
    gateway_status: { provider: 'local-brain', api_key_configured: true },
  }), 'utf8');
  await writeFile(join(reportsDir, 'backlog_scout_report.json'), JSON.stringify({
    checked_at: now, items: [], missing_sources: ['legal', 'fiscal', 'travail'],
  }), 'utf8');
  await writeFile(metricsPath, JSON.stringify({
    available: true, model: 'dolphin3', promptTokens: 3991, completionTokens: 80,
    elapsedMs: 196700, tokensPerSecond: 0.41, reason: null, checkedAt: now,
  }), 'utf8');
  await writeFile(actionsPath, JSON.stringify([
    { id: 'act-1', action: 'run', target: 'scan', status: 'proposed', createdAt: '2026-11-24T03:00:00Z' },
  ]), 'utf8');
  await writeFile(voiceInboxPath, [
    { ok: true, spoken: true, engine: 'local-brain', reason: null, language: 'en', ts: now,
      heard: 'PRIVATE HEARD', reply: 'PRIVATE REPLY' },
    { ok: false, spoken: false, engine: 'local-brain', reason: 'barge_in', ts: now },
    { ok: true, spoken: true, engine: 'local-brain', ts: '2020-01-01T00:00:00Z' },
  ].map((item) => JSON.stringify(item)).join('\n') + '\n', 'utf8');
  await writeFile(actionAuditPath, `${JSON.stringify({
    at: now, id: 'act-1', from: 'proposed', to: 'done', actor: 'hud',
  })}\n`, 'utf8');
  server = createDashboardServer({
    reportsDir,
    brainMetricsPath: metricsPath,
    actionRequestsPath: actionsPath,
    voiceInboxPath,
    actionAuditPath,
    log: () => {},
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  base = `http://127.0.0.1:${server.address().port}`;
});

after(async () => {
  if (server) await new Promise((resolve) => server.close(resolve));
  if (dir) await rm(dir, { recursive: true, force: true });
});

function caps(reports, overrides = {}) {
  return buildCapabilities(reports, {
    brainMetricsPath: metricsPath,
    actionRequestsPath: actionsPath,
    voiceInboxPath,
    actionAuditPath,
    ...overrides,
  });
}

test('A2: chaque capacité a un statut honnête, une preuve et une étape suivante', async () => {
  const result = await caps(reportsDir);
  assert.equal(result.product, 'ESPRIEATHER');
  assert.ok(Array.isArray(result.capabilities));
  assert.ok(result.capabilities.length >= 5);
  for (const item of result.capabilities) {
    assert.ok(ALLOWED.has(item.status), `statut invalide: ${item.status}`);
    assert.ok(typeof item.id === 'string' && item.id);
    assert.ok(Array.isArray(item.evidence));
    assert.ok(typeof item.next === 'string' && item.next);
  }
  const ids = result.capabilities.map((item) => item.id);
  assert.ok(ids.includes('local-brain'));
  assert.ok(ids.includes('brain-metrics'));
  assert.ok(ids.includes('documentary-sources'));
  assert.ok(ids.includes('action-approval'));
  const brain = result.capabilities.find((item) => item.id === 'local-brain');
  assert.equal(brain.status, 'live_verified');
  const sources = result.capabilities.find((item) => item.id === 'documentary-sources');
  assert.equal(sources.status, 'needs_user_data');
});

test('A2: absence de preuve reste not_available, jamais une réussite inventée', async () => {
  const empty = await mkdtemp(join(dir, 'empty-'));
  const result = await caps(empty, {
    brainMetricsPath: join(empty, 'absent-metrics.json'),
    actionRequestsPath: join(empty, 'absent-actions.json'),
    voiceInboxPath: join(empty, 'absent-voice.jsonl'),
    actionAuditPath: join(empty, 'absent-audit.jsonl'),
  });
  const brain = result.capabilities.find((item) => item.id === 'local-brain');
  assert.equal(brain.status, 'not_available');
  const metrics = result.capabilities.find((item) => item.id === 'brain-metrics');
  assert.equal(metrics.status, 'not_available');
  const approval = result.capabilities.find((item) => item.id === 'action-approval');
  assert.equal(approval.status, 'implemented_unverified');
});

test('A2: une preuve périmée n’est plus live_verified', async () => {
  const staleDir = await mkdtemp(join(dir, 'stale-'));
  const old = '2020-01-01T00:00:00Z';
  await writeFile(join(staleDir, 'local_brain_verification.json'), JSON.stringify({
    checked_at: old, router_health: { active: 'dolphin3', count: 3 },
  }), 'utf8');
  await writeFile(join(staleDir, 'quality_guard_report.json'), JSON.stringify({
    checked_at: old, checks: { graph: true }, graph: { nodes: 259, graph_no_cdn: true },
  }), 'utf8');
  await writeFile(join(staleDir, 'backlog_scout_report.json'), JSON.stringify({
    checked_at: old, items: [], missing_sources: [],
  }), 'utf8');
  const staleMetrics = join(staleDir, 'brain_metrics.json');
  await writeFile(staleMetrics, JSON.stringify({
    available: true, tokensPerSecond: 1, elapsedMs: 1, checkedAt: old,
  }), 'utf8');
  const result = await caps(staleDir, {
    brainMetricsPath: staleMetrics,
    actionRequestsPath: join(staleDir, 'actions.json'),
    voiceInboxPath: join(staleDir, 'voice.jsonl'),
    actionAuditPath: join(staleDir, 'audit.jsonl'),
  });
  for (const id of ['local-brain', 'documentary-sources', 'secure-hud', 'brain-metrics']) {
    const item = result.capabilities.find((entry) => entry.id === id);
    assert.notEqual(item.status, 'live_verified', `${id} encore live_verified`);
    assert.ok(item.verifiedAt, `${id} sans verifiedAt`);
    assert.ok(Date.parse(item.expiresAt) < Date.now(), `${id} sans expiresAt périmé`);
  }
});

test('A2: zéro secret dans le registre public', async () => {
  const result = await caps(reportsDir);
  const body = JSON.stringify(result);
  assert.ok(!body.includes('api_key_configured'));
  assert.ok(!body.includes('secret'));
});

test('J87: preuves vocales et approval récentes, sans jamais exposer le texte entendu', async () => {
  const result = await caps(reportsDir);
  const ids = result.capabilities.map((item) => item.id);
  for (const id of ['local-voice', 'barge-in', 'action-approval']) {
    assert.ok(ids.includes(id), `capacité absente: ${id}`);
  }
  const voice = result.capabilities.find((item) => item.id === 'local-voice');
  const barge = result.capabilities.find((item) => item.id === 'barge-in');
  const approval = result.capabilities.find((item) => item.id === 'action-approval');
  assert.equal(voice.status, 'live_verified');
  assert.equal(barge.status, 'live_verified');
  assert.equal(approval.status, 'live_verified');
  for (const item of [voice, barge, approval]) {
    assert.ok(item.verifiedAt && item.expiresAt);
    assert.ok(!JSON.stringify(item).includes('PRIVATE'));
  }
});

test('J87: une preuve vocale périmée retombe en implemented_unverified', async () => {
  const staleDir = await mkdtemp(join(dir, 'stale-voice-'));
  const voicePath = join(staleDir, 'voice.jsonl');
  await writeFile(voicePath, `${JSON.stringify({
    ok: true, spoken: true, engine: 'local-brain', reason: null, ts: '2020-01-01T00:00:00Z',
  })}\n`, 'utf8');
  const result = await caps(reportsDir, { voiceInboxPath: voicePath });
  const voice = result.capabilities.find((item) => item.id === 'local-voice');
  assert.notEqual(voice.status, 'live_verified');
  assert.equal(voice.status, 'implemented_unverified');
});

test('API: GET /api/jarvis/capabilities répond 200 et borné', async () => {
  const res = await fetch(`${base}/api/jarvis/capabilities`);
  assert.equal(res.status, 200);
  const body = await res.json();
  assert.ok(Array.isArray(body.capabilities));
  assert.ok(body.capabilities.length <= 20);
  assert.ok(body.requestId);
  assert.ok(!JSON.stringify(body).includes('api_key_configured'));
});

test('HUD: panneau capacités branché, sans ressource externe ni commande', async () => {
  const html = await readFile(HUD, 'utf8');
  assert.ok(html.includes('id="capabilities"'), 'panneau capacités absent');
  assert.ok(html.includes('/jarvis/api/jarvis/capabilities'), 'endpoint capacités absent');
  assert.ok(/function\s+renderCapabilities/.test(html), 'renderCapabilities absent');
  assert.ok(/renderCapabilities\(/.test(html), 'render non branché');
  assert.ok(!/onclick|POST/.test(html), 'aucune commande depuis le HUD');
  assert.ok(!html.includes('https://'), 'ressource externe');
});
