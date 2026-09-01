#!/usr/bin/env python3
"""اختبار اتصال Supabase — zsemkiomjgrqjjogmrwv — كتابة وقراءة 3 صفوف تجريبية"""
import os
import sys
import uuid
import time
from pathlib import Path
from datetime import datetime, timezone

# ── تحميل المفاتيح من supabase.env ──
env_path = Path.home() / "AppData" / "Local" / "hermes" / "supabase.env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ[k.strip()] = v.strip()
else:
    print(f"⚠️ لم يُعثر على {env_path} — سيُستخدم env الحالي")

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://zsemkiomjgrqjjogmrwv.supabase.co")
# الأفضل للكتابة هو SECRET/SERVICE — ونستخدم PUBLISHABLE كاحتياطي للقراءة فقط
SUPABASE_SECRET = os.getenv("SUPABASE_SECRET_KEY") or os.getenv("SUPABASE_SERVICE_KEY") or ""
SUPABASE_ANON = os.getenv("SUPABASE_PUBLISHABLE_KEY") or os.getenv("SUPABASE_ANON_KEY") or ""
SUPABASE_KEY = SUPABASE_SECRET or SUPABASE_ANON  # الكتابة تحتاج secret
TEST_RUN_ID = str(uuid.uuid4())[:8]
TAG = f"hermes-test-{TEST_RUN_ID}"

print("=" * 60)
print("🔌 اختبار Supabase — المشروع: zsemkiomjgrqjjogmrwv")
print("=" * 60)
print(f"URL : {SUPABASE_URL}")
print(f"KEY : {(SUPABASE_KEY[:20] + '...') if SUPABASE_KEY else '❌ مفقود'} ({len(SUPABASE_KEY)} chars)")
print(f"KEY type: {'SECRET ✅ (كتابة)' if SUPABASE_SECRET else 'PUBLISHABLE ⚠️ (قراءة فقط)'}")
print(f"Test tag: {TAG}")
print(f"Time: {datetime.now(timezone.utc).isoformat()}")
print()

# ── فحص المكتبة ──
try:
    from supabase import create_client
except ImportError:
    print("❌ مكتبة supabase غير مثبتة — ثبّتها:")
    print("   pip install supabase")
    sys.exit(2)

if "zsemkiomjgrqjjogmrwv" not in SUPABASE_URL:
    print(f"⚠️ تحذير: URL لا يطابق المشروع المطلوب zsemkiomjgrqjjogmrwv — الحالي: {SUPABASE_URL}")

if not SUPABASE_KEY:
    print("❌ لا يوجد مفتاح — تأكد من supabase.env")
    sys.exit(1)

# ── إنشاء العميل ──
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    print("✅ Supabase client created")
except Exception as e:
    print(f"❌ فشل إنشاء العميل: {e}")
    sys.exit(1)

# ── فحص صحة المشروع عبر REST/Auth ──
import httpx
headers_secret = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
try:
    r = httpx.get(f"{SUPABASE_URL}/rest/v1/", headers=headers_secret, timeout=10)
    if r.status_code == 200:
        print(f"✅ REST API متاح (200) — المشروع zsemkiomjgrqjjogmrwv يستجيب")
    else:
        print(f"⚠️ REST / : {r.status_code} {r.text[:200]}")
except Exception as e:
    print(f"⚠️ فشل فحص REST: {e}")

try:
    anon_headers = {"apikey": SUPABASE_ANON or SUPABASE_KEY}
    r = httpx.get(f"{SUPABASE_URL}/auth/v1/health", headers=anon_headers, timeout=10)
    print(f"{'✅' if r.status_code == 200 else '⚠️'} Auth health: {r.status_code} {r.text[:120]}")
except Exception as e:
    print(f"⚠️ فحص Auth: {e}")

try:
    r = httpx.get(f"{SUPABASE_URL}/storage/v1/bucket", headers=headers_secret, timeout=10)
    print(f"{'✅' if r.status_code == 200 else '⚠️'} Storage: {r.status_code} {r.text[:200]}")
except Exception as e:
    print(f"⚠️ فحص Storage: {e}")

