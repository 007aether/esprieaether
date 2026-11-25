import test, { before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdir, mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { buildAgentDigest, createDashboardServer } from '../api/server.mjs';
import { STATE_VERSION, validateState, normalizeState } from '../shared/contract.mjs';

const validState = () => ({
  version: STATE_VERSION,
  fields: { 'f-a': '1,20', 'g-rate': '15' },
  products: [{ name: 'فرن 1.50 م', qty: '3' }],
  inventory: [{ name: 'لحام', qty: '1', cond: 'جديدة', owner: 'SEI', price: '1200' }],
  todo: { c1: true, c2: false },
});

let tempDir;
let statePath;
let reportsDir;
let server;
let base;
const logEntries = [];

const REPORT_FIXTURES = {
  'quality_guard_report.json': {
    checked_at: '2026-11-23T02:19:16',
    python: { ran: 53, ok: true },
    dashboard: { passed: 3, failed: 0 },
    env: { hash_matches: true },
    endpoints: 'up=10/10 down=none',
    graph: { nodes: 259, edges: 493, graph_jarvis_brain_edge: true, ok: true },
    checks: { python: true, dashboard: true, env: true, endpoints: true, graph: true },
  },
  'vault_guard_report.json': {
    checked_at: '2026-11-23T02:19:28',
    checks: { jarvis_port_5000: true, jarvis_verified: true, nodes: 259, edges: 493, ok: true },
  },
  'backlog_scout_report.json': {
    checked_at: '2026-11-23T02:19:28',
    items: [],
    missing_sources: ['legal', 'fiscal', 'travail'],
  },
  'local_brain_verification.json': {
    checked_at: '2026-11-23T00:33:23+00:00',
    router_health: { active: 'dolphin3', available: ['dolphin3', 'hermes3', 'llama32uncensored'], count: 3 },
    router_models: ['dolphin3', 'hermes3', 'llama32uncensored'],
    gateway_status: { provider: 'local-brain' },
    gateway_completion: { routed_via: 'local-brain', status: 'success' },
    sentinel: ['ok', 'up=10/10 down=none'],
  },
  'agent_audit_report.json': {
    checked_at: '2026-11-23T03:00:00',
    available: true,
    source: 'PROJECT_MAP.md',
    latest: 'J36',
    items: [
      { id: 'J35', detail: 'Audit A→E terminé' },
      { id: 'J36', detail: 'Queue d’audit terminée' },
      { id: 'J37', detail: 'x'.repeat(400) },
    ],
    secret: 'do-not-expose-me',
  },
};

before(async () => {
  tempDir = await mkdtemp(join(tmpdir(), 'sunnavok-test-'));
  statePath = join(tempDir, 'state', 'dashboard.json');
  reportsDir = join(tempDir, 'reports');
  await mkdir(reportsDir, { recursive: true });
  for (const [name, value] of Object.entries(REPORT_FIXTURES)) {
    await writeFile(join(reportsDir, name), JSON.stringify(value), 'utf8');
  }
  server = createDashboardServer({ statePath, reportsDir, log: (entry) => logEntries.push(entry) });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  base = `http://127.0.0.1:${server.address().port}`;
});

after(async () => {
  if (server) await new Promise((resolve) => server.close(resolve));
  if (tempDir) await rm(tempDir, { recursive: true, force: true });
});

test('contract: accepte un état valide et rejette les énumérations et la version', () => {
  assert.equal(validateState(validState()), null);
  const badCond = validState();
  badCond.inventory[0].cond = 'غير معروف';
  assert.equal(validateState(badCond), 'CONDITION_INVALID');
  const badOwner = validState();
  badOwner.inventory[0].owner = 'غير معروف';
  assert.equal(validateState(badOwner), 'OWNER_INVALID');
  const badVersion = validState();
  badVersion.version = 99;
  assert.equal(validateState(badVersion), 'VERSION_UNSUPPORTED');
  assert.deepEqual(normalizeState(validState()).fields['f-notes'], '');
});

test('API: GET initial, PUT valide, persistance, PUT invalide sans altérer le fichier', async () => {
  const initial = await fetch(`${base}/api/dashboard/state`);
  assert.equal(initial.status, 200);
  assert.equal((await initial.json()).state, null);

  const saved = await fetch(`${base}/api/dashboard/state`, {
    method: 'PUT',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(validState()),
  });
  assert.equal(saved.status, 200);
  const savedBody = await saved.json();
  assert.ok(savedBody.requestId);
  assert.equal(savedBody.state.fields['f-a'], '1,20');

  const reread = await (await fetch(`${base}/api/dashboard/state`)).json();
  assert.equal(reread.state.todo.c1, true);

  const before = await readFile(statePath, 'utf8');
  const rejected = await fetch(`${base}/api/dashboard/state`, {
    method: 'PUT',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ ...validState(), inventory: [{ name: 'x', cond: 'خاطئ', owner: 'SEI' }] }),
  });
  assert.equal(rejected.status, 400);
  const err = await rejected.json();
  assert.equal(err.code, 'CONDITION_INVALID');
  assert.ok(err.requestId);
  assert.equal(await readFile(statePath, 'utf8'), before);

  const restarted = createDashboardServer({ statePath, log: () => {} });
  await new Promise((resolve) => restarted.listen(0, '127.0.0.1', resolve));
  try {
    const url = `http://127.0.0.1:${restarted.address().port}/api/dashboard/state`;
    assert.equal((await (await fetch(url)).json()).state.fields['f-a'], '1,20');
  } finally {
    await new Promise((resolve) => restarted.close(resolve));
  }
});

