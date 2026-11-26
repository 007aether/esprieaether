# مخطط هندسة عكسية — EsprieAether

## الملخص
حلّلنا 7960 ملفات محلية قراءةً فقط، بلا أي تعديل فالكود المُحلَّل.
نقاط الدخول: 40 • TODO/FIXME: 40.

## الأدلة
- `_add_bot_funcs.py` • error_pattern: 43: except Exception:
- `_add_bot_funcs.py` • error_pattern: 59: raise FileNotFoundError
- `_add_bot_funcs.py` • error_pattern: 67: except Exception as e:
- `_fix_bot_final.py` • error_pattern: 41: except Exception:
- `_fix_bot_final.py` • error_pattern: 57: raise FileNotFoundError
- `_fix_bot_final.py` • error_pattern: 65: except Exception as e:
- `esprieaether.py` • error_pattern: 78: except Exception as e:
- `esprieaether.py` • entrypoint: 82: def main():
- `esprieaether.py` • error_pattern: 111: except ValueError:
- `esprieaether.py` • todo: 145: print(Fore.CYAN + f"\n📊 Tasks: TODO:{todo} DOING:{doing} DONE:{done}\n")

## شنو ناقص
- السلوك وقت التشغيل والمدخلات الحقيقية ما تحققوش.
- المسارات الحرجة محتاجة اختبارات قبل أي تطوير.

## مقترحات التطوير
- توثيق نقاط الدخول وعقودها قبل لمس التنفيذ.
- تحويل TODO/FIXME إلى اختبارات صغيرة قابلة للتحقق.

