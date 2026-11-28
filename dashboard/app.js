(() => {
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

  const bootstrap = (() => {
    const tag = document.getElementById('sunnavok-initial-state');
    if (!tag) return null;
    try {
      const parsed = JSON.parse(tag.textContent);
      return parsed && typeof parsed === 'object' ? parsed : null;
    } catch {
      return null;
    }
  })();

  const STORAGE_KEY = 'sunnavok-dashboard-state-v1';
  const PERSISTED_FIELD_IDS = [
    'f-a', 'f-d1', 'f-gap', 'f-d2', 'f-b', 'f-notes',
    'g-rate', 'g-cons', 'g-over', 'g-margin',
  ];

  function readDashboardState() {
    if (bootstrap && bootstrap.state && typeof bootstrap.state === 'object' && !Array.isArray(bootstrap.state)) {
      return { data: bootstrap.state, available: true, hasSavedData: true };
    }
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      const parsed = raw ? JSON.parse(raw) : {};
      return {
        data: parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed : {},
        available: true,
        hasSavedData: Boolean(raw),
      };
    } catch {
      return { data: {}, available: false, hasSavedData: false };
    }
  }

  const loadedState = readDashboardState();
  const savedState = loadedState.data;
  let storageAvailable = loadedState.available;

  function setSaveStatus(message, state = 'ok') {
    const status = $('#save-status');
    if (!status) return;
    status.textContent = message;
    status.dataset.state = state;
  }

  function restoreSavedFields() {
    const fields = savedState.fields;
    if (fields && typeof fields === 'object' && !Array.isArray(fields)) {
      PERSISTED_FIELD_IDS.forEach((id) => {
        const input = $(`#${id}`);
        if (input && Object.prototype.hasOwnProperty.call(fields, id) && typeof fields[id] === 'string') {
          input.value = fields[id];
        }
      });
    }

    const todo = savedState.todo;
    if (todo && typeof todo === 'object' && !Array.isArray(todo)) {
      $$('#panel-todo input[type="checkbox"]').forEach((checkbox) => {
        if (typeof todo[checkbox.id] === 'boolean') checkbox.checked = todo[checkbox.id];
      });
    }
  }

  restoreSavedFields();
  if (!storageAvailable) {
    setSaveStatus('الحفظ التلقائي غير متاح فهاد المتصفح؛ استعمل «جمع ونسخ» للاحتفاظ بنسخة.', 'error');
  } else if (bootstrap && bootstrap.state) {
    setSaveStatus('رجّعنا المعطيات المحفوظة على الخادم.', 'ok');
  } else if (loadedState.hasSavedData) {
    setSaveStatus('رجّعنا المعطيات المحفوظة فهاد المتصفح.', 'ok');
  } else {
    setSaveStatus('التعديلات كتتحفظ تلقائياً فهاد المتصفح.', 'ok');
  }

  const num = (value) => {
    const parsed = parseFloat(String(value ?? '').replace(',', '.'));
    return Number.isFinite(parsed) ? parsed : 0;
  };
  const fmt = (value) => value.toLocaleString('fr-FR', { maximumFractionDigits: 2 });
  const money = (value) => `${fmt(value)} درهم`;
  const esc = (value) =>
    String(value ?? '').replace(
      /[&<>"']/g,
      (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char],
    );

  /* ---------- Tabs ---------- */
  const tabs = $$('[role="tab"]');
  const panels = $$('[role="tabpanel"]');

  function selectTab(id, moveFocus = false) {
    tabs.forEach((tab) => {
      const active = tab.dataset.tab === id;
      tab.setAttribute('aria-selected', String(active));
      tab.tabIndex = active ? 0 : -1;
      if (active) {
        tab.scrollIntoView({ block: 'nearest', inline: 'nearest' });
        if (moveFocus) tab.focus();
      }
    });
    panels.forEach((panel) => {
      panel.hidden = panel.id !== `panel-${id}`;
    });
  }

  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => selectTab(tab.dataset.tab));
    tab.addEventListener('keydown', (event) => {
      // The tab list is right-to-left, so the left arrow moves forward.
      const step = event.key === 'ArrowLeft' ? 1 : event.key === 'ArrowRight' ? -1 : 0;
      if (!step) return;
      event.preventDefault();
      const next = tabs[(index + step + tabs.length) % tabs.length];
      selectTab(next.dataset.tab, true);
    });
  });

  document.addEventListener('click', (event) => {
    const link = event.target.closest('[data-goto]');
    if (!link) return;
    selectTab(link.dataset.goto);
    window.scrollTo({ top: 0 });
  });

  /* ---------- Workshop plan and facade ---------- */
  const FACADE_WIDTH = 6;
  const FACADE_FIELDS = ['a', 'd1', 'gap', 'd2', 'b'];
  const FACADE_LABELS = {
    a: 'من الزاوية اليسرى حتى الباب 1',
    d1: 'عرض الباب 1',
    gap: 'المسافة بين البابين',
    d2: 'عرض الباب 2',
    b: 'من الباب 2 حتى الزاوية اليمنى',
  };

  function renderPlan(facade) {
    const scale = 50;
    const left = 16;
    const top = 20;
    const width = FACADE_WIDTH * scale;
    const height = 12 * scale;
    const aisle = 0.9 * scale;
    const side = (width - aisle) / 2;
    const back = 3 * scale;
    const front = 2.4 * scale;
    const midY = top + back;
    const midH = height - back - front;
    const frontY = top + height - front;
    const aisleX = left + side;
    const bottom = top + height;

    const label = (x, y, lines, cls = 'z-label') =>
      `<text x="${x}" y="${y}" text-anchor="middle" class="${cls}">${lines
        .map((line, i) => `<tspan x="${x}" dy="${i ? 19 : 0}">${line}</tspan>`)
        .join('')}</text>`;

    let svg = '';
    svg += `<rect x="${left}" y="${top}" width="${width}" height="${back}" class="z z-weld"/>`;
    svg += label(left + width / 2, top + back / 2 - 6, ['اللحام TIG/MIG والتجميع', 'الخلف']);

    svg += `<rect x="${left}" y="${midY}" width="${side}" height="${midH}" class="z z-steel"/>`;
    svg += label(left + side / 2, midY + midH / 2 - 6, ['تخزين الحديد', 'والأنابيب']);

    svg += `<rect x="${aisleX + aisle}" y="${midY}" width="${side}" height="${midH}" class="z z-machine"/>`;
    svg += label(aisleX + aisle + side / 2, midY + midH / 2 - 16, ['الحفر', 'القطع', 'الجلخ']);

    svg += `<rect x="${left}" y="${frontY}" width="${width}" height="${front}" class="z z-front"/>`;
    svg += label(left + side / 2, frontY + front / 2 + 5, ['استقبال']);
    svg += label(aisleX + aisle + side / 2, frontY + front / 2 + 5, ['استقبال']);

    svg += `<rect x="${aisleX}" y="${midY}" width="${aisle}" height="${height - back}" class="z-aisle"/>`;
    svg += `<text transform="translate(${aisleX + aisle / 2 + 4} ${midY + (height - back) / 2}) rotate(-90)" text-anchor="middle" class="z-label small">ممر 0.9 م</text>`;

    svg += `<path d="M${left},${bottom} L${left},${top} L${left + width},${top} L${left + width},${bottom}" class="wall"/>`;

    if (facade) {
      const [a, d1, gap, d2] = facade;
      const points = [0, a, a + d1, a + d1 + gap, a + d1 + gap + d2, FACADE_WIDTH].map(
        (meters) => left + meters * scale,
      );
      const wall = (x1, x2) =>
        x2 - x1 > 0.5 ? `<line x1="${x1}" y1="${bottom}" x2="${x2}" y2="${bottom}" class="wall"/>` : '';
      const door = (x1, x2, text) =>
        `<line x1="${x1}" y1="${bottom}" x2="${x2}" y2="${bottom}" class="door"/>` +
        `<text x="${(x1 + x2) / 2}" y="${bottom + 18}" text-anchor="middle" class="door-label">${text}</text>`;
      svg += wall(points[0], points[1]) + wall(points[2], points[3]) + wall(points[4], points[5]);
      svg += door(points[1], points[2], 'باب 1') + door(points[3], points[4], 'باب 2');
    } else {
      svg += `<line x1="${left}" y1="${bottom}" x2="${left + width}" y2="${bottom}" class="wall unknown"/>`;
      svg += `<text x="${left + width / 2}" y="${bottom + 18}" text-anchor="middle" class="door-label">جوج بيبان — القياسات باقية</text>`;
    }

    svg += `<text x="${left + width / 2}" y="${bottom + 40}" text-anchor="middle" class="dim">6 م — الواجهة والمدخل</text>`;
    svg += `<text transform="translate(${left + width + 24} ${top + height / 2}) rotate(90)" text-anchor="middle" class="dim">12 م</text>`;

    $('#plan').innerHTML =
      `<svg viewBox="0 0 ${left + width + 40} ${bottom + 52}" role="img" aria-labelledby="plan-title">` +
      `<title id="plan-title">مخطط علوي تقريبي للورشة 12 × 6 م: اللحام والتجميع فالخلف، تخزين الحديد فاليسار، ممر وسطي 0.9 م، الحفر والقطع والجلخ فاليمين، والاستقبال قدّام.</title>${svg}</svg>`;
  }

  function updateFacade() {
    const raw = FACADE_FIELDS.map((key) => $(`#f-${key}`).value.trim());
    const filled = raw.every((value) => value !== '');
    const values = raw.map(num);
    const sum = values.reduce((total, value) => total + value, 0);
    const status = $('#facade-status');
    const matches = Math.abs(sum - FACADE_WIDTH) < 0.011;

    status.className = 'status';
    if (raw.every((value) => value === '')) {
      status.textContent = 'عمّر القياسات الخمسة بالمتر. المجموع خاصو يساوي 6.00 م.';
    } else if (!filled) {
      status.textContent = `المجموع حتى الآن: ${fmt(sum)} م من 6 م — كمّل باقي الخانات.`;
    } else if (matches) {
      status.textContent = 'المجموع 6 م — القياسات متطابقة، والبابين ترسمو فالمخطط.';
      status.classList.add('ok');
    } else {
      const diff = sum - FACADE_WIDTH;
      status.textContent = `المجموع ${fmt(sum)} م — ${diff > 0 ? 'زايد' : 'ناقص'} ${fmt(Math.abs(diff))} م على 6 م. راجع القياس.`;
      status.classList.add('bad');
    }
    renderPlan(filled && matches ? values : null);
  }

  FACADE_FIELDS.forEach((key) =>
    $(`#f-${key}`).addEventListener('input', () => {
      updateFacade();
      saveDashboardState();
    }),
  );
  $('#f-notes').addEventListener('input', saveDashboardState);

  /* ---------- Costing ---------- */
  const PRODUCT_FIELDS = [
    ['qty', 'العدد', 'وحدة'],
    ['tole', 'الصاج (Tôle)', 'درهم'],
    ['hdid', 'الحديد', 'درهم'],
    ['pieces', 'القطع (Pièces)', 'درهم'],
    ['pliage', 'الطيّ (Pliage)', 'درهم'],
    ['hours', 'ساعات الخدمة', 'ساعة'],
    ['transport', 'النقل', 'درهم'],
  ];
  const GLOBAL_FIELDS = ['rate', 'cons', 'over', 'margin'];

  const blankProduct = (name, qty) => ({
    name,
    qty,
    tole: '',
    hdid: '',
    pieces: '',
    pliage: '',
    hours: '',
    transport: '',
  });

  const defaultProducts = [
    blankProduct('فرن 1.50 م', '4'),
    blankProduct('عربة الخبز', '4'),
    blankProduct('طابلة الخبز', '1'),
    blankProduct('معلف البهائم', ''),
    blankProduct('مشرب البهائم', ''),
  ];
  const productKeys = ['name', 'qty', 'tole', 'hdid', 'pieces', 'pliage', 'hours', 'transport'];
  const storedProducts = Array.isArray(savedState.products) ? savedState.products : defaultProducts;
  const products = storedProducts
    .filter((product) => product && typeof product === 'object' && !Array.isArray(product))
    .map((product, index) => {
      const fallback = defaultProducts[index] || blankProduct('منتوج جديد', '1');
      return Object.fromEntries(
        productKeys.map((key) => [key, product[key] == null ? fallback[key] : String(product[key])]),
      );
    });

  const globals = () => Object.fromEntries(GLOBAL_FIELDS.map((key) => [key, num($(`#g-${key}`).value)]));

  function compute(product, g) {
    const materials = num(product.tole) + num(product.hdid) + num(product.pieces);
    const direct =
      materials +
      num(product.pliage) +
      (materials * g.cons) / 100 +
      num(product.hours) * g.rate +
      num(product.transport);
    const cost = direct * (1 + g.over / 100);
    const price = cost * (1 + g.margin / 100);
    const qty = num(product.qty);
    return { cost, price, qty, batchCost: cost * qty, batchPrice: price * qty };
  }

  function renderProducts() {
    $('#products').innerHTML = products
      .map(
        (product, i) => `
      <article class="card" data-index="${i}">
        <div class="row-between">
          <label class="sr-only" for="p-${i}-name">اسم المنتوج</label>
          <input class="name-input" id="p-${i}-name" data-key="name" value="${esc(product.name)}">
          <button type="button" class="btn ghost small" data-remove="${i}">حذف</button>
        </div>
        <div class="fields">
          ${PRODUCT_FIELDS.map(
            ([key, text, unit]) => `
          <div class="field">
            <label for="p-${i}-${key}">${text} <span class="muted">(${unit})</span></label>
            <input id="p-${i}-${key}" data-key="${key}" type="number" min="0" step="any" inputmode="decimal" value="${esc(product[key])}">
          </div>`,
          ).join('')}
        </div>
        <dl class="results">
          <div><dt>تكلفة الوحدة</dt><dd id="o-${i}-cost"></dd></div>
          <div class="price"><dt>ثمن البيع للوحدة</dt><dd id="o-${i}-price"></dd></div>
          <div><dt>تكلفة الدفعة</dt><dd id="o-${i}-bcost"></dd></div>
          <div><dt>مبيعات الدفعة</dt><dd id="o-${i}-bprice"></dd></div>
        </dl>
      </article>`,
      )
      .join('');
    recalc();
  }

  function recalc() {
    const g = globals();
    let totalCost = 0;
    let totalSales = 0;
    products.forEach((product, i) => {
      const result = compute(product, g);
      totalCost += result.batchCost;
      totalSales += result.batchPrice;
      $(`#o-${i}-cost`).textContent = money(result.cost);
      $(`#o-${i}-price`).textContent = money(result.price);
      $(`#o-${i}-bcost`).textContent = money(result.batchCost);
      $(`#o-${i}-bprice`).textContent = money(result.batchPrice);
    });
    $('#t-cost').textContent = money(totalCost);
    $('#t-sales').textContent = money(totalSales);
    $('#t-profit').textContent = money(totalSales - totalCost);
  }

  $('#products').addEventListener('input', (event) => {
    const card = event.target.closest('[data-index]');
    const key = event.target.dataset.key;
    if (!card || !key) return;
    products[Number(card.dataset.index)][key] = event.target.value;
    recalc();
    saveDashboardState();
  });

  $('#products').addEventListener('click', (event) => {
    const button = event.target.closest('[data-remove]');
    if (!button) return;
    products.splice(Number(button.dataset.remove), 1);
    renderProducts();
    saveDashboardState();
  });

  $('#add-product').addEventListener('click', () => {
    products.push(blankProduct('منتوج جديد', '1'));
    renderProducts();
    saveDashboardState();
    $(`#p-${products.length - 1}-name`).focus();
  });

  GLOBAL_FIELDS.forEach((key) =>
    $(`#g-${key}`).addEventListener('input', () => {
      recalc();
      saveDashboardState();
    }),
  );

  /* ---------- Inventory ---------- */
  const CONDITIONS = bootstrap?.enums?.conditions ?? ['—', 'جديدة', 'مزيانة', 'خاصها صيانة', 'معطلة'];
  const OWNERS = bootstrap?.enums?.owners ?? ['—', 'SEI', 'Four Amine', 'الوالد', 'كراء', 'آخر'];

  const blankItem = (name = '') => ({ name, qty: '', cond: '—', owner: '—', price: '' });

  const defaultInventory = [
    blankItem('آلة الحفر'),
    blankItem('آلة القطع'),
    blankItem('معدات الجلخ'),
    blankItem('بوسط اللحام TIG/MIG'),
  ];
  const inventoryKeys = ['name', 'qty', 'cond', 'owner', 'price'];
  const storedInventory = Array.isArray(savedState.inventory) ? savedState.inventory : defaultInventory;
  const inventory = storedInventory
    .filter((item) => item && typeof item === 'object' && !Array.isArray(item))
    .map((item, index) => {
      const fallback = defaultInventory[index] || blankItem();
      const condition = CONDITIONS.includes(String(item.cond)) ? String(item.cond) : fallback.cond;
      const owner = OWNERS.includes(String(item.owner)) ? String(item.owner) : fallback.owner;
      return Object.fromEntries(
        inventoryKeys.map((key) => {
          if (key === 'cond') return [key, condition];
          if (key === 'owner') return [key, owner];
          return [key, item[key] == null ? fallback[key] : String(item[key])];
        }),
      );
    });

  function collectState() {
    const fields = Object.fromEntries(PERSISTED_FIELD_IDS.map((id) => [id, $(`#${id}`).value]));
    const todo = Object.fromEntries(
      $$('#panel-todo input[type="checkbox"]').map((checkbox) => [checkbox.id, checkbox.checked]),
    );
    return { version: 1, fields, products, inventory, todo };
  }

  function saveDashboardState() {
    const state = collectState();

    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
      storageAvailable = true;
      setSaveStatus('تم حفظ التعديلات تلقائياً فهاد المتصفح.', 'ok');
    } catch {
      storageAvailable = false;
      setSaveStatus('تعذر الحفظ التلقائي؛ استعمل «جمع ونسخ» للاحتفاظ بنسخة.', 'error');
    }

    if (!bootstrap) return;
    fetch('/api/dashboard/state', {
      method: 'PUT',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(state),
    })
      .then((response) => {
        if (!response.ok) throw new Error('save rejected');
        setSaveStatus('تم حفظ التعديلات تلقائياً على الخادم.', 'ok');
      })
      .catch(() => {
        setSaveStatus('تعذر الحفظ على الخادم؛ النسخة محفوظة فهاد المتصفح.', 'error');
      });
  }

  const options = (list, selected) =>
    list.map((item) => `<option${item === selected ? ' selected' : ''}>${esc(item)}</option>`).join('');

  function renderInventory() {
    $('#inventory').innerHTML = inventory
      .map(
        (item, i) => `
      <article class="card" data-index="${i}">
        <div class="row-between">
          <label class="sr-only" for="i-${i}-name">اسم الآلة أو المعدة</label>
          <input class="name-input" id="i-${i}-name" data-key="name" placeholder="اسم الآلة أو المعدة" value="${esc(item.name)}">
          <button type="button" class="btn ghost small" data-remove="${i}">حذف</button>
        </div>
        <div class="fields">
          <div class="field">
            <label for="i-${i}-qty">العدد</label>
            <input id="i-${i}-qty" data-key="qty" type="number" min="0" step="1" inputmode="numeric" value="${esc(item.qty)}">
          </div>
          <div class="field">
            <label for="i-${i}-cond">الحالة</label>
            <select id="i-${i}-cond" data-key="cond">${options(CONDITIONS, item.cond)}</select>
          </div>
          <div class="field">
            <label for="i-${i}-owner">الملكية</label>
            <select id="i-${i}-owner" data-key="owner">${options(OWNERS, item.owner)}</select>
          </div>
          <div class="field">
            <label for="i-${i}-price">ثمن الشراء للوحدة <span class="muted">(درهم)</span></label>
            <input id="i-${i}-price" data-key="price" type="number" min="0" step="any" inputmode="decimal" value="${esc(item.price)}">
          </div>
        </div>
      </article>`,
      )
      .join('');
    updateInventoryTotals();
  }

  function updateInventoryTotals() {
    const named = inventory.filter((item) => item.name.trim() !== '');
    const units = named.reduce((total, item) => total + num(item.qty), 0);
    const value = named.reduce((total, item) => total + num(item.qty) * num(item.price), 0);
    $('#inv-lines').textContent = String(named.length);
    $('#inv-units').textContent = fmt(units);
    $('#inv-value').textContent = money(value);
  }

  const onInventoryChange = (event) => {
    const card = event.target.closest('[data-index]');
    const key = event.target.dataset.key;
    if (!card || !key) return;
    inventory[Number(card.dataset.index)][key] = event.target.value;
    updateInventoryTotals();
    saveDashboardState();
  };
  $('#inventory').addEventListener('input', onInventoryChange);
  $('#inventory').addEventListener('change', onInventoryChange);

  $('#inventory').addEventListener('click', (event) => {
    const button = event.target.closest('[data-remove]');
    if (!button) return;
    inventory.splice(Number(button.dataset.remove), 1);
    renderInventory();
    saveDashboardState();
  });

  $('#add-item').addEventListener('click', () => {
    inventory.push(blankItem());
    renderInventory();
    saveDashboardState();
    $(`#i-${inventory.length - 1}-name`).focus();
  });

  $$('#panel-todo input[type="checkbox"]').forEach((checkbox) =>
    checkbox.addEventListener('change', saveDashboardState),
  );

  /* ---------- Export ---------- */
  function buildExport() {
    const lines = ['SUNNAVOK — معطيات من لوحة المشروع', ''];

    lines.push('## واجهة الورشة 6 م (بالمتر)');
    FACADE_FIELDS.forEach((key) => {
      const value = $(`#f-${key}`).value.trim();
      lines.push(`- ${FACADE_LABELS[key]}: ${value === '' ? 'باقي' : value}`);
    });
    const extra = $('#f-notes').value.trim();
    if (extra) lines.push(`- ملاحظات (نوافذ، أعمدة، ماكينات): ${extra}`);

    const g = globals();
    lines.push('', '## التكلفة');
    lines.push(
      `- ثمن ساعة الخدمة: ${fmt(g.rate)} درهم | المستهلكات: ${fmt(g.cons)}% | المصاريف العامة: ${fmt(g.over)}% | هامش الربح: ${fmt(g.margin)}%`,
    );
    products.forEach((product) => {
      const result = compute(product, g);
      const show = (key) => (String(product[key]).trim() === '' ? 'باقي' : product[key]);
      lines.push(
        `- ${product.name} × ${show('qty')}: صاج ${show('tole')}، حديد ${show('hdid')}، قطع ${show('pieces')}، طيّ ${show('pliage')}، ساعات ${show('hours')}، نقل ${show('transport')} → تكلفة الوحدة ${fmt(result.cost)} درهم، ثمن البيع ${fmt(result.price)} درهم`,
      );
    });

    lines.push('', '## جرد الآلات والمعدات');
    const named = inventory.filter((item) => item.name.trim() !== '');
    if (!named.length) lines.push('- باقي');
    named.forEach((item) => {
      lines.push(
        `- ${item.name}: العدد ${item.qty === '' ? 'باقي' : item.qty}، الحالة ${item.cond}، الملكية ${item.owner}، ثمن الشراء ${item.price === '' ? 'باقي' : `${item.price} درهم`}`,
      );
    });

    const done = $$('#panel-todo input[type="checkbox"]:checked').map((box) => box.dataset.title);
    if (done.length) {
      lines.push('', '## مهام تسالات');
      done.forEach((title) => lines.push(`- ${title}`));
    }
    return lines.join('\n');
  }

  $('#export-btn').addEventListener('click', async () => {
    const output = $('#export-out');
    const status = $('#export-status');
    output.value = buildExport();
    output.focus();
    output.select();
    try {
      await navigator.clipboard.writeText(output.value);
      status.textContent = 'تنسخ النص. لصقو فالشات باش نكملو الحساب.';
    } catch {
      status.textContent = 'النص واجد ومحدد. انسخو يدوياً ولصقو فالشات.';
    }
  });

  /* ---------- État système et rapports ---------- */
  function renderHomeBatch() {
    const named = products.filter((product) => product.name.trim() !== '');
    const oven = named.find((product) => /فرن/.test(product.name)) || named[0];
    $('#home-batch').textContent = oven
      ? `${oven.qty === '' ? '—' : oven.qty} × ${oven.name}`
      : 'ما كاينش منتوج مسجل';
    $('#home-products').textContent = named.length
      ? named.map((product) => `${product.name} × ${product.qty === '' ? '—' : product.qty}`).join(' · ')
      : 'ما كاينش منتوجات';
  }

  async function refreshSystemStatus() {
    const box = $('#system-status');
    if (!box) return;
    try {
      const response = await fetch('/api/system/status');
      if (!response.ok) throw new Error('status unavailable');
      const status = await response.json();
      const rows = [
        ['الحرّاس', status.robots?.sentinel?.summary || '—'],
        [
          'الجودة',
          status.available
            ? `Python ${status.robots.quality.pythonRan ?? '—'} · Dashboard ${status.robots.quality.dashboardPassed ?? '—'} · .env ${status.robots.quality.envHashMatches ? 'ok' : '?'}`
            : 'التقارير غير متاحة',
        ],
        [
          'العقول المحلية',
          status.brains?.count
            ? `${status.brains.count} متاح · النشط ${status.brains.active || '—'} · ${status.brains.routedVia || '—'}`
            : 'غير متاحة',
        ],
        [
          'الجراف',
          status.graph?.nodes != null ? `${status.graph.nodes} عقدة / ${status.graph.edges} رابط` : '—',
        ],
        [
          'مصادر ناقصة',
          (status.robots?.backlog?.missingSources || []).join(', ') || 'none',
        ],
      ];
      box.innerHTML = rows.map(([key, value]) => `<dt>${esc(key)}</dt><dd>${esc(value)}</dd>`).join('');
      $('#system-status-time').textContent = status.checkedAt
        ? `آخر قراءة: ${status.checkedAt}`
        : '';
    } catch {
      box.innerHTML = '<dt>الحالة</dt><dd>تعذرت القراءة من الخادم</dd>';
      $('#system-status-time').textContent = '';
    }
  }

  async function refreshGsmStatus() {
    const box = $('#gsm-status');
    if (!box) return;
    try {
      const response = await fetch('/api/rest/gsm/status', { cache: 'no-store' });
      if (!response.ok) throw new Error('gsm unavailable');
      const gsm = await response.json();
      const rows = [
        ['الحالة', gsm.status],
        ['الأجهزة', `${gsm.online ?? 0} متصل / ${gsm.discovered ?? 0} مكتشف`],
        ['SIM جاهزة', String(gsm.simReady ?? 0)],
        ['القراءة فقط', gsm.readOnly ? 'نعم' : 'لا'],
        ['الموديل الصغير', gsm.modelTrial?.status || '—'],
      ];
      box.innerHTML = rows.map(([key, value]) => `<dt>${esc(key)}</dt><dd>${esc(value)}</dd>`).join('');
      const alert = $('#gsm-alert');
      if (alert) {
        alert.textContent = gsm.alert === 'expired' ? 'الدليل قديم: كيحتاج فحص قراءة فقط جديد.'
          : gsm.alert === 'no_evidence' ? 'ما كاينش دليل GSM محلي.' : '';
      }
    } catch {
      box.innerHTML = '<dt>الحالة</dt><dd>تعذرت القراءة من الخادم</dd>';
    }
  }

  async function refreshGsmCompute() {
    const box = $('#gsm-compute');
    if (!box) return;
    try {
      const response = await fetch('/api/rest/gsm/compute', { cache: 'no-store' });
      if (!response.ok) throw new Error('compute unavailable');
      const c = await response.json();
      const fleet = c.fleet || {};
      const rows = [
        ['قدرة الحوسبة', c.status || '—'],
        ['عمال أحياء', `${fleet.liveWorkers ?? 0} / الهدف ${fleet.targetDevices ?? 20}`],
        ['SIM جاهزة', String(fleet.simReady ?? 0)],
        ['إنترنت مُبلَّغ', String(fleet.internetReported ?? 0)],
        ['زيادة RAM', c.capabilities?.ramExtensionPossible ? 'نعم' : 'لا — التلفون ما كيزيدش RAM'],
      ];
      box.innerHTML = rows.map(([key, value]) => `<dt>${esc(key)}</dt><dd>${esc(value)}</dd>`).join('');
    } catch {
      box.innerHTML = '<dt>قدرة الحوسبة</dt><dd>ما كاينش دليل محلي</dd>';
    }
  }

  async function refreshAgentAudit() {
    const box = $('#agent-audit-feed');
    if (!box) return;
    try {
      const response = await fetch('/api/agent/audit');
      if (!response.ok) throw new Error('audit unavailable');
      const digest = await response.json();
      if (!digest.available || !digest.items.length) {
        box.replaceChildren();
        const empty = document.createElement('li');
        empty.textContent = 'سجل التدقيق غير متاح (لا مصدر محلي).';
        box.append(empty);
        return;
      }
      box.replaceChildren(...digest.items.map((item) => {
        const li = document.createElement('li');
        const id = document.createElement('b');
        id.textContent = item.id;
        const detail = document.createElement('span');
        detail.textContent = ` — ${item.detail}`;
        li.append(id, detail);
        return li;
      }));
    } catch {
      box.replaceChildren();
      const error = document.createElement('li');
      error.textContent = 'تعذرت قراءة سجل التدقيق.';
      box.append(error);
    }
  }

  async function showCopied(text) {
    const output = $('#export-out');
    output.value = text;
    output.focus();
    output.select();
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      return false;
    }
  }

  $('#status-refresh')?.addEventListener('click', refreshSystemStatus);
  $('#gsm-refresh')?.addEventListener('click', () => {
    refreshGsmStatus();
    refreshGsmCompute();
  });
  $('#audit-refresh')?.addEventListener('click', refreshAgentAudit);
  $('#report-btn')?.addEventListener('click', async () => {
    const status = $('#export-status');
    try {
      const response = await fetch('/api/report');
      if (!response.ok) throw new Error('report unavailable');
      const copied = await showCopied(await response.text());
      status.textContent = copied
        ? 'التقرير التنفيذي تنسخ. لصقو فالشات ولا حفظو فملف.'
        : 'التقرير واجد ومحدد؛ انسخو يدوياً.';
    } catch {
      status.textContent = 'تعذر جلب التقرير التنفيذي.';
    }
  });
  $('#json-export-btn')?.addEventListener('click', async () => {
    const text = JSON.stringify(collectState(), null, 2);
    const copied = await showCopied(text);
    $('#export-status').textContent = copied
      ? 'نسخة JSON مكتملة ومنسوخة. احفظوها فبلاصة آمنة.'
      : 'نسخة JSON مكتملة ومحددة؛ انسخوها يدوياً.';
  });
  $('#json-import-input')?.addEventListener('change', (event) => {
    const file = event.target.files && event.target.files[0];
    if (!file) return;
    const status = $('#export-status');
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        const payload = JSON.parse(String(reader.result || ''));
        const response = await fetch('/api/dashboard/state', {
          method: 'PUT',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!response.ok) {
          const error = await response.json().catch(() => ({}));
          throw new Error(error.code || 'rejected');
        }
        status.textContent = 'تم استيراد النسخة؛ كنعيد التحميل…';
        window.location.reload();
      } catch (error) {
        status.textContent = `الملف غير صالح أو الخادم رفضو (${error.message}).`;
      }
    };
    reader.onerror = () => {
      status.textContent = 'تعذرت قراءة الملف.';
    };
    reader.readAsText(file);
  });

  /* ---------- Init ---------- */
  if (bootstrap && !bootstrap.state && loadedState.hasSavedData) saveDashboardState();
  renderProducts();
  renderInventory();
  renderHomeBatch();
  updateFacade();
  refreshSystemStatus();
  refreshGsmStatus();
  refreshGsmCompute();
  refreshAgentAudit();
})();
