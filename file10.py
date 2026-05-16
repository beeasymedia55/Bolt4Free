#!/usr/bin/env python3
"""
TIKTOK LIVE ONLY BOT - SignerPy
Views, Likes, Shares, Follows for LIVE streams only
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
    "webcast-sg.tiktokv.com", "webcast-sea1.tiktokv.com"
]

DEVICES = [
    {"device_id": "7528525775047132680", "install_id": "7528525992324908807", "openudid": "7a59d727a58ee91e", "cdid": "a90f0ed5-8028-413e-a00d-77e931779d00", "model": "SM-G998B"},
    {"device_id": "7528525775047132681", "install_id": "7528525992324908808", "openudid": "8a59d727a58ee91f", "cdid": "b90f0ed5-8028-413e-a00d-77e931779d01", "model": "SM-A528B"},
    {"device_id": "7528525775047132682", "install_id": "7528525992324908809", "openudid": "9a59d727a58ee91g", "cdid": "c90f0ed5-8028-413e-a00d-77e931779d02", "model": "Pixel 8"},
    {"device_id": "7528525775047132683", "install_id": "7528525992324908810", "openudid": "0a59d727a58ee91h", "cdid": "d90f0ed5-8028-413e-a00d-77e931779d03", "model": "SM-F926B"},
    {"device_id": "7528525775047132684", "install_id": "7528525992324908811", "openudid": "1a59d727a58ee91i", "cdid": "e90f0ed5-8028-413e-a00d-77e931779d04", "model": "SM-A136B"},
]

proxy_pool = []
proxy_lock = threading.Lock()

stats_lock = threading.Lock()
views = likes = shares = follows = errors = total_reqs = heartbeats = 0
running = False

# =============================================================================
# PARAMS GENERATOR - LIVE STREAM ONLY
# =============================================================================

def make_base_params(device=None):
    if device is None:
        device = random.choice(DEVICES)
    
    return {
        "aid": "1988",
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

def make_live_enter_params(room_id, device=None):
    params, dev = make_base_params(device)
    params.update({
        "room_id": room_id,
        "live_id": str(random.randint(10**17, 10**18-1)),
        "enter_source": random.choice(["feed", "profile", "search", "related"]),
        "is_login": "1",
        "type": "live",
    })
    return params, dev

def make_live_like_params(room_id, device=None):
    params, dev = make_base_params(device)
    params.update({
        "room_id": room_id,
        "like_count": str(random.randint(1, 5)),
        "live_id": str(random.randint(10**17, 10**18-1)),
        "type": "aweme",
    })
    return params, dev

def make_live_share_params(room_id, device=None):
    params, dev = make_base_params(device)
    params.update({
        "room_id": room_id,
        "share_type": random.choice(["1", "2", "3"]),
        "share_delta": "1",
        "live_id": str(random.randint(10**17, 10**18-1)),
    })
    return params, dev

def make_live_heartbeat_params(room_id, device=None):
    params, dev = make_base_params(device)
    params.update({
        "room_id": room_id,
        "live_id": str(random.randint(10**17, 10**18-1)),
        "heartbeat_duration": str(random.randint(3000, 8000)),
        "type": "1",
    })
    return params, dev

def make_follow_params(sec_uid, device=None):
    params, dev = make_base_params(device)
    params.update({
        "to_user_id": sec_uid,
        "status": "1",
        "type": "aweme",
        "from": "profile",
    })
    return params, dev

# =============================================================================
# SIGNERPY WRAPPER
# =============================================================================
def sign_request(params: dict, payload: dict = None, cookies: dict = None):
    if payload is None:
        payload = {}
    if cookies is None:
        cookies = {}
    m = SignerPy.sign(params=params, payload=payload, cookie=cookies)
    return m

# =============================================================================
# TIKTOK LIVE WORKER
# =============================================================================

class TikTokLiveWorker:
    def __init__(self, room_id, proxy=None, device=None):
        self.room_id = room_id
        self.proxy = proxy
        self.device = device or random.choice(DEVICES)
        self.session = requests.Session()
        if proxy:
            proxy_url = f"http://{proxy}"
            self.session.proxies = {'http': proxy_url, 'https': proxy_url}
        self.session.headers.update({
            'User-Agent': f"com.zhiliaoapp.musically/2023708050 (Linux; U; Android 13; en_US; {self.device['model']}; Build/TP1A.220624.014;tt-ok/3.12.13.16)",
            'Connection': "Keep-Alive",
            'Accept-Encoding': "gzip, deflate",
            'Content-Type': "application/x-www-form-urlencoded; charset=UTF-8",
            'Accept': "application/json",
        })
    
    def _make_request(self, endpoint, params, payload=None):
        domain = random.choice(WEBCAST_DOMAINS)
        url = f"https://{domain}{endpoint}"
        
        if payload:
            m = SignerPy.sign(params=params, payload=payload)
        else:
            m = SignerPy.sign(params=params, payload={})
        
        self.session.headers.update({
            'Host': domain,
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
    
    def enter_room(self):
        params, _ = make_live_enter_params(self.room_id, self.device)
        payload = f"room_id={self.room_id}&live_id={params['live_id']}&enter_source={params['enter_source']}&is_login=1"
        resp = self._make_request('/webcast/room/enter/', params, payload)
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                return data.get('status_code') == 0
            except:
                pass
        return False
    
    def send_like(self):
        params, _ = make_live_like_params(self.room_id, self.device)
        payload = f"room_id={self.room_id}&like_count={params['like_count']}&live_id={params['live_id']}"
        resp = self._make_request('/webcast/like/', params, payload)
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                return data.get('status_code') == 0
            except:
                pass
        return False
    
    def send_share(self):
        params, _ = make_live_share_params(self.room_id, self.device)
        payload = f"room_id={self.room_id}&share_type={params['share_type']}&share_delta=1&live_id={params['live_id']}"
        resp = self._make_request('/webcast/share/', params, payload)
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                return data.get('status_code') == 0
            except:
                pass
        return False
    
    def send_heartbeat(self):
        params, _ = make_live_heartbeat_params(self.room_id, self.device)
        payload = f"room_id={self.room_id}&live_id={params['live_id']}&heartbeat_duration={params['heartbeat_duration']}&type=1"
        resp = self._make_request('/webcast/heartbeat/', params, payload)
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                return data.get('status_code') == 0
            except:
                pass
        return False
    
    def send_follow(self, sec_uid):
        params, _ = make_follow_params(sec_uid, self.device)
        payload = f"to_user_id={sec_uid}&status=1"
        resp = self._make_request('/aweme/v1/commit/follow/user/', params, payload)
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                return data.get('status_code') == 0
            except:
                pass
        return False

# =============================================================================
# PROXY TESTER - WITH QUANTITY SELECTION
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
    def get_test_quantity(total_proxies):
        """Ask user how many proxies to test"""
        print(f"\n📊 Total proxies available: {total_proxies}")
        print(" How many do you want to test?")
        print("   [Enter] = 200 (standard)")
        print("   [A] = All proxies")
        print("   [N] = Enter custom number")
        
        choice = input(" Select: ").strip().lower()
        
        if choice == 'a' or choice == 'all':
            return total_proxies
        elif choice == '':
            return min(200, total_proxies)
        else:
            try:
                num = int(choice)
                return max(1, min(num, total_proxies))
            except:
                return min(200, total_proxies)
    
    @staticmethod
    def test_batch(proxies, max_workers=50):
        """Test proxies - asks how many to test first"""
        if not proxies:
            print(" ❌ No proxies to test")
            return []
        
        # Ask how many to test
        test_count = ProxyTester.get_test_quantity(len(proxies))
        test_proxies = proxies[:test_count]
        
        working = []
        print(f"\n🔬 Testing {len(test_proxies)} proxies...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(ProxyTester.test_proxy, p): p for p in test_proxies}
            completed = 0
            for future in as_completed(futures):
                if future.result():
                    working.append(futures[future])
                completed += 1
                if completed % 50 == 0 or completed == len(test_proxies):
                    print(f"\r⏳ [{completed}/{len(test_proxies)}] Working: {len(working)}", end='')
        
        print(f"\n✅ {len(working)} working proxies found")
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

class TikTokLiveBot:
    def __init__(self):
        self.room_id = ""
        self.sec_uid = ""
        self.mode = "views"
        self.threads = 10
        self.target = 1000
        self.proxies = []
    
    def worker(self):
        global views, likes, shares, follows, errors, total_reqs, heartbeats, running
        while running:
            try:
                proxy = random.choice(self.proxies) if self.proxies else None
                device = random.choice(DEVICES)
                worker = TikTokLiveWorker(self.room_id, proxy, device)
                
                if worker.enter_room():
                    with stats_lock:
                        views += 1
                        total_reqs += 1
                    
                    for cycle in range(random.randint(3, 10)):
                        if not running: break
                        
                        if worker.send_heartbeat():
                            with stats_lock:
                                heartbeats += 1
                                total_reqs += 1
                        
                        if self.mode in ['likes', 'all']:
                            if worker.send_like():
                                with stats_lock:
                                    likes += 1
                                    total_reqs += 1
                        
                        if self.mode in ['shares', 'all'] and random.random() < 0.3:
                            if worker.send_share():
                                with stats_lock:
                                    shares += 1
                                    total_reqs += 1
                        
                        if self.mode in ['follows', 'all'] and random.random() < 0.1 and self.sec_uid:
                            if worker.send_follow(self.sec_uid):
                                with stats_lock:
                                    follows += 1
                                    total_reqs += 1
                        
                        time.sleep(random.uniform(1.5, 3.5))
                else:
                    with stats_lock: errors += 1
                    
            except Exception as e:
                with stats_lock: errors += 1
            
            time.sleep(random.uniform(0.5, 1.5))
    
    def start(self):
        global running
        running = True
        
        print(f"\n🚀 LIVE BOT STARTED | Mode: {self.mode.upper()}")
        print(f"   Room ID: {self.room_id}")
        print(f"   Threads: {self.threads} | Target: {self.target} | Proxies: {len(self.proxies)}")
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
║          TIKTOK LIVE BOT - SignerPy PRODUCTION              ║
╚══════════════════════════════════════════════════════════════╝
                """)
                print(f" 🔐 SignerPy: ✅ ACTIVE")
                print(f" {'─'*55}")
                print(f" 🎯 Mode:     {self.mode.upper():<10}")
                print(f" 🔴 Room ID:  {self.room_id}")
                print(f" 🕒 Uptime:   {int(elapsed//3600):02d}:{int((elapsed%3600)//60):02d}:{int(elapsed%60):02d}")
                print(f" {'─'*55}")
                print(f" 👁️  Views:     {views:>7,}")
                print(f" ❤️  Likes:     {likes:>7,}")
                print(f" 🔗 Shares:    {shares:>7,}")
                print(f" 👤 Follows:   {follows:>7,}")
                print(f" 💓 Heartbeats: {heartbeats:>6,}")
                print(f" ❌ Errors:    {errors:>7,}")
                print(f" {'─'*55}")
                print(f" 📊 Total:     {total_reqs:>7,}")
                if elapsed > 0:
                    print(f" ⚡ Rate:      {total_reqs/elapsed:>5.0f} req/s")
                print(f" 🧵 Threads:   {self.threads}")
                print(f" 🌐 Proxies:   {len(self.proxies)}")
                print(f" {'─'*55}")
                print(f" Press Ctrl+C to stop")
                
                if views >= self.target:
                    print(f"\n✅ TARGET REACHED! {views} views")
                    running = False
                    break
                    
        except KeyboardInterrupt:
            running = False
            print(f"\n🛑 STOPPED")
            print(f"   Views: {views} | Likes: {likes} | Shares: {shares} | Follows: {follows}")
            print(f"   Heartbeats: {heartbeats} | Errors: {errors}")

