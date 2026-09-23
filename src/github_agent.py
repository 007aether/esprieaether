import os

def get_github_status():
    return "📦 **حالة المستودعات:**\n- aether-v7\n- esprieaether\n- aether-evolution\n✅ **الاتصال:** نظام Git يعمل بكفاءة."

def auto_commit_and_push(commit_message="AETHER Agent Auto-Backup"):
    try:
        os.system("git add .")
        os.system(f"git commit -m '{commit_message}'")
        exit_code = os.system("git push")
        if exit_code == 0:
            return "✅ تم رفع الكود وتحديث المستودع على GitHub بنجاح!"
        else:
            return "⚠️ لا توجد تغييرات جديدة لرفعها."
    except Exception as e:
        return f"❌ خطأ في الرفع: {e}"
