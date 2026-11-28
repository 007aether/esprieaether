# openset-llm فـEsprieaether — تقرير محلي (J184)

## شنو لقينا فGitHub

- المستودع: `opensetlabs/openset-llm` — https://github.com/opensetlabs/openset-llm
- الرخصة: MIT؛ الإصدار الأخير: `v0.3.4` (27 نونبر 2026).
- ★2,240 و215 fork؛ تاريخ النشر 13 نونبر 2026، آخر push 27 نونبر 2026.
- الوصف من GitHub: «Fast local LLM inference on plain CPUs. No GPU, 8 GB of RAM. OpenAI-compatible server.»
- كيقول إنو محرك استدلال على CPU عادي، بلا GPU، بـAPI متوافق مع OpenAI على `/v1` (يعني أتوليا كيقدر يكلمو بنفس صيغة `:31416/v1`).
- التقنية: patches على PrismML llama.cpp، kernels خاصة بالأوزان ternary، speculative decoding، attention fused، و_resume_ ديال حلقات الأجنت.
- الموديل: `Bonsai-2-27B` ternary من PrismML، ملفو ~6.2GB بعد التحضير، والتنزيل ~7.3GB من Hugging Face.
- الأرقام المعلنة من طرف المشروع (ما قسناها عندنا): 17–20 tok/s على Ice Lake/AVX-512 بـ8 نوى و8GB RAM؛ وعلى AVX2 بلا AVX-512 (حالة Ryzen 5 4500U ديالنا) 6.1–7.7 tok/s بلا speculation و5.8–7.2 tok/s مع `./serve`.

## شنو نزّلنا وشنو ما درنا

- نزّلنا الكود (clone قراءة فقط) فـ`GITHUB_IMPORT/openset-llm/`، وهاد المجلد مستبعد من Git بـ`.gitignore`.
- قرينا `README.md` و`install.sh` وبيانات GitHub API، وخزّنا ملخص محلي فـ`GITHUB_IMPORT/Atulya-Tantra/tools/plugins/openset_llm.json`.
- أتوليا كجاوب دابا بـ`route=openset_llm` على «شنو هو openset-llm» و«كيفاش نستعمل openset-llm»، بلا نموذج وبلا شبكة.
- **ما ثبّتناش WSL2، وما نزّلتش الموديل (7.3GB)، وما بدّلتش إعدادات النموذج الحي ديال أتوليا.** هادشي كيحتاج موافقة صريحة منك.

## علاش ما كيخدمش دابا على هاد الجهاز

- `install.sh` كيقول `Linux only`؛ على Windows كيحتاج WSL2.
- `wsl --status` كيرجع «النظام الفرعي Windows لـLinux غير مثبّت».
- المعطيات المحلية: AMD Ryzen 5 4500U (6 نوى، Zen 2 / AVX2 بلا AVX-512)، RAM 15.4GB، قرص C فاضي 72.8GB. يعني كيدخل فالحد الأدنى (8GB RAM و~15GB قرص)، وكناخدو مسار الـ256-bit kernels، مع 10GB WSL2 موصى بها.

## حالة التثبيت بعد موافقة المالك (2026-11-28 ~07:20Z)