# =============================================================================
# MAIN
# =============================================================================

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    bot = TikTokLiveBot()
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║     TIKTOK LIVE BOT - SignerPy PRODUCTION                   ║
║                                                              ║
║  ✓ Live Views  ✓ Live Likes  ✓ Live Shares  ✓ Follows       ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    while True:
        print("\n📋 MAIN MENU:")
        print(" [0] ⚙️  Setup (Room ID, Mode, Target)")
        print(" [1] 🌐 Proxy Manager")
        print(" [2] 🚀 Start Bot") 
        print(" [Q] Quit\n")
        
        choice = input(" Select: ").strip().upper()
        
        if choice == 'Q':
            print("👋 Bye!"); break
        
        elif choice == '0':
            room = input(" Live Room ID: ").strip()
            if room.isdigit() and len(room) >= 15:
                bot.room_id = room
                print(f" ✅ Room set: {room}")
            else:
                print(" ❌ Invalid room ID (need 15+ digits)")
            
            sec = input(" sec_uid (for follows, Enter to skip): ").strip()
            if sec:
                bot.sec_uid = sec
                print(f" ✅ sec_uid set")
            
            print("\n Mode:")
            print(" 1 - Views only")
            print(" 2 - Likes only")
            print(" 3 - Shares only")
            print(" 4 - Follows only")
            print(" 5 - ALL (Views + Likes + Shares + Follows)")
            mc = input(" Select (1-5): ").strip()
            mode_map = {'1':'views','2':'likes','3':'shares','4':'follows','5':'all'}
            if mc in mode_map:
                bot.mode = mode_map[mc]
                print(f" ✅ Mode: {bot.mode}")
            
            try:
                bot.threads = max(1, min(500, int(input(" Threads (1-500): ") or "10")))
                bot.target = int(input(" Target views: ") or "1000")
            except: pass
            input("Press Enter...")
        
        elif choice == '1':
            print("\n🌐 PROXY MANAGER:")
            print(" [1] Scrape HTTP proxies")
            print(" [2] Load & test from file")
            print(" [3] Load working proxies")
            print(" [0] Back\n")
            
            pc = input(" Select: ").strip()
            
            if pc == '1':
                proxies = ProxyScraper.scrape()
                print(f"\n🌐 Scraped {len(proxies)} HTTP proxies")
                
                if proxies:
                    test = input("\n Test proxies? (y/n): ").strip().lower()
                    if test == 'y':
                        bot.proxies = ProxyTester.test_batch(proxies)
                        if bot.proxies:
                            save = input(f"\n Save {len(bot.proxies)} working proxies to file? (y/n): ").strip().lower()
                            if save == 'y':
                                with open('proxies_working.txt', 'w') as f:
                                    for p in bot.proxies:
                                        f.write(p + '\n')
                                print(f" ✅ Saved to proxies_working.txt")
                    else:
                        # If not testing, offer to save all scraped
                        save = input(f" Save all {len(proxies)} to file? (y/n): ").strip().lower()
                        if save == 'y':
                            with open('proxies_scraped.txt', 'w') as f:
                                for p in proxies:
                                    f.write(p + '\n')
                            print(f" ✅ Saved to proxies_scraped.txt")
                else:
                    print(" ❌ No proxies scraped")
                
                input("Press Enter...")
            
            elif pc == '2':
                filename = input(" Filename (default: proxies_scraped.txt): ").strip() or "proxies_scraped.txt"
                try:
                    with open(filename, 'r') as f:
                        proxies = [l.strip() for l in f if ':' in l.strip()]
                    print(f" Loaded {len(proxies)} proxies from {filename}")
                    
                    if proxies:
                        bot.proxies = ProxyTester.test_batch(proxies)
                        if bot.proxies:
                            with open('proxies_working.txt', 'w') as f:
                                for p in bot.proxies:
                                    f.write(p + '\n')
                            print(f" ✅ Saved {len(bot.proxies)} working to proxies_working.txt")
                except FileNotFoundError:
                    print(f" ❌ File {filename} not found!")
                input("Press Enter...")
            
            elif pc == '3':
                try:
                    with open('proxies_working.txt', 'r') as f:
                        bot.proxies = [l.strip() for l in f if ':' in l.strip()]
                    print(f" ✅ Loaded {len(bot.proxies)} working proxies")
                except:
                    print(" ❌ No proxies_working.txt found")
                input("Press Enter...")

        
        elif choice == '2':
            if not bot.room_id:
                print(" ❌ Set Room ID first! (Option 0)")
                input(); continue
            
            bot.start()
            input("Press Enter...")

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: print("\n👋 Exiting...")
    except Exception as e: print(f"❌ Error: {e}"); import traceback; traceback.print_exc()
