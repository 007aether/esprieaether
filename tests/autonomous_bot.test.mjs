import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

import {
  classifySuite,
  freshEnough,
  hasSecret,
  buildReport,
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

test('J144: le rapport est vert sans aucun scan GSM', () => {
  const report = buildReport({
    runs: [
      { name: 'node', exit: 0, summary: 'tests=1091 pass=1091 fail=0' },
      { name: 'python', exit: 0, summary: 'tests=332 OK' },
      { name: 'atulya', exit: 0, summary: 'passed=582 skipped=3' },
      { name: 'manifest', exit: 0, summary: 'files=823 version=2.1.6' },
    ],
    now: NOW,
  });
  assert.equal(report.overall, 'live_verified');
  assert.deepEqual(report.missing, []);
  assert.equal(report.gsm.status, 'not_available');
  assert.equal(report.gsm.online, 0);
  assert.equal(report.modelTrial.status, 'not_available');
  assert.match(report.gsm.reason, /annulée par le propriétaire/i);
  assert.ok(!report.suites.some((suite) => suite.name.startsWith('gsm-')));
});

test('J144: une suite locale rouge reste implemented_unverified', () => {
  const report = buildReport({
    runs: [{ name: 'node', exit: 1, summary: 'tests=1 fail=1' }],
    now: NOW,
  });
  assert.equal(report.overall, 'implemented_unverified');
  assert.ok(report.missing.some((item) => item.name === 'node'));
  assert.ok(!report.missing.some((item) => item.name.startsWith('gsm-')));
});

test('J144: le bot ne lance plus ni scan ADB ni sonde de 20 endpoints', () => {
  const source = fs.readFileSync(new URL('../scripts/autonomous_checks.mjs', import.meta.url), 'utf8');
  assert.ok(!source.includes('gsm-scan'));
  assert.ok(!source.includes('gsm-probe'));
  assert.ok(!source.includes('src.gsm_bridge'));
  assert.match(source, /annulée par le propriétaire/);
});

test('J136: le scan de secrets ignore les littéraux de test', () => {
  const source = fs.readFileSync(new URL('../scripts/autonomous_checks.mjs', import.meta.url), 'utf8');
  assert.match(source, /safeFixture/);
  assert.match(source, /assertNotIn|assert\\\./);
});
