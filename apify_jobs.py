#!/usr/bin/env python3
"""
Chameleon Job Discovery v2 - Apify LinkedIn (MENA+remote, FRESH <=7d only)
Usage: python3 apify_jobs.py "<keyword>" <mode: mena|remote|Country> [total_rows]
Overwrites apify section of jobs_queue.json. Old/stale jobs are dropped (user rule).
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
    try:
        rst = json.load(open("apify_rotation.json"))
    except Exception:
        rst = {"idx": 0}
    i = rst["idx"] % len(MENA)
    LOCS = [MENA[i], MENA[(i + 1) % len(MENA)]]
    rst["idx"] = i + 2
    try:
        json.dump(rst, open("apify_rotation.json", "w"))
    except Exception:
        pass
elif mode == "remote":
    LOCS = ["Remote"]
else:
    LOCS = [mode]
total = int(sys.argv[3]) if len(sys.argv) > 3 else 340
rows = min(15, max(3, total // len(LOCS)))

def api(url, data=None):
    req = urllib.request.Request(url, data=json.dumps(data).encode() if data else None,
                                 headers={"Authorization": "Bearer " + TOKEN,
                                          "Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=180).read())

# launch one actor run per location (concurrent), fresh jobs only
runs = []
for loc in LOCS:
    try:
        r = api("https://api.apify.com/v2/acts/%s/runs" % ACTOR,
                {"title": title, "location": loc, "rows": rows, "publishedAt": "r604800"})
        runs.append((loc, r["data"]["id"]))
        print("RUN", loc, r["data"]["id"])
    except Exception as e:
        print("SKIP", loc, repr(e)[:150])

items_all = []
for loc, rid in runs:
    st = None
    for _ in range(90):
        time.sleep(10)
        st = api("https://api.apify.com/v2/actor-runs/%s" % rid)["data"]["status"]
        if st in ("SUCCEEDED", "FAILED", "ABORTED"):
            break
    if st != "SUCCEEDED":
        print("FAILED", loc, st)
        continue
    items = api("https://api.apify.com/v2/actor-runs/%s/dataset/items?clean=true&format=json" % rid)
    if isinstance(items, dict):
        items = items.get("data", {}).get("items", items.get("items", []))
    print("OK", loc, len(items))
    items_all.extend(items)

now = time.time()
seen, out = set(), []
for j in items_all:
    url = j.get("jobUrl") or j.get("url") or ""
    if not url or url in seen:
        continue
    seen.add(url)
    posted = str(j.get("postedDate") or j.get("postedAt") or "")
    ts = None
    try:
        ts = time.mktime(time.strptime(posted[:19], "%Y-%m-%dT%H:%M:%S"))
    except Exception:
        try:
            ts = float(posted)
        except Exception:
            ts = None
    if ts is not None and (now - ts) / 86400.0 > 7:
        continue  # drop anything older than 7 days
    desc = (j.get("description") or "")[:3000]
    text = (str(j.get("title", "")) + " " + desc).lower()
    score = 0
    hits = [m for m in MATCH if m in text]
    score += min(2 * len(hits), 8)
    if ts is not None:
        days = (now - ts) / 86400.0
        score += 3 if days < 1 else (2 if days < 3 else 1)
    remote = ("remote" in text) or ("wfh" in text) or ("work from home" in text) or ("home office" in text)
    if remote:
        score += 2
    out.append({"title": j.get("title"), "company": j.get("companyName") or j.get("company"),
                "location": j.get("location"), "url": url, "posted": posted,
                "match_score": score, "source": "apify/linkedin",
                "easy_apply": "yes" if j.get("easyApplyUrl") else "?",
                "remote": remote, "description": desc})

out.sort(key=lambda x: -x["match_score"])
json.dump(out, open("jobs_queue.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("QUEUED %d fresh jobs -> jobs_queue.json" % len(out))
for j in out[:8]:
    print("  [%s] %s @ %s (%s, %s)" % (j["match_score"], j["title"], j["company"], j["location"], j["posted"][:10]))
