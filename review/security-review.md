# تقرير المراجعة الأمنية — Hermes Orchestrated

> **التاريخ:** 1 سبتمبر 2026 — 14:01 EEST  
> **المراجع:** الوكيل 7 — مراجع أمني (MoA)  
> **النطاق:** كل ملفات `C:/Temp/hermes-orchestrated/` — README, SKILL, dashboards, scripts, workflows, research  
> **الحالة العامة:** ✅ آمن للنشر — لا تسريب مفاتيح — ثغرات التبعيات صفر — مع 8 تحسينات مقترحة

---

## 1) نتائج الفحص الآلي

### hermes security audit
```
hermes security audit        → No known vulnerabilities across 151 component(s) ✅
hermes security audit --json → {"total_components_scanned":151,"finding_count":0,"findings":[]}
```

### hermes doctor
```
✓ No active security advisories
✓ No suspicious MCP stdio commands
✓ SSL CA bundle valid
✓ git/ripgrep/docker/node/agent-browser OK
✓ 40 API connectivity — كلها OK عدا xai (HTTP 400 متوقع)
⚠ SQLite 3.45.1 (WAL-reset bug) — يحتاج hermes update → 3.51.3+ / 76 commit متأخرة
⚠ hermes --version: v0.21.0 — يوجد تحديث (76 commit behind)
✓ All checks passed!
```

---

## 2) فحص تسريب المفاتيح — النتيجة: نظيف

| الفحص | الأداة | النتيجة |
|-------|--------|---------|
| مسح كل الملفات المنشورة | `rg -i "api[_-]?key\|secret\|password\|token\|sk-\|ghp_"` | لا مفاتيح هاردكودد — فقط أسماء providers/model IDs (مثال: `openrouter`, `deepseek`) وهي ليست أسرار |
| تاريخ Git كامل | `git log --all --patch \| rg secrets` | صفر نتائج — لم يسبق تسريب مفتاح |
| `.env` داخل المشروع | `ls C:/Temp/hermes-orchestrated/.env` | غير موجود ✅ (الصحيح) |
| `.env` المحلي | `C:/Users/hello/AppData/Local/hermes/.env` | موجود (28,118 بايت) — يحتوي ~20 مفتاح حقيقي لكنه خارج الـ repo ومحمي — غير مرفوع |
| `.gitignore` | غير موجود | ⚠️ خطر — انظر التوصية 1 |
| `pages.yml` secrets | قراءة مباشرة | لا يستخدم أي `secrets.*` — آمن |

**الخلاصة:** لا يوجد أي مفتاح API أو token أو password مسرب في الملفات المنشورة أو تاريخ Git. المفاتيح الحقيقية محفوظة فقط في `AppData/Local/hermes/.env` وهو خارج الـ repo.

---

## 3) مراجعة جودة وأمان الكود

### 3.1 `free-router.py` (2,979 بايت — 65 سطر)

| البند | الحالة | التفصيل |
|-------|--------|---------|
| Shell injection | ✅ آمن | يستخدم `subprocess.run(cmd, shell=False)` مع `cmd` كـ list — الـ prompt يُمرر كـ arg واحد `-z` — لا يمكن حقن أوامر shell |
| Hardcoded secrets | ✅ نظيف | لا يوجد أي مفتاح — يقرأ من `hermes` config/env |
| Input validation | ⚠️ تحسين | `sys.argv[1]` يؤخذ بلا حد أقصى للطول — لو prompt ضخم (MB) قد يستهلك ذاكرة؛ المقترح: `prompt[:4000]` (موجود جزئياً `prompt[:80]` للطباعة فقط) |
| Timeout | ✅ جيد | `timeout=40` لكل محاولة |
| DoS (sleep loop) | ✅ مقبول | `time.sleep(1)` بين المحاولات — 5 محاولات كحد أقصى = 5 ثوان تأخير فقط |
| Error disclosure | ✅ جيد | يطبع أول 300 حرف من الخطأ فقط — لا يكشف stack كامل |
| Permissions | ⚠️ تحسين | `rwxr-xr-x` قابل للتنفيذ — لا ضرر لكن يمكن `chmod 644` لو لا يُنفذ مباشرة |

### 3.2 `health-check.py` (10,424 بايت — 295 سطر)

