// passerelle REST locale — remplace les petits services Python à fichiers.
// Même format de board que esprieaether/src/veritas_kanban.py (markdown simple).
import { readFile, readdir, writeFile, mkdir } from 'node:fs/promises';
import { dirname, join } from 'node:path';

export const KANBAN_COLS = ['todo', 'doing', 'done'];
export const EVIDENCE_TTL_MS = 7 * 24 * 60 * 60 * 1000;

const SEED = [
  '# 📋 Sunna Kanban',
  '',
  '## todo',
  '- [ ] 🔴 تاريخ الشهادة السلبية (90 يوم!) — Amine',
  '- [ ] 🔴 ثمن الغلفنة — Galvafer 0522 67 46 31 — Amine',
  '- [ ] 🔴 3 عروض أثمنة (devis) — Amine',
  '- [ ] 🟡 اختيار اللوغو (F1/F3/F6/F10) — Amine',
  '- [ ] 🟡 6 صور حقيقية (ورشة + منتجات + équipe) — Amine',
  '- [ ] 🟢 GMB — business.google.com — Bot ready',
  '',
  '## doing',
  '- [ ] 🟢 Netlify site — live (keepalive 24/7)',
  '',
  '## done',
  '- [x] ✅ Netlify deploy + keepalive',
  '- [x] ✅ PDF devis builder',
  '- [x] ✅ Live price tracker (galva/zinc)',
  '- [x] ✅ Telegram /sunna commands',
  '- [x] ✅ SOP wiki',
  '- [x] ✅ 12 integrations linked',
  '',
].join('\n');

