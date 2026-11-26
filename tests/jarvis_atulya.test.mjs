import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { buildAtulya, createDashboardServer } from '../api/server.mjs';

const ROOT = new URL('..', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const VENDOR = join(ROOT, 'GITHUB_IMPORT', 'Atulya-Tantra');
const HUD = join(ROOT, 'esprieaether', 'G0DM0D3', 'out', 'jarvis.html');
const ALLOWED = new Set([
  'live_verified', 'implemented_unverified', 'not_available', 'needs_user_data',
]);

test('J78: le module Atulya importé est inventorié sans secret', async () => {
  const result = await buildAtulya(VENDOR);
  assert.equal(result.source, 'atulyaai/Atulya-Tantra');
  assert.equal(result.imported, true);
  assert.ok(result.fileCount >= 300);
  assert.ok(Array.isArray(result.features) && result.features.length >= 5);
  const ids = result.features.map((item) => item.id);
  for (const id of ['atulya-core', 'atulya-voice', 'atulya-mcp', 'atulya-cloud', 'atulya-external']) {
    assert.ok(ids.includes(id), `fonctionnalité absente: ${id}`);
  }
  for (const item of result.features) {
    assert.ok(ALLOWED.has(item.status), `statut invalide: ${item.status}`);
    assert.ok(Array.isArray(item.evidence));
    assert.ok(typeof item.next === 'string' && item.next);
  }
  assert.doesNotMatch(JSON.stringify(result), /api[_-]?key\s*[:=]\s*["'][^"']+/i);
});

test('J78: le HUD affiche Atulya sans POST ni onclick', async () => {
  const html = await readFile(HUD, 'utf8');
  assert.match(html, /id="atulya"/);
  assert.match(html, /\/api\/jarvis\/atulya/);
  assert.doesNotMatch(html, /onclick/i);
  assert.doesNotMatch(html, /\bPOST\b/);
});

test('J95: le HUD ouvre Atulya dans un cadre local sans script externe', async () => {
  const html = await readFile(HUD, 'utf8');
  assert.match(html, /id="atulyaOpen"/);
  assert.match(html, /id="atulyaFrame"/);
  assert.match(html, /addEventListener\(['"]click['"]/);
  assert.match(html, /['"]\/atulya\/['"]/);
  assert.doesNotMatch(html, /onclick/i);
  assert.doesNotMatch(html, /telegram\.org\/js/i);
  assert.doesNotMatch(html, /https?:\/\/(cdn|unpkg|jsdelivr)/i);
});

test('J96: le lanceur ouvre le HUD local comme page de démarrage d’Atulya', async () => {
  const launcher = await readFile(join(ROOT, 'START_ATULYA_TANTRA.cmd'), 'utf8');
  assert.match(launcher, /set "ATULYA_LANDING_URL=http:\/\/127\.0\.0\.1:3860\/jarvis\.html"/);
  assert.match(launcher, /start "" http:\/\/127\.0\.0\.1:3860\/jarvis\.html/);
  const keeper = await readFile(join(ROOT, 'esprieaether', 'scripts', 'keep_alive.ps1'), 'utf8');
  assert.match(keeper, /ATULYA_LANDING_URL='http:\/\/127\.0\.0\.1:3860\/jarvis\.html'/);
});

test('J97: Atulya tourne en continu, au démarrage PC, toujours en arabe marocain', async () => {
  const launcher = await readFile(join(ROOT, 'START_ATULYA_TANTRA.cmd'), 'utf8');
  const keeper = await readFile(join(ROOT, 'esprieaether', 'scripts', 'keep_alive.ps1'), 'utf8');
  const startup = await readFile(join(ROOT, 'esprieaether', 'start_esprieaether_247.ps1'), 'utf8');
  // Arabe marocain forcé dans le lanceur ET dans chaque redémarrage du superviseur.
  assert.match(launcher, /set "ATULYA_FORCE_DARIJA=1"/);
  assert.match(keeper, /ATULYA_FORCE_DARIJA='1'/);
  // 24/7 : un seul superviseur, qui surveille Atulya et le HUD et les relance.
  assert.match(keeper, /SUNNAVOK_KEEPALIVE_7X24/);
  assert.match(keeper, /Name='atulya';\s+Port=8501/);
  assert.match(keeper, /Name='g0dm0d3-ui';\s+Port=3860/);
  assert.match(keeper, /8501 = '\/api\/health'/);
  assert.match(keeper, /3860 = '\/v1\/health'/);
  // Démarrage PC : une seule entrée, verrouillée et sans fenêtre visible.
  assert.match(startup, /SUNNAVOK_STARTUP_GATE/);
  assert.match(startup, /keep_alive\.ps1/);
  assert.match(startup, /-WindowStyle Hidden/);
  assert.doesNotMatch(startup, /https?:\/\//);
});

test('J106: le serveur journalise la cause des BrainError sans changer le message vocal', async () => {
  const server = await readFile(join(VENDOR, 'atulya', 'server.py'), 'utf8');
  assert.match(server, /record_brain_failure\(/);
  assert.match(server, /stage=["']chat_stream["']/);
  assert.match(server, /stage=["']chat_nonstream["']/);
  assert.match(server, /الجواب توقف فجأة/);
});

test('J108: le superviseur n envoie pas d ArgumentList vide et isole les pannes de demarrage', async () => {
  const keeper = await readFile(join(ROOT, 'esprieaether', 'scripts', 'keep_alive.ps1'), 'utf8');
  assert.match(keeper, /\$argList = @\(\$svc\.Args/);
  assert.match(keeper, /if \(\$argList\.Count -gt 0\)/);
  assert.match(keeper, /START_FAILED/);
  assert.match(keeper, /SkipStart=\$true/);
  assert.doesNotMatch(keeper, /Start-Process -FilePath \$svc\.Exe -ArgumentList @\(\$svc\.Args\)/);
});

test('J80: atulya-core est live_verified seulement avec une preuve HTTP locale', async () => {
  const live = await buildAtulya(VENDOR, async () => ({
    status: 'ok', brain_configured: true,
    voice_ready: false, speech_ready: false, vision_ready: false,
  }), join(ROOT, 'state', '__no_vision_evidence__.json'), undefined, undefined,
    join(ROOT, 'state', '__no_wake_evidence__.json'));
  const core = live.features.find((item) => item.id === 'atulya-core');
  assert.equal(core.status, 'live_verified');
  assert.equal(core.evidence[0].source, 'GET http://127.0.0.1:8501/api/health');
  assert.equal(core.evidence[0].field, 'status/brain_configured');
  assert.equal(core.evidence[0].value, 'ok/true');
  assert.ok(Date.parse(core.verifiedAt) <= Date.now());
  assert.ok(Date.parse(core.expiresAt) > Date.now());

  const offline = await buildAtulya(VENDOR, async () => null,
    join(ROOT, 'state', '__no_vision_evidence__.json'));
  const down = offline.features.find((item) => item.id === 'atulya-core');
  assert.equal(down.status, 'implemented_unverified');
  assert.equal(down.verifiedAt, null);

  const voice = live.features.find((item) => item.id === 'atulya-voice');
  const speech = live.features.find((item) => item.id === 'atulya-speech');
  const vision = live.features.find((item) => item.id === 'atulya-vision');
  const wake = live.features.find((item) => item.id === 'atulya-wake');
  assert.equal(voice.status, 'implemented_unverified');
  assert.equal(speech.status, 'not_available');
  assert.equal(vision.status, 'implemented_unverified');
  assert.equal(wake.status, 'implemented_unverified');
  assert.equal(wake.evidence[0].value, 'present');
  for (const item of [voice, speech, vision, wake]) {
    assert.ok(item.evidence[0].source.startsWith('GET http://127.0.0.1:8501/api/health'));
  }
});

test('J87: les flags réels de /api/health remplacent l’inventaire des fichiers', async () => {
  const ready = await buildAtulya(VENDOR, async () => ({
    status: 'ok', brain_configured: true,
    voice_ready: true, speech_ready: true, vision_ready: true,
  }), join(ROOT, 'state', '__no_vision_evidence__.json'), undefined, undefined,
    join(ROOT, 'state', '__no_wake_evidence__.json'));
  for (const id of ['atulya-voice', 'atulya-speech']) {
    const item = ready.features.find((entry) => entry.id === id);
    assert.equal(item.status, 'live_verified', `${id} devrait être live_verified`);
    assert.equal(item.evidence[0].field, 'voice_ready/speech_ready/vision_ready'.split('/')[
      ['atulya-voice', 'atulya-speech', 'atulya-vision'].indexOf(id)]);
    assert.equal(item.evidence[0].value, 'true');
  }
  const vision = ready.features.find((item) => item.id === 'atulya-vision');
  assert.equal(vision.status, 'implemented_unverified');
  const wake = ready.features.find((item) => item.id === 'atulya-wake');
  assert.equal(wake.status, 'implemented_unverified');
  assert.equal(wake.evidence[0].value, 'present');
});

test('J88: vision est live_verified seulement avec une inférence locale récente', async (t) => {
  const dir = await mkdtemp(join(tmpdir(), 'sunnavok-vision-'));
  t.after(() => rm(dir, { recursive: true, force: true }));
  const evidencePath = join(dir, 'vision_selfcheck.json');
  const probe = async () => ({
    status: 'ok', brain_configured: true,
    voice_ready: true, speech_ready: true, vision_ready: true,
  });
  const getVision = async () => (await buildAtulya(VENDOR, probe, evidencePath))
    .features.find((item) => item.id === 'atulya-vision');

  assert.equal((await getVision()).status, 'implemented_unverified');
  await writeFile(evidencePath, JSON.stringify({
    ok: true, checkedAt: new Date().toISOString(), answer: 'un cercle rouge',
    model: 'Qwen_Qwen3.5-2B-Q4_K_M.gguf',
  }));
  const fresh = await getVision();
  assert.equal(fresh.status, 'live_verified');
  assert.equal(fresh.evidence[0].field, 'local_vision_inference');
  assert.equal(fresh.evidence[0].value, 'true');
  assert.ok(fresh.verifiedAt);
  assert.ok(Date.parse(fresh.expiresAt) > Date.now());

  await writeFile(evidencePath, JSON.stringify({
    ok: false, checkedAt: new Date().toISOString(),
  }));
  assert.equal((await getVision()).status, 'implemented_unverified');
});

test('J89: mcp est live_verified seulement avec une poignée de main stdio récente', async (t) => {
  const dir = await mkdtemp(join(tmpdir(), 'sunnavok-mcp-'));
  t.after(() => rm(dir, { recursive: true, force: true }));
  const evidencePath = join(dir, 'mcp_selfcheck.json');
  const probe = async () => ({
    status: 'ok', brain_configured: true,
    voice_ready: false, speech_ready: false, vision_ready: false,
  });
  const getMcp = async () => (await buildAtulya(
    VENDOR, probe, join(dir, '__none__.json'), evidencePath,
  )).features.find((item) => item.id === 'atulya-mcp');

  assert.equal((await getMcp()).status, 'implemented_unverified');
  await writeFile(evidencePath, JSON.stringify({
    ok: true, checkedAt: new Date().toISOString(), transport: 'stdio',
    tools: ['calculate', 'get_time'],
  }));
  const fresh = await getMcp();
  assert.equal(fresh.status, 'live_verified');
  assert.equal(fresh.evidence[0].field, 'local_mcp_handshake');
  assert.equal(fresh.evidence[0].value, 'true');
  assert.ok(fresh.verifiedAt);
});

test('J90: vault-memory est live_verified seulement avec un index local récent', async (t) => {
  const dir = await mkdtemp(join(tmpdir(), 'sunnavok-vault-'));
  t.after(() => rm(dir, { recursive: true, force: true }));
  const evidencePath = join(dir, 'vault_memory_selfcheck.json');
  const probe = async () => ({
    status: 'ok', brain_configured: true,
    voice_ready: false, speech_ready: false, vision_ready: false,
  });
  const getVault = async () => (await buildAtulya(
    VENDOR, probe, join(dir, '__none_v__.json'), join(dir, '__none_m__.json'), evidencePath,
  )).features.find((item) => item.id === 'atulya-vault-memory');

  assert.equal((await getVault()).status, 'implemented_unverified');
  await writeFile(evidencePath, JSON.stringify({
    ok: true, checkedAt: new Date().toISOString(), noteCount: 212,
    topPath: 'Services/atulya.md', engine: 'local_bm25',
  }));
  const fresh = await getVault();
  assert.equal(fresh.status, 'live_verified');
  assert.equal(fresh.evidence[0].field, 'local_vault_index');
  assert.equal(fresh.evidence[0].value, 'true');
  assert.ok(fresh.verifiedAt);

  await writeFile(evidencePath, JSON.stringify({ ok: false, checkedAt: new Date().toISOString() }));
  assert.equal((await getVault()).status, 'implemented_unverified');
});

test('J78: GET /api/jarvis/atulya répond en loopback', async (t) => {
  const server = createDashboardServer({ log: () => {} });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise((resolve) => {
    server.closeAllConnections?.();
    server.close(resolve);
  }));
  const base = `http://127.0.0.1:${server.address().port}`;
  const response = await fetch(`${base}/api/jarvis/atulya`, {
    headers: { connection: 'close' },
  });
  assert.equal(response.status, 200);
  const body = await response.json();
  assert.equal(body.source, 'atulyaai/Atulya-Tantra');
  assert.equal(typeof body.requestId, 'string');
});
