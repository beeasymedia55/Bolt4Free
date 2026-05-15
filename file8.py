#!/usr/bin/env python3
"""
TIKTOK LIVE BOT - SignerPy Style (from example)
Uses SignerPy.sign() exactly like the TikTok account creator example
"""

import requests
from urllib.parse import urlencode
import re
import time
import random
import string
import os
import uuid
import json
import secrets
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import SignerPy

requests.packages.urllib3.disable_warnings()

# =============================================================================
# CONFIGURATION
# =============================================================================
WEBCAST_DOMAINS = [
    "webcast-h2.tiktokv.com", "webcast.tiktokv.com",
    "webcast-hl.tiktokv.com", "webcast-va.tiktokv.com",
]

# Device profiles
DEVICES = [
    {"device_id": "7528525775047132680", "install_id": "7528525992324908807", "openudid": "7a59d727a58ee91e", "cdid": "a90f0ed5-8028-413e-a00d-77e931779d00"},
    {"device_id": "7528525775047132681", "install_id": "7528525992324908808", "openudid": "8a59d727a58ee91f", "cdid": "b90f0ed5-8028-413e-a00d-77e931779d01"},
    {"device_id": "7528525775047132682", "install_id": "7528525992324908809", "openudid": "9a59d727a58ee91g", "cdid": "c90f0ed5-8028-413e-a00d-77e931779d02"},
]

# Proxies pool
proxy_pool = []
proxy_lock = threading.Lock()

# Stats
stats_lock = threading.Lock()
views = likes = shares = follows = errors = total_reqs = 0
running = False

# =============================================================================
# PARAMS GENERATOR (exactly like your example)
# =============================================================================
def make_tiktok_params(device=None):
    """Generate TikTok params exactly like the example"""
    if device is None:
        device = random.choice(DEVICES)
    
    dd = str(random.randint(1, 10**19))
    return {
        "passport-sdk-version": "6031990",
        "device_platform": "android",
        "os": "android",
        "ssmix": "a",
        "_rticket": str(int(time.time() * 1000)),
        "cdid": device['cdid'],
        "channel": "googleplay",
        "aid": "1233",
        "app_name": "musical_ly",
        "version_code": "370805",
        "version_name": "37.8.5",
        "manifest_version_code": "2023708050",
        "update_version_code": "2023708050",
        "ab_version": "37.8.5",
        "resolution": "900*1600",
        "dpi": "240",
        "device_type": "NE2211",
        "device_brand": "OnePlus",
        "language": "en",
        "os_api": "28",
        "os_version": "9",
        "ac": "wifi",
        "is_pad": "0",
        "current_region": "TW",
        "app_type": "normal",
        "sys_region": "US",
        "last_install_time": str(int(time.time()) - random.randint(1000, 10000)),
        "mcc_mnc": "46692",
        "timezone_name": "Asia/Baghdad",
        "carrier_region_v2": "466",
        "residence": "TW",
        "app_language": "en",
        "carrier_region": "TW",
        "timezone_offset": "10800",
        "host_abi": "arm64-v8a",
        "locale": "en-GB",
        "ac2": "wifi",
        "uoo": "0",
        "op_region": "TW",
        "build_number": "37.8.5",
        "region": "GB",
        "ts": str(int(time.time())),
        "iid": device['install_id'],
        "device_id": device['device_id'],
        "openudid": device['openudid'],
        "support_webview": "1",
        "reg_store_region": "tw",
        "user_selected_region": "0",
        "okhttp_version": "4.2.210.6-tiktok",
        "use_store_region_cookie": "1",
        "app_version": "37.8.5"
    }, device['install_id']

