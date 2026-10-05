#!/usr/bin/env python3
# notify_bots.py — إشعارات منظومة الحرباء عبر البوتين (Bot API HTTPS)
# Usage:
#   python3 notify_bots.py apps  "نص الرسالة"   -> سجل التقديمات @Ydvdhsbot
#   python3 notify_bots.py replies "نص الرسالة"  -> بوت الردود @Sjgddygsgcsbot
#   python3 notify_bots.py both   "نص الرسالة"   -> الاتنين
import json, os, sys, time, urllib.request, urllib.parse

HASSAN_CHAT = "6434711549"  # chat id ثابت لحسن

def _load_env():
    env = {}
    try:
        with open("/app/.agents/.env") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    env[k.strip()] = v.strip().strip('"').strip("'")
    except Exception:
        pass
    return env

def send(token, text, chat=HASSAN_CHAT):
    data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data)
    with urllib.request.urlopen(req, timeout=20) as r:
        res = json.loads(r.read())
    return res.get("ok", False)

def notify(target, text):
    env = {**os.environ, **_load_env()}
    tokens = {
        "apps":   env.get("TELEGRAM_BOT_TOKEN_3"),   # @Ydvdhsbot سجل التقديمات
        "replies": env.get("TELEGRAM_BOT_TOKEN_4"), # @Sjgddygsgcsbot بوت الردود
    }
    if target == "both":
        targets = ["apps", "replies"]
    else:
        targets = [target]
    ok_all = True
    for t in targets:
        tok = tokens.get(t)
        if not tok:
            print(f"[{t}] NO TOKEN"); ok_all = False; continue
        try:
            ok = send(tok, text)
            print(f"[{t}] {'OK' if ok else 'FAIL'}")
            ok_all = ok_all and ok
        except Exception as e:
            print(f"[{t}] ERROR: {e}"); ok_all = False
        time.sleep(1)
    return ok_all

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "apps"
    text = sys.argv[2] if len(sys.argv) > 2 else "(empty)"
    sys.exit(0 if notify(target, text) else 1)
