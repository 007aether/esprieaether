import { createServer } from 'node:http';
import { appendFile, readFile, readdir, stat, mkdir, writeFile, rename } from 'node:fs/promises';
import { statSync } from 'node:fs';
import { dirname, extname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomUUID } from 'node:crypto';
import { CONDITIONS, OWNERS, errorEnvelope, normalizeState, validateState } from '../shared/contract.mjs';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const DEFAULT_DASHBOARD_DIR = join(ROOT, 'dashboard');
const DEFAULT_STATE_PATH = join(ROOT, 'state', 'dashboard.json');
const DEFAULT_REPORTS_DIR = join(ROOT, 'esprieaether', 'state');
const DEFAULT_LEDGER_PATH = join(ROOT, 'esprieaether', 'state', 'run_ledger.json');
const DEFAULT_INTERNET_PATH = join(ROOT, 'esprieaether', 'state', 'internet_status.json');
const DEFAULT_VOICE_INBOX = join(ROOT, 'esprieaether', 'state', 'voice_inbox.jsonl');
const DEFAULT_VOICE_LOCK = join(ROOT, 'esprieaether', 'state', 'voice_daemon.lock');
const DEFAULT_VOICE_STATUS = join(ROOT, 'esprieaether', 'state', 'voice_status.json');
const DEFAULT_BRAIN_METRICS = join(ROOT, 'esprieaether', 'state', 'brain_metrics.json');
const DEFAULT_ACTION_REQUESTS = join(ROOT, 'esprieaether', 'state', 'action_requests.json');
const DEFAULT_ACTION_AUDIT = join(ROOT, 'esprieaether', 'state', 'action_audit.jsonl');
const DEFAULT_ATULYA_DIR = join(ROOT, 'GITHUB_IMPORT', 'Atulya-Tantra');
const DEFAULT_VISION_EVIDENCE = join(ROOT, 'esprieaether', 'state', 'vision_selfcheck.json');
const DEFAULT_MCP_EVIDENCE = join(ROOT, 'esprieaether', 'state', 'mcp_selfcheck.json');
const DEFAULT_VAULT_EVIDENCE = join(ROOT, 'esprieaether', 'state', 'vault_memory_selfcheck.json');
const DEFAULT_EGRESS_EVIDENCE = join(ROOT, 'esprieaether', 'state', 'egress_selfcheck.json');
const DEFAULT_BARGE_REVIEW = join(ROOT, 'esprieaether', 'state', 'barge_in_review.json');
const DEFAULT_WAKE_EVIDENCE = join(ROOT, 'esprieaether', 'state', 'wake_selfcheck.json');
const VOICE_STAGES = new Set(['idle', 'listening', 'thinking', 'speaking']);
const REPORT_FILES = {
  quality: 'quality_guard_report.json',
  vault: 'vault_guard_report.json',
  backlog: 'backlog_scout_report.json',
  brains: 'local_brain_verification.json',
};
const AGENT_AUDIT_FILE = 'agent_audit_report.json';
const LOCAL_ORIGINS = new Set([
  'http://127.0.0.1:5000', 'http://localhost:5000',
  'http://127.0.0.1:5100', 'http://localhost:5100',
  // Le HUD statique est servi par le relais loopback :3860 (J84).
  'http://127.0.0.1:3860', 'http://localhost:3860',
]);
// Une preuve n'est live_verified que pendant 7 jours ; au-delà, on dégrade.
const VERIFY_TTL_MS = 7 * 24 * 60 * 60 * 1000;
function verifiedStamp(status, verifiedAt) {
  const parsed = typeof verifiedAt === 'string' ? Date.parse(verifiedAt) : NaN;
  const now = Date.now();
  const fresh = Number.isFinite(parsed) && parsed <= now + 5 * 60 * 1000 && now - parsed <= VERIFY_TTL_MS;
  return {
    status: status === 'live_verified' && !fresh ? 'implemented_unverified' : status,
    verifiedAt: Number.isFinite(parsed) ? new Date(parsed).toISOString() : null,
    expiresAt: Number.isFinite(parsed) ? new Date(parsed + VERIFY_TTL_MS).toISOString() : null,
  };
}
function stampOf(obj, filePath) {
  for (const key of ['checked_at', 'checkedAt', 'verifiedAt', 'updatedAt', 'updated']) {
    const value = obj && obj[key];
    if (typeof value === 'string' && Number.isFinite(Date.parse(value))) return value;
  }
  try { return statSync(filePath).mtime.toISOString(); } catch { return null; }
}
const PLACEHOLDER = '{ "__sunnavok_placeholder": true }';
const MAX_BODY = 1024 * 1024;
const STATIC_FILES = new Set(['index.html', 'app.js', 'styles.css']);
const CONTENT_TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8' };

function defaultLog(entry) {
  process.stderr.write(`${JSON.stringify(entry)}\n`);
}

async function readState(statePath) {
  try {
    const raw = await readFile(statePath, 'utf8');
    return raw.trim() ? JSON.parse(raw) : null;
  } catch (error) {
    if (error && error.code === 'ENOENT') return null;
    throw error;
  }
}

async function writeState(statePath, state) {
  await mkdir(dirname(statePath), { recursive: true });
  const tmp = `${statePath}.${process.pid}.${randomUUID()}.tmp`;
  await writeFile(tmp, `${JSON.stringify(state, null, 2)}\n`, 'utf8');
  await rename(tmp, statePath);
}

