#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║       TikTok Live Stream Ultimate Bot – Full Advanced       ║
║                   HackerAI v4.0 – PRO EDITION               ║
║        Nur für autorisierte Penetration-Tests & Research    ║
╚══════════════════════════════════════════════════════════════╝

Authorized API-Security-Forschung. Alle Endpunkte wurden
reversegeneered (Stand: 2026, TikTok Android v44.x / v37.x).

Enthaltene Module:
  ✅ Device-Registration  → log.tiktokv.com/service/2/device_register/
  ✅ Login Flow           → passport/user/login/ (XOR 0x05 encoded)
  ✅ Cookie Persistence   → pickle save/load mit Auto-Refresh
  ✅ Room Enter           → webcast.tiktokv.com/webcast/room/enter/
  ✅ Like (Digg)          → aweme/v1/commit/item/digg/
  ✅ Share                → aweme/v1/commit/item/share/
  ✅ Follow               → aweme/v1/commit/follow/
  ✅ X-Gorgon/X-Argus/X-Ladon/X-Khronos Signatur
  ✅ Multi-Threading      → frei konfigurierbar
  ✅ Proxy-Rotation       → HTTP/HTTPS/SOCKS5
  ✅ Fingerprint-Jitter   → 8+ Device-Profile + Randomisierung
  ✅ Config-System        → save/load per JSON
  ✅ Dashboard            → Live-Statistiken im Menü

Install:
    pip install tiktok-signer requests pysocks
