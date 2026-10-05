#!/usr/bin/env python3
"""
Chameleon Job Discovery - Apify LinkedIn Jobs -> scored queue (jobs_queue.json)
Usage: python3 apify_jobs.py "Marketing Manager" "Egypt" [rows]
Scoring (approved policy #12): freshness-first + role-match keywords from bank.
Output: jobs_queue.json (sorted), prints top summary.
"""
import json, os, sys, time, urllib.request

TOKEN = os.environ.get("APIFY_API_TOKEN", "")
ACTOR = "curious_coder~linkedin-jobs-scraper"
MATCH = ["marketing", "digital", "community", "content", "brand", "performance",
         "social media", "growth", "crm", "b2b", "media", "partnership", "communications"]

MENA = ["Egypt","United Arab Emirates","Saudi Arabia","Qatar","Kuwait","Oman","Bahrain","Jordan","Lebanon","Iraq","Yemen","Palestine","Libya","Morocco","Algeria","Tunisia","Sudan"]
title = sys.argv[1] if len(sys.argv) > 1 else "Marketing Manager"
mode = sys.argv[2] if len(sys.argv) > 2 else "mena"
if mode == "mena":
    LOCS = MENA
elif mode == "remote":
    LOCS = ["Remote", "Worldwide"]
else:
    LOCS = [mode]
rows = int(sys.argv[3]) if len(sys.argv) > 3 else 20
rows = max(3, rows // len(LOCS))

def api(url, data=None):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None,
                                 headers={"Authorization": "Bearer " + TOKEN,
                                          "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=180).read())

for loc in LOCS:
    r = api(f"https://api.apify.com/v2/acts/{ACTOR}/runs", {"title": title, "location": loc, "rows": rows})
    print("RUN", loc, r["data"]["id"])
while True:
    time.sleep(10)
    st = api(f"https://api.apify.com/v2/actor-runs/{run_id}")["data"]["status"]
    print("status:", st)
    if st in ("SUCCEEDED", "FAILED", "ABORTED"):
        break
if st != "SUCCEEDED":
    print("RUN_FAILED")
    sys.exit(1)

items = api(f"https://api.apify.com/v2/actor-runs/{run_id}/dataset/items?clean=true&format=json")
if isinstance(items, dict):
    items = items.get("data", {}).get("items", items.get("items", []))

out = []
for j in items:
    url = j.get("jobUrl") or j.get("url") or ""
    desc = (j.get("description") or "")[:3000]
    text = (str(j.get("title", "")) + " " + desc).lower()
    score = 0
    hits = [m for m in MATCH if m in text]
    score += min(2 * len(hits), 8)
    posted = str(j.get("postedDate") or j.get("postedAt") or "")
    if posted:
        try:
            ts = time.mktime(time.strptime(posted[:19], "%Y-%m-%dT%H:%M:%S"))
            days = (time.time() - ts) / 86400
            score += 3 if days < 1 else (2 if days < 3 else (1 if days < 7 else 0))
        except Exception:
            pass
    out.append({"title": j.get("title"), "company": j.get("companyName") or j.get("company"),
                "location": j.get("location"), "url": url, "posted": posted,
                "match_score": score, "source": "apify/linkedin",
                "easy_apply": "?", "remote": "remote" in text or "عن بعد" in text,
                "description": desc})

out.sort(key=lambda x: -x["match_score"])
json.dump(out, open("jobs_queue.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"QUEUED {len(out)} jobs -> jobs_queue.json")
for j in out[:8]:
    print(f"  [{j['match_score']}] {j['title']} @ {j['company']} ({j['posted'][:10]})")