# =============================================================================
# LIVE STREAM PARAMS (different endpoints but same pattern)
# =============================================================================
def make_live_enter_params(room_id, device=None):
    """Params for /webcast/room/enter/"""
    if device is None:
        device = random.choice(DEVICES)
    
    return {
        "aid": "1233",
        "app_name": "musical_ly",
        "version_code": "370805",
        "version_name": "37.8.5",
        "device_id": device['device_id'],
        "device_platform": "android",
        "device_type": "NE2211",
        "os_version": "9",
        "os_api": "28",
        "channel": "googleplay",
        "resolution": "900*1600",
        "dpi": "240",
        "openudid": device['openudid'],
        "cdid": device['cdid'],
        "iid": device['install_id'],
        "language": "en",
        "app_language": "en",
        "region": "GB",
        "sys_region": "US",
        "timezone_name": "Asia/Baghdad",
        "timezone_offset": "10800",
        "carrier_region": "TW",
        "carrier_region_v2": "466",
        "mcc_mnc": "46692",
        "ac": "wifi",
        "ac2": "wifi",
        "uoo": "0",
        "is_pad": "0",
        "host_abi": "arm64-v8a",
        "locale": "en-GB",
        "build_number": "37.8.5",
        "manifest_version_code": "2023708050",
        "update_version_code": "2023708050",
        "_rticket": str(int(time.time() * 1000)),
        "ts": str(int(time.time())),
        "room_id": room_id,
        "live_id": str(random.randint(10**17, 10**18-1)),
        "enter_source": "feed",
        "is_login": "1",
        "type": "live",
    }, device

def make_live_like_params(room_id, device=None):
    """Params for /webcast/like/"""
    if device is None:
        device = random.choice(DEVICES)
    
    return {
        "aid": "1233",
        "app_name": "musical_ly",
        "version_code": "370805",
        "version_name": "37.8.5",
        "device_id": device['device_id'],
        "device_platform": "android",
        "device_type": "NE2211",
        "os_version": "9",
        "os_api": "28",
        "channel": "googleplay",
        "resolution": "900*1600",
        "dpi": "240",
        "openudid": device['openudid'],
        "cdid": device['cdid'],
        "iid": device['install_id'],
        "language": "en",
        "app_language": "en",
        "region": "GB",
        "sys_region": "US",
        "timezone_name": "Asia/Baghdad",
        "timezone_offset": "10800",
        "carrier_region": "TW",
        "carrier_region_v2": "466",
        "mcc_mnc": "46692",
        "ac": "wifi",
        "ac2": "wifi",
        "uoo": "0",
        "is_pad": "0",
        "host_abi": "arm64-v8a",
        "locale": "en-GB",
        "build_number": "37.8.5",
        "manifest_version_code": "2023708050",
        "update_version_code": "2023708050",
        "_rticket": str(int(time.time() * 1000)),
        "ts": str(int(time.time())),
        "room_id": room_id,
        "like_count": str(random.randint(1, 5)),
        "live_id": str(random.randint(10**17, 10**18-1)),
        "type": "aweme",
    }, device

def make_live_share_params(room_id, device=None):
    """Params for /webcast/share/"""
    if device is None:
        device = random.choice(DEVICES)
    
    return {
        "aid": "1233",
        "app_name": "musical_ly",
        "version_code": "370805",
        "version_name": "37.8.5",
        "device_id": device['device_id'],
        "device_platform": "android",
        "device_type": "NE2211",
        "os_version": "9",
        "os_api": "28",
        "channel": "googleplay",
        "resolution": "900*1600",
        "dpi": "240",
        "openudid": device['openudid'],
        "cdid": device['cdid'],
        "iid": device['install_id'],
        "language": "en",
        "app_language": "en",
        "region": "GB",
        "sys_region": "US",
        "timezone_name": "Asia/Baghdad",
        "timezone_offset": "10800",
        "carrier_region": "TW",
        "carrier_region_v2": "466",
        "mcc_mnc": "46692",
        "ac": "wifi",
        "ac2": "wifi",
        "uoo": "0",
        "is_pad": "0",
        "host_abi": "arm64-v8a",
        "locale": "en-GB",
        "build_number": "37.8.5",
        "manifest_version_code": "2023708050",
        "update_version_code": "2023708050",
        "_rticket": str(int(time.time() * 1000)),
        "ts": str(int(time.time())),
        "room_id": room_id,
        "share_type": random.choice(["1", "2", "3"]),
        "share_delta": "1",
        "live_id": str(random.randint(10**17, 10**18-1)),
    }, device