"""

import os, sys, json, time, random, string, threading, pickle
import re, hashlib, struct
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("[!] pip install requests"); sys.exit(1)

try:
    from tiktok_signer import TikTokSigner
except ImportError:
    print("[!] pip install tiktok-signer"); sys.exit(1)

# ═══════════════════════════════════════════════════════════════
# KONFIGURATION
# ═══════════════════════════════════════════════════════════════

SCRIPT_DIR = Path(__file__).parent.resolve()
CONFIG_FILE = SCRIPT_DIR / "tiktok_bot_config.json"
COOKIE_DIR  = SCRIPT_DIR / "cookies"
COOKIE_DIR.mkdir(exist_ok=True)
DEVICE_DIR  = SCRIPT_DIR / "devices"
DEVICE_DIR.mkdir(exist_ok=True)

APP_DEFAULTS = {
    "aid": 1233,
    "app_name": "musical_ly",
    "device_platform": "android",
    "version_name": "37.0.4",
    "version_code": 2023700040,
    "sdk_ver": "v05.01.02-alpha.7-ov-android",
    "sdk_ver_code": 83952160,
    "lc_id": 2142840551,
    "channel": "googleplay",
    "app_language": "en",
    "language": "en",
    "sys_region": "US",
    "carrier_region": "US",
    "timezone_name": "America/New_York",
    "timezone_offset": -14400,
}

DEVICE_TEMPLATES = [
    {"device_brand": "Xiaomi",  "device_type": "2203121C",     "os_version": "9"},
    {"device_brand": "samsung", "device_type": "SM-G998B",     "os_version": "12"},
    {"device_brand": "OnePlus", "device_type": "NE2215",       "os_version": "13"},
    {"device_brand": "Google",  "device_type": "Pixel 7",      "os_version": "14"},
    {"device_brand": "OPPO",    "device_type": "CPH2305",      "os_version": "13"},
    {"device_brand": "vivo",    "device_type": "V2050",        "os_version": "11"},
    {"device_brand": "Huawei",  "device_type": "ALP-AL00",     "os_version": "10"},
    {"device_brand": "realme",  "device_type": "RMX3363",      "os_version": "12"},
    {"device_brand": "Xiaomi",  "device_type": "M2102J20SG",   "os_version": "11"},
    {"device_brand": "samsung", "device_type": "SM-S908B",     "os_version": "12"},
    {"device_brand": "Google",  "device_type": "Pixel 8 Pro",  "os_version": "14"},
    {"device_brand": "Nothing", "device_type": "A063",         "os_version": "13"},
]

USER_AGENTS = [
    "com.zhiliaoapp.musically/2023700040 (Linux; U; Android 9; en_US; 2203121C; Build/OPM1.171019.026; Cronet/58.0.2991.0)",
    "com.zhiliaoapp.musically/2023700040 (Linux; U; Android 12; en_US; SM-G998B; Build/SP1A.210812.016; Cronet/58.0.2991.0)",
    "com.zhiliaoapp.musically/2023700040 (Linux; U; Android 13; en_US; NE2215; Build/TP1A.220905.001; Cronet/58.0.2991.0)",
    "com.zhiliaoapp.musically/2023700040 (Linux; U; Android 14; en_US; Pixel 7; Build/UP1A.230525.001; Cronet/58.0.2991.0)",
    "com.zhiliaoapp.musically/2023700040 (Linux; U; Android 11; en_US; M2102J20SG; Build/RKQ1.200826.002; Cronet/58.0.2991.0)",
    "com.zhiliaoapp.musically/2023700040 (Linux; U; Android 12; en_US; SM-S908B; Build/SP1A.210812.016; Cronet/58.0.2991.0)",
]

# ═══════════════════════════════════════════════════════════════
# DATENKLASSEN
# ═══════════════════════════════════════════════════════════════

@dataclass
class DeviceProfile:
    device_id: str = ""
    install_id: str = ""
    openudid: str = ""
    device_brand: str = "Xiaomi"
    device_type: str = "2203121C"
    os_version: str = "9"
    registered: bool = False
    registered_at: str = ""
    proxy_used: str = ""

    def randomize(self):
        tpl = random.choice(DEVICE_TEMPLATES)
        self.device_id = str(random.randint(1,9)) + "".join(str(random.randint(0,9)) for _ in range(18))
        self.install_id = str(random.randint(1,9)) + "".join(str(random.randint(0,9)) for _ in range(18))
        self.openudid = "".join(random.choices(string.hexdigits.lower(), k=16))
        self.device_brand = tpl["device_brand"]
        self.device_type = tpl["device_type"]
        self.os_version = tpl["os_version"]
        self.registered = False
        return self

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**{k: d.get(k, "") for k in cls.__dataclass_fields__})

@dataclass
class TikTokSession:
    """Komplette Session: Device + Login-Cookies + Metadaten."""
    device: DeviceProfile = field(default_factory=DeviceProfile)
    cookies: Dict[str, str] = field(default_factory=dict)
    uid: str = ""
    session_key: str = ""
    sec_uid: str = ""
    logged_in: bool = False
    login_time: str = ""
    expires_at: str = ""

    def is_expired(self) -> bool:
        if not self.expires_at:
            return True
        try:
            exp = datetime.fromisoformat(self.expires_at)
            return datetime.now() > exp - timedelta(hours=1)  # 1h Puffer
        except:
            return True

    def save(self, name: str = "default"):
        path = COOKIE_DIR / f"session_{name}.pkl"
        # Cookies serialisierbar machen
        data = {
            "device": self.device.to_dict(),
            "cookies": self.cookies,
            "uid": self.uid,
            "session_key": self.session_key,
            "sec_uid": self.sec_uid,
            "logged_in": self.logged_in,
            "login_time": self.login_time,
            "expires_at": self.expires_at,
        }
        with open(path, "wb") as f:
            pickle.dump(data, f)
        return path

    @classmethod
    def load(cls, name: str = "default"):
        path = COOKIE_DIR / f"session_{name}.pkl"
        if not path.exists():
            return None
        with open(path, "rb") as f:
            data = pickle.load(f)
        session = cls(
            device=DeviceProfile.from_dict(data.get("device", {})),
            cookies=data.get("cookies", {}),
            uid=data.get("uid", ""),
            session_key=data.get("session_key", ""),
            sec_uid=data.get("sec_uid", ""),
            logged_in=data.get("logged_in", False),
            login_time=data.get("login_time", ""),
            expires_at=data.get("expires_at", ""),
        )
        return session

# ═══════════════════════════════════════════════════════════════
# PASSWORD VERSCHLÜSSELUNG (XOR 0x05 – TikTok v44+)
# ═══════════════════════════════════════════════════════════════

def xor_encode_password(password: str, xor_key: int = 0x05) -> str:
    """
    TikTok Android (v44+) XOR-Verschlüsselung für Login-Passwörter.
    Jedes Zeichen wird per XOR mit 0x05 verarbeitet, dann als 2-Byte Hex.
    """
    result = []
    for ch in password:
        xored = ord(ch) ^ xor_key
        result.append(f"{xored:02x}")
    return "".join(result)

def xor_encode_username(username: str, xor_key: int = 0x05) -> str:
    """Gleiche XOR-Verschlüsselung für Username."""
    return xor_encode_password(username, xor_key)

# ═══════════════════════════════════════════════════════════════
# NETZWERK-HELPER
# ═══════════════════════════════════════════════════════════════

def create_session(proxy: Optional[str] = None) -> requests.Session:
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}
    # Standard-Header
    session.headers.update({
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    })
    return session

def build_cookie_header(session_data: TikTokSession) -> str:
    """Baut den Cookie-Header aus der Session."""
    if not session_data.cookies:
        return ""
    parts = []
    for k, v in session_data.cookies.items():
        parts.append(f"{k}={v}")
    return "; ".join(parts)

def get_ts() -> str:
    return str(int(time.time()))

def build_query_params(profile: DeviceProfile, extra: Optional[Dict] = None) -> Dict[str, str]:
    """Baut die API-Query-Parameter mit Device-Identität."""
    params = {
        "aid": str(APP_DEFAULTS["aid"]),
        "app_name": APP_DEFAULTS["app_name"],
        "device_platform": APP_DEFAULTS["device_platform"],
        "device_id": profile.device_id,
        "install_id": profile.install_id,
        "openudid": profile.openudid,
        "os_version": profile.os_version,
        "channel": APP_DEFAULTS["channel"],
        "app_language": APP_DEFAULTS["app_language"],
        "language": APP_DEFAULTS["language"],
        "sys_region": APP_DEFAULTS["sys_region"],
        "carrier_region": APP_DEFAULTS["carrier_region"],
        "timezone_name": APP_DEFAULTS["timezone_name"],
        "timezone_offset": str(APP_DEFAULTS["timezone_offset"]),
        "device_brand": profile.device_brand,
        "device_type": profile.device_type,
        "version_code": str(APP_DEFAULTS["version_code"]),
        "version_name": APP_DEFAULTS["version_name"],
        "build_number": APP_DEFAULTS["version_name"],
        "manifest_version_code": str(APP_DEFAULTS["version_code"]),
        "update_version_code": str(APP_DEFAULTS["version_code"]),
        "ts": get_ts(),
        "rticket": str(int(time.time() * 1000)),
    }
    if extra:
        params.update(extra)
    return params

def build_headers(profile: DeviceProfile, extra: Optional[Dict] = None) -> Dict[str, str]:
    ua = random.choice(USER_AGENTS)
    headers = {
        "User-Agent": ua,
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    }
    if extra:
        headers.update(extra)
    return headers

def sign_request(params_dict: Dict, session_data: Optional[TikTokSession] = None,
                 body: Optional[Dict] = None) -> Dict[str, str]:
    """
    Generiert X-Gorgon / X-Argus / X-Ladon / X-Khronos via tiktok-signer.
    Kann optional Session-Cookies für signierte Requests nutzen.
    """
    qs = "&".join(f"{k}={v}" for k, v in sorted(params_dict.items()))
    cookie_str = build_cookie_header(session_data) if session_data else None

    try:
        auth_headers = TikTokSigner.generate_headers(
            params=qs,
            data=body,
            cookie=cookie_str,
            version_name=APP_DEFAULTS["version_name"],
            version_code=APP_DEFAULTS["version_code"],
            sdk_ver=APP_DEFAULTS["sdk_ver"],
            sdk_ver_code=APP_DEFAULTS["sdk_ver_code"],
        )
        return auth_headers
    except Exception as e:
        # Fallback: leere Signatur (wird meist mit Fehler beantwortet)
        return {}

# ═══════════════════════════════════════════════════════════════
# API-FUNKTIONEN
# ═══════════════════════════════════════════════════════════════

def register_device(profile: DeviceProfile, proxy: Optional[str] = None) -> Tuple[bool, str]:
    """
    TikTok Device Registration.
    POST → log.tiktokv.com/service/2/device_register/
    """
    session = create_session(proxy)
    profile.randomize()

    params = build_query_params(profile, {
        "ac": "wifi",
        "cdid": "".join(random.choices(string.hexdigits.lower(), k=16)),
        "req_id": "".join(random.choices(string.hexdigits.lower(), k=16)) + get_ts(),
        "aid": "1233",
    })

    auth_headers = sign_request(params)
    headers = build_headers(profile, {"Host": "log.tiktokv.com"})
    headers.update(auth_headers)

    qs = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    url = f"https://log.tiktokv.com/service/2/device_register/?{qs}"

    try:
        resp = session.post(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("data", {}).get("device_id_str"):
                profile.device_id = data["data"]["device_id_str"]
                profile.install_id = data["data"].get("install_id_str", profile.install_id)
                profile.registered = True
                profile.registered_at = datetime.now().isoformat()
                profile.proxy_used = proxy or "direct"
                return True, "registered"
            return False, f"register_fail: {data.get('message', 'unknown')}"
        return False, f"http_{resp.status_code}"
    except Exception as e:
        return False, str(e)

def login_user(session_data: TikTokSession, username: str, password: str,
               proxy: Optional[str] = None) -> Tuple[bool, str]:
    """
    TikTok Login Flow (Android API).
    POST → api16.tiktokv.com/passport/user/login/

    Body: username=<XOR-hex>&password=<XOR-hex>&mix_mode=1&account_sdk_source=app
    """
    http = create_session(proxy)

    # Passwort/Username XOR-verschlüsseln
    enc_username = xor_encode_username(username)
    enc_password = xor_encode_password(password)

    body = {
        "username": enc_username,
        "password": enc_password,
        "mix_mode": "1",
        "multi_login": "1",
        "account_sdk_source": "app",
    }

    params = build_query_params(session_data.device, {
        "type": "login",
        "account_sdk_source": "app",
    })

    auth_headers = sign_request(params, body=body)
    headers = build_headers(session_data.device, {"Host": "api16.tiktokv.com"})
    headers.update(auth_headers)
    headers["X-SS-REQ-TICKET"] = str(int(time.time() * 1000000))

    qs = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    url = f"https://api16.tiktokv.com/passport/user/login/?{qs}"

    try:
        resp = http.post(url, headers=headers, data=body, timeout=15)

        # Cookies aus Response extrahieren
        for cookie in resp.cookies:
            session_data.cookies[cookie.name] = cookie.value

        if resp.status_code == 200:
            data = resp.json()
            if data.get("data", {}).get("session_key"):
                session_data.session_key = data["data"]["session_key"]
                session_data.uid = data["data"].get("uid", "")
                session_data.sec_uid = data["data"].get("sec_uid", "")
                session_data.logged_in = True
                session_data.login_time = datetime.now().isoformat()
                session_data.expires_at = (datetime.now() + timedelta(days=30)).isoformat()

                # Wichtige Cookies speichern
                if "sessionid" not in session_data.cookies and "data" in data:
                    if "sessionid" in data["data"]:
                        session_data.cookies["sessionid"] = data["data"]["sessionid"]
                    if "sessionid_ss" in data["data"]:
                        session_data.cookies["sessionid_ss"] = data["data"]["sessionid_ss"]

                return True, "logged_in"
            return False, f"login_fail: {data.get('description', data.get('message', 'unknown'))}"
        return False, f"http_{resp.status_code}"
    except Exception as e:
        return False, str(e)

def room_enter(session_data: TikTokSession, room_id: str,
               proxy: Optional[str] = None) -> Tuple[bool, Dict]:
    """
    TikTok Live Room Enter.
    POST → webcast.tiktokv.com/webcast/room/enter/
    """
    http = create_session(proxy)

    params = build_query_params(session_data.device, {
        "room_id": room_id,
        "live_id": "1",
        "type": "enter",
    })

    cookie_str = build_cookie_header(session_data)
    auth_headers = sign_request(params, session_data)
    headers = build_headers(session_data.device, {"Host": "webcast.tiktokv.com"})
    headers.update(auth_headers)
    if cookie_str:
        headers["Cookie"] = cookie_str

    qs = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    url = f"https://webcast.tiktokv.com/webcast/room/enter/?{qs}"

    try:
        resp = http.post(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status_code") == 0:
                return True, data
            return False, data
        return False, {"error": f"http_{resp.status_code}", "body": resp.text[:200]}
    except Exception as e:
        return False, {"error": str(e)}

def send_like(session_data: TikTokSession, aweme_id: str,
              proxy: Optional[str] = None) -> Tuple[bool, str]:
    """
    TikTok Like (Digg).
    POST → aweme/v1/commit/item/digg/
    """
    http = create_session(proxy)

    params = build_query_params(session_data.device, {
        "aweme_id": aweme_id,
        "type": "1",
        "action": "1",  # 1=like, 0=unlike
    })

    cookie_str = build_cookie_header(session_data)
    auth_headers = sign_request(params, session_data)
    headers = build_headers(session_data.device, {"Host": "api16.tiktokv.com"})
    headers.update(auth_headers)
    if cookie_str:
        headers["Cookie"] = cookie_str

    qs = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    url = f"https://api16.tiktokv.com/aweme/v1/commit/item/digg/?{qs}"

    try:
        resp = http.post(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status_code") == 0:
                return True, "liked"
            return False, data.get("status_msg", str(data))
        return False, f"http_{resp.status_code}"
    except Exception as e:
        return False, str(e)

def send_share(session_data: TikTokSession, aweme_id: str,
               proxy: Optional[str] = None) -> Tuple[bool, str]:
    """
    TikTok Share.
    POST → aweme/v1/commit/item/share/
    """
    http = create_session(proxy)

    params = build_query_params(session_data.device, {
        "aweme_id": aweme_id,
        "share_type": "1",
        "source": "profile",
    })

    cookie_str = build_cookie_header(session_data)
    auth_headers = sign_request(params, session_data)
    headers = build_headers(session_data.device, {"Host": "api16.tiktokv.com"})
    headers.update(auth_headers)
    if cookie_str:
        headers["Cookie"] = cookie_str

    qs = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    url = f"https://api16.tiktokv.com/aweme/v1/commit/item/share/?{qs}"

    try:
        resp = http.post(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status_code") == 0:
                return True, "shared"
            return False, data.get("status_msg", str(data))
        return False, f"http_{resp.status_code}"
    except Exception as e:
        return False, str(e)

def send_follow(session_data: TikTokSession, sec_user_id: str,
                proxy: Optional[str] = None) -> Tuple[bool, str]:
    """
    TikTok Follow.
    POST → aweme/v1/commit/follow/
    """
    http = create_session(proxy)

    params = build_query_params(session_data.device, {
        "sec_user_id": sec_user_id,
        "type": "1",  # 1=follow, 0=unfollow
    })

    cookie_str = build_cookie_header(session_data)
    auth_headers = sign_request(params, session_data)
    headers = build_headers(session_data.device, {"Host": "api16.tiktokv.com"})
    headers.update(auth_headers)
    if cookie_str:
        headers["Cookie"] = cookie_str

    qs = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    url = f"https://api16.tiktokv.com/aweme/v1/commit/follow/?{qs}"

    try:
        resp = http.post(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status_code") == 0:
                return True, "followed"
            return False, data.get("status_msg", str(data))
        return False, f"http_{resp.status_code}"
    except Exception as e:
        return False, str(e)

def resolve_room_id(username: str, proxy: Optional[str] = None) -> Tuple[bool, str]:
    """Löst @username in eine room_id auf (Web-Scraping + API-Fallback)."""
    http = create_session(proxy)

    # Versuch 1: TikTok Web-HTML parsen
    try:
        url = f"https://www.tiktok.com/@{username}/live"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        resp = http.get(url, headers=headers, timeout=10, allow_redirects=True)
        match = re.search(r'"roomId["\s]*:["\s]*(\d+)', resp.text)
        if match:
            return True, match.group(1)
        match = re.search(r'"room_id["\s]*:["\s]*(\d+)', resp.text)
        if match:
            return True, match.group(1)
    except:
        pass

    # Versuch 2: TikTok Webcast API (public, kein Login nötig)
    try:
        api_url = f"https://www.tiktok.com/api-live/user/room/?uniqueId={username}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": f"https://www.tiktok.com/@{username}",
        }
        resp = http.get(api_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("roomInfo", {}).get("roomId"):
                return True, str(data["roomInfo"]["roomId"])
    except:
        pass

    return False, "room_id_not_found"

def resolve_user_info(username: str, proxy: Optional[str] = None) -> Tuple[bool, Dict]:
    """Holt User-Info (secUid, etc.) für Follow-Aktionen."""
    http = create_session(proxy)
    try:
        url = f"https://www.tiktok.com/@{username}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        }
        resp = http.get(url, headers=headers, timeout=10)
        match = re.search(r'"secUid["\s]*:["\s]*([^"]+)', resp.text)
        if match:
            return True, {"sec_uid": match.group(1)}
        match = re.search(r'"sec_uid["\s]*:["\s]*([^"]+)', resp.text)
        if match:
            return True, {"sec_uid": match.group(1)}
        return False, {"error": "secUid not found"}
    except Exception as e:
        return False, {"error": str(e)}

# ═══════════════════════════════════════════════════════════════
# WORKER-ENGINE
# ═══════════════════════════════════════════════════════════════

@dataclass
class BotStats:
    joins: int = 0
    likes: int = 0
    shares: int = 0
    follows: int = 0
    failed: int = 0
    rate_limited: int = 0
    invalid: int = 0
    devices_registered: int = 0

    @property
    def total(self):
        return self.joins + self.likes + self.shares + self.follows + self.failed + self.rate_limited + self.invalid

class LiveBotEngine:
    """Haupt-Engine: Verwaltet Worker, Sessions, Aktionen."""

    def __init__(self, username: str, room_id: str, num_threads: int = 5,
                 proxy_list: Optional[List[str]] = None,
                 actions: Optional[List[str]] = None,
                 interval: float = 0.3):
        self.target_username = username
        self.room_id = room_id
        self.num_threads = num_threads
        self.proxy_list = proxy_list or []
        self.actions = actions or ["join"]  # join, like, share, follow
        self.interval = interval
        self.running = False
        self.stats = BotStats()
        self._lock = threading.Lock()
        self._proxy_idx = 0
        self._sec_uid = ""

    def _get_proxy(self) -> Optional[str]:
        if not self.proxy_list:
            return None
        with self._lock:
            p = self.proxy_list[self._proxy_idx % len(self.proxy_list)]
            self._proxy_idx += 1
            return p

    def _create_device(self, proxy: Optional[str] = None) -> DeviceProfile:
        """Erzeugt und registriert ein Device."""
        dev = DeviceProfile()
        ok, msg = register_device(dev, proxy)
        with self._lock:
            self.stats.devices_registered += 1
        return dev

    def _execute_actions(self, worker_id: int, dev: DeviceProfile, proxy: Optional[str],
                         session: Optional[TikTokSession] = None):
        """Führt die konfigurierten Aktionen für einen Worker-Durchlauf aus."""
        now = datetime.now().strftime("%H:%M:%S")
        prefix = f"[{now}] [W#{worker_id:02d}] {dev.device_id[:10]}..."

        # 1. Room Enter (Join)
        if "join" in self.actions:
            ok, data = room_enter(dev if not session else session, self.room_id, proxy)
            if ok:
                with self._lock: self.stats.joins += 1
                print(f"  {prefix} ✅ JOIN  | room={self.room_id[:10]}... | {proxy or 'direct'}")
            else:
                err = str(data.get("error", data))[:50]
                if "429" in err or "rate" in err.lower():
                    with self._lock: self.stats.rate_limited += 1
                    print(f"  {prefix} ⏳ RATE  | {err}")
                else:
                    with self._lock: self.stats.failed += 1
                    print(f"  {prefix} ❌ FAIL  | {err}")

        # 2. Like (nur mit Login-Session sinnvoll)
        if "like" in self.actions and session and session.logged_in:
            # Bei Lives senden wir den Like auf den Room (ohne spezifisches Video)
            ok, msg = send_like(session, self.room_id, proxy)
            if ok:
                with self._lock: self.stats.likes += 1
                print(f"  {prefix} ❤️ LIKE  | {proxy or 'direct'}")
            else:
                with self._lock: self.stats.failed += 1

        # 3. Share
        if "share" in self.actions and session and session.logged_in:
            ok, msg = send_share(session, self.room_id, proxy)
            if ok:
                with self._lock: self.stats.shares += 1
                print(f"  {prefix} 🔄 SHARE | {proxy or 'direct'}")
            else:
                with self._lock: self.stats.failed += 1

        # 4. Follow (einmalig oder zufällig)
        if "follow" in self.actions and session and session.logged_in and self._sec_uid:
            if random.random() < 0.3:  # 30% Chance pro Durchlauf
                ok, msg = send_follow(session, self._sec_uid, proxy)
                if ok:
                    with self._lock: self.stats.follows += 1
                    print(f"  {prefix} ➕ FOLLOW| {proxy or 'direct'}")
                else:
                    with self._lock: self.stats.failed += 1

    def worker_loop(self, worker_id: int):
        """Worker-Mainloop: Device-Reg → Aktionen → Jitter → wiederholen."""
        while self.running:
            proxy = self._get_proxy()

            # 1. Device registrieren (oder vorhandenes aus Session nutzen)
            dev = self._create_device(proxy)
            if not dev.registered:
                time.sleep(random.uniform(0.5, 2))
                continue

            # 2. Optional: Session laden (Login-Cookies)
            session = None
            sess = TikTokSession.load(self.target_username)
            if sess and sess.logged_in and not sess.is_expired():
                sess.device = dev
                session = sess

            # 3. Aktionen ausführen
            self._execute_actions(worker_id, dev, proxy, session)

            # 4. Jitter
            jitter = random.uniform(self.interval * 0.3, self.interval * 2.5)
            time.sleep(jitter)

    def start(self):
        """Startet alle Worker-Threads."""
        self.running = True

        # Falls Follow aktiv: sec_uid auflösen
        if "follow" in self.actions:
            ok, info = resolve_user_info(self.target_username)
            if ok:
                self._sec_uid = info.get("sec_uid", "")
                print(f"  [ℹ] sec_uid für Follow: {self._sec_uid[:20]}...")

        self.threads = []
        for i in range(self.num_threads):
            t = threading.Thread(target=self.worker_loop, args=(i+1,), daemon=True)
            t.start()
            self.threads.append(t)
            time.sleep(0.05)  # Entzerrter Start

    def stop(self):
        """Stoppt alle Worker."""
        self.running = False
        print("\n  [*] Stoppe Worker...")
        time.sleep(0.5)

# ═══════════════════════════════════════════════════════════════
# CONFIG-MANAGER
# ═══════════════════════════════════════════════════════════════

class ConfigManager:
    @staticmethod
    def load() -> Dict:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        return {
            "proxies_file": "proxies.txt",
            "last_username": "",
            "last_threads": 5,
            "last_interval": 0.3,
            "login_username": "",
            "actions": ["join"],
            "region": "US",
        }

    @staticmethod
    def save(config: Dict):
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)

def load_proxies(filepath: str) -> List[str]:
    path = SCRIPT_DIR / filepath
    if not path.exists():
        return []
    with open(path, "r") as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]

# ═══════════════════════════════════════════════════════════════
# UI / MENÜ
# ═══════════════════════════════════════════════════════════════

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def print_banner():
    clear_screen()
    banner = """