test('CSRF: PUT cross-origin refusé sans écrire l’état local', async () => {
  const before = await readFile(statePath, 'utf8');
  const evil = await fetch(`${base}/api/dashboard/state`, {
    method: 'PUT',
    headers: { 'content-type': 'application/json', 'origin': 'https://attacker.example' },
    body: JSON.stringify(validState()),
  });
  assert.equal(evil.status, 403);
  assert.equal(await readFile(statePath, 'utf8'), before);
});

test('GUI: la page reçoit le bootstrap sans injection brute et les logs restent anonymes', async () => {
  const html = await (await fetch(`${base}/`)).text();
  assert.match(html, /<script id="sunnavok-initial-state" type="application\/json">/);
  assert.match(html, /007aether\/esprieaether/);
  assert.doesNotMatch(html, /<script id="sunnavok-initial-state"[^>]*>[\s\S]*<\/script>[\s\S]*<script id="sunnavok-initial-state"/);
  const payload = html.match(/<script id="sunnavok-initial-state" type="application\/json">([\s\S]*?)<\/script>/)[1];
  assert.doesNotMatch(payload, /</);
  const parsed = JSON.parse(payload);
  assert.equal(parsed.state.fields['f-a'], '1,20');
  assert.ok(parsed.enums.conditions.includes('جديدة'));

  const serialized = JSON.stringify(logEntries);
  assert.doesNotMatch(serialized, /فرن 1\.50 م|1200/);
  for (const entry of logEntries) {
    assert.deepEqual(Object.keys(entry).sort(), ['durationMs', 'method', 'path', 'requestId', 'status']);
    assert.doesNotMatch(entry.path, /api\/dashboard\/state\/f-/);
  }
});

test('Santé: /health répond sans exposer de donnée ni de secret', async () => {
  const response = await fetch(`${base}/health`);
  assert.equal(response.status, 200);
  const body = await response.json();
  assert.equal(body.status, 'ok');
  assert.equal(body.service, 'sunnavok-dashboard');
  assert.ok(body.time);
  assert.doesNotMatch(JSON.stringify(body), /frn|1200|de9449/i);
});

test('CORS: seules les origines locales sont autorisées', async () => {
  const local = await fetch(`${base}/health`, { headers: { origin: 'http://127.0.0.1:5000' } });
  assert.equal(local.headers.get('access-control-allow-origin'), 'http://127.0.0.1:5000');
  const foreign = await fetch(`${base}/health`, { headers: { origin: 'https://evil.example' } });
  assert.equal(foreign.headers.get('access-control-allow-origin'), null);
});

