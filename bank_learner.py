#!/usr/bin/env python3
"""
Chameleon Self-Learning Engine (#6):
extracts skill phrases from jd_*.txt job descriptions,
adds NEW unique skills to bank.json skills_pool (auto-learning),
and reports candidates needing manual review.
Usage: python3 bank_learner.py [jd_file ...]
"""
import glob, json, re, sys

KNOWN_PAT = re.compile(
 r"\b(SEM|SEO|CRM|CMS|ERP|KPI|ROAS|CPA|CPC|B2B|B2C|PR|UX|UI|GA4|SQL|API)s?\b", re.I)
SKILL_WORDS = [
 "marketing","advertising","branding","copywriting","content creation",
 "social media","community management","influencer marketing","email marketing",
 "performance marketing","media buying","google ads","meta ads","paid media",
 "campaign management","market research","public relations","event management",
 "lead generation","sales enablement","product marketing","growth marketing",
 "crm","analytics","data analysis","a/b testing","marketing automation",
 "seo","sem","asana","jira","photoshop","canva","figma","video editing",
 "project management","stakeholder management","budget management",
 "team leadership","agile","notion","hubspot","mailchimp","google analytics",
 "crm systems","content strategy","storytelling","localization","translation",
 "negotiation","presentation","press releases","media relations","loyalty",
 "retention","acquisition","fintech","ecommerce","saas","web3","crypto"]

def extract(text):
    t = " " + text.lower().replace("‑","-") + " "
    found = set()
    for w in SKILL_WORDS:
        if re.search(r"(?<![a-z])" + re.escape(w) + r"(?![a-z])", t):
            found.add(w)
    found |= {m.upper() for m in KNOWN_PAT.findall(text)}
    return found

bank = json.load(open("bank.json", encoding="utf-8"))
pool = set()
for v in bank["skills_pool"].values():
    pool |= set(x.lower() for x in v)
before = len(pool)

files = sys.argv[1:] or sorted(glob.glob("jd_*.txt"))
all_skills = set()
for f in files:
    try:
        all_skills |= extract(open(f, encoding="utf-8", errors="ignore").read())
    except FileNotFoundError:
        pass

new = {s for s in all_skills if s.lower() not in pool}
for s in new:
    bank["skills_pool"].setdefault("learned_from_jds", []).append(s)
    pool.add(s.lower())

json.dump(bank, open("bank.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"files scanned: {len(files)}")
print(f"skills found: {len(all_skills)} | NEW added to bank: {len(new)} ({before} -> {len(pool)})")
for s in sorted(new):
    print("  +", s)