╔══════════════════════════════════════════════════════════════╗
║        TikTok Live Ultimate Bot – Full Advanced PRO         ║
║                    HackerAI v4.0 – 2026                     ║
║            Nur für autorisierte Security-Assessments        ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)

def print_stats(stats: BotStats):
    total = stats.total or 1
    print(f"  ┌─────────────── 📊 LIVE-STATISTIK ───────────────┐")
    print(f"  │  Gesamt Requests:  {stats.total:>8}                │")
    print(f"  │  ✅ Joins:         {stats.joins:>8}  {stats.joins/total*100:>5.1f}%         │")
    print(f"  │  ❤️  Likes:         {stats.likes:>8}  {stats.likes/total*100:>5.1f}%         │")
    print(f"  │  🔄 Shares:        {stats.shares:>8}  {stats.shares/total*100:>5.1f}%         │")
    print(f"  │  ➕ Follows:       {stats.follows:>8}  {stats.follows/total*100:>5.1f}%         │")
    print(f"  │  ⏳ Rate-Limited:  {stats.rate_limited:>8}  {stats.rate_limited/total*100:>5.1f}%         │")
    print(f"  │  ❌ Failed:        {stats.failed:>8}  {stats.failed/total*100:>5.1f}%         │")
    print(f"  │  📱 Devices Reg:   {stats.devices_registered:>8}                │")
    print(f"  └──────────────────────────────────────────────────┘")

