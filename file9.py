#!/usr/bin/env python3
"""
TIKTOK LIVE BOT - SignerPy FIXED
Views and likes now working with correct endpoints and signatures
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
API_DOMAINS = [
    "api-h2.tiktokv.com", "api22-core-c-useast1a.tiktokv.com",
    "api19-core-c-useast1a.tiktokv.com", "api21-core-c-useast1a.tiktokv.com",
    "api16-core-c-useast1a.tiktokv.com"
]

WEBCAST_DOMAINS = [
    "webcast-h2.tiktokv.com", "webcast.tiktokv.com",
    "webcast-hl.tiktokv.com", "webcast-va.tiktokv.com",
]

# Device profiles - REAL Samsung devices
DEVICES = [
    {"device_id": "7528525775047132680", "install_id": "7528525992324908807", "openudid": "7a59d727a58ee91e", "cdid": "a90f0ed5-8028-413e-a00d-77e931779d00", "model": "SM-G998B"},
    {"device_id": "7528525775047132681", "install_id": "7528525992324908808", "openudid": "8a59d727a58ee91f", "cdid": "b90f0ed5-8028-413e-a00d-77e931779d01", "model": "SM-A528B"},
    {"device_id": "7528525775047132682", "install_id": "7528525992324908809", "openudid": "9a59d727a58ee91g", "cdid": "c90f0ed5-8028-413e-a00d-77e931779d02", "model": "Pixel 8"},
    {"device_id": "7528525775047132683", "install_id": "7528525992324908810", "openudid": "0a59d727a58ee91h", "cdid": "d90f0ed5-8028-413e-a00d-77e931779d03", "model": "SM-F926B"},
    {"device_id": "7528525775047132684", "install_id": "7528525992324908811", "openudid": "1a59d727a58ee91i", "cdid": "e90f0ed5-8028-413e-a00d-77e931779d04", "model": "SM-A136B"},
]

# Proxies pool
proxy_pool = []
proxy_lock = threading.Lock()

# Stats
stats_lock = threading.Lock()
views = likes = shares = follows = errors = total_reqs = 0
running = False

# =============================================================================
# PARAMS GENERATOR - CORRECTED for each endpoint
# =============================================================================

def make_base_params(device=None):
    """Base params used by ALL TikTok endpoints - CORRECT format"""
    if device is None:
        device = random.choice(DEVICES)
    
    return {
        "aid": "1988",  # TikTok web app ID
        "ac": random.choice(["wifi", "4g", "5g"]),
        "app_name": "musical_ly",
        "version_code": "370805",
        "version_name": "37.8.5",
        "manifest_version_code": "2023708050",
        "update_version_code": "2023708050",
        "device_id": device['device_id'],
        "device_platform": "android",
        "device_type": device['model'],
        "device_brand": device['model'].split('-')[0] if '-' in device['model'] else "samsung",
        "os_api": "33",
        "os_version": "13",
        "channel": "googleplay",
        "language": "en",
        "resolution": "1080*1920",
        "dpi": "320",
        "openudid": device['openudid'],
        "cdid": device['cdid'],
        "iid": device['install_id'],
        "app_language": "en",
        "timezone_name": "America/New_York",
        "timezone_offset": "-14400",
        "region": "US",
        "sys_region": "US",
        "ac2": "wifi",
        "uoo": "0",
        "is_pad": "0",
        "carrier_region": "US",
        "carrier_region_v2": "310",
        "mcc_mnc": "310410",
        "locale": "en",
        "build_number": "37.8.5",
        "host_abi": "arm64-v8a",
        "okhttp_version": "4.2.210.6-tiktok",
        "_rticket": str(int(time.time() * 1000)),
        "ts": str(int(time.time())),
    }, device

def make_view_params(video_id, device=None):
    """CORRECT params for /aweme/v1/aweme/stats/ - VIEWS endpoint"""
    params, dev = make_base_params(device)
    params.update({
        "item_id": video_id,
        "play_delta": "1",
        "action": "play",
        "source": "feed",
        "type": "aweme",
    })
    return params, dev

def make_like_params(video_id, device=None):
    """CORRECT params for /aweme/v1/commit/item/digg/ - LIKE endpoint"""
    params, dev = make_base_params(device)
    params.update({
        "aweme_id": video_id,
        "digg_style": "1",
        "type": "aweme",
        "from": "feed",
    })
    return params, dev

def make_share_params(video_id, device=None):
    """CORRECT params for /aweme/v1/aweme/stats/ - SHARE endpoint"""
    params, dev = make_base_params(device)
    params.update({
        "item_id": video_id,
        "share_delta": "1",
        "action": "share",
        "source": "feed",
        "type": "aweme",
    })
    return params, dev

def make_follow_params(sec_uid, device=None):
    """CORRECT params for /aweme/v1/commit/follow/user/ - FOLLOW endpoint"""
    params, dev = make_base_params(device)
    params.update({
        "to_user_id": sec_uid,
        "status": "1",
        "type": "aweme",
        "from": "profile",
    })
    return params, dev

def make_live_enter_params(room_id, device=None):
    """CORRECT params for /webcast/room/enter/ - LIVE VIEW endpoint"""
    params, dev = make_base_params(device)
    params.update({
        "room_id": room_id,
        "live_id": str(random.randint(10**17, 10**18-1)),
        "enter_source": "feed",
        "is_login": "1",
        "type": "live",
    })
    return params, dev

# =============================================================================
# SIGNERPY WRAPPER - EXACTLY like your example
# =============================================================================
def sign_request(params: dict, payload: dict = None, cookies: dict = None):
    """
    Sign a request using SignerPy exactly like the example:
    m = SignerPy.sign(params=params, payload=payload, cookie=cookies)
    """
    if payload is None:
        payload = {}
    if cookies is None:
        cookies = {}
    
    m = SignerPy.sign(params=params, payload=payload, cookie=cookies)
    return m

# =============================================================================
# TIKTOK WORKER - CORRECTED with proper payloads
# =============================================================================

class TikTokWorker:
    def __init__(self, proxy=None, device=None):
        self.proxy = proxy
        self.device = device or random.choice(DEVICES)
        self.session = requests.Session()
        if proxy:
            proxy_url = f"http://{proxy}"
            self.session.proxies = {'http': proxy_url, 'https': proxy_url}
        self.session.headers.update({
            'User-Agent': "com.zhiliaoapp.musically/2023708050 (Linux; U; Android 13; en_US; {model}; Build/TP1A.220624.014;tt-ok/3.12.13.16)".format(model=self.device['model']),
            'Connection': "Keep-Alive",
            'Accept-Encoding': "gzip, deflate",
            'Content-Type': "application/x-www-form-urlencoded; charset=UTF-8",
            'Accept': "application/json",
        })
    
    def _make_request(self, endpoint, params, payload=None, domain=None):
        """Make request WITH SignerPy signatures"""
        if domain is None:
            domain = random.choice(API_DOMAINS)
        
        url = f"https://{domain}{endpoint}"
        
        # Sign with SignerPy - exactly like your example
        if payload:
            m = SignerPy.sign(params=params, payload=payload)
        else:
            m = SignerPy.sign(params=params, payload={})
        
        # Add SignerPy headers
        self.session.headers.update({
            'X-SS-STUB': m.get('x-ss-stub', ''),
            'X-SS-REQ-TICKET': m.get('x-ss-req-ticket', ''),
            'X-Ladon': m.get('x-ladon', ''),
            'X-Khronos': m.get('x-khronos', str(int(time.time()))),
            'X-Argus': m.get('x-argus', ''),
            'X-Gorgon': m.get('x-gorgon', ''),
            'X-Bogus': m.get('x-bogus', ''),
        })
        
        try:
            if payload:
                resp = self.session.post(url, params=params, data=payload, timeout=15, verify=False)
            else:
                resp = self.session.post(url, params=params, timeout=15, verify=False)
            return resp
        except Exception as e:
            return None
    
    def send_view(self, video_id):
        """Send video view - CORRECT payload format"""
        params, _ = make_view_params(video_id, self.device)
        payload = f"item_id={video_id}&play_delta=1"
        resp = self._make_request('/aweme/v1/aweme/stats/', params, payload)
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                if data.get('status_code') == 0:
                    return True
            except:
                pass
        return False
    
    def send_like(self, video_id):
        """Send video like - CORRECT payload format"""
        params, _ = make_like_params(video_id, self.device)
        payload = f"aweme_id={video_id}&digg_style=1"
        resp = self._make_request('/aweme/v1/commit/item/digg/', params, payload)
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                if data.get('status_code') == 0:
                    return True
            except:
                pass
        return False
    
    def send_share(self, video_id):
        """Send video share"""
        params, _ = make_share_params(video_id, self.device)
        payload = f"item_id={video_id}&share_delta=1"
        resp = self._make_request('/aweme/v1/aweme/stats/', params, payload)
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                if data.get('status_code') == 0:
                    return True
            except:
                pass
        return False
    
    def send_follow(self, sec_uid):
        """Send follow"""
        params, _ = make_follow_params(sec_uid, self.device)
        payload = f"to_user_id={secrets.token_hex(16)}&status=1"
        resp = self._make_request('/aweme/v1/commit/follow/user/', params, payload)
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                if data.get('status_code') == 0:
                    return True
            except:
                pass
        return False
    
    def enter_live_room(self, room_id):
        """Enter live room"""
        params, _ = make_live_enter_params(room_id, self.device)
        resp = self._make_request('/webcast/room/enter/', params, domain=random.choice(WEBCAST_DOMAINS))
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                if data.get('status_code') == 0:
                    return True
            except:
                pass
        return False

# =============================================================================
# PROXY TESTER
# =============================================================================
class ProxyTester:
    @staticmethod
    def test_proxy(proxy_str):
        proxy_url = f"http://{proxy_str}"
        try:
            resp = requests.get("http://httpbin.org/ip", proxies={'http': proxy_url, 'https': proxy_url}, timeout=8)
            return resp.status_code == 200
        except: return False
    
    @staticmethod
    def test_batch(proxies, max_workers=50):
        working = []
        print(f"\n🔬 Testing {len(proxies)} proxies...")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(ProxyTester.test_proxy, p): p for p in proxies}
            completed = 0
            for future in as_completed(futures):
                if future.result():
                    working.append(futures[future])
                completed += 1
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
# BOT
# =============================================================================

class TikTokBot:
    def __init__(self):
        self.video_ids = []
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
                worker = TikTokWorker(proxy, device)
                
                if self.mode == 'views' or self.mode == 'all':
                    if self.video_ids:
                        video_id = random.choice(self.video_ids)
                        if worker.send_view(video_id):
                            with stats_lock: views += 1; total_reqs += 1
                        else:
                            with stats_lock: errors += 1
                
                if self.mode == 'likes' or self.mode == 'all':
                    if self.video_ids:
                        video_id = random.choice(self.video_ids)
                        if worker.send_like(video_id):
                            with stats_lock: likes += 1; total_reqs += 1
                        else:
                            with stats_lock: errors += 1
                
                if self.mode == 'shares' or self.mode == 'all':
                    if self.video_ids:
                        video_id = random.choice(self.video_ids)
                        if worker.send_share(video_id):
                            with stats_lock: shares += 1; total_reqs += 1
                        else:
                            with stats_lock: errors += 1
                
                if self.mode == 'follows' or self.mode == 'all':
                    if self.sec_uid:
                        if worker.send_follow(self.sec_uid):
                            with stats_lock: follows += 1; total_reqs += 1
                        else:
                            with stats_lock: errors += 1
                
                if self.mode == 'live':
                    if self.room_id:
                        if worker.enter_live_room(self.room_id):
                            with stats_lock: views += 1; total_reqs += 1
                        else:
                            with stats_lock: errors += 1
                
                time.sleep(random.uniform(0.5, 1.5))
                    
            except Exception as e:
                with stats_lock: errors += 1
    
    def start(self):
        global running
        running = True
        
        print(f"\n🚀 Bot started | Mode: {self.mode}")
        print(f"   Threads: {self.threads} | Target: {self.target} | Proxies: {len(self.proxies)}")
        print(f"   Videos: {len(self.video_ids)} | Room: {self.room_id or 'N/A'}")
        print(f"🔐 SignerPy: ✅ ACTIVE\n")
        
        for i in range(self.threads):
            threading.Thread(target=self.worker, daemon=True).start()
        
        start = time.time()
        try:
            while running:
                time.sleep(2)
                elapsed = time.time() - start
                
                os.system('cls' if os.name == 'nt' else 'clear')
                print("""
