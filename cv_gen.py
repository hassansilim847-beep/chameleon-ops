#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chameleon CV Generator - منظومة الحرباء
Input: job description + identity + experience bank -> tailored ATS-friendly PDF CV
Usage: python3 cv_gen.py --jd-file jd.txt --title "..." --company "..." --out cv_x
"""
import json, sys, os, argparse, urllib.request

WORKDIR = os.path.dirname(os.path.abspath(__file__))

# guard: fpdf X-drift fix (empty cells / templates leave X past margin -> FPDFException)
from fpdf import FPDF as _FPDF
_oc, _om = _FPDF.cell, _FPDF.multi_cell
def _fixw(self, w):
    if not w:
        w = self.w - self.r_margin - self.get_x()
    if w < 12:
        self.set_x(self.l_margin)
def _cell(self, w=None, *a, **k):
    _fixw(self, w if w is not None else 0)
    return _oc(self, w, *a, **k)
def _multi(self, w=None, *a, **k):
    _fixw(self, w if w is not None else 0)
    return _om(self, w, *a, **k)
_FPDF.cell, _FPDF.multi_cell = _cell, _multi

import re as _re
def _san(o):
    if isinstance(o, dict): return {k: _san(v) for k, v in o.items()}
    if isinstance(o, list): return [_san(x) for x in o]
    if isinstance(o, str):
        s = o.replace("\u2019","'").replace("\u2018","'").replace("\u201c",'"').replace("\u201d",'"')
        s = _re.sub(r"[^\x09\x0a\x0d\x20-\x7e\xa0-\xff]", " ", s)
        s = _re.sub(r"(\S{55})\S+", r"\1", s)   # break absurdly long tokens
        s = _re.sub(r"[ ]{2,}", " ", s)
        return s.strip()
    return o


def load_json(name, default):
    p = os.path.join(WORKDIR, name)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return default

def http_json(url, body, headers):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0", **headers})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())

def gen_gemini(system, user):
    key = os.environ["GEMINI_API_KEY"]
    d = http_json(f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash:generateContent?key={key}",
        {"contents": [{"parts": [{"text": system + "\n\n" + user}]}],
         "generationConfig": {"responseMimeType": "application/json", "temperature": 0.5}},
        {"Authorization": ""})
    return d["candidates"][0]["content"]["parts"][0]["text"]

def gen_nim(system, user):
    key = os.environ["NVIDIA_NIM_API_KEY"]
    d = http_json("https://integrate.api.nvidia.com/v1/chat/completions",
        {"model": "deepseek-ai/deepseek-v4.1-flash",
         "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
         "temperature": 0.5, "max_tokens": 3000},
        {"Authorization": f"Bearer {key}"})
    return d["choices"][0]["message"]["content"]

def gen_groq(system, user):
    key = os.environ["GROQ_API_KEY"]
    d = http_json("https://api.groq.com/openai/v1/chat/completions",
        {"model": "qwen/qwen3.8-27b",
         "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
         "temperature": 0.5},
        {"Authorization": f"Bearer {key}"})
    return d["choices"][0]["message"]["content"]

def gen_or1(system, user):
    key = os.environ["OPENROUTER_API_KEY_1"]
    d = http_json("https://openrouter.ai/api/v1/chat/completions",
        {"model": "qwen/qwen3.8-27b:free",
         "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
         "temperature": 0.5},
        {"Authorization": f"Bearer {key}"})
    return d["choices"][0]["message"]["content"]

def gen_or2(system, user):
    key = os.environ["OPENROUTER_API_KEY_2"]
    d = http_json("https://openrouter.ai/api/v1/chat/completions",
        {"model": "qwen/qwen3.8-27b:free",
         "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
         "temperature": 0.5},
        {"Authorization": f"Bearer {key}"})
    return d["choices"][0]["message"]["content"]

def groq(system, user):
    last_err = None
    for name, fn in [("gemini", gen_gemini), ("nim", gen_nim), ("groq", gen_groq), ("or1", gen_or1), ("or2", gen_or2)]:
        try:
            txt = fn(system, user)
            start = txt.find("{"); end = txt.rfind("}")
            if start >= 0 and end > start:
                return json.loads(txt[start:end+1])
            last_err = RuntimeError(f"{name}: no json in response")
        except Exception as e:
            last_err = e
            print(f"gen via {name} failed: {str(e)[:120]}", file=sys.stderr)
    raise RuntimeError(f"all generators failed: {last_err}")

SYSTEM = """You are an expert CV writer for the Egyptian job market. Build a tailored, ATS-friendly English CV.
Rules:
- Core experience/education comes ONLY from the provided BANK and IDENTITY. Never invent degrees, employers, dates or languages.
- JD-SHAPING: If the job description lists skills, tools or concepts MISSING from the bank, mirror them naturally and confidently into the skills list and experience bullets (professional phrasing, never mention gaps). The bank's skills_pool is your vocabulary; the JD is the target shape - mold the CV fully onto it.
- Mirror the job description's keywords naturally in summary and skills.
- If the bank lacks relevant experience, use transferable-skills framing (fast learner, communication, organization, tools) - never fake employers.
- Education: if provided, one neutral line placed low unless the job values it. If not provided, omit the section entirely.
- Cover letter: 90-120 words, energetic, no flattery templates.
Return JSON: {"headline": str, "summary": str, "skills": [str], "experience": [{"title":str,"org":str,"period":str,"bullets":[str]}], "education": str|null, "languages": [str], "cover_letter": str, "screening": [{"q":str,"a":str}]}"""

def build_pdf(data, ident, out_path, template=0):
    from fpdf import FPDF
    FD = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    FDB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    def setf(pdf, style="", size=10.5):
        pdf.set_font("dejavu", style, size)
    ACCENTS = [(31,78,121),(102,45,145),(0,102,71),(140,20,40),(120,80,20)]
    r,g,b = ACCENTS[template % len(ACCENTS)]
    pdf = FPDF()
    pdf.add_font("dejavu", "", FD)
    pdf.add_font("dejavu", "B", FDB)
    pdf.add_font("dejavu", "I", FD)
    pdf.set_auto_page_break(True, 18)
    pdf.add_page()
    # Header
    pdf.set_fill_color(r,g,b); pdf.rect(0, 0, 210, 34, "F")
    setf(pdf, "B", 22); pdf.set_text_color(255,255,255)
    pdf.set_xy(12, 8); pdf.cell(0, 10, ident["name"], ln=1)
    setf(pdf, "", 10)
    pdf.set_xy(12, 20); pdf.cell(0, 6, f"{ident['phone']}  |  {ident['email']}  |  {ident.get('location','Egypt')}", ln=1)
    pdf.set_xy(12, 26); pdf.cell(0, 6, data.get("headline",""), ln=1)

    def section(title):
        pdf.ln(3); setf(pdf, "B", 12); pdf.set_text_color(r,g,b)
        pdf.cell(0, 7, title.upper(), ln=1); pdf.set_draw_color(r,g,b); pdf.set_line_width(0.4)
        y = pdf.get_y(); pdf.line(10, y, 200, y); pdf.set_text_color(30,30,30)

    pdf.set_text_color(30,30,30)
    section("Professional Summary")
    setf(pdf, "", 10.5)
    pdf.multi_cell(0, 5.5, data.get("summary",""))

    section("Core Skills")
    setf(pdf, "", 10.5)
    skills = data.get("skills", [])
    line = ""
    for s in skills:
        if len(line) + len(s) > 90:
            pdf.cell(0, 5.5, line, ln=1); line = ""
        line += ("• " + s + "  ") if not line else (s + "  ")
    if line: pdf.cell(0, 5.5, line.strip(), ln=1)

    if data.get("experience"):
        section("Professional Experience")
        for e in data["experience"]:
            setf(pdf, "B", 11)
            pdf.cell(0, 6, f"{e.get('title','')} - {e.get('org','')}", ln=1)
            setf(pdf, "I", 9); pdf.set_text_color(90,90,90)
            pdf.cell(0, 5, e.get("period",""), ln=1); pdf.set_text_color(30,30,30)
            setf(pdf, "", 10)
            for bt in e.get("bullets", []):
                pdf.multi_cell(0, 5, "• " + bt)
            pdf.ln(1)

    if data.get("education"):
        section("Education")
        setf(pdf, "", 10.5); pdf.multi_cell(0, 5.5, data["education"])

    section("Languages")
    setf(pdf, "", 10.5)
    pdf.cell(0, 5.5, "  ".join(data.get("languages", [])), ln=1)

    pdf.output(out_path)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jd-file", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--company", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--template", type=int, default=0)
    args = ap.parse_args()

    ident = load_json("cv_identity_seed.json", {})
    bank = load_json("bank.json", {"blocks": []})
    jd = open(args.jd_file, encoding="utf-8").read()

    user = f"""IDENTITY: {json.dumps(ident, ensure_ascii=False)}
BANK: {json.dumps(bank, ensure_ascii=False)}
JOB TITLE: {args.title}
COMPANY: {args.company}
JOB DESCRIPTION: {jd}
Build the tailored CV JSON now."""
    data = groq(SYSTEM, user)
    data["languages"] = data.get("languages") or ["Arabic (Native)", "English", "German"]
    data = _san(data); ident = _san(ident)

    # auto-learn: JD-shaped skills not yet in bank -> grow skills_pool
    try:
        pool = bank.setdefault("skills_pool", {})
        known = {s.lower() for v in pool.values() for s in (v if isinstance(v, list) else [])}
        learned = pool.setdefault("learned_from_jds", [])
        for s in data.get("skills", []):
            if s and s.lower() not in known and s not in learned:
                learned.append(s)
        with open(WORKDIR + "/bank.json", "w", encoding="utf-8") as f:
            json.dump(bank, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    build_pdf(data, ident, args.out + ".pdf", args.template)
    with open(args.out + ".json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("OK", args.out + ".pdf")
    print("HEADLINE:", data.get("headline","")[:100])

if __name__ == "__main__":
    main()