print()

# ── تعريف SQL المطلوب ──
SQL_MEMORIES = """
CREATE TABLE IF NOT EXISTS public.memories (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content text NOT NULL,
  metadata jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now()
);
ALTER TABLE public.memories ENABLE ROW LEVEL SECURITY;
-- للاختبار: اسمح للجميع (عدّلها لاحقاً حسب الحاجة)
DROP POLICY IF EXISTS "allow_all_memories" ON public.memories;
CREATE POLICY "allow_all_memories" ON public.memories FOR ALL USING (true) WITH CHECK (true);
""".strip()

SQL_CRON = """
CREATE TABLE IF NOT EXISTS public.cron_results (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  job_id text NOT NULL,
  output text,
  status text DEFAULT 'ok',
  created_at timestamptz DEFAULT now()
);
ALTER TABLE public.cron_results ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "allow_all_cron" ON public.cron_results;
CREATE POLICY "allow_all_cron" ON public.cron_results FOR ALL USING (true) WITH CHECK (true);
""".strip()

def ensure_table_or_hint(table: str, sql: str) -> bool:
    """يتحقق هل الجدول موجود، وإن لم يكن يطبع SQL ويرجع False"""
    try:
        supabase.table(table).select("*").limit(1).execute()
        print(f"✅ جدول {table} موجود")
        return True
    except Exception as e:
        msg = str(e)
        if "PGRST205" in msg or "Could not find the table" in msg:
            print(f"ℹ️ جدول {table} غير موجود بعد (PGRST205)")
            print(f"   → شغّل هذا SQL في Supabase Dashboard → SQL Editor:")
            print(f"   ── {table} ──")
            for line in sql.splitlines():
                print(f"   {line}")
            print()
            return False
        else:
            print(f"⚠️ خطأ غير متوقع عند فحص {table}: {e}")
            return False

memories_ok = ensure_table_or_hint("memories", SQL_MEMORIES)
cron_ok = ensure_table_or_hint("cron_results", SQL_CRON)

if not memories_ok or not cron_ok:
    print("─" * 60)
    print("⏳ الجداول غير جاهزة — الاتصال نفسه سليم، لكن الكتابة مؤجلة حتى تنشئ الجداول.")
    print("   بعد تشغيل SQL أعلاه، أعد تشغيل:  python C:/Temp/hermes-orchestrated/supabase-test.py")
    print("─" * 60)
    # لا نخرج بخطأ — الاتصال نجح، فقط الجداول ناقصة
    if not SUPABASE_SECRET:
        print("⚠️ تنبيه: أنت تستخدم مفتاح PUBLISHABLE فقط — الكتابة قد تفشل بسبب RLS. استخدم SECRET.")
    sys.exit(0)

# ── اختبار الكتابة والقراءة: 3 صفوف لكل جدول ──
print("─" * 60)
print(f"🧪 اختبار الكتابة — إدخال 3 صفوف في كل جدول (tag={TAG})")
print("─" * 60)

all_ok = True

# 1) memories — 3 صفوف
memories_payload = [
    {"content": f"[{TAG}] ذكرى تجريبية 1 — {datetime.now(timezone.utc).isoformat()}", "metadata": {"test_run": TAG, "idx": 1}},
    {"content": f"[{TAG}] ذكرى تجريبية 2 — تجربة عربية", "metadata": {"test_run": TAG, "idx": 2}},
    {"content": f"[{TAG}] ذكرى تجريبية 3 — Hermes Orchestrator", "metadata": {"test_run": TAG, "idx": 3}},
]
try:
    # جرّب مع metadata، وإن فشل جرّب content فقط (لتوافق السكيمة المختلفة)
    try:
        res = supabase.table("memories").insert(memories_payload).execute()
    except Exception as e1:
        if "metadata" in str(e1) or "column" in str(e1).lower():
            print(f"   ℹ️ metadata غير مدعوم — أعيد المحاولة بـ content فقط: {e1}")
            memories_payload_simple = [{"content": r["content"]} for r in memories_payload]
            res = supabase.table("memories").insert(memories_payload_simple).execute()
        else:
            raise
    inserted_ids = [row.get("id", "?") for row in res.data]
    print(f"✅ memories: أُدخلت 3 صفوف — IDs: {inserted_ids}")
    # قراءة تحقق
    res2 = supabase.table("memories").select("*").ilike("content", f"%{TAG}%").execute()
    print(f"✅ memories: قراءة تحقق — وُجد {len(res2.data)} صفوف بـ tag {TAG}")
    for row in res2.data:
        print(f"   - {row.get('id')} | {str(row.get('content'))[:80]}")
    if len(res2.data) < 3:
        print(f"⚠️ memories: متوقع 3 صفوف، وُجد {len(res2.data)}")
        all_ok = False
