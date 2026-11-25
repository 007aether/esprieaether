import test, { before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, writeFile, mkdir, readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { buildActionApprovals, decideAction, createDashboardServer, ensureActionRequests } from '../api/server.mjs';

const ROOT = new URL('..', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const HUD = join(ROOT, 'esprieaether', 'G0DM0D3', 'out', 'jarvis.html');

let dir;
let statePath;
let auditPath;
let server;
let base;

const initial = [
  { id: 'act-1', action: 'run', target: 'scan local', reason: 'demande vocale', status: 'proposed', createdAt: '2026-11-24T03:00:00Z' },
  { id: 'act-2', action: 'write', target: 'api_key=abc123', reason: 'note', status: 'approved_once', createdAt: '2026-11-24T03:01:00Z' },
  { id: 'act-3', action: 'connect', target: 'loopback', status: 'denied', createdAt: '2026-11-24T03:02:00Z' },
  { id: 'act-4', action: 'scan', target: '127.0.0.1', status: 'proposed', createdAt: '2026-11-24T03:03:00Z' },
];

before(async () => {
  dir = await mkdtemp(join(tmpdir(), 'sunnavok-approvals-'));
  statePath = join(dir, 'state', 'action_requests.json');
  auditPath = join(dir, 'state', 'action_audit.jsonl');
  await mkdir(join(dir, 'state'), { recursive: true });
  await writeFile(statePath, JSON.stringify(initial), 'utf8');
  server = createDashboardServer({
    reportsDir: join(dir, 'empty-reports'),
    actionRequestsPath: statePath,
    actionAuditPath: auditPath,
    log: () => {},
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  base = `http://127.0.0.1:${server.address().port}`;
});

after(async () => {
  if (server) await new Promise((resolve) => server.close(resolve));
  if (dir) await rm(dir, { recursive: true, force: true });
});

test('C1: liste publique bornée, sans secret et honnête si absente', async () => {
  const live = await buildActionApprovals(statePath);
  assert.equal(live.available, true);
  assert.ok(live.items.length <= 20);
  assert.ok(live.items.some((item) => item.id === 'act-1' && item.status === 'proposed'));
  assert.ok(!JSON.stringify(live).includes('abc123'));
  const absent = await buildActionApprovals(join(dir, 'absent.json'));
  assert.equal(absent.available, false);
  assert.equal(absent.reason, 'no_data_source');
});

test('C1: le dossier d’actions est créé vide au premier démarrage', async () => {
  const bootstrap = join(dir, 'bootstrap', 'action_requests.json');
  await ensureActionRequests(bootstrap);
  const fresh = await buildActionApprovals(bootstrap);
  assert.equal(fresh.available, true);
  assert.deepEqual(fresh.items, []);
});

test('API: GET /api/jarvis/approvals répond 200', async () => {
  const res = await fetch(`${base}/api/jarvis/approvals`);
  assert.equal(res.status, 200);
  const body = await res.json();
  assert.ok(Array.isArray(body.items));
  assert.ok(body.requestId);
});

test('C2: décision explicite unique, journalisée, sans tiers', async () => {
  const res = await fetch(`${base}/api/jarvis/approvals/act-1`, {
    method: 'PUT',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ decision: 'approved_once' }),
  });
  assert.equal(res.status, 200);
  const body = await res.json();
  assert.equal(body.item.status, 'approved_once');
  const audit = await readFile(auditPath, 'utf8');
  assert.ok(audit.includes('proposed->approved_once'));
  const again = await fetch(`${base}/api/jarvis/approvals/act-1`, {
    method: 'PUT',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ decision: 'denied' }),
  });
  assert.equal(again.status, 409);
  const bad = await fetch(`${base}/api/jarvis/approvals/act-3`, {
    method: 'PUT',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ decision: 'approved_once' }),
  });
  assert.equal(bad.status, 409);
  const invalid = await fetch(`${base}/api/jarvis/approvals/act-1`, {
    method: 'PUT',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ decision: 'execute_now' }),
  });
  assert.equal(invalid.status, 400);
});

test('CSRF: PUT cross-origin refusé, PUT depuis le HUD loopback autorisé', async () => {
  const before = await readFile(statePath, 'utf8');
  const evil = await fetch(`${base}/api/jarvis/approvals/act-4`, {
    method: 'PUT',
    headers: { 'content-type': 'application/json', 'origin': 'https://attacker.example' },
    body: JSON.stringify({ decision: 'approved_once' }),
  });
  assert.equal(evil.status, 403);
  assert.equal(await readFile(statePath, 'utf8'), before);
  const local = await fetch(`${base}/api/jarvis/approvals/act-4`, {
    method: 'PUT',
    headers: { 'content-type': 'application/json', 'origin': 'http://127.0.0.1:3860' },
    body: JSON.stringify({ decision: 'approved_once' }),
  });
  assert.equal(local.status, 200);
});

test('HUD: panneau de décision local sans POST ni clique inline', async () => {
  const html = await readFile(HUD, 'utf8');
  assert.ok(html.includes('id="approvals"'), 'panneau approvals absent');
  assert.ok(/function\s+renderApprovals/.test(html), 'renderApprovals absent');
  assert.ok(html.includes('/jarvis/api/jarvis/approvals/'), 'route de décision absente');
  assert.ok(html.includes('addEventListener("click"'), 'décision par écouteur attendue');
  assert.ok(/method:\s*["']PUT["']/.test(html), 'décision par PUT local attendue');
  assert.ok(!/onclick|POST/.test(html), 'aucune commande inline ni POST');
  assert.ok(!html.includes('https://'), 'ressource externe');
});
