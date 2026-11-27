import test, { after, before } from 'node:test';
import assert from 'node:assert/strict';
import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import {
  withTtlCache, readGsmSnapshot, readIntegrationCatalog, readHomedockWidgets,
} from '../api/rest_services.mjs';
import { createDashboardServer } from '../api/server.mjs';

let dir;
let server;
let base;
let gsmStatusPath;
let gsmWorkersPath;
let gsmModelTrialPath;
let integrationsDir;
let reportsDir;
let kanbanPath;

const now = new Date().toISOString();
const stale = new Date(Date.now() - 8 * 24 * 60 * 60 * 1000).toISOString();

function gsmFixture(checkedAt = now) {
  return {
    ok: true,
    status: 'live_verified',
    readOnly: true,
    checkedAt,
    expiresAt: checkedAt,
    online: 10,
    discovered: 10,
    devices: [
      { serial: 'aaa', model: 'SM-G955U1', sim_state: 'READY', battery_level: 91,
        abi: 'arm64-v8a', root: false, termux: false },
      { serial: 'bbb', model: 'SM-G9550', sim_state: 'ABSENT', battery_level: 42,
        abi: 'arm64-v8a', root: false, termux: false },
    ],
    errors: [],
  };
}

before(async () => {
  dir = await mkdtemp(join(tmpdir(), 'sunnavok-rest2-'));
  gsmStatusPath = join(dir, 'gsm_status.json');
  gsmWorkersPath = join(dir, 'gsm_workers.json');
  gsmModelTrialPath = join(dir, 'gsm_model_trial.json');
  integrationsDir = join(dir, 'integrations');
  reportsDir = join(dir, 'reports');
  kanbanPath = join(dir, 'kanban.md');
  await mkdir(integrationsDir, { recursive: true });
  await mkdir(reportsDir, { recursive: true });
  await writeFile(gsmStatusPath, JSON.stringify(gsmFixture()), 'utf8');
  await writeFile(gsmWorkersPath, JSON.stringify({ status: 'needs_user_data', online: 0 }), 'utf8');
  await writeFile(gsmModelTrialPath, JSON.stringify({
    status: 'needs_user_data', ready: false, reason: 'fichiers absents', maxModelMb: 600,
  }), 'utf8');
  await mkdir(join(integrationsDir, 'alpha'), { recursive: true });
  await writeFile(join(integrationsDir, 'alpha', 'package.json'), '{}\n', 'utf8');
  await writeFile(join(integrationsDir, 'beta'), 'x', 'utf8');
  await writeFile(join(reportsDir, 'one.json'), '{}', 'utf8');
  await writeFile(kanbanPath, '# board\n\n## todo\n- [ ] tâche\n\n## doing\n\n## done\n', 'utf8');
  server = createDashboardServer({
    gsmStatusPath, gsmWorkersPath, gsmModelTrialPath, integrationsDir, reportsDir, kanbanPath,
    log: () => {},
  });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  base = `http://127.0.0.1:${server.address().port}`;
});

after(async () => {
  if (server) await new Promise((resolve) => server.close(resolve));
  if (dir) await rm(dir, { recursive: true, force: true });
});

test('REST J154: withTtlCache ne recharge pas tant que le TTL n’est pas dépassé', async () => {
  const cache = new Map();
  let clock = 1000;
  let reads = 0;
  const loader = async () => { reads += 1; return { reads }; };
  const options = { cache, ttlMs: 1000, now: () => clock };
  assert.equal((await withTtlCache('a', loader, options)).reads, 1);
  assert.equal((await withTtlCache('a', loader, options)).reads, 1);
  assert.equal(reads, 1);
  clock += 1001;
  assert.equal((await withTtlCache('a', loader, options)).reads, 2);
  assert.equal(reads, 2);
});

test('REST J154: readGsmSnapshot ne certifie que la preuve fraîche', async () => {
  const paths = { gsmStatusPath, gsmWorkersPath, gsmModelTrialPath };
  const fresh = await readGsmSnapshot(paths);
  assert.equal(fresh.status, 'live_verified');
  assert.equal(fresh.fresh, true);
  assert.equal(fresh.alert, null);
  assert.equal(fresh.online, 10);
  assert.equal(fresh.readOnly, true);
  assert.equal(fresh.simReady, 1);
  assert.equal(fresh.devices.length, 2);

  await writeFile(gsmStatusPath, JSON.stringify(gsmFixture(stale)), 'utf8');
  const old = await readGsmSnapshot(paths);
  assert.equal(old.status, 'implemented_unverified');
  assert.equal(old.fresh, false);
  assert.equal(old.alert, 'expired');

  await rm(gsmStatusPath);
  const none = await readGsmSnapshot(paths);
  assert.equal(none.status, 'needs_user_data');
  assert.equal(none.alert, 'no_evidence');
  await writeFile(gsmStatusPath, JSON.stringify(gsmFixture()), 'utf8');
});

test('REST J154: readIntegrationCatalog détecte la stack sans rien exécuter', async () => {
  const catalog = await readIntegrationCatalog(integrationsDir);
  assert.equal(catalog.count, 1);
  assert.deepEqual(catalog.integrations[0], { name: 'alpha', stack: 'node', status: 'present' });
});

test('REST J154: readHomedockWidgets agrège les fichiers locaux', async () => {
  const widgets = await readHomedockWidgets({ reportsDir, gsmStatusPath, kanbanPath });
  assert.equal(widgets.reports, 1);
  assert.equal(widgets.gsm.status, 'live_verified');
  assert.equal(widgets.kanban.todo, 1);
});

test('REST J154: la passerelle sert GSM, integrations et homedock', async () => {
  const gsm = await fetch(`${base}/api/rest/gsm/status`);
  assert.equal(gsm.status, 200);
  const body = await gsm.json();
  assert.equal(body.status, 'live_verified');
  assert.equal(body.readOnly, true);
  assert.equal(typeof body.requestId, 'string');

  const integrations = await fetch(`${base}/api/rest/integrations/list`);
  assert.equal(integrations.status, 200);
  assert.equal((await integrations.json()).count, 1);

  const widgets = await fetch(`${base}/api/rest/homedock/widgets`);
  assert.equal(widgets.status, 200);
  assert.equal((await widgets.json()).reports, 1);
});

test('J155: la page d’accueil affiche un état GSM réel, pas une statique', async () => {
  const response = await fetch(`${base}/`);
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /id="gsm-status"/);
  assert.match(html, /id="gsm-refresh"/);
  assert.match(html, /id="gsm-alert"/);
  const script = await (await fetch(`${base}/app.js`)).text();
  assert.match(script, /\/api\/rest\/gsm\/status/);
  assert.match(script, /refreshGsmStatus/);
});
