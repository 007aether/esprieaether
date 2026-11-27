import test, { before, after } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import {
  KANBAN_COLS, parseBoard, readBoard, addBoardItem, moveBoardItem,
} from '../api/rest_services.mjs';
import { createDashboardServer } from '../api/server.mjs';

let dir;
let boardPath;
let server;
let base;

before(async () => {
  dir = await mkdtemp(join(tmpdir(), 'sunnavok-rest-'));
  boardPath = join(dir, 'Coordination', 'kanban.md');
  await mkdir(dirname(boardPath), { recursive: true });
  server = createDashboardServer({ kanbanPath: boardPath, log: () => {} });
  await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
  base = `http://127.0.0.1:${server.address().port}`;
});

after(async () => {
  if (server) await new Promise((resolve) => server.close(resolve));
  if (dir) await rm(dir, { recursive: true, force: true });
});

const SAMPLE = [
  '# 📋 Sunna Kanban',
  '',
  '## todo',
  '- [ ] 🔴 tâche A — Amine',
  '',
  '## doing',
  '- [ ] 🟢 tâche B',
  '',
  '## done',
  '- [x] ✅ tâche C',
  '',
].join('\n');

test('REST J1: parseBoard lit les trois colonnes et l’état done', () => {
  assert.deepEqual(KANBAN_COLS, ['todo', 'doing', 'done']);
  const board = parseBoard(SAMPLE);
  assert.deepEqual(Object.keys(board), KANBAN_COLS);
  assert.equal(board.todo.length, 1);
  assert.equal(board.todo[0].title, '🔴 tâche A — Amine');
  assert.equal(board.todo[0].done, false);
  assert.equal(board.done[0].done, true);
});

test('REST J1: readBoard crée un board initial quand le fichier manque', async () => {
  const fresh = join(dir, 'fresh', 'kanban.md');
  const board = await readBoard(fresh);
  assert.deepEqual(Object.keys(board), KANBAN_COLS);
  assert.ok(board.todo.length > 0);
});

test('REST J1: addBoardItem ajoute une carte et refuse une colonne inconnue', async () => {
  await writeFile(boardPath, SAMPLE, 'utf8');
  const board = await addBoardItem(boardPath, { title: 'nouvelle carte', col: 'todo' });
  assert.equal(board.todo.length, 2);
  assert.equal(board.todo[1].title, 'nouvelle carte');
  await assert.rejects(() => addBoardItem(boardPath, { title: 'x', col: 'inconnue' }),
    (error) => error.code === 'BAD_COLUMN');
  await assert.rejects(() => addBoardItem(boardPath, { title: '', col: 'todo' }),
    (error) => error.code === 'BAD_TITLE');
});

test('REST J1: moveBoardItem déplace et marque done', async () => {
  await writeFile(boardPath, SAMPLE, 'utf8');
  const board = await moveBoardItem(boardPath, { title: 'tâche A', to: 'done' });
  assert.equal(board.todo.length, 0);
  assert.equal(board.done.length, 2);
  assert.equal(board.done[1].title, '🔴 tâche A — Amine');
  assert.equal(board.done[1].done, true);
  await assert.rejects(() => moveBoardItem(boardPath, { title: 'absente', to: 'doing' }),
    (error) => error.code === 'NOT_FOUND');
});

test('REST J1: la passerelle :5100 sert le board et accepte les mutations', async () => {
  await writeFile(boardPath, SAMPLE, 'utf8');
  const read = await fetch(`${base}/api/rest/kanban/board`);
  assert.equal(read.status, 200);
  assert.equal((await read.json()).board.todo.length, 1);

  const headers = { origin: 'http://127.0.0.1:5100', 'content-type': 'application/json' };
  const added = await fetch(`${base}/api/rest/kanban/add`, {
    method: 'POST', headers, body: JSON.stringify({ title: 'via REST', col: 'todo' }),
  });
  assert.equal(added.status, 200);
  assert.equal((await added.json()).board.todo.length, 2);

  const moved = await fetch(`${base}/api/rest/kanban/move`, {
    method: 'POST', headers, body: JSON.stringify({ title: 'tâche A', to: 'done' }),
  });
  assert.equal(moved.status, 200);
  const board = (await moved.json()).board;
  assert.equal(board.todo.length, 1);
  assert.equal(board.todo[0].title, 'via REST');
  assert.equal(board.done.length, 2);

  const bad = await fetch(`${base}/api/rest/kanban/add`, {
    method: 'POST', headers, body: JSON.stringify({ title: 'x', col: 'nope' }),
  });
  assert.equal(bad.status, 400);
});
