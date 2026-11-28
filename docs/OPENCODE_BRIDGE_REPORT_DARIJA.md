# تقرير: ربط أتوليا بـOpenCode والجواب السريع (J174)

## 1. اللي طلبتيه
قلتي: « BERITO WIWALI SERI3 ET IWALI IFEHAM KOLECHI BEHAAK NETA DABA MOMEKIN DIT LIH 3AKLAK OU ITISAL BIK MOBACHIR ».
فهمتها هكاك، واخترتي «كلشي مع بعض»، واخترتي للربط «1+2» (ملف مشترك + جواب جاهز)، وقلتي «نسيان» للمنبه.

## 2. اللي تّدار
- **جواب سريع بلا نموذج**: «من أنت؟» و«شنو تقدر تدير؟» ولاو كيجييو من ملف محلي فـ milliseconds، بالدارجة، بلا سحابة وبلا اختراع حالة.
- **إقرار فوري بالصوت**: عند «سول أوبن كود: …» كينطق أتوليا «كنسجّل سؤالك.» فوراً حتى قبل ما يقرّر النموذج.
- **ملف مشترك** فـ`esprieaether/state/opencode_bridge/` (داخل `state/` اللي فـgitignore، ما كيدخلش المستودع):
  - `questions.jsonl`: أتوليا كيكتب فيه السؤال بـid `q-…` ووقت و`status=pending`.
  - `answers.jsonl`: أنا (OpenCode) ككتب فيه الجواب بـ`answeredBy=opencode` و`question_id`.
- **جواب جاهز صادق**: «شنو قال أوبن كود؟» كيقرا غير `answers.jsonl`؛ إلا ما كاينش جواب كيقول «ما جاتنيش أي إجابة من OpenCode دابا». ما كيخترعش.
- **تنظيف**: السؤال والجواب كيدوزو من نفس مرشّح `pc_gateway._scrub`، فما كيتكتبش أي `api_key=...` فالملفات.

## 3. كيفاش كيستعمل
1. قول لأتوليا: `سول أوبن كود: واش الخدمة شغّالة؟`
2. من هنا (OpenCode) شغّل:
   - `python esprieaether/scripts/opencode_bridge.py pending`
   - `python esprieaether/scripts/opencode_bridge.py answer q-xxxxxxxx "الجواب..."`
3. رجّع قول لأتوليا: `شنو قال أوبن كود؟` → كيعطيك الجواب اللي فالملف، ولا جواب صادق إلا ما كاينش.

## 4. اللي ما تّدارش (بقرار منك)
- ما حطّيتش مؤقت ولا automation باش يقرا الصندوق تلقائياً؛ قلت «stop timer»، فالقراءة كتكون غير إلا طلبتيها هنا.
- ما كاين أي SMS/call ولا لمس جهاز GSM، ولا لمس `touping.exe`، ولا كتابة فـ`.env`.
- ما كاين أي جواب كيدّعي حالة حية بلا دليل من ملف ولا من أداة.

## 5. الاختبارات
- Atulya: `tests/plugins/test_local_bridge.py` 8/8، `tests/core/test_darija_fillers.py` 6/6، `tests/plugins/test_pc_intents.py` 8/8، web_intents 18/27 subtests → المجموع 32 passed + 27 subtests فالجولة المستهدفة.
- Esprieaether: `tests/test_opencode_bridge.py` 5/5.
- الجولات الكاملة والدليل الحي مذكورين فآخر تحديث فـ`V2_RELEASE.md`.
