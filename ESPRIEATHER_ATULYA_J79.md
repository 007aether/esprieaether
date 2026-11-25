# ESPRIEATHER ← Atulya ← الدماغ المحلي (J79)

هادي وثيقة داخل المستودع كتلخّص اللي تزاد. الملاحظة ديال Obsidian كاينة فالـ vault الحقيقي:
`C:\Users\aether\ObsidianVault\EsprieAether\Services\atulya.md`.

## اللي كاين دابا

- **`ESPRIEATHER`** هو الاسم ديال المنتج؛ المسارات الداخلية `esprieaether/` باقية كيف ما هي.
- **`Atulya-Tantra`** مستورد كامل فـ `GITHUB_IMPORT/Atulya-Tantra` (MIT، 364 ملف، بلا `.git` ولا مفاتيح).
- السيرفر ديال Atulya شغّال فالخلفية على `http://127.0.0.1:8501`، والـ WebUI كيطلب كلمة سر `admin`.
- الدماغ ديالو مربوط بـ **`dolphin3`** عبر `http://127.0.0.1:31416/v1` (محلي 100%، بلا cloud، بلا مفتاح).
- القاعدة ديال اللغة مفعّلة: الجواب كيجي بالدارجة بحروف عربية. إثبات مباشر: `سلام، كيفاش ندير؟`.
- `START_ATULYA_TANTRA.cmd` كيضبط كلشي تلقائياً عند الإقلاع (provider + model + timeout + darija).
- `esprieaether/scripts/keep_alive.ps1` كيدير Atulya و15 خدمة أخرى، مع فحص `8501/api/health`؛ الـ shortcut ديال Startup (`start_esprieaether_247.ps1`) كيطلق الـ supervisor بوحدو. إثبات: `PASS up=15 down=0 restarted=0`.

## الروابط داخل الـ vault

- [[atulya|الملاحظة الجديدة فـ Obsidian]]
- [[local-brain]] · [[dolphin3]] · [[jarvis]] · [[ETAT_VERIFIE]] · [[_Index]]
- ملفات المستودع المرتبطة: `GITHUB_IMPORT/Atulya-Tantra`، `api/server.mjs`، `esprieaether/src/local_brain.py`.

## الحالة الصادقة

| الميزة | الحالة |
|---|---|
| السيرفر + الدماغ المحلي + الدارجة | `live_verified` (إثبات `/api/health` + `/api/chat`) |
| الإقلاع التلقائي والـ self-heal والـ PC شغّال | `live_verified` (سجل `keep_alive.log`) |
| الصوت / MCP / skills ديال Atulya | `implemented_unverified` |
| السحاب / القنوات الخارجية / PC عن بُعد / سيرفر برّا الـ PC | `needs_user_data` |
| 24/24 والـ PC مطفي | ما يمكنش محلياً؛ كيحتاج مضيف دائم — شوف `docs/ALWAYS_ON_REMOTE_TEMPLATE.md` |

## حدود مهمة

- ما كاين أي commit/push/upload، ولا تغيير فـ `.env` ديال ESPRIEATHER (الهاش باقي `DE9449DD…`).
- الملاحظات السحابية والقنوات الخارجية ما تفعّلوش بلا إذن صريح ومعطيات منك.