async function readJsonFile(filePath) {
  try {
    const raw = await readFile(filePath, 'utf8');
    return raw.trim() ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

/** Dernière ligne JSONL correspondante ; ne retourne que des champs publics. */
async function lastMatchingLine(filePath, predicate, limit = 500) {
  try {
    const raw = await readFile(filePath, 'utf8');
    const lines = raw.split(/\r?\n/).filter(Boolean).slice(-limit);
    for (let index = lines.length - 1; index >= 0; index -= 1) {
      let row;
      try { row = JSON.parse(lines[index]); } catch { continue; }
      if (row && predicate(row)) return row;
    }
  } catch {
    return null;
  }
  return null;
}

function lineStamp(row) {
  for (const key of ['ts', 'at', 'checkedAt', 'checked_at', 'verifiedAt']) {
    const value = row && row[key];
    if (typeof value === 'string' && Number.isFinite(Date.parse(value))) return value;
  }
  return null;
}

/** Une ligne périmée n'est pas une preuve : on cherche la dernière ligne fraîche. */
function isFreshLine(row) {
  const stamp = lineStamp(row);
  if (!stamp) return false;
  const parsed = Date.parse(stamp);
  const now = Date.now();
  return parsed <= now + 5 * 60 * 1000 && now - parsed <= VERIFY_TTL_MS;
}

/** Agrège uniquement les champs publics des rapports des robots — jamais de secret. */
export async function buildSystemStatus(reportsDir, brainMetricsPath = DEFAULT_BRAIN_METRICS) {
  const raw = {};
  for (const [key, file] of Object.entries(REPORT_FILES)) {
    raw[key] = await readJsonFile(join(reportsDir, file));
  }
  const quality = raw.quality || {};
  const checks = quality.checks || {};
  const vault = (raw.vault || {}).checks || {};
  const backlog = raw.backlog || {};
  const brains = raw.brains || {};
  const router = brains.router_health || {};
  const metrics = await readJsonFile(brainMetricsPath);
  const rate = Number(metrics && metrics.tokensPerSecond);
  const brainMetrics = metrics && metrics.available === true && Number.isFinite(rate)
    ? {
      available: true,
      model: String(metrics.model || ''),
      promptTokens: Number.isFinite(Number(metrics.promptTokens)) ? Number(metrics.promptTokens) : null,
      completionTokens: Number.isFinite(Number(metrics.completionTokens)) ? Number(metrics.completionTokens) : null,
      elapsedMs: Number.isFinite(Number(metrics.elapsedMs)) ? Number(metrics.elapsedMs) : null,
      tokensPerSecond: Math.round(rate * 100) / 100,
      checkedAt: metrics.checkedAt ?? null,
      reason: null,
    }
    : {
      available: false, reason: 'no_data_source', model: null,
      promptTokens: null, completionTokens: null, elapsedMs: null,
      tokensPerSecond: null, checkedAt: null,
    };
  const available = Object.values(raw).some((value) => value !== null);

  return {
    checkedAt: new Date().toISOString(),
    available,
    source: 'robot reports',
    robots: {
      sentinel: { ok: checks.endpoints === true, summary: quality.endpoints || null },
      quality: {
        ok: Object.values(checks).length > 0 && Object.values(checks).every(Boolean),
        pythonRan: quality.python?.ran ?? null,
        pythonOk: quality.python?.ok ?? null,
        dashboardPassed: quality.dashboard?.passed ?? null,
        envHashMatches: quality.env?.hash_matches ?? null,
      },
      vault: {
        ok: vault.ok ?? null,
        jarvisPort5000: vault.jarvis_port_5000 ?? null,
        graphLocalBrain: vault.graph_local_brain ?? null,
      },
      backlog: {
        ok: Array.isArray(backlog.items),
        open: Array.isArray(backlog.items) ? backlog.items.length : null,
        missingSources: Array.isArray(backlog.missing_sources) ? backlog.missing_sources : [],
      },
    },
    brains: {
      available: Boolean(available && router.count > 0),
      count: router.count ?? 0,
      active: router.active ?? null,
      models: Array.isArray(router.available) ? router.available : [],
      provider: brains.gateway_status?.provider ?? null,
      routedVia: brains.gateway_completion?.routed_via ?? null,
      checkedAt: brains.checked_at ?? null,
    },
    brainMetrics,
    graph: {
      nodes: vault.nodes ?? quality.graph?.nodes ?? null,
      edges: vault.edges ?? quality.graph?.edges ?? null,
      jarvisBrainEdge: vault.graph_jarvis_brain_edge ?? quality.graph?.graph_jarvis_brain_edge ?? null,
      noCdn: quality.graph?.graph_no_cdn ?? null,
    },
  };
}

/** Rapport exécutif lisible, construit uniquement à partir de l'état et des rapports. */
export function buildExecutiveReport(state, status) {
  const lines = ['# SUNNAVOK — تقرير تنفيذي', '', `الوقت: ${status.checkedAt}`, ''];
  if (!state) {
    lines.push('المعطيات: **aucune donnée enregistrée** — اللوحة ما عندهاش حالة محفوظة بعد.', '');
  } else {
    const fields = state.fields || {};
    lines.push('## المعطيات المحفوظة');
    lines.push(`- ثمن الساعة: ${fields['g-rate'] || '—'} | المستهلكات: ${fields['g-cons'] || '—'}% | المصاريف: ${fields['g-over'] || '—'}% | الهامش: ${fields['g-margin'] || '—'}%`);
    const products = Array.isArray(state.products) ? state.products : [];
    lines.push(`- المنتوجات: ${products.length}`);
    for (const product of products.slice(0, 12)) {
      lines.push(`  - ${product.name || 'منتوج بلا اسم'} × ${product.qty || '—'}`);
    }
    const todo = state.todo && typeof state.todo === 'object' ? state.todo : {};
    const done = Object.values(todo).filter(Boolean).length;
    lines.push(`- المهام: ${done}/${Object.keys(todo).length} منجزة`);
    lines.push('');
  }

  lines.push('## الحالة التقنية');
  lines.push(`- الخدمة: ${status.available ? 'rapports disponibles' : '**statut indisponible**'}`);
  lines.push(`- الحرّاس: ${status.robots.sentinel.summary || '—'}`);
  lines.push(`- الجودة: Python ${status.robots.quality.pythonRan ?? '—'} | Dashboard ${status.robots.quality.dashboardPassed ?? '—'} | empreinte .env ${status.robots.quality.envHashMatches === true ? 'ok' : 'غير متحقق'}`);
  lines.push(`- العقول المحلية: ${status.brains.count} متاح | النشط: ${status.brains.active || '—'} | المسار: ${status.brains.routedVia || '—'}`);
  lines.push(`- الجراف: ${status.graph.nodes ?? '—'} عقدة / ${status.graph.edges ?? '—'} رابط`);
  const missing = status.robots.backlog.missingSources;
  lines.push(`- مصادر ناقصة: ${missing.length ? missing.join(', ') : 'none'}`);
  lines.push('', '_كل الأرقام مأخوذة من تقارير SYS_01..04 والحالة المحفوظة؛ ما كاينش تخمين ولا سر._', '');
  return lines.join('\n');
}

/** Miroir local du journal d'audit : champs whitelistés, jamais de secret. */
export async function buildAgentDigest(reportsDir) {
  const report = await readJsonFile(join(reportsDir, AGENT_AUDIT_FILE));
  if (!report || report.available !== true || !Array.isArray(report.items)) {
    return { available: false, reason: 'no_data_source', items: [] };
  }
  const items = report.items.slice(-20).map((item) => ({
    id: typeof item?.id === 'string' ? item.id.slice(0, 16) : '',
    detail: typeof item?.detail === 'string' ? item.detail.slice(0, 240) : '',
  })).filter((item) => item.id && item.detail);
  return {
    available: true,
    checkedAt: typeof report.checked_at === 'string' ? report.checked_at : null,
    latest: typeof report.latest === 'string' ? report.latest.slice(0, 16) : null,
    items,
  };
}

const LEDGER_STATUSES = ['succeeded', 'failed', 'timed_out', 'cancelled', 'running'];

function publicLedger(ledger) {
  if (!ledger) return { available: false, reason: 'no_data_source', stats: null, recent: [] };
  const rawStats = ledger.stats && typeof ledger.stats === 'object' ? ledger.stats : {};
  const stats = {};
  for (const key of LEDGER_STATUSES) stats[key] = Number(rawStats[key] || 0);
  stats.total = Number(rawStats.total || 0);
  const recent = (Array.isArray(ledger.runs) ? ledger.runs : []).slice(0, 10).map((run) => ({
    id: run.id ?? null,
    action: String(run.action || ''),
    actor: String(run.actor || ''),
    status: String(run.status || ''),
    createdAt: run.createdAt ?? run.created_at ?? null,
  }));
  return { available: true, generatedAt: ledger.generatedAt ?? null, stats, recent };
}

function publicInternet(data) {
  if (!data) return { available: false, reason: 'no_data_source', mode: null, host: null, checkedAt: null, latencyMs: null };
  return {
    available: Boolean(data.available),
    mode: String(data.mode || 'internet'),
    host: String(data.host || ''),
    checkedAt: data.checkedAt ?? null,
    reason: data.reason ?? null,
    latencyMs: Number.isFinite(data.latencyMs) ? data.latencyMs : null,
  };
}

function redactPublic(text) {
  return String(text || '').replace(
    /(api[_-]?key|token|password|secret|authorization)\s*[=:]\s*\S+/gi,
    '$1=<redacted>'
  );
}

/** État vocal public : dernier tour et daemon, sans jamais exposer de secret. */
export async function publicVoice({
  inboxPath = DEFAULT_VOICE_INBOX,
  lockPath = DEFAULT_VOICE_LOCK,
  statusPath = DEFAULT_VOICE_STATUS,
} = {}) {
  let status = null;
  try {
    const raw = JSON.parse(await readFile(statusPath, 'utf8'));
    if (raw && VOICE_STAGES.has(raw.stage)) {
      const level = Number(raw.level);
      status = {
        stage: raw.stage,
        level: Number.isFinite(level) ? Math.round(Math.min(1, Math.max(0, level)) * 100) / 100 : 0,
        statusAt: raw.updatedAt ?? null,
        statusReason: raw.reason ? redactPublic(String(raw.reason)).slice(0, 160) : null,
      };
    }
  } catch {
    status = null;
  }
  let row = null;
  try {
    const lines = (await readFile(inboxPath, 'utf8')).split('\n').filter(Boolean);
    row = lines.length ? JSON.parse(lines[lines.length - 1]) : null;
  } catch {
    row = null;
  }
  let pid = '';
  try {
    pid = (await readFile(lockPath, 'utf8')).trim();
  } catch {
    pid = '';
  }
  const running = /^\d+$/.test(pid);
  if (!row && !running && !status) {
    return {
      available: false, reason: 'no_data_source', running: false, mode: null,
      lastAt: null, lastHeard: '', lastReply: '', lastOk: null,
      stage: null, level: null, statusAt: null,
    };
  }
  return {
    available: true,
    reason: row?.reason ?? status?.statusReason ?? null,
    running,
    mode: running ? 'always_on_voice' : status ? 'voice_status_only' : 'voice_inbox_only',
    lastAt: row?.ts ?? null,
    lastHeard: redactPublic(row?.heard).slice(0, 160),
    lastReply: redactPublic(row?.reply).slice(0, 160),
    lastOk: row ? Boolean(row.ok) : null,
    stage: status?.stage ?? null,
    level: status?.level ?? null,
    statusAt: status?.statusAt ?? null,
  };
}

/** Vue « est-ce que JARVIS attend quelque chose de moi ? » — champs publics uniquement. */
export async function buildAttention(
  reportsDir,
  ledgerPath = DEFAULT_LEDGER_PATH,
  internetPath = DEFAULT_INTERNET_PATH,
  voice = {}
) {
  const quality = (await readJsonFile(join(reportsDir, 'quality_guard_report.json'))) || {};
  const backlog = (await readJsonFile(join(reportsDir, 'backlog_scout_report.json'))) || {};
  const brains = (await readJsonFile(join(reportsDir, 'local_brain_verification.json'))) || {};
  const ledger = await readJsonFile(ledgerPath);
  const internet = await readJsonFile(internetPath);
  const items = [];
  const add = (id, level, reason, detail) => {
    if (items.length >= 20) return;
    items.push({ id, level, reason, detail: String(detail).slice(0, 200) });
  };

  for (const [key, value] of Object.entries(quality.checks || {})) {
    if (value === false) add(`guard-${key}`, 'error', 'guard_failed', key);
  }
  const match = /down=(\d+)/.exec(String(quality.endpoints || ''));
  if (match && Number(match[1]) > 0) add('services-down', 'error', 'services_down', match[1]);

  const missing = Array.isArray(backlog.missing_sources) ? backlog.missing_sources : [];
  if (missing.length) add(`source-${missing.join('-')}`, 'info', 'no_data_source', missing.join(','));

  if (!(Number(brains.router_health?.count || 0) > 0)) {
    add('local-brain', 'warning', 'no_local_brain', 'router_health.count=0');
  }

  if (ledger) {
    const stats = ledger.stats && typeof ledger.stats === 'object' ? ledger.stats : {};
    for (const key of ['failed', 'timed_out', 'running']) {
      if (Number(stats[key] || 0) > 0) {
        add(`ledger-${key}`, key === 'failed' ? 'error' : 'warning', `${key}_runs`, stats[key]);
      }
    }
    for (const run of (Array.isArray(ledger.runs) ? ledger.runs : []).slice(0, 12)) {
      if (run.status === 'failed' || run.status === 'timed_out' || run.status === 'running') {
        add(`run-${run.id}-${run.status}`, run.status === 'failed' ? 'error' : 'warning',
          'run_needs_attention', `${run.action || '?'} / ${run.actor || '?'}`);
      }
    }
  }

  return {
    checkedAt: new Date().toISOString(),
    available: true,
    product: 'ESPRIEATHER',
    source: 'robot reports + run ledger',
    needsAttention: items.some((item) => item.level === 'error' || item.level === 'warning'),
    items,
    internet: publicInternet(internet),
    voice: await publicVoice(voice),
    ledger: publicLedger(ledger),
  };
}

const ACTION_DECISIONS = new Set(['approved_once', 'denied']);

function decidedBy(payload) {
  if (!payload || typeof payload !== 'object') return 'hud';
  const value = payload.decidedBy ?? payload.decided_by ?? 'hud';
  return typeof value === 'string' ? value.slice(0, 40) : 'hud';
}

function scrubAction(value, max = 200) {
  return String(value ?? '').replace(
    /(?:api[_-]?key|token|password|secret|authorization|bearer)\s*[=:]\s*\S+/gi,
    '[redacted]'
  ).slice(0, max);
}

/** Le dossier d'actions existe dès le premier démarrage, vide et honnête. */
export async function ensureActionRequests(statePath = DEFAULT_ACTION_REQUESTS) {
  try {
    await readFile(statePath, 'utf8');
  } catch (error) {
    if (!error || error.code !== 'ENOENT') throw error;
    await mkdir(dirname(statePath), { recursive: true });
    await writeFile(statePath, '[]\n', 'utf8');
  }
}

/**file d'actions locales : champs whitelistés, jamais de secret, jamais d'exécution. */
export async function buildActionApprovals(statePath = DEFAULT_ACTION_REQUESTS) {
  if (statePath === DEFAULT_ACTION_REQUESTS) await ensureActionRequests(statePath);
  const rows = await readJsonFile(statePath);
  if (!Array.isArray(rows)) {
    return { available: false, reason: 'no_data_source', checkedAt: new Date().toISOString(), items: [] };
  }
  const keys = ['id', 'action', 'target', 'reason', 'source', 'status', 'createdAt', 'decidedAt', 'decidedBy'];
  return {
    available: true,
    checkedAt: new Date().toISOString(),
    items: rows.slice(-20).map((row) => Object.fromEntries(
      keys.map((key) => [key, key in (row || {})
        ? (key === 'target' || key === 'reason' ? scrubAction(row[key]) : row[key])
        : null])
    )),
  };
}

/** Décision explicite et unique, sans tiers ni commande : proposed → approved_once|denied. */
export async function decideAction(
  statePath,
  auditPath,
  actionId,
  decision,
  decidedBy = 'hud'
) {
  if (!ACTION_DECISIONS.has(decision)) {
    const error = new Error('invalid_decision');
    error.code = 'INVALID_DECISION';
    throw error;
  }
  const rows = await readJsonFile(statePath);
  if (!Array.isArray(rows)) {
    const error = new Error('no_data_source');
    error.code = 'NO_DATA_SOURCE';
    throw error;
  }
  const row = rows.find((item) => item && String(item.id) === String(actionId));
  if (!row || row.status !== 'proposed') {
    const error = new Error('invalid_transition');
    error.code = 'INVALID_TRANSITION';
    throw error;
  }
  const previous = String(row.status);
  row.status = decision;
  row.decidedAt = new Date().toISOString();
  row.decidedBy = scrubAction(decidedBy, 40);
  await writeState(statePath, rows.slice(-200));
  await mkdir(dirname(auditPath), { recursive: true });
  const entry = {
    at: new Date().toISOString(),
    id: String(row.id),
    from: previous,
    to: decision,
    actor: 'hud',
    transition: `${previous}->${decision}`,
  };
  await appendFile(auditPath, `${JSON.stringify(entry)}\n`, 'utf8');
  return { item: row, transition: entry.transition };
}

/** Registre public des capacités : statut + preuve + étape, sans jamais deviner. */
export async function buildCapabilities(
  reportsDir,
  {
    brainMetricsPath = DEFAULT_BRAIN_METRICS,
    actionRequestsPath = DEFAULT_ACTION_REQUESTS,
    actionAuditPath = DEFAULT_ACTION_AUDIT,
    voiceStatusPath = DEFAULT_VOICE_STATUS,
    voiceInboxPath = DEFAULT_VOICE_INBOX,
    egressPath = DEFAULT_EGRESS_EVIDENCE,
    bargeReviewPath = DEFAULT_BARGE_REVIEW,
  } = {}
) {
  if (actionRequestsPath === DEFAULT_ACTION_REQUESTS) await ensureActionRequests(actionRequestsPath);
  const brains = (await readJsonFile(join(reportsDir, 'local_brain_verification.json'))) || {};
  const quality = (await readJsonFile(join(reportsDir, 'quality_guard_report.json'))) || {};
  const backlog = (await readJsonFile(join(reportsDir, 'backlog_scout_report.json'))) || {};
  const metrics = await readJsonFile(brainMetricsPath);
  const actions = await readJsonFile(actionRequestsPath);
  const voice = await readJsonFile(voiceStatusPath);
  const egress = await readJsonFile(egressPath);
  const bargeReview = await readJsonFile(bargeReviewPath);
  const invalidBarge = new Set(
    (Array.isArray(bargeReview?.invalidTimestamps) ? bargeReview.invalidTimestamps : [])
      .map((value) => Date.parse(value)).filter(Number.isFinite)
  );
  const bargeRejected = invalidBarge.size > 0;
  const voiceSuccess = await lastMatchingLine(voiceInboxPath, (row) =>
    isFreshLine(row) && row.ok === true && row.spoken === true && row.engine === 'local-brain');
  const bargeEvent = await lastMatchingLine(voiceInboxPath, (row) =>
    isFreshLine(row) && row.reason === 'barge_in' && !invalidBarge.has(Date.parse(row.ts)));
  const approvalDecision = await lastMatchingLine(actionAuditPath, (row) =>
    isFreshLine(row) && (typeof row.transition === 'string'
      ? row.transition.includes('->') : Boolean(row.from && row.to)));
  const router = brains.router_health || {};
  const checks = quality.checks || {};
  const graph = quality.graph || {};
  const missing = Array.isArray(backlog.missing_sources) ? backlog.missing_sources : [];
  const pending = Array.isArray(actions)
    ? actions.filter((item) => item && item.status === 'proposed').length
    : 0;
  const list = [];
  const add = (id, status, evidence, next, verifiedAt = null) => {
    const stamp = verifiedStamp(status, verifiedAt);
    list.push({
      id, status: stamp.status, evidence, next: String(next).slice(0, 200),
      verifiedAt: stamp.verifiedAt, expiresAt: stamp.expiresAt,
    });
  };

  if (Number(router.count) > 0 && router.active) {
    add('local-brain', 'live_verified', [
      { source: 'local_brain_verification.json', field: 'router_health.active', value: String(router.active) },
      { source: 'local_brain_verification.json', field: 'router_health.count', value: Number(router.count) },
    ], 'Retester POST /v1/chat/completions sur le routeur local :31416',
    stampOf(brains, join(reportsDir, 'local_brain_verification.json')));
  } else {
    add('local-brain', 'not_available', [
      { source: 'local_brain_verification.json', field: 'router_health.count', value: Number(router.count) || 0 },
    ], 'Installer un GGUF vérifié puis relancer le routeur local :31416');
  }

  if (voiceSuccess) {
    const stamp = lineStamp(voiceSuccess);
    add('local-voice', 'live_verified', [
      { source: 'voice_inbox.jsonl', field: 'ts', value: stamp },
      { source: 'voice_inbox.jsonl', field: 'engine', value: String(voiceSuccess.engine) },
      { source: 'voice_inbox.jsonl', field: 'spoken', value: Boolean(voiceSuccess.spoken) },
      { source: 'voice_inbox.jsonl', field: 'language', value: String(voiceSuccess.language || '') },
    ], 'Refaire un essai micro réel avant la expiration de la preuve', stamp);
  } else if (voice && VOICE_STAGES.has(voice.stage)) {
    add('local-voice', 'implemented_unverified', [
      { source: 'voice_status.json', field: 'stage', value: String(voice.stage) },
    ], 'Faire un essai micro réel et vérifier la réception SAPI locale');
  } else {
    add('local-voice', 'not_available', [
      { source: 'voice_status.json', field: 'stage', value: 'no_data_source' },
    ], 'Démarrer le daemon vocal local puis refaire un essai micro');
  }

  if (bargeEvent) {
    const stamp = lineStamp(bargeEvent);
    add('barge-in', 'live_verified', [
      { source: 'voice_inbox.jsonl', field: 'reason', value: 'barge_in' },
      { source: 'voice_inbox.jsonl', field: 'ts', value: stamp },
    ], 'Refaire une vraie interruption microphone avant expiration', stamp);
  } else {
    add('barge-in', 'implemented_unverified', [
      { source: 'voice_inbox.jsonl', field: 'reason', value: 'no_recent_event' },
      ...(bargeRejected ? [{ source: 'barge_in_review.json', field: 'review', value: 'invalidated' }] : []),
    ], 'Interrompre réellement la parole pendant une réponse locale');
  }

  if (missing.length) {
    add('documentary-sources', 'needs_user_data', [
      { source: 'backlog_scout_report.json', field: 'missing_sources', value: missing.join(',') },
    ], 'Fournir des fichiers réels dans data/sources/legal, fiscal et travail');
  } else if (backlog.checked_at) {
    add('documentary-sources', 'live_verified', [
      { source: 'backlog_scout_report.json', field: 'checked_at', value: String(backlog.checked_at) },
    ], 'Conserver les fichiers sources et refaire le contrôle',
    stampOf(backlog, join(reportsDir, 'backlog_scout_report.json')));
  } else {
    add('documentary-sources', 'not_available', [
      { source: 'backlog_scout_report.json', field: 'missing_sources', value: 'no_data_source' },
    ], 'Fournir des fichiers sources réels puis relancer le robot backlog');
  }

  if (graph.graph_no_cdn === true || checks.graph === true) {
    add('secure-hud', 'live_verified', [
      { source: 'quality_guard_report.json', field: 'graph.graph_no_cdn', value: graph.graph_no_cdn === true },
      { source: 'quality_guard_report.json', field: 'graph.nodes', value: Number(graph.nodes) || 0 },
    ], 'Maintenir le HUD sans ressource externe et sans commande d’exécution',
    stampOf(quality, join(reportsDir, 'quality_guard_report.json')));
  } else {
    add('secure-hud', 'not_available', [
      { source: 'quality_guard_report.json', field: 'graph.graph_no_cdn', value: 'no_data_source' },
    ], 'Relancer le contrôle du graphe local');
  }

  const rate = Number(metrics && metrics.tokensPerSecond);
  if (metrics && metrics.available === true && Number.isFinite(rate) && rate >= 0) {
    add('brain-metrics', 'live_verified', [
      { source: 'brain_metrics.json', field: 'elapsedMs', value: Number(metrics.elapsedMs) || 0 },
      { source: 'brain_metrics.json', field: 'tokensPerSecond', value: Math.round(rate * 100) / 100 },
    ], 'Continuer à mesurer chaque réponse locale réelle',
    stampOf(metrics, brainMetricsPath));
  } else {
    add('brain-metrics', 'not_available', [
      { source: 'brain_metrics.json', field: 'available', value: 'no_data_source' },
    ], 'Attendre une réponse locale réelle avec données d’usage');
  }

  if (approvalDecision) {
    const stamp = lineStamp(approvalDecision);
    add('action-approval', 'live_verified', [
      { source: 'action_audit.jsonl', field: 'transition',
        value: String(approvalDecision.transition || `${approvalDecision.from}->${approvalDecision.to}`) },
      { source: 'action_audit.jsonl', field: 'at', value: stamp },
      { source: 'action_requests.json', field: 'pending', value: pending },
    ], 'Refaire une décision explicite depuis le HUD avant expiration', stamp);
  } else {
    add('action-approval', 'implemented_unverified', [
      { source: 'action_requests.json', field: 'pending', value: pending },
      { source: 'action_audit.jsonl', field: 'decisions', value: 0 },
    ], 'Proposer une action locale puis l’accorder ou la refuser explicitement depuis le HUD');
  }

  const egressEvidence = egress ? [
    { source: 'egress_selfcheck.json', field: 'loopbackOnly', value: Boolean(egress.loopbackOnly) },
    { source: 'egress_selfcheck.json', field: 'webLinksPublicHttpsOnly',
      value: Boolean(egress.webLinksPublicHttpsOnly) },
    { source: 'egress_selfcheck.json', field: 'modelHost', value: String(egress.modelHost || '') },
  ] : [
    { source: 'egress_selfcheck.json', field: 'selfcheck', value: 'no_data_source' },
  ];
  if (egress && egress.ok === true && egress.loopbackOnly === true
      && egress.webLinksPublicHttpsOnly === true && isFreshLine(egress)) {
    add('local-egress-guard', 'live_verified', egressEvidence,
      'Revérifier les URL locales et les liens publics avant expiration', lineStamp(egress));
  } else if (egress) {
    add('local-egress-guard', 'implemented_unverified', egressEvidence,
      'Relancer le selfcheck de sortie locale', lineStamp(egress));
  } else {
    add('local-egress-guard', 'not_available', egressEvidence,
      'Produire une preuve de sortie locale avec le selfcheck egress');
  }

  return {
    checkedAt: new Date().toISOString(),
    available: true,
    product: 'ESPRIEATHER',
    source: 'robot reports + local state',
    capabilities: list.slice(0, 20),
  };
}

function send(res, status, body, type = 'application/json; charset=utf-8') {
  res.writeHead(status, { 'content-type': type, 'cache-control': 'no-store' });
  res.end(typeof body === 'string' ? body : JSON.stringify(body));
}

/** CSRF: un PUT venant d'un navigateur porte toujours un Origin loopback autorisé. */
function requireLoopbackOrigin(req, res, requestId) {
  const origin = req.headers.origin;
  const site = String(req.headers['sec-fetch-site'] || '').toLowerCase();
  if ((origin && !LOCAL_ORIGINS.has(origin)) || site === 'cross-site') {
    send(res, 403, errorEnvelope('CROSS_ORIGIN_REFUSED', 'Mutation refusée hors origine locale', requestId));
    return false;
  }
  return true;
}

/** J80 — sonde loopback uniquement : aucun secret, aucun appel externe. */
async function probeAtulyaHealth() {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 1500);
  try {
    const response = await fetch('http://127.0.0.1:8501/api/health', { signal: controller.signal });
    if (!response.ok) return null;
    const body = await response.json();
    return body && body.status === 'ok' && body.brain_configured === true ? body : null;
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

/** J78/J80 — inventaire local du dépôt Atulya-Tantra importé, sans secret ni réseau. */
export async function buildAtulya(vendorDir = DEFAULT_ATULYA_DIR, probe = probeAtulyaHealth,
                                  visionEvidencePath = DEFAULT_VISION_EVIDENCE,
                                  mcpEvidencePath = DEFAULT_MCP_EVIDENCE,
                                  vaultEvidencePath = DEFAULT_VAULT_EVIDENCE,
                                   wakeEvidencePath = DEFAULT_WAKE_EVIDENCE) {
  const add = (list, id, status, source, field, value, next, verifiedAt = null) => {
    const stamp = verifiedStamp(status, verifiedAt);
    list.push({
      id, status: stamp.status, evidence: [{ source, field, value: String(value) }],
      next: String(next).slice(0, 200), verifiedAt: stamp.verifiedAt, expiresAt: stamp.expiresAt,
    });
  };
  const features = [];
  let fileCount = 0;
  let totalBytes = 0;
  let entries = [];
  let core = false;
  let voice = false;
  let mcp = false;
  let skills = false;
  let pc = false;
  let cloud = false;
  let external = false;
  let version = 'unknown';

  try {
    entries = await readdir(vendorDir, { recursive: true, withFileTypes: true });
    const files = entries.filter((entry) => entry.isFile());
    const fullPath = (entry) => entry.parentPath
      ? join(entry.parentPath, entry.name)
      : join(vendorDir, entry.name);
    fileCount = files.length;
    const sizes = await Promise.all(files.map(async (entry) => {
      try {
        return (await stat(fullPath(entry))).size;
      } catch {
        return 0;
      }
    }));
    totalBytes = sizes.reduce((sum, size) => sum + size, 0);
    const names = new Set(files.map((entry) => entry.name));
    const paths = new Set(files.map((entry) => String(entry.parentPath || '').replace(/\\/g, '/')));
    core = files.some((entry) => String(entry.parentPath || '').replace(/\\/g, '/').endsWith('/atulya')
      && entry.name === 'server.py');
    skills = Array.from(paths).some((path) => path.endsWith('/tools'));
    voice = names.has('voice_context.py') || names.has('openwakeword') || false;
    mcp = names.has('mcp_connections.py');
    skills = skills || names.has('proactive.py');
    pc = names.has('Connect-This-PC.cmd');
    const reqs = files.find((entry) => entry.name === 'requirements.lock.txt');
    const cli = files.find((entry) => entry.name === 'cli.py');
    const auth = files.find((entry) => entry.name === 'google_auth.py');
    const reqText = reqs ? await readFile(fullPath(reqs), 'utf8') : '';
    const cliText = cli ? await readFile(fullPath(cli), 'utf8') : '';
    if (/openwakeword|faster-whisper/i.test(reqText)) voice = true;
    if (/^mcp==/mi.test(reqText)) mcp = true;
    cloud = /cloudflare|remote/i.test(cliText);
    external = Boolean(auth) || /TELEGRAM_BOT_TOKEN/i.test(cliText);
    const initFile = files.find((entry) => entry.name === '__init__.py');
    if (initFile) {
      const initText = await readFile(fullPath(initFile), 'utf8');
      const match = initText.match(/__version__\s*=\s*["']([^"']+)["']/);
      if (match) version = match[1];
    }
  } catch {
    fileCount = 0;
  }

  // live_verified uniquement avec une réponse locale réelle et un cerveau configuré.
  let live = null;
  if (core) {
    try { live = await probe(); } catch { live = null; }
  }

  add(features, 'atulya-core', live ? 'live_verified' : (core ? 'implemented_unverified' : 'not_available'),
    live ? 'GET http://127.0.0.1:8501/api/health' : 'GITHUB_IMPORT/Atulya-Tantra',
    live ? 'status/brain_configured' : 'atulya/server.py',
    live ? 'ok/true' : (core ? 'present' : 'absent'),
    live ? 'Preuve locale: /api/health 200, cerveau local configuré; aucun cloud.'
         : 'Lancer START_ATULYA_TANTRA.cmd puis vérifier /health avant de dire live_verified',
    live ? new Date().toISOString() : null);
  const healthSource = 'GET http://127.0.0.1:8501/api/health';
  const liveStamp = live ? new Date().toISOString() : null;
  const ready = (field) => Boolean(live && live[field] === true);
  add(features, 'atulya-voice',
    ready('voice_ready') ? 'live_verified' : ((live || voice) ? 'implemented_unverified' : 'not_available'),
    live ? healthSource : 'GITHUB_IMPORT/Atulya-Tantra',
    live ? 'voice_ready' : 'voice+wake-word',
    live ? String(ready('voice_ready')) : (voice ? 'present' : 'absent'),
    'Faire un essai micro réel et vérifier voice_ready=true dans /api/health', liveStamp);
  add(features, 'atulya-speech', ready('speech_ready') ? 'live_verified' : 'not_available',
    live ? healthSource : 'GITHUB_IMPORT/Atulya-Tantra', 'speech_ready', String(ready('speech_ready')),
    'Installer les modèles TTS locaux puis vérifier speech_ready=true', liveStamp);
  // Le simple fichier mmproj ne prouve pas une inférence : seule une réponse
  // locale récente du serveur llama.cpp autorise live_verified (TTL 7 jours).
  const visionProof = await readJsonFile(visionEvidencePath);
  const wakeProof = await readJsonFile(wakeEvidencePath);
  const visionLive = Boolean(visionProof && visionProof.ok === true
    && typeof visionProof.answer === 'string' && visionProof.answer.trim()
    && isFreshLine(visionProof));
  add(features, 'atulya-vision',
    visionLive ? 'live_verified' : (ready('vision_ready') || live ? 'implemented_unverified' : 'not_available'),
    visionLive ? 'POST http://127.0.0.1:11438/v1/chat/completions (llama.cpp local)'
      : (live ? healthSource : 'GITHUB_IMPORT/Atulya-Tantra'),
    visionLive ? 'local_vision_inference' : 'vision_ready',
    visionLive ? 'true' : String(ready('vision_ready')),
    visionLive ? 'View.preuve: réponse locale récente à une image réelle, sans token cloud'
      : 'Faire une inférence locale réelle avec le mmproj puis vérifier la preuve datée',
    visionLive ? lineStamp(visionProof) : null);
  let wake = false;
  try {
    const wakeDir = join(vendorDir, 'models', 'voice', 'wake');
    wake = (await readdir(wakeDir, { withFileTypes: true }))
      .some((entry) => entry.isFile() && /\.(onnx|tflite)$/i.test(entry.name));
  } catch {
    wake = false;
  }
  const wakeLive = Boolean(wakeProof && wakeProof.ok === true
    && Number(wakeProof.hits) > 0 && isFreshLine(wakeProof));
  add(features, 'atulya-wake',
    wakeLive ? 'live_verified' : (wake ? 'implemented_unverified' : 'not_available'),
    wakeLive ? 'wake_selfcheck.json'
      : (live ? healthSource : 'GITHUB_IMPORT/Atulya-Tantra/models/voice/wake'),
    wakeLive ? 'hits' : 'wake_word_models',
    wakeLive ? String(wakeProof.hits) : (wake ? 'present' : 'absent'),
    wakeLive ? 'Preuve locale: détection récente par le micro, sans envoi réseau'
      : 'Faire un essai réel de mot réveil puis vérifier wake_selfcheck.json',
    wakeLive ? lineStamp(wakeProof) : null);
  const mcpProof = await readJsonFile(mcpEvidencePath);
  const mcpLive = Boolean(mcpProof && mcpProof.ok === true
    && Array.isArray(mcpProof.tools) && mcpProof.tools.length
    && isFreshLine(mcpProof));
  add(features, 'atulya-mcp',
    mcpLive ? 'live_verified' : (mcp ? 'implemented_unverified' : 'not_available'),
    mcpLive ? 'stdio python -m atulya.cli mcp' : 'GITHUB_IMPORT/Atulya-Tantra',
    mcpLive ? 'local_mcp_handshake' : 'atulya/mcp_connections.py',
    mcpLive ? 'true' : (mcp ? 'present' : 'absent'),
    mcpLive ? 'Preuve locale: initialize + tools/list + tools/call via stdio'
      : 'Faire une poignée de main stdio locale réelle puis vérifier la preuve datée',
    mcpLive ? lineStamp(mcpProof) : null);
  const vaultProof = await readJsonFile(vaultEvidencePath);
  const vaultLive = Boolean(vaultProof && vaultProof.ok === true
    && vaultProof.noteCount > 0 && typeof vaultProof.topPath === 'string'
    && isFreshLine(vaultProof));
  add(features, 'atulya-vault-memory',
    vaultLive ? 'live_verified' : 'implemented_unverified',
    vaultLive ? 'python esprieaether/src/vault_memory.py (BM25 local)' : 'esprieaether/src/vault_memory.py',
    vaultLive ? 'local_vault_index' : 'vault_memory_module',
    vaultLive ? 'true' : 'present',
    vaultLive ? 'Preuve locale: requête BM25 récente sur les notes markdown du vault'
      : 'Lancer une requête locale sur le vault puis vérifier la preuve datée',
    vaultLive ? lineStamp(vaultProof) : null);
  add(features, 'atulya-skills', skills ? 'implemented_unverified' : 'not_available',
    'GITHUB_IMPORT/Atulya-Tantra', 'proactive/tools', skills ? 'present' : 'absent',
    'Vérifier chaque skill local avant de lui confier une action');
  add(features, 'atulya-cloud', cloud ? 'needs_user_data' : 'not_available',
    'GITHUB_IMPORT/Atulya-Tantra', 'remote/cloudflare', cloud ? 'code present, identifiants absents' : 'absent',
    'Fournir ses propres identifiants puis vérifier une session chiffrée réelle');
  add(features, 'atulya-external', external ? 'needs_user_data' : 'not_available',
    'GITHUB_IMPORT/Atulya-Tantra', 'telegram/google', external ? 'code present, comptes absents' : 'absent',
    'Connecter des comptes autorisés puis tester une livraison réelle');
  add(features, 'atulya-pc', pc ? 'needs_user_data' : 'not_available',
    'GITHUB_IMPORT/Atulya-Tantra', 'Connect-This-PC.cmd', pc ? 'present, non appairé' : 'absent',
    'Appairer le PC puis n’exécuter qu’une action approuvée explicitement');

  return {
    product: 'ESPRIEATHER',
    source: 'atulyaai/Atulya-Tantra',
    imported: core,
    fileCount,
    totalBytes,
    version,
    launcher: 'START_ATULYA_TANTRA.cmd',
    note: live
      ? 'preuve locale: /api/health 200 et brain_configured=true ; aucun cloud, aucune clé'
      : 'code importé et activable localement ; aucun statut live_verified sans preuve locale',
    features,
  };
}

function readBody(req) {
  return new Promise((resolveBody, rejectBody) => {
    let size = 0;
    const chunks = [];
    req.on('data', (chunk) => {
      size += chunk.length;
      if (size > MAX_BODY) {
        rejectBody(Object.assign(new Error('body too large'), { code: 'BODY_TOO_LARGE' }));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => resolveBody(Buffer.concat(chunks).toString('utf8')));
    req.on('error', rejectBody);
  });
}

export function createDashboardServer({
  dashboardDir = DEFAULT_DASHBOARD_DIR,
  statePath = DEFAULT_STATE_PATH,
  reportsDir = DEFAULT_REPORTS_DIR,
  ledgerPath = DEFAULT_LEDGER_PATH,
  internetPath = DEFAULT_INTERNET_PATH,
  brainMetricsPath = DEFAULT_BRAIN_METRICS,
  actionRequestsPath = DEFAULT_ACTION_REQUESTS,
  actionAuditPath = DEFAULT_ACTION_AUDIT,
  voiceStatusPath = DEFAULT_VOICE_STATUS,
  voiceInboxPath = DEFAULT_VOICE_INBOX,
  egressPath = DEFAULT_EGRESS_EVIDENCE,
  bargeReviewPath = DEFAULT_BARGE_REVIEW,
  atulyaDir = DEFAULT_ATULYA_DIR,
  voice = {},
  log = defaultLog,
} = {}) {
  return createServer(async (req, res) => {
    const requestId = randomUUID();
    const started = Date.now();
    const pathname = new URL(req.url, 'http://localhost').pathname;
    const origin = req.headers.origin;
    if (LOCAL_ORIGINS.has(origin)) {
      res.setHeader('access-control-allow-origin', origin);
      res.setHeader('vary', 'Origin');
      res.setHeader('access-control-allow-methods', 'GET, PUT, OPTIONS');
      res.setHeader('access-control-allow-headers', 'content-type');
    }
    let status = 200;

    let logged = false;
    const finish = () => {
      if (logged) return;
      logged = true;
      log({ requestId, method: req.method, path: pathname, status, durationMs: Date.now() - started });
    };
    res.on('finish', finish);
    res.on('close', finish);

    try {
      if (req.method === 'OPTIONS' && LOCAL_ORIGINS.has(origin)) {
        send(res, 204, '');
        return;
      }

      if (pathname === '/health' && req.method === 'GET') {
        send(res, 200, { status: 'ok', service: 'sunnavok-dashboard', time: new Date().toISOString() });
        return;
      }

      if (pathname === '/api/system/status' && req.method === 'GET') {
        const status = await buildSystemStatus(reportsDir, brainMetricsPath);
        send(res, 200, { ...status, requestId });
        return;
      }

      if (pathname === '/api/jarvis/attention' && req.method === 'GET') {
        send(res, 200, {
          ...(await buildAttention(reportsDir, ledgerPath, internetPath, voice)), requestId,
        });
        return;
      }

      if (pathname === '/api/jarvis/capabilities' && req.method === 'GET') {
        send(res, 200, {
          ...(await buildCapabilities(reportsDir, {
            brainMetricsPath, actionRequestsPath, actionAuditPath, voiceStatusPath, voiceInboxPath,
            egressPath,
            bargeReviewPath,
          })), requestId,
        });
        return;
      }

      if (pathname === '/api/jarvis/atulya' && req.method === 'GET') {
        send(res, 200, { ...(await buildAtulya(atulyaDir)), requestId });
        return;
      }

      if (pathname === '/api/jarvis/approvals' && req.method === 'GET') {
        send(res, 200, { ...(await buildActionApprovals(actionRequestsPath)), requestId });
        return;
      }

      if (pathname.startsWith('/api/jarvis/approvals/') && req.method === 'PUT') {
        if (!requireLoopbackOrigin(req, res, requestId)) return;
        const actionId = pathname.slice('/api/jarvis/approvals/'.length).replace(/[^a-zA-Z0-9_-]/g, '');
        let payload;
        try {
          payload = JSON.parse(await readBody(req));
        } catch (error) {
          status = 400;
          send(res, status, errorEnvelope('JSON_INVALID', 'Corps JSON invalide', requestId));
          return;
        }
        try {
          const result = await decideAction(
            actionRequestsPath, actionAuditPath, actionId, payload?.decision, decidedBy(payload)
          );
          send(res, 200, { ...result, requestId });
        } catch (error) {
          const code = error && error.code;
          status = code === 'INVALID_TRANSITION' || code === 'NO_DATA_SOURCE' ? 409 : 400;
          send(res, status, errorEnvelope(code || 'INVALID_REQUEST', 'Décision refusée', requestId));
        }
        return;
      }

      if (pathname === '/api/agent/audit' && req.method === 'GET') {
        const digest = await buildAgentDigest(reportsDir);
        send(res, 200, { ...digest, requestId });
        return;
      }

      if (pathname === '/api/report' && req.method === 'GET') {
        const state = await readState(statePath);
        const status = await buildSystemStatus(reportsDir);
        send(res, 200, buildExecutiveReport(state, status), 'text/markdown; charset=utf-8');
        return;
      }

      if (pathname === '/api/dashboard/state' && req.method === 'GET') {
        const state = await readState(statePath);
        send(res, 200, { state, requestId });
        return;
      }

      if (pathname === '/api/dashboard/state' && req.method === 'PUT') {
        if (!requireLoopbackOrigin(req, res, requestId)) return;
        let payload;
        try {
          payload = JSON.parse(await readBody(req));
        } catch (error) {
          status = error && error.code === 'BODY_TOO_LARGE' ? 413 : 400;
          send(res, status, errorEnvelope(status === 413 ? 'BODY_TOO_LARGE' : 'JSON_INVALID', 'Corps JSON invalide', requestId));
          return;
        }
        const code = validateState(payload);
        if (code) {
          status = 400;
          send(res, status, errorEnvelope(code, 'État DashboardState invalide', requestId));
          return;
        }
        const state = normalizeState(payload);
        await writeState(statePath, state);
        send(res, 200, { state, requestId });
        return;
      }

      const file = pathname === '/' || pathname === '/index.html' ? 'index.html' : pathname.slice(1);
      if (req.method === 'GET' && STATIC_FILES.has(file)) {
        const filePath = join(dashboardDir, file);
        let body = await readFile(filePath, 'utf8');
        if (file === 'index.html') {
          const state = await readState(statePath);
          const payload = JSON.stringify({ state, enums: { conditions: CONDITIONS, owners: OWNERS }, requestId })
            .replace(/</g, '\\u003c')
            .replace(/>/g, '\\u003e');
          if (!body.includes(PLACEHOLDER)) throw new Error('BOOTSTRAP_MARKER_MISSING');
          body = body.replace(PLACEHOLDER, payload);
        }
        send(res, 200, body, CONTENT_TYPES[extname(filePath)]);
        return;
      }

      status = 404;
      send(res, status, errorEnvelope('NOT_FOUND', 'Ressource introuvable', requestId));
    } catch (error) {
      status = 500;
      send(res, status, errorEnvelope('INTERNAL_ERROR', 'Erreur interne', requestId));
    }
  });
}

const isMain = process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url);
if (isMain) {
  const port = Number(process.env.PORT || 5100);
  const server = createDashboardServer();
  server.listen(port, '127.0.0.1', () => {
    defaultLog({ requestId: randomUUID(), method: 'LISTEN', path: `/:${port}`, status: 200, durationMs: 0 });
  });
  const shutdown = () => server.close(() => process.exit(0));
  process.on('SIGTERM', shutdown);
  process.on('SIGINT', shutdown);
}