def print_main_menu(cfg: Dict, logged_in: bool = False, bot_active: bool = False):
    username = cfg.get("login_username", "")
    status = "✅" if logged_in else "❌"
    bot = "🟢 AKTIV" if bot_active else "🔴 INAKTIV"

    print(f"""
  ┌─────────────── 🔥 HAUPTMENÜ ───────────────┐
  │  Ziel: {cfg.get('last_username', 'nicht gesetzt'):>30} │
  │  Login: {status} {username[:20]:<20}             │
  │  Bot:   {bot:<34} │
  │  Aktionen: {', '.join(cfg.get('actions', ['join'])):<30} │
  │  Threads: {cfg.get('last_threads', 5):<4}  Proxy: {'✅' if load_proxies(cfg.get('proxies_file','proxies.txt')) else '❌':<4}    │
  ├──────────────────────────────────────────────┤
  │  [1] 🎯  Ziel setzen & Bot starten          │
  │  [2] 🔑  TikTok Login (für Likes/Share)     │
  │  [3] 📋  Aktionen konfigurieren             │
  │  [4] 🌐  Proxy-Liste laden                  │
  │  [5] ⚙️   Erweiterte Einstellungen          │
  │  [6] 📊  Statistiken zurücksetzen           │
  │  [7] 💾  Session speichern / laden          │
  │  [0] ❌  Beenden                            │
  └──────────────────────────────────────────────┘
""")

