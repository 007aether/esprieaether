# مواصفة ربط الروبوت بـPanda — J202

الحالة: **مسوّدة للمراجعة فقط**. ما كاين أي تنفيذ، أي اتصال بـPanda، ولا أي فعل على جهاز.

## 1. خطوط حمراء (ما كيتجاوزوش حتى بصلاحيات كاملة)
- `C:\Program Files (x86)\panda_android\touping.exe`: ممنوع. ما كيتسمّى ولا كيتستعمل كمنفّذ.
- ما كاينش وضع «الوصول لكولشي». كل عملية مقيدة بقائمة مسموحة وسجل تدقيق.
- كل فعل جهاز كيحتاج: serial واضح + SIM `READY` + مستلم ومحتوى صريحين + `approved_once` فكل مرة.
- ما كاينش SMS/call/APK/root/ADB TCP بلا هاد الشروط.
- التلفون ما كيزيدش RAM الحاسوب؛ التفويض ممكن، التوسيع الذاكري مستحيل.

## 2. الواجهة المطلوبة من الروبوت (لازم تعطيها قبل أي تنفيذ)
| الحقل | القيمة المطلوبة |
|---|---|
| المنفّذ | اسم الملف/الـAPI اللي غايجيب الروبوت (ماشي `touping.exe`) |
| البروتوكول | HTTP loopback `:PORT` ولا stdin/stdout |
| الصحة | `GET /health` → `{"ok": true}` |
| الأجهزة | `GET /v1/devices` → قائمة serials وحالات SIM |
| الأوامر | قائمة الأوامر المسموحة بالضبط، مع مثال لكل واحد |
| المصادقة | token محلي، ما كيخرجش من الجهاز |

ما كاينش أي افتراض على هاد الحقول دابا. أي قيمة غايبة = `needs_user_data`.

## 3. العقد بين أتوليا والروبوت
- أتوليا كيرسل غير `POST /v1/command` بـ`{serial, action, recipient, content, approvalId}`.
- الروبوت كيرجّع `{ok, executed, result, auditId}`؛ `executed` كيبقى `false` إلا بجواب حقيقي من الجهاز.
- كل طلب كيتسجّل فـ`esprieaether/state/action_audit.jsonl` مع scrub للأسرار.
- أي رفض كيولّي `denied` ولا `not_available`، ما كيتخضرش.

## 4. مخطط الموافقة (موجود أصلاً فـ`action_request.py`)
```json
{
  "state": "approved_once",
  "actor": "owner",
  "serial": "<serial>",
  "action": "gsm_termux_bootstrap",
  "recipient": "<وصف صريح>",
  "content": "<شنو بالضبط>",
  "approvedAt": "<ISO>"
}
```
`finish()` كيتطلب `approved_once` قبل `executed`. الاستهلاك مرة واحدة.

## 5. الحالة الحقيقية دابا
12 جهاز ADB للقراءة فقط · SIM READY: 0 · إنترنت: 0 · root/Termux: 0 · قدرة الحوسبة `not_available`.
خطة Termux محضّرة فـ`esprieaether/state/gsm_termux_plan/` بـ12 `pending` و0 تنفيذ.
لا يوجد روبوت ولا منفّذ Panda موصول فالنظام.

## 6. اللي كيحتاج المالك باش نكمّل
1. اسم المنفّذ/الـAPI والمنفذ والبروتوكول.
2. قائمة الأوامر المسموحة.
3. مثال واحد: serial +command +المستلم والمحتوى + SIM READY.

من غير هادشي، التقرير الصادق هو `needs_user_data`، وما كنخترعش واجهة.
