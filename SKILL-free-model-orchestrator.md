---
name: free-model-orchestrator
description: "Use when routing to the best free model per task."
version: 1.0.0
author: Hermes Orchestrator
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [model-routing, free-models, orchestration]
---

# Free Model Orchestrator — أوركسترا الموديلات المجانية

مهارة تمنح الوكيل حرية اختيار أفضل موديل مجاني لكل مهمة وربط الوكلاء مع بعض لأفضل نتيجة احترافية.

## فلسفة المهارة

لا يوجد موديل واحد هو الأفضل لكل شيء. كل مهمة لها موديل أنسب.

## خريطة الموديلات المجانية المتاحة

| الموديل | المزود | الاستخدام الأمثل |
|---------|--------|------------------|
| `muse-spark-1.2-contributor-free` | opencode-free | عام، سريع، متوازن |
| `upstage/solar-pro4:free` | nous | مهام مساعدة (vision, compression) |
| `deepseek/deepseek-v4-pro` | openrouter | كود وتحليل عميق |
| `anthropic/claude-opus-4.8` | openrouter (MoA aggregator) | تجميع احترافي |
| `gpt-5.5` | openai-codex | مرجع قوي للمهام الصعبة |
| `google/gemini-2.0-flash` | google | سرعة + سياق كبير |
| `minimax/minimax-m2` | minimax | كتابة عربية ممتازة |

OpenRouter يفتح 100+ موديل مجاني إضافي: `meta-llama/llama-3.3-70b:free`, `qwen/qwen-2.5-72b:free`

## جدول التوجيه الذكي

| نوع المهمة | الموديل الأول | البديل |
|------------|--------------|--------|
| كتابة كود جديد | `deepseek-v4-pro` | `muse-spark` |
| إصلاح Bugs | `muse-spark` | `deepseek` |
| كتابة محتوى عربي | `minimax-m2` | `solar-pro4` |
| تحليل وبحث | `gemini-2.0-flash` | `solar-pro4` |
| مراجعة كود/أمان | `claude-opus-4.8` (MoA) | `deepseek` |
| مهام سريعة | `solar-pro4:free` | `muse-spark` |
| قرار معقد | **MoA** (عدة مراجع + مجمع) | `muse-spark` |

## كيف يستخدمها الوكيل

### اختيار الموديل تلقائيا
```bash
# كود → deepseek
 hermes -m deepseek/deepseek-v4-pro --provider openrouter -z "اكتب دالة بايثون..."
# عربي → minimax
 hermes -m minimax/minimax-m2 --provider minimax -z "اكتب مقال عربي..."
# سريع → solar مجاني
 hermes -m upstage/solar-pro4:free --provider nous -z "لخص هذا النص..."
# قرار مهم → MoA
 hermes --moa -z "قارن بين 3 حلول واختر الأفضل"
```

### ربط الوكلاء
```
delegate_task(tasks=[
  {"goal": "ابني الـ backend", "context": "استخدم deepseek - الأفضل للكود. workdir: ./backend"},
  {"goal": "اكتب الوثائق عربي", "context": "استخدم minimax - الأفضل للعربية. workdir: ./docs"},
  {"goal": "راجع الأمان", "context": "استخدم MoA - الأفضل للمراجعة."}
])
```

## نمط العمل الاحترافي (4 مراحل)

```
1. تحليل → solar-pro4:free (سريع)
       ↓
2. تنفيذ متوازي → كل وكيل بموديله الأمثل
   ├─ كود → deepseek  ├─ كتابة → minimax  ├─ بحث → gemini
       ↓
3. مراجعة متقاطعة → MoA
       ↓
4. تجميع نهائي → claude-opus
```

## أوامر جاهزة

```bash
hermes moa enable
hermes fallback add openrouter --model "meta-llama/llama-3.3-70b:free"
hermes fallback add nous --model "upstage/solar-pro4:free"
```

## قاعدة ثابتة أساسية: البحث عن الجديد أولا (مع أقصى استفادة)

> **هذه قاعدة إلزامية قبل أي رد:** قيّم هل المهمة تستفيد من معلومة جديدة؟ 
> - **لو نعم (90% من الحالات):** نفّذ `web_search` + `web_extract` لأحدث المصادر (آخر 7 أيام) قبل التحليل. لا ترد بمعلومات قديمة.
> - **لو لا (إبداع صرف/منطق داخلي/كود لا يحتاج بحث):** تخطّ البحث لتوفير الوقت، واذكر السبب.
> - **المعيار:** هل البحث سيغيّر جودة الرد فعلا؟ لو الإجابة نعم → ابحث. لو لا → لا تبحث شكليا.

```python
# نمط إلزامي في كل مهمة:
# 1. تقييم سريع: هل أحتاج بحث؟ (نعم → web_search، لا → تخطي مع ذكر السبب)
# 2. اختيار الموديل حسب الجدول
# 3. تنفيذ + مراجعة MoA
```

## قواعد ذهبية

1. لا تسأل المستخدم أي موديل — اختر أنت حسب الجدول
2. المهام البسيطة → solar المجاني، المعقدة → opus/deepseek
3. شغّل وكلاء بموديلات مختلفة في نفس الوقت عبر delegation
4. أي مخرج احترافي لازم يمر على MoA قبل التسليم
5. اذكر لماذا اخترت هذا الموديل
6. **البحث عن الجديد قاعدة ثابتة — طبّقها بذكاء لأقصى إفادة، مش بحث شكلي**
