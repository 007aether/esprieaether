(() => {
  const $ = (selector) => document.querySelector(selector);
  const dialog = $("#control-dialog"), content = $("#control-content");
  const camera = $("#quick-camera");
  const shown = new Set();
  let polling = false;
  const node = (tag, text, className) => {
    const item = document.createElement(tag);
    if (text !== undefined) item.textContent = text;
    if (className) item.className = className;
    return item;
  };
  const when = (value) => new Date(value).toLocaleString();
  const STATUS_DARIJA = Object.freeze({
    "implemented_unverified": "مطبّق غير متحقق",
    "live_verified": "مُتحقق مباشرة",
    "needs_user_data": "كيتطلب بيانات المستخدم",
    "not_available": "غير متاح",
    "setup required": "كيتطلب الإعداد",
    "waiting for approval": "كيتستنى الموافقة",
    "No execution receipt": "ما كاين إيصال تنفيذ",
    "not connected": "غير متصل",
    "unconfirmed": "غير متحقق",
    "executed": "تنفّذ",
    "cancelled": "ملغى",
    "granted": "ممنوح",
    "denied": "مرفوض",
    "offline": "غير متصل",
    "online": "متصل",
    "queued": "مصفوف",
    "running": "كيدير",
    "failed": "فشل",
    "ready": "جاهز",
    "active": "ناشط",
    "live": "مباشر",
    "setup": "إعداد",
    "alert sent": "تم إرسال تنبيه",
    "admin": "مدير",
    "user": "مستعمل",
    "phone": "جوال",
    "laptop": "كمبيوتر محمول",
    "rain": "مطر",
    "off": "موقوف",
  });
  const DARIJA_PATTERNS = [
    [/^Saved reminder #(\d+) for (.+)\.$/, (m) => `تذكير #${m[1]} محفوظ لـ ${m[2]}.`],
    [/^Save changes to #(\d+)$/, (m) => `احفظ التبديلات على #${m[1]}`],
    [/^Shown in page (.+)$/, (m) => `ظهر فالصفحة ${m[1]}`],
    [/^Access: (.+)$/, (m) => `الصلاحية: ${m[1]}`],
    [/^Exported tools depend on enabled plugins: (.+)$/, (m) => `الأدوات المُصدّرة كتعتمد على الإضافات المفعّلة: ${m[1]}`],
    [/^Jobs \((\d+)\)$/, (m) => `المهام (${m[1]})`],
    [/^Total Spending: (.+)$/, (m) => `مجموع المصاريف: ${m[1]}`],
    [/^(\d+) recorded transactions$/, (m) => `${m[1]} معاملات مسجّلة`],
    [/^rain (\S+)%$/, (m) => `مطر ${m[1]}%`],
    [/^Next: (.+)$/, (m) => `الخطوة الجاية: ${m[1]}`],
    [/^Updated (.+)$/, (m) => `آخر تحديث ${m[1]}`],
    [/^Worker: (.+)\. (.+)$/, (m) => `العامل: ${m[1]}. ${m[2]}`],
    [/^(\d+) checks$/, (m) => `${m[1]} فحوصات`],
    [/^Granted scopes: (.+)$/, (m) => `النطاقات الممنوحة: ${m[1]}`],
    [/^Connected: (.+)$/, (m) => `متصل: ${m[1]}`],
    [/^Cancelled (\d+) app reminders and (\d+) Telegram reminders; paused (\d+) recurring reminders\. (.+)$/,
      (m) => `ألغيت ${m[1]} تذكيرات فالتطبيق و${m[2]} تذكيرات تيليجرام؛ أوقفت ${m[3]} تذكيرات متكررة. ${m[4]}`],
  ];
  const DASH_KEYS = Object.freeze({
    service: "الخدمة", model: "النموذج", cpu: "المعالج", memory: "الذاكرة",
    network: "الشبكة", host: "الجهاز", voice: "الصوت", speech: "النطق",
    vision: "الرؤية", gesture: "الإيماءة", telegram: "تيليجرام", issue: "مشكل",
  });
  function darija(value) {
    const text = String(value ?? "");
    for (const [pattern, translate] of DARIJA_PATTERNS) {
      const match = text.match(pattern);
      if (match) return translate(match);
    }
    let out = text;
    for (const [key, translation] of Object.entries(STATUS_DARIJA)) {
      const escaped = key.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      out = out.replace(new RegExp(`\\b${escaped}\\b`, "g"), translation);
    }
    return out;
  }
  async function api(path, options = {}) {
    const response = await fetch(path, { ...options, headers: { "Content-Type": "application/json", ...options.headers } });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      const error = new Error(response.status === 401 ? "سجّل الدخول باش تشوف المعلومات المحفوظة ديالك." :
        response.status === 403 ? "هاد المعلومات متاحة غير لحساب المالك." :
          (typeof body.detail === "string" ? body.detail : "الطلب فشل. حاول مرة اخرى."));
      error.status = response.status;
      throw error;
    }
    return response.json();
  }
  function syncCamera() {
    if (!camera || camera.disabled) return;
    const active = document.body.classList.contains("camera-on");
    camera.setAttribute("aria-pressed", String(active));
    camera.dataset.status = active ? "green" : "red";
    const pip = camera.querySelector(".status-pip");
    if (pip) pip.className = `status-pip ${active ? "green" : "red"}`;
    camera.title = active ? "الكاميرا: مباشرة · اضغط باش توقفها" : "الكاميرا: موقوفة · اضغط باش تشغّلها";
  }
  new MutationObserver(syncCamera).observe(document.body, { attributes: true, attributeFilter: ["class"] });
  syncCamera();
  const legendDialog = $("#legend-dialog");
  $("#quick-legend")?.addEventListener("click", () => {
    if (legendDialog && !legendDialog.open) legendDialog.showModal();
  });
  $("#close-legend")?.addEventListener("click", () => legendDialog?.close());
  function open(title) {
    $("#control-title").textContent = title;
    content.replaceChildren(node("p", "كيتحمّل…"));
    if (!dialog.open) dialog.showModal();
  }
  function errorMessage(error) { content.append(node("p", darija(error.message), "control-error")); }
  $("#close-control").addEventListener("click", () => dialog.close());
  document.addEventListener("atulya-device-status", (event) => {
    const notice = node("article");
    notice.append(node("strong", "الإيماءات كيتطلبو الانتباه"), node("p", darija(event.detail.gesture)));
    const dismiss = node("button", "أغلق"); dismiss.addEventListener("click", () => notice.remove());
    notice.append(dismiss); $("#reminder-notices").append(notice);
  });
  async function maintenancePanel() {
    open("الصيانة والإصلاحات المقترحة");
    try {
      const data = await api("/api/maintenance");
      content.replaceChildren(node("p", "الفحص كيدير كل خمس دقائق، بما فيه اتصال Google وحالة ضربات قلب التابع. أتوليا تقدر تفحص ملفات الواجهة والخلفية المسموح بها وتقترح إصلاحات مع إمكانية التراجع. أنت كتراجع الفروق والاختبارات قبل التطبيق. المصادقة والأسرار وإعدادات النشر محميين."));
      const auto = node("button", data.proactive.enabled ? "اقتراحات الذكاء الاصطناعي شغالة · اطفئها" : "اقتراحات الذكاء الاصطناعي موقوفة · شغّلها");
      auto.addEventListener("click", async () => {
        auto.disabled = true;
        try { await api("/api/maintenance/proactive", { method: "PUT", body: JSON.stringify({ enabled: !data.proactive.enabled }) }); await maintenancePanel(); }
        catch (error) { errorMessage(error); auto.disabled = false; }
      });
      content.append(auto, node("small", "كيستعمل الذكاء الاصطناعي المضبوط ديالك وربما كيستهلك رصيد المزوّد. كيدير غير للأعطاب المبدّلة، مرة على الأقل كل ساعة. كيبعت تنبيه للمالك عبر تيليجرام أو الإشعارات المربوطة. كيقترح تبديلات للمراجعة؛ ما كيطبّقهاش تلقائياً."));
      if (data.proactive.last_run.result) content.append(node("p", darija(data.proactive.last_run.result)));
      const check = node("button", "افحص دابا"); check.type = "button";
      check.addEventListener("click", async () => {
        check.disabled = true;
        try { await api("/api/maintenance/check", { method: "POST" }); await maintenancePanel(); }
        catch (error) { errorMessage(error); check.disabled = false; }
      }); content.append(check);
      content.append(node("h3", "آخر فحص"));
      const health = data.health;
      content.append(node("p", health.checked_at ? when(health.checked_at) : "أول فحص كيتستنى"));
      for (const finding of health.findings || []) content.append(node("p", darija(`${finding.area}: ${finding.message}${finding.next_step ? " · " + finding.next_step : ""}`), "control-error"));
      if (health.checked_at && !health.findings?.length) content.append(node("p", "فحص وجود الملفات وصحة صيغة الواجهة نجح. الكاميرا الحقيقية والتعرف على الإيماءات كيتطلبو فحص من الجهاز."));
      content.append(node("h3", "ملفات قابلة للتعديل"), node("p", (health.editable_files || []).join(", ")));
      content.append(node("p", health.skill_policy || "مهارات جديدة يقدرو يقترحوها للمراجعة من المالك."));
      content.append(node("h3", "الإصلاحات المقترحة"));
      if (!data.proposals.length) content.append(node("p", "ما كاينشي إصلاحات مقترحة. اطلب من أتوليا تشغّل maintenance_check، تفحص ملف مسموح، وتقترح إصلاحاً."));
      for (const proposal of data.proposals) {
        const row = node("div", undefined, "control-row");
        row.append(node("strong", darija(`${proposal.path} · ${proposal.state}`)), node("p", darija(proposal.reason)), node("small", darija(proposal.check)));
        const details = node("details"), summary = node("summary", "راجع الأسطر المبدّلة"), diff = node("pre", proposal.diff);
        details.append(summary, diff); row.append(details);
        if (["proposed", "applied"].includes(proposal.state)) {
          const action = proposal.state === "applied" ? "rollback" : "apply";
          const button = node("button", action === "apply" ? "وافق وطبّق هاد التصحيح" : "تراجع على هاد التصحيح");
          button.addEventListener("click", async () => {
            button.disabled = true;
            try { await api(`/api/maintenance/proposals/${proposal.id}/${action}`, { method: "POST" }); await maintenancePanel(); }
            catch (error) { errorMessage(error); button.disabled = false; }
          }); row.append(button);
        }
        content.append(row);
      }
    } catch (error) { content.replaceChildren(); errorMessage(error); }
  }
  $("#quick-maintenance").addEventListener("click", maintenancePanel);
  async function reminders() {
    open("التذكيرات والاجتماعات");
    try {
      const data = await api("/api/reminders");
      content.replaceChildren(node("p", "التذكيرات كتظهر فهاد الصفحة إلا كانت أتوليا مفتوحة ومسجّل الدخول. إلا سكرتيها، التذكيرات المتأخرة كتظهر من بعد ما ترجعي. التوصيل في الخلفية ولا عبر تيليجرام غير مفعّل لهاد التذكيرات."));
      const form = node("form");
      const messageLabel = node("label", "ذكّرني باش");
      const message = node("input"); message.required = true; message.maxLength = 1000; message.name = "message";
      messageLabel.append(message);
      const dateLabel = node("label", "متى (بالوقت المحلي ديال جهازك)");
      const date = node("input"); date.type = "datetime-local"; date.required = true; date.name = "due_at";
      dateLabel.append(date);
      const save = node("button", "احفظ التذكير"); save.type = "submit";
      let editingId = null;
      const test = node("button", "اختبر تذكير من بعد 10 ثواني"); test.type = "button";
      const feedback = node("p"); feedback.setAttribute("role", "status");
      form.append(messageLabel, dateLabel, save, test, feedback); content.append(form);
      async function create(text, due) {
        save.disabled = test.disabled = true;
        try {
          const result = await api(editingId ? `/api/reminders/${editingId}` : "/api/reminders", { method: editingId ? "PUT" : "POST", body: JSON.stringify({ message: text, due_at: due.toISOString() }) });
          const savedId = editingId || result.id;
          await reminders();
          content.prepend(node("p", `Saved reminder #${savedId} for ${when(due.toISOString())}.`, "control-success"));
        } catch (error) { feedback.textContent = darija(error.message); }
        finally { save.disabled = test.disabled = false; }
      }
      form.addEventListener("submit", (event) => { event.preventDefault(); void create(message.value, new Date(date.value)); });
      test.addEventListener("click", () => { editingId = null; void create("اختبار توصيل التذكير", new Date(Date.now() + 10000)); });
      content.append(node("h3", "التذكيرات المحفوظة"));
      if (!data.reminders.length) content.append(node("p", "ما كاينشي تذكيرات ويب محفوظة."));
      for (const item of data.reminders) {
        const row = node("div", undefined, "control-row");
        const state = item.cancelled_at ? "ملغى" : item.shown_at ? darija(`Shown in page ${when(item.shown_at)}`) : "مجدول";
        row.append(node("strong", `#${item.id} · ${item.message}`), node("small", `${when(item.due_at)} · ${state}`));
        if (!item.cancelled_at && !item.shown_at) {
          const edit = node("button", "عدّل التذكير"); edit.type = "button";
          edit.addEventListener("click", () => {
            editingId = item.id; message.value = item.message;
            const local = new Date(item.due_at);
            date.value = new Date(local.getTime() - local.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
            save.textContent = darija(`Save changes to #${item.id}`); form.scrollIntoView({ block: "nearest" }); message.focus();
          }); row.append(edit);
          const cancel = node("button", "ألغِ التذكير"); cancel.type = "button";
          cancel.addEventListener("click", async () => {
            cancel.disabled = true;
            try { await api(`/api/reminders/${item.id}`, { method: "DELETE" }); await reminders(); }
            catch (error) { errorMessage(error); cancel.disabled = false; }
          }); row.append(cancel);
        }
        content.append(row);
      }
      content.append(node("h3", "الاجتماعات الجاية"));
      const meetings = await api("/api/calendar?conversation_id=controls");
      if (!meetings.events.length) content.append(node("p", "ما كاينشي اجتماعات جاية محفوظة."));
      for (const item of meetings.events) {
        const row = node("div", undefined, "control-row");
        row.append(node("strong", `#${item.id} · ${item.title}`), node("small", when(item.starts_at)));
        const remove = node("button", "احذف الاجتماع");
        remove.addEventListener("click", async () => {
          remove.disabled = true;
          try { await api(`/api/calendar/${item.id}?conversation_id=controls`, { method: "DELETE" }); await reminders(); }
          catch (error) { errorMessage(error); remove.disabled = false; }
        }); row.append(remove); content.append(row);
      }
      if (!document.body.classList.contains("non-admin")) {
        content.append(node("h3", "تاريخ تذكيرات تيليجرام"));
        const telegram = await api("/api/reminders/telegram");
        content.append(node("small", darija(telegram.delivery)));
        if (!telegram.reminders.length) content.append(node("p", "ما كاينشي تذكيرات محفوظة فطابور توصيل تيليجرام."));
        for (const item of telegram.reminders) {
          const state = item.cancelled_at ? "ملغى" : item.failed_at ? "فشل" : item.delivered_at ? "تبعت لتليليجرام · تنبيه الجوال غير متحقق" : "مجدول";
          const row = node("div", undefined, "control-row");
          row.append(node("strong", `#${item.id} · ${item.message}`), node("small", `${when(item.due_at)} · ${state}`));
          content.append(row);
        }
      }
    } catch (error) { content.replaceChildren(); errorMessage(error); }
  }
  $("#quick-reminders").addEventListener("click", reminders);
  $("#quick-connections").addEventListener("click", async () => {
    open("الاتصالات والصلاحيات");
    try {
      const data = await api("/api/connections");
      content.replaceChildren(node("h3", "الإضافات المدمجة"));
      for (const plugin of data.plugins) {
        const row = node("div", undefined, "control-row");
        row.append(node("strong", plugin.name), node("small", darija(`Access: ${(plugin.permissions || []).join(", ") || "أدوات أساسية"}`)));
        const toggle = node("button", plugin.enabled ? "مفعّل · عطّل" : "معطّل · شغّل");
        toggle.type = "button";
        toggle.addEventListener("click", async () => {
          toggle.disabled = true;
          try {
            const result = await api(`/api/plugins/${encodeURIComponent(plugin.id)}`, {
              method: "POST", body: JSON.stringify({ enabled: !plugin.enabled }) });
            plugin.enabled = result.plugin.enabled;
            await refreshCapabilities();
            toggle.textContent = plugin.enabled ? "مفعّل · عطّل" : "معطّل · شغّل";
          } catch (error) { errorMessage(error); }
          finally { toggle.disabled = false; }
        });
        row.append(toggle); content.append(row);
      }
      const capabilityPanel = node("div");
      async function refreshCapabilities() {
        const result = await api("/api/capabilities");
        capabilityPanel.replaceChildren(node("h3", "جاهزية الأدوات"), node("p", "الجاهزية ما كتأكدش التنفيذ ولا التحقق من الجهاز."));
        for (const cap of result.capabilities) {
          const row = node("div", undefined, "control-row");
          row.append(node("strong", `${darija(cap.name)} · ${darija(cap.status)}`), node("small", darija(cap.description)), node("small", darija(cap.next_step)));
          capabilityPanel.append(row);
        }
      }
      content.append(capabilityPanel);
      await refreshCapabilities();
      const googleAccount = node("button", "حسابات Google وGmail وCalendar");
      googleAccount.addEventListener("click", connectionsPanel); content.prepend(googleAccount);
      content.append(node("h3", "المهارات"), node("p", "المهارات كتعطي تعليمات عمل. أفعالها كتطلب أدوات مربوطة ونفس الموافقات."));
      if (!data.skills.length) content.append(node("p", "ما كاينشي مهارات منصّبة."));
      for (const skill of data.skills) {
        const row = node("div", undefined, "control-row");
        row.append(node("strong", skill.name), node("small", skill.description)); content.append(row);
      }
      content.append(node("h3", "MCP"), node("p", darija(data.mcp.incoming)), node("p", darija(data.mcp.outgoing)),
        node("p", darija(`Exported tools depend on enabled plugins: ${data.mcp.tools.join(", ")}`)),
        node("h3", "صلاحية الصيانة"), node("p", darija(data.maintenance)));
      const form = node("form");
      const nameLabel = node("label", "اسم الاتصال"), name = node("input"); name.required = true; name.maxLength = 60; nameLabel.append(name);
      const urlLabel = node("label", "عنوان MCP HTTPS ولا HTTP محلي (loopback)"), url = node("input"); url.required = true; url.type = "url"; url.placeholder = "https://your-server.example/mcp or http://127.0.0.1:3001/mcp"; urlLabel.append(url);
      const add = node("button", "احفظ اتصال MCP"); add.type = "submit";
      form.append(nameLabel, urlLabel, node("small", "استعمل عنواناً كتثق فيه. الدعم الأولي كيربط السيرفرات بلا مصادقة. الحفظ ما كيعطي حتى أداة."), add);
      form.addEventListener("submit", async (event) => {
        event.preventDefault(); add.disabled = true;
        try { await api("/api/mcp/connections", { method: "POST", body: JSON.stringify({ name: name.value, url: url.value }) }); $("#quick-connections").click(); }
        catch (error) { errorMessage(error); add.disabled = false; }
      }); content.append(node("h3", "سيرفرات MCP الخارجية"), form);
      for (const connection of data.external_mcp || []) {
        const row = node("div", undefined, "control-row");
        row.append(node("strong", connection.name), node("small", darija(connection.url)), node("p", darija(connection.status)));
        const test = node("button", "اختبر واكتشف الأدوات");
        test.addEventListener("click", async () => {
          test.disabled = true;
          try { await api(`/api/mcp/connections/${connection.id}/test`, { method: "POST" }); $("#quick-connections").click(); }
          catch (error) { errorMessage(error); test.disabled = false; }
        }); row.append(test);
        const remove = node("button", "افصل");
        remove.addEventListener("click", async () => {
          remove.disabled = true;
          try { await api(`/api/mcp/connections/${connection.id}`, { method: "DELETE" }); $("#quick-connections").click(); }
          catch (error) { errorMessage(error); remove.disabled = false; }
        }); row.append(remove);
        for (const tool of connection.tools) {
          const grant = node("button", `${tool.granted ? "اسحب" : "امنح"} ${tool.name}`);
          grant.title = darija(tool.description);
          grant.addEventListener("click", async () => {
            grant.disabled = true;
            try { await api(`/api/mcp/connections/${connection.id}/grant`, { method: "POST", body: JSON.stringify({ tool: tool.name, granted: !tool.granted }) }); $("#quick-connections").click(); }
            catch (error) { errorMessage(error); grant.disabled = false; }
          }); row.append(grant);
        }
        content.append(row);
      }
    } catch (error) { content.replaceChildren(); errorMessage(error); }
  });
  $("#quick-status").addEventListener("click", async () => {
    open("لوحة التحكم");
    const cameraOn = document.body.classList.contains("camera-on");
    content.replaceChildren(node("p", `الكاميرا على هاد الجهاز: ${cameraOn ? "شغالة" : "موقوفة"}. ${cameraOn ? darija($("#gesture-result")?.textContent || "") : "التعرف على الإيماءات كيستنى الكاميرا."}`));
    content.append(node("p", "الاتصالات كتدير أدوات MCP الممنوحة. الصيانة تقدر تشخّص المشاكل وتقترح تعديلات على ملفات الواجهة والمهارات المسموح بها. آخر تشغيلات الأدوات تحت كتعرض اللي تنفّذ فعلاً."));
    try {
      const data = await api("/api/status?conversation_id=controls");
      const grid = node("div", undefined, "dashboard-grid"); content.append(grid);
      for (const key of ["service", "model", "cpu", "memory", "network", "host", "voice", "speech", "vision", "gesture", "telegram", "issue"]) {
        const row = node("div", undefined, "control-row");
        row.dataset.state = data[key]?.state || "unknown";
        row.append(node("strong", DASH_KEYS[key] || key), node("span", darija(data[key]?.label || "غير معروف"))); grid.append(row);
      }
      content.append(node("h3", "آخر تشغيلات الأدوات"));
      const activity = await api("/api/activity?limit=30");
      if (!activity.entries.length) content.append(node("p", "ما كاينشي تشغيلات أدوات مسجّلة. هادشي ما كأكدش أن العملية كملت."));
      for (const item of activity.entries) {
        const row = node("div", undefined, "control-row");
        row.append(node("strong", darija(`${item.tool} · ${item.outcome}`)), node("small", darija(`${when(item.at)} · ${item.channel}`))); content.append(row);
      }
    } catch (error) { errorMessage(error); }
  });
  function googleConnect(features) {
    const url = new URL("/api/auth/google/start", location.origin);
    url.searchParams.set("connect", "true"); url.searchParams.set("features", features);
    if (window.AtulyaNative) window.AtulyaNative.postMessage(JSON.stringify({cmd:"google_login", url:url.href}));
    else location.assign(url.href);
  }
  async function connectionsPanel() {
    open("الاتصالات");
    try {
      const google = await api("/api/google/status");
      content.replaceChildren(node("h3", "Google · Gmail وCalendar"),
        node("p", "تسجيل الدخول لأتوليا ومنح صلاحية خدمات Google شيئان منفصلان. اختر الخدمات اللي بغيتي تربطها."),
        node("p", google.متصل ? `Connected: ${google.email || "حساب Google"}` : "غير متصل"));
      if (!google.configured) content.append(node("p", "Google OAuth غير مضبوط على السيرفر."));
      if (google.last_error) content.append(node("p", google.last_error, "control-error"));
      content.append(node("small", `امنحed scopes: ${(google.scopes || []).join(", ") || "لا شيء"}`));
      for (const [label, features] of [["اربط Gmail", "gmail"], ["اربط Calendar", "calendar"], ["اربطهما معاً", "all"]]) {
        const button = node("button", label); button.disabled = !google.configured;
        button.addEventListener("click", () => googleConnect(features)); content.append(button);
      }
      const test = node("button", "اختبر وصول Google");
      test.addEventListener("click", async () => {
        test.disabled = true;
        try { const result = await api("/api/google/test", {method:"POST"}); content.append(node("p", darija(result.message))); }
        catch (error) { errorMessage(error); } finally { test.disabled = false; }
      });
      const disconnect = node("button", "افصل خدمات Google");
      disconnect.addEventListener("click", async () => {
        disconnect.disabled = true;
        try { await api("/api/google/connection", {method:"DELETE"}); await connectionsPanel(); }
        catch (error) { errorMessage(error); disconnect.disabled = false; }
      }); content.append(test, disconnect);
      content.append(node("h3", "Telegram"), node("p", "المحادثة والتذكيرات والتحديثات المجدولة كيستعملو السيرفر. استعمل «الجدولة» باش تتحكم فالرسائل المتكررة. صوت إشعار الجوال كيتحكم فيه أندرويد وتيليجرام."));
      const readiness = await api("/api/readiness");
      content.append(node("h3", "اللي كيتطلب الانتباه"));
      if (!readiness.findings.length) content.append(node("p", "الاتصالات المضبوطة وضربات قلب الأجهزة الأخيرة جاهزة. شغّل اختبارات الخدمة/الجهاز باش تتحقق من التنفيذ."));
      for (const finding of readiness.findings) content.append(node("p", `${finding.message} · ${finding.next_step}`, "control-error"));
      content.append(node("h3", "واتساب بيزنس"), node("p", "غير متصل. حساب أتوليا بيزنس الجديد كيتطلب حساب Meta ورقم جوال وبيانات سيرفر موافق عليها."));
      const mcp = node("button", "دير اتصالات MCP");
      mcp.addEventListener("click", () => $("#quick-connections")?.click()); content.append(mcp);
    } catch (error) { errorMessage(error); }
  }
  async function devicesPanel() {
    open("الأجهزة وإيصالات التنفيذ");
    try {
      const data = await api("/api/devices");
      content.replaceChildren(node("p", "كل جهاز عنده بيانات دخول قابلة للسحب وأفعال مسموحة. الطلب المصفوف ماشي تنفيذ."));
      const refresh = node("button", "حدّث الأجهزة والإيصالات");
      refresh.addEventListener("click", devicesPanel); content.append(refresh);
      if (window.AtulyaNative) {
        const stay = node("button", "خلّي هاد الجوال متصل");
        stay.addEventListener("click", () => window.AtulyaNative.postMessage(JSON.stringify({cmd:"background_connection"})));
        content.append(stay);
      }
      for (const device of data.devices) {
        const row = node("details", undefined, "control-row device-block");
        const deviceJobs = data.jobs.filter(job => job.device === device.name);
        const seen = device.seen ? new Date(device.seen * 1000).toLocaleString() : "أبداً";
        row.append(node("summary", `${darija(device.name)} · ${darija(device.status)} · آخر ظهور ${seen}`),
          node("small", `القدرات: ${darija(device.abilities.join(", "))}`));
        const jobList = node("div");
        jobList.append(node("h4", darija(`Jobs (${deviceJobs.length})`)));
        for (const job of deviceJobs.slice(0, 10)) jobList.append(node("p", darija(`${job.kind} · ${job.status} · ${job.output || "ما كاين إيصال تنفيذ حتى دابا."}`)));
        row.append(jobList);
        const test = node("button", "اختبر الاتصال");
        test.disabled = !device.abilities.includes("ping");
        test.addEventListener("click", async () => {
          test.disabled = true;
          const feedback = node("p", "كيبعت إشارة؛ كيستنى إيصال الجهاز…"); row.append(feedback);
          try {
            const result = await api(`/api/devices/${encodeURIComponent(device.name)}/test`, {method:"POST"});
            const deadline = Date.now() + 15000;
            let finished = false;
            while (Date.now() < deadline && dialog.open) {
              const snapshot = await api("/api/devices");
              const job = snapshot.jobs.find(item => item.id === result.job.id);
              if (job && ["executed", "failed", "cancelled", "unconfirmed"].includes(job.status)) {
                feedback.textContent = darija(`${job.status === "executed" ? "الاتصال مُتحقق" : job.status}: ${job.output || "ما كاين إيصال تنفيذ"}`);
                finished = true; break;
              }
              await new Promise(resolve => setTimeout(resolve, 1000));
            }
            if (!finished) feedback.textContent = "ما كاين إيصال حتى دابا. شغّل التابع على هاد الجهاز، من بعد حدّث الأجهزة باش تشوف الإشارة المصفوفة.";
          } catch(error) { feedback.textContent = darija(error.message); }
          finally { test.disabled = false; }
        }); row.append(test);
        const revoke = node("button", "اسحب الجهاز");
        revoke.addEventListener("click", async () => {
          revoke.disabled = true;
          try { await api(`/api/devices/${encodeURIComponent(device.name)}`, {method:"DELETE"}); await devicesPanel(); }
          catch (error) { errorMessage(error); revoke.disabled = false; }
        }); row.append(revoke); content.append(row);
      }
      const form = node("form");
      const typeSelect = node("select");
      typeSelect.style.cssText = "width:100%;margin-bottom:8px;padding:8px;border-radius:6px;background:#102630;color:#fff;border:1px solid #437181;";
      typeSelect.innerHTML = `
        <option value="phone">📱 جوال (أندرويد / iOS)</option>
        <option value="tv">📺 تلفاز ذكي (Android TV / Fire TV)</option>
        <option value="tablet">📟 جهاز لوحي (iPad / أندرويد)</option>
        <option value="laptop" selected>💻 كمبيوتر محمول / مكتبي (ويندوز / ماك / لينكس)</option>
      `;
      const labelType = node("label", "نوع الجهاز");
      labelType.append(typeSelect);

      const label = node("label", "اسم الجهاز (مثال: تلفاز قاعة الجلوس، Pixel 9، MacBook)");
      const name = node("input"); name.required = true; name.maxLength = 40; name.placeholder = "تلفاز قاعة الجلوس"; label.append(name);
      const choices = node("fieldset"); choices.append(node("legend", "القدرات الممنوحة"));
      const allAbilities = [
        "ping", "say", "open_url", "open_app",
        "list_files", "read_file",
        "take_photo", "list_photos",
        "media_control", "send_sms", "place_call",
        "display_message", "battery_status"
      ];
      const presets = {
        phone: ["ping", "say", "take_photo", "list_photos", "send_sms", "place_call", "open_app", "battery_status"],
        tv: ["ping", "say", "media_control", "open_app", "open_url", "display_message"],
        tablet: ["ping", "say", "take_photo", "list_photos", "open_app", "list_files", "read_file", "display_message"],
        laptop: ["ping", "battery_status", "open_app", "open_url", "media_control", "display_message"]
      };
      const checkMap = {};
      const grants = [];
      choices.style.cssText = "display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:6px;";
      for (const ability of allAbilities) {
        const item = node("label", ability); item.style.cssText = "display:flex;align-items:center;gap:6px;font-size:13px;";
        const check = node("input"); check.type = "checkbox"; check.value = ability;
        check.style.cssText = "width:auto;margin:0;";
        check.checked = presets.laptop.includes(ability);
        checkMap[ability] = check;
        item.prepend(check); choices.append(item); grants.push(check);
      }
      typeSelect.addEventListener("change", () => {
        const selectedPreset = presets[typeSelect.value] || [];
        for (const ability of allAbilities) {
          if (checkMap[ability]) {
            checkMap[ability].checked = selectedPreset.includes(ability);
          }
        }
      });

      const pair = node("button", "أنشئ بيانات دخول للجهاز"); pair.type = "submit";
      form.append(labelType, label, choices, pair); content.append(form);
      form.addEventListener("submit", async (event) => {
        event.preventDefault(); pair.disabled = true;
        try {
          const result = await api("/api/devices/pair", {method:"POST", body:JSON.stringify({name:name.value, abilities:grants.filter(c=>c.checked).map(c=>c.value), device_type:typeSelect.value})});
          const secret = node("textarea"); secret.readOnly = true; secret.value = result.token;
          secret.style.cssText = "width:100%;height:60px;margin-top:8px;background:#031018;color:#65e7f5;font-family:monospace;padding:8px;";
          content.append(node("p", "خلي هاد البيانات سرية. على الكمبيوتر ديالك نفّذ الأمر اللي لتحت والصق الرمز فالطلب المخفي. خلّي التابع شغال، من بعد استعمل «اختبر الاتصال». تطبيق أندرويد الحالي ما كيستهلكش طابور هاد الجهاز؛ كيتطلب تابع مثبّت."), secret,
            node("pre", `python -m tools.device_companion --url ${location.origin}`));
        } catch (error) { errorMessage(error); } finally { pair.disabled = false; }
      });
      const orphanJobs = data.jobs.filter(job => !data.devices.some(device => device.name === job.device));
      if (orphanJobs.length) content.append(node("h3", "مهام للأجهزة المحذوفة"));
      for (const job of orphanJobs) {
        const row = node("div", undefined, "control-row");
        row.append(node("strong", `${job.device} · ${job.kind} · ${job.status}`), node("small", job.id), node("p", job.output || "ما كاين إيصال تنفيذ حتى دابا.")); content.append(row);
      }
    } catch (error) { errorMessage(error); }
  }

  async function smartHomePanel() {
    open("المنزل الذكي والمشاهد المحيطة");
    try {
      content.replaceChildren(node("p", "أتمت إضاءة الغرف والأجهزة الذكية وشغّل مشاهد محيطة."));
      const grid = node("div", undefined, "dashboard-grid");
      const scenes = [
        { id: "movie_mode", title: "🎬 وضع الفيلم", desc: "خفّف الإضاءة لـ 20%، أوقف الصوت الخلفي، هيّئ التلفاز" },
        { id: "work_mode", title: "💼 وضع العمل", desc: "ضوء نهار أبيض 100%، صوت إنتاجية وتنبيهات" },
        { id: "goodnight", title: "🌙 تصبح على خير", desc: "أطفئ كل الأضواء، تحقق من الحساسات، اسكّت غير الطوارئ" },
        { id: "relax", title: "☕ استرخاء", desc: "إضاءة دافئة ومستوى صوت مهدّئ" }
      ];
      for (const scene of scenes) {
        const card = node("div", undefined, "control-row");
        card.append(node("strong", scene.title), node("small", scene.desc));
        const trigger = node("button", "شغّل");
        trigger.addEventListener("click", async () => {
          trigger.disabled = true;
          try {
            const res = await api("/api/smarthome/scene", { method: "POST", body: JSON.stringify({ scene: scene.id }) });
            card.append(node("p", darija(res.result)));
          } catch (err) { errorMessage(err); } finally { trigger.disabled = false; }
        });
        card.append(trigger); grid.append(card);
      }
      content.append(grid);

      content.append(node("h3", "فعل مباشر على الجهاز"));
      const devForm = node("form");
      const devLabel = node("label", "اسم الجهاز أو العنصر (مثال: مصباح المكتب، تلفاز قاعة الجلوس)");
      const devInput = node("input"); devInput.required = true; devInput.placeholder = "مصباح المكتب"; devLabel.append(devInput);
      const actLabel = node("label", "الفعل (turn_on، turn_off، toggle)");
      const actInput = node("input"); actInput.value = "turn_on"; actLabel.append(actInput);
      const brightLabel = node("label", "السطوع % (اختياري، 0-100)");
      const brightInput = node("input"); brightInput.type = "number"; brightInput.min = 0; brightInput.max = 100; brightInput.placeholder = "80"; brightLabel.append(brightInput);
      const sendBtn = node("button", "نفّذ الأمر"); sendBtn.type = "submit";
      devForm.append(devLabel, actLabel, brightLabel, sendBtn); content.append(devForm);
      devForm.addEventListener("submit", async (e) => {
        e.preventDefault(); sendBtn.disabled = true;
        try {
          const res = await api("/api/smarthome/scene", {
            method: "POST",
            body: JSON.stringify({ device: devInput.value, action: actInput.value, brightness: brightInput.value ? parseInt(brightInput.value) : null })
          });
          content.append(node("p", darija(res.result)));
        } catch (err) { errorMessage(err); } finally { sendBtn.disabled = false; }
      });
    } catch (err) { errorMessage(err); }
  }

  async function expensesPanel() {
    open("المصاريف والتحليل المالي");
    try {
      const data = await api("/api/expenses");
      const summary = data.summary || { total_spent: 0, total_transactions: 0, by_category: {} };
      const card = node("div", undefined, "control-row");
      card.append(
        node("strong", darija(`Total Spending: ₹${Number(summary.total_spent).toLocaleString("en-IN", {minimumFractionDigits: 2})}`)),
        node("small", darija(`${summary.total_transactions} recorded transactions`))
      );
      content.replaceChildren(card);

      const addForm = node("form");
      addForm.append(node("h3", "سجّل مصروفاً"));
      const amtLabel = node("label", "المبلغ (₹)");
      const amtInput = node("input"); amtInput.type = "number"; amtInput.step = "any"; amtInput.required = true; amtInput.placeholder = "450"; amtLabel.append(amtInput);
      const merchLabel = node("label", "التاجر / المستلم");
      const merchInput = node("input"); merchInput.required = true; merchInput.placeholder = "Swiggy / Amazon / Metro"; merchLabel.append(merchInput);
      const catLabel = node("label", "الفئة");
      const catSelect = node("select");
      catSelect.style.cssText = "width:100%;margin-bottom:8px;padding:8px;border-radius:6px;background:#102630;color:#fff;border:1px solid #437181;";
      catSelect.innerHTML = "<option>الأكل والمطاعم</option><option>السفر والتنقل</option><option>التسوق</option><option>المرافق</option><option>الصحة</option><option>شخصي</option>";
      catLabel.append(catSelect);
      const submitExpense = node("button", "سجّل المصروف"); submitExpense.type = "submit";
      addForm.append(amtLabel, merchLabel, catLabel, submitExpense); content.append(addForm);
      addForm.addEventListener("submit", async (e) => {
        e.preventDefault(); submitExpense.disabled = true;
        try {
          await api("/api/expenses", { method: "POST", body: JSON.stringify({ amount: parseFloat(amtInput.value), merchant: merchInput.value, category: catSelect.value }) });
          await expensesPanel();
        } catch (err) { errorMessage(err); submitExpense.disabled = false; }
      });

      const smsForm = node("form");
      smsForm.append(node("h3", "اختبر تحليل رسائل البنك/UPI"));
      const smsLabel = node("label", "الصق نص رسالة البنك/UPI");
      const smsInput = node("input"); smsInput.required = true; smsInput.placeholder = "صُرفت 450 روبية بالبطاقة عند SWIGGY"; smsLabel.append(smsInput);
      const smsBtn = node("button", "حلّل وسجّل تلقائياً"); smsBtn.type = "submit";
      smsForm.append(smsLabel, smsBtn); content.append(smsForm);
      smsForm.addEventListener("submit", async (e) => {
        e.preventDefault(); smsBtn.disabled = true;
        try {
          const res = await api("/api/expenses/parse-sms", { method: "POST", body: JSON.stringify({ sms_text: smsInput.value }) });
          if (res.parsed) { await expensesPanel(); } else { errorMessage(res.message); smsBtn.disabled = false; }
        } catch (err) { errorMessage(err); smsBtn.disabled = false; }
      });

      content.append(node("h3", "آخر المعاملات"));
      for (const item of data.recent || []) {
        const row = node("div", undefined, "control-row");
        row.append(
          node("strong", `₹${Number(item.amount).toLocaleString("en-IN", {minimumFractionDigits: 2})} · ${item.merchant}`),
          node("small", darija(`${item.category} · ${item.date}`))
        );
        content.append(row);
      }
    } catch (err) { errorMessage(err); }
  }

  $("#open-connections")?.addEventListener("click", connectionsPanel);
  $("#quick-devices")?.addEventListener("click", devicesPanel);
  $("#quick-smarthome")?.addEventListener("click", smartHomePanel);
  $("#quick-expenses")?.addEventListener("click", expensesPanel);

  async function weatherPanel(city="", period="today") {
    open("الطقس والتوقعات");
    const form = node("form"),label = node("label","المدينة"),input = node("input"),submit=node("button","اعرض الطقس");
    input.value=city;input.maxLength=100;label.append(input);submit.type="submit";form.append(label,submit);
    content.replaceChildren(form);
    form.addEventListener("submit",event=>{event.preventDefault();weatherPanel(input.value,period);});
    try {
      const data=await api(`/api/weather?city=${encodeURIComponent(city)}&when=${period}`);
      const card=node("p",darija(data.summary));card.style.whiteSpace="pre-line";content.append(card);
      for (const [name,value] of [["اليوم","today"],["غداً","tomorrow"],["7 أيام","week"]]) {
        const button=node("button",name);button.setAttribute("aria-pressed",String(value===period));
        button.addEventListener("click",()=>weatherPanel(input.value,value));content.append(button);
      }
      const daily=data.daily,days=daily.time || [],highs=daily.temperature_2m_max || [],lows=daily.temperature_2m_min || [];
      const points=days.map((day,i)=>({day,hi:highs[i],lo:lows[i],rain:daily.precipitation_probability_max?.[i]})).filter(p=>Number.isFinite(p.hi)&&Number.isFinite(p.lo));
      if (points.length) {
        const ns="http://www.w3.org/2000/svg",svg=document.createElementNS(ns,"svg");svg.setAttribute("viewBox","0 0 560 180");svg.setAttribute("role","img");svg.setAttribute("aria-label","توقع درجات الحرارة الدنيا والعليا يومياً، بالدرجات المئوية");
        const title=document.createElementNS(ns,"title");title.textContent="درجات الحرارة الدنيا والعليا يومياً (°C)";svg.append(title);
        const min=Math.min(...points.map(p=>p.lo))-2,max=Math.max(...points.map(p=>p.hi))+2;
        for (const [index,point] of points.entries()) {
          const x=40+index*480/Math.max(1,points.length-1),y=v=>130-(v-min)/(max-min)*105;
          const line=document.createElementNS(ns,"line");line.setAttribute("x1",x);line.setAttribute("x2",x);line.setAttribute("y1",y(point.hi));line.setAttribute("y2",y(point.lo));line.setAttribute("stroke","#65e7f5");line.setAttribute("stroke-width","10");svg.append(line);
          const text=document.createElementNS(ns,"text");text.setAttribute("x",x);text.setAttribute("y","158");text.setAttribute("text-anchor","middle");text.setAttribute("fill","#eefaff");text.setAttribute("font-size","11");text.textContent=`${point.lo}–${point.hi}°`;svg.append(text);
        }
        content.append(svg,node("small","مدى التوقعات حسب اليوم · Open-Meteo"));
        for (const point of points) content.append(node("p",darija(`${point.day}: ${point.lo}–${point.hi}°C · rain ${point.rain ?? "?"}%`)));
      }
    } catch(error){errorMessage(error);}
  }
  $("#quick-weather")?.addEventListener("click",()=>weatherPanel());

  async function phonePanel() {
    open("أفعال الجوال");
    try {
      const data = await api("/api/phone/actions");
      content.replaceChildren(node("p", "مسودات الرسائل وطلبات الاتصال المجهزة على السيرفر كتظهر هنا. اضغط على الطلب من تطبيق أندرويد. أنت كتبعت الرسالة ولا كتصل المكالمة من تطبيق الجوال نفسو."));
      if (!window.AtulyaNative) content.append(node("p", "افتح هاد الشاشة من تطبيق أتوليا أندرويد المحدّث باش تنفّذ أفعال الجوال."));
      for (const item of data.requests) {
        const row = node("div", undefined, "control-row");
        row.append(node("strong", `${item.kind === "dial" ? "مكالمة" : "مسودة رسالة"} · ${item.number}`));
        if (item.body) row.append(node("p", item.body));
        const run = node("button", item.kind === "dial" ? "افتح لوحة الاتصال" : "افتح محرر الرسائل");
        run.disabled = !window.AtulyaNative;
        run.addEventListener("click", () => {
          run.disabled = true;
          window.AtulyaNative.postMessage(JSON.stringify({cmd:item.kind,id:item.id,number:item.number,body:item.body}));
          row.append(node("small", "كيستنى إيصال تطبيق الجوال…"));
        });
        const cancel = node("button", "ألغِ الطلب");
        cancel.addEventListener("click", async () => {
          try {await api(`/api/phone/actions/${item.id}/receipt`,{method:"POST",body:JSON.stringify({state:"cancelled"})});await phonePanel();}
          catch(error){errorMessage(error);}
        }); row.append(run,cancel);content.append(row);
      }
      if (!data.requests.length) content.append(node("p", "ما كاينشي طلبات جوال معلّقة. اطلب من أتوليا تجهيز رسالة ولا مكالمة مع الرقم."));
    } catch (error) { errorMessage(error); }
  }
  document.addEventListener("atulya-phone-receipt", async event => {
    const receipt = event.detail;
    try {
      await api(`/api/phone/actions/${encodeURIComponent(receipt.id)}/receipt`,{method:"POST",body:JSON.stringify({state:receipt.status})});
      if (dialog.open && $("#control-title").textContent === "أفعال الجوال") {
        await phonePanel();content.prepend(node("p", darija(`${receipt.status.replaceAll("_"," ")}. No SMS send or completed call is verified.`)));
      }
    } catch(error){errorMessage(error);}
  });
  $("#quick-phone")?.addEventListener("click",phonePanel);

  async function schedulesPanel() {
    open("التحديثات المجدولة والتذكيرات المتكررة");
    try {
      const data = await api("/api/automations");
      content.replaceChildren(node("p", "التذكيرات لمرة وحدة والجدولة المتكررة منفصلون. هاد اللائحة كتعرض تحديثات تيليجرام المتكررة."));
      for (const item of data.routines) {
        const row = node("div", undefined, "control-row");
        row.append(node("strong", item.name), node("small", `${darija(data.types[item.action] || item.action)} · ${darija(item.days)} ${darija(item.when)} · ${item.enabled ? "شغال" : "موقوف"}`));
        const toggle = node("button", item.enabled ? "أوقف" : "أكمل");
        toggle.addEventListener("click", async () => {
          toggle.disabled = true;
          try { await api(`/api/automations/${encodeURIComponent(item.id)}`, { method: "PUT", body: JSON.stringify({ enabled: !item.enabled }) }); await schedulesPanel(); }
          catch (error) { errorMessage(error); toggle.disabled = false; }
        });
        const remove = node("button", "احذف الجدولة");
        remove.addEventListener("click", async () => {
          remove.disabled = true;
          try { await api(`/api/automations/${encodeURIComponent(item.id)}`, { method: "DELETE" }); await schedulesPanel(); }
          catch (error) { errorMessage(error); remove.disabled = false; }
        });
        row.append(toggle, remove); content.append(row);
      }
      if (!data.routines.length) content.append(node("p", "ما كاينشي جدولات متكررة."));
      const stop = node("button", "ألغِ كل التذكيرات لمرة وحدة والمتكررة");
      stop.addEventListener("click", async () => {
        stop.disabled = true;
        try {
          const result = await api("/api/reminders/cancel-all", { method: "POST" });
          await schedulesPanel();
          content.prepend(node("p", darija(`Cancelled ${result.web_cancelled} app reminders and ${result.telegram_cancelled} Telegram reminders; paused ${result.recurring_reminders_disabled} recurring reminders. ${result.note}`)));
        } catch (error) { errorMessage(error); stop.disabled = false; }
      });
      content.append(stop, node("small", data.delivery));
      const history=await api("/api/notifications");
      content.append(node("h3","آخر الرسائل المجدولة"),node("small",darija(history.note)));
      for(const item of history.deliveries) {
        const row=node("div",undefined,"control-row");
        row.append(node("strong",darija(`${item.source} · ${item.status}`)),node("small",new Date(item.created*1000).toLocaleString()),node("p",darija(item.text)));
        content.append(row);
      }

    } catch (error) { errorMessage(error); }
  }
  $("#quick-schedules")?.addEventListener("click", schedulesPanel);

  async function pollReminders() {
    if (polling || document.hidden) return;
    polling = true;
    try {
      const data = await api("/api/reminders?due_only=true");
      for (const item of data.reminders) {
        if (!shown.has(item.id)) {
          const notice = node("article");
          notice.append(node("strong", `Reminder #${item.id}`), node("p", item.message), node("small", `Due ${when(item.due_at)}`));
          const dismiss = node("button", "أغلق"); dismiss.type = "button";
          dismiss.addEventListener("click", () => notice.remove()); notice.append(dismiss);
          // Dialogs occupy the browser's top layer. Put notices in the open dialog so they are visible there too.
          (dialog.open ? content : $("#reminder-notices")).prepend(notice);
          shown.add(item.id);
        }
        await api(`/api/reminders/${item.id}/shown`, { method: "POST" });
      }
    } catch (error) {
      if (error.status === 401) { shown.clear(); $("#reminder-notices").replaceChildren(); }
    } finally { polling = false; }
  }
  window.setInterval(pollReminders, 3000);
  document.addEventListener("visibilitychange", () => { void pollReminders(); });
  async function implementationPanel() {
    open("سجل العمل: مكتمل، ناشط وغير مكتمل");
    try {
      const report = await api("/api/implementation");
      content.replaceChildren(node("p", `${darija(report.scope)} ${darija(`Updated ${report.updated}`)}.`));
      for (const item of report.items) {
        const row = node("div", undefined, "control-row");
        row.append(node("strong", `${darija(item.title)} · ${darija(item.status)}`));
        row.append(node("p", darija(item.evidence)), node("p", darija(`Next: ${item.next}`)));
        content.append(row);
      }
    } catch (error) { errorMessage(error); }
  }
  async function operationsPanel() {
    open("عمليات السيرفر والتنبيهات الحرجة");
    try {
      const report = await api("/api/operations");
      content.replaceChildren(node("p", darija(`Worker: ${report.worker_connected ? "connected" : "not connected"}. ${report.limits}`)));
      const refresh = node("button", "حدّث العمليات");
      refresh.addEventListener("click", operationsPanel); content.append(refresh);
      const toggle = node("button", report.alerts_enabled ? "اسكّت التنبيهات الحرجة للسيرفر" : "شغّل التنبيهات الحرجة للسيرفر");
      toggle.addEventListener("click", async () => {
        try { await api(`/api/operations/alerts/${!report.alerts_enabled}`, {method:"PUT"}); await operationsPanel(); }
        catch (error) { errorMessage(error); }
      });
      content.append(toggle, node("p", "باش تعيد التشغيل، اطلب من أتوليا تعيد تشغيل خدمتها، راجع الموافقة، من بعد تحقق من الإيصال هنا. قبول تيليجرام ما كيتحققش من صوت الجوال ولا التوصيل."));
      for (const item of report.jobs) content.append(node("p", darija(`${item.kind} ${item.target} · ${item.status} · ${item.result || "ما كاين إيصال تنفيذ حتى دابا"}`)));
      for (const alert of report.alerts) content.append(node("p", darija(`${alert.message} · ${alert.status}`)));
    } catch (error) { errorMessage(error); }
  }
  async function tasksPanel() {
    open("مهام التشخيص المستمرة");
    try {
      const report = await api("/api/tasks");
      content.replaceChildren(node("p", darija(report.limits)));
      const refresh = node("button", "حدّث المهام");
      refresh.addEventListener("click", tasksPanel); content.append(refresh);
      const start = node("button", "افحص أجهزتي واتصال Google");
      start.addEventListener("click", async () => {
        start.disabled = true;
        try { await api("/api/tasks", {method:"POST", body:JSON.stringify({checks:["devices","google_connection"]})}); await tasksPanel(); }
        catch (error) { errorMessage(error); start.disabled = false; }
      });
      content.append(start);
      for (const task of report.tasks) {
        const row = node("div", undefined, "control-row");
        row.append(node("strong", darija(`${task.id} · ${task.status} · ${task.checkpoint}/${task.plan.length} checks`)));
        for (const result of task.results) row.append(node("pre", JSON.stringify(result, null, 2)));
        if (["queued","running"].includes(task.status)) {
          const cancel = node("button", "ألغِ المهمة");
          cancel.addEventListener("click", async () => {
            try { await api(`/api/tasks/${encodeURIComponent(task.id)}`, {method:"DELETE"}); await tasksPanel(); }
            catch (error) { errorMessage(error); }
          });
          row.append(cancel);
        }
        content.append(row);
      }
    } catch (error) { errorMessage(error); }
  }

  async function smartHomePanel() {
    open("المنزل الذكي والمشاهد المحيطة");
    try {
      content.replaceChildren(node("p", "أتمت إضاءة الغرف والأجهزة الذكية وشغّل مشاهد محيطة."));
      const grid = node("div", undefined, "dashboard-grid");
      const scenes = [
        { id: "movie_mode", title: "🎬 وضع الفيلم", desc: "خفّف الإضاءة لـ 20%، أوقف الصوت الخلفي، هيّئ التلفاز" },
        { id: "work_mode", title: "💼 وضع العمل", desc: "ضوء نهار أبيض 100%، صوت إنتاجية وتنبيهات" },
        { id: "goodnight", title: "🌙 تصبح على خير", desc: "أطفئ كل الأضواء، تحقق من الحساسات، اسكّت غير الطوارئ" },
        { id: "relax", title: "☕ استرخاء", desc: "إضاءة دافئة ومستوى صوت مهدّئ" }
      ];
      for (const scene of scenes) {
        const card = node("div", undefined, "control-row");
        card.append(node("strong", scene.title), node("small", scene.desc));
        const trigger = node("button", "شغّل");
        trigger.addEventListener("click", async () => {
          trigger.disabled = true;
          try {
            const res = await api("/api/smarthome/scene", { method: "POST", body: JSON.stringify({ scene: scene.id }) });
            card.append(node("p", darija(res.result)));
          } catch (err) { errorMessage(err); } finally { trigger.disabled = false; }
        });
        card.append(trigger); grid.append(card);
      }
      content.append(grid);

      content.append(node("h3", "فعل مباشر على الجهاز"));
      const devForm = node("form");
      const devLabel = node("label", "اسم الجهاز أو العنصر (مثال: مصباح المكتب، تلفاز قاعة الجلوس)");
      const devInput = node("input"); devInput.required = true; devInput.placeholder = "مصباح المكتب"; devLabel.append(devInput);
      const actLabel = node("label", "الفعل (turn_on، turn_off، toggle)");
      const actInput = node("input"); actInput.value = "turn_on"; actLabel.append(actInput);
      const brightLabel = node("label", "السطوع % (اختياري، 0-100)");
      const brightInput = node("input"); brightInput.type = "number"; brightInput.min = 0; brightInput.max = 100; brightInput.placeholder = "80"; brightLabel.append(brightInput);
      const sendBtn = node("button", "نفّذ الأمر"); sendBtn.type = "submit";
      devForm.append(devLabel, actLabel, brightLabel, sendBtn); content.append(devForm);
      devForm.addEventListener("submit", async (e) => {
        e.preventDefault(); sendBtn.disabled = true;
        try {
          const res = await api("/api/smarthome/scene", {
            method: "POST",
            body: JSON.stringify({ device: devInput.value, action: actInput.value, brightness: brightInput.value ? parseInt(brightInput.value) : null })
          });
          content.append(node("p", darija(res.result)));
        } catch (err) { errorMessage(err); } finally { sendBtn.disabled = false; }
      });
    } catch (err) { errorMessage(err); }
  }

  async function expensesPanel() {
    open("المصاريف والتحليل المالي");
    try {
      const data = await api("/api/expenses");
      const summary = data.summary || { total_spent: 0, total_transactions: 0, by_category: {} };
      const card = node("div", undefined, "control-row");
      card.append(
        node("strong", darija(`Total Spending: ₹${Number(summary.total_spent).toLocaleString("en-IN", {minimumFractionDigits: 2})}`)),
        node("small", darija(`${summary.total_transactions} recorded transactions`))
      );
      content.replaceChildren(card);

      const addForm = node("form");
      addForm.append(node("h3", "سجّل مصروفاً"));
      const amtLabel = node("label", "المبلغ (₹)");
      const amtInput = node("input"); amtInput.type = "number"; amtInput.step = "any"; amtInput.required = true; amtInput.placeholder = "450"; amtLabel.append(amtInput);
      const merchLabel = node("label", "التاجر / المستلم");
      const merchInput = node("input"); merchInput.required = true; merchInput.placeholder = "Swiggy / Amazon / Metro"; merchLabel.append(merchInput);
      const catLabel = node("label", "الفئة");
      const catSelect = node("select");
      catSelect.style.cssText = "width:100%;margin-bottom:8px;padding:8px;border-radius:6px;background:#102630;color:#fff;border:1px solid #437181;";
      catSelect.innerHTML = "<option>الأكل والمطاعم</option><option>السفر والتنقل</option><option>التسوق</option><option>المرافق</option><option>الصحة</option><option>شخصي</option>";
      catLabel.append(catSelect);
      const submitExpense = node("button", "سجّل المصروف"); submitExpense.type = "submit";
      addForm.append(amtLabel, merchLabel, catLabel, submitExpense); content.append(addForm);
      addForm.addEventListener("submit", async (e) => {
        e.preventDefault(); submitExpense.disabled = true;
        try {
          await api("/api/expenses", { method: "POST", body: JSON.stringify({ amount: parseFloat(amtInput.value), merchant: merchInput.value, category: catSelect.value }) });
          await expensesPanel();
        } catch (err) { errorMessage(err); submitExpense.disabled = false; }
      });

      const smsForm = node("form");
      smsForm.append(node("h3", "اختبر تحليل رسائل البنك/UPI"));
      const smsLabel = node("label", "الصق نص رسالة البنك/UPI");
      const smsInput = node("input"); smsInput.required = true; smsInput.placeholder = "صُرفت 450 روبية بالبطاقة عند SWIGGY"; smsLabel.append(smsInput);
      const smsBtn = node("button", "حلّل وسجّل تلقائياً"); smsBtn.type = "submit";
      smsForm.append(smsLabel, smsBtn); content.append(smsForm);
      smsForm.addEventListener("submit", async (e) => {
        e.preventDefault(); smsBtn.disabled = true;
        try {
          const res = await api("/api/expenses/parse-sms", { method: "POST", body: JSON.stringify({ sms_text: smsInput.value }) });
          if (res.parsed) { await expensesPanel(); } else { errorMessage(res.message); smsBtn.disabled = false; }
        } catch (err) { errorMessage(err); smsBtn.disabled = false; }
      });

      content.append(node("h3", "آخر المعاملات"));
      for (const item of data.recent || []) {
        const row = node("div", undefined, "control-row");
        row.append(
          node("strong", `₹${Number(item.amount).toLocaleString("en-IN", {minimumFractionDigits: 2})} · ${item.merchant}`),
          node("small", darija(`${item.category} · ${item.date}`))
        );
        content.append(row);
      }
    } catch (err) { errorMessage(err); }
  }

  $("#open-device-connections")?.addEventListener("click", () => {
    const menu = document.querySelector(".account-menu");
    if (menu) menu.open = false;
    void devicesPanel();
  });
  $("#quick-implementation")?.addEventListener("click", implementationPanel);
  $("#quick-operations")?.addEventListener("click", operationsPanel);
  $("#quick-tasks")?.addEventListener("click", tasksPanel);
})();
