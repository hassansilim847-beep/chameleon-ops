#!/usr/bin/env python3
"""
tg_account.py - Direct Telegram account bridge over WSS (no external server, no credits).
Needs env: TELEGRAM_SESSION_STRING, TELEGRAM_API_ID, TELEGRAM_API_HASH
Usage:
  python3 tg_account.py test
  python3 tg_account.py send <chat_id_or_username> <text...>
  python3 tg_account.py read <chat_id_or_username> [n=5]
"""
import asyncio, os, sys

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.network.connection.tcpobfuscated import ConnectionTcpObfuscated
try:
    from websockets.asyncio.client import connect as ws_connect
except ImportError:
    from websockets import connect as ws_connect

HOSTS = {1: "pluto", 2: "venus", 3: "aurora", 4: "vesta", 5: "flora"}
HASSAN = 6434711549


class WsStream:
    def __init__(self, ws):
        self.ws = ws
        self.buf = bytearray()
        self.pending = bytearray()
        self.cond = asyncio.Condition()

    async def attach(self):
        self._task = asyncio.create_task(self._pump())

    async def _pump(self):
        try:
            async for msg in self.ws:
                async with self.cond:
                    self.buf += msg
                    self.cond.notify_all()
        except Exception:
            pass

    async def readexactly(self, n):
        while True:
            async with self.cond:
                if len(self.buf) >= n:
                    out = bytes(self.buf[:n])
                    del self.buf[:n]
                    return out
                await self.cond.wait()

    def write(self, data):
        self.pending += data

    async def drain(self):
        if self.pending:
            data = bytes(self.pending)
            self.pending.clear()
            try:
                await self.ws.send(data)
            except Exception:
                pass

    def close(self):
        try:
            asyncio.get_event_loop().create_task(self.ws.close())
        except Exception:
            pass

    async def wait_closed(self):
        try:
            await self.ws.close()
        except Exception:
            pass


class ConnectionWsObf(ConnectionTcpObfuscated):
    async def _connect(self, timeout=None, ssl=None):
        ws = await ws_connect(f"wss://{self._ip}/apiws", max_size=None,
                              ping_interval=None, open_timeout=20,
                              subprotocols=["binary"])
        stream = WsStream(ws)
        self._reader = stream
        self._writer = stream
        self._codec = self.packet_codec(self)
        self._init_conn()
        await self._writer.drain()
        await stream.attach()


ORIG = os.environ["TELEGRAM_SESSION_STRING"]


class S(StringSession):
    def __init__(self):
        StringSession.__init__(self, ORIG)
        self.set_dc(self.dc_id, HOSTS[self.dc_id] + ".web.telegram.org", 443)

    def save(self):
        return ORIG


client = TelegramClient(S(), int(os.environ["TELEGRAM_API_ID"]),
                        os.environ["TELEGRAM_API_HASH"], connection=ConnectionWsObf)


async def main():
    act = sys.argv[1] if len(sys.argv) > 1 else "test"
    await client.connect()
    if act == "test":
        me = await asyncio.wait_for(client.get_me(), timeout=35)
        print("BRIDGE_OK:", me.first_name, "| id:", me.id)
    elif act == "send":
        chat, text = sys.argv[2], " ".join(sys.argv[3:])
        chat = int(chat) if chat.lstrip("-").isdigit() else chat
        m = await asyncio.wait_for(client.send_message(chat, text), timeout=60)
        print("SENT_OK id:", m.id, "| chat:", chat)
    elif act == "read":
        chat = sys.argv[2]
        n = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        chat = int(chat) if chat.lstrip("-").isdigit() else chat
        msgs = await asyncio.wait_for(client.get_messages(chat, limit=n), timeout=60)
        for m in reversed(msgs):
            who = getattr(m.sender, "first_name", None) or getattr(m.sender, "username", "") or m.sender_id
            print(f"[{m.date.strftime('%m-%d %H:%M')}] {who}: {(m.text or '')[:200]}")
    await client.disconnect()

asyncio.run(main())