except Exception as e:
    print(f"❌ memories كتابة/قراءة فشلت: {e}")
    all_ok = False

print()

# 2) cron_results — 3 صفوف
cron_payload = [
    {"job_id": f"{TAG}-job-1", "output": f"[{TAG}] نتيجة تجريبية 1 — {datetime.now(timezone.utc).isoformat()}", "status": "ok"},
    {"job_id": f"{TAG}-job-2", "output": f"[{TAG}] نتيجة تجريبية 2", "status": "ok"},
    {"job_id": f"{TAG}-job-3", "output": f"[{TAG}] نتيجة تجريبية 3", "status": "ok"},
]
try:
    try:
        res = supabase.table("cron_results").insert(cron_payload).execute()
    except Exception as e1:
        if "status" in str(e1):
            print(f"   ℹ️ عمود status غير موجود — أعيد بـ job_id/output فقط: {e1}")
            cron_simple = [{"job_id": r["job_id"], "output": r["output"]} for r in cron_payload]
            res = supabase.table("cron_results").insert(cron_simple).execute()
        else:
            raise
    inserted_ids = [row.get("id", "?") for row in res.data]
    print(f"✅ cron_results: أُدخلت 3 صفوف — IDs: {inserted_ids}")
    res2 = supabase.table("cron_results").select("*").ilike("job_id", f"%{TAG}%").execute()
    print(f"✅ cron_results: قراءة تحقق — وُجد {len(res2.data)} صفوف بـ tag {TAG}")
    for row in res2.data:
        print(f"   - {row.get('id')} | {row.get('job_id')} | {str(row.get('output'))[:60]}")
    if len(res2.data) < 3:
        print(f"⚠️ cron_results: متوقع 3 صفوف، وُجد {len(res2.data)}")
        all_ok = False
except Exception as e:
    print(f"❌ cron_results كتابة/قراءة فشلت: {e}")
    all_ok = False

print()

# ── تنظيف (اختياري) — احذف الصفوف التجريبية ──
try:
    supabase.table("memories").delete().ilike("content", f"%{TAG}%").execute()
    supabase.table("cron_results").delete().ilike("job_id", f"%{TAG}%").execute()
    print(f"🧹 تنظيف: حُذفت الصفوف التجريبية (tag={TAG})")
    # تحقق الحذف
    r1 = supabase.table("memories").select("id").ilike("content", f"%{TAG}%").execute()
    r2 = supabase.table("cron_results").select("id").ilike("job_id", f"%{TAG}%").execute()
    print(f"   تحقق: memories بقي {len(r1.data)} | cron_results بقي {len(r2.data)} (0 = نظيف)")
except Exception as e:
    print(f"ℹ️ التنظيف تخطّي (قد يكون RLS يمنع DELETE): {e}")
    print(f"   احذف يدوياً إن لزم: DELETE FROM memories WHERE content LIKE '%{TAG}%';")

print()
print("=" * 60)
if all_ok:
    print("✅✅ الاختبار اكتمل بنجاح — الكتابة والقراءة تعمل (6 صفوف: 3+3)")
else:
    print("⚠️ الاختبار اكتمل مع تحذيرات — راجع الأسطر أعلاه")
print(f"   المشروع: zsemkiomjgrqjjogmrwv.supabase.co | tag: {TAG}")
print("=" * 60)
