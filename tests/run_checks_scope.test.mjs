import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const source = fs.readFileSync(new URL('../scripts/run-checks.mjs', import.meta.url), 'utf8');

test('J132: le wrapper npm test ne balaie pas les sauvegardes BACKUP_*', () => {
  assert.match(source, /args:\s*\['--test',\s*'--test-reporter=tap',\s*'tests'\]/);
  assert.match(source, /runTests\(probe,\s*\{[^}]*cwd/);
});