export function parseBoard(text) {
  const board = Object.fromEntries(KANBAN_COLS.map((col) => [col, []]));
  let current = null;
  for (const line of String(text).split(/\r?\n/)) {
    const header = line.trim().match(/^##\s+(\w+)/);
    if (header) {
      const col = header[1].toLowerCase();
      if (KANBAN_COLS.includes(col)) current = col;
      continue;
    }
    const item = line.match(/^\s*-\s*\[([ xX])\]\s*(.+)/);
    if (item && current) {
      board[current].push({ title: item[2].trim(), done: item[1].toLowerCase() === 'x' });
    }
  }
  return board;
}

export function boardToMarkdown(board) {
  const lines = ['# 📋 Sunna Kanban', ''];
  for (const col of KANBAN_COLS) {
    lines.push(`## ${col}`);
    for (const item of board[col] || []) lines.push(`- [${item.done ? 'x' : ' '}] ${item.title}`);
    lines.push('');
  }
  return `${lines.join('\n')}\n`;
}

function fail(code, message) {
  const error = new Error(message);
  error.code = code;
  throw error;
}

async function persist(boardPath, board) {
  await mkdir(dirname(boardPath), { recursive: true });
  await writeFile(boardPath, boardToMarkdown(board), 'utf8');
}

export async function readBoard(boardPath) {
  let text;
  try {
    text = await readFile(boardPath, 'utf8');
  } catch (error) {
    if (!error || error.code !== 'ENOENT') throw error;
    await persist(boardPath, parseBoard(SEED));
    return parseBoard(SEED);
  }
  return parseBoard(text);
}

export async function addBoardItem(boardPath, input = {}) {
  const title = typeof input.title === 'string' ? input.title.trim() : '';
  const col = typeof input.col === 'string' ? input.col : 'todo';
  if (!title) fail('BAD_TITLE', 'need title');
  if (!KANBAN_COLS.includes(col)) fail('BAD_COLUMN', 'need valid col');
  const board = await readBoard(boardPath);
  board[col].push({ title, done: col === 'done' });
  await persist(boardPath, board);
  return board;
}

export async function moveBoardItem(boardPath, input = {}) {
  const title = typeof input.title === 'string' ? input.title.trim() : '';
  const to = typeof input.to === 'string' ? input.to : '';
  if (!title) fail('BAD_TITLE', 'need title');
  if (!KANBAN_COLS.includes(to)) fail('BAD_COLUMN', 'need valid to');
  const board = await readBoard(boardPath);
  let found = null;
  for (const col of KANBAN_COLS) {
    for (const item of board[col]) {
      if (item.title.toLowerCase().includes(title.toLowerCase())) {
        found = { col, item };
        break;
      }
    }
    if (found) break;
  }
  if (!found) fail('NOT_FOUND', 'item not found');
  board[found.col].splice(board[found.col].indexOf(found.item), 1);
  found.item.done = to === 'done';
  board[to].push(found.item);
  await persist(boardPath, board);
  return board;
}

/* ---- J154 : phase 2 de la passerelle REST, fichiers locaux uniquement ---- */

const TTL_CACHE = new Map();

/** Mémoïse une lecture coûteuse sans jamais déclarer live_verified. */
export async function withTtlCache(key, loader, {
  cache = TTL_CACHE, ttlMs = 30_000, now = Date.now,
} = {}) {
  const at = now();
  const hit = cache.get(key);
  if (hit && at >= hit.at && at - hit.at < ttlMs) return hit.value;
  const value = await loader();
  cache.set(key, { at, value });
  return value;
}

export function clearTtlCache(key, cache = TTL_CACHE) {
  if (key === undefined) cache.clear();
  else cache.delete(key);
}

async function readJson(path) {
  if (!path) return null;
  try {
    const raw = await readFile(path, 'utf8');
    return raw.trim() ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function isFreshEvidence(row, { ttlMs = EVIDENCE_TTL_MS, now = Date.now } = {}) {
  const stamp = row && (row.checkedAt || row.checked_at || row.verifiedAt || row.updatedAt);
  const parsed = typeof stamp === 'string' ? Date.parse(stamp) : NaN;
  const at = now();
  return Number.isFinite(parsed) && parsed <= at + 5 * 60 * 1000 && at - parsed <= ttlMs;
}

/**
 * Vue GSM locale en lecture seule. Une preuve périmée OU absente ne devient
 * jamais live_verified : on dégrade et on lève une alerte explicite.
 */
export async function readGsmSnapshot({ gsmStatusPath, gsmWorkersPath, gsmModelTrialPath }) {
  const gsm = await readJson(gsmStatusPath);
  const workers = await readJson(gsmWorkersPath);
  const trial = await readJson(gsmModelTrialPath);
  const fresh = Boolean(gsm && isFreshEvidence(gsm));
  const alert = !gsm ? 'no_evidence' : (fresh ? null : 'expired');
  const status = !gsm ? 'needs_user_data'
    : (gsm.status === 'live_verified' && !fresh ? 'implemented_unverified' : gsm.status);
  const devices = Array.isArray(gsm?.devices) ? gsm.devices.map((device) => ({
    serial: device?.serial || '',
    model: device?.model || '',
    simState: device?.sim_state || device?.simState || '',
    batteryLevel: Number.isFinite(device?.battery_level) ? device.battery_level : null,
    abi: device?.abi || '',
    root: Boolean(device?.root),
    termux: Boolean(device?.termux),
  })) : [];
  return {
    status,
    fresh,
    alert,
    online: Number.isFinite(gsm?.online) ? gsm.online : 0,
    discovered: Number.isFinite(gsm?.discovered) ? gsm.discovered : devices.length,
    readOnly: gsm?.readOnly === true,
    simReady: devices.filter((device) => device.simState === 'READY').length,
    checkedAt: gsm?.checkedAt || gsm?.checked_at || null,
    expiresAt: gsm?.expiresAt || null,
    devices,
    workers: {
      status: workers?.status || 'needs_user_data',
      online: Number.isFinite(workers?.online) ? workers.online : 0,
      succeeded: Number.isFinite(workers?.succeeded) ? workers.succeeded : 0,
      errors: Array.isArray(workers?.errors) ? workers.errors.length : 0,
    },
    modelTrial: {
      status: trial?.status || 'needs_user_data',
      ready: Boolean(trial?.ready),
      reason: trial?.reason || '',
      binary: trial?.binary || null,
      model: trial?.model || null,
      maxModelMb: Number.isFinite(trial?.maxModelMb) ? trial.maxModelMb : 600,
      expiresAt: trial?.expiresAt || null,
    },
  };
}

/** Inventaire des projets importés : aucune commande n'est lancée. */
export async function readIntegrationCatalog(integrationsDir) {
  let entries = [];
  try {
    entries = await readdir(integrationsDir, { withFileTypes: true });
  } catch {
    return { count: 0, integrations: [] };
  }
  const integrations = [];
  for (const entry of entries) {
    if (!entry.isDirectory() || entry.name.startsWith('.')) continue;
    let names = [];
    try {
      names = await readdir(join(integrationsDir, entry.name));
    } catch {
      names = [];
    }
    const set = new Set(names);
    const stack = set.has('package.json') ? 'node'
      : (set.has('requirements.txt') || set.has('pyproject.toml') || set.has('setup.py')) ? 'python'
        : set.has('go.mod') ? 'go'
          : set.has('Cargo.toml') ? 'rust' : 'unknown';
    integrations.push({ name: entry.name, stack, status: 'present' });
  }
  integrations.sort((a, b) => a.name.localeCompare(b.name));
  return { count: integrations.length, integrations };
}

export async function readHomedockWidgets({ reportsDir, gsmStatusPath, kanbanPath }) {
  let files = [];
  try {
    files = await readdir(reportsDir);
  } catch {
    files = [];
  }
  const gsm = await readJson(gsmStatusPath);
  let text = '';
  try {
    text = await readFile(kanbanPath, 'utf8');
  } catch {
    text = '';
  }
  const board = parseBoard(text);
  return {
    reports: files.filter((name) => name.endsWith('.json')).length,
    gsm: {
      status: gsm?.status || 'needs_user_data',
      online: Number.isFinite(gsm?.online) ? gsm.online : 0,
    },
    kanban: Object.fromEntries(KANBAN_COLS.map((col) => [col, (board[col] || []).length])),
    checkedAt: gsm?.checkedAt || null,
  };
}
