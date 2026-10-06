#!/usr/bin/env python3
"""
Chameleon Autofill v3 - تعبئة مودال Easy Apply كاملًا في أمر واحد عبر CDP
يدعم: حقن CV + نصوص + قوائم منسدلة (select) + Cover Letter + تقديم
Usage: python3 autofill_modal.py <WSS> <cv.json> <cv.pdf> <answers.json> [--submit]
"""
import asyncio, base64, json, sys

import websockets

WSS, CVJ, PDF, ANSJ = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
SUBMIT = "--submit" in sys.argv

cfg = json.load(open(ANSJ, encoding="utf-8"))
cvj = json.load(open(CVJ, encoding="utf-8"))
b64 = base64.b64encode(open(PDF, "rb").read()).decode()
payload = {"answers": cfg.get("answers", []), "phone": cfg.get("phone", "1013821957"),
           "cover": cvj.get("cover_letter", ""), "b64": b64,
           "fname": "Hasan_CV.pdf", "submit": SUBMIT}

JS = """
(async () => {
  try {
  const C = %s;
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const dlg = () => document.querySelector('dialog') || document.querySelector('div[role=dialog]');
  const txt = () => dlg() ? dlg().innerText : '';
  const vis = e => e && e.offsetParent !== null;
  const findBtn = (...keys) => [...document.querySelectorAll('button')].filter(vis)
      .find(b => keys.some(k => (b.textContent||'').trim().includes(k)));
  const setVal = (inp, val) => {
    if (inp.tagName === 'SELECT') {
      const opt = [...inp.options].find(o => o.text.toLowerCase().includes(String(val).toLowerCase()))
        || [...inp.options].find(o => String(val).toLowerCase().includes(o.text.toLowerCase()) && o.text.length > 2)
        || [...inp.options].find(o => o.value && o.text !== 'None' && !/select|تحديد/i.test(o.text) && o.text.length > 2);
      if (!opt) return 'NO_OPT:' + val;
      inp.value = opt.value; opt.selected = true;
      inp.dispatchEvent(new Event('input', {bubbles:true}));
      inp.dispatchEvent(new Event('change', {bubbles:true}));
      return 'SEL:' + opt.text;
    }
    const proto = inp.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    Object.getOwnPropertyDescriptor(proto, 'value').set.call(inp, val);
    inp.dispatchEvent(new Event('input', {bubbles:true}));
    inp.dispatchEvent(new Event('change', {bubbles:true}));
    return 'OK';
  };
  const fieldsIn = () => dlg() ? [...dlg().querySelectorAll('input,textarea,select')].filter(vis) : [];
  const qField = (qkey) => {
    for (const f of fieldsIn()) {
      if (f.type === 'hidden' || f.type === 'file') continue;
      let node = f;
      for (let i = 0; i < 9 && node; i++) {
        node = node.parentElement;
        try {
          if (node && node.innerText && node.innerText.toLowerCase().includes(qkey.toLowerCase())
              && node.querySelectorAll('input,select').length === 1) return f;
        } catch (e) {}
      }
    }
    return null;
  };
  const log = [];
  const clickNext = async () => { const b = findBtn('التالي','Next'); if(!b) return false; b.click(); await sleep(2500); return true; };

  await sleep(800);
  for (let step = 0; step < 20; step++) {
    const t = txt();
    if (!t) return 'NO_MODAL';
    if (t.includes('تم إرسال طلب التقديم') || t.includes('Application submitted')) return 'SUBMITTED|' + log.join(';');
    if (/Contact info|معلومات الاتصال/.test(t)) {
      const empt = fieldsIn().filter(i => ['text','tel'].includes(i.type) && !i.value);
      for (const e of empt) { setVal(e, C.phone); log.push('phone'); }
      await sleep(700);
      if (!await clickNext()) return 'STUCK_CONTACT'; continue;
    }
    if (/سيرة ذاتية|Resume/.test(t) && t.includes('DOC')) {
      let up = document.querySelector('input[type=file]');
      if (!up) { const b = findBtn('تحميل السيرة الذاتية','Upload resume'); if (b) { b.click(); await sleep(1500); } up = document.querySelector('input[type=file]'); }
      if (!up) return 'NO_UPLOAD_INPUT';
      const bin = atob(C.b64); const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      const file = new File([bytes], C.fname, {type: 'application/pdf'});
      const dt = new DataTransfer(); dt.items.add(file); up.files = dt.files;
      up.dispatchEvent(new Event('input', {bubbles:true})); up.dispatchEvent(new Event('change', {bubbles:true}));
      for (let w = 0; w < 12; w++) { await sleep(1500); const tt = txt(); if (tt.includes('تم تحميل السيرة الذاتية بنجاح') || tt.includes('تم تحميل ملف')) break; }
      log.push('resume=' + (up.files[0] ? up.files[0].name : 'none'));
      if (!await clickNext()) return 'STUCK_RESUME'; continue;
    }
    if (/Additional Questions|أسئلة إضافية/.test(t)) {
      const answered = [];
      for (const {q, a} of C.answers) {
        const f = qField(q);
        if (f) { const r = setVal(f, a); answered.push(q.slice(0,10) + '=' + r); await sleep(400); }
      }
      const missing = fieldsIn().filter(f => (f.hasAttribute('required') || f.getAttribute('aria-required') === 'true')
        && !f.value && f.type !== 'file');
      if (missing.length) {
        let qt = '';
        for (let n = missing[0], i = 0; i < 9 && n; i++, n = n.parentElement) {
          const sib = n.innerText || ''; if (sib && sib.length > 5) { qt = sib.split('\\n')[0]; break; }
        }
        return 'UNKNOWN_Q|' + (qt || 'unlabeled') + '|answered=' + answered.length;
      }
      // v4: maxlength-aware answer compaction
      if (answered.length && answered.length === qs.length) {} else if (invalidCount > 0 && unanswered === 0) {
        const bad = [...dlg().querySelectorAll('input')].filter(i => i.maxLength > 0 && i.value.length >= i.maxLength);
        for (const i of bad) { const d = (i.value.match(/\d+/g)||[]).join(''); if (d && d.length <= i.maxLength) { i.value = ''; setVal(i, d); } }
      }
      const rev = findBtn('مراجعة','Review'); if (!rev) return 'STUCK_QUESTIONS';
      rev.click(); await sleep(2000); continue;
    }
    if (/مراجعة استمارتك|Review your application/.test(t)) {
      const ta = dlg().querySelector('textarea');
      if (ta && C.cover) { setVal(ta, C.cover); log.push('cover'); }
      if (!C.submit) return 'AT_REVIEW|' + log.join(';');
      const sub = findBtn('تقديم الاستمارة','Submit application','إرسال طلب');
      if (!sub) return 'NO_SUBMIT_BTN';
      sub.click(); await sleep(3000); continue;
    }
    await sleep(1800);
  }
  return 'LOOP_END|' + txt().slice(0, 120);
  } catch (e) { return 'JS_ERR|' + (e && e.message); }
})()
""" % json.dumps(payload)

async def main():
    async with websockets.connect(WSS, max_size=20_000_000, ping_interval=20) as ws:
        mid = 0
        async def call(method, params=None):
            nonlocal mid
            mid += 1
            await ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
            while True:
                msg = json.loads(await asyncio.wait_for(ws.recv(), 300))
                if msg.get("id") == mid:
                    return msg
        await call("Runtime.enable")
        res = await call("Runtime.evaluate", {"expression": JS, "awaitPromise": True,
                                              "returnByValue": True, "userGesture": True})
        body = res.get("result", res)
        err = body.get("exceptionDetails")
        if err:
            print("EXC:", json.dumps(err)[:500])
        print(body.get("result", {}).get("value") or body.get("value"))

asyncio.run(main())
