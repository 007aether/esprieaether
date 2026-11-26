import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import vm from 'node:vm';

const ROOT = new URL('..', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const TEMPLATE = join(ROOT, 'esprieaether', 'src', 'templates', 'health.html');

const LIVE_SERVICES = {
  jarvis: 'active',
  jarvis_backend: 'active',
  jarvis_backend_provider: 'local-brain',
  jarvis_backend_status: 'active',
  ollama: 'active',
  ollama_reason: 'active',
  web: 'active',
};

async function renderHealth(services) {
  const html = await readFile(TEMPLATE, 'utf8');
  const script = /<script>([\s\S]*?)<\/script>/.exec(html);
  assert.ok(script, 'script de health.html introuvable');

  const elements = {};
  const document = {
    getElementById(id) {
      elements[id] ??= { textContent: '', innerHTML: '', style: {} };
      return elements[id];
    },
  };
  const fixture = {
    status: 'ok',
    services,
    guardian: {},
    alerts: {},
    autonomous: {},
    system: {},
  };
  const context = vm.createContext({
    document,
    fetch: async () => ({ json: async () => fixture }),
    setInterval: () => 0,
    Date,
  });
  vm.runInContext(script[1], context);
  await context.loadHealth();
  return elements;
}

test('J129: le nom du fournisseur local n’est pas une carte en panne', async () => {
  const el = await renderHealth(LIVE_SERVICES);
  const rows = el['services-list'].innerHTML;

  assert.doesNotMatch(rows, /🔴[^<]*jarvis_backend_provider/);
  assert.match(rows, /ℹ️[^<]*jarvis_backend_provider[^<]*<\/span><b>local-brain<\/b>/);
  for (const name of Object.keys(LIVE_SERVICES).filter(k => k !== 'jarvis_backend_provider')) {
    assert.match(rows, new RegExp(`🟢[^<]*${name}</span>`));
  }
});

test('J129: le fournisseur n’entre pas dans le compteur des services actifs', async () => {
  const el = await renderHealth(LIVE_SERVICES);
  assert.equal(el['services-active'].textContent, '6');
  assert.equal(el['services-total'].textContent, '6');
});

test('J129: un vrai service en panne reste rouge', async () => {
  const el = await renderHealth({ ...LIVE_SERVICES, jarvis_backend: 'down' });
  assert.match(el['services-list'].innerHTML, /🔴[^<]*jarvis_backend<\/span><b>down<\/b>/);
  assert.equal(el['services-active'].textContent, '5');
});