test('État système: agrège les rapports réels et reste honnête s\'ils manquent', async () => {
  const response = await fetch(`${base}/api/system/status`);
  assert.equal(response.status, 200);
  const body = await response.json();
  assert.equal(body.available, true);
  assert.equal(body.robots.sentinel.summary, 'up=10/10 down=none');
  assert.equal(body.robots.quality.pythonRan, 53);
  assert.equal(body.robots.quality.envHashMatches, true);
  assert.deepEqual(body.robots.backlog.missingSources, ['legal', 'fiscal', 'travail']);
  assert.equal(body.robots.vault.ok, true);
  assert.equal(body.brains.count, 3);
  assert.equal(body.brains.active, 'dolphin3');
  assert.equal(body.brains.provider, 'local-brain');
  assert.equal(body.brains.routedVia, 'local-brain');
  assert.equal(body.graph.nodes, 259);
  assert.equal(body.graph.edges, 493);
  assert.ok(body.checkedAt);

  const emptyDir = join(tempDir, 'empty-reports');
  await mkdir(emptyDir, { recursive: true });
  const emptyServer = createDashboardServer({ statePath, reportsDir: emptyDir, log: () => {} });
  await new Promise((resolve) => emptyServer.listen(0, '127.0.0.1', resolve));
  try {
    const url = `http://127.0.0.1:${emptyServer.address().port}/api/system/status`;
    const missing = await (await fetch(url)).json();
    assert.equal(missing.available, false);
    assert.equal(missing.brains.count, 0);
    assert.equal(missing.graph.nodes, null);
    assert.equal(missing.robots.quality.pythonRan, null);
  } finally {
    await new Promise((resolve) => emptyServer.close(resolve));
  }
});

test('Rapport exécutif: Markdown lisible, sans secret, et honnête sans état', async () => {
  const response = await fetch(`${base}/api/report`);
  assert.equal(response.status, 200);
  assert.match(response.headers.get('content-type'), /text\/markdown/);
  const text = await response.text();
  assert.match(text, /SUNNAVOK/);
  assert.match(text, /فرن 1\.50 م/);
  assert.match(text, /up=10\/10 down=none/);
  assert.match(text, /dolphin3/);
  assert.match(text, /legal, fiscal, travail/);
  assert.doesNotMatch(text, /de9449/i);

  const emptyReports = join(tempDir, 'empty-reports-for-report');
  await mkdir(emptyReports, { recursive: true });
  const emptyServer = createDashboardServer({
    statePath: join(tempDir, 'missing-state.json'), reportsDir: emptyReports, log: () => {},
  });
  await new Promise((resolve) => emptyServer.listen(0, '127.0.0.1', resolve));
  try {
    const url = `http://127.0.0.1:${emptyServer.address().port}/api/report`;
    const empty = await (await fetch(url)).text();
    assert.match(empty, /aucune donnée enregistrée/i);
    assert.match(empty, /statut indisponible/i);
  } finally {
    await new Promise((resolve) => emptyServer.close(resolve));
  }
});

test('Journal d’audit: endpoint local, borné, sans secret et honnête sans rapport', async () => {
  const response = await fetch(`${base}/api/agent/audit`);
  assert.equal(response.status, 200);
  const body = await response.json();
  assert.equal(body.available, true);
  assert.equal(body.latest, 'J36');
  assert.equal(body.items.length, 3);
  assert.deepEqual(Object.keys(body.items[0]).sort(), ['detail', 'id']);
  assert.ok(body.items[2].detail.length <= 240);
  assert.ok(!JSON.stringify(body).includes('do-not-expose-me'));
  assert.ok(body.requestId);

  const emptyDir = join(tempDir, 'empty-audit-reports');
  await mkdir(emptyDir, { recursive: true });
  const empty = await buildAgentDigest(emptyDir);
  assert.equal(empty.available, false);
  assert.equal(empty.reason, 'no_data_source');
  assert.deepEqual(empty.items, []);
});

test('GUI: aucune ressource externe, contrôles de statut/rapport/backup présents', async () => {
  const html = await (await fetch(`${base}/`)).text();
  assert.doesNotMatch(html, /<link[^>]+href=["']https?:\/\//);
  assert.doesNotMatch(html, /<script[^>]+src=["']https?:\/\//);
  assert.match(html, /id="system-status"/);
  assert.match(html, /id="agent-audit-feed"/);
  assert.match(html, /id="audit-refresh"/);
  assert.match(html, /id="report-btn"/);
  assert.match(html, /id="json-export-btn"/);
  assert.match(html, /id="json-import-input"/);
  assert.match(html, /id="home-batch"/);
  const js = await (await fetch(`${base}/app.js`)).text();
  assert.match(js, /api\/system\/status/);
  assert.match(js, /api\/agent\/audit/);
  assert.match(js, /api\/report/);
  assert.match(js, /FileReader/);
});
