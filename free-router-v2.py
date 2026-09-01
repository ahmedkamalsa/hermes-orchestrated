#!/usr/bin/env python3
"""Router مجاني v2 - 6 موديلات + Poe/Perplexity كبدائل + كشف ليمت محسن"""
import subprocess, sys, json, time, re

# خريطة الموديلات المجانية بالترتيب حسب الأولوية - 6 موديلات
FREE_CHAIN = [
    ("muse-spark-1.2-contributor-free", "opencode-free", "الأساسي السريع"),
    ("deepseek/deepseek-v4-pro", "openrouter", "الأقوى للكود"),
    ("upstage/solar-pro4:free", "nous", "المجاني الاحتياطي 1"),
    ("google/gemini-2.0-flash", "google", "المجاني الاحتياطي 2"),
    ("minimax/minimax-m2", "minimax", "للعربي"),
    ("perplexity/sonar-pro", "perplexity", "بحث متقدم - Perplexity"),
]

# بدائل إضافية خارج السلسلة الأساسية (Poe + Perplexity)
ALTERNATIVE_PROVIDERS = {
    "poe": [
        ("claude-3.5-sonnet", "poe", "Poe - Claude"),
        ("gpt-4o", "poe", "Poe - GPT-4o"),
    ],
    "perplexity": [
        ("perplexity/sonar-pro", "perplexity", "Perplexity Sonar Pro"),
        ("perplexity/sonar", "perplexity", "Perplexity Sonar"),
    ],
}

FREE_ALIASES = {
    "كود": ("deepseek/deepseek-v4-pro", "openrouter"),
    "عربي": ("minimax/minimax-m2", "minimax"),
    "بحث": ("perplexity/sonar-pro", "perplexity"),
    "سريع": ("upstage/solar-pro4:free", "nous"),
    "عام": ("muse-spark-1.2-contributor-free", "opencode-free"),
    "poe": ("claude-3.5-sonnet", "poe"),
    "perplexity": ("perplexity/sonar-pro", "perplexity"),
}

# كشف الليمت المحسن - يغطي كل أنواع الليمت
LIMIT_KEYWORDS = [
    "rate limit", "429", "quota", "quota exceeded", "limit exceeded",
    "overloaded", "too many requests", "billing", "payment required",
    "insufficient_quota", "insufficient quota", "billing error",
    "overloaded_error", "capacity", "over capacity", "resource exhausted",
    "unavailable", "server overloaded", "model overloaded", "quota_exceeded",
    "billing_quota", "usage limit", "credit limit", "free limit",
]

def is_limit_error(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in LIMIT_KEYWORDS)

def try_model(model, provider, prompt, timeout=40):
    cmd = ["hermes", "-m", model, "--provider", provider, "-z", prompt]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding='utf-8', errors='ignore')
        out = (r.stdout or "") + (r.stderr or "")
        lower = out.lower()
        if is_limit_error(out):
            return False, f"⛔ ليمت في {model} ({provider}): {out[:300]}"
        if r.returncode == 0 and len(out.strip()) > 20:
            return True, out.strip()
        # اعتبر الأخطاء القصيرة أو returncode غير صفر كفشل يستحق fallback
        if "error" in lower or "failed" in lower or "exception" in lower:
            return False, out[:600]
        if len(out.strip()) > 20:
            return True, out.strip()
        return False, out[:600]
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)

def smart_ask(prompt, task_type="عام"):
    print(f"🎯 الطلب: {prompt[:80]} | النوع: {task_type}")
    preferred = FREE_ALIASES.get(task_type, (FREE_CHAIN[0][0], FREE_CHAIN[0][1]))
    # السلسلة الأساسية: المفضل أولا ثم باقي الـ 6 بالترتيب
    chain = [preferred] + [(m, p) for m, p, _ in FREE_CHAIN if (m, p) != preferred]
    # أضف بدائل Poe و Perplexity في النهاية كـ fallback أخير
    for alt_list in ALTERNATIVE_PROVIDERS.values():
        for m, p, _ in alt_list:
            if (m, p) not in chain:
                chain.append((m, p))

    for model, provider in chain:
        print(f"  → يجرب {model} عبر {provider} ...", end=" ", flush=True)
        ok, out = try_model(model, provider, prompt)
        if ok:
            print("✅ نجح")
            return model, provider, out
        else:
            print(f"❌ فشل - ينتقل للتالي ({out[:60]}...)")
            time.sleep(1)
    return None, None, "كل الموديلات وصلت لليمت - حاول بعد دقائق"

if __name__ == "__main__":
    prompt = sys.argv[1] if len(sys.argv) > 1 else "اكتب جملة ترحيب بالعربي"
    ttype = sys.argv[2] if len(sys.argv) > 2 else "عام"
    m, p, res = smart_ask(prompt, ttype)
    print("\n" + "="*50)
    if m:
        print(f"✅ تم عبر: {m} ({p})")
        print(res[:2000])
    else:
        print(res)
