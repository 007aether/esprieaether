# 🖥️ نضام الويندوز مع مشروعنا — Windows Alignment Report

**المؤلف:** ESPRIEAETHER  
**التاريخ:** 2026-10-24  
**الهدف:** تكييف البيئة (الويندوز) مع مشروع الذكاء المحلي المستقل (EsprieAether).

---

## 1. الحالة الحالية

### ما هو متاح
- ✅ **النظام:** Windows 11
- ✅ **Python:** 3.14.9 (مثبت في `C:\Users\ESPRIEAETHER\AppData\Local\Python\pythoncore-3.15-64`)
- ✅ **Node/v26.7.0:** للواجهة البرممجة (عند الحاجة)
- ✅ **مثبت عبر pip:** 30+ حزمة (الأكثر أهمية): fastapi, Flask, pydantic, ollama, python-telegram-bot, loguru, letta, psutil, gitpython, watchdog، خلف ذلك.
- ✅ **التراخيص:** JWT, cryptography, open-telemetry, prometheus (اختياري)
- ✅ **المساحة:** 20GB من 121GB متوفرة — كافية للتطوير والنشر
- ✅ **الروابط:** `http://localhost:5000` (لوحة التحكم)، `http://localhost:11434` (JARVIS/Ollama)

### ما يحتاج إلى اهتمام (الفجوات)

| الفجوة | التأثير | الحل |
|--------|--------|-------|
| `requirements.txt` غير متوافق | `fastapi 0.141.1` (في الملف) مقابل `0.161.0` (المثبت فعلياً) | تحديث `requirements.txt` أو تثبيت الإصدار المطابق |
| `node_modules` غير موجود | الواجهة الأمامية (إذا غيّرتها) | `npm install` عند الحاجة |
| لا حاوية | مشكلة التوزيع | `Docker`/`docker-compose` (اختياري) |
| `.env` مكفي | TELEGRAM_BOT_TOKEN، TELEGRAM_CHAT_ID فقط | إضافة متغيرات trade-cycle، OAuth، webhook |
| لا خدمة عملية | النظام يعمل يدويًا لمرة واحدة | إنشاء `AetherStartup.ps1`/`.bat` للتشغيل التلقائي عند restart |

---

## 2. خارطة النضام (ملفات المحاذاة / مستويات اللائحة)

| المستوى | العنصر | الحالة الحالية | الإجراء المطلوب |
|----------|--------|----------------|-----------------|
| **1 (مهم)** | Python & pip | 3.14.9 / 26.2.2 ✅ | لا شيء (تأكيد التثبيت) |
| **2 (مهم)** | requirements.txt | غير متوافق | تحديث الإصدارات |
| **3 (مهم)** | متغيرات البيئة | مكتملة (TELEGRAM_*) | إضافة trade/webhook/OAUTH |
| **4 (مهم)** | start_all_services | اليدوي | التهيئة التلقائية (PS1/BAT) |
| **5 (مهم)** | Auto-start على startup | خطأ | إنشاء رابط Shortcut في Startup |
| **6 (مهم)** | العثور على النظام | في Desktop | تثبيت في Program Files / AppData |
| **7 (مهم)** | حسابات المستخدم | تعمل مع الاسم الحالي | التحقق من إذن التشغيل |
| **8 (متوسط)** | Log rotation | دليل `data/logs` صغير | ضبط-size logrotate |
| **9 (متوسط)** | عمليات الخلفية | تنتهي عند إغلاق فتحة الطرفية | إعداد Background (start_new_session) |
| **10 (متوسط)** | شبكة الوصلات | Ollama مُحدد | التحقق من `http://localhost:11434` |

---

## 3. تكوين الويندوز (الملفات المهمة)

### 3.1 متغيرات البيئة (System Environment Variables)
- `PATH` يجب أن يتضمن:
  - `C:\Users\ESPRIEAETHER\AppData\Local\Python\pythoncore-3.15-64\Scripts`
  - `C:\Program Files\Git\bin` (Git Bash)
- `PYTHONIOENCODING=utf-8`
- `PYTHONUTF8=1`

### 3.2 ملف التشغيل (Startup Script)
```powershell
# AetherStartup.ps1
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"
cd "C:\Users\ESPRIEAETHER\Desktop\esprieaether"
python src/autonome_evolve.py --daemon
python src/bot.py
python src/ai_router.py
python work/agents/trade_cycle/loop.py --daemon
```
(يمكن تخزينه في `C:\Users\ESPRIEAETHER\Desktop\AetherStartup.ps1`، وإضافة المفتاح للحافلة: `shell:startup`)

### 3.3 اختصار تشغيل التلقائي (Startup Shortcut)
- إنشاء رابط `AetherStartup.bat` في `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup` ليدخل مع قرب تشغيل النظام.

---

## 4. افتراضي لـ Windows (أفضل الممارسات)

| الممارسة | التفاصيل |
|----------|-----------|
| `set +m` والـ `start_new_session` | منع توقف العمليات عند غلق الطرفية |
| `nohup` أو `powershell -NoExit` | واجهة أمامية للعمليات الخلفية |
| log rotation | الدليل `data/logs` يحتاج دوران (حجم الحد) |
| جدار الحماية (Windows Defender) | السماح لـ Python وOllama و Tor (حسب الحاجة) |
| Update تلقائية | نظام التشغيل والبرامج (أمان) |

---

## 5. خطة التنفيذ (خطوات التنفيذ)

1. **تحديث `requirements.txt`**: مطابقة الإصدارات المثبتة (fastapi 0.161.0، ollama 0.6.3، إلخ).
2. **إضافة متغيرات البيئة** في `.env`: trade-cycle، OAuth، webhook.
3. **إنشاء `AetherStartup.ps1`** ووضع رابط التشغيل التلقائي (Startup).
4. **إضافة التوثيق**: `README.md`، `STATUS_WINDOWS.md`، `docs/`.
5. **الاختبار**: `python work/agents/trade_cycle/loop.py --once`، `python src/autonome_evolve.py --cycle 1`.
6. **الانتشار**: نسخ الملفات في مكان ثابت (AppData أو Program Files)، مع تأكيد الحقوق والصلاحيات.

---

## 6. ملخص مختصر للودم (الفر_tags)
- ✅ **متاح**: Python 3.14.9، pip 26.2.2، 30+ حزمة، 20GB مساحة، ollama/جاري.
- ⚠️ **غير متوافق**: `requirements.txt` (fastapi 0.141.1 vs 0.161.0).
- 🔧 **مطلوب**: متغيرات `.env`، script تشغيل تلقائي (Startup)، توثيق الواجهة.

---
**الملف:** `windows_alignment_report.md` — لربط النظام بالبيئة المناسبة