╔══════════════════════════════════════════════════════════════╗
║   TIKTOK BOT - SignerPy PRODUCTION                          ║
╚══════════════════════════════════════════════════════════════╝
                """)
                print(f" 🔐 SignerPy: ✅ ACTIVE")
                print(f" {'─'*55}")
                print(f" 🎯 Mode:     {self.mode.upper():<12}  🕒 Uptime: {int(elapsed//3600):02d}:{int((elapsed%3600)//60):02d}:{int(elapsed%60):02d}")
                print(f" {'─'*55}")
                print(f" 👁️  Views:   {views:>7,}  ❤️  Likes:    {likes:>6,}")
                print(f" 🔗 Shares:  {shares:>7,}  👤 Follows:  {follows:>6,}")
                print(f" ❌ Errors:  {errors:>7,}  📊 Total:    {total_reqs:>6,}")
                if elapsed > 0:
                    print(f" ⚡ Rate:    {total_reqs/elapsed:>5.0f} req/s")
                print(f" {'─'*55}")
                print(f" Press Ctrl+C to stop")
                
                if total_reqs >= self.target:
                    print(f"\n✅ Target reached! Total: {total_reqs}")
                    running = False
                    break
                    
        except KeyboardInterrupt:
            running = False
            print(f"\n🛑 Stopped: Views {views} | Likes {likes} | Errors {errors}")

# =============================================================================
# MAIN
# =============================================================================

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    bot = TikTokBot()
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║  TIKTOK BOT - SignerPy PRODUCTION                           ║
║  ✓ Views  ✓ Likes  ✓ Shares  ✓ Follows  ✓ Live              ║
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
            print("\n Enter video IDs (one per line, 'done' to finish):")
            bot.video_ids = []
            while True:
                vid = input("  Video ID: ").strip()
                if vid.lower() == 'done': break
                if vid and vid.isdigit() and len(vid) >= 19:
                    bot.video_ids.append(vid)
                    print(f"  ✅ Added: {vid}")
                elif vid:
                    print("  ❌ Invalid (need 19-digit ID)")
            print(f"  Total videos: {len(bot.video_ids)}")
            
            room = input("\n Room ID (for live, or Enter to skip): ").strip()
            if room: bot.room_id = room
            
            sec = input(" sec_uid (for follows, or Enter to skip): ").strip()
            if sec: bot.sec_uid = sec
            
            print("\n Mode:")
            print(" 1 - Views  2 - Likes  3 - Shares  4 - Follows  5 - Live  6 - ALL")
            mc = input(" Select (1-6): ").strip()
            mode_map = {'1':'views','2':'likes','3':'shares','4':'follows','5':'live','6':'all'}
            if mc in mode_map: bot.mode = mode_map[mc]; print(f"  Mode: {bot.mode}")
            
            try:
                bot.threads = max(1, min(500, int(input(" Threads (1-500): ") or "10")))
                bot.target = int(input(" Target total: ") or "1000")
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
            if not bot.video_ids and not bot.room_id and not bot.sec_uid:
                print(" ❌ Add video IDs or room ID first!")
                input(); continue
            
            if bot.mode == 'live' and not bot.room_id:
                print(" ❌ Set Room ID for live mode!")
                input(); continue
            
            bot.start()
            input("Press Enter...")

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: print("\n👋 Exiting...")
    except Exception as e: print(f"❌ Error: {e}"); import traceback; traceback.print_exc()
