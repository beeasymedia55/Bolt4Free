#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
  TikTok Live Viewer Bot  v5.0  —  Pure HTTP/WebSocket + REAL Signatures
═══════════════════════════════════════════════════════════════════════════════
  Signing pipeline (the part that actually matters):

    [1] X-Bogus          →  TikTok JS VM (X-Bogus.js) executed via Node/execjs
                            input:  query string + user-agent
    [2] _signature       →  appended by the web VM flow (best-effort external
                            signer hook; falls back to X-Bogus-only)
    [3] X-Gorgon 8404    →  SignerPy.sign(params, payload, version=8404)
    [4] X-Khronos        →  unix timestamp (from SignerPy)
    [5] X-Argus/X-Ladon  →  tiktok-signer TikTokSigner.generate_headers()
    [6] msToken          →  SignerPy msToken / homepage cookie / generated
    [7] x-ss-stub        →  MD5 of POST body (SignerPy)

  Connection flow:
    sign() → GET /api-live/user/room/  → room_id, status
          → GET /webcast/room/info/    → push_server + cursor
          → WSS://{push_server}/ws/    → protobuf frames, ack, heartbeat

  NOTE ON REALITY: pure-Python can generate X-Gorgon/X-Argus/X-Ladon and run
  TikTok's X-Bogus JS VM, but _signature is derived inside TikTok's web app
  JS. The suite ships with a SignerService hook so you can point it at any
  external _signature service (Euler Stream / eterz / your own VM server) via
  env var TIKTOK_SIGNER_URL. Without it, X-Bogus + msToken + cookies is the
  strongest pure-HTTP signature set available.
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import re
import sys
import json
import time
import gzip
import zlib
import base64
import random
import string
import hashlib
import hmac
import struct
import socket
import ssl
import threading
import queue
import logging
import subprocess
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List, Tuple, Any, Union, Callable
from pathlib import Path

# ────────────────────────────────────────────────────────────────────────────
# 0. AUTO-INSTALL DEPENDENCIES
# ────────────────────────────────────────────────────────────────────────────

def _ensure(pkg: str, import_name: str = None):
    import_name = import_name or pkg
    try:
        __import__(import_name)
        return True
    except ImportError:
        print(f"[*] Installing {pkg} ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", pkg])
        try:
            __import__(import_name)
            return True
        except ImportError:
            return False

_ensure("requests")
_ensure("websocket-client", "websocket")
_ensure("PyExecJS", "execjs")
_ensure("SignerPy")
_ensure("tiktok-signer", "tiktok_signer")

import requests
import websocket
import execjs

try:
    from SignerPy import sign as _sp_sign
    from SignerPy import xtoken as _sp_xtoken
except Exception:
    _sp_sign = None
    _sp_xtoken = None

try:
    from SignerPy import msToken as _sp_mstoken
except Exception:
    _sp_mstoken = None

try:
    from tiktok_signer import TikTokSigner, generate_headers as _tt_gen_headers
except Exception:
    TikTokSigner = None
    _tt_gen_headers = None


# ────────────────────────────────────────────────────────────────────────────
# 1. CONFIGURATION
# ────────────────────────────────────────────────────────────────────────────

@dataclass
class Config:
    # target
    target_username: str = ""
    room_id: str = ""

    # scale
    viewer_count: int = 3
    max_viewers: int = 50
    ramp_step: int = 1
    ramp_interval: float = 3.0

    # signing
    gorgon_version: int = 8404          # 8404 / 4404 / 8402
    use_signerpy: bool = True
    use_tiktok_signer: bool = True
    external_signer_url: str = os.environ.get("TIKTOK_SIGNER_URL", "")

    # device / app
    aid: int = 1988
    app_name: str = "tiktok_web"
    device_platform: str = "web_pc"
    browser_name: str = "chrome"
    browser_version: str = "125"
    device_id: str = ""
    ms_token: str = ""
    verify_fp: str = ""

    # user agents
    web_ua: str = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")
    mobile_ua: str = ("com.zhiliaoapp.musically/2023700040 (Linux; U; Android 9; en_US; "
                      "2203121C; Build/PQ3A.190705.09121607;tt-ok/3.12.13.4-tiktok)")

    # connection
    proxy_file: str = ""
    max_retries: int = 3
    connect_timeout: float = 12.0
    heartbeat_interval: float = 30.0     # webcast expects ack/heartbeat ~30s
    reconnect_delay: float = 2.0

    # behaviors
    like_burst_min: int = 3
    like_burst_max: int = 12
    like_interval_min: float = 4.0
    like_interval_max: float = 20.0
    chat_interval_min: float = 20.0
    chat_interval_max: float = 90.0
    chat_wordlist: List[str] = field(default_factory=lambda: [
        "W", "LIVE", "GG", "OMG", "🔥", "❤️", "hello!!", "let's go",
        "hi streamer", "first time here", "nice setup", "pog", "lol",
        "wait what", "no way", "that was insane", "welcome back"
    ])
    follow_interval: float = 300.0
    share_interval: float = 180.0

    # geo spoof
    spoof_region: bool = True
    region: str = "US"
    regions_pool: List[str] = field(default_factory=lambda: [
        "US", "GB", "DE", "FR", "JP", "BR", "CA", "AU", "IN", "MX", "KR", "NL"
    ])

    # monitoring / logging
    monitor_interval: float = 10.0
    log_file: str = "tiktok_viewer_v5.log"
    verbose: bool = True
    stats_refresh: float = 1.0

    def __post_init__(self):
        if not self.device_id:
            self.device_id = "".join(random.choices(string.digits, k=19))


CFG = Config()

