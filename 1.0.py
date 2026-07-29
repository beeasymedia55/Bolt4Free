#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║       TikTok Live Stream Ultimate Bot – Full Advanced       ║
║                   HackerAI v5.0 – PRO EDITION               ║
║        Nur für autorisierte Penetration-Tests & Research    ║
╚══════════════════════════════════════════════════════════════╝

Features:
  ✅ Device-Registration     → log.tiktokv.com/service/2/device_register/
  ✅ Login Flow              → passport/user/login/ (XOR 0x05 encoded)
  ✅ Cookie Persistence      → pickle save/load mit Auto-Refresh
  ✅ Room Enter              → webcast.tiktokv.com/webcast/room/enter/
  ✅ Like (Digg)             → aweme/v1/commit/item/digg/
  ✅ Share                   → aweme/v1/commit/item/share/
  ✅ Follow                  → aweme/v1/commit/follow/
  ✅ X-Gorgon/X-Argus/X-Ladon/X-Khronos Signatur
  ✅ Multi-Threading         → frei konfigurierbar
  ✅ Proxy-Rotation          → HTTP/HTTPS/SOCKS5
  ✅ Fingerprint-Jitter      → 12 Device-Profile + Randomisierung
  ✅ Config-System           → save/load per JSON
  ✅ Dashboard               → Live-Statistiken im Menü
  ✅ Account Manager         → Lädt accounts.txt / sessions.txt
  ✅ Session Validator       → Prüft Gültigkeit per TikTok-API
  ✅ Account Pool            → Rotation + Auto-Refresh

Install:
    pip install tiktok-signer requests pysocks
