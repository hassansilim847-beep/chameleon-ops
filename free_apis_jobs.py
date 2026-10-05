#!/usr/bin/env python3
"""Free public job APIs (no keys): Remotive + Jobicy remote jobs -> jobs_queue.json (merge+dedupe)."""
import json, time, urllib.request
q = "marketing"
def get(url):
    return json.loads(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"}), timeout=30).read())
out = []
try:
    d = get(f"https://remotive.com/api/remote-jobs?search={q}&limit=10")
    for j in d.get("jobs", []):
        out.append({"title": j.get("title"), "company": j.get("company_name"), "location": "Remote",
            "url": j.get("url"), "posted": (j.get("publication_date") or "")[:10],
            "match_score": 4, "source": "remotive", "easy_apply": "?", "remote": True,
            "description": (j.get("description") or "")[:2000]})
except Exception as e:
    print("remotive err:", e)
try:
    d = get(f"https://jobicy.com/api/v2/remote-jobs?count=10&tag={q}")
    for j in d.get("jobs", []):
        out.append({"title": j.get("jobName"), "company": j.get("companyName"), "location": j.get("jobGeo"),
            "url": j.get("url"), "posted": (j.get("pubDate") or "")[:10],
            "match_score": 4, "source": "jobicy", "easy_apply": "?", "remote": True,
            "description": (j.get("jobExcerpt") or "")[:2000]})
except Exception as e:
    print("jobicy err:", e)
try:
    cur = json.load(open("jobs_queue.json"))
except Exception:
    cur = []
seen = {j.get("url") for j in cur}
merged = cur + [j for j in out if j.get("url") and j["url"] not in seen]
json.dump(merged, open("jobs_queue.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"free APIs: +{len(merged)-len(cur)} jobs (remotive/jobicy), total queue: {len(merged)}")
for j in out[:6]: print("  *", j.get("title"), "@", j.get("company"))
