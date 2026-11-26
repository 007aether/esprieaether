import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, writeFile, mkdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { buildCapabilities } from '../api/server.mjs';

async function fixture() {
  const dir = await mkdtemp(join(tmpdir(), 'sunnavok-new-agents-'));
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
  };
  return { dir, state, paths };
}

async function caps(fx) {
  return buildCapabilities(fx.dir, fx.paths);
}

test('J120: les trois nouveaux agents publient une preuve datée', async () => {
  const fx = await fixture();
  try {
    const now = new Date().toISOString();
    await writeFile(fx.paths.githubScoutPath, JSON.stringify({
      ok: true, status: 'live_verified', checked_at: now, scanned: 1000,
    }));
    await writeFile(fx.paths.doctorPath, JSON.stringify({
      ok: true, status: 'live_verified', checked_at: now, detected: 3, fixed: 2,
    }));
    await writeFile(fx.paths.reaPath, JSON.stringify({
      ok: true, status: 'live_verified', checked_at: now, files: 412,
    }));
    const result = await caps(fx);
    const ids = result.capabilities.map((row) => row.id);
    for (const id of ['github-scout', 'doctor', 'rea']) {
      assert.ok(ids.includes(id), `capacité absente: ${id}`);
      const row = result.capabilities.find((item) => item.id === id);
      assert.equal(row.status, 'live_verified');
      assert.ok(row.evidence.length > 0);
      assert.ok(row.verifiedAt && row.expiresAt);
      assert.match(row.next, /\S/);
    }
    const scout = result.capabilities.find((item) => item.id === 'github-scout');
    assert.ok(scout.evidence.some((row) => row.field === 'scanned' && row.value === 1000));
  } finally {
    await rm(fx.dir, { recursive: true, force: true });
  }
});

test('J120: sans preuve, aucune capacité n’est inventée', async () => {
  const fx = await fixture();
  try {
    const result = await caps(fx);
    for (const id of ['github-scout', 'doctor', 'rea']) {
      const row = result.capabilities.find((item) => item.id === id);
      assert.ok(row, `capacité absente: ${id}`);
      assert.equal(row.status, 'not_available');
      assert.ok(row.evidence[0].value === 'no_data_source');
    }
  } finally {
    await rm(fx.dir, { recursive: true, force: true });
  }
});

test('J120: une preuve périmée est dégradée, pas affirmée', async () => {
  const fx = await fixture();
  try {
    const old = new Date(Date.now() - 8 * 24 * 60 * 60 * 1000).toISOString();
    await writeFile(fx.paths.doctorPath, JSON.stringify({
      ok: true, status: 'live_verified', checked_at: old, detected: 1, fixed: 1,
    }));
    const result = await caps(fx);
    const row = result.capabilities.find((item) => item.id === 'doctor');
    assert.equal(row.status, 'implemented_unverified');
    assert.ok(row.expiresAt);
  } finally {
    await rm(fx.dir, { recursive: true, force: true });
  }
});
