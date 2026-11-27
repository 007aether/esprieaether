import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

import {
  classifySuite,
  freshEnough,
  hasSecret,
  buildReport,
  readGsmEvidence,
  GSM_ENABLED_REASON,
} from '../scripts/autonomous_checks.mjs';

const NOW = Date.parse('2026-11-26T09:00:00Z');

test('J131: le bot n’utilise que les statuts autorisés', () => {
  assert.equal(classifySuite(0), 'live_verified');
  assert.equal(classifySuite(1), 'implemented_unverified');
  assert.equal(freshEnough('2026-11-26T08:50:00Z', NOW), true);
  assert.equal(freshEnough('2026-11-19T08:50:00Z', NOW), false);
  assert.equal(hasSecret('api_key: abc123'), true);
  assert.equal(hasSecret('online: 20'), false);
});

const GREEN_RUNS = [
  { name: 'node', exit: 0, summary: 'tests=1091 pass=1091 fail=0' },
  { name: 'python', exit: 0, summary: 'tests=332 OK' },
  { name: 'atulya', exit: 0, summary: 'passed=582 skipped=3' },
  { name: 'manifest', exit: 0, summary: 'files=823 version=2.1.6' },
];

test('J152: GSM réactivé reste needs_user_data sans preuve fraîche, jamais vert', () => {
  const report = buildReport({
    runs: GREEN_RUNS,
    now: NOW,
    gsmEvidence: { status: 'needs_user_data', enabled: true, online: 0, readOnly: false, reason: GSM_ENABLED_REASON },
  });
  assert.equal(report.overall, 'live_verified');
  assert.deepEqual(report.missing, []);
  assert.equal(report.gsm.status, 'needs_user_data');
  assert.equal(report.gsm.enabled, true);
  assert.equal(report.gsm.readOnly, false);
  assert.equal(report.gsm.online, 0);
  assert.equal(report.modelTrial.status, 'needs_user_data');
  assert.match(report.gsm.reason, /réactivée par le propriétaire/i);
  assert.ok(!report.suites.some((suite) => suite.name.startsWith('gsm-')));
});

test('J153: une preuve ADB fraîche et vérifiée monte gsm-fleet en live_verified', () => {
  const report = buildReport({
    runs: GREEN_RUNS,
    now: NOW,
    gsmEvidence: {
      ok: true, status: 'live_verified', online: 10, discovered: 10,
      errors: [], readOnly: true, checkedAt: '2026-11-26T08:50:00Z',
      reason: 'scan ADB local en lecture seule',
    },
    modelTrialEvidence: { status: 'needs_user_data', ready: false, checkedAt: '2026-11-26T08:50:00Z' },
  });
  assert.equal(report.gsm.status, 'live_verified');
  assert.equal(report.gsm.online, 10);
  assert.equal(report.gsm.succeeded, 10);
  assert.equal(report.gsm.readOnly, true);
  assert.equal(report.gsm.checkedAt, '2026-11-26T08:50:00Z');
  assert.equal(report.modelTrial.status, 'needs_user_data');
  assert.ok(freshEnough(report.gsm.checkedAt, NOW));
  assert.ok(['live_verified', 'implemented_unverified', 'not_available', 'needs_user_data'].includes(report.gsm.status));
});

test('J153: une preuve GSM périmée ne devient jamais verte', () => {
  const report = buildReport({
    runs: GREEN_RUNS,
    now: NOW,
    gsmEvidence: {
      ok: true, status: 'live_verified', online: 20, readOnly: true,
      checkedAt: '2026-11-01T00:00:00Z', reason: 'ancien scan',
    },
  });
  assert.equal(report.gsm.status, 'needs_user_data');
  assert.equal(report.gsm.online, 0);
  assert.match(report.gsm.reason, /périmée/i);
});

test('J153: readGsmEvidence lit le state local sans lancer de scan', async () => {
  const { mkdtemp, writeFile, rm } = await import('node:fs/promises');
  const { tmpdir } = await import('node:os');
  const { join } = await import('node:path');
  const dir = await mkdtemp(join(tmpdir(), 'sunnavok-gsm-evidence-'));
  try {
    await writeFile(join(dir, 'gsm_status.json'), JSON.stringify({
      ok: true, status: 'live_verified', online: 10, readOnly: true,
      checkedAt: '2026-11-26T08:50:00Z',
    }));
    const evidence = readGsmEvidence(dir, NOW);
    assert.equal(evidence.gsmEvidence.online, 10);
    assert.equal(evidence.gsmEvidence.fresh, true);
    assert.equal(evidence.modelTrialEvidence, null);
  } finally {
    await rm(dir, { recursive: true, force: true });
  }
});

test('J144: une suite locale rouge reste implemented_unverified', () => {
  const report = buildReport({
    runs: [{ name: 'node', exit: 1, summary: 'tests=1 fail=1' }],
    now: NOW,
  });
  assert.equal(report.overall, 'implemented_unverified');
  assert.ok(report.missing.some((item) => item.name === 'node'));
  assert.ok(!report.missing.some((item) => item.name.startsWith('gsm-')));
  assert.equal(report.gsm.status, 'needs_user_data');
});

test('J144: le bot ne lance plus ni scan ADB ni sonde de 20 endpoints', () => {
  const source = fs.readFileSync(new URL('../scripts/autonomous_checks.mjs', import.meta.url), 'utf8');
  assert.ok(!source.includes('gsm-scan'));
  assert.ok(!source.includes('gsm-probe'));
  assert.ok(!source.includes('src.gsm_bridge'));
  assert.match(source, /réactivée par le propriétaire/);
});

test('J136: le scan de secrets ignore les littéraux de test', () => {
  const source = fs.readFileSync(new URL('../scripts/autonomous_checks.mjs', import.meta.url), 'utf8');
  assert.match(source, /safeFixture/);
  assert.match(source, /assertNotIn|assert\\\./);
});
