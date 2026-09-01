#!/usr/bin/env python3
"""
Hermes Health Check — مراقبة صحة نظام Hermes Agent
يفحص: الأمان، المساحة، الـ checkpoints، الـ logs، حالة الخدمات، والـ config
الاستخدام: python health-check.py [--json] [--fix]
"""
import json
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERMES_HOME = Path.home() / "AppData" / "Local" / "hermes"
CONFIG_PATH = HERMES_HOME / "config.yaml"
LOGS_DIR = HERMES_HOME / "logs"
SESSIONS_DIR = HERMES_HOME / "sessions"
CHECKPOINTS_DIR = HERMES_HOME / "checkpoints"

CRITICAL_DISK_PCT = 10   # % حر تنبيه حرج
WARN_DISK_PCT = 20       # % حر تحذير
CRITICAL_LOG_MB = 50     # حجم لوق كبير
WARN_SESSIONS = 100      # عدد جلسات كبير


def run(cmd, timeout=20):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, shell=False)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except Exception as e:
        return "", str(e), -1


def fmt_bytes(n):
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def check_disk():
    total, used, free = shutil.disk_usage("C:/")
    pct_free = free / total * 100
    status = "OK"
    if pct_free < CRITICAL_DISK_PCT:
        status = "CRITICAL"
    elif pct_free < WARN_DISK_PCT:
        status = "WARN"
    return {
        "name": "disk_space",
        "label": "مساحة القرص C:",
        "status": status,
        "detail": f"حر {fmt_bytes(free)} / {fmt_bytes(total)} ({pct_free:.1f}% حر)",
        "pct_free": round(pct_free, 1),
        "free_bytes": free,
        "total_bytes": total,
    }


def check_security_audit():
    out, err, code = run(["hermes", "security", "audit"], timeout=30)
    ok = "No known vulnerabilities" in out
    return {
        "name": "security_audit",
        "label": "فحص الأمان (OSV.dev)",
        "status": "OK" if ok else ("WARN" if code == 0 else "FAIL"),
        "detail": out[:300] if out else err[:300],
        "vulnerable": not ok,
    }


def check_doctor():
    out, err, code = run(["hermes", "doctor"], timeout=30)
    has_fail = "FAIL" in out or "✗" in out
    # تجاهل تحذير SQLite المعروف
    sqlite_warn = "SQLite 3.45.1" in out
    status = "OK" if not has_fail else "WARN"
    detail = "All checks passed" if "All checks passed" in out else out[:400]
    if sqlite_warn:
        detail += " | تنبيه: SQLite قديم (يحتاج hermes update)"
    return {
        "name": "doctor",
        "label": "hermes doctor",
        "status": status,
        "detail": detail,
        "sqlite_warn": sqlite_warn,
    }


def check_gateway():
    out, err, code = run(["hermes", "gateway", "status"], timeout=15)
    running = "running" in out.lower()
    return {
        "name": "gateway",
        "label": "حالة Gateway",
        "status": "OK" if running else "INFO",
        "detail": out[:300] if out else err[:300] or "Gateway متوقف (طبيعي إذا لا تستخدم Telegram/Discord)",
    }


def check_logs():
    results = []
    for name in ("agent.log", "errors.log", "gateway.log", "gui.log"):
        p = LOGS_DIR / name
        if not p.exists():
            continue
        sz = p.stat().st_size
        st = "OK"
        if sz > CRITICAL_LOG_MB * 1024 * 1024:
            st = "WARN"
        results.append({"file": name, "size": fmt_bytes(sz), "bytes": sz, "status": st,
                        "label": name, "detail": f"{fmt_bytes(sz)}"})

    # عد أخطاء حديثة
    err_log = LOGS_DIR / "errors.log"
    recent_errors = 0
    if err_log.exists():
        try:
            text = err_log.read_text(encoding="utf-8", errors="ignore")
            # أخطاء غير تحذيرات الـ check_fn المتوقعة
            for line in text.splitlines()[-100:]:
                if "ERROR" in line and "check_" not in line:
                    recent_errors += 1
        except Exception:
            pass
    return {
        "name": "logs",
        "label": "ملفات السجلات",
        "status": "WARN" if any(r["status"] == "WARN" for r in results) else "OK",
        "detail": f"{len(results)} ملفات، الأكبر {max((r['bytes'] for r in results), default=0) / 1024:.0f}KB",
        "files": results,
        "recent_errors": recent_errors,
    }


def check_checkpoints():
    out, err, code = run(["hermes", "checkpoints", "status"], timeout=15)
    # parse total size
    size_str = "0 B"
    if "Total size" in out:
        for line in out.splitlines():
            if "Total size" in line:
                size_str = line.split(":", 1)[-1].strip()
                break
    return {
        "name": "checkpoints",
        "label": "Checkpoints",
        "status": "OK",
        "detail": out.strip()[:400] if out else "لا يوجد checkpoints",
        "size_str": size_str,
    }


