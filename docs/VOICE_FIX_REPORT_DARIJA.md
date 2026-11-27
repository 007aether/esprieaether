# تقرير شامل: مشكل صوت أتوليا (J159)

## 1. شكوى المالك
قال المالك: «أتوليا عندو مشكل فالصوت، ما كنسمعوش، صلّح المشكل وعطيني تقرير شامل».

## 2. التشخيص — واش كاين، واش سمع، واش مسموع

### المسارات اللي فحصتهم
| المسار | الدور | الحالة |
|---|---|---|
| `webui/assistant.js` على `:8501` | الواجهة اللي كيولّد منها أتوليا الجواب والصوت فالتاب | هو المسار اللي كيهمّ؛ بعد الإصلاح كيخدم |
| `esprieaether/G0DM0D3/out/jarvis.html` على `:3860` | HUD كيعرض حالة الصوت، وما كان كيخرج منو أي صوت | ولا فيه كبسة تجربة صوت محلية |
| `esprieaether/voice_daemon.py` | دايمون صوت قديم — ميكروفون ← دماغ ← SAPI | مطفّى افتراضياً، الـlock فيه PID قديم `2464`، ما تلمّس |
| `esprieaether/src/local_voice.py` | نطق SAPI المحلي | غير مشغّال فهاد الدورة؛ ما كاينش صوت كيطلع منه دابا |

### الأسباب اللي لقيتهم فمسار المتصفح
1. **سياسة Autoplay:** Chrome كيمنع `audio.play()` قبل أول ضغطة/تفعيل من المستخدم. الجواب الأول كان كيضيع بصمت.
2. **`AudioContext` suspended:** `playBlob` كان كيخلق `AudioContext`، كيعاود `resume()`، وكيمرّر الصوت عبر `createMediaElementSource`. على Chrome/Windows هادشي كيقطع الصوت حتى واخا التوليد ناجح.
3. **ما كاينش صوت `ar-MA`:** الحاسوب فيه غير `Microsoft Zira Desktop` بـ`en-US`. عند سقوط التوليد المحلي، `speakWithBrowser` كان كيختار `ar-MA` اللي ما كاينة، فكيبقى صامت.
4. **`voice_inbox.jsonl` ما كيعطيش دليل حالي:** 216 سطر نطق، آخر واحد من `2026-11-25`، ومن بعدو `empty_transcript` بالجملة. يعني الإثبات القديم ما كيدعمش أن الصوت كيطلع دابا.

## 3. الإصلاحات اللي تّطبّقات

### أتوليا WebUI — `GITHUB_IMPORT/Atulya-Tantra/webui/assistant.js`
- `soundUnlocked` + `unlockSound()`: أول `pointerdown` ولا `keydown` كيفتح الصوت، وكيطلق الجواب اللي كان مؤجّل (`pendingSpeech`) بدل ما يضيع.
- `playBlob()`: تشغيل مباشر بـ`new Audio(url)`؛ ما بقاش `AudioContext`، ولا `resume().then()`، ولا `createMediaElementSource`. أي فشل كيبان كـ`playback blocked` عوض الصمت.
- `preferMaleVoice()`: كيلاقي أي صوت مثبّت (`matching[0] || voices[0]`) قبل ما يبقى بلا صوت، خصوصاً فاش `ar-MA` غائب.
- `/api/voice/synthesize` باقي loopback، بلا URL خارجي ولا مفتاح.
- أثر جانبي تّصلح: كود `unlockSound` نُقّل قبل `speakWithBrowser` باش ما يدخلش فالمقطع اللي كيختبره `tests/voice/test_web_speech_split.py` فـNode بلا DOM.

### HUD — `esprieaether/G0DM0D3/out/jarvis.html`
- كبسة «شغّل جملة» فبطاقة الصوت، بضغطة صريحة من المالك.
- `fetch("/local-voice/say?text=…&language=auto")` بـGET (بلا POST ولا onclick، حفاظاً على قاعدة HUD) كيجيب WAV محلي، و`new Audio(url).play()` كيلعبّو فنفس التاب. الحالة كتكتب فـ`voiceTestResult` بلا ادّعاء أنك سمعتها.