"""

import os, sys, json, time, random, string, threading, pickle
import re, hashlib, struct
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Tuple, Union
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("[!] Fehlende Abhängigkeit: requests")
    print("    pip install requests")
    sys.exit(1)

try:
    from tiktok_signer import TikTokSigner
except ImportError:
    print("[!] Fehlende Abhängigkeit: tiktok-signer")
    print("    pip install tiktok-signer")
    sys.exit(1)

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
class TikTokAccount:
    """
    Repräsentiert einen TikTok-Account aus account.txt / sessions.txt.

    Unterstützte Formate (account.txt / accounts.txt):
      - username:password
      - username:password:sessionid
      - username:password:sessionid:ttwid

    session.txt / sessions.txt:
      - sessionid
      - username:sessionid
      - username:sessionid:ttwid
      - Netscape-Cookie-Format (mit sessionid-Detektion)
    """
    username: str = ""
    password: str = ""
    sessionid: str = ""
    ttwid: str = ""
    sid_tt: str = ""
    sessionid_ss: str = ""
    uid: str = ""
    sec_uid: str = ""
    cookies: Dict[str, str] = field(default_factory=dict)
    valid: bool = False
    validated_at: str = ""
    error: str = ""
    used_count: int = 0
    proxy_locked: str = ""
    source_file: str = ""

    @property
    def identifier(self) -> str:
        return self.username or self.sessionid[:16] + "..." if self.sessionid else "unknown"

    def to_short_str(self) -> str:
        if self.username:
            return self.username
        if self.sessionid:
            return f"sid:{self.sessionid[:12]}..."
        return "unknown"

    def cookie_header(self) -> str:
        """Baut einen vollständigen Cookie-Header aus allen verfügbaren Werten."""
        parts = []
        if self.sessionid:
            parts.append(f"sessionid={self.sessionid}")
        if self.ttwid:
            parts.append(f"ttwid={self.ttwid}")
        if self.sid_tt:
            parts.append(f"sid_tt={self.sid_tt}")
        if self.sessionid_ss:
            parts.append(f"sessionid_ss={self.sessionid_ss}")
        # Zusätzliche Cookies aus Dict
        for k, v in self.cookies.items():
            if k not in ["sessionid", "ttwid", "sid_tt", "sessionid_ss"]:
                parts.append(f"{k}={v}")
        return "; ".join(parts)


# ═══════════════════════════════════════════════════════════════
# ACCOUNT-LOADER (account.txt / accounts.txt / session.txt / sessions.txt)
# ═══════════════════════════════════════════════════════════════

def detect_account_files() -> List[Path]:
    """
    Sucht nach account.txt, accounts.txt, session.txt, sessions.txt
    im Skript-Verzeichnis. Gibt alle gefundenen zurück.
    """
    candidates = [
        SCRIPT_DIR / "account.txt",
        SCRIPT_DIR / "accounts.txt",
        SCRIPT_DIR / "session.txt",
        SCRIPT_DIR / "sessions.txt",
    ]
    found = []
    for p in candidates:
        if p.exists():
            found.append(p)
    return found


def parse_account_line(line: str, source_file: str) -> Optional[TikTokAccount]:
    """
    Parst eine Zeile aus account.txt / accounts.txt.

    Formate:
      username:password
      username:password:sessionid
      username:password:sessionid:ttwid
      username:password:sessionid:ttwid:cookie_json

    Oder auch:
      sessionid  (nur sessionid)
      username:sessionid
    """
    line = line.strip()
    if not line or line.startswith("#") or line.startswith("//"):
        return None

    parts = line.split(":", 4)  # max 5 Teile

    acc = TikTokAccount(source_file=source_file)

    # Fall: reine sessionid (kein username)
    if len(parts) == 1 and len(parts[0]) > 20:
        acc.sessionid = parts[0]
        return acc

    # Fall: username:sessionid
    if len(parts) == 2:
        # Prüfen ob Teil2 eine sessionid ist (lang + alphanumerisch)
        if len(parts[1]) > 20 and not parts[1].startswith("http"):
            acc.username = parts[0]
            acc.sessionid = parts[1]
            return acc
        # Sonst: username:password
        acc.username = parts[0]
        acc.password = parts[1]
        return acc

    # Fall: username:password:sessionid
    if len(parts) >= 3:
        acc.username = parts[0]
        acc.password = parts[1]
        acc.sessionid = parts[2]
        if len(parts) >= 4:
            acc.ttwid = parts[3]
        if len(parts) >= 5:
            # Versuche JSON-Cookies zu parsen
            try:
                extra = json.loads(parts[4])
                if isinstance(extra, dict):
                    for k, v in extra.items():
                        setattr(acc, k, v) if hasattr(acc, k) else acc.cookies.update({k: v})
            except:
                pass
        return acc

    return None


def parse_session_line(line: str, source_file: str) -> Optional[TikTokAccount]:
    """
    Parst eine Zeile aus session.txt / sessions.txt.

    Formate:
      sessionid
      username:sessionid
      username:sessionid:ttwid
      # Netscape Cookie Format:
      # .tiktok.com TRUE / TRUE <expires> sessionid <value>
    """
    line = line.strip()
    if not line or line.startswith("#") or line.startswith("//"):
        return None

    # Netscape Cookie-Format erkennen: beginnt mit Domain
    if line.startswith(".") or line.startswith("http"):
        # Netscape: .tiktok.com TRUE / TRUE <expires> <name> <value>
        parts = line.split()
        if len(parts) >= 6:
            name = parts[4]
            value = parts[5]
            acc = TikTokAccount(source_file=source_file)
            if name == "sessionid":
                acc.sessionid = value
            elif name == "ttwid":
                acc.ttwid = value
            elif name == "sid_tt":
                acc.sid_tt = value
            elif name == "sessionid_ss":
                acc.sessionid_ss = value
            else:
                acc.cookies[name] = value
            return acc
        return None

    # Normale Formate
    parts = line.split(":", 2)

    if len(parts) == 1:
        # Nur sessionid
        if len(parts[0]) > 20:
            return TikTokAccount(sessionid=parts[0], source_file=source_file)
        return None

    if len(parts) == 2:
        # username:sessionid
        return TikTokAccount(username=parts[0], sessionid=parts[1], source_file=source_file)

    if len(parts) >= 3:
        # username:sessionid:ttwid
        return TikTokAccount(username=parts[0], sessionid=parts[1], ttwid=parts[2], source_file=source_file)

    return None


def load_accounts_from_file(filepath: Path) -> List[TikTokAccount]:
    """
    Lädt Accounts aus einer Datei.
    Erkennt automatisch ob account.txt (mit Passwort) oder session.txt (nur Session).
    """
    accounts = []
    is_session_file = filepath.name.lower() in ["session.txt", "sessions.txt"]
    parser = parse_session_line if is_session_file else parse_account_line

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            acc = parser(line, filepath.name)
            if acc:
                accounts.append(acc)

    return accounts


def load_all_accounts() -> List[TikTokAccount]:
    """Lädt Accounts aus ALLEN existing account/session-Dateien."""
    all_accounts = []
    files = detect_account_files()
    for f in files:
        accs = load_accounts_from_file(f)
        all_accounts.extend(accs)
    return all_accounts


# ═══════════════════════════════════════════════════════════════
# ACCOUNT-VALIDATOR
# ═══════════════════════════════════════════════════════════════

def validate_session_via_api(account: TikTokAccount,
                              proxy: Optional[str] = None) -> Tuple[bool, str]:
    """
    Prüft ob eine TikTok-Session gültig ist, indem die User-Info-API
    aufgerufen wird. Wenn die Session lebt, kommt uid + sec_uid zurück.

    GET https://www.tiktok.com/api/user/detail/?uniqueId=...
    mit Cookie: sessionid=xxx
    """
    if not account.sessionid:
        return False, "keine_sessionid"

    http = create_session(proxy)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Cookie": account.cookie_header(),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.tiktok.com/",
        "Origin": "https://www.tiktok.com",
    }

    # Methode 1: User-Detail-API mit logged-in Check
    try:
        url = "https://www.tiktok.com/api/user/detail/"
        resp = http.get(url, headers=headers, params={"uniqueId": "tiktok"}, timeout=10)

        if resp.status_code == 200:
            data = resp.json()
            # Wenn wir logged-in sind, kommt userData zurück
            if data.get("user") or data.get("userInfo") or not data.get("statusCode"):
                # Extrahiere uid/sec_uid aus response
                cookies = http.cookies.get_dict()
                if "sessionid" in cookies:
                    account.cookies["sessionid"] = cookies["sessionid"]
                if "ttwid" in cookies:
                    account.ttwid = cookies.get("ttwid", account.ttwid)
                if "sid_tt" in cookies:
                    account.sid_tt = cookies.get("sid_tt", account.sid_tt)

                # uid aus Response extrahieren (verschiedene Pfade)
                user = data.get("user", {}) or data.get("userInfo", {}).get("user", {})
                if user:
                    account.uid = user.get("id", "") or user.get("uid", "")
                    account.sec_uid = user.get("secUid", "") or user.get("sec_uid", "")

                account.valid = True
                account.validated_at = datetime.now().isoformat()
                account.error = ""

                # Versuche Username aus API zu holen falls nicht vorhanden
                if not account.username and user:
                    account.username = user.get("uniqueId", "") or user.get("nickname", "")

                return True, f"gültig | uid:{account.uid[:12] if account.uid else 'unbekannt'}"

        # Wenn StatusCode == 10204 oder ähnlich → Session invalid
        if resp.status_code == 200:
            data = resp.json()
            if data.get("statusCode") == 10204 or data.get("statusCode") == 2:
                account.valid = False
                account.error = f"session_invalid: {data.get('statusCode')}"
                return False, f"session_invalid: {data.get('statusCode')}"

        # Rate-Limited
        if resp.status_code == 429:
            return False, "rate_limited"

        # 403/401 = session invalid
        if resp.status_code in (401, 403):
            account.valid = False
            account.error = f"http_{resp.status_code}"
            return False, f"session_invalid (http {resp.status_code})"

    except Exception as e:
        return False, f"error: {e}"

    # Methode 2: Fallback – Profil-Seite aufrufen
    try:
        url = "https://www.tiktok.com/"
        resp = http.get(url, headers=headers, timeout=10)
        cookies = http.cookies.get_dict()

        # Wenn sessionid in den Response-Cookies auftaucht → Session lebt
        if "sessionid" in cookies and cookies["sessionid"] == account.sessionid:
            account.valid = True
            account.validated_at = datetime.now().isoformat()
            account.error = ""
            # ttwid merken
            if "ttwid" in cookies:
                account.ttwid = cookies["ttwid"]
            return True, "gültig (cookie_bestätigt)"
    except:
        pass

    account.valid = False
    account.error = "validation_fehlgeschlagen"
    return False, "validation_failed"


def validate_all_accounts(accounts: List[TikTokAccount],
                           proxy_list: Optional[List[str]] = None,
                           max_workers: int = 10) -> Tuple[List[TikTokAccount], List[TikTokAccount]]:
    """
    Validiert alle Accounts parallel.
    Gibt (gültige, ungültige) zurück.
    """
    if not accounts:
        return [], []

    valid_accounts = []
    invalid_accounts = []
    lock = threading.Lock()

    def validate_one(acc: TikTokAccount):
        proxy = random.choice(proxy_list) if proxy_list else None
        ok, msg = validate_session_via_api(acc, proxy)
        with lock:
            if ok:
                valid_accounts.append(acc)
            else:
                acc.error = msg
                invalid_accounts.append(acc)

    print(f"  [*] Validiere {len(accounts)} Accounts mit {min(max_workers, len(accounts))} Threads...")

    threads = []
    for i, acc in enumerate(accounts):
        t = threading.Thread(target=validate_one, args=(acc,), daemon=True)
        t.start()
        threads.append(t)
        time.sleep(0.1)  # Entzerren
        if (i + 1) >= max_workers:
            # Warte bis einer fertig ist
            for th in threads:
                th.join(timeout=30)
            threads = [t for t in threads if t.is_alive()]

    for t in threads:
        t.join(timeout=30)

    return valid_accounts, invalid_accounts


# ═══════════════════════════════════════════════════════════════
# ACCOUNT-POOL
# ═══════════════════════════════════════════════════════════════

class AccountPool:
    """Thread-sicherer Pool von TikTok-Accounts mit Rotation."""

    def __init__(self, accounts: Optional[List[TikTokAccount]] = None):
        self._accounts: List[TikTokAccount] = accounts or []
        self._valid_cache: List[TikTokAccount] = []
        self._idx = 0
        self._lock = threading.Lock()
        self._refreshed_at = None
        self._needs_refresh = threading.Event()

    @property
    def total(self) -> int:
        return len(self._accounts)

    @property
    def valid_count(self) -> int:
        return len([a for a in self._accounts if a.valid])

    @property
    def invalid_count(self) -> int:
        return len([a for a in self._accounts if not a.valid])

    def add(self, account: TikTokAccount):
        with self._lock:
            self._accounts.append(account)

    def add_many(self, accounts: List[TikTokAccount]):
        with self._lock:
            self._accounts.extend(accounts)

    def get_next(self) -> Optional[TikTokAccount]:
        """Holt den nächsten validen Account (Round-Robin)."""
        with self._lock:
            valid = [a for a in self._accounts if a.valid]
            if not valid:
                return None
            if self._idx >= len(valid):
                self._idx = 0
            acc = valid[self._idx]
            self._idx += 1
            acc.used_count += 1
            return acc

    def get_random(self) -> Optional[TikTokAccount]:
        """Holt einen zufälligen validen Account."""
        with self._lock:
            valid = [a for a in self._accounts if a.valid]
            if not valid:
                return None
            acc = random.choice(valid)
            acc.used_count += 1
            return acc

    def remove_invalid(self):
        """Entfernt alle als invalid markierten Accounts."""
        with self._lock:
            self._accounts = [a for a in self._accounts if a.valid]

    def mark_invalid(self, account: TikTokAccount):
        """Markiert einen Account als ungültig."""
        with self._lock:
            for a in self._accounts:
                if a is account or (a.sessionid and account.sessionid and a.sessionid == account.sessionid):
                    a.valid = False
                    a.error = "marked_invalid_by_worker"
                    break

    def save_valid_to_file(self, filepath: Path = SCRIPT_DIR / "valid_accounts.txt"):
        """Speichert alle validen Accounts im Format username:sessionid:ttwid."""
        with self._lock:
            valid = [a for a in self._accounts if a.valid]
        with open(filepath, "w") as f:
            for a in valid:
                line = f"{a.username}:{a.sessionid}:{a.ttwid}" if a.ttwid else f"{a.username}:{a.sessionid}"
                f.write(line + "\n")
        print(f"  [✅] {len(valid)} valide Accounts gespeichert → {filepath}")

    def refresh_in_background(self, proxy_list: Optional[List[str]] = None, interval: int = 300):
        """
        Startet einen Hintergrund-Thread der regelmäßig die Gültigkeit prüft.
        interval = Sekunden zwischen Prüfungen.
        """
        def _refresher():
            while True:
                time.sleep(interval)
                if not self._accounts:
                    continue
                # Stichprobenartig 5 zufällige Accounts validieren
                with self._lock:
                    sample = random.sample(self._accounts, min(5, len(self._accounts)))
                for acc in sample:
                    proxy = random.choice(proxy_list) if proxy_list else None
                    ok, _ = validate_session_via_api(acc, proxy)
                    with self._lock:
                        acc.valid = ok
                        if not ok:
                            acc.error = "refresh_failed"
                self._refreshed_at = datetime.now().isoformat()

        t = threading.Thread(target=_refresher, daemon=True)
        t.start()

    def get_stats(self) -> Dict:
        with self._lock:
            valid = [a for a in self._accounts if a.valid]
            invalid = [a for a in self._accounts if not a.valid]
            total_uses = sum(a.used_count for a in self._accounts)
        return {
            "total": len(self._accounts),
            "valid": len(valid),
            "invalid": len(invalid),
            "total_uses": total_uses,
            "refreshed_at": self._refreshed_at or "nie",
        }


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
    session.headers.update({
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    })
    return session

def get_ts() -> str:
    return str(int(time.time()))

def build_query_params(profile: DeviceProfile, extra: Optional[Dict] = None) -> Dict[str, str]:
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

def sign_request(params_dict: Dict, session_data=None,
                 body: Optional[Dict] = None) -> Dict[str, str]:
    qs = "&".join(f"{k}={v}" for k, v in sorted(params_dict.items()))
    cookie_str = ""
    if session_data and hasattr(session_data, 'cookie_header'):
        cookie_str = session_data.cookie_header()
    elif session_data and isinstance(session_data, dict):
        cookie_str = "; ".join(f"{k}={v}" for k, v in session_data.items())

    try:
        auth_headers = TikTokSigner.generate_headers(
            params=qs,
            data=body,
            cookie=cookie_str or None,
            version_name=APP_DEFAULTS["version_name"],
            version_code=APP_DEFAULTS["version_code"],
            sdk_ver=APP_DEFAULTS["sdk_ver"],
            sdk_ver_code=APP_DEFAULTS["sdk_ver_code"],
        )
        return auth_headers
    except Exception:
        return {}

# ═══════════════════════════════════════════════════════════════
# API-FUNKTIONEN
# ═══════════════════════════════════════════════════════════════

def register_device(profile: DeviceProfile, proxy: Optional[str] = None) -> Tuple[bool, str]:
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


def login_user(session_data, username: str, password: str,
               proxy: Optional[str] = None):
    """TikTok Login – XOR(0x05) encoded username+password."""
    http = create_session(proxy)

    enc_username = xor_encode_username(username)
    enc_password = xor_encode_password(password)

    body = {
        "username": enc_username,
        "password": enc_password,
        "mix_mode": "1",
        "multi_login": "1",
        "account_sdk_source": "app",
    }

    dev = session_data.device if hasattr(session_data, 'device') else session_data
    params = build_query_params(dev, {"type": "login", "account_sdk_source": "app"})

    auth_headers = sign_request(params, body=body)
    headers = build_headers(dev, {"Host": "api16.tiktokv.com"})
    headers.update(auth_headers)
    headers["X-SS-REQ-TICKET"] = str(int(time.time() * 1000000))

    qs = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    url = f"https://api16.tiktokv.com/passport/user/login/?{qs}"

    try:
        resp = http.post(url, headers=headers, data=body, timeout=15)
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

                if "sessionid" not in session_data.cookies and "data" in data:
                    if "sessionid" in data["data"]:
                        session_data.cookies["sessionid"] = data["data"]["sessionid"]
                    if "sessionid_ss" in data["data"]:
                        session_data.cookies["sessionid_ss"] = data["data"]["sessionid_ss"]
                return True, "logged_in"
            return False, f"login_fail: {data.get('description', 'unknown')}"
        return False, f"http_{resp.status_code}"
    except Exception as e:
        return False, str(e)


def room_enter(account: TikTokAccount, room_id: str, profile: DeviceProfile,
               proxy: Optional[str] = None) -> Tuple[bool, Dict]:
    http = create_session(proxy)

    params = build_query_params(profile, {
        "room_id": room_id,
        "live_id": "1",
        "type": "enter",
    })

    auth_headers = sign_request(params, account)
    headers = build_headers(profile, {"Host": "webcast.tiktokv.com"})
    headers.update(auth_headers)
    cookie_str = account.cookie_header()
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


def send_like(account: TikTokAccount, aweme_id: str, profile: DeviceProfile,
              proxy: Optional[str] = None) -> Tuple[bool, str]:
    http = create_session(proxy)

    params = build_query_params(profile, {
        "aweme_id": aweme_id,
        "type": "1",
        "action": "1",
    })

    auth_headers = sign_request(params, account)
    headers = build_headers(profile, {"Host": "api16.tiktokv.com"})
    headers.update(auth_headers)
    cookie_str = account.cookie_header()
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


def send_share(account: TikTokAccount, aweme_id: str, profile: DeviceProfile,
               proxy: Optional[str] = None) -> Tuple[bool, str]:
    http = create_session(proxy)

    params = build_query_params(profile, {
        "aweme_id": aweme_id,
        "share_type": "1",
        "source": "profile",
    })

    auth_headers = sign_request(params, account)
    headers = build_headers(profile, {"Host": "api16.tiktokv.com"})
    headers.update(auth_headers)
    cookie_str = account.cookie_header()
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


def send_follow(account: TikTokAccount, sec_user_id: str, profile: DeviceProfile,
                proxy: Optional[str] = None) -> Tuple[bool, str]:
    http = create_session(proxy)

    params = build_query_params(profile, {
        "sec_user_id": sec_user_id,
        "type": "1",
    })

    auth_headers = sign_request(params, account)
    headers = build_headers(profile, {"Host": "api16.tiktokv.com"})
    headers.update(auth_headers)
    cookie_str = account.cookie_header()
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


def xor_encode_password(password: str, xor_key: int = 0x05) -> str:
    result = []
    for ch in password:
        xored = ord(ch) ^ xor_key
        result.append(f"{xored:02x}")
    return "".join(result)

def xor_encode_username(username: str, xor_key: int = 0x05) -> str:
    return xor_encode_password(username, xor_key)


def resolve_room_id(username: str, proxy: Optional[str] = None) -> Tuple[bool, str]:
    http = create_session(proxy)

    # Versuch 1: Web-HTML
    try:
        url = f"https://www.tiktok.com/@{username}/live"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
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

    # Versuch 2: API
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
    accounts_used: int = 0
    session_errors: int = 0

    @property
    def total(self):
        return self.joins + self.likes + self.shares + self.follows + self.failed + self.rate_limited + self.invalid


class LiveBotEngine:
    """Haupt-Engine mit Account-Pool-Integration."""

    def __init__(self, username: str, room_id: str, num_threads: int = 5,
                 proxy_list: Optional[List[str]] = None,
                 actions: Optional[List[str]] = None,
                 interval: float = 0.3,
                 account_pool: Optional[AccountPool] = None):
        self.target_username = username
        self.room_id = room_id
        self.num_threads = num_threads
        self.proxy_list = proxy_list or []
        self.actions = actions or ["join"]
        self.interval = interval
        self.account_pool = account_pool
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
        dev = DeviceProfile()
        ok, msg = register_device(dev, proxy)
        with self._lock:
            self.stats.devices_registered += 1
        return dev

    def _execute_actions(self, worker_id: int, dev: DeviceProfile, proxy: Optional[str],
                         account: Optional[TikTokAccount] = None):
        now = datetime.now().strftime("%H:%M:%S")
        acc_name = account.to_short_str() if account else "no_account"
        prefix = f"[{now}] [W#{worker_id:02d}] {dev.device_id[:10]}... ({acc_name})"

        # 1. Room Enter
        if "join" in self.actions:
            ok, data = room_enter(account if account else TikTokAccount(), self.room_id, dev, proxy)
            if ok:
                with self._lock:
                    self.stats.joins += 1
                print(f"  {prefix} ✅ JOIN  | {proxy or 'direct'}")
            else:
                err = str(data.get("error", data))[:50]
                if "429" in err or "rate" in err.lower():
                    with self._lock:
                        self.stats.rate_limited += 1
                    print(f"  {prefix} ⏳ RATE  | {err}")
                elif "session" in err.lower() and account:
                    with self._lock:
                        self.stats.session_errors += 1
                    print(f"  {prefix} 🔴 SESS  | {err}")
                    if self.account_pool:
                        self.account_pool.mark_invalid(account)
                else:
                    with self._lock:
                        self.stats.failed += 1
                    print(f"  {prefix} ❌ FAIL  | {err}")

        # 2. Like
        if "like" in self.actions and account and account.valid:
            ok, msg = send_like(account, self.room_id, dev, proxy)
            if ok:
                with self._lock:
                    self.stats.likes += 1
                print(f"  {prefix} ❤️ LIKE  | {proxy or 'direct'}")
            else:
                with self._lock:
                    self.stats.failed += 1

        # 3. Share
        if "share" in self.actions and account and account.valid:
            ok, msg = send_share(account, self.room_id, dev, proxy)
            if ok:
                with self._lock:
                    self.stats.shares += 1
                print(f"  {prefix} 🔄 SHARE | {proxy or 'direct'}")
            else:
                with self._lock:
                    self.stats.failed += 1

        # 4. Follow
        if "follow" in self.actions and account and account.valid and self._sec_uid:
            if random.random() < 0.3:
                ok, msg = send_follow(account, self._sec_uid, dev, proxy)
                if ok:
                    with self._lock:
                        self.stats.follows += 1
                    print(f"  {prefix} ➕ FOLLOW| {proxy or 'direct'}")
                else:
                    with self._lock:
                        self.stats.failed += 1

    def worker_loop(self, worker_id: int):
        while self.running:
            proxy = self._get_proxy()

            # Account aus Pool holen (falls vorhanden)
            account = None
            if self.account_pool:
                account = self.account_pool.get_random()
                if account:
                    with self._lock:
                        self.stats.accounts_used += 1

            # Device registrieren
            dev = self._create_device(proxy)
            if not dev.registered:
                time.sleep(random.uniform(0.5, 2))
                continue

            # Aktionen ausführen
            self._execute_actions(worker_id, dev, proxy, account)

            # Jitter
            jitter = random.uniform(self.interval * 0.3, self.interval * 2.5)
            time.sleep(jitter)

    def start(self):
        self.running = True

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
            time.sleep(0.05)

    def stop(self):
        self.running = False
        print("\n  [*] Stoppe Worker...")


# ═══════════════════════════════════════════════════════════════
# ACCOUNT-MANAGER-MENÜ
# ═══════════════════════════════════════════════════════════════

class AccountManager:
    """
    Account-Manager für Menü-Operationen:
    - Laden aus Dateien
    - Validieren
    - Pool verwalten
    - Speichern
    """

    def __init__(self):
        self.pool = AccountPool()

    def load_from_files(self) -> int:
        """Lädt alle Accounts aus account.txt / session.txt etc."""
        accounts = load_all_accounts()
        if accounts:
            self.pool.add_many(accounts)
        return len(accounts)

    def validate_all(self, proxy_list: Optional[List[str]] = None) -> Tuple[int, int]:
        """Validiert alle ungültigen Accounts im Pool."""
        to_check = [a for a in self.pool._accounts if not a.valid]
        if not to_check:
            return 0, 0
        valid, invalid = validate_all_accounts(to_check, proxy_list)
        return len(valid), len(invalid)

    def validate_new(self, proxy_list: Optional[List[str]] = None) -> Tuple[int, int]:
        """Validiert nur Accounts, die noch nie validiert wurden."""
        to_check = [a for a in self.pool._accounts if not a.validated_at]
        if not to_check:
            return 0, 0
        valid, invalid = validate_all_accounts(to_check, proxy_list)
        return len(valid), len(invalid)

    def print_status(self):
        stats = self.pool.get_stats()
        print(f"""
  ┌─────────────── 👥 ACCOUNT-POOL ───────────┐
  │  Gesamt:      {stats['total']:>8}                     │
  │  ✅ Valide:    {stats['valid']:>8}                     │
  │  ❌ Invalide:  {stats['invalid']:>8}                     │
  │  🔄 Genutzt:   {stats['total_uses']:>8}x                    │
  │  🔄 Refresh:   {stats['refreshed_at']:<22} │
  └──────────────────────────────────────────────┘
