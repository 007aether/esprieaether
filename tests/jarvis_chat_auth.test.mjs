import test, { before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, rm, writeFile, mkdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { buildCapabilities, createDashboardServer } from '../api/server.mjs';

let dir;
let reportsDir;
let proofPath;
let server;
let base;
const now = new Date().toISOString();

before(async () => {
  dir = await mkdtemp(join(tmpdir(), 'sunnavok-chat-auth-'));
  reportsDir = join(dir, 'reports');
  await mkdir(reportsDir, { recursive: true });
  await mkdir(join(dir, 'state'), { recursive: true });
  proofPath = join(dir, 'state', 'chat_auth_selfcheck.json');
  await writeFile(proofPath, JSON.stringify({
    ok: true,
    checkedAt: now,
    status: 'live_verified',
    method: 'passkey',
    authenticated: true,
    turns: 2,
    cookie: 'atulya_session=REDACTEDSESSION',
    requestId: 'chat-1',
  }), 'utf8');
  server = createDashboardServer({ reportsDir, chatAuthPath: proofPath, log: () => {} });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  base = `http://127.0.0.1:${server.address().port}`;
});

after(async () => {
  if (server) await new Promise((resolve) => server.close(resolve));
  if (dir) await rm(dir, { recursive: true, force: true });
});

test('J115: la capacité chat-auth n’est prouvée que par une session passkey réelle', async () => {
  const fresh = await buildCapabilities(reportsDir, { chatAuthPath: proofPath });
  const item = fresh.capabilities.find((entry) => entry.id === 'chat-auth');
  assert.ok(item, 'chat-auth doit exister');
  assert.equal(item.status, 'live_verified');
  assert.ok(item.evidence.some((row) => row.field === 'method' && row.value === 'passkey'));
  assert.ok(item.next.includes('passkey'));

  const absent = await buildCapabilities(reportsDir, {
    chatAuthPath: join(dir, 'state', 'absent.json'),
  });
  assert.equal(absent.capabilities.find((entry) => entry.id === 'chat-auth').status, 'not_available');
});

test('J115: /api/jarvis/chat-auth ne publie ni cookie ni jeton', async () => {
  const res = await fetch(`${base}/api/jarvis/chat-auth`);
  assert.equal(res.status, 200);
  const body = await res.json();
  assert.equal(body.available, true);
  assert.equal(body.method, 'passkey');
  assert.equal(body.turns, 2);
  assert.equal(typeof body.requestId, 'string');
  const text = JSON.stringify(body);
  assert.ok(!text.includes('REDACTEDSESSION'));
  assert.ok(!text.includes('atulya_session'));
});

test('J115: sans preuve, le routeur reste no_data_source', async () => {
  const empty = createDashboardServer({
    reportsDir,
    chatAuthPath: join(dir, 'state', 'missing.json'),
    log: () => {},
  });
  await new Promise((resolve) => empty.listen(0, '127.0.0.1', resolve));
  try {
    const res = await fetch(`http://127.0.0.1:${empty.address().port}/api/jarvis/chat-auth`);
    assert.equal(res.status, 200);
    const body = await res.json();
    assert.equal(body.available, false);
    assert.equal(body.reason, 'no_data_source');
  } finally {
    await new Promise((resolve) => empty.close(resolve));
  }
});
