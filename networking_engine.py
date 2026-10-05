#!/usr/bin/env python3
"""
محرك العلاقات (Relationship Engine) — منظومة الحرباء
الوظيفة: تجهيز خطة دعوات يومية لمسؤولي التوظيف/مديري التوظيف + قوالب الرسائل + مراقبة الحد الأسبوعي.
التقديم الفعلي للدعوات يتم في نافذة ذهبية عبر متصفح الآلي (10:30-12:30 Cairo) — السكربت ده هو المخطط والمراقب.
حد لينكد إن الرسمي: 100 دعوة/أسبوع. الاستخدام الآمن: 12/يوم.
"""
import json, os, random, sys
from datetime import datetime, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))
SENT_LOG = os.path.join(BASE, "networking_log.json")

# 1) استعلامات البحث — مسؤولو توظيف ومديرو Marketing في مصر/الشرق الأوسط
SEARCH_QUERIES = [
    ("talent acquisition marketing egypt", "Egypt"),
    ("marketing recruiter egypt", "Egypt"),
    ("hiring manager marketing MENA", "Egypt"),
    ("head of growth egypt", "Egypt"),
    ("marketing recruiter dubai", "United Arab Emirates"),
    ("talent acquisition marketing UAE", "United Arab Emirates"),
    ("marketing recruiter riyadh", "Saudi Arabia"),
]

# 2) قوالب رسالة الدعوة (تدوير عشوائي — ممنوع التكرار الحرفي)
TEMPLATES = [
    "السلام عليكم {name}، متابع شغلك في {company} ومعجب بالتوجه. نفسي نتواصل في مجال التسويق.",
    "Hi {name}, I've been following {company}'s work and would love to connect with fellow marketing professionals.",
    "مرحبا {name}، بنيت شبكة مهنية في التسويق الرقمي وحابب نتواصل — محتمل نستفيد من بعض.",
    "Hello {name}, fellow marketing enthusiast here. Would appreciate connecting and learning from your experience at {company}.",
]

DAILY_BUDGET = 12
WEEKLY_LIMIT = 100

def load_log():
    if os.path.exists(SENT_LOG):
        return json.load(open(SENT_LOG, encoding="utf-8"))
    return {"sent": [], "week_start": None}

def week_key():
    today = datetime.now()
    return (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")

def count_week(log):
    wk = week_key()
    return len([s for s in log["sent"] if s["date"] >= wk])

def plan(recruiters):
    """recruiters: list of dicts {name, company, role, profile_url}"""
    log = load_log()
    wk = count_week(log)
    remaining_week = WEEKLY_LIMIT - wk
    today = datetime.now().strftime("%Y-%m-%d")
    today_count = len([s for s in log["sent"] if s["date"] == today])
    budget = max(0, min(DAILY_BUDGET - today_count, remaining_week))
    chosen, used_urls = [], {s["url"] for s in log["sent"]}
    for r in recruiters:
        if len(chosen) >= budget: break
        if r["profile_url"] in used_urls: continue
        t = random.choice(TEMPLATES)
        msg = t.format(name=r.get("name", "").split()[0] if r.get("name") else "",
                       company=r.get("company", "your company"))
        chosen.append({**r, "message": msg})
    return {"budget": budget, "week_used": wk, "queue": chosen}

def record(results):
    """results: list of {name, url, company, status}"""
    log = load_log()
    for r in results:
        log["sent"].append({**r, "date": datetime.now().strftime("%Y-%m-%d")})
    json.dump(log, open(SENT_LOG, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return count_week(log)

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        log = load_log()
        print(f"week used: {count_week(log)}/{WEEKLY_LIMIT}")
        print(f"today: {len([s for s in log['sent'] if s['date']==datetime.now().strftime('%Y-%m-%d')])}/{DAILY_BUDGET}")
    elif cmd == "plan":
        data = json.load(sys.stdin)  # recruiters from browser harvest
        print(json.dumps(plan(data), ensure_ascii=False, indent=1))