""")

    def save_valid(self):
        self.pool.save_valid_to_file()


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
            "auto_validate": True,
            "accounts_file": "accounts.txt",
            "sessions_file": "sessions.txt",
            "refresh_interval": 300,
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
║                    HackerAI v5.0 – 2026                     ║
║            Nur für autorisierte Security-Assessments        ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)

def print_stats(stats: BotStats, pool_stats: Optional[Dict] = None):
    total = stats.total or 1
    print(f"  ┌─────────────── 📊 LIVE-STATISTIK ───────────────┐")
    print(f"  │  Gesamt Requests:     {stats.total:>8}              │")
    print(f"  │  ✅ Joins:             {stats.joins:>8}  {stats.joins/total*100:>5.1f}%       │")
    print(f"  │  ❤️  Likes:             {stats.likes:>8}  {stats.likes/total*100:>5.1f}%       │")
    print(f"  │  🔄 Shares:            {stats.shares:>8}  {stats.shares/total*100:>5.1f}%       │")
    print(f"  │  ➕ Follows:           {stats.follows:>8}  {stats.follows/total*100:>5.1f}%       │")
    print(f"  │  ⏳ Rate-Limited:      {stats.rate_limited:>8}  {stats.rate_limited/total*100:>5.1f}%       │")
    print(f"  │  🔴 Session-Fehler:    {stats.session_errors:>8}              │")
    print(f"  │  ❌ Failed:            {stats.failed:>8}  {stats.failed/total*100:>5.1f}%       │")
    print(f"  │  📱 Devices:           {stats.devices_registered:>8}              │")
    print(f"  │  👥 Accounts genutzt:  {stats.accounts_used:>8}              │")
    if pool_stats:
        print(f"  │  Pool: {pool_stats['valid']}/{pool_stats['total']} valid ({pool_stats['invalid']} invalid) │")
    print(f"  └──────────────────────────────────────────────────┘")

def print_main_menu(cfg: Dict, logged_in: bool = False, bot_active: bool = False,
                    pool_accounts: int = 0, pool_valid: int = 0):
    username = cfg.get("login_username", "")
    status = "✅" if logged_in else "❌"
    bot = "🟢 AKTIV" if bot_active else "🔴 INAKTIV"

    print(f"""
  ┌────────────────── 🔥 HAUPTMENÜ ──────────────────┐
  │  Ziel:   {cfg.get('last_username', 'nicht gesetzt'):<34} │
  │  Login:  {status} {username[:20]:<20}                    │
  │  Bot:    {bot:<38} │
  │  Pool:   👥 {pool_valid}/{pool_accounts} Accounts valid                         │
  │  Aktionen: {', '.join(cfg.get('actions', ['join'])):<30} │
  │  Threads: {cfg.get('last_threads', 5):<4}  Proxy: {'✅' if load_proxies(cfg.get('proxies_file','proxies.txt')) else '❌':<4}     │
  ├──────────────────────────────────────────────────┤
  │  [1]  🎯  Ziel setzen & Bot starten             │
  │  [2]  👥  Account-Manager (accounts.txt...)     │
  │  [3]  🔑  TikTok Login (neuer Account)          │
  │  [4]  📋  Aktionen konfigurieren                │
  │  [5]  🌐  Proxy-Liste laden                     │
  │  [6]  ⚙️   Erweiterte Einstellungen             │
  │  [7]  📊  Statistiken zurücksetzen              │
  │  [8]  💾  Session speichern / laden             │
  │  [0]  ❌  Beenden                               │
  └──────────────────────────────────────────────────┘