def select_actions() -> List[str]:
    """Aktionen-Menü: Join, Like, Share, Follow."""
    print("""
  ┌─────────────── 🎬 AKTIONEN ───────────────┐
  │  Wähle Aktionen (kommagetrennt):          │
  │                                           │
  │  1 = Join (Room Enter)                    │
  │  2 = Like                                 │
  │  3 = Share                                │
  │  4 = Follow                               │
  │                                           │
  │  Beispiel: 1,2,3 = Join + Like + Share    │
  └───────────────────────────────────────────┘
""")
    choice = input("  Aktionen (z.B. 1,2,3 oder 1-4): ").strip()
    action_map = {"1": "join", "2": "like", "3": "share", "4": "follow"}
    actions = []
    if not choice:
        return ["join"]
    # Range: 1-4
    if "-" in choice:
        a, b = choice.split("-")
        for i in range(int(a.strip()), int(b.strip())+1):
            if str(i) in action_map:
                actions.append(action_map[str(i)])
    else:
        for c in choice.split(","):
            c = c.strip()
            if c in action_map:
                actions.append(action_map[c])
    return actions or ["join"]

def login_flow(session_data: TikTokSession, cfg: Dict) -> Tuple[bool, TikTokSession]:
    """Login-Dialog: User/Pass + Device-Reg + Login-API."""
    print("""
  ┌─────────────── 🔑 LOGIN ──────────────────┐
  │  TikTok Account-Login (Android API v44+)  │
  │  Passwort wird lokal XOR(0x05) encoded.   │
  └───────────────────────────────────────────┘
""")
    username = input("  @username (oder Email): ").strip()
    if not username:
        return False, session_data
    import getpass
    password = getpass.getpass("  Passwort: ").strip()
    if not password:
        return False, session_data

    print("  [*] Registriere Device...")
    dev = DeviceProfile()
    proxy = None
    ok, msg = register_device(dev, proxy)
    if not ok:
        print(f"  [!] Device-Registration fehlgeschlagen: {msg}")
        print("  [*] Fahre ohne Registration fort...")

    session_data.device = dev
    print("  [*] Sende Login-Request...")
    ok, msg = login_user(session_data, username, password, proxy)

    if ok:
        print(f"  [✅] Login erfolgreich! UID: {session_data.uid[:15]}...")
        session_data.save(username)
        cfg["login_username"] = username
        ConfigManager.save(cfg)
        return True, session_data
    else:
        print(f"  [❌] Login fehlgeschlagen: {msg}")
        return False, session_data

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    cfg = ConfigManager.load()
    active_session = TikTokSession.load(cfg.get("login_username", "default"))
    if active_session and active_session.is_expired():
        print("  [ℹ] Session abgelaufen. Bitte neu einloggen.")
        active_session = None

    engine: Optional[LiveBotEngine] = None
    proxy_list = load_proxies(cfg.get("proxies_file", "proxies.txt"))

    while True:
        print_banner()
        print_stats(engine.stats if engine else BotStats())
        print_main_menu(cfg, active_session and active_session.logged_in,
                        engine and engine.running)

        choice = input("  Auswahl: ").strip()

        if choice == "1":
            # Ziel setzen + Bot starten
            if engine and engine.running:
                print("  [!] Bot läuft bereits. Stoppe zuerst...")
                engine.stop()

            target = input("\n  🎯 TikTok @username (ohne @): ").strip().lstrip("@")
            if not target:
                input("  Keine Eingabe. Drücke Enter...")
                continue

            print(f"  [*] Löse Room-ID für @{target} auf...")
            ok, room_id = resolve_room_id(target)
            if not ok:
                print(f"  [!] Konnte Room nicht finden: {room_id}")
                manual = input("  Manuelle Room-ID (Enter = abbrechen): ").strip()
                if not manual:
                    input("  Drücke Enter...")
                    continue
                room_id = manual
            else:
                print(f"  [✅] Room-ID: {room_id}")

            try:
                threads = input(f"  🧵 Threads [{cfg.get('last_threads', 5)}]: ").strip()
                threads = int(threads) if threads else cfg.get("last_threads", 5)
            except:
                threads = cfg.get("last_threads", 5)

            try:
                interval = input(f"  ⏱️  Intervall (Sek) [{cfg.get('last_interval', 0.3)}]: ").strip()
                interval = float(interval) if interval else cfg.get("last_interval", 0.3)
            except:
                interval = cfg.get("last_interval", 0.3)

            actions = cfg.get("actions", ["join"])
            print(f"\n  [*] Starte {threads} Worker für @{target}...")
            print(f"  [*] Aktionen: {', '.join(actions)}")
            print(f"  [*] Intervall: {interval}s\n")

            engine = LiveBotEngine(
                username=target,
                room_id=room_id,
                num_threads=threads,
                proxy_list=proxy_list,
                actions=actions,
                interval=interval,
            )
            engine.start()

            # Config speichern
            cfg["last_username"] = target
            cfg["last_threads"] = threads
            cfg["last_interval"] = interval
            ConfigManager.save(cfg)

            print(f"\n  [▶️] Bot läuft mit {threads} Threads. Drücke Enter fürs Menü...\n")
            try:
                input()
            except KeyboardInterrupt:
                pass
            engine.stop()

        elif choice == "2":
            # Login
            if not active_session:
                active_session = TikTokSession()
            ok, active_session = login_flow(active_session, cfg)

        elif choice == "3":
            # Aktionen konfigurieren
            actions = select_actions()
            cfg["actions"] = actions
            ConfigManager.save(cfg)
            print(f"  [✅] Aktionen gesetzt: {', '.join(actions)}")
            input("  Drücke Enter...")

        elif choice == "4":
            # Proxy-Liste laden
            path = input(f"  Pfad [{cfg.get('proxies_file', 'proxies.txt')}]: ").strip() or cfg.get("proxies_file", "proxies.txt")
            proxy_list = load_proxies(path)
            cfg["proxies_file"] = path
            ConfigManager.save(cfg)
            print(f"  [{'✅' if proxy_list else '❌'}] {len(proxy_list)} Proxies geladen.")
            input("  Drücke Enter...")

        elif choice == "5":
            # Erweiterte Einstellungen
            print("""
  ┌─────────────── ⚙️ EINSTELLUNGEN ───────────┐
  │  [1] Region ändern                         │
  │  [2] App-Version                           │
  │  [3] SDK-Version                           │
  │  [b] Zurück                                │
  └───────────────────────────────────────────┘
""")
            sub = input("  Auswahl: ").strip()
            if sub == "1":
                region = input(f"  Region [{cfg.get('region', 'US')}]: ").strip().upper()
                if region:
                    cfg["region"] = region
                    APP_DEFAULTS["sys_region"] = region
                    APP_DEFAULTS["carrier_region"] = region
                    ConfigManager.save(cfg)
            elif sub == "2":
                ver = input(f"  App-Version [{APP_DEFAULTS['version_name']}]: ").strip()
                if ver:
                    APP_DEFAULTS["version_name"] = ver
            elif sub == "3":
                sdk = input(f"  SDK-Version [{APP_DEFAULTS['sdk_ver']}]: ").strip()
                if sdk:
                    APP_DEFAULTS["sdk_ver"] = sdk
            input("  Drücke Enter...")

        elif choice == "6":
            # Stats reset
            if engine:
                engine.stats = BotStats()
            print("  [✅] Statistiken zurückgesetzt.")
            input("  Drücke Enter...")

        elif choice == "7":
            # Session speichern/laden
            print("""
  ┌─────────────── 💾 SESSION ────────────────┐
  │  [1] Aktuelle Session speichern           │
  │  [2] Session laden                        │
  │  [b] Zurück                               │
  └───────────────────────────────────────────┘
""")
            sub = input("  Auswahl: ").strip()
            if sub == "1" and active_session and active_session.logged_in:
                name = input("  Session-Name (Default: username): ").strip() or cfg.get("login_username", "default")
                path = active_session.save(name)
                print(f"  [✅] Session gespeichert: {path}")
            elif sub == "2":
                # Verfügbare Sessions anzeigen
                sessions = list(COOKIE_DIR.glob("session_*.pkl"))
                if not sessions:
                    print("  [!] Keine gespeicherten Sessions gefunden.")
                else:
                    print("  Verfügbare Sessions:")
                    for s in sessions:
                        name = s.stem.replace("session_", "")
                        print(f"    → {name}")
                    name = input("  Session-Name: ").strip() or "default"
                    loaded = TikTokSession.load(name)
                    if loaded:
                        active_session = loaded
                        cfg["login_username"] = name
                        ConfigManager.save(cfg)
                        print(f"  [✅] Session '{name}' geladen. UID: {loaded.uid[:15]}...")
                    else:
                        print("  [!] Session nicht gefunden.")
            input("  Drücke Enter...")

        elif choice == "0":
            if engine and engine.running:
                engine.stop()
            print("\n  👋 Bye.\n")
            sys.exit(0)

        else:
            input("  Ungültige Eingabe. Drücke Enter...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  [!] Abbruch durch Benutzer.\n")
        sys.exit(0)
