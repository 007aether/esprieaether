import test, { before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, writeFile, mkdir, readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { buildSystemStatus, createDashboardServer } from '../api/server.mjs';

const ROOT = new URL('..', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const MAIN = join(ROOT, 'esprieaether', 'G0DM0D3', 'out', 'jarvis.html');
const SYSTEM = join(ROOT, 'esprieaether', 'G0DM0D3', 'out', 'system.html');

let dir;
let reportsDir;
let metricsPath;
let server;
let base;

before(async () => {
  dir = await mkdtemp(join(tmpdir(), 'sunnavok-system-hud-'));
  reportsDir = join(dir, 'reports');
  metricsPath = join(dir, 'state', 'brain_metrics.json');
  await mkdir(reportsDir, { recursive: true });
  await mkdir(join(dir, 'state'), { recursive: true });
  await writeFile(join(reportsDir, 'quality_guard_report.json'), JSON.stringify({
    checked_at: '2026-11-24T03:00:00',
    endpoints: 'up=10/10 down=none',
    checks: { python: true, dashboard: true, env: true, endpoints: true, graph: true },
    graph: { nodes: 259, edges: 493, graph_no_cdn: true },
  }), 'utf8');
  await writeFile(join(reportsDir, 'local_brain_verification.json'), JSON.stringify({
    router_health: { active: 'dolphin3', count: 3 },
  }), 'utf8');
  await writeFile(metricsPath, JSON.stringify({
    available: true, model: 'dolphin3', promptTokens: 3991, completionTokens: 80,
    elapsedMs: 196700, tokensPerSecond: 0.41, reason: null,
  }), 'utf8');
  server = createDashboardServer({ reportsDir, brainMetricsPath: metricsPath, log: () => {} });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  base = `http://127.0.0.1:${server.address().port}`;
});

after(async () => {
  if (server) await new Promise((resolve) => server.close(resolve));
  if (dir) await rm(dir, { recursive: true, force: true });
});

test('D2: mesure locale bornée et honnête quand la preuve manque', async () => {
  const live = await buildSystemStatus(reportsDir, metricsPath);
  assert.equal(live.brainMetrics.available, true);
  assert.equal(live.brainMetrics.elapsedMs, 196700);
  assert.equal(live.brainMetrics.tokensPerSecond, 0.41);
  const absent = await buildSystemStatus(reportsDir, join(dir, 'absent.json'));
  assert.equal(absent.brainMetrics.available, false);
  assert.equal(absent.brainMetrics.reason, 'no_data_source');
  assert.equal(absent.brainMetrics.tokensPerSecond, null);
  assert.ok(!JSON.stringify(live).includes('api_key_configured'));
});

test('API: /api/system/status publie la mesure locale', async () => {
  const res = await fetch(`${base}/api/system/status`);
  assert.equal(res.status, 200);
  const body = await res.json();
  assert.equal(body.brainMetrics.available, true);
  assert.ok(Number.isFinite(body.brainMetrics.tokensPerSecond));
});

test('D1: jarvis.html pilote des satellites depuis les états réels', async () => {
  const html = await readFile(MAIN, 'utf8');
  assert.ok(html.includes('id="satellites"'), 'satellites absents');
  for (const id of ['sat-brain', 'sat-voice', 'sat-services', 'sat-network']) {
    assert.ok(html.includes(`id="${id}"`), `satellite ${id} absent`);
  }
  assert.ok(/function\s+renderSatellites/.test(html), 'renderSatellites absent');
  assert.ok(/renderSatellites\(s,\s*d\)/.test(html), 'satellites non branchés sur SYS+ATT');
  assert.ok(!/onclick|POST/.test(html), 'aucune commande depuis le HUD');
  assert.ok(!html.includes('https://'), 'ressource externe');
});

test('D1/D2: system.html affiche satellites et mesure sans inventer de nombre', async () => {
  const html = await readFile(SYSTEM, 'utf8');
  assert.ok(html.includes('id="satellites"'), 'satellites absents');
  assert.ok(/function\s+renderSatellites/.test(html), 'renderSatellites absent');
  assert.ok(/renderSatellites\(s,\s*d\)/.test(html), 'satellites non branchés');
  assert.ok(html.includes('id="brainMetrics"'), 'tuile mesure absente');
  assert.ok(/function\s+renderBrainMetrics/.test(html), 'renderBrainMetrics absent');
  assert.ok(/renderBrainMetrics\(s\.brainMetrics\)/.test(html), 'mesure non branchée');
  assert.ok(html.includes('no_data_source'), 'statut honnête absent');
  assert.ok(!/onclick|POST/.test(html), 'aucune commande depuis le HUD');
  assert.ok(!html.includes('https://'), 'ressource externe');
});
