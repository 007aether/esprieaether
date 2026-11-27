// passerelle REST locale — remplace les petits services Python à fichiers.
// Même format de board que esprieaether/src/veritas_kanban.py (markdown simple).
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { dirname } from 'node:path';

export const KANBAN_COLS = ['todo', 'doing', 'done'];

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