def make_follow_params(sec_uid, device=None):
    """Params for /aweme/v1/commit/follow/user/"""
    if device is None:
        device = random.choice(DEVICES)
    
    return {
        "aid": "1233",
        "app_name": "musical_ly",
        "version_code": "370805",
        "version_name": "37.8.5",
        "device_id": device['device_id'],
        "device_platform": "android",
        "device_type": "NE2211",
        "os_version": "9",
        "os_api": "28",
        "channel": "googleplay",
        "resolution": "900*1600",
        "dpi": "240",
        "openudid": device['openudid'],
        "cdid": device['cdid'],
        "iid": device['install_id'],
        "language": "en",
        "app_language": "en",
        "region": "GB",
        "sys_region": "US",
        "timezone_name": "Asia/Baghdad",
        "timezone_offset": "10800",
        "carrier_region": "TW",
        "carrier_region_v2": "466",
        "mcc_mnc": "46692",
        "ac": "wifi",
        "ac2": "wifi",
        "uoo": "0",
        "is_pad": "0",
        "host_abi": "arm64-v8a",
        "locale": "en-GB",
        "build_number": "37.8.5",
        "manifest_version_code": "2023708050",
        "update_version_code": "2023708050",
        "_rticket": str(int(time.time() * 1000)),
        "ts": str(int(time.time())),
        "to_user_id": sec_uid,
        "status": "1",
        "type": "aweme",
        "from": "profile",
    }, device

# =============================================================================
# SIGNERPY WRAPPER - EXACTLY like your example
# =============================================================================
def sign_request(params: dict, payload: dict = None, cookies: dict = None):
    """
    Sign a request using SignerPy exactly like the example:
    m = SignerPy.sign(params=params, payload=payload, cookie=cookies)
    Returns the signature dict with x-gorgon, x-argus, x-khronos, x-ladon, etc.
    """
    if payload is None:
        payload = {}
    if cookies is None:
        cookies = {}
    
    # EXACTLY like your example code
    m = SignerPy.sign(params=params, payload=payload, cookie=cookies)
    return m

# =============================================================================
# PROXY TESTER
# =============================================================================
class ProxyTester:
    @staticmethod
    def test_against_webcast(proxy_url, timeout=8):
        test_domain = random.choice(WEBCAST_DOMAINS)
        test_url = f"https://{test_domain}/webcast/room/enter/"
        params = {"aid": "1233", "room_id": "123456789012345678", "ts": str(int(time.time()))}
        try:
            resp = requests.get(test_url, params=params, 
                              proxies={'http': proxy_url, 'https': proxy_url},
                              timeout=timeout, verify=False)
            return resp.status_code in [200, 403, 429, 503], resp.elapsed.total_seconds()
        except: return False, 0
    
    @staticmethod
    def test_batch(proxies, max_workers=50):
        working = []
        print(f"\n🔬 Testing {len(proxies)} proxies...")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for p in proxies:
                scheme = "http"
                futures[executor.submit(ProxyTester.test_against_webcast, f"{scheme}://{p}")] = p
            completed = 0
            for future in as_completed(futures):
                success, latency = future.result()
                completed += 1
                if success:
                    working.append(futures[future])
                print(f"\r⏳ [{completed}/{len(proxies)}] Working: {len(working)}", end='')
        print(f"\n✅ {len(working)} working proxies")
        return working

class ProxyScraper:
    @staticmethod
    def scrape():
        urls = [
            "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all",
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
        ]
        all_proxies = set()
        for url in urls:
            try:
                resp = requests.get(url, timeout=10)
                for line in resp.text.split('\n'):
                    line = line.strip()
                    if ':' in line and not line.startswith('#'):
                        all_proxies.add(line)
            except: pass
        return list(all_proxies)

# =============================================================================
# TIKTOK LIVE WORKER - Uses SignerPy exactly like your example
# =============================================================================