""")

def account_manager_menu(acc_mgr: AccountManager, cfg: Dict) -> AccountManager:
    """Untermenü für Account-Verwaltung."""
    while True:
        clear_screen()
        print_banner()
        acc_mgr.print_status()
        print("""
  ┌─────────────── 👥 ACCOUNT-MANAGER ───────────┐
  │  [1] Accounts aus Dateien laden             │
  │  [2] Alle Accounts validieren               │
  │  [3] Nur neue Accounts validieren           │
  │  [4] Invalide Accounts entfernen            │
  │  [5] Valide Accounts speichern              │
  │  [6] Status aktualisieren                   │
  │  [7] Auto-Refresh starten                   │
  │  [b] Zurück zum Hauptmenü                   │
  └─────────────────────────────────────────────┘
""")
        choice = input("  Auswahl: ").strip()

        if choice == "1":
            count = acc_mgr.load_from_files()
            print(f"  [{'✅' if count else '❌'}] {count} Accounts geladen.")
            input("  Drücke Enter...")

        elif choice == "2":
            proxy_list = load_proxies(cfg.get("proxies_file", "proxies.txt"))
            valid, invalid = acc_mgr.validate_all(proxy_list if proxy_list else None)
            print(f"  [✅] {valid} valid, [❌] {invalid} invalid")
            input("  Drücke Enter...")

        elif choice == "3":
            proxy_list = load_proxies(cfg.get("proxies_file", "proxies.txt"))
            valid, invalid = acc_mgr.validate_new(proxy_list if proxy_list else None)
            print(f"  [✅] {valid} valid, [❌] {invalid} invalid")
            input("  Drücke Enter...")

        elif choice == "4":
            before = acc_mgr.pool.total
            acc_mgr.pool.remove_invalid()
            removed = before - acc_mgr.pool.total
            print(f"  [🗑️] {removed} invalide Accounts entfernt.")
            input("  Drücke Enter...")

        elif choice == "5":
            acc_mgr.save_valid()
            input("  Drücke Enter...")

        elif choice == "6":
            continue  # Refresh-Anzeige

        elif choice == "7":
            proxy_list = load_proxies(cfg.get("proxies_file", "proxies.txt"))
            interval = cfg.get("refresh_interval", 300)
            acc_mgr.pool.refresh_in_background(proxy_list if proxy_list else None, interval)
            print(f"  [🔄] Auto-Refresh gestartet (alle {interval}s).")
            input("  Drücke Enter...")

        elif choice in ("b", "B", ""):
            break

        else:
            input("  Ungültige Eingabe. Drücke Enter...")

    return acc_mgr


def select_actions() -> List[str]:
    print("""
  ┌─────────────── 🎬 AKTIONEN ───────────────┐
  │  Wähle Aktionen (kommagetrennt):          │
  │  1 = Join (Room Enter)                    │
  │  2 = Like                                 │
  │  3 = Share                                │
  │  4 = Follow                               │
  │  Beispiel: 1,2,3 = Join + Like + Share    │
  └───────────────────────────────────────────┘