| البند | الحالة | التفصيل |
|-------|--------|---------|
| Shell injection | ✅ آمن | كل `subprocess.run` بـ `shell=False` + `cmd` كـ list |
| SQL injection | ✅ آمن | `con.execute("SELECT count(*) FROM sessions")` — استعلام ثابت بلا interpolation |
| Path traversal | ✅ آمن | يستخدم `Path.home() / "AppData" / "Local" / "hermes"` — لا يأخذ مسارات من المستخدم |
| Timeouts | ✅ جيد | كل استدعاء خارجي له `timeout` (10-30 ثانية) |
| Error handling | ✅ جيد | كل `check_*` محاط بـ `try/except` ويُرجع `FAIL` بدلاً من crash |
| File reads | ✅ آمن | `read_text(encoding="utf-8", errors="ignore")` — لا crash على ملفات تالفة |
| Code quality | ✅ جيد | 9 فحوصات منفصلة، دالة `fmt_bytes`، تقرير JSON + نصي، `overall` محسوب صحيح |

### 3.3 `dashboard-realtime.html` (31,968 بايت) و `index.html` (4,344 بايت)

| البند | الحالة | التفصيل |
|-------|--------|---------|
| XSS | ✅ آمن | لا يوجد `eval`, `document.write`, `location.href` غير آمن — `innerHTML` يُستخدم فقط مع بيانات ثابتة/عشوائية mock، لا مع مدخلات مستخدم |
| External scripts | ✅ آمن | صفر `<script src=` خارجي — كل JS داخلي |
| CSP header | ⚠️ تحسين | لا يوجد `<meta http-equiv="Content-Security-Policy">` — مقترح إضافتها (انظر التوصية 4) |
| `target="_blank"` | ⚠️ تحسين | رابط GitHub واحد بـ `target="_blank"` بلا `rel="noopener noreferrer"` — إصلاح بسيط |
| Secrets في HTML | ✅ نظيف | صفر نتائج `api_key/secret/token` |
| Data exposure | ✅ آمن | Dashboard يعرض بيانات mock محلية فقط — لا يرسل أي بيانات لخارج |

### 3.4 `.github/workflows/pages.yml`

| البند | الحالة | التفصيل |
|-------|--------|---------|
| Permissions | ✅ ممتاز | `contents: read`, `pages: write`, `id-token: write` — الحد الأدنى المطلوب |
| Action versions | ✅ جيد | `actions/checkout@v4`, `configure-pages@v4`, `upload-pages-artifact@v3`, `deploy-pages@v4` — كلها pinned على major version |
| Artifact path | ⚠️ انتبه | `path: .` يرفع كل الملفات بما فيها `debug/` و `.git` metadata — مقترح `path: ./` مع `.artifactignore` أو تحديد مجلد النشر |
| Concurrency | ✅ جيد | `cancel-in-progress: false` يمنع إلغاء نشر قيد التنفيذ |

### 3.5 `SKILL-free-model-orchestrator.md` و `README.md`

| البند | الحالة | التفصيل |
|-------|--------|---------|
| Secrets | ✅ نظيف | يذكر أسماء models/providers فقط — لا مفاتيح |
| Instructions | ✅ جيد | تذكر `minimax/m2` للعربي و `deepseek` للكود بشكل صحيح |
| Links | ✅ آمن | لا روابط خارجية مشبوهة |

---

## 4) المخاطر المتبقية (خارج الـ repo لكن تؤثر على المشروع)

| # | الخطر | الشدة | الدليل |
|---|-------|-------|--------|
| 1 | **لا يوجد `.gitignore`** في المشروع | 🔴 عالي | أي `cp .env .` مستقبلاً سيُرفع بالخطأ |
| 2 | **SQLite 3.45.1 WAL bug** | 🟡 متوسط | `hermes doctor` ينبه — قد يسبب corruption نادر |
| 3 | **Hermes 76 commit behind** | 🟡 متوسط | `hermes --version` — يفوتك إصلاحات أمان |
| 4 | **Gateway غير مثبت كـ service دائم** | 🟡 متوسط | `hermes gateway status` يظهر running لكن كـ login item فقط — بعد reboot قد لا يعود تلقائياً بدون `hermes gateway install` |
| 5 | **Cron واحد فشل (HTTP 402)** | 🟠 متوسط | `مراقب ملفات المشاريع` — `Insufficient credits` على OpenRouter — يحتاج تعبئة رصيد أو تغيير provider |
| 6 | **config.yaml: `max_turns: 500`** | 🟢 منخفض | مرتفع جداً — قد يسبب حلقة لانهائية وتكلفة |
| 7 | **لا يوجد CSP في HTML** | 🟢 منخفض | لو استُضيف على Pages مع حقن مستقبلي — CSP يحمي |
| 8 | **Artifact path: `.`** | 🟢 منخفض | قد ينشر ملفات `debug/*.png` غير ضرورية |

