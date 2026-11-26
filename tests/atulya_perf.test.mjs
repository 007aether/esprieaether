import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const atulya = new URL('../GITHUB_IMPORT/Atulya-Tantra/', import.meta.url);
const server = fs.readFileSync(new URL('atulya/server.py', atulya), 'utf8');
const assistant = fs.readFileSync(new URL('webui/assistant.js', atulya), 'utf8');
const controls = fs.readFileSync(new URL('webui/controls.js', atulya), 'utf8');
const tts = fs.readFileSync(new URL('tools/plugins/voice/tts.py', atulya), 'utf8');

test('J139: les empreintes des modèles vocaux ne sont calculées qu’une fois', () => {
  assert.match(tts, /from functools import lru_cache/);
  assert.match(tts, /@lru_cache\(maxsize=8\)\s*\ndef model_assets_ready\(models_dir: Path\) -> bool:/);
});

test('J137: les sondes publiques ne passent pas par la base SQLite d’authentification', () => {
  assert.match(server, /FAST_PUBLIC_PATHS\s*=\s*frozenset/);
  assert.match(server, /if path not in self\.FAST_PUBLIC_PATHS and path\.startswith\("\/api\/"\) and client_ip and await asyncio\.to_thread\(self\.auth_store\.ip_banned, client_ip\)/);
  assert.match(server, /"\/api\/health"/);
  assert.match(server, /"\/api\/auth\/status"/);
});

test('J138: les sondes de l’interface passent de 3 à 10 secondes', () => {
  assert.match(assistant, /setInterval\(checkPendingLogins, 10000\)/);
  assert.match(assistant, /}, 10000\); \/\/ live CPU\/RAM\/network meters/);
  assert.match(controls, /setInterval\(pollReminders, 10000\)/);
});
