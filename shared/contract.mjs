// SUNNAVOK — contrat unique DashboardState (GUI <-> API).
export const STATE_VERSION = 1;
export const CONDITIONS = ['—', 'جديدة', 'مزيانة', 'خاصها صيانة', 'معطلة'];
export const OWNERS = ['—', 'SEI', 'Four Amine', 'الوالد', 'كراء', 'آخر'];
export const FIELD_IDS = [
  'f-a', 'f-d1', 'f-gap', 'f-d2', 'f-b', 'f-notes',
  'g-rate', 'g-cons', 'g-over', 'g-margin',
];
export const INVENTORY_KEYS = ['name', 'qty', 'cond', 'owner', 'price'];

export function errorEnvelope(code, message, requestId) {
  return { code, message, requestId };
}

const isRecord = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);

/** Valide un état complet. Retourne null si valide, sinon un code d'erreur stable. */
export function validateState(state) {
  if (!isRecord(state)) return 'STATE_NOT_OBJECT';
  if (state.version !== STATE_VERSION) return 'VERSION_UNSUPPORTED';
  if (!isRecord(state.fields)) return 'FIELDS_INVALID';
  for (const id of FIELD_IDS) {
    if (id in state.fields && typeof state.fields[id] !== 'string') return 'FIELD_INVALID';
  }
  if (!Array.isArray(state.products)) return 'PRODUCTS_INVALID';
  for (const product of state.products) {
    if (!isRecord(product)) return 'PRODUCT_INVALID';
  }
  if (!Array.isArray(state.inventory)) return 'INVENTORY_INVALID';
  for (const item of state.inventory) {
    if (!isRecord(item)) return 'ITEM_INVALID';
    for (const key of INVENTORY_KEYS) {
      if (key in item && typeof item[key] !== 'string') return 'ITEM_FIELD_INVALID';
    }
    if ('cond' in item && !CONDITIONS.includes(item.cond)) return 'CONDITION_INVALID';
    if ('owner' in item && !OWNERS.includes(item.owner)) return 'OWNER_INVALID';
  }
  if (!isRecord(state.todo)) return 'TODO_INVALID';
  for (const value of Object.values(state.todo)) {
    if (typeof value !== 'boolean') return 'TODO_VALUE_INVALID';
  }
  return null;
}

/** Normalise un état valide en garantissant les clés attendues. */
export function normalizeState(state) {
  const fields = Object.fromEntries(FIELD_IDS.map((id) => [id, typeof state.fields[id] === 'string' ? state.fields[id] : '']));
  const products = state.products.map((product) => ({ ...product }));
  const inventory = state.inventory.map((item) =>
    Object.fromEntries(INVENTORY_KEYS.map((key) => [key, typeof item[key] === 'string' ? item[key] : ''])),
  );
  return { version: STATE_VERSION, fields, products, inventory, todo: { ...state.todo } };
}
