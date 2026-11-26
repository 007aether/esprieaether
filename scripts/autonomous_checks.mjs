import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const espria = path.join(root, 'esprieaether');
const atulya = path.join(root, 'GITHUB_IMPORT', 'Atulya-Tantra');
const state = path.join(espria, 'state');
const pythonEspria = path.join(espria, '.venv', 'Scripts', 'python.exe');
const pythonAtulya = path.join(atulya, '.venv', 'Scripts', 'python.exe');
const nodeDir = path.dirname(process.execPath);
const TTL_DAYS = 7;
const SECRET = /(\b(?:api[_-]?key|password|secret|token)\b)\s*[:=]\s*\S+/i;

export const STATUSES = new Set([
  'live_verified',
  'implemented_unverified',
  'not_available',
  'needs_user_data',
]);

export function classifySuite(exitCode) {
  return exitCode === 0 ? 'live_verified' : 'implemented_unverified';
}

export function freshEnough(checkedAt, now = Date.now(), days = TTL_DAYS) {
  const stamp = Date.parse(String(checkedAt || ''));
  if (!Number.isFinite(stamp)) return false;
  const age = now - stamp;
  return age >= -60_000 && age <= days * 24 * 60 * 60 * 1000;
}

export function hasSecret(value) {
  return SECRET.test(String(value ?? ''));
}

function sanitize(text) {
  return String(text ?? '').replace(SECRET, '$1=***').replace(/\s+/g, ' ').trim();
}

function check(list, field, ok, value) {
  list.push({ field, ok: Boolean(ok), value: sanitize(value) });
}

export function validateGsmEvidence({ gsm, workers, trial }, now = Date.now()) {
  const checks = [];
  const gsmReport = gsm || {};
  const workerReport = workers || {};
  const trialReport = trial || {};

  check(checks, 'gsm.status', gsmReport.status === 'live_verified', gsmReport.status);
  check(checks, 'gsm.online', gsmReport.online === 20, gsmReport.online);
  check(checks, 'gsm.errors', Array.isArray(gsmReport.errors) && gsmReport.errors.length === 0, gsmReport.errors?.length);
  check(checks, 'gsm.readOnly', gsmReport.readOnly === true, gsmReport.readOnly);
  check(checks, 'gsm.workerMode', gsmReport.worker?.mode === 'thin_endpoint', gsmReport.worker?.mode);
  check(checks, 'gsm.workersReady', gsmReport.worker?.ready === 20, gsmReport.worker?.ready);
  check(checks, 'gsm.fresh', freshEnough(gsmReport.checkedAt, now), gsmReport.checkedAt);

  check(checks, 'workers.status', workerReport.status === 'live_verified', workerReport.status);
  check(checks, 'workers.online', workerReport.online === 20, workerReport.online);
  check(checks, 'workers.succeeded', Number(workerReport.succeeded) >= 20, workerReport.succeeded);
  check(checks, 'workers.errors', Array.isArray(workerReport.errors) && workerReport.errors.length === 0, workerReport.errors?.length);
  check(checks, 'workers.readOnly', workerReport.readOnly === true, workerReport.readOnly);
  check(checks, 'workers.fresh', freshEnough(workerReport.checkedAt, now), workerReport.checkedAt);

  check(checks, 'trial.status', STATUSES.has(trialReport.status), trialReport.status);
  check(checks, 'evidence.noSecret', !hasSecret(JSON.stringify({ gsmReport, workerReport, trialReport })), 'false');

  const ok = checks.every((item) => item.ok);
  return {
    status: ok ? 'live_verified' : 'implemented_unverified',
    checks,
    online: Number(gsmReport.online) || 0,
    succeeded: Number(workerReport.succeeded) || 0,
    readOnly: gsmReport.readOnly === true && workerReport.readOnly === true,
    gsmCheckedAt: gsmReport.checkedAt || null,
    workersCheckedAt: workerReport.checkedAt || null,
  };
}

