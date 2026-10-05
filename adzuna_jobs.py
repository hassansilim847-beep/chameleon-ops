#!/usr/bin/env python3
"""
المصدر الرابع: Adzuna — وظائف Remote عالمية (gb, us, ca, au, de, ...)
ملاحظة: Adzuna لا يدعم مصر/الشرق الأوسط — يخدم شق Remote Worldwide فقط.
Limit: Trial Access (~250 req/شهر تقريبًا). 5 طلبات/تشغيل كافية.
"""
import json, os, sys, urllib.request, urllib.parse
from datetime import date

AID = os.environ.get("ADZUNA_APP_ID", "86ee46a8")
AKEY = os.environ.get("ADZUNA_APP_KEY", "cdc61e3e07b446fd57d97228c181a356")
QFILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jobs_queue.json")
COUNTRIES = ["gb", "us", "ca", "au", "de"]
WHAT = ["remote marketing", "remote digital marketing", "remote growth marketing", "remote social media"]

def fetch(what, country, page=1):
    u = f"https://api.adzuna.com/v1/api/jobs/{country}/search?" + urllib.parse.urlencode({
        "app_id": AID, "app_key": AKEY, "what": what, "results_per_page": 10})
    req = urllib.request.Request(u, headers={"User-Agent": "curl/8.5.0"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.load(r).get("results", [])
    except Exception as e:
        print("ERR", country, what, e); return []

def main():
    queue = json.load(open(QFILE, encoding="utf-8")) if os.path.exists(QFILE) else []
    seen_urls = {(j.get("company") or "", j.get("title") or "") for j in queue}
    added = 0
    for i, (country, what) in enumerate([(c, w) for w in WHAT for c in COUNTRIES][:6]):
        for r in fetch(what, country):
            title, desc = (r.get("title") or ""), (r.get("description") or "")
            if "remote" not in (title + " " + desc).lower(): continue
            company = (r.get("company") or {}).get("display_name") or "Unknown"
            key = (company, title)
            if key in seen_urls: continue
            seen_urls.add(key)
            queue.append({
                "title": title, "company": company,
                "location": (r.get("location") or {}).get("display_name") or country.upper(),
                "url": r.get("redirect_url") or "", "posted": r.get("created") or str(date.today()),
                "match_score": 2, "source": "adzuna", "easy_apply": "no", "remote": True,
                "description": desc[:600]})
            added += 1
    json.dump(queue, open(QFILE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"ADZUNA_OK added={added} total={len(queue)}")

if __name__ == "__main__":
    main()
