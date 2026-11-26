import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const source = fs.readFileSync(new URL('../tests/jarvis_atulya.test.mjs', import.meta.url), 'utf8');

test('J133: le serveur de test libère les connexions keep-alive avant close', () => {
  assert.match(source, /closeAllConnections\?\.\(\)/);
  assert.match(source, /connection:\s*['"]close['"]/i);
});
