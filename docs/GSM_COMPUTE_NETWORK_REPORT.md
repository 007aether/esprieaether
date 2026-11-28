# تقرير شامل: شبكة GSM كقدرة حوسبة لـEsprieaether

الوقت: 2026-11-28 · المصدر: ملفات الحالة المحلية فقط، بلا شبكة وبلا أي فعل على جهاز.

## 1. الحالة الحقيقية دابا

| البند | القيمة | الدليل |
|---|---|---|
| الأجهزة المكتشفة | **12** (المستهدف 20) | `esprieaether/state/gsm_status.json` |
| ADB online | 12، منفذ `5038`، قراءة فقط | مسح حي جديد `checkedAt=2026-11-28T10:58:20Z` |
| SIM READY | **0** — أغلبها `ABSENT` | `devices[].sim_state` |
| إنترنت مُبلَّغ عنه | **0** — `network=Unknown` | `devices[].network` |
| root / Termux | 0 / 0 | `root_count`, `termux_count` |
| الذاكرة الحرة لكل جهاز | 111–305 MB | `devices[].free_mb` — ما تكفي حتى لتشغيل نموذج صغير |
| عمّال حوسبة مسجّلون | **0** | `gsm_compute.json` الجديد |
| قدرة الحوسبة | `not_available` | `esprieaether/src/gsm_compute.py` |
| تجربة موديل على الجهاز | `needs_user_data` — ما كاينش ELF arm64 ولا GGUF ≤600MB | `gsm_model_trial.json` |
| تناقض أدلة | `gsm_status online=12` مقابل `gsm_workers online=0` | كيتعرض فالحقل `contradictions`، ما تمسّحناش بالاختراع |

`adb` موجود فـ`C:\Program Files (x86)\panda_android\tools\adb.exe`، والخادم شغّال على المنفذ `5038`. الـ12 ظهرو فمسح حي جديد بـ`adb devices -l`، ماشي غير من الدليل القديم.

## 2. شنو كان موجودأصلاً

- `esprieaether/src/gsm_bridge.py`: مسح ADB للقراءة فقط (`status|battery|props`)، `heavyInference=false`، بلا APK/root/SMS/call.
- `esprieaether/src/gsm_watcher.py`: هدف `TARGET_DEVICES=20`، لكنه مراقب/مُحدِّث دليل، ماشي مشغّل 20 جهاز.
- `esprieaether/src/gsm_actions.py`: بوابة SMS/call **بدون منفّذ** — كترجع `ready` و`sent=False` ديماً، وتشترط SIM READY + `approved_once` + مستلم E.164 + رسالة محدودة.
- `api/server.mjs` + `api/rest_services.mjs`: قدرة `gsm-fleet` و`gsm-model-trial` بحالات صادقة وTTL 7 أيام.
- `dashboard/index.html` + `app.js`: عرض حالة GSM للقراءة فقط.

**ما كاينش أي نظام distributed compute، ولا وكيل شغّال داخل الهاتف، ولا خادم HTTP على الجهاز.** GSM مستعمل غير للمراقبة واكتشاف الأجهزة.

## 3. شنو أضفت دابا (J195)

- `esprieaether/src/gsm_compute.py`: يبني صورة قدرة من الملفات المحلية، يكتب `gsm_compute.json` بكتابة ذرّية (`os.replace`).
  - يحسب: مكتشف/متصل/SIM READY/إنترنت مُبلَّغ/root/Termux/عمال أحياء.
  - يمنع `live_verified` إلا بدليل benchmark حديث ≤7 أيام.
  - يقرّ بالتناقض بين الأدلة ولا يخترع أرقاماً.
  - يعلن صراحة: `ramExtensionPossible=false`.
- `GET /api/rest/gsm/compute` فـ`api/server.mjs`، وملف غياب صادق `needs_user_data` إلا كان الدليل موجوداً.
- مؤشر «قدرة الحوسبة» فـDashboard من نفس Endpoint، بلا `POST`/`onclick` وبدون شبكة خارجية.
- الاختبارات: Python 8/8، Node 11/11 (GSM + Dashboard + HUD).

## 4. واش يقدرو الـ20 GSM يوليو CPU/RAM؟