""")
    choice = input("  Aktionen (z.B. 1,2,3): ").strip()
    action_map = {"1": "join", "2": "like", "3": "share", "4": "follow"}
    actions = []
    if not choice:
        return ["join"]
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


def login_flow(session_data, cfg: Dict) -> Tuple[bool, any]:
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
    ok, msg = register_device(dev, None)
    if not ok:
        print(f"  [!] Device-Registration fehlgeschlagen: {msg}")

    session_data.device = dev if hasattr(session_data, 'device') else dev
    print("  [*] Sende Login-Request...")
    ok, msg = login_user(session_data, username, password, None)

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

@dataclass
class TikTokSession:
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
            return datetime.now() > exp - timedelta(hours=1)
        except:
            return True

    def save(self, name: str = "default"):
        path = COOKIE_DIR / f"session_{name}.pkl"
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
        return cls(
            device=DeviceProfile.from_dict(data.get("device", {})),
            cookies=data.get("cookies", {}),
            uid=data.get("uid", ""),
            session_key=data.get("session_key", ""),
            sec_uid=data.get("sec_uid", ""),
            logged_in=data.get("logged_in", False),
            login_time=data.get("login_time", ""),
            expires_at=data.get("expires_at", ""),
        )


def main():
    cfg = ConfigManager.load()
    active_session = TikTokSession.load(cfg.get("login_username", "default"))
    if active_session and active_session.is_expired():
        print("  [ℹ] Session abgelaufen. Bitte neu einloggen.")
        active_session = None

    acc_mgr = AccountManager()

    # Auto-Load Accounts aus Dateien
    found_files = detect_account_files()
    if found_files:
        count = acc_mgr.load_from_files()
        print(f"  [ℹ] {count} Accounts aus {len(found_files)} Dateien geladen.")
        if cfg.get("auto_validate", True):
            print("  [*] Validiere Accounts...")
            proxy_list = load_proxies(cfg.get("proxies_file", "proxies.txt"))
            valid, invalid = acc_mgr.validate_all(proxy_list if proxy_list else None)
            print(f"  [✅] {valid} valid, [❌] {invalid} invalid")
        time.sleep(1)

    engine: Optional[LiveBotEngine] = None
    proxy_list = load_proxies(cfg.get("proxies_file", "proxies.txt"))

    while True:
        print_banner()
        pool_stats = acc_mgr.pool.get_stats() if acc_mgr.pool._accounts else None
        print_stats(engine.stats if engine else BotStats(), pool_stats)
        print_main_menu(cfg,
                        active_session and active_session.logged_in,
                        engine and engine.running,
                        pool_stats['total'] if pool_stats else 0,
                        pool_stats['valid'] if pool_stats else 0)

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

            # Accounts aus Pool verwenden?
            use_accounts = False
            if acc_mgr.pool.valid_count > 0:
                use_acc_input = input("  👥 Accounts aus Pool verwenden? (J/n): ").strip().lower()
                use_accounts = use_acc_input != "n"

            print(f"\n  [*] Starte {threads} Worker für @{target}...")
            print(f"  [*] Aktionen: {', '.join(actions)}")
            print(f"  [*] Intervall: {interval}s")
            if use_accounts:
                print(f"  [*] Accounts: {acc_mgr.pool.valid_count} valid im Pool")

            engine = LiveBotEngine(
                username=target,
                room_id=room_id,
                num_threads=threads,
                proxy_list=proxy_list,
                actions=actions,
                interval=interval,
                account_pool=acc_mgr.pool if use_accounts else None,
            )
            engine.start()

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
            # Account-Manager
            acc_mgr = account_manager_menu(acc_mgr, cfg)

        elif choice == "3":
            # Login
            if not active_session:
                active_session = TikTokSession()
            ok, active_session = login_flow(active_session, cfg)

        elif choice == "4":
            # Aktionen
            actions = select_actions()
            cfg["actions"] = actions
            ConfigManager.save(cfg)
            print(f"  [✅] Aktionen: {', '.join(actions)}")
            input("  Drücke Enter...")

        elif choice == "5":
            # Proxy
            path = input(f"  Pfad [{cfg.get('proxies_file', 'proxies.txt')}]: ").strip() or cfg.get("proxies_file", "proxies.txt")
            proxy_list = load_proxies(path)
            cfg["proxies_file"] = path
            ConfigManager.save(cfg)
            print(f"  [{'✅' if proxy_list else '❌'}] {len(proxy_list)} Proxies geladen.")
            input("  Drücke Enter...")

        elif choice == "6":
            # Einstellungen
            print("""
  ┌─────────────── ⚙️ EINSTELLUNGEN ───────────┐
  │  [1] Region ändern                         │
  │  [2] App-Version                           │
  │  [3] SDK-Version                           │
  │  [4] Auto-Validate (beim Start)            │
  │  [5] Refresh-Intervall (Sekunden)          │
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
            elif sub == "4":
                current = cfg.get("auto_validate", True)
                val = input(f"  Auto-Validate beim Start [{current}] (j/n): ").strip().lower()
                if val in ("j", "ja", "y", "yes"):
                    cfg["auto_validate"] = True
                elif val in ("n", "nein", "no"):
                    cfg["auto_validate"] = False
                ConfigManager.save(cfg)
            elif sub == "5":
                sec = input(f"  Refresh-Intervall [{cfg.get('refresh_interval', 300)}]: ").strip()
                if sec.isdigit():
                    cfg["refresh_interval"] = int(sec)
                    ConfigManager.save(cfg)
            input("  Drücke Enter...")

        elif choice == "7":
            # Stats reset
            if engine:
                engine.stats = BotStats()
            print("  [✅] Statistiken zurückgesetzt.")
            input("  Drücke Enter...")

        elif choice == "8":
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
                name = input("  Session-Name: ").strip() or cfg.get("login_username", "default")
                path = active_session.save(name)
                print(f"  [✅] Session gespeichert: {path}")
            elif sub == "2":
                sessions = list(COOKIE_DIR.glob("session_*.pkl"))
                if not sessions:
                    print("  [!] Keine Sessions gefunden.")
                else:
                    print("  Verfügbar:")
                    for s in sessions:
                        print(f"    → {s.stem.replace('session_', '')}")
                    name = input("  Name: ").strip() or "default"
                    loaded = TikTokSession.load(name)
                    if loaded:
                        active_session = loaded
                        cfg["login_username"] = name
                        ConfigManager.save(cfg)
                        print(f"  [✅] Geladen. UID: {loaded.uid[:15]}...")
                    else:
                        print("  [!] Nicht gefunden.")
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