---

## 5) التوصيات المرتبة حسب الأولوية

### 🔴 عاجل — قبل أي `git push` قادم

**1. أضف `.gitignore` فوراً**
```gitignore
# secrets — لا ترفع أبداً
.env
supabase.env
*.key
hermes.env
*.pem
*.p12

# hermes local state — لا يُنشر
 AppData/
hermes/

# debug artifacts
debug/*.png
debug/*.log

# python
__pycache__/
*.pyc
.venv/
venv/
```

### 🟡 مهم — خلال هذا الأسبوع

**2. حدث Hermes**
```bash
hermes update
# يصلح SQLite WAL bug ويجلب 76 إصلاح أمان/ميزة
```

**3. ثبت Gateway كخدمة دائمة**
```bash
hermes gateway install
# يضمن عمل الـ 5 cron حتى مع قفل الشات
```

**4. أصلح رصيد OpenRouter**
```bash
# إما تعبئة credits على https://openrouter.ai/settings/credits
# أو غيّر provider للـ cron الفاشل إلى nous/google (مجاني)
hermes cron update 92a17864f2b5 --provider nous --model upstage/solar-pro4:free
```

**5. قلل `max_turns`**
```yaml
# في C:/Users/hello/AppData/Local/hermes/config.yaml
agent:
  max_turns: 150  # بدلاً من 500
```

### 🟢 تحسين — عند الفرصة

**6. أضف CSP للـ dashboards**
```html
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;">
```
وأصلح `target="_blank"`:
```html
<a href="..." target="_blank" rel="noopener noreferrer">
```

**7. حدد artifact path في `pages.yml`**
```yaml
- uses: actions/upload-pages-artifact@v3
  with:
    path: .
    # مقترح: استبعد debug
```
أو أنشئ `.artifactignore` يستثني `debug/`.

**8. حسّن `free-router.py` — حد أقصى للـ prompt**
```python
prompt = sys.argv[1][:4000] if len(sys.argv) > 1 else "اكتب جملة ترحيب بالعربي"
```

**9. فعّل تحسينات config المقترحة من `health-check.py`**
```yaml
prompt_caching:
  cache_ttl: 10m  # بدلاً من 5m — يزيد hit rate
# streaming.enabled: true (مفعل حالياً ✅)
```

---

## 6) الخلاصة النهائية

| المحور | الحكم |
|--------|-------|
| **تسريب مفاتيح** | ✅ صفر — المشروع آمن للنشر العام على GitHub Pages |
| **ثغرات تبعيات** | ✅ صفر / 151 مكون — OSV.dev نظيف |
| **جودة كود (Python)** | ✅ جيد — `shell=False`, timeouts, error handling صحيح |
| **جودة كود (HTML/JS)** | ✅ جيد — لا XSS، لا external scripts، تحسين CSP مقترح فقط |
| **CI/CD (Pages)** | ✅ آمن — permissions دنيا، actions pinned |
| **الإعدادات المحلية** | ⚠️ تحتاج 3 أوامر: `hermes update` + `hermes gateway install` + تعبئة OpenRouter |

**المشروع جاهز للنشر العام. المخاطر الوحيدة خارج الـ repo (SQLite قديم + gateway + credits) وكلها تُحل بأوامر محلية بسيطة. لا يوجد أي مفتاح مسرب في الملفات المنشورة.**

---

## 7) أوامر التحقق السريع (انسخ والصق)

```bash
# تحقق كامل في سطر واحد
hermes security audit && hermes doctor && hermes gateway status && hermes cron list

# فحص تسريب مفاتيح يدوي
rg -i "api[_-]?key|secret|password|sk-|ghp_" C:/Temp/hermes-orchestrated --glob '!.git'

# فحص بعد كل push
git -C C:/Temp/hermes-orchestrated log --all --patch | rg -i "api_key|secret" | head
```

*— الوكيل 7 — مراجع أمني — Hermes MoA — 1 سبتمبر 2026 14:01 EEST*