export function buildReport({ runs = [], evidence, trial = {}, now = Date.now() }) {
  const suites = runs.map((run) => ({
    name: run.name,
    label: run.label || run.name,
    status: classifySuite(run.exit),
    exit: run.exit,
    summary: sanitize(run.summary),
    durationMs: run.durationMs || 0,
  }));
  const missing = suites
    .filter((suite) => suite.status !== 'live_verified')
    .map((suite) => ({ name: suite.name, status: suite.status, reason: suite.summary }));

  if (evidence?.status !== 'live_verified') {
    missing.push({ name: 'gsm-evidence', status: evidence?.status || 'not_available', reason: 'preuve datée ou lecture seule invalide' });
  }
  if (STATUSES.has(trial.status) && trial.status !== 'live_verified') {
    missing.push({ name: 'gsm-model-trial', status: trial.status, reason: sanitize(trial.reason) });
  }

  const overall = suites.length > 0
    && suites.every((suite) => suite.status === 'live_verified')
    && evidence?.status === 'live_verified'
    ? 'live_verified'
    : 'implemented_unverified';

  return {
    generatedAt: new Date(now).toISOString(),
    bot: 'SUNNAVOK — vérification locale autonome',
    scope: 'local_only_read_only',
    overall,
    suites,
    gsm: {
      status: evidence?.status || 'not_available',
      online: evidence?.online || 0,
      succeeded: evidence?.succeeded || 0,
      readOnly: Boolean(evidence?.readOnly),
      checkedAt: evidence?.gsmCheckedAt || null,
      probeCheckedAt: evidence?.workersCheckedAt || null,
    },
    modelTrial: {
      status: STATUSES.has(trial.status) ? trial.status : 'not_available',
      ready: trial.ready === true,
      reason: sanitize(trial.reason),
    },
    missing,
  };
}

function readJson(file) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch {
    return null;
  }
}

