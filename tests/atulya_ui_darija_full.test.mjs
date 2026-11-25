import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';

const ROOT = new URL('..', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const VENDOR = join(ROOT, 'GITHUB_IMPORT', 'Atulya-Tantra');
const WEBUI = join(VENDOR, 'webui');
const OUT = join(ROOT, 'esprieaether', 'G0DM0D3', 'out');

const HUD_ENGLISH = [
  'SYSTEM', 'SERVICE', 'MODEL', 'CPU', 'CAMERA PREVIEW', 'CAMERA STARTING',
  'Scanning', 'Not configured', 'No upcoming meetings', 'Delivery unavailable',
  'Offline', 'Online', 'Close', 'Search', 'CONTINUE', 'CREATE ACCOUNT', 'SAVE',
  'DELETE', 'EXPORT', 'OPEN SELECTED', 'AGE & CONTENT', 'LOCAL USERS',
];

const SUPERVISION_LEGACY = [
  'SYSTEM SERVICES', 'CENTRO DE MANDO LOCAL', 'ESTADO DO SISTEMA',
  'INTERFACE VOCALE', 'ATENÇÃO NECESSÁRIA', 'ROBÔS / CEREBRO LOCAL',
  'REGISTRO DE EXECUÇÃO', 'CAPACIDADES · ESTADO REAL', 'AÇÕES · DECISÃO EXPLÍCITA',
  'SENTINEL · ATIVIDADE', 'RÉACTEUR', 'SERVICES', 'ROBOTS / CERVEAU',
  'REGISTRE', 'RÉSEAU', 'VOIX', 'MESURE CERVEAU LOCAL', 'WITHOUT CLOUD',
  'Visualisation', 'no execution control', 'a carregar', 'chargement',
];

test('J104: aucune des étiquettes visibles du HUD Atulya ne reste en anglais', async () => {
  const html = await readFile(join(WEBUI, 'index.html'), 'utf8');
  const visible = html
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/\s+/g, ' ');
  for (const label of HUD_ENGLISH) {
    assert.ok(!new RegExp(`\\b${label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i').test(visible),
      `étiquette anglaise visible : ${label}`);
  }
  for (const darija of ['النظام', 'الخدمة', 'النموذج', 'المعالج', 'معاينة الكاميرا', 'كيبحث على اليد']) {
    assert.ok(visible.includes(darija), `traduction darija manquante : ${darija}`);
  }
});

test('J104: les erreurs de flux sont en darija côté serveur', async () => {
  const server = await readFile(join(VENDOR, 'atulya', 'server.py'), 'utf8');
  assert.ok(server.includes('الجواب توقف فجأة. حاول مرة اخرى ولا صيّح الرسالة.'));
  assert.ok(server.includes('تدفق النموذج توقف فجأة.'));
  assert.ok(!server.includes('The reply stopped unexpectedly. Please retry or type a correction.'));
  assert.ok(!server.includes('The model stream ended unexpectedly.'));
});

test('J104: les états dynamiques passent par le traducteur', async () => {
  const source = await readFile(join(WEBUI, 'assistant.js'), 'utf8');
  for (const english of [
    'SERVICE UNREACHABLE', 'Cannot reach Atulya service', 'No active issues',
    'Camera access was denied. Allow it for this site in browser settings, then reload.',
    'MODEL ERROR', 'RETRY NEEDED', 'Frame recognition failed',
  ]) {
    assert.ok(source.includes(english), `texte source à traduire absent : ${english}`);
  }
  for (const darija of [
    'الخدمة غير قابلة للوصول',
    'ما قدرناش نتصلو بخدمة أتوليا',
    'ما كاينشي مشكل ناشط',
    'النموذج فيه خطأ',
    'كيتطلب إعادة المحاولة',
    'التعرف على الإطار فشل',
  ]) {
    assert.ok(source.includes(darija), `traduction darija manquante : ${darija}`);
  }
  assert.match(source, /function setSystemTile\([^)]*\)\s*\{[\s\S]*?darija\(label\)/);
  assert.match(source, /function showGestureResult\([^)]*\)\s*\{[\s\S]*?darija\(/);
});

test('J104: les pages de supervision locales sont aussi en darija', async () => {
  for (const name of ['jarvis.html', 'system.html']) {
    const html = await readFile(join(OUT, name), 'utf8');
    const visible = html
      .replace(/<script[\s\S]*?<\/script>/gi, ' ')
      .replace(/<style[\s\S]*?<\/style>/gi, ' ')
      .replace(/<!--[\s\S]*?-->/g, ' ')
      .replace(/<[^>]+>/g, ' ')
      .replace(/&amp;/g, '&')
      .replace(/\s+/g, ' ');
    for (const label of SUPERVISION_LEGACY) {
      assert.ok(!new RegExp(`\\b${label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'i').test(visible),
        `${name}: étiquette étrangère visible : ${label}`);
    }
    assert.match(html, /<html lang="ar-MA">/, `${name}: langue déclarée`);
    assert.match(html, /var DARIJA = \{[\s\S]*?"no_data_source"/, `${name}: dictionnaire de statuts`);
    assert.match(html, /function tr\(v\)/, `${name}: traducteur dynamique`);
  }
  const hud = await readFile(join(OUT, 'jarvis.html'), 'utf8');
  for (const darija of ['لوحة القيادة المحلية', 'حالة النظام', 'كيتحمل', 'الشبكة', 'الصوت', 'ما كاينش مصدر بيانات']) {
    assert.ok(hud.includes(darija), `jarvis.html: traduction darija manquante : ${darija}`);
  }
  const system = await readFile(join(OUT, 'system.html'), 'utf8');
  for (const darija of ['خدمات النظام', 'المفاعل', 'كيتحمل', 'الشبكة', 'الصوت', 'ما كاينش مصدر بيانات']) {
    assert.ok(system.includes(darija), `system.html: traduction darija manquante : ${darija}`);
  }
});
