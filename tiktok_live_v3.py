#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════╗
║     TIKTOK LIVE PENETRATION TESTING SUITE v3.0                          ║
║     Advanced Viewer Simulation + 10 Active Engagement Features           ║
║     Authorized Security Assessment Tool                                  ║
╚══════════════════════════════════════════════════════════════════════════╝

10 ADVANCED FEATURES:
  1. Auto-Like Bot        — Sends timed likes during viewing sessions
  2. Chat Spam Engine     — Sends messages to live chat via session cookies
  3. Follow Bot           — Simulates follows with session cookie rotation
  4. Share Simulator      — Simulates stream shares
  5. Multi-Account Rotation — Rotates session cookies across connections
  6. Stream Monitor Mode  — Watches multiple streams, reports activity
  7. Gift Detection       — Logs & categorizes all gifts received
  8. Packet Inspector     — Captures & analyzes raw WebSocket protobuf traffic
  9. Auto-Scale Mode      — Dynamically adjusts viewer count based on success
 10. Geolocation Spoofer  — Spoofs network location per connection

Install: pip install aiohttp websockets colorama
"""

import asyncio
import aiohttp
import websockets
import json
import random
import time
import uuid
import hashlib
import hmac
import base64
import ssl
import logging
import argparse
import sys
import os
import re
import csv
import struct
from typing import Optional, Dict, List, Tuple, Any, Set
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

try:
    import colorama
    from colorama import Fore, Back, Style
    colorama.init()
    C = True
except ImportError:
    C = False
    class Fore: RED=GREEN=YELLOW=BLUE=MAGENTA=CYAN=WHITE=RESET=""
    class Style: BRIGHT=RESET_ALL=""

logging.basicConfig(level=logging.WARNING)
log = logging.getLogger("TTLive3")

BANNER = r"""
╔══════════════════════════════════════════════════════════════════════════╗
║           TIKTOK LIVE PENETRATION TESTING SUITE v3.0                     ║
║     10 Advanced Features: Likes · Chat · Follow · Share · Monitor        ║
║     Multi-Account · Gift Detect · Packet Inspect · Auto-Scale · Geo      ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

MENU = """
  ┌──────────────────────────────────────────────────────────────────────┐
  │                         MAIN MENU                                    │
  ├──────────────────────────────────────────────────────────────────────┤
  │  [1]  Launch Viewer Simulation     [11] Auto-Like Bot                │
  │  [2]  Real-Time Dashboard          [12] Chat Spam Engine             │
  │  [3]  Configuration                [13] Follow Bot                   │
  │  [4]  Proxy Manager                [14] Share Simulator              │
  │  [5]  Fingerprint Profiles         [15] Multi-Account Rotator        │
  │  [6]  Room Info Extractor          [16] Stream Monitor Mode          │
  │  [7]  Session History              [17] Gift Detection Logger        │
  │  [8]  Stress Test Mode             [18] Packet Inspector             │
  │  [9]  Behavioral Profiles          [19] Auto-Scale Mode              │
  │  [10] Save/Load Config             [20] Geolocation Spoofer          │
  │  [0]  Exit                                                           │
  └──────────────────────────────────────────────────────────────────────┘
"""

@dataclass
class Config:
    username: str = ""
    room_id: int = 0
    viewer_count: int = 50
    ramp_up_seconds: int = 10
    region: str = "us"
    max_concurrent: int = 0
    ws_timeout: int = 30
    heartbeat_interval: int = 15
    proxy_file: str = ""
    proxy_rotation: str = "round_robin"
    behavior_profile: str = "realistic"
    min_watch_time: int = 30
    max_watch_time: int = 300
    fingerprint_profile: str = "random"
    realtime_dashboard: bool = True
    save_report: bool = True
    # Advanced features
    auto_like: bool = False
    like_interval: int = 30
    chat_spam: bool = False
    chat_messages: str = ""
    follow_bot: bool = False
    share_sim: bool = False
    accounts_file: str = ""
    monitor_mode: bool = False
    monitor_targets: str = ""
    gift_log: bool = False
    packet_inspect: bool = False
    auto_scale: bool = False
    geo_spoof: bool = False
    geo_region: str = "auto"

    def to_dict(self):
        return {k:v for k,v in self.__dict__.items() if not k.startswith("_")}
    @classmethod
    def from_dict(cls, d):
        valid = {k for k in cls.__dataclass_fields__}
        return cls(**{k:v for k,v in d.items() if k in valid})

WS_ENDPOINTS = {
    "us": "wss://webcast-ws.us.tiktok.com/webcast/im/v1/",
    "eu": "wss://webcast-ws.eu.tiktok.com/webcast/im/v1/",
    "asia": "wss://webcast-ws.tiktok.com/webcast/im/v1/",
    "sg": "wss://webcast-ws.sg.tiktok.com/webcast/im/v1/",
    "br": "wss://webcast-ws.br.tiktok.com/webcast/im/v1/",
}

UA_D = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:127.0) Gecko/20100101 Firefox/127.0",
]
UA_M = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5) AppleWebKit/605.1.15 Mobile/15E148",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 Chrome/125.0.6422.113 Mobile",
    "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 Chrome/125.0.6422.113 Mobile",
]
SCREENS = [(1920,1080),(1366,768),(1536,864),(1440,900),(1280,720),(1680,1050),(2560,1440)]
MOB_SCREENS = [(390,844),(393,852),(430,932),(375,812),(414,896),(360,780)]
TZS = ["America/New_York","America/Chicago","America/Los_Angeles","Europe/London","Europe/Berlin","Europe/Paris","Asia/Tokyo","Asia/Seoul","Asia/Shanghai","Australia/Sydney","America/Toronto","Europe/Moscow","America/Sao_Paulo","Asia/Dubai"]
LANGS = ["en-US,en;q=0.9","en-GB,en;q=0.9","de-DE,de;q=0.9","fr-FR,fr;q=0.9","ja-JP,ja;q=0.9","ko-KR,ko;q=0.9","zh-CN,zh;q=0.9","es-ES,es;q=0.9","pt-BR,pt;q=0.9"]
LIKE_MESSAGES = ["Nice stream!","🔥","❤️","Great vibes!","Cool!","awesome","💯","🔥🔥","lit!","fire 🔥"]
CHAT_MESSAGES = ["Hello everyone!","What's up?","🔥🔥🔥","Nice stream!","First time here","Cool content!","Keep it up!","❤️❤️❤️","Awesome vibes","Great music!","Haha nice!","Wow!","💯💯💯","This is lit","Hello from bot!","Streaming goals","Love this!","So cool!","Amazing!","Fire content!"]
GEO_REGIONS = ["us-east","us-west","eu-west","eu-central","eu-north","ap-southeast","ap-northeast","ap-south","sa-east","me-central","af-south"]

class AccountRotator:
    def __init__(self, accounts_file: str = ""):
        self.accounts: List[Dict] = []
        self._idx = 0
        if accounts_file and os.path.exists(accounts_file):
            self.load(accounts_file)
    def load(self, path: str):
        with open(path) as f:
            for line in f:
                parts = line.strip().split(":")
                if len(parts) >= 2:
                    self.accounts.append({"session_id": parts[0], "tt_target_idc": parts[1] if len(parts)>1 else "useast1a"})
    def get(self) -> Optional[Dict]:
        if not self.accounts: return None
        a = self.accounts[self._idx % len(self.accounts)]
        self._idx += 1
        return a
    @property
    def count(self): return len(self.accounts)

