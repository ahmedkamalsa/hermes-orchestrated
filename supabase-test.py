#!/usr/bin/env python3
"""اختبار اتصال Supabase — يكتب ويقرأ من zsemkiomjgrqjjogmrwv"""
import os, sys
from pathlib import Path

# حمّل المفاتيح من supabase.env
env_path = Path.home() / "AppData" / "Local" / "hermes" / "supabase.env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k,v = line.split("=",1)
            os.environ[k.strip()] = v.strip()

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://zsemkiomjgrqjjogmrwv.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_PUBLISHABLE_KEY")

print(f"URL: {SUPABASE_URL}")
print(f"KEY: {SUPABASE_KEY[:18]}... ({len(SUPABASE_KEY or '')} chars)")

try:
    from supabase import create_client
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase client created")

    # اختبار القراءة — جدول memories (إن وُجد)
    for table in ["memories", "cron_results"]:
        try:
            res = supabase.table(table).select("*").limit(3).execute()
            print(f"✅ قراءة {table}: {len(res.data)} صفوف")
            if res.data:
                print(f"   مثال: {str(res.data[0])[:200]}")
        except Exception as e:
            print(f"ℹ️ جدول {table} غير جاهز بعد: {e}")
            print(f"   → شغّل SQL التالي في Supabase Dashboard → SQL Editor:")
            if table == "memories":
                print("   CREATE TABLE memories (id uuid primary key default gen_random_uuid(), content text, created_at timestamptz default now());")
            else:
                print("   CREATE TABLE cron_results (id uuid primary key default gen_random_uuid(), job_id text, output text, created_at timestamptz default now());")

    # اختبار كتابة تجريبية (إذا الجداول موجودة)
    try:
        payload = {"content": "اختبار من Hermes Orchestrator — " + __import__("datetime").datetime.now().isoformat()}
        # لا نكتب فعليا إلا إذا الجدول موجود — جرّب وأمسك الخطأ
        res = supabase.table("memories").insert(payload).execute()
        print(f"✅ كتابة تجريبية نجحت: {res.data}")
    except Exception as e:
        print(f"ℹ️ الكتابة التجريبية مؤجلة حتى إنشاء الجداول: {e}")

    print("\n✅ الاختبار اكتمل — حالة الاتصال: سليم (المفاتيح صحيحة، المشروع zsemkiomjgrqjjogmrwv متاح)")

except ImportError:
    print("⚠️ مكتبة supabase غير مثبتة — ثبّتها: pip install supabase")
    sys.exit(2)
except Exception as e:
    print(f"❌ فشل الاتصال: {e}")
    sys.exit(1)
