#!/usr/bin/env python3
"""
TIKTOK LIVE BOT - SignerPy ULTIMATE
Full proxy validation • Device management • Session tracking • Live stats
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
from datetime import datetime
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

# Global variables
devices = []  # Will be populated
DEFAULT_DEVICES = [
    {"device_id": "7528525775047132680", "install_id": "7528525992324908807", "openudid": "7a59d727a58ee91e", "cdid": "a90f0ed5-8028-413e-a00d-77e931779d00", "model": "SM-G998B", "session_id": ""},
    {"device_id": "7528525775047132681", "install_id": "7528525992324908808", "openudid": "8a59d727a58ee91f", "cdid": "b90f0ed5-8028-413e-a00d-77e931779d01", "model": "SM-A528B", "session_id": ""},
    {"device_id": "7528525775047132682", "install_id": "7528525992324908809", "openudid": "9a59d727a58ee91g", "cdid": "c90f0ed5-8028-413e-a00d-77e931779d02", "model": "Pixel 8", "session_id": ""},
    {"device_id": "7528525775047132683", "install_id": "7528525992324908810", "openudid": "0a59d727a58ee91h", "cdid": "d90f0ed5-8028-413e-a00d-77e931779d03", "model": "SM-F926B", "session_id": ""},
    {"device_id": "7528525775047132684", "install_id": "7528525992324908811", "openudid": "1a59d727a58ee91i", "cdid": "e90f0ed5-8028-413e-a00d-77e931779d04", "model": "SM-A136B", "session_id": ""},
]

proxy_lock = threading.Lock()
stats_lock = threading.Lock()
views = likes = shares = follows = errors = total_reqs = heartbeats = 0
running = False

# Session tracking
session_log = []
MAX_SESSION_LOG = 1000

# =============================================================================
# DEVICE MANAGEMENT
# =============================================================================

def generate_device():
    """Auto-generate a new device"""
    device_id = str(random.randint(10**18, 10**19-1))
    install_id = str(random.randint(10**18, 10**19-1))
    openudid = secrets.token_hex(8)
    cdid = str(uuid.uuid4())
    models = ["SM-G998B", "SM-A528B", "Pixel 8", "SM-F926B", "SM-A136B", "iPhone15,2", "SM-S908B", "SM-S901B"]
    return {
        "device_id": device_id,
        "install_id": install_id,
        "openudid": openudid,
        "cdid": cdid,
        "model": random.choice(models),
        "session_id": ""
    }

def load_devices_from_file(filename="devices.txt"):
    """Load devices from file (format: device_id:install_id:openudid:cdid:model)"""
    loaded = []
    try:
        with open(filename, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split(':')
                    if len(parts) >= 4:
                        loaded.append({
                            "device_id": parts[0],
                            "install_id": parts[1],
                            "openudid": parts[2],
                            "cdid": parts[3],
                            "model": parts[4] if len(parts) > 4 else "Unknown",
                            "session_id": parts[5] if len(parts) > 5 else ""
                        })
        print(f" ✅ Loaded {len(loaded)} devices from {filename}")
    except FileNotFoundError:
        print(f" ❌ {filename} not found")
    return loaded

def save_devices_to_file(devices_list, filename="devices.txt"):
    """Save devices to file"""
    with open(filename, 'w') as f:
        for d in devices_list:
            f.write(f"{d['device_id']}:{d['install_id']}:{d['openudid']}:{d['cdid']}:{d['model']}:{d.get('session_id', '')}\n")
    print(f" ✅ Saved {len(devices_list)} devices to {filename}")

def get_device_count():
    global devices
    return len(devices) if devices else len(DEFAULT_DEVICES)

def get_device(index=None):
    global devices
    if devices:
        return random.choice(devices) if index is None else devices[index % len(devices)]
    return random.choice(DEFAULT_DEVICES) if index is None else DEFAULT_DEVICES[index % len(DEFAULT_DEVICES)]

# =============================================================================
# SESSION TRACKING
# =============================================================================

def log_session(room_id, device_id, action, success):
    """Log a session action"""
    global session_log
    entry = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "room_id": room_id,
        "device_id": str(device_id)[-8:],
        "action": action,
        "success": "✅" if success else "❌"
    }
    session_log.append(entry)
    if len(session_log) > MAX_SESSION_LOG:
        session_log = session_log[-MAX_SESSION_LOG:]

# =============================================================================
# PARAMS GENERATOR
# =============================================================================

def make_base_params(device=None):
    if device is None:
        device = get_device()
    
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
        self.device = device or get_device()
        self.session = requests.Session()
        
        # Set proxy
        if proxy:
            proxy_url = f"http://{proxy}"
            self.session.proxies = {'http': proxy_url, 'https': proxy_url}
        
        # Set session ID from device if available
        self.session_id = self.device.get('session_id', '')
        cookies = {}
        if self.session_id:
            cookies['sessionid'] = self.session_id
            cookies['sessionid_ss'] = self.session_id
        
        self.session.headers.update({
            'User-Agent': f"com.zhiliaoapp.musically/2023708050 (Linux; U; Android 13; en_US; {self.device['model']}; Build/TP1A.220624.014;tt-ok/3.12.13.16)",
            'Connection': "Keep-Alive",
            'Accept-Encoding': "gzip, deflate",
            'Content-Type': "application/x-www-form-urlencoded; charset=UTF-8",
            'Accept': "application/json",
            'Cookie': '; '.join([f"{k}={v}" for k, v in cookies.items()]) if cookies else '',
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
                success = data.get('status_code') == 0
                if success and 'data' in data:
                    session_data = data.get('data', {})
                    if 'session_id' in session_data:
                        self.session_id = session_data['session_id']
                return success
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
# PROXY TESTER
# =============================================================================
class ProxyTester:
    @staticmethod
    def test_proxy_standard(proxy_str, test_url="http://httpbin.org/ip"):
        proxy_url = f"http://{proxy_str}"
        try:
            resp = requests.get(test_url, proxies={'http': proxy_url, 'https': proxy_url}, timeout=8, verify=False)
            return resp.status_code == 200, resp.elapsed.total_seconds()
        except: return False, 0
    
    @staticmethod
    def test_proxy_webcast(proxy_str):
        proxy_url = f"http://{proxy_str}"
        test_domain = random.choice(WEBCAST_DOMAINS)
        test_url = f"https://{test_domain}/webcast/room/enter/"
        params = {"aid": "1988", "room_id": "123456789012345678", "ts": str(int(time.time()))}
        try:
            resp = requests.get(test_url, params=params, proxies={'http': proxy_url, 'https': proxy_url}, timeout=8, verify=False)
            return resp.status_code in [200, 403, 429, 503], resp.elapsed.total_seconds()
        except: return False, 0
    
    @staticmethod
    def test_proxy_custom(proxy_str, custom_url):
        proxy_url = f"http://{proxy_str}"
        try:
            resp = requests.get(custom_url, proxies={'http': proxy_url, 'https': proxy_url}, timeout=8, verify=False)
            return resp.status_code == 200, resp.elapsed.total_seconds()
        except: return False, 0
    
    @staticmethod
    def get_test_quantity(total_proxies):
        print(f"\n📊 Total proxies available: {total_proxies}")
        print(" How many to test?")
        print("   [Enter] = 200 (standard)")
        print("   [A] = All proxies")
        print("   [N] = Custom number")
        choice = input(" Select: ").strip().lower()
        if choice == 'a' or choice == 'all': return total_proxies
        elif choice == '': return min(200, total_proxies)
        else:
            try: return max(1, min(int(choice), total_proxies))
            except: return min(200, total_proxies)
    
    @staticmethod
    def get_test_method():
        print("\n🔬 Proxy Test Method:")
        print(" [1] Standard (httpbin.org)")
        print(" [2] TikTok Webcast")
        print(" [3] Custom URL")
        print(" [4] All methods")
        choice = input(" Select: ").strip()
        return choice
    
    @staticmethod
    def get_proxy_type():
        print("\n🌐 Proxy Type:")
        print(" [1] HTTP")
        print(" [2] HTTPS")
        print(" [3] SOCKS4")
        print(" [4] SOCKS5")
        choice = input(" Select: ").strip()
        types = {'1': 'http', '2': 'https', '3': 'socks4', '4': 'socks5'}
        return types.get(choice, 'http')
    
    @staticmethod
    def test_batch(proxies, test_method='1', proxy_type='http', custom_url=None, max_workers=50):
        if not proxies:
            print(" ❌ No proxies to test")
            return []
        
        test_count = ProxyTester.get_test_quantity(len(proxies))
        test_proxies = proxies[:test_count]
        
        working = []
        print(f"\n🔬 Testing {len(test_proxies)} proxies (method: {test_method}, type: {proxy_type})...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for p in test_proxies:
                if test_method == '1':
                    futures[executor.submit(ProxyTester.test_proxy_standard, p)] = p
                elif test_method == '2':
                    futures[executor.submit(ProxyTester.test_proxy_webcast, p)] = p
                elif test_method == '3' and custom_url:
                    futures[executor.submit(ProxyTester.test_proxy_custom, p, custom_url)] = p
                elif test_method == '4':
                    futures[executor.submit(ProxyTester.test_proxy_standard, p)] = ('standard', p)
                    futures[executor.submit(ProxyTester.test_proxy_webcast, p)] = ('webcast', p)
                else:
                    futures[executor.submit(ProxyTester.test_proxy_standard, p)] = p
            
            completed = 0
            proxy_results = {}
            
            for future in as_completed(futures):
                result = futures[future]
                completed += 1
                
                if test_method == '4':
                    # For "all methods", need both standard AND webcast to pass
                    test_type = result[0]
                    proxy_str = result[1]
                    success, latency = future.result()
                    
                    if proxy_str not in proxy_results:
                        proxy_results[proxy_str] = {'standard': False, 'webcast': False}
                    proxy_results[proxy_str][test_type] = success
                    
                    if proxy_results[proxy_str]['standard'] and proxy_results[proxy_str]['webcast']:
                        if proxy_str not in working:
                            working.append(proxy_str)
                else:
                    proxy_str = result
                    success, latency = future.result()
                    if success and proxy_str not in working:
                        working.append(proxy_str)
                
                if completed % 25 == 0 or completed == len(futures):
                    print(f"\r⏳ [{completed}/{len(futures)}] Working: {len(working)}", end='')
        
        print(f"\n✅ {len(working)}/{len(test_proxies)} proxies working")
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
        self.use_devices_from_file = False
        self.show_live_sessions = True
    
    def worker(self):
        global views, likes, shares, follows, errors, total_reqs, heartbeats, running, session_log
        while running:
            try:
                proxy = random.choice(self.proxies) if self.proxies else None
                device = get_device()
                worker = TikTokLiveWorker(self.room_id, proxy, device)
                
                if worker.enter_room():
                    with stats_lock:
                        views += 1
                        total_reqs += 1
                    log_session(self.room_id, device['device_id'], "ENTER", True)
                    
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
                                log_session(self.room_id, device['device_id'], "LIKE", True)
                        
                        if self.mode in ['shares', 'all'] and random.random() < 0.3:
                            if worker.send_share():
                                with stats_lock:
                                    shares += 1
                                    total_reqs += 1
                                log_session(self.room_id, device['device_id'], "SHARE", True)
                        
                        if self.mode in ['follows', 'all'] and random.random() < 0.1 and self.sec_uid:
                            if worker.send_follow(self.sec_uid):
                                with stats_lock:
                                    follows += 1
                                    total_reqs += 1
                                log_session(self.room_id, device['device_id'], "FOLLOW", True)
                        
                        time.sleep(random.uniform(1.5, 3.5))
                else:
                    with stats_lock: errors += 1
                    log_session(self.room_id, device['device_id'], "ENTER", False)
                    
            except Exception as e:
                with stats_lock: errors += 1
                log_session(self.room_id, "unknown", "ERROR", False)
            
            time.sleep(random.uniform(0.5, 1.5))
    
    def start(self):
        global running
        running = True
        
        print(f"\n🚀 LIVE BOT STARTED | Mode: {self.mode.upper()}")
        print(f"   Room ID: {self.room_id}")
        print(f"   Threads: {self.threads} | Target: {self.target} | Proxies: {len(self.proxies)}")
        print(f"   Devices: {get_device_count()}")
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
║     TIKTOK LIVE BOT - SignerPy ULTIMATE                     ║
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
                print(f" 📱 Devices:   {get_device_count()}")
                print(f" {'─'*55}")
                
                # Show live sessions
                if self.show_live_sessions and session_log:
                    print(f" 📋 RECENT SESSIONS (last {min(10, len(session_log))}):")
                    print(f" {'─'*55}")
                    for entry in session_log[-10:]:
                        print(f"    {entry['time']} | {entry['device_id']} | {entry['action']:>7} | {entry['success']}")
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
# DEVICE MENU
# =============================================================================

def device_menu(bot):
    global devices
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("""
╔══════════════════════════════════════════════════════════════╗
║                    DEVICE MANAGEMENT                         ║
╚══════════════════════════════════════════════════════════════╝
        """)
        print(f" Current devices: {get_device_count()}")
        if devices:
            print(f"   (loaded from file or generated)")
        else:
            print(f"   (using {len(DEFAULT_DEVICES)} built-in devices)")
        print(f" Auto-generate on start: {'✅' if not bot.use_devices_from_file else '❌'}")
        print()
        print(" [1] Auto-generate N devices")
        print(" [2] Load devices from file")
        print(" [3] Save current devices to file")
        print(" [4] Show device list")
        print(" [5] Toggle auto-generate / file mode")
        print(" [0] Back\n")
        
        choice = input(" Select: ").strip()
        
        if choice == '0': break
        elif choice == '1':
            try:
                n = int(input(" How many devices to generate? ") or "50")
                new_devices = [generate_device() for _ in range(n)]
                devices = new_devices
                print(f" ✅ Generated {n} devices")
            except: print(" ❌ Invalid number")
            input("Press Enter...")
        elif choice == '2':
            filename = input(" Filename (default: devices.txt): ").strip() or "devices.txt"
            loaded = load_devices_from_file(filename)
            if loaded:
                devices = loaded
                bot.use_devices_from_file = True
            input("Press Enter...")
        elif choice == '3':
            if devices:
                filename = input(" Filename (default: devices.txt): ").strip() or "devices.txt"
                save_devices_to_file(devices, filename)
            else:
                print(" ❌ No devices to save (generate first)")
            input("Press Enter...")
        elif choice == '4':
            print(f"\n 📱 DEVICE LIST ({get_device_count()} devices):")
            print(f" {'─'*65}")
            all_devs = devices if devices else DEFAULT_DEVICES
            for i, d in enumerate(all_devs[:20]):
                print(f"  {i+1:>3}. {d['device_id'][:12]}... | {d['model']:>12} | session: {d.get('session_id', 'N/A')[:12]}...")
            if len(all_devs) > 20:
                print(f"  ... and {len(all_devs) - 20} more")
            print(f" {'─'*65}")
            input("Press Enter...")
        elif choice == '5':
            bot.use_devices_from_file = not bot.use_devices_from_file
            if bot.use_devices_from_file:
                print(" ✅ Mode: Load devices from file")
            else:
                print(" ✅ Mode: Auto-generate devices")
            input("Press Enter...")

# =============================================================================
# MAIN
# =============================================================================

def main():
    global devices  # <-- THIS IS THE FIX! Declare global
    os.system('cls' if os.name == 'nt' else 'clear')
    bot = TikTokLiveBot()
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║  TIKTOK LIVE BOT - SignerPy ULTIMATE EDITION                ║
║                                                              ║
║  ✓ Live Views  ✓ Live Likes  ✓ Live Shares  ✓ Follows       ║
║  ✓ Proxy Validation (Standard/Webcast/Custom)               ║
║  ✓ Device Management (Auto-gen/File)                        ║
║  ✓ Session Tracking & Live Dashboard                        ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    while True:
        print("\n📋 MAIN MENU:")
        print(" [0] ⚙️  Setup (Room ID, Mode, Target)")
        print(" [1] 🌐 Proxy Manager (Scrape/Test/Load)")
        print(" [2] 📱 Device Manager")
        print(" [3] 🚀 Start Bot") 
        print(" [4] 📊 Session Log")
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
            
            ls = input(" Show live sessions in dashboard? (y/n): ").strip().lower()
            bot.show_live_sessions = ls != 'n'
            
            input("Press Enter...")
        
        elif choice == '1':
            while True:
                os.system('cls' if os.name == 'nt' else 'clear')
                print("\n🌐 PROXY MANAGER:")
                print(f"   Working proxies: {len(bot.proxies)}")
                print(" [1] Scrape HTTP proxies")
                print(" [2] Test proxies (from file or scraped)")
                print(" [3] Load working proxies from file")
                print(" [4] Clear proxy pool")
                print(" [0] Back\n")
                
                pc = input(" Select: ").strip()
                
                if pc == '0': break
                elif pc == '1':
                    proxies = ProxyScraper.scrape()
                    print(f"\n🌐 Scraped {len(proxies)} HTTP proxies")
                    if proxies:
                        save = input(f" Save to file? (y/n): ").strip().lower()
                        if save == 'y':
                            with open('proxies_scraped.txt', 'w') as f:
                                for p in proxies:
                                    f.write(p + '\n')
                            print(f" ✅ Saved to proxies_scraped.txt")
                        
                        test = input(" Test them now? (y/n): ").strip().lower()
                        if test == 'y':
                            test_method = ProxyTester.get_test_method()
                            proxy_type = ProxyTester.get_proxy_type()
                            custom_url = None
                            if test_method == '3':
                                custom_url = input(" Custom URL to test against: ").strip()
                            bot.proxies = ProxyTester.test_batch(proxies, test_method, proxy_type, custom_url)
                    input("Press Enter...")
                
                elif pc == '2':
                    filename = input(" Filename (default: proxies_scraped.txt): ").strip() or "proxies_scraped.txt"
                    try:
                        with open(filename, 'r') as f:
                            proxies = [l.strip() for l in f if ':' in l.strip()]
                        print(f" Loaded {len(proxies)} proxies")
                        
                        test_method = ProxyTester.get_test_method()
                        proxy_type = ProxyTester.get_proxy_type()
                        custom_url = None
                        if test_method == '3':
                            custom_url = input(" Custom URL to test against: ").strip()
                        
                        bot.proxies = ProxyTester.test_batch(proxies, test_method, proxy_type, custom_url)
                        
                        if bot.proxies:
                            with open('proxies_working.txt', 'w') as f:
                                for p in bot.proxies:
                                    f.write(p + '\n')
                            print(f" ✅ Saved {len(bot.proxies)} working to proxies_working.txt")
                    except FileNotFoundError:
                        print(f" ❌ File not found!")
                    input("Press Enter...")
                
                elif pc == '3':
                    try:
                        with open('proxies_working.txt', 'r') as f:
                            bot.proxies = [l.strip() for l in f if ':' in l.strip()]
                        print(f" ✅ Loaded {len(bot.proxies)} working proxies")
                    except:
                        print(" ❌ No proxies_working.txt found")
                    input("Press Enter...")
                
                elif pc == '4':
                    bot.proxies = []
                    print(" ✅ Proxy pool cleared")
                    input("Press Enter...")
        
        elif choice == '2':
            device_menu(bot)
        
        elif choice == '3':
            if not bot.room_id:
                print(" ❌ Set Room ID first! (Option 0)")
                input(); continue
            
            # Auto-generate devices if needed
            if not devices and not bot.use_devices_from_file:
                print("\n 🔄 Auto-generating 50 devices...")
                devices = [generate_device() for _ in range(50)]
                print(f" ✅ Generated {len(devices)} devices")
            
            bot.start()
            input("Press Enter...")
        
        elif choice == '4':
            os.system('cls' if os.name == 'nt' else 'clear')
            print("\n📋 SESSION LOG:")
            print(f" {'─'*65}")
            if session_log:
                for entry in session_log[-30:]:
                    print(f"  {entry['time']} | Device: {entry['device_id']} | {entry['action']:>7} | {entry['success']} | Room: {entry['room_id'][:12]}...")
            else:
                print("  No sessions recorded yet")
            print(f" {'─'*65}")
            print(f" Total sessions logged: {len(session_log)}")
            input("\nPress Enter...")

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: print("\n👋 Exiting...")
    except Exception as e: print(f"❌ Error: {e}"); import traceback; traceback.print_exc()
