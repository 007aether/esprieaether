import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createDashboardServer } from '../api/server.mjs';

test('J195: /api/rest/gsm/compute lit le dossier local et reste honnête', async (t) => {
  const dir = await mkdtemp(join(tmpdir(), 'sunnavok-gsm-compute-'));
  const file = join(dir, 'gsm_compute.json');
  const server = createDashboardServer({ gsmComputePath: file, log: () => {} });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  const base = `http://127.0.0.1:${server.address().port}`;
  t.after(async () => {
    await new Promise((resolve) => server.close(resolve));
    await rm(dir, { recursive: true, force: true });
  });

  let res = await fetch(`${base}/api/rest/gsm/compute`);
  let body = await res.json();
  assert.equal(res.status, 200);
  assert.equal(body.status, 'needs_user_data');
  assert.equal(body.ok, false);

  await writeFile(file, JSON.stringify({
    status: 'not_available', ok: false,
    fleet: { targetDevices: 20, discovered: 10, adbOnline: 10, simReady: 0 },
    capabilities: { ramExtensionPossible: false },
  }), 'utf8');
  res = await fetch(`${base}/api/rest/gsm/compute`);
  body = await res.json();
  assert.equal(body.status, 'not_available');
  assert.equal(body.fleet.adbOnline, 10);
  assert.equal(body.capabilities.ramExtensionPossible, false);
  assert.ok(body.requestId);
});
