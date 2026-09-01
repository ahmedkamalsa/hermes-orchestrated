#!/usr/bin/env python3
"""Router مجاني مع fallback تلقائي - يتنقل بسهولة بين الموديلات عند الليمت أو العقبات"""
import subprocess, sys, json, time

# خريطة الموديلات المجانية بالترتيب حسب الأولوية
FREE_CHAIN = [
    ("muse-spark-1.2-contributor-free", "opencode-free", "الأساسي السريع"),
    ("deepseek/deepseek-v4-pro", "openrouter", "الأقوى للكود"),
    ("upstage/solar-pro4:free", "nous", "المجاني الاحتياطي 1"),
    ("google/gemini-2.0-flash", "google", "المجاني الاحتياطي 2"),
    ("minimax/minimax-m2", "minimax", "للعربي"),
]

FREE_ALIASES = {
    "كود": ("deepseek/deepseek-v4-pro", "openrouter"),
    "عربي": ("minimax/minimax-m2", "minimax"),
    "بحث": ("google/gemini-2.0-flash", "google"),
    "سريع": ("upstage/solar-pro4:free", "nous"),
    "عام": ("muse-spark-1.2-contributor-free", "opencode-free"),
}

def try_model(model, provider, prompt, timeout=40):
    cmd = ["hermes", "-m", model, "--provider", provider, "-z", prompt]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding='utf-8', errors='ignore')
        out = (r.stdout or "") + (r.stderr or "")
        # كشف الليمت / الأخطاء
        lower = out.lower()
        if any(x in lower for x in ["rate limit", "429", "quota", "limit exceeded", "overloaded", "too many requests", "billing"]):
            return False, f"⛔ ليمت في {model}: {out[:300]}"
        if r.returncode == 0 and len(out.strip()) > 20:
            return True, out.strip()
        return False, out[:600]
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)

def smart_ask(prompt, task_type="عام"):
    print(f"🎯 الطلب: {prompt[:80]} | النوع: {task_type}")
    # اختر الموديل الأنسب أولا
    preferred = FREE_ALIASES.get(task_type, (FREE_CHAIN[0][0], FREE_CHAIN[0][1]))
    chain = [preferred] + [ (m,p) for m,p,_ in FREE_CHAIN if (m,p) != preferred ]
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
    m,p,res = smart_ask(prompt, ttype)
    print("\n" + "="*50)
    if m:
        print(f"✅ تم عبر: {m} ({p})")
        print(res[:2000])
    else:
        print(res)
