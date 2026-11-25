# ربط SUNNAVOK مع Obsidian وHermes

## مجلد الـvault
افتح هذا المجلد نفسه في Obsidian كـvault:

`C:\Users\aether\Documents\Codex\2026-11-04\https-chatgpt-com-g-g-p\outputs\SUNNAVOK`

في Obsidian اختر **Open folder as vault** أو **Open folder as vault / Open folder** حسب لغة الواجهة، ثم حدد المجلد أعلاه. لا تختَر مجلد `sources`.

## ربط Hermes
1. افتح مساحة العمل أو المشروع في Hermes على مجلد SUNNAVOK نفسه.
2. فعّل مهارة Obsidian المضمنة إن ظهرت ضمن مهارات Hermes.
3. عيّن متغير البيئة `OBSIDIAN_VAULT_PATH` إلى مسار الـvault أعلاه من إعدادات Hermes. إذا كانت نسختك تعتمد ملف إعدادات، أضف السطر التالي إلى إعداد Hermes المحلي:

   `OBSIDIAN_VAULT_PATH=C:\Users\aether\Documents\Codex\2026-11-04\https-chatgpt-com-g-g-p\outputs\SUNNAVOK`

4. اطلب من Hermes فتح `00_HOME_SUNNAVOK.md` و`.hermes.md` قبل تسجيل أي تحديث.

هذا يجهز نفس المجلد ليُفتح في التطبيقين؛ لا يعني أن التطبيقات رُبطت أو أن إعداد Hermes المحلي تغيّر تلقائياً.
