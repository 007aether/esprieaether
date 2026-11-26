import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const files = {};
const SKIP_DIRS = new Set(['__pycache__', '.venv', '.tools', 'models', 'node_modules', 'state', '.git']);
const SKIP_FILE = /\.pyc$|\.log$|^\.env|\.(key|pem|pfx|p12)$/i;
function add(relative) {
  const absolute = path.join(root, relative);
  const stat = fs.lstatSync(absolute);
  if (stat.isSymbolicLink()) throw new Error(`Refusing symlink: ${relative}`);
  if (stat.isDirectory()) {
    for (const name of fs.readdirSync(absolute).sort()) {
      if (SKIP_DIRS.has(name) || SKIP_FILE.test(name)) continue;
      add(`${relative}/${name}`);
    }
  } else if (!SKIP_FILE.test(path.basename(relative))) {
    files[relative] = crypto.createHash('sha256').update(fs.readFileSync(absolute)).digest('hex');
  }
}
for (const relative of [
  'README.md', 'INSTALL.md', 'LICENSE', 'CONTRIBUTING.md', 'package.json',
  'install.mjs', '.gitignore', '.gitattributes',
  'skills', 'adapters', 'integration', 'scripts', 'tests', 'evals', '.github', 'assets', 'docs',
  // Coeur local vérifié : jamais state/, .venv/, .tools/, models/ ni secrets.
  'api', 'dashboard', 'shared',
  'esprieaether/G0DM0D3/out',
  'esprieaether/scripts/local_sentinel.py',
  'esprieaether/scripts/local_converter.py',
  'esprieaether/src/action_request.py',
  'esprieaether/src/voice_loop.py',
  'esprieaether/src/voice_status.py',
  'esprieaether/src/model_manager.py',
  'esprieaether/src/vault_memory.py',
  'esprieaether/src/egress_guard.py',
  'esprieaether/src/egress_selfcheck.py',
  'esprieaether/src/jarvis_bridge.py',
  'esprieaether/src/sources_intake.py',
  'esprieaether/src/learning_agent.py',
  'esprieaether/tests/test_action_request.py',
  'esprieaether/tests/test_live_status.py',
  'esprieaether/tests/test_local_sentinel.py',
  'esprieaether/tests/test_local_converter.py',
  'esprieaether/tests/test_model_manager.py',
  'esprieaether/tests/test_vault_memory.py',
  'esprieaether/tests/test_egress_guard.py',
  'esprieaether/tests/test_jarvis_bridge_local.py',
  'esprieaether/tests/test_sources_intake.py',
  'esprieaether/tests/test_learning_agent.py',
  'GITHUB_IMPORT/Atulya-Tantra/atulya',
  'GITHUB_IMPORT/Atulya-Tantra/tools',
  'GITHUB_IMPORT/Atulya-Tantra/tests/core',
  'GITHUB_IMPORT/Atulya-Tantra/tests/plugins',
  'GITHUB_IMPORT/Atulya-Tantra/docs/implementation-status.json',
  'GITHUB_IMPORT/Atulya-All-File-Converter/atulya_all_file_converter',
  'GITHUB_IMPORT/Atulya-All-File-Converter/tests',
  'GITHUB_IMPORT/Atulya-All-File-Converter/README.md',
  'GITHUB_IMPORT/Atulya-All-File-Converter/LICENSE',
  'GITHUB_IMPORT/Atulya-All-File-Converter/pyproject.toml',
  'GITHUB_IMPORT/Atulya-All-File-Converter/requirements.txt',
]) add(relative);
const { name, version } = JSON.parse(fs.readFileSync(path.join(root, 'package.json'), 'utf8'));
fs.writeFileSync(path.join(root, 'manifest.json'), JSON.stringify({ name, version, files }, null, 2) + '\n');
console.log(`Manifest: ${Object.keys(files).length} files, version ${version}`);