class TikTokLiveWorker:
    def __init__(self, room_id, proxy=None, device=None):
        self.room_id = room_id
        self.proxy = proxy
        self.device = device or random.choice(DEVICES)
        self.session = requests.Session()
        if proxy:
            self.session.proxies = {'http': f"http://{proxy}", 'https': f"http://{proxy}"}
    
    def _make_request(self, endpoint, params, payload=None):
        """Make request WITH SignerPy signatures - EXACTLY like your example"""
        domain = random.choice(WEBCAST_DOMAINS)
        url = f"https://{domain}{endpoint}"
        
        # Generate headers using SignerPy - exactly like your example
        if payload:
            m = SignerPy.sign(params=params, payload=payload)
        else:
            m = SignerPy.sign(params=params, payload={})
        
        headers = {
            'User-Agent': "com.zhiliaoapp.musically/2023708050 (Linux; U; Android 9; en_GB; NE2211; Build/SKQ1.220617.001;tt-ok/3.12.13.16)",
            'Connection': "Keep-Alive",
            'Accept-Encoding': "gzip",
            'Content-Type': "application/x-www-form-urlencoded; charset=UTF-8",
            'X-SS-STUB': m['x-ss-stub'],
            'X-SS-REQ-TICKET': m['x-ss-req-ticket'],
            'X-Ladon': m['x-ladon'],
            'X-Khronos': m['x-khronos'],
            'X-Argus': m['x-argus'],
            'X-Gorgon': m['x-gorgon'],
            'x-tt-pba-enable': "1",
            'x-bd-kmsv': "0",
            'x-tt-dm-status': "login=1;ct=1;rt=8",
            'x-bd-client-key': "#yEjw14J8W9l4SfT9U1TO60CXVvhTKWlciV4wIs/yJvoJp9e6R85bFU+QLZlj2NzfUISVioYXoQrs9gx6",
            'x-tt-passport-csrf-token': secrets.token_hex(16),
            'sdk-version': "2",
            'passport-sdk-version': "6031990",
            'passport-sdk-settings': "x-tt-token",
            'passport-sdk-sign': "x-tt-token",
            'x-tt-bypass-dp': "1",
            'x-tt-request-tag': f"n=0;nr=011;bg=0",
            'Host': domain,
            'Accept': "application/json",
        }
        
        try:
            if payload:
                resp = self.session.post(url, params=params, data=payload, headers=headers, timeout=10, verify=False)
            else:
                resp = self.session.get(url, params=params, headers=headers, timeout=10, verify=False)
            return resp
        except:
            return None
    
    def enter_room(self):
        params, dev = make_live_enter_params(self.room_id, self.device)
        resp = self._make_request('/webcast/room/enter/', params)
        if resp and resp.status_code == 200:
            try: 
                data = resp.json()
                return data.get('status_code') == 0
            except: pass
        return False
    
    def send_like(self):
        params, dev = make_live_like_params(self.room_id, self.device)
        resp = self._make_request('/webcast/like/', params)
        return resp is not None and resp.status_code == 200
    
    def send_share(self):
        params, dev = make_live_share_params(self.room_id, self.device)
        resp = self._make_request('/webcast/share/', params)
        return resp is not None and resp.status_code == 200
    
    def send_follow(self, sec_uid):
        params, dev = make_follow_params(sec_uid, self.device)
        resp = self._make_request('/aweme/v1/commit/follow/user/', params)
        return resp is not None and resp.status_code == 200

# =============================================================================
# BOT
# =============================================================================