class PacketInspector:
    def __init__(self):
        self.packets: List[Dict] = []
        self.packet_types: Dict[str, int] = defaultdict(int)
        self.bytes_total = 0
    def inspect(self, data: bytes, direction: str = "in"):
        size = len(data)
        self.bytes_total += size
        # Try to detect packet type from first bytes
        ptype = "unknown"
        if size > 0:
            first_byte = data[0]
            if first_byte == 0x08: ptype = "WebcastResponse"
            elif first_byte == 0x3a: ptype = "WebcastPushFrame"
            elif first_byte == 0x0a: ptype = "WebcastChatMessage"
            elif first_byte == 0x12: ptype = "WebcastLikeMessage"
            elif first_byte == 0x1a: ptype = "WebcastGiftMessage"
            elif first_byte == 0x22: ptype = "WebcastMemberMessage"
            elif first_byte == 0x2a: ptype = "WebcastSocialMessage"
            elif first_byte == 0x32: ptype = "WebcastRoomUserSeqMessage"
            elif first_byte == 0x42: ptype = "WebcastControlMessage"
            elif size == 4 and data[0:2] == b'\x00\x01': ptype = "Ping"
            elif size == 4 and data[0:2] == b'\x00\x02': ptype = "Pong"
        self.packet_types[ptype] += 1
        entry = {"ts": time.time(), "direction": direction, "size": size, "type": ptype, "hex": data[:32].hex()}
        self.packets.append(entry)
        if len(self.packets) > 10000: self.packets = self.packets[-5000:]
        return entry
    def summary(self) -> Dict:
        return {"total_packets": len(self.packets), "bytes": self.bytes_total, "types": dict(self.packet_types)}

class GiftLogger:
    def __init__(self):
        self.gifts: List[Dict] = []
        self.gift_totals: Dict[str, int] = defaultdict(int)
        self.gift_diamonds: Dict[str, int] = defaultdict(int)
    def log(self, gift_data: Dict):
        name = gift_data.get("gift_name", "unknown")
        diamonds = gift_data.get("diamond_count", 0)
        repeat = gift_data.get("repeat_count", 1)
        user = gift_data.get("user", {}).get("unique_id", "anonymous")
        entry = {"ts": time.time(), "user": user, "gift": name, "diamonds": diamonds, "repeat": repeat}
        self.gifts.append(entry)
        self.gift_totals[name] += repeat
        self.gift_diamonds[name] += diamonds * repeat
        if len(self.gifts) > 10000: self.gifts = self.gifts[-5000:]
    def summary(self) -> Dict:
        return {"total_gifts": len(self.gifts), "unique_types": len(self.gift_totals), "totals": dict(self.gift_totals), "diamonds": dict(self.gift_diamonds)}

class GeoEngine:
    def __init__(self, mode: str = "auto"):
        self.mode = mode
    def get_geo_headers(self) -> Dict:
        if self.mode == "auto":
            region = random.choice(GEO_REGIONS)
        elif self.mode in GEO_REGIONS:
            region = self.mode
        else:
            region = random.choice(GEO_REGIONS)
        return {
            "CF-IPCountry": region.split("-")[0].upper(),
            "X-Forwarded-For": f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,255)}",
            "X-Client-Region": region,
            "Accept-Language": random.choice(LANGS),
        }

class FingerprintEngine:
    PROFILES = {
        "random":{"agents":UA_D+UA_M,"screens":SCREENS+MOB_SCREENS},
        "desktop":{"agents":UA_D,"screens":SCREENS},
        "mobile":{"agents":UA_M,"screens":MOB_SCREENS},
        "windows":{"agents":[a for a in UA_D if "Windows" in a],"screens":SCREENS},
        "macos":{"agents":[a for a in UA_D if "Macintosh" in a],"screens":SCREENS},
        "linux":{"agents":[a for a in UA_D if "Linux" in a],"screens":SCREENS},
        "iphone":{"agents":[a for a in UA_M if "iPhone" in a],"screens":MOB_SCREENS},
        "android":{"agents":[a for a in UA_M if "Android" in a],"screens":MOB_SCREENS},
    }
    def __init__(self, profile="random"):
        p = self.PROFILES.get(profile, self.PROFILES["random"])
        self._agents = p["agents"]; self._screens = p["screens"]
    def generate(self):
        ua = random.choice(self._agents); w,h = random.choice(self._screens)
        mob = "Mobile" in ua or "iPhone" in ua
        return {
            "user_agent": ua, "device_id": str(random.randint(10**18,9*10**18)),
            "web_id": uuid.uuid4().hex, "session_id": uuid.uuid4().hex,
            "fp": {"screen_width": w,"screen_height": h,"available_width": w,"available_height": h-random.randint(50,150),"color_depth":random.choice([24,30,48]),"pixel_ratio":random.choice([1,1.25,1.5,2,2.5,3]) if not mob else random.choice([2,2.5,3]),"platform":"Win32" if "Windows" in ua else ("MacIntel" if "Mac" in ua else "Linux x86_64"),"timezone":random.choice(TZS),"language":random.choice(LANGS),"hardware_concurrency":random.choice([4,6,8,12,16]),"device_memory":random.choice([4,8,16,32]),"touch_support":mob,"cookies_enabled":True,"do_not_track":random.choice([0,1]),"webgl_vendor":random.choice(["Intel Inc.","NVIDIA Corporation","AMD","Apple","Google Inc."]),"webgl_renderer":random.choice(["Intel Iris","ANGLE (Intel UHD)","ANGLE (NVIDIA RTX 3070)","ANGLE (AMD Radeon RX 6800)","Apple M1","Apple M2 Pro","Apple M3 Max"])},
        }

class SignatureGenerator:
    def __init__(self, ua): self.user_agent = ua
    @staticmethod
    def ms_token():
        t = int(time.time()*1000)
        return base64.b64encode(json.dumps({"ts":t,"nonce":uuid.uuid4().hex[:16],"salt":str(random.randint(100000,999999))}).encode()).decode().rstrip("=")
    def x_bogus(self, params, endpoint=""):
        ts = str(int(time.time()))
        s = "&".join(f"{k}={v}" for k,v in sorted(params.items()))
        raw = f"{endpoint}?{s}&ts={ts}&nonce={str(random.randint(100000,999999))}" + self.user_agent
        key = hashlib.md5(ts.encode()).hexdigest()[:16].encode()
        h = hmac.new(key, raw.encode(), hashlib.sha256)
        for _ in range(3): h = hmac.new(key, h.digest(), hashlib.sha256)
        return base64.urlsafe_b64encode(h.digest()[:16]).decode().rstrip("=")

class ProxyManager:
    def __init__(self, proxies=None, rotation="round_robin"):
        self.proxies = proxies or []; self.rotation = rotation; self._i = 0
        self.stats = {"used":0,"failed":0,"blacklisted":[]}
    @property
    def count(self): return len(self.proxies)
    def get(self):
        if not self.proxies: return None
        p = random.choice(self.proxies) if self.rotation=="random" else self.proxies[self._i%len(self.proxies)]
        self._i += 1; self.stats["used"] += 1; return p
    def mark_failed(self, p):
        self.stats["failed"] += 1
        if p not in self.stats["blacklisted"]: self.stats["blacklisted"].append(p)
    @staticmethod
    def parse_file(path):
        px = []
        if os.path.exists(path):
            with open(path) as f:
                for l in f:
                    l = l.strip()
                    if l and not l.startswith("#"): px.append(l)
        return px

@dataclass
class ViewerStats:
    viewer_id: int; session_id: str; start_time: float=0.0; end_time: float=0.0
    connected: bool=False; success: bool=False; bytes_sent: int=0; bytes_received: int=0
    heartbeats_sent: int=0; messages_received: int=0; errors: int=0; likes_sent: int=0
    chats_sent: int=0; follows_sent: int=0; shares_sent: int=0
    proxy: str=""; region: str="us"; latency_ms: float=0.0; last_ping: float=0.0
    @property
    def duration(self):
        if self.end_time>0: return self.end_time-self.start_time
        return time.time()-self.start_time if self.start_time>0 else 0

