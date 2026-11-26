import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, writeFile, mkdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { buildCapabilities } from '../api/server.mjs';

async function fixture() {
  const dir = await mkdtemp(join(tmpdir(), 'sunnavok-gsm-'));
  const state = join(dir, 'state');
  await mkdir(state, { recursive: true });
  const paths = {
    brainMetricsPath: join(state, 'brain_metrics.json'),
    actionRequestsPath: join(state, 'action_requests.json'),
    actionAuditPath: join(state, 'action_audit.jsonl'),
    voiceInboxPath: join(state, 'voice_inbox.jsonl'),
    egressPath: join(state, 'egress_selfcheck.json'),
    bargeReviewPath: join(state, 'barge_in_review.json'),
    learningPath: join(state, 'learning_selfcheck.json'),
    chatAuthPath: join(state, 'chat_auth_selfcheck.json'),
    githubScoutPath: join(state, 'github_scout_report.json'),
    doctorPath: join(state, 'doctor_selfcheck.json'),
    reaPath: join(state, 'rea_selfcheck.json'),
    gsmPath: join(state, 'gsm_status.json'),
  };
  return { dir, paths };
}

function report(stamp) {
  return {
    ok: true,
    status: 'live_verified',
    readOnly: true,
    checkedAt: stamp,
    discovered: 20,
    online: 20,
    errors: [],
  };
}

function find(caps) {
  return caps.capabilities.find((row) => row.id === 'gsm-fleet');
}

test('J129: la flotte GSM locale publie une preuve datée et lecture seule', async () => {
  const fx = await fixture();
  try {
    await writeFile(fx.paths.gsmPath, JSON.stringify(report(new Date().toISOString())));
    const row = find(await buildCapabilities(fx.dir, fx.paths));
    assert.ok(row, 'capacité gsm-fleet absente');
    assert.equal(row.status, 'live_verified');
    assert.ok(row.evidence.some((item) => item.field === 'online' && item.value === 20));
    assert.ok(row.evidence.some((item) => item.field === 'readOnly' && item.value === true));
    assert.ok(row.verifiedAt && row.expiresAt);
    assert.match(row.next, /\S/);
  } finally {
    await rm(fx.dir, { recursive: true, force: true });
  }
});

test('J129: une preuve GSM périmée n’est plus live_verified', async () => {
  const fx = await fixture();
  try {
    const old = new Date(Date.now() - 8 * 24 * 60 * 60 * 1000).toISOString();
    await writeFile(fx.paths.gsmPath, JSON.stringify(report(old)));
    const row = find(await buildCapabilities(fx.dir, fx.paths));
    assert.equal(row.status, 'implemented_unverified');
  } finally {
    await rm(fx.dir, { recursive: true, force: true });
  }
});

test('J129: sans preuve GSM, aucune capacité n’est inventée', async () => {
  const fx = await fixture();
  try {
    const row = find(await buildCapabilities(fx.dir, fx.paths));
    assert.equal(row.status, 'not_available');
    assert.equal(row.evidence[0].value, 'no_data_source');
  } finally {
    await rm(fx.dir, { recursive: true, force: true });
  }
});