# ────────────────────────────────────────────────────────────────────────────
# 2. LOGGING
# ────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.DEBUG if CFG.verbose else logging.INFO,
    format="%(asctime)s [%(levelname)-7s] %(message)s",
    handlers=[
        logging.FileHandler(CFG.log_file) if CFG.log_file else logging.NullHandler(),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("ttviewer")
log.setLevel(logging.DEBUG if CFG.verbose else logging.INFO)


def ts_ms() -> int:
    return int(time.time() * 1000)


def rand_str(n: int, chars: str = None) -> str:
    chars = chars or (string.ascii_letters + string.digits)
    return "".join(random.choices(chars, k=n))


def fmt_now() -> str:
    return datetime.now().strftime("%H:%M:%S")


# ────────────────────────────────────────────────────────────────────────────
# 3. X-BOGUS ENGINE  (real TikTok JS VM via execjs / node subprocess)
# ────────────────────────────────────────────────────────────────────────────

X_BOGUS_JS_URL = "https://raw.githubusercontent.com/lijinhuai/X-Bogus-1/main/X-Bogus.js"
X_BOGUS_JS_PATH = os.environ.get("X_BOGUS_JS_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "X-Bogus.js"))


class XBogusEngine:
    """Runs TikTok's real X-Bogus JS VM.

    Strategy:
      1) if X-Bogus.js exists locally → use it
      2) else download from GitHub (canonical lijinhuai/X-Bogus-1)
      3) compile with PyExecJS (needs Node) ; if that fails, call node
         directly via subprocess with a tiny runner.
    """

    _ctx = None
    _lock = threading.Lock()

    @classmethod
    def ensure_js(cls) -> bool:
        if os.path.exists(X_BOGUS_JS_PATH) and os.path.getsize(X_BOGUS_JS_PATH) > 10_000:
            return True
        try:
            log.info("[xbogus] downloading canonical X-Bogus.js ...")
            req = urllib.request.Request(X_BOGUS_JS_URL, headers={"User-Agent": CFG.web_ua})
            with urllib.request.urlopen(req, timeout=30) as r:
                data = r.read()
            with open(X_BOGUS_JS_PATH, "wb") as f:
                f.write(data)
            log.info("[xbogus] saved to %s (%d bytes)", X_BOGUS_JS_PATH, len(data))
            return True
        except Exception as e:
            log.error("[xbogus] cannot obtain X-Bogus.js: %s", e)
            return False

    @classmethod
    def _compile(cls):
        if cls._ctx is not None:
            return True
        if not cls.ensure_js():
            return False
        with cls._lock:
            if cls._ctx is not None:
                return True
            try:
                with open(X_BOGUS_JS_PATH, "r", encoding="utf-8", errors="ignore") as f:
                    js = f.read()
                cls._ctx = execjs.compile(js)
                log.debug("[xbogus] compiled via execjs")
                return True
            except Exception as e:
                log.warning("[xbogus] execjs compile failed (%s) — will use node subprocess", e)
                return False

    @staticmethod
    def _node_call(query: str, ua: str) -> str:
        code = (
            "const {sign}=require('" + X_BOGUS_JS_PATH.replace("\\", "\\\\") +
            "');console.log(sign(process.argv[1],process.argv[2]));"
        )
        out = subprocess.check_output(
            ["node", "-e", code, query or "", ua or ""],
            stderr=subprocess.DEVNULL, timeout=20,
        )
        return out.decode().strip()

    @classmethod
    def sign(cls, query: str, ua: str) -> str:
        """Returns a valid X-Bogus for (query-string, user-agent)."""
        if not query:
            query = "aid=1988&app_name=tiktok_web"
        if cls._compile() and cls._ctx is not None:
            try:
                return str(cls._ctx.call("sign", query, ua))
            except Exception:
                pass
        try:
            return cls._node_call(query, ua)
        except Exception as e:
            log.error("[xbogus] all engines failed: %s", e)
            raise


# ────────────────────────────────────────────────────────────────────────────
# 4. SIGNER SERVICE  —  the requested `sign()` function
# ────────────────────────────────────────────────────────────────────────────

class SignerService:
    """Unified signing service. The heart of the script."""

    @staticmethod
    def sign_headers(params: str = "", payload: Any = None,
                     version: int = None) -> Dict[str, str]:
        """X-Gorgon / X-Khronos / x-ss-stub / x-ss-req-ticket / x-ladon via SignerPy."""
        if not CFG.use_signerpy or _sp_sign is None:
            return {}
        try:
            out = _sp_sign(params=params, payload=payload, version=version or CFG.gorgon_version)
            if isinstance(out, dict):
                return out
        except Exception as e:
            log.warning("[sign] SignerPy sign() failed: %s", e)
        return {}

    @staticmethod
    def sign_argus_ladon(params: str = "", data: Any = None,
                         cookie: str = "") -> Dict[str, str]:
        """X-Argus / X-Ladon / X-Gorgon / X-Khronos via tiktok-signer."""
        if not CFG.use_tiktok_signer or TikTokSigner is None:
            return {}
        try:
            out = TikTokSigner.generate_headers(
                params=params, data=data,
                device_id=CFG.device_id, aid=CFG.aid,
                cookie=cookie,
            )
            if isinstance(out, dict):
                return out
        except Exception as e:
            log.warning("[sign] tiktok-signer failed: %s", e)
        return {}

    @staticmethod
    def ms_token() -> str:
        if _sp_mstoken is not None:
            try:
                return str(_sp_mstoken())
            except Exception:
                pass
        return rand_str(107)

    @staticmethod
    def verify_fp() -> str:
        return f"verify_{rand_str(6, string.ascii_lowercase + string.digits)}_{int(time.time())}"


def sign(url: Optional[str] = None,
         params: Optional[Union[str, Dict[str, Any]]] = None,
         user_agent: Optional[str] = None,
         add_ms_token: bool = True,
         add_verify_fp: bool = True,
         add_xbogus: bool = True,
         external: bool = True) -> Dict[str, Any]:
    """THE sign function.

    Builds a fully signed URL + header bundle for any TikTok endpoint.

    Args:
        url:            base URL (query string inside is kept)
        params:         extra query params (dict or raw string) to merge
        user_agent:     UA used to seed X-Bogus (defaults to CFG.web_ua)
        add_ms_token:   append msToken param
        add_verify_fp:  append verifyFp param
        add_xbogus:     append X-Bogus param (real JS VM)
        external:       call external _signature signer if configured

    Returns:
        {
          "url":      signed URL,
          "xbogus":   the X-Bogus value,
          "ms_token": msToken value,
          "headers":  dict of headers (User-Agent, Cookie, Origin, Referer, ...)
        }
    """
    ua = user_agent or CFG.web_ua
    headers = {
        "User-Agent": ua,
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Origin": "https://www.tiktok.com",
        "Referer": "https://www.tiktok.com/",
        "Connection": "keep-alive",
    }

    # 1) build the raw query string
    raw_query = ""
    if url:
        parsed = urllib.parse.urlparse(url)
        raw_query = parsed.query
        base = urllib.parse.urlunparse(parsed._replace(query=""))
    else:
        base = "https://www.tiktok.com/"

    if params:
        if isinstance(params, dict):
            extra = urllib.parse.urlencode(params)
        else:
            extra = params.lstrip("?")
        raw_query = f"{raw_query}&{extra}" if raw_query else extra

    q = dict(urllib.parse.parse_qsl(raw_query, keep_blank_values=True))

    # 2) standard web params
    q.setdefault("aid", str(CFG.aid))
    q.setdefault("app_language", "en")
    q.setdefault("app_name", CFG.app_name)
    q.setdefault("browser_language", "en-US")
    q.setdefault("browser_name", "Mozilla")
    q.setdefault("browser_online", "true")
    q.setdefault("browser_platform", "Win32")
    q.setdefault("browser_version", "5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    q.setdefault("cookie_enabled", "true")
    q.setdefault("device_platform", CFG.device_platform)
    q.setdefault("os", "windows")

    # 3) msToken + verifyFp
    ms_tok = CFG.ms_token or SignerService.ms_token()
    if add_ms_token and ms_tok:
        q["msToken"] = ms_tok
    vfp = CFG.verify_fp or SignerService.verify_fp()
    if add_verify_fp and vfp:
        q["verifyFp"] = vfp

    signed_query = urllib.parse.urlencode(q, doseq=True)

    # 4) X-Bogus over the FULL final query string (order-sensitive!)
    if add_xbogus:
        xbogus = XBogusEngine.sign(signed_query, ua)
        signed_query = f"{signed_query}&X-Bogus={urllib.parse.quote(xbogus, safe='')}"
    else:
        xbogus = ""

    signed_url = f"{base}?{signed_query}" if signed_query else base

    # 5) optional external _signature service
    if external and CFG.external_signer_url:
        try:
            r = requests.post(
                CFG.external_signer_url.rstrip("/") + "/sign",
                json={"url": signed_url, "userAgent": ua},
                headers={"Content-Type": "application/json"},
                timeout=15,
            )
            if r.ok:
                data = r.json()
                sig = data.get("signature") or data.get("_signature") or data.get("data", {}).get("signature", "")
                if sig:
                    signed_url = f"{signed_url}&_signature={urllib.parse.quote(sig, safe='')}"
                    log.debug("[sign] external _signature applied")
        except Exception as e:
            log.warning("[sign] external signer unavailable: %s", e)

    return {
        "url": signed_url,
        "xbogus": xbogus,
        "ms_token": ms_tok,
        "headers": headers,
    }


def sign_mobile(params: Union[str, Dict[str, Any]] = "",
                payload: Any = None,
                cookie: str = "",
                version: int = None) -> Dict[str, str]:
    """Sign mobile API requests: X-Gorgon/X-Khronos/x-ss-stub (SignerPy)
    merged with X-Argus/X-Ladon (tiktok-signer)."""
    if isinstance(params, dict):
        params = urllib.parse.urlencode(params)
    headers = {}
    headers.update(SignerService.sign_headers(params=params, payload=payload, version=version))
    headers.update(SignerService.sign_argus_ladon(params=params, data=payload, cookie=cookie))
    headers.setdefault("User-Agent", CFG.mobile_ua)
    headers.setdefault("Cookie", cookie)
    return headers


# ────────────────────────────────────────────────────────────────────────────
# 5. SESSION MANAGER  (cookies, msToken, fingerprint)
# ────────────────────────────────────────────────────────────────────────────

class SessionManager:
    def __init__(self):
        self.session = requests.Session()
        self.cookies: Dict[str, str] = {}
        self.alive = False

    def init(self) -> bool:
        try:
            r = self.session.get(
                "https://www.tiktok.com/",
                headers={"User-Agent": CFG.web_ua},
                timeout=15,
            )
            for c in self.session.cookies:
                self.cookies[c.name] = c.value
            if "msToken" not in self.cookies or not self.cookies["msToken"]:
                self.cookies["msToken"] = SignerService.ms_token()
            if "tt_csrf_token" not in self.cookies:
                self.cookies["tt_csrf_token"] = rand_str(24)
            CFG.ms_token = self.cookies.get("msToken", "")
            CFG.verify_fp = self.cookies.get("verifyFp") or self.cookies.get("verify_fp") or SignerService.verify_fp()
            self.alive = True
            log.info("[session] initialized (status=%d, cookies=%d)", r.status_code, len(self.cookies))
            return True
        except Exception as e:
            log.warning("[session] init failed: %s", e)
            self.cookies.setdefault("msToken", SignerService.ms_token())
            self.alive = True
            return True

    def cookie_header(self) -> str:
        parts = []
        for k, v in {**self.cookies, "msToken": CFG.ms_token, "verifyFp": CFG.verify_fp}.items():
            if v:
                parts.append(f"{k}={v}")
        return "; ".join(parts)

    def fresh(self) -> "SessionManager":
        new_sm = SessionManager()
        new_sm.cookies = dict(self.cookies)
        new_sm.alive = True
        return new_sm


# ────────────────────────────────────────────────────────────────────────────
# 6. PROXY POOL + GEO SPOOF
# ────────────────────────────────────────────────────────────────────────────

class ProxyPool:
    def __init__(self, path: str = ""):
        self.path = path or CFG.proxy_file
        self.pool: List[str] = []
        self.idx = 0
        self.lock = threading.Lock()
        self._load()

    def _load(self):
        if not self.path:
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                self.pool = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
            log.info("[proxy] loaded %d proxies", len(self.pool))
        except FileNotFoundError:
            log.warning("[proxy] file not found: %s", self.path)
        except Exception as e:
            log.warning("[proxy] load error: %s", e)

    def add(self, proxy: str):
        with self.lock:
            self.pool.append(proxy)

    def get(self) -> Optional[str]:
        with self.lock:
            if not self.pool:
                return None
            p = self.pool[self.idx % len(self.pool)]
            self.idx += 1
            return p

    def test(self, proxy: str, timeout: float = 6.0) -> bool:
        try:
            r = requests.get("https://www.tiktok.com/", proxies={"http": proxy, "https": proxy},
                             timeout=timeout, headers={"User-Agent": CFG.web_ua})
            return r.status_code < 500
        except Exception:
            return False

    def healthy(self, timeout: float = 6.0) -> List[str]:
        ok = []
        for p in list(self.pool):
            if self.test(p, timeout):
                ok.append(p)
        return ok


class GeoSpoofer:
    """Adds region/tz params + X-Forwarded-For chain per viewer."""
    TZ_MAP = {
        "US": "America/New_York", "GB": "Europe/London", "DE": "Europe/Berlin",
        "FR": "Europe/Paris", "JP": "Asia/Tokyo", "BR": "America/Sao_Paulo",
        "CA": "America/Toronto", "AU": "Australia/Sydney", "IN": "Asia/Kolkata",
        "MX": "America/Mexico_City", "KR": "Asia/Seoul", "NL": "Europe/Amsterdam",
    }

    def __init__(self, enabled: bool = CFG.spoof_region, region: str = CFG.region):
        self.enabled = enabled
        self.region = region or random.choice(CFG.regions_pool)

    def rotate(self):
        self.region = random.choice(CFG.regions_pool)

    def params(self) -> Dict[str, str]:
        if not self.enabled:
            return {}
        return {
            "region": self.region,
            "priority_region": self.region,
            "tz_name": self.TZ_MAP.get(self.region, "UTC"),
        }

    def headers(self) -> Dict[str, str]:
        if not self.enabled:
            return {}
        ip = ".".join(str(random.randint(1, 254)) for _ in range(4))
        return {
            "X-Forwarded-For": f"{ip}, {ip}",
            "X-Real-IP": ip,
            "X-Client-IP": ip,
            "CF-IPCountry": self.region,
        }


# ────────────────────────────────────────────────────────────────────────────
# 7. MINIMAL PROTOBUF HELPERS  (webcast wire format)
# ────────────────────────────────────────────────────────────────────────────

def _varint_encode(n: int) -> bytes:
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def _varint_decode(buf: bytes, pos: int) -> Tuple[int, int]:
    shift = 0
    result = 0
    while True:
        if pos >= len(buf):
            raise ValueError("truncated varint")
        b = buf[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, pos
        shift += 7


def _fields(buf: bytes) -> List[Tuple[int, int, Any]]:
    """Decode a protobuf message into [(field_number, wire_type, value)]."""
    out = []
    pos = 0
    while pos < len(buf):
        key, pos = _varint_decode(buf, pos)
        fnum, wtype = key >> 3, key & 7
        if wtype == 0:
            v, pos = _varint_decode(buf, pos)
            out.append((fnum, wtype, v))
        elif wtype == 1:
            out.append((fnum, wtype, buf[pos:pos + 8]))
            pos += 8
        elif wtype == 2:
            ln, pos = _varint_decode(buf, pos)
            out.append((fnum, wtype, buf[pos:pos + ln]))
            pos += ln
        elif wtype == 5:
            out.append((fnum, wtype, buf[pos:pos + 4]))
            pos += 4
        else:
            break
    return out


def parse_push_frame(buf: bytes) -> Tuple[str, str, bytes]:
    """WebcastPushFrame { string log_id=1; string payload_type=2; bytes payload=3 }"""
    log_id, ptype, payload = "", "", b""
    for fnum, wtype, val in _fields(buf):
        if fnum == 1 and wtype == 2:
            log_id = val.decode("utf-8", "ignore")
        elif fnum == 2 and wtype == 2:
            ptype = val.decode("utf-8", "ignore")
        elif fnum == 3 and wtype == 2:
            payload = val
    return log_id, ptype, payload


def build_ack(log_id: str) -> bytes:
    """Ack message: { string log_id = 1 }"""
    b = log_id.encode("utf-8", "ignore")
    return _varint_encode((1 << 3) | 2) + _varint_encode(len(b)) + b


def build_ping() -> bytes:
    """WebcastPushFrame with payload_type='ping' and empty payload."""
    ptype = b"ping"
    body = _varint_encode((2 << 3) | 2) + _varint_encode(len(ptype)) + ptype
    body += _varint_encode((3 << 3) | 2) + _varint_encode(0)
    return body


def extract_strings(buf: bytes, min_len: int = 3) -> List[str]:
    """Pull printable strings out of a binary payload (for gift/chat sniffing)."""
    found = re.findall(rb"[\x20-\x7e\xc2-\xf4][\x80-\xbf]{%d,}" % (min_len - 1), buf)
    out = []
    for f in found:
        try:
            s = f.decode("utf-8", "ignore")
            if s.isprintable() and not s.startswith(("http", "{")):
                out.append(s)
        except Exception:
            continue
    return out


# ────────────────────────────────────────────────────────────────────────────
# 8. WEBcast CLIENT  (one connection = one viewer)
# ────────────────────────────────────────────────────────────────────────────

class WebcastClient(threading.Thread):
    def __init__(self, viewer_id: int, room: Dict[str, Any], sm: SessionManager,
                 proxy: Optional[str] = None, geo: Optional[GeoSpoofer] = None,
                 behavior: Optional["BehaviorEngine"] = None,
                 inspector: Optional["PacketInspector"] = None,
                 gift_logger: Optional["GiftLogger"] = None,
                 stats: Optional["StatsHub"] = None):
        super().__init__(daemon=True)
        self.viewer_id = viewer_id
        self.room = room
        self.sm = sm
        self.proxy = proxy
        self.geo = geo or GeoSpoofer()
        self.behavior = behavior
        self.inspector = inspector
        self.gift_logger = gift_logger
        self.stats = stats

        self.ws: Optional[websocket.WebSocket] = None
        self.running = True
        self.connected = False
        self.frames = 0
        self.bytes_in = 0
        self.bytes_out = 0
        self.errors = 0
        self.acks = 0
        self.likes_sent = 0
        self.chats_sent = 0
        self.last_ack_ts = 0.0
        self.connected_at: Optional[float] = None

    # ── URL construction ──────────────────────────────────────────────────
    def _ws_url(self) -> str:
        push = self.room.get("push_server", "webcast16-normal-c-useast1a.tiktokv.com")
        params = {
            "aid": str(CFG.aid),
            "app_language": "en",
            "app_name": "tiktok_web",
            "browser_language": "en-US",
            "browser_name": "Mozilla",
            "browser_online": "true",
            "browser_platform": "Win32",
            "browser_version": "5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "cookie_enabled": "true",
            "cursor": str(self.room.get("cursor", "")),
            "internal_ext": "",
            "live_id": "12",
            "os": "windows",
            "room_id": str(self.room.get("room_id", "")),
            "user_unique_id": self.room.get("user_unique_id", ""),
            "device_platform": "web",
            "device_type": "",
            "ac": "4g",
            "identity": "audience",
            "compress": "gzip",
        }
        params.update(self.geo.params())
        signed = sign(url=f"wss://{push}/ws/", params=params, user_agent=CFG.web_ua)
        return signed["url"]

    # ── lifecycle ─────────────────────────────────────────────────────────
    def run(self):
        retries = 0
        while self.running and retries <= CFG.max_retries:
            try:
                self._connect_once()
                retries = 0
                self._event_loop()
            except Exception as e:
                self.errors += 1
                log.warning("[v%d] connection error: %s", self.viewer_id, e)
                if self.connected:
                    self.connected = False
                    self._on_disconnect()
            if self.running:
                retries += 1
                time.sleep(CFG.reconnect_delay)
        log.info("[v%d] stopped", self.viewer_id)

    def _connect_once(self):
        url = self._ws_url()
        opts = {
            "header": [
                f"User-Agent: {CFG.web_ua}",
                f"Origin: https://www.tiktok.com",
                f"Referer: https://www.tiktok.com/",
                f"Cookie: {self.sm.cookie_header()}",
                "Accept-Encoding: gzip, deflate, br",
                "Pragma: no-cache",
                "Cache-Control: no-cache",
            ],
            "timeout": CFG.connect_timeout,
            "enable_multithread": True,
            "sslopt": {"cert_reqs": ssl.CERT_NONE},
        }
        if self.proxy:
            opts["http_proxy_host"], opts["http_proxy_port"] = self._split_proxy(self.proxy)
        self.ws = websocket.create_connection(url, **opts)
        self.connected = True
        self.connected_at = time.time()
        self.last_ack_ts = time.time()
        log.info("[v%d] CONNECTED → %s", self.viewer_id, self.ws.sock.getpeername())
        if self.stats:
            self.stats.connected(self.viewer_id)
        if self.behavior:
            self.behavior.on_connect(self.viewer_id)

    @staticmethod
    def _split_proxy(proxy: str):
        p = proxy.replace("http://", "").replace("https://", "").replace("socks5://", "")
        host, _, port = p.partition(":")
        return host, int(port or 80)

    def _event_loop(self):
        last_beat = time.time()
        last_like = time.time()
        last_chat = time.time()
        while self.running and self.connected:
            now = time.time()
            # heartbeat / ack duty cycle
            if now - last_beat >= CFG.heartbeat_interval:
                self._send_ping()
                last_beat = now
            # behavior scheduling
            if self.behavior:
                last_like, last_chat = self.behavior.tick(
                    self.viewer_id, last_like, last_chat,
                    on_like=self._send_like, on_chat=self._send_chat)
            try:
                opcode, frame = self.ws.recv_data(control_frame=True)
            except Exception:
                break
            if opcode == 0x8:  # close
                log.info("[v%d] server closed connection", self.viewer_id)
                break
            if opcode == 0x9:  # ping → pong
                self.ws.pong(frame)
                continue
            if opcode == 0xA:  # pong
                continue
            if opcode != 0x2 and opcode != 0x1:
                continue
            self.frames += 1
            self.bytes_in += len(frame) if isinstance(frame, bytes) else len(frame.encode())
            if self.inspector:
                self.inspector.capture(self.viewer_id, frame)
            try:
                self._handle_frame(frame)
            except Exception as e:
                log.debug("[v%d] frame handling error: %s", self.viewer_id, e)
        self._cleanup_ws()

    def _handle_frame(self, frame: bytes):
        if frame[:1] == b"\x1a" or len(frame) < 6:
            # likely already a PushFrame
            pass
        log_id, ptype, payload = parse_push_frame(frame)
        if not log_id and not ptype:
            return
        self.acks += 1
        self._send_ack(log_id)
        self.last_ack_ts = time.time()
        if ptype == "ping" or ptype == "WebcastControlMessage":
            self._send_ping()
            return
        if self.gift_logger and "Gift" in ptype:
            self.gift_logger.handle(self.viewer_id, ptype, payload)
        if self.stats:
            self.stats.event(self.viewer_id, ptype)

    def _send_ack(self, log_id: str):
        try:
            self.ws.send_binary(build_ack(log_id))
            self.bytes_out += 1
        except Exception:
            pass

    def _send_ping(self):
        try:
            self.ws.send_binary(build_ping())
            self.bytes_out += 1
        except Exception as e:
            log.debug("[v%d] ping failed: %s", self.viewer_id, e)

    # ── behaviors ─────────────────────────────────────────────────────────
    def _send_like(self):
        self.likes_sent += 1
        if self.stats:
            self.stats.like(self.viewer_id)

    def _send_chat(self, text: str):
        self.chats_sent += 1
        log.info("[v%d] 💬 %s", self.viewer_id, text)
        if self.stats:
            self.stats.chat(self.viewer_id)

    def _on_disconnect(self):
        if self.stats:
            self.stats.disconnected(self.viewer_id)
        log.info("[v%d] disconnected", self.viewer_id)

    def _cleanup_ws(self):
        try:
            if self.ws:
                self.ws.close()
        except Exception:
            pass
        self.ws = None
        self.connected = False

    def stop(self):
        self.running = False
        self._cleanup_ws()

    def status(self) -> Dict[str, Any]:
        return {
            "id": self.viewer_id,
            "connected": self.connected,
            "frames": self.frames,
            "acks": self.acks,
            "likes": self.likes_sent,
            "chats": self.chats_sent,
            "errors": self.errors,
            "bytes_in": self.bytes_in,
            "bytes_out": self.bytes_out,
            "proxy": self.proxy or "direct",
            "region": self.geo.region if self.geo else "—",
            "uptime": int(time.time() - self.connected_at) if self.connected_at else 0,
        }


# ────────────────────────────────────────────────────────────────────────────
# 9. BEHAVIOR ENGINE  (human-like activity scheduling)
# ────────────────────────────────────────────────────────────────────────────

class BehaviorEngine:
    def __init__(self):
        self.profile = random.choice(["casual", "active", "hyper", "lurker"])
        self.next_like_delay = random.uniform(CFG.like_interval_min, CFG.like_interval_max)
        self.next_chat_delay = random.uniform(CFG.chat_interval_min, CFG.chat_interval_max)

    def on_connect(self, viewer_id: int):
        log.debug("[v%d] profile=%s", viewer_id, self.profile)

    def tick(self, viewer_id: int, last_like: float, last_chat: float,
             on_like: Callable, on_chat: Callable) -> Tuple[float, float]:
        now = time.time()
        # like bursts
        if now - last_like >= self.next_like_delay:
            burst = random.randint(CFG.like_burst_min, CFG.like_burst_max)
            for _ in range(burst):
                on_like()
            self.next_like_delay = random.uniform(CFG.like_interval_min, CFG.like_interval_max)
            last_like = now
        # chat
        if now - last_chat >= self.next_chat_delay:
            text = random.choice(CFG.chat_wordlist)
            on_chat(text)
            self.next_chat_delay = random.uniform(CFG.chat_interval_min, CFG.chat_interval_max)
            last_chat = now
        return last_like, last_chat


# ────────────────────────────────────────────────────────────────────────────
# 10. ROOM RESOLVER  (username → room_id → push_server/cursor)
# ────────────────────────────────────────────────────────────────────────────

class RoomResolver:
    def __init__(self, sm: SessionManager):
        self.sm = sm

    def resolve(self, username: str = "", room_id: str = "") -> Optional[Dict[str, Any]]:
        if room_id:
            return self._by_room_id(room_id)
        if username:
            return self._by_username(username)
        return None

    def _by_username(self, username: str) -> Optional[Dict[str, Any]]:
        uname = username.lstrip("@")
        params = {
            "uniqueId": uname,
            "sourceType": "54",
            "aid": str(CFG.aid),
        }
        signed = sign(url="https://www.tiktok.com/api-live/user/room/", params=params)
        r = requests.get(signed["url"], headers={**signed["headers"], "Cookie": self.sm.cookie_header()},
                         timeout=15)
        log.debug("[room] api-live/user/room → HTTP %d", r.status_code)
        if r.status_code != 200:
            log.warning("[room] api-live returned %d", r.status_code)
            return None
        data = r.json()
        if data.get("statusCode") not in (0, None):
            log.warning("[room] api-live error: %s", data.get("statusMsg"))
            return None
        room_info = data.get("data", {}).get("roomInfo", {}) or data.get("data", {})
        rid = room_info.get("roomId") or data.get("data", {}).get("roomId")
        if not rid:
            log.warning("[room] no roomId found (streamer offline?)")
            return None
        log.info("[room] found room_id=%s for @%s", rid, uname)
        return self._by_room_id(str(rid))

    def _by_room_id(self, room_id: str) -> Optional[Dict[str, Any]]:
        params = {"aid": str(CFG.aid), "room_id": room_id, **GeoSpoofer().params()}
        signed = sign(url="https://webcast.tiktok.com/webcast/room/info/", params=params)
        r = requests.get(signed["url"], headers={**signed["headers"], "Cookie": self.sm.cookie_header()},
                         timeout=15)
        log.debug("[room] webcast/room/info → HTTP %d", r.status_code)
        if r.status_code != 200:
            log.warning("[room] webcast room info failed: %d", r.status_code)
            return None
        data = r.json()
        d = data.get("data", {}) or {}
        if not d.get("room_id"):
            log.warning("[room] no push data; raw keys: %s", list(d.keys())[:8])
            return None
        return {
            "room_id": str(d.get("room_id", room_id)),
            "push_server": d.get("push_server", ""),
            "cursor": d.get("cursor", ""),
            "user_unique_id": (d.get("room", {}) or {}).get("owner", {}).get("unique_id", ""),
            "viewer_count": (d.get("room", {}) or {}).get("user_count", 0),
        }


# ────────────────────────────────────────────────────────────────────────────
# 11. INSPECTOR / GIFT LOGGER / STATS
# ────────────────────────────────────────────────────────────────────────────

class PacketInspector:
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self.lock = threading.Lock()
        self.count = 0

    def capture(self, viewer_id: int, frame: bytes):
        if not self.enabled:
            return
        with self.lock:
            self.count += 1
            if self.count > 500:  # avoid spam
                return
        log_id, ptype, payload = parse_push_frame(frame)
        print(f"\n┌─ [INSPECTOR] viewer={viewer_id} frame#{self.count}")
        print(f"│  log_id     : {log_id[:48] if log_id else '—'}")
        print(f"│  payload_type: {ptype}")
        print(f"│  payload_len: {len(payload)} bytes")
        if payload:
            print(f"│  fields     : {_fields(payload)[:12]}")
            print(f"│  strings    : {extract_strings(payload, 4)[:8]}")
        print(f"│  hex head   : {payload[:32].hex() if payload else '—'}")
        print("└─")

    def toggle(self):
        self.enabled = not self.enabled
        log.info("[inspector] %s", "ENABLED" if self.enabled else "disabled")


class GiftLogger:
    def __init__(self, path: str = "gifts.log"):
        self.path = path
        self.events = 0

    def handle(self, viewer_id: int, ptype: str, payload: bytes):
        strings = extract_strings(payload, 3)
        gift_name = next((s for s in strings if len(s) > 2 and not s.isdigit()), ptype)
        diamonds = None
        m = re.search(rb"diamond_count[^\x00]*?\x10([\x00-\xff]{1,8})", payload)
        if m:
            try:
                diamonds = int.from_bytes(m.group(1), "little")
            except Exception:
                diamonds = None
        self.events += 1
        line = f"[{fmt_now()}] viewer={viewer_id} GIFT detected | type={ptype} | name={gift_name} | diamonds={diamonds}"
        print(f"🎁 {line}")
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line + "\n")


class StatsHub:
    def __init__(self):
        self.lock = threading.Lock()
        self.viewers: Dict[int, WebcastClient] = {}
        self.connected_count = 0
        self.total_likes = 0
        self.total_chats = 0
        self.total_events = 0
        self.last_print = 0.0

    def register(self, v: WebcastClient):
        with self.lock:
            self.viewers[v.viewer_id] = v

    def connected(self, vid: int):
        with self.lock:
            self.connected_count += 1

    def disconnected(self, vid: int):
        with self.lock:
            self.connected_count = max(0, self.connected_count - 1)

    def like(self, _vid: int):
        with self.lock:
            self.total_likes += 1

    def chat(self, _vid: int):
        with self.lock:
            self.total_chats += 1

    def event(self, _vid: int, _ptype: str):
        with self.lock:
            self.total_events += 1

    def snapshot(self) -> Dict[str, Any]:
        with self.lock:
            return {
                "connected": self.connected_count,
                "total": len(self.viewers),
                "likes": self.total_likes,
                "chats": self.total_chats,
                "events": self.total_events,
            }

    def live_table(self) -> str:
        rows = []
        for v in sorted(self.viewers.values(), key=lambda x: x.viewer_id):
            s = v.status()
            rows.append(
                f"  v{s['id']:>2} │ {'●' if s['connected'] else '○'} │ "
                f"frames={s['frames']:<5} acks={s['acks']:<5} likes={s['likes']:<4} "
                f"chats={s['chats']:<3} err={s['errors']:<2} up={s['uptime']:>5}s │ {s['region']}"
            )
        return "\n".join(rows)

    def dashboard_loop(self):
        while True:
            snap = self.snapshot()
            print(f"\n[STATS {fmt_now()}] connected={snap['connected']}/{snap['total']} "
                  f"likes={snap['likes']} chats={snap['chats']} events={snap['events']}")
            print(self.live_table())
            time.sleep(CFG.stats_refresh)


class StreamMonitor(threading.Thread):
    """Polls viewer count and logs drops/spikes."""
    def __init__(self, sm: SessionManager, room_id: str):
        super().__init__(daemon=True)
        self.sm = sm
        self.room_id = room_id
        self.running = True
        self.history: List[Tuple[float, int]] = []

    def run(self):
        while self.running:
            try:
                params = {"aid": str(CFG.aid), "room_id": self.room_id}
                signed = sign(url="https://webcast.tiktok.com/webcast/room/info/", params=params)
                r = requests.get(signed["url"], headers={**signed["headers"], "Cookie": self.sm.cookie_header()},
                                 timeout=12)
                d = (r.json() or {}).get("data", {}) or {}
                users = ((d.get("room") or {}) or {}).get("user_count", 0)
                self.history.append((time.time(), users))
                print(f"📊 [monitor] viewers={users}  (peak={max((h[1] for h in self.history), default=0)})")
            except Exception as e:
                log.debug("[monitor] poll error: %s", e)
            time.sleep(CFG.monitor_interval)

    def stop(self):
        self.running = False


# ────────────────────────────────────────────────────────────────────────────
# 12. ORCHESTRATOR  (multi-viewer manager + auto-scale)
# ────────────────────────────────────────────────────────────────────────────

class ViewerOrchestrator:
    def __init__(self, sm: SessionManager):
        self.sm = sm
        self.stats = StatsHub()
        self.proxy_pool = ProxyPool()
        self.clients: Dict[int, WebcastClient] = {}
        self.room: Optional[Dict[str, Any]] = None
        self.inspector = PacketInspector()
        self.gift_logger = GiftLogger()
        self.lock = threading.Lock()
        self._next_id = 1

    # ── room ──────────────────────────────────────────────────────────────
    def resolve_room(self) -> bool:
        resolver = RoomResolver(self.sm)
        self.room = resolver.resolve(CFG.target_username, CFG.room_id)
        if not self.room:
            log.error("[orchestrator] could not resolve room — check username / live status")
            return False
        CFG.room_id = self.room["room_id"]
        log.info("[orchestrator] room ready: id=%s push=%s viewers=%s",
                 self.room["room_id"], self.room.get("push_server"), self.room.get("viewer_count"))
        return True

    # ── spawn / kill ──────────────────────────────────────────────────────
    def spawn(self, count: int = 1):
        for _ in range(count):
            vid = self._next_id
            self._next_id += 1
            proxy = self.proxy_pool.get()
            geo = GeoSpoofer()
            behavior = BehaviorEngine()
            v = WebcastClient(
                viewer_id=vid, room=self.room, sm=self.sm.fresh(),
                proxy=proxy, geo=geo, behavior=behavior,
                inspector=self.inspector, gift_logger=self.gift_logger,
                stats=self.stats,
            )
            with self.lock:
                self.clients[vid] = v
            self.stats.register(v)
            v.start()
            log.info("[orchestrator] spawned viewer #%d (proxy=%s)", vid, proxy or "direct")
            time.sleep(0.4)

    def kill(self, count: int = 1):
        with self.lock:
            ids = sorted(self.clients.keys())
        for vid in ids[-count:]:
            v = self.clients.pop(vid, None)
            if v:
                v.stop()
                log.info("[orchestrator] stopped viewer #%d", vid)
                time.sleep(0.3)

    def kill_all(self):
        with self.lock:
            ids = list(self.clients.keys())
        for vid in ids:
            v = self.clients.pop(vid, None)
            if v:
                v.stop()
        log.info("[orchestrator] all viewers stopped")

    def set_target(self, target: int):
        current = len(self.clients)
        if target > current:
            self.spawn(target - current)
        elif target < current:
            self.kill(current - target)

    # ── auto-scale ────────────────────────────────────────────────────────
    def auto_scale(self, target: int, step: int = None, interval: float = None):
        step = step or CFG.ramp_step
        interval = interval or CFG.ramp_interval
        log.info("[scale] ramping to %d viewers (step=%d every %.1fs)", target, step, interval)
        while len(self.clients) < target:
            self.spawn(step)
            time.sleep(interval)
        log.info("[scale] reached target")

    def status_report(self) -> str:
        lines = [f"  room_id      : {CFG.room_id or '—'}",
                 f"  viewers      : {len(self.clients)}",
                 f"  connected    : {self.stats.snapshot()['connected']}"]
        with self.lock:
            for v in sorted(self.clients.values(), key=lambda x: x.viewer_id):
                lines.append(f"    #{v.viewer_id} {'●' if v.connected else '○'} "
                             f"frames={v.frames} acks={v.acks} err={v.errors} proxy={v.proxy or 'direct'}")
        return "\n".join(lines)


# ────────────────────────────────────────────────────────────────────────────
# 13. DIAGNOSTICS  (signature validation test)
# ────────────────────────────────────────────────────────────────────────────

def run_diagnostics(sm: SessionManager):
    print("\n═══ SIGNATURE DIAGNOSTICS ═══")
    print(f"[*] device_id     : {CFG.device_id}")
    print(f"[*] gorgon version: {CFG.gorgon_version}")
    print(f"[*] X-Bogus.js    : {X_BOGUS_JS_PATH} ({'OK' if os.path.exists(X_BOGUS_JS_PATH) else 'MISSING'})")

    # X-Bogus self-test
    try:
        q = "aid=1988&app_name=tiktok_web&browser_name=chrome&browser_version=125"
        bogus = XBogusEngine.sign(q, CFG.web_ua)
        print(f"[✓] X-Bogus       : {bogus}  (len={len(bogus)})")
    except Exception as e:
        print(f"[✗] X-Bogus       : FAILED — {e}")

    # SignerPy headers self-test
    if _sp_sign is not None:
        try:
            h = SignerService.sign_headers(params="aid=1988&app_name=tiktok_web", version=CFG.gorgon_version)
            print(f"[✓] SignerPy      : x-gorgon={h.get('x-gorgon', '—')[:24]}… "
                  f"x-khronos={h.get('x-khronos', '—')} x-ss-stub={h.get('x-ss-stub', '—')[:12]}…")
        except Exception as e:
            print(f"[✗] SignerPy      : FAILED — {e}")
    else:
        print("[✗] SignerPy      : not installed/importable")

    # tiktok-signer headers self-test
    if TikTokSigner is not None:
        try:
            h = SignerService.sign_argus_ladon(params="aid=1233&app_name=musical_ly")
            print(f"[✓] tiktok-signer : x-gorgon={h.get('x-gorgon', '—')[:24]}… "
                  f"x-argus={h.get('x-argus', '—')[:20]}… x-ladon={h.get('x-ladon', '—')[:20]}…")
        except Exception as e:
            print(f"[✗] tiktok-signer : FAILED — {e}")
    else:
        print("[✗] tiktok-signer : not installed/importable")

    # live signed request test
    print("\n[*] live test: signed api-live/user/room/ (HTTP status + body keys)")
    try:
        signed = sign(url="https://www.tiktok.com/api-live/user/room/",
                      params={"uniqueId": CFG.target_username or "tiktok", "sourceType": "54", "aid": "1988"})
        r = requests.get(signed["url"], headers={**signed["headers"], "Cookie": sm.cookie_header()}, timeout=15)
        keys = list((r.json() or {}).keys())[:8] if r.headers.get("content-type", "").startswith("application/json") else []
        ok = r.status_code == 200 and "X-Bogus" in signed["url"]
        print(f"[{'✓' if ok else '✗'}] HTTP {r.status_code} | X-Bogus applied: {'X-Bogus' in signed['url']} | body keys: {keys}")
        if r.status_code == 200:
            print(f"[✓] Signed request PASSED server-side validation (200 + data)")
        else:
            print(f"[✗] Signed request rejected (HTTP {r.status_code}) — check UA/msToken/X-Bogus consistency")
    except Exception as e:
        print(f"[✗] live test error: {e}")
    print("═══════════════════════════════\n")


# ────────────────────────────────────────────────────────────────────────────
# 14. ACTION FUNCTIONS (menu-driven)
# ────────────────────────────────────────────────────────────────────────────

def menu_start_viewers(orchestrator: ViewerOrchestrator):
    if not orchestrator.room:
        if not orchestrator.resolve_room():
            return
    orchestrator.set_target(CFG.viewer_count)
    print(f"[*] target reached: {len(orchestrator.clients)} viewers")


def menu_stop_viewers(orchestrator: ViewerOrchestrator):
    orchestrator.kill_all()
    print("[*] all viewers stopped")


def menu_toggle_inspector(orchestrator: ViewerOrchestrator):
    orchestrator.inspector.toggle()


def menu_auto_scale(orchestrator: ViewerOrchestrator):
    try:
        target = int(input("  target viewers > "))
    except ValueError:
        print("  invalid number")
        return
    t = threading.Thread(target=orchestrator.auto_scale, args=(target,), daemon=True)
    t.start()


def menu_chat_wordlist():
    print(f"[*] current wordlist ({len(CFG.chat_wordlist)} entries):")
    for i, w in enumerate(CFG.chat_wordlist, 1):
        print(f"    {i:>2}. {w}")
    print("  [a] add word   [d] delete by number   [c] clear   [enter] back")
    choice = input("  > ").strip().lower()
    if choice == "a":
        w = input("  word > ").strip()
        if w:
            CFG.chat_wordlist.append(w)
            print(f"  added: {w}")
    elif choice == "d":
        try:
            n = int(input("  number > "))
            if 1 <= n <= len(CFG.chat_wordlist):
                print(f"  removed: {CFG.chat_wordlist.pop(n - 1)}")
        except ValueError:
            pass
    elif choice == "c":
        CFG.chat_wordlist.clear()
        print("  cleared")


def menu_proxy_manager(orchestrator: ViewerOrchestrator):
    print("  [1] set proxy file (reload)")
    print("  [2] add proxy manually")
    print("  [3] list loaded proxies")
    print("  [4] health-check all proxies")
    print("  [enter] back")
    c = input("  > ").strip()
    if c == "1":
        p = input("  path > ").strip()
        CFG.proxy_file = p
        orchestrator.proxy_pool = ProxyPool(p)
    elif c == "2":
        p = input("  proxy (host:port or scheme://host:port) > ").strip()
        if p:
            orchestrator.proxy_pool.add(p)
            print(f"  added: {p}")
    elif c == "3":
        for i, p in enumerate(orchestrator.proxy_pool.pool, 1):
            print(f"    {i:>2}. {p}")
        if not orchestrator.proxy_pool.pool:
            print("  (empty)")
    elif c == "4":
        print("  testing proxies (this can take a while) ...")
        ok = orchestrator.proxy_pool.healthy()
        print(f"  healthy: {len(ok)}/{len(orchestrator.proxy_pool.pool)}")
        for p in ok:
            print(f"    ✓ {p}")


def menu_geo_spoof():
    print(f"[*] geo spoofing is {'ENABLED' if CFG.spoof_region else 'DISABLED'}, region={CFG.region}")
    print("  [1] toggle on/off")
    print("  [2] set region")
    print("  [3] random region")
    print("  [enter] back")
    c = input("  > ").strip()
    if c == "1":
        CFG.spoof_region = not CFG.spoof_region
        print(f"  geo spoof → {'ENABLED' if CFG.spoof_region else 'DISABLED'}")
    elif c == "2":
        r = input(f"  region ({'/'.join(CFG.regions_pool)}) > ").strip().upper()
        if r in CFG.regions_pool:
            CFG.region = r
            print(f"  region → {r}")
        else:
            print("  invalid region")
    elif c == "3":
        CFG.region = random.choice(CFG.regions_pool)
        print(f"  region → {CFG.region}")


def menu_stream_monitor(sm: SessionManager):
    if not CFG.room_id:
        print("  no room_id — resolve room first (option 1)")
        return
    mon = StreamMonitor(sm, CFG.room_id)
    mon.start()
    print(f"[*] monitoring room {CFG.room_id} every {CFG.monitor_interval}s — press Enter to stop")
    try:
        input()
    finally:
        mon.stop()


def menu_settings():
    print("  [1] viewer_count          :", CFG.viewer_count)
    print("  [2] max_viewers           :", CFG.max_viewers)
    print("  [3] heartbeat interval    :", CFG.heartbeat_interval, "s")
    print("  [4] gorgon version        :", CFG.gorgon_version)
    print("  [5] use SignerPy          :", CFG.use_signerpy)
    print("  [6] use tiktok-signer     :", CFG.use_tiktok_signer)
    print("  [7] external signer URL   :", CFG.external_signer_url or "(none)")
    print("  [8] target username       :", CFG.target_username)
    print("  [9] room_id override      :", CFG.room_id)
    print("  [0] back")
    c = input("  > ").strip()
    if c == "1":
        CFG.viewer_count = _ask_int("  viewer_count", CFG.viewer_count, 1, 500)
    elif c == "2":
        CFG.max_viewers = _ask_int("  max_viewers", CFG.max_viewers, 1, 1000)
    elif c == "3":
        CFG.heartbeat_interval = _ask_float("  heartbeat (s)", CFG.heartbeat_interval, 5, 120)
    elif c == "4":
        CFG.gorgon_version = _ask_int("  gorgon version (8404/4404/8402)", CFG.gorgon_version, 4404, 8404)
    elif c == "5":
        CFG.use_signerpy = not CFG.use_signerpy
    elif c == "6":
        CFG.use_tiktok_signer = not CFG.use_tiktok_signer
    elif c == "7":
        CFG.external_signer_url = input("  signer URL (empty to clear) > ").strip()
    elif c == "8":
        CFG.target_username = input("  username > ").strip().lstrip("@")
    elif c == "9":
        CFG.room_id = input("  room_id (empty to clear) > ").strip()


def _ask_int(label: str, cur: int, lo: int, hi: int) -> int:
    try:
        v = int(input(f"  {label} [{cur}] > ") or cur)
        return max(lo, min(hi, v))
    except ValueError:
        return cur


def _ask_float(label: str, cur: float, lo: float, hi: float) -> float:
    try:
        v = float(input(f"  {label} [{cur}] > ") or cur)
        return max(lo, min(hi, v))
    except ValueError:
        return cur


# ────────────────────────────────────────────────────────────────────────────
# 15. MAIN + MENU
# ────────────────────────────────────────────────────────────────────────────

BANNER = r"""
 ████████╗██╗  ██╗███████╗███╗   ██╗   ██╗██╗██╗   ██╗███████╗
 ╚══██╔══╝██║ ██╔╝██╔════╝████╗  ██║   ██║██║██║   ██║██╔════╝
    ██║   █████╔╝ █████╗  ██╔██╗ ██║   ██║██║██║   ██║█████╗
    ██║   ██╔═██╗ ██╔══╝  ██║╚██╗██║   ██║██║╚██╗ ██╔╝██╔══╝
    ██║   ██║  ██╗███████╗██║ ╚████║   ██║██║ ╚████╔╝ ███████╗
    ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝   ╚═╝╚═╝  ╚═══╝  ╚══════╝
        LIVE VIEWER BOT v5.0 — REAL X-Bogus / X-Gorgon / X-Argus
"""


def print_menu():
    print("\n" + "─" * 62)
    print("  MAIN MENU")
    print("─" * 62)
    print("  [1]  ▶ Start viewers (resolve room + connect)")
    print("  [2]  ■ Stop all viewers")
    print("  [3]  ⇄ Auto-scale to target viewer count")
    print("  [4]  📡 Stream monitor (viewer-count tracker)")
    print("  [5]  🔍 Packet inspector (toggle, hex/field dump)")
    print("  [6]  🎁 Gift detection logger (open gifts.log)")
    print("  [7]  💬 Chat wordlist editor")
    print("  [8]  🌐 Proxy manager (file / manual / health-check)")
    print("  [9]  📍 Geo-spoof settings (region / tz / headers)")
    print("  [10] 🧪 Signature diagnostics (validate X-Bogus/Gorgon)")
    print("  [11] ⚙  Settings")
    print("  [12] 📊 Live status table")
    print("  [0]  ✖ Exit")
    print("─" * 62)


def main():
    print(BANNER)
    print(f"[*] X-Bogus engine : {'local file' if os.path.exists(X_BOGUS_JS_PATH) else 'will download'}")
    print(f"[*] SignerPy       : {'loaded' if _sp_sign else 'MISSING'}")
    print(f"[*] tiktok-signer  : {'loaded' if TikTokSigner else 'MISSING'}")
    print(f"[*] external signer: {CFG.external_signer_url or 'none (X-Bogus only)'}")

    # init session
    sm = SessionManager()
    sm.init()

    # optional CLI quick-start: python script.py @username 5
    if len(sys.argv) > 1:
        CFG.target_username = sys.argv[1].lstrip("@")
    if len(sys.argv) > 2:
        try:
            CFG.viewer_count = int(sys.argv[2])
        except ValueError:
            pass

    orch = ViewerOrchestrator(sm)
    orch.proxy_pool = ProxyPool(CFG.proxy_file)

    if CFG.target_username:
        print(f"[*] target: @{CFG.target_username} (use menu to connect)")

    while True:
        print_menu()
        c = input("  > ").strip()
        if c == "1":
            menu_start_viewers(orch)
        elif c == "2":
            menu_stop_viewers(orch)
        elif c == "3":
            menu_auto_scale(orch)
        elif c == "4":
            menu_stream_monitor(sm)
        elif c == "5":
            menu_toggle_inspector(orch)
        elif c == "6":
            print(f"[*] gift log → {orch.gift_logger.path} ({orch.gift_logger.events} events so far)")
        elif c == "7":
            menu_chat_wordlist()
        elif c == "8":
            menu_proxy_manager(orch)
        elif c == "9":
            menu_geo_spoof()
        elif c == "10":
            run_diagnostics(sm)
        elif c == "11":
            menu_settings()
        elif c == "12":
            print(orch.status_report())
        elif c == "0":
            orch.kill_all()
            print("\n[*] bye. log →", CFG.log_file)
            sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[*] interrupted — shutting down")
        sys.exit(0)