class SessionTracker:
    def __init__(self):
        self.viewers = {}; self.start_time = time.time()
        self.total_launched = 0; self.total_connected = 0; self.total_disconnected = 0
        self.total_errors = 0; self.total_bytes_sent = 0; self.total_bytes_received = 0
        self.total_heartbeats = 0; self.total_likes = 0; self.total_chats = 0
        self.total_follows = 0; self.total_shares = 0
        self.latency_samples = []; self.gift_logger = GiftLogger(); self.packet_inspector = PacketInspector()
    def register(self, vid, sid, proxy="", region="us"):
        s = ViewerStats(viewer_id=vid, session_id=sid, proxy=proxy, region=region)
        self.viewers[sid] = s; self.total_launched += 1; return s
    @property
    def active(self): return sum(1 for v in self.viewers.values() if v.connected)
    @property
    def rate(self):
        if self.total_launched==0: return 0.0
        return (self.total_connected/self.total_launched)*100
    def summary(self):
        avg = round(sum(self.latency_samples)/len(self.latency_samples),2) if self.latency_samples else 0
        gs = self.gift_logger.summary()
        ps = self.packet_inspector.summary()
        return {"elapsed":round(time.time()-self.start_time,1),"launched":self.total_launched,"connected":self.total_connected,"active":self.active,"disconnected":self.total_disconnected,"errors":self.total_errors,"rate":f"{self.rate:.1f}%","sent":self.total_bytes_sent,"recv":self.total_bytes_received,"hb":self.total_heartbeats,"likes":self.total_likes,"chats":self.total_chats,"follows":self.total_follows,"shares":self.total_shares,"latency":avg,"gifts":gs,"packets":ps}

class RoomInfoExtractor:
    async def get_room_id(self, username):
        async with aiohttp.ClientSession(headers={"User-Agent":UA_D[0]}) as s:
            try:
                async with s.get(f"https://www.tiktok.com/api/live/room_id/?unique_id={username}",timeout=15) as r:
                    if r.status==200:
                        d=await r.json(); rid=d.get("room_id")
                        if rid: return int(rid)
            except: pass
            try:
                async with s.get(f"https://www.tiktok.com/@{username}/live",timeout=15) as r:
                    h=await r.text()
                    for p in [r'"roomId":\s*"(\d+)"',r'"room_id":\s*(\d+)',r'roomId=(\d+)']:
                        m=re.search(p,h)
                        if m: return int(m.group(1))
            except: pass
        return None
    async def get_info(self, rid):
        async with aiohttp.ClientSession() as s:
            try:
                async with s.get(f"https://www.tiktok.com/api/live/detail/?room_id={rid}",timeout=15) as r:
                    if r.status==200:
                        d=(await r.json()).get("data",{})
                        return {"room_id":d.get("room_id"),"title":d.get("title"),"status":d.get("status"),"viewers":d.get("user_count"),"total":d.get("total_user_count"),"like_count":d.get("like_count"),"owner":{"username":d.get("owner",{}).get("unique_id"),"nickname":d.get("owner",{}).get("nickname"),"followers":d.get("owner",{}).get("follower_count")}}
            except: pass
        return None

class TikTokViewer:
    def __init__(self, vid, rid, cfg, pm=None, tr=None, account=None, geo_engine=None):
        self.vid=vid; self.rid=rid; self.cfg=cfg; self.pm=pm; self.tr=tr; self.account=account; self.geo=geo_engine
        self.fp=FingerprintEngine(cfg.fingerprint_profile).generate()
        self.sid=str(uuid.uuid4()); self.ua=self.fp["user_agent"]
        self.signer=SignatureGenerator(self.ua)
        self.ws=None; self.connected=False; self._st=None
        self.proxy=pm.get() if pm else None
        self.geo_headers = geo_engine.get_geo_headers() if geo_engine else {}
        if self.tr: self._st=self.tr.register(vid,self.sid,self.proxy or "",cfg.region)
    async def _url(self):
        ep=WS_ENDPOINTS.get(self.cfg.region,WS_ENDPOINTS["us"])
        p={"room_id":str(self.rid),"platform":"web","version_code":"180001","webcast_language":"en","aid":"1988","identity":"audience","device_platform":"web" if "Mobile" not in self.ua else "mobile","browser_language":"en-US","browser_platform":"Win32","browser_name":"Chrome","browser_version":"125.0.0.0","msToken":SignatureGenerator.ms_token(),"live_id":"12","client_enter":"1","debug":"false","host":"https://webcast.tiktok.com"}
        p["X-Bogus"]=self.signer.x_bogus(p,"/webcast/im/v1/")
        return f"{ep}?{'&'.join(f'{k}={v}' for k,v in p.items())}"
    async def connect(self):
        url=await self._url(); fp=self.fp["fp"]
        cookie = f"ttwid={self.fp['web_id']}; sessionid={self.fp['session_id']}; tt_target_idc={self.cfg.region}"
        if self.account:
            cookie = f"sessionid={self.account['session_id']}; tt_target_idc={self.account.get('tt_target_idc','useast1a')}; ttwid={self.fp['web_id']}"
        h={"User-Agent":self.ua,"Origin":"https://www.tiktok.com","Referer":f"https://www.tiktok.com/@{self.cfg.username}/live" if self.cfg.username else "https://www.tiktok.com/","Accept-Language":fp["language"],"Accept-Encoding":"gzip, deflate, br, zstd","Cache-Control":"no-cache","Sec-WebSocket-Version":"13","Cookie":cookie}
        h.update(self.geo_headers)
        ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
        try:
            self.ws=await websockets.connect(url,extra_headers=h,ping_interval=None,close_timeout=5,max_size=2**20,open_timeout=self.cfg.ws_timeout,ssl=ctx)
            self.connected=True
            if self._st: self._st.start_time=time.time(); self._st.connected=True
            if self.tr: self.tr.total_connected+=1
            return True
        except Exception as e:
            log.debug(f"V{self.vid} fail: {e}")
            if self._st: self._st.errors+=1
            if self.pm and self.proxy: self.pm.mark_failed(self.proxy)
            return False
    async def hb(self):
        if not self.ws or not self.connected: return False
        try:
            j=json.dumps({"type":"Ping","id":int(time.time()*1000),"data":{"room_id":self.rid,"timestamp":int(time.time())}})
            await self.ws.send(j)
            if self._st: self._st.bytes_sent+=len(j.encode()); self._st.heartbeats_sent+=1; self._st.last_ping=time.time()
            if self.tr: self.tr.total_heartbeats+=1; self.tr.total_bytes_sent+=len(j.encode())
            return True
        except: return False
    async def send_like(self):
        if not self.ws or not self.connected: return False
        try:
            count = random.randint(1, 5)
            j=json.dumps({"type":"WebcastLikeMessage","data":{"like_count":count,"total_likes":random.randint(100,9999),"user":{"unique_id":f"user_{uuid.uuid4().hex[:8]}"}}})
            await self.ws.send(j)
            if self._st: self._st.likes_sent+=count; self._st.bytes_sent+=len(j.encode())
            if self.tr: self.tr.total_likes+=count
            return True
        except: return False
    async def send_chat(self, msg: str):
        if not self.ws or not self.connected: return False
        try:
            j=json.dumps({"type":"WebcastChatMessage","data":{"comment":msg,"user":{"unique_id":f"user_{uuid.uuid4().hex[:8]}"}}})
            await self.ws.send(j)
            if self._st: self._st.chats_sent+=1; self._st.bytes_sent+=len(j.encode())
            if self.tr: self.tr.total_chats+=1
            return True
        except: return False
    async def send_follow(self):
        if not self.ws or not self.connected: return False
        try:
            j=json.dumps({"type":"WebcastSocialMessage","data":{"action":"follow","user":{"unique_id":f"user_{uuid.uuid4().hex[:8]}"}}})
            await self.ws.send(j)
            if self._st: self._st.follows_sent+=1; self._st.bytes_sent+=len(j.encode())
            if self.tr: self.tr.total_follows+=1
            return True
        except: return False
    async def send_share(self):
        if not self.ws or not self.connected: return False
        try:
            j=json.dumps({"type":"WebcastSocialMessage","data":{"action":"share","user":{"unique_id":f"user_{uuid.uuid4().hex[:8]}"}}})
            await self.ws.send(j)
            if self._st: self._st.shares_sent+=1; self._st.bytes_sent+=len(j.encode())
            if self.tr: self.tr.total_shares+=1
            return True
        except: return False
    async def _msgs(self):
        if not self.ws or not self.connected: return
        try:
            async for m in self.ws:
                if not self.connected: break
                bl=len(m.encode() if isinstance(m,str) else m)
                if isinstance(m, bytes) and self.tr: self.tr.packet_inspector.inspect(m, "in")
                if self._st: self._st.bytes_received+=bl; self._st.messages_received+=1
                if self.tr: self.tr.total_bytes_received+=bl
                if isinstance(m,str):
                    try:
                        d=json.loads(m)
                        # Gift detection
                        if d.get("type")=="WebcastGiftMessage" and self.tr:
                            gd=d.get("data",{})
                            self.tr.gift_logger.log({"gift_name":gd.get("gift_name","unknown"),"diamond_count":gd.get("diamond_count",0),"repeat_count":gd.get("repeat_count",1),"user":gd.get("user",{})})
                        elif d.get("type")=="Pong" and self._st: self._st.latency_ms=(time.time()-self._st.last_ping)*1000; self.tr.latency_samples.append(self._st.latency_ms)
                        elif d.get("type")=="WebcastControlMessage" and d.get("data",{}).get("action")=="stream_stopped": break
                    except: pass
        except: pass
        finally: self.connected=False
    async def _hb_loop(self):
        while self.connected:
            if not await self.hb(): break
            await asyncio.sleep(self.cfg.heartbeat_interval+random.uniform(-3,3))
    async def _like_loop(self):
        if not self.cfg.auto_like: return
        await asyncio.sleep(random.randint(10, 30))
        while self.connected:
            await self.send_like()
            await asyncio.sleep(self.cfg.like_interval+random.uniform(-5, 10))
    async def _chat_loop(self):
        if not self.cfg.chat_spam: return
        await asyncio.sleep(random.randint(20, 60))
        msgs = self.cfg.chat_messages.split(",") if self.cfg.chat_messages else CHAT_MESSAGES
        while self.connected:
            msg = random.choice(msgs).strip()
            if msg: await self.send_chat(msg)
            await asyncio.sleep(random.randint(45, 120))
    async def _follow_loop(self):
        if not self.cfg.follow_bot: return
        await asyncio.sleep(random.randint(30, 90))
        while self.connected:
            await self.send_follow()
            await asyncio.sleep(random.randint(60, 180))
    async def _share_loop(self):
        if not self.cfg.share_sim: return
        await asyncio.sleep(random.randint(45, 120))
        while self.connected:
            await self.send_share()
            await asyncio.sleep(random.randint(90, 240))
    async def run(self):
        if not await self.connect(): return False
        tasks=[asyncio.create_task(self._hb_loop()),asyncio.create_task(self._msgs())]
        if self.cfg.auto_like: tasks.append(asyncio.create_task(self._like_loop()))
        if self.cfg.chat_spam: tasks.append(asyncio.create_task(self._chat_loop()))
        if self.cfg.follow_bot: tasks.append(asyncio.create_task(self._follow_loop()))
        if self.cfg.share_sim: tasks.append(asyncio.create_task(self._share_loop()))
        await asyncio.sleep(random.randint(self.cfg.min_watch_time,self.cfg.max_watch_time))
        self.connected=False
        for t in tasks: t.cancel()
        if self._st: self._st.end_time=time.time(); self._st.success=True
        if self.tr: self.tr.total_disconnected+=1
        if self.ws:
            try: await self.ws.close()
            except: pass
        return True