function summarize(name, result) {
  const output = `${result.stdout || ''}\n${result.stderr || ''}`;
  if (name === 'node') {
    const match = output.match(/# tests (\d+)[\s\S]*?# pass (\d+)[\s\S]*?# fail (\d+)/);
    if (match) return `tests=${match[1]} pass=${match[2]} fail=${match[3]}`;
  }
  if (name === 'python') {
    const match = output.match(/Ran (\d+) tests? in [\d.]+s/);
    if (match) return `tests=${match[1]} ${/^OK$/m.test(output.trim()) ? 'OK' : 'FAILED'}`;
  }
  if (name === 'atulya') {
    const match = output.match(/(\d+) passed, (\d+) skipped/);
    if (match) return `passed=${match[1]} skipped=${match[2]}`;
  }
  if (name === 'gsm-scan' || name === 'gsm-probe') {
    const firstLine = String(result.stdout || '').trim().split(/\r?\n/)[0] || '';
    try {
      const row = JSON.parse(firstLine);
      return `status=${row.status} online=${row.online ?? '-'} succeeded=${row.succeeded ?? '-'} errors=${row.errors?.length ?? '-'}`;
    } catch {
      // fall through to the raw line
    }
  }
  if (name === 'manifest') {
    const match = output.match(/Manifest: (\d+) files, version ([\d.]+)/);
    if (match) return `files=${match[1]} version=${match[2]}`;
  }
  const lines = output.split(/\r?\n/).map(sanitize).filter(Boolean);
  return lines.at(-1)?.slice(0, 200) || 'sans sortie';
}

const pyEnv = {
  ...process.env,
  PYTHONIOENCODING: 'utf-8',
  PYTHONPATH: path.join(espria, 'src'),
};
const atulyaEnv = {
  ...process.env,
  PYTHONIOENCODING: 'utf-8',
  PATH: `${nodeDir}${path.delimiter}${process.env.PATH || ''}`,
};

const COMMANDS = [
  { name: 'node', label: 'Node — suite locale', command: process.execPath, args: ['--test', '--test-reporter=tap', 'tests'], cwd: root, env: process.env, timeout: 1_800_000 },
  { name: 'python', label: 'Python — unittest esprieaether', command: pythonEspria, args: ['-m', 'unittest', 'discover', '-s', 'tests', '-q'], cwd: espria, env: pyEnv, timeout: 300_000 },
  { name: 'atulya', label: 'Atulya — pytest local', command: pythonAtulya, args: ['-m', 'pytest', '-q', 'tests'], cwd: atulya, env: atulyaEnv, timeout: 600_000 },
  { name: 'gsm-scan', label: 'GSM — scan ADB lecture seule', command: pythonEspria, args: ['-m', 'src.gsm_bridge'], cwd: espria, env: pyEnv, timeout: 600_000 },
  { name: 'gsm-probe', label: 'GSM — sonde 20 endpoints', command: pythonEspria, args: ['-m', 'src.gsm_bridge', '--probe'], cwd: espria, env: pyEnv, timeout: 600_000 },
  { name: 'manifest', label: 'Manifeste local', command: process.execPath, args: ['scripts/manifest.mjs'], cwd: root, env: process.env, timeout: 120_000 },
];

function runAll() {
  const runs = [];
  for (const spec of COMMANDS) {
    const started = Date.now();
    const result = spawnSync(spec.command, spec.args, {
      cwd: spec.cwd,
      env: spec.env,
      encoding: 'utf8',
      timeout: spec.timeout,
      windowsHide: true,
      maxBuffer: 16 * 1024 * 1024,
    });
    const exit = result.error ? 1 : (result.status ?? 1);
    const run = {
      name: spec.name,
      label: spec.label,
      exit,
      durationMs: Date.now() - started,
      summary: summarize(spec.name, result),
    };
    runs.push(run);
    console.log(`${run.label}: ${classifySuite(exit)} — ${sanitize(run.summary)}`);
  }
  return runs;
}

function runTool(command, args, cwd = root, timeout = 120_000) {
  const result = spawnSync(command, args, {
    cwd,
    encoding: 'utf8',
    timeout,
    windowsHide: true,
    maxBuffer: 16 * 1024 * 1024,
  });
  return {
    exit: result.error ? 1 : (result.status ?? 1),
    stdout: result.stdout || '',
    stderr: result.stderr || '',
  };
}

async function probe(url) {
  try {
    const response = await fetch(url, { signal: AbortSignal.timeout(8000) });
    return { ok: response.ok, body: await response.text() };
  } catch {
    return { ok: false, body: '' };
  }
}

async function servicesHealthy() {
  const capabilities = await probe('http://127.0.0.1:5100/api/jarvis/capabilities');
  const health = await probe('http://127.0.0.1:5000/health');
  let count = 0;
  try {
    count = JSON.parse(capabilities.body).capabilities?.length || 0;
  } catch {
    // reported below as unhealthy
  }
  return capabilities.ok && count === 15 && health.ok && health.body.includes('services-total');
}

async function reloadServices() {
  const listeners = runTool('powershell.exe', [
    '-NoProfile', '-Command',
    'Get-NetTCPConnection -LocalPort 5100,5000 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique',
  ]);
  const pids = listeners.stdout.split(/\r?\n/).map((line) => line.trim()).filter(/^\d+$/);
  for (const pid of pids) runTool('taskkill', ['/PID', pid, '/F', '/T']);
  runTool('powershell.exe', ['-NoProfile', '-Command', 'Start-Sleep -Seconds 75'], root, 120_000);
  return servicesHealthy();
}

async function maintain(report) {
  const actions = { git: 'not_available', reload: 'not_available' };
  if (report.overall !== 'live_verified') {
    actions.git = 'implemented_unverified';
    actions.reload = 'implemented_unverified';
    report.maintenance = actions;
    console.log('الصيانة متوقفة: الجولة غير خضراء');
    return;
  }

  const git = path.join(root, '.tools', 'git', 'cmd', 'git.exe');
  if (fs.existsSync(git)) {
    const base = ['-c', 'safe.directory=*'];
    const status = runTool(git, [...base, 'status', '--porcelain']);
    const changes = status.stdout.split(/\r?\n/).map((line) => line.trim()).filter(Boolean);
    if (status.exit !== 0) {
      actions.git = 'not_available';
    } else if (changes.length === 0) {
      actions.git = 'live_verified';
    } else {
      runTool(git, [...base, 'add', '-A']);
      const diffCheck = runTool(git, [...base, 'diff', '--cached', '--check']);
      const diff = runTool(git, [...base, 'diff', '--cached']);
      const safeFixture = /assertNotIn|assert\.|const SECRET|hasSecret\(|api_key: abc123|token=abc|test-secret|placeholder/i;
      const leaks = diff.stdout.split(/\r?\n/).filter((line) => SECRET.test(line) && !safeFixture.test(line));
      if (diffCheck.exit !== 0 || leaks.length > 0) {
        actions.git = 'implemented_unverified';
        console.log(`commit ممنوع: diff_check=${diffCheck.exit} secret_lines=${leaks.length}`);
      } else {
        const message = `chore: autonomous checks ${report.generatedAt}`;
        const commit = runTool(git, [...base, 'commit', '-m', message]);
        const push = commit.exit === 0 ? runTool(git, [...base, 'push', 'origin', 'main'], root, 180_000) : commit;
        actions.git = push.exit === 0 ? 'live_verified' : 'implemented_unverified';
        console.log(`git: ${actions.git} changed=${changes.length}`);
      }
    }
  }

  if (await servicesHealthy()) {
    actions.reload = 'live_verified';
  } else {
    actions.reload = await reloadServices() ? 'live_verified' : 'implemented_unverified';
    console.log(`إعادة التحميل: ${actions.reload}`);
  }
  report.maintenance = actions;
}

async function main() {
  if (process.argv.includes('--help')) {
    console.log('SUNNAVOK autonomous checks: Node + Python + Atulya + 20 GSM en lecture seule + manifeste. --autonomous ajoute commit/push et rechargement uniquement si tout est vert. Jamais SMS, appel ni écriture appareil.');
    return;
  }

  const runs = runAll();
  const gsm = readJson(path.join(state, 'gsm_status.json'));
  const workers = readJson(path.join(state, 'gsm_workers.json'));
  const trial = readJson(path.join(state, 'gsm_model_trial.json')) || {};
  const evidence = validateGsmEvidence({ gsm, workers, trial });
  const report = buildReport({ runs, evidence, trial, now: Date.now() });
  if (process.argv.includes('--autonomous')) await maintain(report);
  const reportPath = path.join(state, 'autonomous_report.json');
  fs.mkdirSync(state, { recursive: true });
  fs.writeFileSync(reportPath, `${JSON.stringify(report, null, 2)}\n`, 'utf8');

  console.log(`التقرير: ${reportPath}`);
  console.log(`الحالة العامة: ${report.overall}`);
  console.log(`GSM: ${report.gsm.status} online=${report.gsm.online} succeeded=${report.gsm.succeeded} readOnly=${report.gsm.readOnly}`);
  console.log(`الموديل الصغير: ${report.modelTrial.status} — ${report.modelTrial.reason || 'بدون سبب'}`);
  if (report.missing.length > 0) {
    console.log(`ناقص: ${report.missing.map((item) => `${item.name}(${item.status})`).join(', ')}`);
  }
  process.exitCode = report.overall === 'live_verified' ? 0 : 1;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch((error) => {
    console.error(`فشل البوت: ${sanitize(error?.stack || error)}`);
    process.exitCode = 1;
  });
}