### خدمة صوت محلية — `esprieaether/src/atulya_voice.py`
- `:5105`، loopback فقط. كتستعمل نفس موديل Supertonic int8 الموجود محلياً، بلا سحابة ولا مفتاح ولا `subprocess`.
- `GET /say?text=…&language=auto` كيرجّع `audio/wav` (و`POST /say` باقي مدعوم للتوافق)، مع cache حسب بصمة النص/اللغة.
- `GET /health` كيقول `live_verified` غير يلا الموديل جاهز.
- `GET /evidence` وكتابة `state/voice_output_evidence.json` كيعطو دليل العينة: `status=implemented_unverified` و`playback=owner_confirmation_pending` (ما كنقولوش «سمعت» بلا تأكيد منك).

### الربط والمراقبة
- `esprieaether/scripts/serve_g0dm0d3.mjs`: `/local-voice/*` كيترحّل لـ`:5105` على نفس الأصل — ما كاينش CORS ولا طلب خارجي.
- `esprieaether/scripts/keep_alive.ps1`: خدمة `atulya-voice` على `:5105` ولا تحت المراقبة مع فحص `/health`.
- `docs/V2_RELEASE.md`: سجل J159 مضاف.

## 4. الدليل الحي (محلي، بلا خدمة خارجية)
- `/health` على `:5105` و`/local-voice/health` على `:3860`: `ok=true`, `engine=supertonic-3-int8-local`.
- `GET /local-voice/say?text=…&language=auto` بالدارجة عبر بروكسي HUD: `200`, `audio/wav`, `252446` بايت، `magic=RIFF`.
- تحليل العينة: 44100Hz، 2.86s، `peak=13093`, `rms=1813.3`, `nonSilent=true`.
- الواجهة المحمّلة فعلاً: `assistant.js` على `:8501` فيه `soundUnlocked` و`playback blocked`؛ `jarvis.html` على `:3860` فيه `voiceTestBtn`.
- تشغيل العينة عبر `System.Media.SoundPlayer` محلياً رجّع `playback_api=ok` (هادشي كثبت أن مسار السبيكرات والـ API ديال التشغيل كيخدم، ماشي أنك نتا سمعتها).
- `state/voice_output_evidence.json`: `implemented_unverified` + `owner_confirmation_pending`.

## 5. الجولات والاختبارات (آخر جولة فعلية)
- **Node:** `1110/1110`، `fail=0`، خرج `0`.
- **Python (esprieaether):** `380` اختبار، `OK`.
- **Atulya pytest:** `591 passed`، `3 skipped`، `27 subtests passed`.
- **المانيفست:** `836` ملف، الإصدار `2.1.6`، والبصمات مطابقة للملفات.
- **اختبارات J159 المستهدفة:** Node `59/59` (منها 11 الاختبارات اللي كانوا كيشكّو فـHUD)، Python `9/9` للخدمة الجديدة.
- تّصلحت مهلة `tests/core/test_optional_voice_import.py` من 30 لـ90 ثانية لأن استيراد `atulya.server` بلا numpy كياخد ~28 ثانية، و30 كانت كتفشل فالضغط بلا ما يبدّل المتن المُختبر.
- وفي جولة وسيطة، 122 اختبار Node فشلو غير لأن `manifest.json` كان قديم بعد تعديل ملف اختبار؛ تعاد توليد المانيفست ورجعنا `1110/1110`. ما خفّيناش ولا تجاهلنا أي فشل.

## 6. اللي ما تّدارش، وعلاش
- ما فتحتش الميكروفون، وما شغّلتش `voice_daemon.py`، وما لمستش الـlock القديم: الدايمون مطفّى افتراضياً بقرار سابق.
- ما كاين أي SMS/call، ولا مستلم، ولا لمس لـ`C:\Program Files (x86)\panda_android\touping.exe`.
- ما تكتبش أي مفتاح فـ`.env`، ولا تركّب حزمة من مستودع مجهول.
- ما كادّعيش أنك سمعت الصوت: هادشي كيتطلب منك كبسة واحدة وتأكيد من سمعك.

## 7. اللي كيتطلب منك دابا
1. أعد تحميل `:3860/jarvis.html` (أو `:8501`) باش تاخد الكود الجديد.
2. اضغط «شغّل جملة» فبطاقة الصوت، ولا أرسل جواب فأتوليا. أول ضغطة كتفكّ قفل المتصفح.
3. قول «سمعتها» ولا «ما سمعتش»؛ إلا ما سمعتش كنكمّل التشخيص على الصوت اللي كيطلع من السبيكرات بلا ما نخمّن.
