#!/usr/bin/env python3
"""
Chameleon CDP CV Injector - حقن ملف PDF في حقل رفع LinkedIn بدون نافذة نظام
Usage: python3 inject_cv_cdp.py <WSS_DEBUG_URL> <PDF_PATH> <FILENAME>
Connects to the browser session's CDP debug endpoint, builds a real File object
in-page from base64 data, and sets it on the modal's input[type=file].
"""
import asyncio, base64, json, sys, re

import websockets

WSS, PDF, FNAME = sys.argv[1], sys.argv[2], sys.argv[3]

raw = open(PDF, "rb").read()
if len(raw) > 1_800_000:
    print("ERROR: PDF too large for injection", len(raw)); sys.exit(1)
b64 = base64.b64encode(raw).decode()

JS = """
(async () => {
  const b64 = "%s";
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  const file = new File([bytes], "%s", {type: "application/pdf"});
  const inputs = Array.from(document.querySelectorAll('input[type=file]'));
  if (!inputs.length) return "NO_INPUT";
  const input = inputs[inputs.length - 1];
  const dt = new DataTransfer();
  dt.items.add(file);
  input.files = dt.files;
  input.dispatchEvent(new Event("input", {bubbles: true}));
  input.dispatchEvent(new Event("change", {bubbles: true}));
  const f = input.files && input.files[0];
  return f ? ("INJECTED|" + f.name + "|" + f.size + "|inputs=" + inputs.length) : "SET_FAILED";
})()
""" % (b64, FNAME)


async def main():
    async with websockets.connect(WSS, max_size=20_000_000, ping_interval=20) as ws:
        mid = 0

        async def call(method, params=None):
            nonlocal mid
            mid += 1
            await ws.send(json.dumps({"id": mid, "method": method,
                                      "params": params or {}}))
            while True:
                msg = json.loads(await asyncio.wait_for(ws.recv(), 120))
                if msg.get("id") == mid:
                    if "error" in msg:
                        return {"error": msg["error"]}
                    return msg.get("result", {})
                # ignore events

        await call("Runtime.enable")
        res = await call("Runtime.evaluate", {
            "expression": JS, "awaitPromise": True,
            "returnByValue": True, "userGesture": True})
        if "error" in res:
            print("CDP_ERROR:", res["error"]); sys.exit(2)
        val = res.get("result", {}).get("value", "EMPTY")
        print(val if isinstance(val, str) else str(val))

asyncio.run(main())