- `wsl --install` رجع بـtimeout فتحميل حزمة WSL 3.0.5 (مرة بالStore ومرة بـ`--web-download`)؛ الرسالة: «Le délai de l'opération est dépassé — Téléchargement en cours : Sous-système Windows pour Linux 3.0.5».
- فحص الميزات (dism، صلاحية مرتفعة): `VirtualMachinePlatform=Activé`، `Microsoft-Windows-Subsystem-Linux=Désactivé`، `Microsoft-Hyper-V-All=Désactivé`.
- فعّلنا `Microsoft-Windows-Subsystem-Linux` بـ`/NoRestart`؛ خرج بـ`EXIT=3010` يعني **كيتطلب إعادة تشغيل**.
- تحميل يدوي لحزمة `wsl.3.0.5.0.x64.msi` (367,788,032 بايت) من GitHub Releases كمل بـBITS، وتثبّتت بـ`msiexec /quiet /norestart` (EXIT=0)； `wsl --version` كيرجع 3.0.5.0.
- `.wslconfig` تكتب بـ`memory=10GB`, `processors=6`, `swap=2GB`, `localhostForwarding=true`.
- تحميل rootfs Ubuntu 24.04 (`ubuntu-24.04-server-cloudimg-amd64-root.tar.xz`, 227,213,232 بايت) كمل بـBITS، والـSHA256 مطابق تماماً (`ec6972af8ea2bd05c55299d204e5ae3f91769b84cfaec7395639d236a39f9a03`).
- `wsl --import Ubuntu2404` نجح، و`Ubuntu 24.04.5 LTS / x86_64` كيجاوب. **WSL خدم بلا إعادة تشغيل.**
- `.wslconfig` كيعطي 9948 MiB RAM، و`install.sh --check` أكّد مسار AVX2 (256-bit kernels) على Ryzen 5 4500U.
- المحرك الجاهز `openset-llm-linux-x86_64.tar.gz` (19,098,202 بايت) تّنزّل وتحقّق بـSHA256SUMS (`04f086c5…`)، وتّستخرج فـ`/root/.openset-llm/bin` داخل WSL.
- تحميل أوزان الموديل جاري بـBITS: `Ternary-Bonsai-2-27B-PTQ1_0.gguf` (~6GB) و`mtp-Qwen3.8-27B-Q4_0.gguf` (~1.4GB). هادشي كياخد ساعات على هاد الشبكة.
- `libgomp1` تثبّت يدوياً بـ`.deb` من أرشيف Ubuntu (SHA checksum غير مطلوب من dpkg؛ الحزمة رسمية)؛ `llama-cli --version` كيرجع `0.2.0-dev (commit e3de71522)` يعني المحرك شغّال فـWSL.
- تحميل الموديل كيديرو الآن `curl -C -` فعملية منفصلة، بـSHA256 متوقع `53107f53…` وحجم `5,946,648,928` بايت. التحميل المتوازي توقّف فـCDN، والمtp sidecar (1.37GB) ما كيتحمّلش: أول تشغيل غيكون بـ`no-mtp` (plain decoding) على AVX2.
- سكريبت `finalize_openset.ps1` جاهز: كينتظر التحميل، كيتحقق من الـSHA256، كينسخ الموديل فـWSL، كيشغّل `serve --no-webui --port 8080`، وكيتحقق من `/v1/models` و`chat/completions` قبل أي ربط مع أتوليا.
- اختبار بـGGUF عادي (`Dolphin3.0-Llama3.2-3B-Q4_K_M`) مع المحرك المرقّع: `llama-server` و`llama-cli` تعلّقو عند `llama threadpool init`، بلا خطأ واضح. يعني المحرك مخصّص لموديل Bonsai ternary؛ ما كيقبلش أي GGUF عادي. ما كاينش دليل حي على `:8080` دابا.
- `hf_xet` والتحميل المتوازي كيتعلّقو فهاد الشبكة كمان؛ التحميل الوحيد اللي كيصمد هو `curl -C -` (مستمر، قابل للاستئناف).
- تحسين جديد فالنظام: أتوليا كجاوب على «شنو حالة openset-llm» و`kifach kayn l 7al openset llm` بـ`route=openset_llm`، من ملف حالة محلي `esprieaether/state/openset_llm_install.json` + حجم الملف على القرص. الجواب كيعطي النسبة المئوية الحقيقية، وكَيقول بوضوح إن API ما تحققش حياً وإن موديل أتوليا ما تبدّلش. الاختبار الحي على :8501 نجح (6.2% فاللحظة).
- Docker مثبّت (29.9.3) لكن daemon موقف، وHyper-V موقوف؛ ما كاينش بديل جاهز بلا WSL.
- winget كيشوف `Canonical.Ubuntu.2404` (الإصدار 2404.0.5.0)؛ نستعملو باش ننزّل distro بلا Store.

## شنو غنوليو عندنا إلا وافقت

1. نثبّت WSL2 + Ubuntu 24.04، ونضبط `.wslconfig` بـ`memory=10GB` (عمل نظام بصريحة؛ ما نبدأش بلا موافقتك).
2. داخل WSL (مش `/mnt/c`): `install.sh --check` باش نأكدو مسار AVX2، من بعد `install.sh` (كيجلب الموديل ~7.3GB ويحضّرو) و`./serve --no-webui`.
3. الخدمة كتولي OpenAI-compatible فـ`http://127.0.0.1:8080/v1` بـ`model=openset-llm`. ما كاينش مفتاح حقيقي: `api_key=unused`.
4. نقدرو نوجّهو أتوليا للـendpoint هادا (بعد اختبار `curl /v1/models` وجواب واحد)، مع الاحتفاظ بـ`:31416/v1` كـfallback محلي.
5. اللي غيولي عندنا بالفعل: استدلال محلي بلا سحابة، بلا GPU، بلا مفتاح، بـagent-loop resume (إعادة قراءة أقل فالحلقات الطويلة)، و`--multi` إلا بغيت خدمة متعددة الطلبات.
6. اللي ما غيوليش مضمون: السرعة 17–20 tok/s (هدي لقياسات على CPU autre)، والجودة على الدارجة؛ كنختبرها قبل أي تغيير دائم فالموديل الافتراضي.

## تحقق الـ50 مشروع (نفس الجولة)

- GitHub API `/repos/{owner}/{repo}`، بتاريخ `2026-11-28T06:40:44+00:00` (دليل أقل من 7 أيام).
- 50/50 مستودع قابل للقراءة، 0 محذوف، 0 معطّل.
- 1 مؤرشف: `esengine/DeepSeek-Reasonix`.
- فرق النجوم مقارنة مع لقطة 06:07: +277؛ آخر push ما تبدّلش لأي مشروع.
- الدليل فـ`esprieaether/state/github_catalog_verification.json` (حالة محلية، ما دخلتش فالكوميت).
- وكيل التطوير: `cycle=1206`، `status=diagnosed`، `local_pct=100`، `error_count=0`، و3 خدمات تحت: `cloud_desktop:5001`، `ollama:11434`، `jarvis:8000`. تقريرو `github_projects_report.json` كيعني 20 مشروعاً من اختيار المالك (تاريخ 2026-11-27)، ومستقل على كاتالوج الـ50.
