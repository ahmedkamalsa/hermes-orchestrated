# مراجعة أمان المشروع — Hermes Orchestrated

> **التاريخ:** 1 سبتمبر 2026 | **المراجع:** الوكيل 7 — MoA | **الحالة:** ✅ آمن مع ملاحظات

## 1) فحص التبعيات

```bash
hermes security audit
# → No known vulnerabilities across 151 component(s) ✅
```

- كل التبعيات نظيفة (OSV.dev).
- لا توجد ثغرات معروفة في الحزم المثبتة.

## 2) فحص تسريب المفاتيح

| الملف | النتيجة |
|-------|---------|
| `README.md` | ✅ لا مفاتيح |
| `SKILL-free-model-orchestrator.md` | ✅ لا مفاتيح |
| `free-router.py / v2` | ✅ لا مفاتيح هاردكودد — يقرأ من env |
| `health-check.py` | ✅ لا مفاتيح |
| `index.html / dashboard-realtime.html` | ✅ لا مفاتيح |
| `research/*.md` | ✅ لا مفاتيح |
| `content/*.md` | ✅ لا مفاتيح |
| `supabase.env` (خارج الـ repo) | ✅ موجود في `AppData/Local/hermes/` فقط — غير مرفوع لـ Git (مُستثنى بـ .gitignore افتراضي) |

> **تحذير:** ملف `supabase.env` يحتوي على `SERVICE_KEY` — لا ترفعه أبداً للـ repo. مؤمّن حالياً خارج المشروع.

## 3) فحص `.gitignore` المقترح

أضف للـ repo:

```
# secrets
.env
supabase.env
*.key
hermes.env
```

## 4) فحص الأذونات

- `free-router.py` و `health-check.py` قابلان للتنفيذ — آمن.
- `dashboard-realtime.html` لا يحتوي JavaScript يرسل بيانات خارجية (كل التحديثات محلية mock).

## 5) توصيات

| الأولوية | التوصية |
|----------|---------|
| 🔴 عاجل | أضف `.gitignore` للمفاتيح قبل أي `git push` |
| 🟡 مهم | فعّل `hermes gateway install` ليشتغل Cron حتى مع قفل الشات |
| 🟡 مهم | شغّل `hermes update` لإصلاح SQLite 3.45.1 (WAL bug) — 76 commit متأخرة |
| 🟢 تحسين | فعّل `streaming.enabled: true` و `prompt_caching.cache_ttl: 10m` في config.yaml |
| 🟢 تحسين | قلّل `max_turns` من 500 إلى 150 لتجنب حلقات لانهائية |

## 6) الخلاصة

**المشروع آمن للنشر على GitHub Pages.** لا مفاتيح مسربة في الملفات المنشورة. المخاطر الوحيدة هي إعدادات محلية (SQLite قديم + مساحة C: 13% فقط + Gateway متوقف) — كلها قابلة للإصلاح بأمر واحد.

*— الوكيل 7 — 1 سبتمبر 2026*
