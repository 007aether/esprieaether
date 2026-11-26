import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

import {
  classifySuite,
  freshEnough,
  hasSecret,
  validateGsmEvidence,
  buildReport,
} from '../scripts/autonomous_checks.mjs';

const NOW = Date.parse('2026-11-26T09:00:00Z');

function evidenceFixture(overrides = {}) {
  const gsm = {
    status: 'live_verified',
    online: 20,
    errors: [],
    readOnly: true,
    worker: { mode: 'thin_endpoint', ready: 20 },
    checkedAt: '2026-11-26T08:50:00Z',
    ...(overrides.gsm || {}),
  };
  const workers = {
    status: 'live_verified',
    online: 20,
    succeeded: 60,
    errors: [],
    readOnly: true,
    checkedAt: '2026-11-26T08:51:00Z',
    ...(overrides.workers || {}),
  };
  const trial = {
    status: 'needs_user_data',
    ready: false,
    reason: 'fichiers locaux absents',
    checkedAt: '2026-11-26T08:49:00Z',
    ...(overrides.trial || {}),
  };
  return { gsm, workers, trial };
}

test('J131: le bot n’utilise que les statuts autorisés', () => {
  assert.equal(classifySuite(0), 'live_verified');
  assert.equal(classifySuite(1), 'implemented_unverified');
  assert.equal(freshEnough('2026-11-26T08:50:00Z', NOW), true);
  assert.equal(freshEnough('2026-11-19T08:50:00Z', NOW), false);
  assert.equal(hasSecret('api_key: abc123'), true);
  assert.equal(hasSecret('online: 20'), false);
});

test('J131: la preuve GSM valide 20 endpoints en lecture seule', () => {
  const result = validateGsmEvidence(evidenceFixture(), NOW);
  assert.equal(result.status, 'live_verified');
  assert.equal(result.online, 20);
  assert.equal(result.succeeded, 60);
  assert.ok(result.checks.every((check) => check.ok));
});

test('J131: une preuve périmée ou secrète n’est pas live_verified', () => {
  const stale = validateGsmEvidence(evidenceFixture({
    gsm: { checkedAt: '2026-11-19T08:50:00Z' },
  }), NOW);
  assert.equal(stale.status, 'implemented_unverified');
  assert.ok(stale.checks.some((check) => check.field === 'gsm.fresh' && !check.ok));

  const leaky = validateGsmEvidence(evidenceFixture({
    workers: { gateway: 'http://127.0.0.1:31416?token=abc' },
  }), NOW);
  assert.equal(leaky.status, 'implemented_unverified');
  assert.ok(leaky.checks.some((check) => check.field === 'evidence.noSecret' && !check.ok));
});

test('J136: le scan de secrets ignore les littéraux de test', () => {
  const source = fs.readFileSync(new URL('../scripts/autonomous_checks.mjs', import.meta.url), 'utf8');
  assert.match(source, /safeFixture/);
  assert.match(source, /assertNotIn\|assert\\\./);
});

test('J131: le trial on-device reste needs_user_data sans casser le rapport', () => {
  const evidence = validateGsmEvidence(evidenceFixture(), NOW);
  const report = buildReport({
    runs: [{ name: 'node', exit: 0 }, { name: 'python', exit: 0 }],
    evidence,
    trial: evidenceFixture().trial,
    now: NOW,
  });
  assert.equal(report.overall, 'live_verified');
  assert.equal(report.modelTrial.status, 'needs_user_data');
  assert.ok(report.missing.some((item) => item.name === 'gsm-model-trial'));

  const failed = buildReport({
    runs: [{ name: 'node', exit: 1 }],
    evidence,
    trial: evidenceFixture().trial,
    now: NOW,
  });
  assert.equal(failed.overall, 'implemented_unverified');
  assert.ok(failed.missing.some((item) => item.name === 'node'));
});