class TikTokLiveBot:
    def __init__(self):
        self.room_id = ""
        self.sec_uid = ""
        self.mode = "views"
        self.threads = 10
        self.target = 1000
        self.proxies = []
    
    def worker(self):
        global views, likes, shares, follows, errors, total_reqs, running
        while running:
            try:
                proxy = random.choice(self.proxies) if self.proxies else None
                device = random.choice(DEVICES)
                worker = TikTokLiveWorker(self.room_id, proxy, device)
                
                if worker.enter_room():
                    with stats_lock:
                        views += 1
                        total_reqs += 1
                    
                    for _ in range(random.randint(3, 8)):
                        if not running: break
                        
                        if self.mode in ['likes', 'all'] and worker.send_like():
                            with stats_lock: likes += 1; total_reqs += 1
                        
                        if self.mode in ['shares', 'all'] and random.random() < 0.3:
                            if worker.send_share():
                                with stats_lock: shares += 1; total_reqs += 1
                        
                        if self.mode in ['follows', 'all'] and random.random() < 0.1 and self.sec_uid:
                            if worker.send_follow(self.sec_uid):
                                with stats_lock: follows += 1; total_reqs += 1
                        
                        time.sleep(random.uniform(1.5, 3.5))
                else:
                    with stats_lock: errors += 1
                    
            except:
                with stats_lock: errors += 1
            
            time.sleep(0.5)
    
    def start(self):
        global running
        running = True
        print(f"\n🚀 Bot started | Mode: {self.mode} | Room: {self.room_id} | Threads: {self.threads} | Target: {self.target}")
        print(f"🔐 Using SignerPy for ALL signatures\n")
        
        for i in range(self.threads):
            threading.Thread(target=self.worker, daemon=True).start()
        
        # Dashboard
        start = time.time()
        try:
            while running:
                time.sleep(2)
                elapsed = time.time() - start
                
                os.system('cls' if os.name == 'nt' else 'clear')
                print("""
╔══════════════════════════════════════════════════════════════╗
║   TIKTOK LIVE BOT - SignerPy PRODUCTION                     ║
╚══════════════════════════════════════════════════════════════╝
                """)
                print(f" 🔐 SignerPy: ✅ ACTIVE (signing ALL requests)")
                print(f" {'─'*55}")
                print(f" 🎯 Mode:     {self.mode.upper():<12}  🕒 Uptime: {int(elapsed//3600):02d}:{int((elapsed%3600)//60):02d}:{int(elapsed%60):02d}")
                print(f" 🔴 Room ID:  {self.room_id}")
                print(f" {'─'*55}")
                print(f" 👁️  Views:   {views:>7,}  ❤️  Likes:    {likes:>6,}")
                print(f" 🔗 Shares:  {shares:>7,}  👤 Follows:  {follows:>6,}")
                print(f" ❌ Errors:  {errors:>7,}  📊 Total:    {total_reqs:>6,}")
                print(f" ⚡ Rate:    {total_reqs/elapsed:>5.0f} req/s")
                print(f" {'─'*55}")
                print(f" 🧵 Threads: {self.threads}  🌐 Proxies:  {len(self.proxies)}")
                print(f" {'─'*55}")
                print(f" Press Ctrl+C to stop")
                
                if views >= self.target:
                    print(f"\n✅ Target reached! {views} views")
                    running = False
                    break
                    
        except KeyboardInterrupt:
            running = False
            print(f"\n🛑 Stopped | Views: {views} | Likes: {likes} | Errors: {errors}")

# =============================================================================
# MAIN
# =============================================================================

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    bot = TikTokLiveBot()
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║  TIKTOK LIVE BOT - SignerPy INTEGRATED                      ║
║  Uses SignerPy.sign() exactly like account creator example   ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    while True:
        print("\n📋 MAIN MENU:")
        print(" [0] ⚙️  Setup")
        print(" [1] 🌐 Proxy Manager") 
        print(" [2] 🚀 Start Bot")
        print(" [Q] Quit\n")
        
        choice = input(" Select: ").strip().upper()
        
        if choice == 'Q':
            print("👋 Bye!"); break
        
        elif choice == '0':
            room = input(" Room ID: ").strip()
            if room.isdigit() and len(room) >= 15:
                bot.room_id = room
            
            sec = input(" sec_uid (for follows, Enter to skip): ").strip()
            if sec: bot.sec_uid = sec
            
            print("\n Mode:")
            print(" 1 - Views  2 - Likes  3 - Shares  4 - Follows  5 - ALL")
            mc = input(" Select (1-5): ").strip()
            mode_map = {'1':'views','2':'likes','3':'shares','4':'follows','5':'all'}
            if mc in mode_map: bot.mode = mode_map[mc]
            
            try:
                bot.threads = max(1, min(500, int(input(" Threads (1-500): ") or "10")))
                bot.target = int(input(" Target: ") or "1000")
            except: pass
            input("Press Enter...")
        
        elif choice == '1':
            print("\n [1] Scrape HTTP proxies")
            print(" [2] Load from file")
            pc = input(" Select: ").strip()
            if pc == '1':
                proxies = ProxyScraper.scrape()
                print(f" Scraped {len(proxies)} proxies")
                test = input(" Test? (y/n): ").strip().lower()
                if test == 'y':
                    bot.proxies = ProxyTester.test_batch(proxies[:200])
                input("Press Enter...")
            elif pc == '2':
                try:
                    with open('proxies_working.txt') as f:
                        bot.proxies = [l.strip() for l in f if ':' in l.strip()]
                    print(f" Loaded {len(bot.proxies)} proxies")
                except: print(" File not found")
                input("Press Enter...")
        
        elif choice == '2':
            if not bot.room_id: print(" Set Room ID first!"); input(); continue
            bot.start()
            input("Press Enter...")

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: print("\n👋 Exiting...")
    except Exception as e: print(f"❌ {e}"); import traceback; traceback.print_exc()