def check_sessions():
    db = HERMES_HOME / "state.db"
    count = 0
    msgs = 0
    db_size = 0
    if db.exists():
        db_size = db.stat().st_size
        try:
            con = sqlite3.connect(str(db))
            count = con.execute("SELECT count(*) FROM sessions").fetchone()[0]
            msgs = con.execute("SELECT count(*) FROM messages").fetchone()[0]
            con.close()
        except Exception as e:
            return {"name": "sessions", "label": "الجلسات", "status": "WARN", "detail": str(e)}
    st = "OK"
    if count > WARN_SESSIONS:
        st = "WARN"
    return {
        "name": "sessions",
        "label": "قاعدة الجلسات",
        "status": st,
        "detail": f"{count} جلسة، {msgs} رسالة، حجم DB {fmt_bytes(db_size)}",
        "count": count,
        "messages": msgs,
        "db_bytes": db_size,
    }


def check_config():
    issues = []
    if CONFIG_PATH.exists():
        text = CONFIG_PATH.read_text(encoding="utf-8", errors="ignore")
        if "max_turns: 500" in text:
            issues.append("max_turns=500 مرتفع جداً — يُنصح 150-200")
        if "reasoning_effort: medium" in text:
            issues.append("reasoning_effort=medium مناسب، لكن low أسرع وأرخص")
        if "prompt_caching:" in text and "cache_ttl: 5m" in text:
            issues.append("cache_ttl 5m جيد، يمكن رفعه إلى 10m لزيادة hit rate")
        if "streaming:\n  enabled: false" in text:
            issues.append("streaming.enabled=false — فعّله لتحسين زمن الاستجابة")
        if "fallback_model" not in text or "# fallback_model" in text:
            issues.append("fallback_model غير مُفعل — فعّله للمرونة عند فشل المزود الأساسي")
    return {
        "name": "config",
        "label": "إعدادات config.yaml",
        "status": "INFO" if issues else "OK",
        "detail": "; ".join(issues) if issues else "الإعدادات تبدو سليمة",
        "issues": issues,
    }


def check_updates():
    out, err, code = run(["hermes", "--version"], timeout=10)
    behind = "behind" in out
    return {
        "name": "updates",
        "label": "تحديثات Hermes",
        "status": "WARN" if behind else "OK",
        "detail": out.strip()[:200],
        "behind": behind,
    }


CHECKS = [check_disk, check_security_audit, check_doctor, check_gateway, check_logs, check_checkpoints, check_sessions, check_config, check_updates]

ICON = {"OK": "✓", "WARN": "⚠", "CRITICAL": "✗", "FAIL": "✗", "INFO": "ℹ"}


def main():
    use_json = "--json" in sys.argv
    do_fix = "--fix" in sys.argv

    results = []
    for fn in CHECKS:
        try:
            results.append(fn())
        except Exception as e:
            results.append({"name": fn.__name__, "label": fn.__name__, "status": "FAIL", "detail": str(e)})

    overall = "OK"
    if any(r["status"] == "CRITICAL" or r["status"] == "FAIL" for r in results):
        overall = "CRITICAL"
    elif any(r["status"] == "WARN" for r in results):
        overall = "WARN"

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall": overall,
        "checks": results,
    }

    if use_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if overall == "OK" else 1

    # تقرير نصي عربي
    print("=" * 58)
    print("  🩺 تقرير صحة Hermes —", datetime.now().strftime("%Y-%m-%d %H:%M"))
    print("=" * 58)
    print(f"  الحالة العامة: {ICON.get(overall,'?')} {overall}")
    print()
    for r in results:
        icon = ICON.get(r["status"], "?")
        print(f"  {icon} [{r['status']:8s}] {r['label']}")
        print(f"     └─ {r['detail'][:160]}")
    print()
    print("-" * 58)
    print("  التوصيات:")
    printed = False
    for r in results:
        if r["status"] in ("WARN", "CRITICAL", "INFO") and r.get("issues"):
            for iss in r["issues"]:
                print(f"   • {iss}")
                printed = True
        if r["name"] == "disk_space" and r["status"] != "OK":
            print(f"   • نظف القرص: احذف audio_cache/image_cache/cache غير المستخدمة")
            printed = True
        if r["name"] == "logs" and r["status"] == "WARN":
            print(f"   • السجلات كبيرة — شغّل: hermes logs --help ونظف القديم")
            printed = True
        if r["name"] == "sessions" and r.get("count", 0) > WARN_SESSIONS:
            print(f"   • عدد الجلسات كبير — شغّل: hermes sessions list ثم احذف القديم")
            printed = True
        if r["name"] == "updates" and r.get("behind"):
            print(f"   • يوجد تحديث — شغّل: hermes update (يصلح SQLite أيضاً)")
            printed = True
    if not printed and overall == "OK":
        print("   • كل شيء سليم — لا إجراء مطلوب")
    print("=" * 58)

    if do_fix:
        print("\n  🔧 وضع الإصلاح --fix غير مُفعل تلقائياً حالياً.")
        print("  راجع التوصيات أعلاه ونفذها يدوياً.")

    return 0 if overall == "OK" else (2 if overall == "CRITICAL" else 1)


if __name__ == "__main__":
    sys.exit(main())
