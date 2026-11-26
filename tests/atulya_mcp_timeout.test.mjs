import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const source = fs.readFileSync(
  new URL('../GITHUB_IMPORT/Atulya-Tantra/tests/mcp/test_server.py', import.meta.url),
  'utf8',
);

test('J134: le client MCP stdio tolère une machine locale chargée', () => {
  assert.match(source, /read_timeout_seconds=30/);
  assert.doesNotMatch(source, /read_timeout_seconds=5\)/);
});

const cliSource = fs.readFileSync(new URL('../tests/reference.test.mjs', import.meta.url), 'utf8');

test('J135: le CLI de référence tolère une machine locale chargée', () => {
  assert.match(cliSource, /timeout: 120000/);
  assert.doesNotMatch(cliSource, /timeout: 15000/);
});
