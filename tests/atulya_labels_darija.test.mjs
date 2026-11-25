import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';

const ROOT = new URL('..', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const WEBUI = join(ROOT, 'GITHUB_IMPORT', 'Atulya-Tantra', 'webui');

test('J101: les libellés du panneau Atulya sont en darija', async () => {
  const html = await readFile(join(WEBUI, 'index.html'), 'utf8');
  for (const darija of ['جلسة مباشرة', '>نص<', '>صوت<', '>رؤية<', '>إيماءة<']) {
    assert.ok(html.includes(darija), `libellé darija manquant : ${darija}`);
  }
  for (const english of ['LIVE SESSION', '>TEXT<', '>VOICE<', '>VISION<', '>GESTURE<']) {
    assert.ok(!html.includes(english), `libellé anglais restant : ${english}`);
  }
});

test('J101: les phases et les erreurs passent par le traducteur darija', async () => {
  const source = await readFile(join(WEBUI, 'assistant.js'), 'utf8');
  assert.match(source, /const DARIJA_UI\s*=\s*Object\.freeze\(/);
  assert.match(source, /status\.textContent\s*=\s*darija\(label\)/);
  assert.match(source, /statusDetail\.textContent\s*=\s*darija\(detail\)/);
  assert.match(source, /waveHelp\.textContent\s*=\s*darija\(/);
  for (const darija of [
    'كيسمع', 'كيتفكّر', 'جاهز', 'كيتكلّم',
    'أتوليا ما قدرتش تكمل الجواب. حاول مرة اخرى.',
    'تكلّم كيف كتسول، وغادي نجاوبك إلا سكتّي.',
  ]) {
    assert.ok(source.includes(darija), `traduction darija manquante : ${darija}`);
  }
});