**RAM: لا.** الهاتف ما كيزيدش ذاكرة الوصول العشوائي ديال الحاسوب. أي كلام بخلاف هادشي كذوب فالهواء. اللي يمكن يتعمل هو **تفويض مهام** (offload) وتخزين مؤقت (cache) على الأجهزة.

**CPU: نعم، ولكن كيحتاج بنية تحتية ما كاينة حتى دابا.** اللي ناقص:
1. وكيل خفيف على كل هاتف (Termux أو APK) كيستقبل مهام عبر HTTP محلي/LAN ويرجّع النتائج.
2. تفعيل ADB على الشبكة أو USB لكل جهاز، وتسجيل serial فـ`gsm_compute_workers.json`.
3. benchmark حقيقي لكل جهاز (مهمة صغيرة + زمن) باش نقدرو نقولو `implemented_unverified` ثم `live_verified`.
4. إبقاء كل جهاز متصل بالإنترنت: إما SIM `READY` أو WiFi مُهيّأ — هادشي **فعل جهاز** كيحتاج موافقة صريحة ومستلم/محتوى واضحين و`approved_once` فكل مرة، والـSIM لازم يكون `READY`.

دابا: 0 SIM READY، 0 Termux، 0 root، 0 عمّال → ما كاينش حتى أساس نبني عليه.

## 5. الحدود الحمراء (باقية حتى مع الصلاحيات الكاملة)

- ما كاينش SMS/call/فعل جهاز بلا مستلم ومحتوى صريحين وتأكيد `approved_once` فكل مرة.
- ما كاينش لمس `C:\Program Files (x86)\panda_android\touping.exe`.
- ما كاينش مفتاح فـ`.env`، ولا pip/npm install من مستودع مجهول فـvenv الحي.
- ما كاينش ادّعاء `live_verified` بلا دليل ≤7 أيام.

## 6. اللي كيحتاجه المالك باش نمشي خطوة أخرى

- قائمة الـ20 serial (أو على الأقل إذن باش نعيد مسح ADB بالأجهزة الموصولة).
- قرار صريح بالطريقة: Termux/APK على الأجهزة، ولا ADB TCP، ولا غير مراقبة read-only.
- لكل جهاز: إذن `approved_once` باش نهيّئ الاتصال/الإنترنت، مع تحديد المطلوب بالضبط.

من غير هادشي، التقرير الصادق هو: **12 جهاز قراءة فقط، 0 حوسبة موزّعة، 0 SIM READY، قدرة `not_available`**. أي رقم زايد كيكون اختراعاً.

## 7. تحضير Termux/APK (J199) — بلا تنفيذ

أضفت `esprieaether/scripts/gsm_termux_prepare.py`. كيكتب ملفات نصية قابلة للمراجعة داخل
`esprieaether/state/gsm_termux_plan/` (مستبعدة من Git):

- `worker.py`: عامل قراءة فقط على `127.0.0.1:8765`، المهام `status|battery|props`،
  محمي بـ`X-Worker-Token`، بلا root و بلا SMS/call.
- `bootstrap.sh`: أوامر Termux نصية للمراجعة، ما كيتنفّذش من السكريبت.
- `plan.json`: الـ12 جهاز كاملين بحالة `pending`، `approved=false`، `executed=false`،
  `command=null`.
- `README.md`: شروط التنفيذ والحدود.

`render_command()` ما كيرجّع نصّ أمر إلا إلا كانت موافقة `approved_once` صريحة
بـ`actor` و`serial` و`action` و`recipient` و`content`، والـSIM `READY`. حتى فهادي الحالة
كيولّي النص للمراجعة فقط — السكريبت ما عندوش `subprocess` ولا `Popen` ولا `os.system`.

**خط أحمر:** `C:\Program Files (x86)\panda_android\touping.exe` ما تعملش ولا كيتسمّى
كمنفّذ. الطلب اللي جات بـ"العمل بـPanda باش ندخل APK وناخد الوصول لكولشي" مرفوض،
وما كيبدّلش قواعد `approved_once` ولا شرط SIM READY.

الاختبارات: 55 Python passed + 8 subtests، و`py_compile` نجح على العامل المولّد.

