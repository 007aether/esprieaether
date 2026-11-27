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
    workerProbePath: join(state, 'gsm_workers.json'),
    modelTrialPath: join(state, 'gsm_model_trial.json'),
  };
  return { dir, paths };
}

function find(caps) {
  return caps.capabilities.find((row) => row.id === 'gsm-fleet');
}

function findModel(caps) {
  return caps.capabilities.find((row) => row.id === 'gsm-model-trial');
}

test('J144: une capacité GSM annulée est not_available, jamais verte', async () => {
  const fx = await fixture();
  try {
    const stamp = new Date().toISOString();
    await writeFile(fx.paths.gsmPath, JSON.stringify({
      ok: true, status: 'not_available', cancelled: true,
      reason: 'capacité GSM annulée par le propriétaire — aucun appareil requis',
      online: 0, errors: [], readOnly: true, checkedAt: stamp,
    }));
    await writeFile(fx.paths.workerProbePath, JSON.stringify({
      status: 'not_available', cancelled: true, online: 0, checkedAt: stamp,
    }));
    await writeFile(fx.paths.modelTrialPath, JSON.stringify({
      status: 'not_available', cancelled: true, ready: false,
      reason: 'capacité GSM annulée par le propriétaire — aucun appareil requis',
      checkedAt: stamp,
    }));
    const caps = await buildCapabilities(fx.dir, fx.paths);
    assert.equal(caps.capabilities.length, 15);
    const row = find(caps);
    const model = findModel(caps);
    assert.ok(row, 'capacité gsm-fleet absente');
    assert.equal(row.status, 'not_available');
    assert.ok(row.evidence.some((item) => item.field === 'status' && item.value === 'not_available'));
    assert.match(row.next, /annulée par le propriétaire/);
    assert.ok(model, 'capacité gsm-model-trial absente');
    assert.equal(model.status, 'not_available');
    assert.match(model.next, /annulée par le propriétaire/);
  } finally {
    await rm(fx.dir, { recursive: true, force: true });
  }
});

test('J152: GSM réactivé sans appareil est needs_user_data, jamais vert', async () => {
  const fx = await fixture();
  try {
    const stamp = new Date().toISOString();
    await writeFile(fx.paths.gsmPath, JSON.stringify({
      ok: true, status: 'needs_user_data', cancelled: false,
      reason: 'capacité GSM réactivée par le propriétaire — aucun appareil détecté',
      online: 0, discovered: 0, errors: [], readOnly: false, checkedAt: stamp,
    }));
    await writeFile(fx.paths.modelTrialPath, JSON.stringify({
      status: 'needs_user_data', cancelled: false, ready: false,
      reason: 'capacité GSM réactivée par le propriétaire — aucun appareil détecté',
      checkedAt: stamp,
    }));
    const caps = await buildCapabilities(fx.dir, fx.paths);
    const row = find(caps);
    const model = findModel(caps);
    assert.equal(row.status, 'needs_user_data');
    assert.equal(model.status, 'needs_user_data');
    assert.doesNotMatch(row.next, /annulée par le propriétaire/);
  } finally {
    await rm(fx.dir, { recursive: true, force: true });
  }
});

test('J144: aucune preuve annulée ne fait monter une capacité inventée', async () => {
  const fx = await fixture();
  try {
    const caps = await buildCapabilities(fx.dir, fx.paths);
    assert.equal(caps.capabilities.length, 15);
    assert.equal(find(caps).status, 'not_available');
    assert.equal(findModel(caps).status, 'not_available');
  } finally {
    await rm(fx.dir, { recursive: true, force: true });
  }
});