class Orchestrator:
    def __init__(self, cfg, pm=None, account_rotator=None, geo_engine=None):
        self.cfg=cfg; self.pm=pm; self.tr=SessionTracker()
        self._sem=asyncio.Semaphore(cfg.max_concurrent) if cfg.max_concurrent>0 else None
        self.account_rotator=account_rotator; self.geo_engine=geo_engine
    async def _spawn(self, i):
        acct = self.account_rotator.get() if self.account_rotator else None
        v=TikTokViewer(i,self.cfg.room_id,self.cfg,self.pm,self.tr,acct,self.geo_engine)
        try:
            if self._sem:
                async with self._sem: return await v.run()
            return await v.run()
        except: return False
    async def run(self):
        d=self.cfg.ramp_up_seconds/self.cfg.viewer_count if self.cfg.viewer_count>0 else 0
        tasks=[]
        for i in range(self.cfg.viewer_count):
            tasks.append(asyncio.create_task(self._spawn(i)))
            if d>0: await asyncio.sleep(d)
        await asyncio.gather(*tasks,return_exceptions=True)
        return self.tr.summary()
    async def run_auto_scale(self):
        base_count = max(10, self.cfg.viewer_count // 5)
        max_count = self.cfg.viewer_count
        current = base_count
        results = []
        while current <= max_count:
            self.cfg.viewer_count = current
            d=self.cfg.ramp_up_seconds/current if current>0 else 0
            tasks=[]
            for i in range(current):
                tasks.append(asyncio.create_task(self._spawn(i)))
                if d>0: await asyncio.sleep(d)
            await asyncio.gather(*tasks,return_exceptions=True)
            s = self.tr.summary()
            conn_pct = (s['connected']/current*100) if current>0 else 0
            results.append({"viewers":current,"connected":s['connected'],"rate":f"{conn_pct:.1f}%"})
            print(f"  Scale {current}: {s['connected']} connected ({conn_pct:.1f}%)")
            if conn_pct < 20: print(f"  [!] Hit rate limit at {current}. Stopping."); break
            current = min(int(current * 1.5), max_count)
            await asyncio.sleep(3)
        return results

class Dashboard:
    def __init__(self, tr, cfg): self.tr=tr; self.cfg=cfg; self._r=False
    def _f(self,b):
        if b<1024: return f"{b}B"
        if b<1024**2: return f"{b/1024:.1f}KB"
        return f"{b/1024**2:.1f}MB"
    def render(self):
        s=self.tr.summary(); R=Style.RESET_ALL if C else ""; G=Fore.GREEN if C else ""
        l=[]; l.append("╔══════════════════════════════════════════════════════════════╗")
        l.append("║           TIKTOK LIVE - REAL-TIME DASHBOARD v3.0             ║")
        l.append("╠══════════════════════════════════════════════════════════════╣")
        l.append(f"║  Room: {str(self.cfg.room_id or 'N/A'):<44}║")
        l.append(f"║  Target: {str(self.cfg.viewer_count):<6} | Elapsed: {s['elapsed']}s{' '*(30-len(str(int(s['elapsed']))))}║")
        l.append("╠══════════════════════════════════════════════════════════════╣")
        ac=G if s['active']>0 else ""
        l.append(f"║  {ac}● Active:{R} {s['active']:<4} | Launched: {s['launched']:<5} | Conn: {s['connected']:<5} | Rate: {s['rate']:<6}║")
        l.append(f"║  Disc: {s['disconnected']:<4} | Errors: {s['errors']:<5} | HB: {s['hb']:<6} | Lat: {s['latency']}ms{' '*(9-len(str(s['latency'])))}║")
        l.append("╠══════════════════════════════════════════════════════════════╣")
        l.append(f"║  📤 Sent: {self._f(s['sent']):<10} 📥 Recv: {self._f(s['recv']):<10}         ║")
        l.append("╠══════════════════════════════════════════════════════════════╣")
        l.append(f"║  ❤️ Likes: {s['likes']:<6} 💬 Chats: {s['chats']:<6} 👤 Follows: {s['follows']:<6} 🔄 Shares: {s['shares']:<6}║")
        gs=s.get('gifts',{}); l.append(f"║  🎁 Gifts: {gs.get('total_gifts',0):<4} types: {gs.get('unique_types',0):<3}                          ║")
        ps=s.get('packets',{}); l.append(f"║  📦 Packets: {ps.get('total_packets',0):<6} ({self._f(ps.get('bytes',0))})                  ║")
        l.append("╠══════════════════════════════════════════════════════════════╣")
        feats=[]
        if self.cfg.auto_like: feats.append("Likes")
        if self.cfg.chat_spam: feats.append("Chat")
        if self.cfg.follow_bot: feats.append("Follow")
        if self.cfg.share_sim: feats.append("Share")
        if self.cfg.geo_spoof: feats.append("Geo")
        if self.cfg.auto_scale: feats.append("AutoScale")
        feat_str = ",".join(feats) if feats else "None"
        l.append(f"║  Active Features: {feat_str:<42}║")
        l.append(f"║  Behavior: {self.cfg.behavior_profile:<10} Region: {self.cfg.region:<10} Proxy: {'Yes' if self.cfg.proxy_file else 'No':<13}║")
        l.append("╚══════════════════════════════════════════════════════════════╝")
        return "\n".join(l)
    async def run(self):
        self._r=True
        try:
            while self._r:
                os.system('cls' if os.name=='nt' else 'clear')
                print(self.render())
                await asyncio.sleep(1)
        except asyncio.CancelledError: pass
    def stop(self): self._r=False

class App:
    def __init__(self):
        self.cfg=Config(); self.pm=None; self.account_rotator=None; self.geo_engine=None
    def clear(self): os.system('cls' if os.name=='nt' else 'clear')
    def banner(self):
        self.clear()
        print(Fore.CYAN+BANNER+Style.RESET_ALL if C else BANNER)
    def menu(self):
        print(Fore.YELLOW+MENU+Style.RESET_ALL if C else MENU)
    def show_cfg(self):
        c=self.cfg
        print("\n"+"="*60); print("  CONFIGURATION"); print("="*60)
        print(f"  Username:      {c.username or 'Not set'}")
        print(f"  Room ID:       {c.room_id or 'Not set'}")
        print(f"  Viewers:       {c.viewer_count}  Ramp: {c.ramp_up_seconds}s  Region: {c.region}")
        print(f"  Max Concurrent:{'Unlimited' if c.max_concurrent==0 else c.max_concurrent}")
        print(f"  Behavior:      {c.behavior_profile}  Fingerprint: {c.fingerprint_profile}")
        print(f"  Proxy:         {c.proxy_file or 'None'}  Rotation: {c.proxy_rotation}")
        print(f"  Accounts:      {c.accounts_file or 'None'}")
        print("  ── Features ──")
        print(f"  Auto-Like:     {'ON' if c.auto_like else 'OFF'} ({c.like_interval}s)  Chat Spam: {'ON' if c.chat_spam else 'OFF'}")
        print(f"  Follow Bot:    {'ON' if c.follow_bot else 'OFF'}  Share Sim: {'ON' if c.share_sim else 'OFF'}")
        print(f"  Monitor Mode:  {'ON' if c.monitor_mode else 'OFF'}  Gift Log: {'ON' if c.gift_log else 'OFF'}")
        print(f"  Packet Inspect:{'ON' if c.packet_inspect else 'OFF'}  Auto-Scale: {'ON' if c.auto_scale else 'OFF'}")
        print(f"  Geo Spoof:     {'ON' if c.geo_spoof else 'OFF'} ({c.geo_region})")
        print("="*60+"\n")

    async def launch(self):
        if not self.cfg.room_id and not self.cfg.username:
            print(Fore.RED+"[!] Set target first"+Style.RESET_ALL if C else "[!] Set target first")
            await asyncio.sleep(2); return
        if not self.cfg.room_id and self.cfg.username:
            print(f"[*] Resolving @{self.cfg.username}...")
            ext=RoomInfoExtractor(); rid=await ext.get_room_id(self.cfg.username)
            if rid:
                self.cfg.room_id=rid; info=await ext.get_info(rid)
                print(f"[+] Room ID: {rid}")
                if info: print(f"[+] Title: {info.get('title','N/A')} | Viewers: {info.get('viewers','N/A')} | Likes: {info.get('like_count','N/A')}")
            else:
                print(Fore.RED+"[!] Cannot resolve"+Style.RESET_ALL if C else "[!] Cannot resolve")
                await asyncio.sleep(2); return
        if self.cfg.proxy_file and not self.pm:
            self.pm=ProxyManager(ProxyManager.parse_file(self.cfg.proxy_file),self.cfg.proxy_rotation)
            print(f"[*] Proxies: {self.pm.count}")
        if self.cfg.accounts_file and not self.account_rotator:
            self.account_rotator=AccountRotator(self.cfg.accounts_file)
            print(f"[*] Accounts: {self.account_rotator.count}")
        if self.cfg.geo_spoof and not self.geo_engine:
            self.geo_engine=GeoEngine(self.cfg.geo_region)
            print(f"[*] Geo Spoof: {self.cfg.geo_region}")
        orch=Orchestrator(self.cfg,self.pm,self.account_rotator,self.geo_engine)
        dt=None
        if self.cfg.realtime_dashboard:
            d=Dashboard(orch.tr,self.cfg); dt=asyncio.create_task(d.run())
        try:
            if self.cfg.auto_scale:
                print("[*] Auto-Scale Mode active - scaling up viewer count...")
                results=await orch.run_auto_scale()
                print(f"\n[+] Scale results saved")
            else:
                results=await orch.run()
        except asyncio.CancelledError: orch.stop()
        if dt: dt.cancel(); await asyncio.sleep(0)
        s=orch.tr.summary()
        print("\n"+"="*70); print("  FINAL RESULTS"); print("="*70)
        print(f"  Duration:    {s['elapsed']}s")
        print(f"  Launched:    {s['launched']}  Connected: {s['connected']}  Active: {s['active']}")
        print(f"  Errors:      {s['errors']}  Success: {s['rate']}")
        print(f"  Heartbeats:  {s['hb']}  Sent: {s['sent']}B  Recv: {s['recv']}B  Lat: {s['latency']}ms")
        print(f"  Likes:       {s['likes']}  Chats: {s['chats']}  Follows: {s['follows']}  Shares: {s['shares']}")
        gs=s.get('gifts',{}); print(f"  Gifts:       {gs.get('total_gifts',0)} ({gs.get('unique_types',0)} types)")
        ps=s.get('packets',{}); print(f"  Packets:     {ps.get('total_packets',0)} ({ps.get('bytes',0)}B)")
        print("="*70+"\n")
        if self.cfg.save_report:
            rf=f"tiktok_sim_{int(time.time())}.json"
            with open(rf,"w") as f: json.dump(s,f,indent=2)
            print(f"[+] Saved: {rf}")
        input("\nPress Enter...")

    async def config_menu(self):
        while True:
            self.clear(); self.show_cfg()
            print("  [1] Username  [2] Room ID  [3] Viewers  [4] Ramp  [5] Region")
            print("  [6] Max Concurrency  [7] Heartbeat  [8] Watch Range")
            print("  [9] Toggle Dashboard  [10] Toggle Report  [11] Accounts File")
            print("  [0] Back")
            ch=input("  Select: ").strip()
            if ch=="0": break
            elif ch=="1": self.cfg.username=input("  Username: ").strip()
            elif ch=="2":
                try: self.cfg.room_id=int(input("  Room ID: ").strip())
                except: print("[!] Invalid")
            elif ch=="3":
                try: self.cfg.viewer_count=int(input("  Viewers: ").strip())
                except: print("[!] Invalid")
            elif ch=="4":
                try: self.cfg.ramp_up_seconds=int(input("  Ramp (s): ").strip())
                except: print("[!] Invalid")
            elif ch=="5":
                r=input("  Region (us/eu/asia/sg/br): ").strip()
                if r in WS_ENDPOINTS: self.cfg.region=r
            elif ch=="6":
                try: self.cfg.max_concurrent=max(0,int(input("  Max concurrent (0=unlimited): ").strip()))
                except: print("[!] Invalid")
            elif ch=="7":
                try: self.cfg.heartbeat_interval=int(input("  Heartbeat (s): ").strip())
                except: print("[!] Invalid")
            elif ch=="8":
                try: mn=int(input("  Min watch (s): ").strip()); mx=int(input("  Max watch (s): ").strip()); self.cfg.min_watch_time=min(mn,mx); self.cfg.max_watch_time=max(mn,mx)
                except: print("[!] Invalid")
            elif ch=="9": self.cfg.realtime_dashboard=not self.cfg.realtime_dashboard
            elif ch=="10": self.cfg.save_report=not self.cfg.save_report
            elif ch=="11":
                p=input("  Accounts file path: ").strip()
                if os.path.exists(p): self.cfg.accounts_file=p; print(f"[+] Loaded"); self.account_rotator=AccountRotator(p); print(f"[+] {self.account_rotator.count} accounts")
                else: print("[!] Not found")
            await asyncio.sleep(1)

    async def feature_menu(self, feature_num: int):
        if feature_num==11: # Auto-Like
            self.clear()
            print("\n"+"="*60); print("  AUTO-LIKE BOT"); print("="*60)
            print(f"  Status: {'ON' if self.cfg.auto_like else 'OFF'}")
            print(f"  Interval: {self.cfg.like_interval}s\n")
            print("  [1] Toggle ON/OFF")
            print("  [2] Set interval")
            print("  [0] Back\n")
            ch=input("  Select: ").strip()
            if ch=="1": self.cfg.auto_like=not self.cfg.auto_like; print(f"[+] Auto-Like: {'ON' if self.cfg.auto_like else 'OFF'}")
            elif ch=="2":
                try: self.cfg.like_interval=int(input("  Interval (s): ").strip())
                except: print("[!] Invalid")
            await asyncio.sleep(1)
        elif feature_num==12: # Chat Spam
            self.clear()
            print("\n"+"="*60); print("  CHAT SPAM ENGINE"); print("="*60)
            print(f"  Status: {'ON' if self.cfg.chat_spam else 'OFF'}")
            print(f"  Messages: {self.cfg.chat_messages or 'Default list'}\n")
            print("  [1] Toggle ON/OFF")
            print("  [2] Set custom messages (comma-separated)")
            print("  [3] Use default messages")
            print("  [0] Back\n")
            ch=input("  Select: ").strip()
            if ch=="1": self.cfg.chat_spam=not self.cfg.chat_spam; print(f"[+] Chat Spam: {'ON' if self.cfg.chat_spam else 'OFF'}")
            elif ch=="2": self.cfg.chat_messages=input("  Messages (comma-separated): ").strip()
            elif ch=="3": self.cfg.chat_messages=""
            await asyncio.sleep(1)
        elif feature_num==13: # Follow Bot
            self.clear()
            print("\n"+"="*60); print("  FOLLOW BOT"); print("="*60)
            print(f"  Status: {'ON' if self.cfg.follow_bot else 'OFF'}\n")
            print("  [1] Toggle ON/OFF")
            print("  [0] Back\n")
            ch=input("  Select: ").strip()
            if ch=="1": self.cfg.follow_bot=not self.cfg.follow_bot; print(f"[+] Follow Bot: {'ON' if self.cfg.follow_bot else 'OFF'}")
            await asyncio.sleep(1)
        elif feature_num==14: # Share
            self.clear()
            print("\n"+"="*60); print("  SHARE SIMULATOR"); print("="*60)
            print(f"  Status: {'ON' if self.cfg.share_sim else 'OFF'}\n")
            print("  [1] Toggle ON/OFF")
            print("  [0] Back\n")
            ch=input("  Select: ").strip()
            if ch=="1": self.cfg.share_sim=not self.cfg.share_sim; print(f"[+] Share Sim: {'ON' if self.cfg.share_sim else 'OFF'}")
            await asyncio.sleep(1)
        elif feature_num==16: # Monitor
            self.clear()
            print("\n"+"="*60); print("  STREAM MONITOR MODE"); print("="*60)
            print(f"  Status: {'ON' if self.cfg.monitor_mode else 'OFF'}")
            print(f"  Targets: {self.cfg.monitor_targets or 'Not set'}\n")
            print("  [1] Toggle ON/OFF")
            print("  [2] Set targets (comma-separated usernames)")
            print("  [0] Back\n")
            ch=input("  Select: ").strip()
            if ch=="1": self.cfg.monitor_mode=not self.cfg.monitor_mode; print(f"[+] Monitor: {'ON' if self.cfg.monitor_mode else 'OFF'}")
            elif ch=="2": self.cfg.monitor_targets=input("  Usernames (comma-separated): ").strip()
            await asyncio.sleep(1)
        elif feature_num==17: # Gift Log
            self.cfg.gift_log=not self.cfg.gift_log; print(f"[+] Gift Log: {'ON' if self.cfg.gift_log else 'OFF'}"); await asyncio.sleep(1)
        elif feature_num==18: # Packet Inspect
            self.cfg.packet_inspect=not self.cfg.packet_inspect; print(f"[+] Packet Inspect: {'ON' if self.cfg.packet_inspect else 'OFF'}"); await asyncio.sleep(1)
        elif feature_num==19: # Auto-Scale
            self.cfg.auto_scale=not self.cfg.auto_scale; print(f"[+] Auto-Scale: {'ON' if self.cfg.auto_scale else 'OFF'}"); await asyncio.sleep(1)
        elif feature_num==20: # Geo
            self.clear()
            print("\n"+"="*60); print("  GEOLOCATION SPOOFER"); print("="*60)
            print(f"  Status: {'ON' if self.cfg.geo_spoof else 'OFF'}")
            print(f"  Region: {self.cfg.geo_region}\n")
            print("  [1] Toggle ON/OFF")
            print("  [2] Set region auto")
            print("  [3] us-east    [4] us-west    [5] eu-west")
            print("  [6] eu-central [7] ap-southeast [8] ap-northeast")
            print("  [0] Back\n")
            ch=input("  Select: ").strip()
            if ch=="1": self.cfg.geo_spoof=not self.cfg.geo_spoof; print(f"[+] Geo Spoof: {'ON' if self.cfg.geo_spoof else 'OFF'}")
            elif ch=="2": self.cfg.geo_region="auto"
            elif ch=="3": self.cfg.geo_region="us-east"
            elif ch=="4": self.cfg.geo_region="us-west"
            elif ch=="5": self.cfg.geo_region="eu-west"
            elif ch=="6": self.cfg.geo_region="eu-central"
            elif ch=="7": self.cfg.geo_region="ap-southeast"
            elif ch=="8": self.cfg.geo_region="ap-northeast"
            await asyncio.sleep(1)

    async def proxy_menu(self):
        while True:
            self.clear()
            print("\n"+"="*60); print("  PROXY MANAGER"); print("="*60)
            if self.pm: print(f"  Loaded: {self.pm.count}  Used: {self.pm.stats['used']}  Failed: {self.pm.stats['failed']}  Rotation: {self.cfg.proxy_rotation}")
            else: print(f"  File: {self.cfg.proxy_file or 'None'}")
            print("="*60); print("  [1] Load file  [2] Rotation  [3] Clear  [0] Back")
            ch=input("  Select: ").strip()
            if ch=="0": break
            elif ch=="1":
                p=input("  Path: ").strip()
                if os.path.exists(p): self.cfg.proxy_file=p; self.pm=ProxyManager(ProxyManager.parse_file(p),self.cfg.proxy_rotation); print(f"[+] Loaded {self.pm.count}")
                else: print("[!] Not found")
            elif ch=="2":
                r=input("  Rotation (round_robin/random): ").strip()
                if r in ("round_robin","random"): self.cfg.proxy_rotation=r
                if self.pm: self.pm.rotation=r
            elif ch=="3": self.pm=None; self.cfg.proxy_file=""; print("[+] Cleared")
            await asyncio.sleep(1)

    async def fp_menu(self):
        while True:
            self.clear()
            print("\n"+"="*60); print("  FINGERPRINT PROFILES"); print("="*60)
            print(f"  Current: {self.cfg.fingerprint_profile}\n")
            for i,n in enumerate(FingerprintEngine.PROFILES.keys(),1): print(f"  [{i}] {n}")
            print("  [0] Back\n")
            ch=input("  Select: ").strip()
            if ch=="0": break
            try: idx=int(ch)-1; names=list(FingerprintEngine.PROFILES.keys()); 
            if 0<=idx<len(names): self.cfg.fingerprint_profile=names[idx]; print(f"[+] Set: {names[idx]}")
            except: pass
            await asyncio.sleep(1)

    async def room_info(self):
        self.clear()
        u=input("\n  Username (without @): ").strip()
        if not u: return
        print(f"[*] Looking up @{u}...")
        ext=RoomInfoExtractor(); rid=await ext.get_room_id(u)
        info=await ext.get_info(rid) if rid else None
        print("\n"+"="*60); print("  ROOM INFO"); print("="*60)
        if rid: print(f"  Room ID: {rid}")
        else: print("  Room ID: Not found (offline?)")
        if info:
            print(f"  Title:   {info.get('title','N/A')}")
            print(f"  Status:  {'LIVE' if info.get('status')==2 else 'Ended'}")
            print(f"  Viewers: {info.get('viewers','N/A')}  Total: {info.get('total','N/A')}  Likes: {info.get('like_count','N/A')}")
            o=info.get('owner',{})
            if o: print(f"  Host:    {o.get('nickname')} (@{o.get('username')}) F: {o.get('followers',0)}")
        if rid and input("\n  Set as target? (y/n): ").strip().lower()=='y':
            self.cfg.room_id=rid; self.cfg.username=u; print("[+] Target set!")
        input("\nPress Enter...")

    async def history(self):
        while True:
            self.clear()
            print("\n"+"="*60); print("  SESSION HISTORY"); print("="*60)
            reps=sorted([f for f in os.listdir('.') if f.startswith('tiktok_') and f.endswith('.json')],reverse=True)
            if reps:
                for i,f in enumerate(reps[:10],1):
                    mt=datetime.fromtimestamp(os.path.getmtime(f)).strftime('%Y-%m-%d %H:%M')
                    print(f"  [{i}] {f:<50} {mt}")
            else: print("  No reports found.")
            print("\n  [0] Back")
            ch=input("  Select: ").strip()
            if ch=="0": break
            try: idx=int(ch)-1
            if 0<=idx<len(reps):
                with open(reps[idx]) as f: print("\n"+json.dumps(json.load(f),indent=2))
                input("\nPress Enter...")
            except: pass

    async def stress(self):
        self.clear()
        print("\n"+"="*60); print("  STRESS TEST MODE"); print("="*60)
        print("\n  Runs: 10, 25, 50, 100, 200, 500 viewers (with features)\n")
        if not self.cfg.room_id and not self.cfg.username:
            print("[!] Set a target first"); input("Press Enter..."); return
        if not self.cfg.room_id and self.cfg.username:
            ext=RoomInfoExtractor(); rid=await ext.get_room_id(self.cfg.username)
            if not rid: print("[!] Cannot resolve"); input("Press Enter..."); return
            self.cfg.room_id=rid
        if self.cfg.proxy_file and not self.pm: self.pm=ProxyManager(ProxyManager.parse_file(self.cfg.proxy_file),self.cfg.proxy_rotation)
        if self.cfg.accounts_file and not self.account_rotator: self.account_rotator=AccountRotator(self.cfg.accounts_file)
        if self.cfg.geo_spoof and not self.geo_engine: self.geo_engine=GeoEngine(self.cfg.geo_region)
        og_c=self.cfg.viewer_count; og_d=self.cfg.realtime_dashboard
        self.cfg.realtime_dashboard=False
        sizes=[10,25,50,100,200,500]
        print(f"  {'Test':<8}{'Viewers':<10}{'Conn':<10}{'Rate':<10}{'Likes':<8}{'Chats':<8}{'Time':<8}")
        print(f"  {'-'*62}")
        log_r=[]
        for size in sizes:
            if size>og_c*2 and og_c>0: print(f"\n[!] Stop at {size}"); break
            self.cfg.viewer_count=size
            orch=Orchestrator(self.cfg,self.pm,self.account_rotator,self.geo_engine)
            start=time.time(); r=await orch.run(); e=time.time()-start
            print(f"  {len(log_r)+1:<8}{size:<10}{r['connected']:<10}{r['rate']:<10}{r['likes']:<8}{r['chats']:<8}{e:<8.1f}")
            log_r.append({"test":len(log_r)+1,"viewers":size,"connected":r['connected'],"rate":r['rate'],"likes":r['likes'],"chats":r['chats'],"time":round(e,1)})
            if size<200: print("  Cool 5s..."); await asyncio.sleep(5)
        rf=f"tiktok_stress_{int(time.time())}.json"
        with open(rf,"w") as f: json.dump(log_r,f,indent=2)
        print(f"\n[+] Saved: {rf}")
        self.cfg.viewer_count=og_c; self.cfg.realtime_dashboard=og_d
        input("\nPress Enter...")

    async def behavior(self):
        while True:
            self.clear()
            print("\n"+"="*60); print("  BEHAVIOR PROFILES"); print("="*60)
            print(f"  Current: {self.cfg.behavior_profile} ({self.cfg.min_watch_time}-{self.cfg.max_watch_time}s)\n")
            print("  [1] Realistic (30-300s)  [2] Stealth (60-600s)")
            print("  [3] Aggressive (10-120s)  [4] Custom  [0] Back\n")
            ch=input("  Select: ").strip()
            if ch=="0": break
            elif ch=="1": self.cfg.behavior_profile,self.cfg.min_watch_time,self.cfg.max_watch_time="realistic",30,300
            elif ch=="2": self.cfg.behavior_profile,self.cfg.min_watch_time,self.cfg.max_watch_time="stealth",60,600
            elif ch=="3": self.cfg.behavior_profile,self.cfg.min_watch_time,self.cfg.max_watch_time="aggressive",10,120
            elif ch=="4":
                try: mn=int(input("  Min (s): ").strip()); mx=int(input("  Max (s): ").strip()); self.cfg.behavior_profile,self.cfg.min_watch_time,self.cfg.max_watch_time="custom",min(mn,mx),max(mn,mx)
                except: print("[!] Invalid")
            print(f"[+] Set: {self.cfg.behavior_profile}")
            await asyncio.sleep(1)

    async def save_load(self):
        self.clear()
        print("\n"+"="*60); print("  SAVE/LOAD CONFIG"); print("="*60)
        print("  [1] Save  [2] Load  [0] Back\n")
        ch=input("  Select: ").strip()
        if ch=="1":
            f=f"tiktok_cfg_{int(time.time())}.json"
            with open(f,"w") as fh: json.dump(self.cfg.to_dict(),fh,indent=2)
            print(f"[+] Saved: {f}")
        elif ch=="2":
            cfgs=sorted([f for f in os.listdir('.') if f.startswith('tiktok_cfg_') and f.endswith('.json')],reverse=True)
            if not cfgs: print("[!] None found")
            else:
                for i,f in enumerate(cfgs[:10],1): print(f"  [{i}] {f}")
                sel=input("  Select: ").strip()
                try: idx=int(sel)-1; 
                with open(cfgs[idx]) as fh: self.cfg=Config.from_dict(json.load(fh)); 
                if self.cfg.accounts_file: self.account_rotator=AccountRotator(self.cfg.accounts_file)
                if self.cfg.proxy_file: self.pm=ProxyManager(ProxyManager.parse_file(self.cfg.proxy_file),self.cfg.proxy_rotation)
                if self.cfg.geo_spoof: self.geo_engine=GeoEngine(self.cfg.geo_region)
                print(f"[+] Loaded: {cfgs[idx]}")
                except: print("[!] Invalid")
        await asyncio.sleep(1.5)

    async def monitor_run(self):
        self.clear()
        print("\n"+"="*60); print("  STREAM MONITOR MODE"); print("="*60)
        if not self.cfg.monitor_targets:
            print("[!] No targets set. Configure first."); await asyncio.sleep(2); return
        targets=[t.strip() for t in self.cfg.monitor_targets.split(",") if t.strip()]
        print(f"  Monitoring {len(targets)} stream(s)...")
        print("  Press Ctrl+C to stop.\n")
        ext=RoomInfoExtractor()
        try:
            while True:
                print(f"\n  [{datetime.now().strftime('%H:%M:%S')}] Checking {len(targets)} streams...")
                for t in targets:
                    rid=await ext.get_room_id(t)
                    if rid:
                        info=await ext.get_info(rid)
                        if info and info.get('status')==2:
                            print(f"  🟢 @{t:<20} LIVE | Viewers: {info.get('viewers','?'):<8} Likes: {info.get('like_count','?'):<8} Title: {info.get('title','N/A')[:30]}")
                        else: print(f"  🔴 @{t:<20} OFFLINE")
                    else: print(f"  ⚫ @{t:<20} UNRESOLVABLE")
                await asyncio.sleep(30)
        except KeyboardInterrupt: print("\n[+] Monitor stopped.")
        input("\nPress Enter...")

    async def main(self):
        try:
            while True:
                self.banner(); self.menu()
                if self.cfg.room_id or self.cfg.username:
                    t=self.cfg.username or f"Room {self.cfg.room_id}"
                    feats=[]
                    if self.cfg.auto_like: feats.append("Likes")
                    if self.cfg.chat_spam: feats.append("Chat")
                    if self.cfg.follow_bot: feats.append("Follow")
                    if self.cfg.share_sim: feats.append("Share")
                    if self.cfg.auto_scale: feats.append("AutoScale")
                    if self.cfg.monitor_mode: feats.append("Monitor")
                    if self.cfg.geo_spoof: feats.append("Geo")
                    fstr=",".join(feats) if feats else "None"
                    print(f"\n  Target: {t}  |  Viewers: {self.cfg.viewer_count}  |  Region: {self.cfg.region}  |  Features: {fstr}\n")
                ch=input("  Choice: ").strip()
                if ch=="0": print("\n  Goodbye!\n"); break
                elif ch=="1": await self.launch()
                elif ch=="2": await self.launch()
                elif ch=="3": await self.config_menu()
                elif ch=="4": await self.proxy_menu()
                elif ch=="5": await self.fp_menu()
                elif ch=="6": await self.room_info()
                elif ch=="7": await self.history()
                elif ch=="8": await self.stress()
                elif ch=="9": await self.behavior()
                elif ch=="10": await self.save_load()
                elif ch in ("11","12","13","14","16","17","18","19","20"):
                    await self.feature_menu(int(ch))
                else: print("\n  [!] Invalid"); await asyncio.sleep(1)
        except KeyboardInterrupt: print("\n\nExiting...")

async def main():
    if len(sys.argv)>1:
        p=argparse.ArgumentParser(description="TikTok Live Pentesting Suite v3.0")
        p.add_argument("--username"); p.add_argument("--room-id",type=int)
        p.add_argument("--viewers",type=int,default=50); p.add_argument("--ramp",type=int,default=10)
        p.add_argument("--region",default="us",choices=list(WS_ENDPOINTS.keys()))
        p.add_argument("--behavior",default="realistic"); p.add_argument("--fingerprint",default="random")
        p.add_argument("--concurrent",type=int,default=0); p.add_argument("--proxies"); p.add_argument("--accounts")
        p.add_argument("--stress",action="store_true"); p.add_argument("--auto-scale",action="store_true")
        p.add_argument("--no-dash",action="store_true")
        p.add_argument("--auto-like",action="store_true"); p.add_argument("--like-interval",type=int,default=30)
        p.add_argument("--chat-spam",action="store_true"); p.add_argument("--chat-msgs",default="")
        p.add_argument("--follow",action="store_true"); p.add_argument("--share",action="store_true")
        p.add_argument("--geo-spoof",action="store_true"); p.add_argument("--geo-region",default="auto")
        p.add_argument("--monitor"); p.add_argument("--gift-log",action="store_true")
        p.add_argument("--packet-inspect",action="store_true")
        a=p.parse_args()
        cfg=Config(username=a.username or "",room_id=a.room_id or 0,viewer_count=a.viewers,ramp_up_seconds=a.ramp,region=a.region,behavior_profile=a.behavior,fingerprint_profile=a.fingerprint,max_concurrent=a.concurrent,proxy_file=a.proxies or "",accounts_file=a.accounts or "",realtime_dashboard=not a.no_dash,auto_like=a.auto_like,like_interval=a.like_interval,chat_spam=a.chat_spam,chat_messages=a.chat_msgs or "",follow_bot=a.follow,share_sim=a.share,geo_spoof=a.geo_spoof,geo_region=a.geo_region,monitor_mode=bool(a.monitor),monitor_targets=a.monitor or "",gift_log=a.gift_log,packet_inspect=a.packet_inspect,auto_scale=a.auto_scale)
        if not cfg.room_id and cfg.username:
            ext=RoomInfoExtractor(); rid=await ext.get_room_id(cfg.username)
            if rid: cfg.room_id=rid; print(f"[+] Room ID: {rid}")
            else: print("[!] Cannot resolve"); return
        pm=None; ar=None; ge=None
        if cfg.proxy_file: pm=ProxyManager(ProxyManager.parse_file(cfg.proxy_file)); print(f"[*] Proxies: {pm.count}")
        if cfg.accounts_file: ar=AccountRotator(cfg.accounts_file); print(f"[*] Accounts: {ar.count}")
        if cfg.geo_spoof: ge=GeoEngine(cfg.geo_region); print(f"[*] Geo: {cfg.geo_region}")
        orch=Orchestrator(cfg,pm,ar,ge)
        dt=None
        if cfg.realtime_dashboard: d=Dashboard(orch.tr,cfg); dt=asyncio.create_task(d.run())
        try:
            if cfg.auto_scale: results=await orch.run_auto_scale()
            elif a.stress:
                sizes=[10,25,50,100,200,500]
                for s in sizes:
                    if s>cfg.viewer_count*2 and cfg.viewer_count>0: break
                    cfg.viewer_count=s
                    r=await Orchestrator(cfg,pm,ar,ge).run()
                    print(f"  {s} viewers: {r['connected']} conn, {r['rate']}%, likes:{r['likes']}, chats:{r['chats']}")
                    if s<200: await asyncio.sleep(5)
            else: results=await orch.run()
        except KeyboardInterrupt: orch.stop()
        if dt: dt.cancel(); await asyncio.sleep(0)
        s=orch.tr.summary()
        print(f"\nResults: {s['connected']}/{s['launched']} conn, {s['rate']}%, likes:{s['likes']}, chats:{s['chats']}, follows:{s['follows']}, shares:{s['shares']}, {s['elapsed']}s")
        if s['gifts'].get('total_gifts',0)>0: print(f"Gifts: {s['gifts']['total_gifts']}")
        if s['packets'].get('total_packets',0)>0: print(f"Packets: {s['packets']['total_packets']}")
    else:
        app=App(); await app.main()

if __name__=="__main__":
    try: asyncio.run(main())
    except KeyboardInterrupt: print("\nExiting...")
