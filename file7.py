#!/usr/bin/env python3
"""
TIKTOK LIVE BOT v6.0 - SignerPy PRODUCTION
SignerPy import at top for ALL signature generation
"""

# =============================================================================
# SignerPy IMPORT - ABSOLUTE TOP FOR SIGNATURE GENERATION
# =============================================================================
import SignerPy
from SignerPy import XBogusSigner, GorgonSigner, Signer

# Verify SignerPy loaded successfully
try:
    SIGNERPY_VERSION = signerpy.__version__
    print(f"✅ SignerPy v{SIGNERPY_VERSION} loaded - Ready for signature generation")
except AttributeError:
    SIGNERPY_VERSION = "unknown"
    print(f"✅ SignerPy loaded - Ready for signature generation")

SIGNERPY_AVAILABLE = True

# =============================================================================
# STANDARD LIBRARY IMPORTS
# =============================================================================
import os, sys, ssl, time, random, threading, requests, hashlib, json, uuid, secrets, re
from urllib.parse import urlencode, quote
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

requests.packages.urllib3.disable_warnings()
ssl._create_default_https_context = ssl._create_unverified_context

# =============================================================================
# CONFIGURATION
# =============================================================================
WEBCAST_DOMAINS = [
    "webcast-h2.tiktokv.com", "webcast.tiktokv.com",
    "webcast-hl.tiktokv.com", "webcast-va.tiktokv.com",
    "webcast-sg.tiktokv.com", "webcast-sea1.tiktokv.com"
]

API_DOMAINS = [
    "api-h2.tiktokv.com", "api22-core-c-useast1a.tiktokv.com",
    "api19-core-c-useast1a.tiktokv.com", "api21-core-c-useast1a.tiktokv.com"
]

DEVICE_PROFILES = [
    {'device_id': '1234567890123456789', 'install_id': '9876543210987654321', 'cdid': 'cdid1234567890abcdef', 'openudid': 'openudid1234567890abcdef', 'model': 'SM-G998B', 'brand': 'samsung', 'os': 'Android', 'os_version': '14', 'os_api': '34'},
    {'device_id': '2345678901234567890', 'install_id': '8765432109876543210', 'cdid': 'cdid2345678901abcdef', 'openudid': 'openudid2345678901abcdef', 'model': 'Pixel 8 Pro', 'brand': 'google', 'os': 'Android', 'os_version': '14', 'os_api': '34'},
    {'device_id': '3456789012345678901', 'install_id': '7654321098765432109', 'cdid': 'cdid3456789012abcdef', 'openudid': 'openudid3456789012abcdef', 'model': 'SM-A528B', 'brand': 'samsung', 'os': 'Android', 'os_version': '13', 'os_api': '33'},
    {'device_id': '4567890123456789012', 'install_id': '6543210987654321098', 'cdid': 'cdid4567890123abcdef', 'openudid': 'openudid4567890123abcdef', 'model': 'iPhone15,2', 'brand': 'apple', 'os': 'iOS', 'os_version': '17.4', 'os_api': '1704'},
    {'device_id': '5678901234567890123', 'install_id': '5432109876543210987', 'cdid': 'cdid5678901234abcdef', 'openudid': 'openudid5678901234abcdef', 'model': 'SM-F926B', 'brand': 'samsung', 'os': 'Android', 'os_version': '12', 'os_api': '32'},
]

proxy_pool = []
proxy_lock = threading.Lock()

# =============================================================================
# SignerPy SIGNATURE GENERATOR - Uses the imported SignerPy library
# =============================================================================

class SignerPyGenerator:
    """
    TikTok signature generator using SignerPy library
    - XBogusSigner for X-Bogus header (v26+ required)
    - GorgonSigner for X-Gorgon header  
    - Signer for full signature generation
    """
    
    def __init__(self):
        self.xbogus = XBogusSigner()
        self.gorgon = GorgonSigner()
        self.full = Signer()
        self.initialized = True
        print(f"🔐 SignerPy v{SIGNERPY_VERSION}: XBogusSigner + GorgonSigner + Signer ready")
    
    def sign_xbogus(self, params_dict, user_agent="", cookies=""):
        """Generate X-Bogus using SignerPy's XBogusSigner"""
        params_str = urlencode(sorted(params_dict.items()))
        return self.xbogus.sign(params_str, user_agent)
    
    def sign_gorgon(self, params_dict, cookies=None, data=None, unix=None):
        """Generate X-Gorgon using SignerPy's GorgonSigner"""
        unix = unix or int(time.time())
        params_str = urlencode(sorted(params_dict.items()))
        return self.gorgon.sign(params_str, cookies, data, unix)
    
    def sign_full(self, params_dict, headers_dict=None):
        """Generate complete signature set using SignerPy's Signer"""
        return self.full.sign(params_dict, headers_dict)

# =============================================================================
# Instantiate SignerPy generator GLOBALLY
# =============================================================================
signer = SignerPyGenerator()

# =============================================================================
# HEADER GENERATOR - Uses SignerPy for ALL signatures
# =============================================================================

class HeaderGenerator:
    """Generate TikTok headers with SignerPy signatures"""
    
    def __init__(self):
        self.app_versions = ["27.2.4", "27.1.3", "27.0.2", "26.9.1"]
        self.version_codes = ["270204", "270103", "270002", "260901"]
        self.manifest_versions = ["2024010100", "2023120100", "2023110100"]
        self.sdk_versions = ["3.12.13", "3.12.12", "3.12.11"]
    
    def generate(self, device_profile=None, extra_params=None):
        """Generate COMPLETE headers with SignerPy signatures"""
        if device_profile is None:
            device_profile = random.choice(DEVICE_PROFILES)
        
        app_version = random.choice(self.app_versions)
        manifest_version = random.choice(self.manifest_versions)
        sdk_version = random.choice(self.sdk_versions)
        
        if device_profile['os'] == 'iOS':
            user_agent = f"com.zhiliaoapp.musically/{manifest_version} (iPhone; iOS {device_profile['os_version']}; en_US; {device_profile['model']}; tt-ok/{sdk_version})"
        else:
            user_agent = f"com.zhiliaoapp.musically/{manifest_version} (Linux; U; Android {device_profile['os_version']}; en_US; {device_profile['model']}; Build/TP1A.220624.014; tt-ok/{sdk_version})"
        
        headers = {
            'User-Agent': user_agent,
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Cookie': f"sessionid={secrets.token_hex(24)}; install_id={str(random.randint(10**18, 10**19-1))}; odin_tt={secrets.token_hex(16)}; ttreq={secrets.token_hex(8)}",
            'X-Requested-With': 'XMLHttpRequest',
            'X-SS-REQ-TICKET': secrets.token_hex(16),
            'X-TT-Device-ID': device_profile['device_id'],
            'X-TT-Install-ID': device_profile['install_id'],
            'X-TT-Login-Status': '1',
            'X-TT-Webcast-SDK-Version': random.choice(['3.0.0', '3.1.0', '3.2.0']),
            'Origin': 'https://www.tiktok.com',
            'Referer': 'https://www.tiktok.com/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'Connection': 'keep-alive',
        }
        
        # USE SignerPy FOR SIGNATURES
        if extra_params:
            sigs = signer.sign_full(extra_params, headers)
            headers['X-Bogus'] = sigs.get('X-Bogus', '')
            headers['X-Gorgon'] = sigs.get('X-Gorgon', '')
            headers['X-Khronos'] = sigs.get('X-Khronos', str(int(time.time())))
        else:
            headers['X-Bogus'] = signer.sign_xbogus({}, user_agent)
            headers['X-Gorgon'] = signer.sign_gorgon({})
            headers['X-Khronos'] = str(int(time.time()))
        
        return headers, device_profile

header_gen = HeaderGenerator()

# =============================================================================
# PROXY TESTER
# =============================================================================

class ProxyTester:
    @staticmethod
    def test_against_webcast(proxy_url, timeout=8):
        test_domain = random.choice(WEBCAST_DOMAINS)
        test_url = f"https://{test_domain}/webcast/room/enter/"
        test_params = {
            'aid': '1988',
            'app_name': 'musically_go',
            'device_id': str(random.randint(10**18, 10**19-1)),
            'room_id': str(random.randint(10**17, 10**18-1)),
            'live_id': str(random.randint(10**17, 10**18-1)),
            'ts': str(int(time.time())),
        }
        try:
            resp = requests.get(test_url, params=test_params, 
                              proxies={'http': proxy_url, 'https': proxy_url},
                              timeout=timeout,
                              headers={'User-Agent': 'com.zhiliaoapp.musically/2024010100 (Linux; U; Android 14; SM-G998B; tt-ok/3.12.13)'},
                              verify=False)
            return (resp.status_code in [200, 403, 429, 503]), resp.status_code, resp.elapsed.total_seconds()
        except: return False, 0, 0
    
    @staticmethod
    def test_single_proxy(proxy_str, proxy_type='HTTP'):
        scheme = {'HTTP': 'http', 'HTTPS': 'https', 'SOCKS4': 'socks4', 'SOCKS5': 'socks5'}.get(proxy_type.upper(), 'http')
        proxy_url = f"{scheme}://{proxy_str}"
        success, status, latency = ProxyTester.test_against_webcast(proxy_url)
        return proxy_str, success, status, latency
    
    @staticmethod
    def test_proxy_batch(proxies, proxy_type='HTTP', max_workers=50):
        working, failed = [], []
        print(f"\n🔬 Testing {len(proxies)} proxies against TikTok webcast...")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(ProxyTester.test_single_proxy, p, proxy_type): p for p in proxies}
            completed = 0
            for future in as_completed(futures):
                proxy_str, success, status, latency = future.result()
                completed += 1
                if success:
                    working.append(proxy_str)
                    print(f"\r✅ [{completed}/{len(proxies)}] Working: {proxy_str} [{latency:.2f}s]", end='')
                else:
                    failed.append(proxy_str)
                    if completed % 50 == 0: print(f"\r⏳ [{completed}/{len(proxies)}] Testing... ({len(working)} working)", end='')
        print(f"\n\n📊 Results: {len(working)} working / {len(failed)} failed")
        return working, failed

# =============================================================================
# PROXY SCRAPER  
# =============================================================================

class ProxyScraper:
    SOURCES = {
        'HTTP': [
            "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all",
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
            "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt",
            "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTP_RAW.txt",
            "https://raw.githubusercontent.com/hookzof/socks5_list/master/http.txt",
        ],
        'SOCKS5': [
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
            "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks5.txt",
        ]
    }
    
    @staticmethod
    def scrape(proxy_type='HTTP', timeout=15):
        all_proxies = set()
        sources = ProxyScraper.SOURCES.get(proxy_type, ProxyScraper.SOURCES['HTTP'])
        print(f"🌐 Scraping {proxy_type} proxies from {len(sources)} sources...")
        for i, url in enumerate(sources, 1):
            try:
                resp = requests.get(url, timeout=timeout, headers={'User-Agent': 'Mozilla/5.0'})
                for line in resp.text.split('\n'):
                    line = line.strip()
                    if ':' in line and not line.startswith('#'): all_proxies.add(line)
                print(f"  Source {i}: +{len(resp.text.splitlines())} proxies")
            except Exception as e: print(f"  Source {i}: ❌ {str(e)[:30]}")
        return list(all_proxies)

# =============================================================================
# TIKTOK LIVE WORKER - Uses SignerPy for ALL requests
# =============================================================================

class TikTokLiveWorker:
    def __init__(self, room_id, proxy=None):
        self.room_id = room_id
        self.proxy = proxy
        self.device_profile = random.choice(DEVICE_PROFILES)
        self.session = requests.Session()
        if proxy:
            self.session.proxies = {'http': f"http://{proxy}", 'https': f"http://{proxy}"}
    
    def _make_request(self, endpoint, params, payload=None):
        """Make request WITH SignerPy signatures"""
        headers, _ = header_gen.generate(self.device_profile, params)
        domain = random.choice(WEBCAST_DOMAINS)
        headers['Host'] = domain
        url = f"https://{domain}{endpoint}"
        try:
            if payload:
                resp = self.session.post(url, params=params, data=payload, headers=headers, timeout=10, verify=False)
            else:
                resp = self.session.get(url, params=params, headers=headers, timeout=10, verify=False)
            return resp
        except: return None
    
    def enter_room(self):
        params = {
            'aid': '1988', 'app_name': 'musically_go', 'app_version': random.choice(['27.2.4', '27.1.3']),
            'device_id': self.device_profile['device_id'], 'device_platform': 'android', 'device_type': self.device_profile['model'],
            'os_version': self.device_profile['os_version'], 'os_api': self.device_profile['os_api'],
            'live_id': str(random.randint(10**17, 10**18-1)), 'room_id': self.room_id,
            'enter_source': random.choice(['feed', 'profile', 'search']), 'is_login': '1',
            'region': random.choice(['US', 'ES', 'FR', 'DE']), 'tz_name': random.choice(['America/New_York', 'Europe/Madrid']),
            'ts': str(int(time.time())),
        }
        resp = self._make_request('/webcast/room/enter/', params)
        if resp and resp.status_code == 200:
            try: return resp.json().get('status_code') == 0
            except: pass
        return False
    
    def send_heartbeat(self):
        params = {
            'aid': '1988', 'app_name': 'musically_go', 'device_id': self.device_profile['device_id'],
            'live_id': str(random.randint(10**17, 10**18-1)), 'room_id': self.room_id,
            'heartbeat_duration': str(random.randint(3000, 8000)), 'type': '1', 'ts': str(int(time.time())),
        }
        resp = self._make_request('/webcast/heartbeat/', params)
        return resp is not None and resp.status_code == 200
    
    def send_like(self, count=1):
        params = {
            'aid': '1988', 'app_name': 'musically_go', 'device_id': self.device_profile['device_id'],
            'room_id': self.room_id, 'like_count': str(count), 'live_id': str(random.randint(10**17, 10**18-1)),
            'type': 'aweme', 'ts': str(int(time.time())),
        }
        resp = self._make_request('/webcast/like/', params)
        return resp is not None and resp.status_code == 200
    
    def send_share(self):
        params = {
            'aid': '1988', 'app_name': 'musically_go', 'device_id': self.device_profile['device_id'],
            'room_id': self.room_id, 'share_type': random.choice(['1', '2', '3']),
            'share_delta': '1', 'live_id': str(random.randint(10**17, 10**18-1)), 'ts': str(int(time.time())),
        }
        resp = self._make_request('/webcast/share/', params)
        return resp is not None and resp.status_code == 200
    
    def send_follow(self, streamer_sec_uid):
        params = {
            'aid': '1988', 'app_name': 'musically_go', 'device_id': self.device_profile['device_id'],
            'room_id': self.room_id, 'to_user_id': streamer_sec_uid, 'status': '1',
            'type': 'aweme', 'from': 'profile', 'ts': str(int(time.time())),
        }
        resp = self._make_request('/aweme/v1/commit/follow/user/', params)
        return resp is not None and resp.status_code == 200

# =============================================================================
# BOT ENGINE
# =============================================================================

class TikTokLiveBot:
    def __init__(self):
        self.running = False
        self.room_id = ""
        self.streamer_sec_uid = ""
        self.threads = 10
        self.target = 1000
        self.mode = "views"
        self.views = self.likes = self.shares = self.follows = self.errors = self.total_requests = 0
        self.start_time = 0
        self._lock = threading.Lock()
        self.proxies = []
    
    def set_proxies(self, proxies): self.proxies = proxies
    
    def worker_loop(self, worker_id):
        while self.running:
            try:
                proxy = random.choice(self.proxies) if self.proxies else None
                worker = TikTokLiveWorker(self.room_id, proxy)
                if worker.enter_room():
                    with self._lock: self.views += 1; self.total_requests += 1
                    for cycle in range(random.randint(3, 8)):
                        if not self.running: break
                        if worker.send_heartbeat():
                            with self._lock: self.total_requests += 1
                        if self.mode in ['likes', 'all']:
                            if worker.send_like(random.randint(1, 5)):
                                with self._lock: self.likes += 1; self.total_requests += 1
                        if self.mode in ['shares', 'all'] and random.random() < 0.3:
                            if worker.send_share():
                                with self._lock: self.shares += 1; self.total_requests += 1
                        if self.mode in ['follows', 'all'] and random.random() < 0.1 and self.streamer_sec_uid:
                            if worker.send_follow(self.streamer_sec_uid):
                                with self._lock: self.follows += 1; self.total_requests += 1
                        time.sleep(random.uniform(1.5, 3.5))
                else:
                    with self._lock: self.errors += 1
            except:
                with self._lock: self.errors += 1
            time.sleep(random.uniform(0.5, 1.5))
    
    def start(self):
        self.running = True
        self.start_time = time.time()
        print(f"\n🚀 Starting {self.mode} bot | Room: {self.room_id} | Threads: {self.threads} | Target: {self.target} | Proxies: {len(self.proxies)}")
        print(f"🔐 SignerPy v{SIGNERPY_VERSION}: ✅ Production signatures ACTIVE")
        threading.Thread(target=self.dashboard, daemon=True).start()
        for i in range(self.threads):
            threading.Thread(target=self.worker_loop, args=(i,), daemon=True).start()
    
    def stop(self):
        self.running = False
        elapsed = time.time() - self.start_time if self.start_time else 0
        print(f"\n\n🛑 Views: {self.views} | Likes: {self.likes} | Shares: {self.shares} | Follows: {self.follows} | Errors: {self.errors} | Total: {self.total_requests} | Time: {elapsed:.1f}s")
    
    def dashboard(self):
        while self.running:
            os.system('cls' if os.name == 'nt' else 'clear')
            elapsed = time.time() - self.start_time
            print(f"""
╔══════════════════════════════════════════════════════════════╗
║     TIKTOK LIVE BOT v6.0 - SignerPy PRODUCTION              ║
╚══════════════════════════════════════════════════════════════╝
 🔐 SignerPy v{SIGNERPY_VERSION}: ✅ ACTIVE - Production signatures
 {'─'*55}
 🎯 Mode:     {self.mode.upper():<10}  🕒 Uptime: {int(elapsed//3600):02d}:{int((elapsed%3600)//60):02d}:{int(elapsed%60):02d}
 🔴 Room ID:  {self.room_id}
 {'─'*55}
 👁️  Views:   {self.views:>7,}  ❤️  Likes:    {self.likes:>6,}
 🔗 Shares:  {self.shares:>7,}  👤 Follows:  {self.follows:>6,}
 ❌ Errors:  {self.errors:>7,}  📊 Total:    {self.total_requests:>6,}
 ⚡ Rate:    {self.total_requests/elapsed:>5.0f} req/s
 {'─'*55}
 🧵 Workers: {sum(1 for _ in threading.enumerate())-1}  🌐 Proxies: {len(self.proxies)}
 {'─'*55}
 Press Ctrl+C to stop
            """)
            time.sleep(2)

# =============================================================================
# MAIN
# =============================================================================

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    bot = TikTokLiveBot()
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║  TIKTOK LIVE BOT v6.0 - SignerPy INTEGRATED                 ║
║  ✓ XBogusSigner  ✓ GorgonSigner  ✓ Full Signer              ║
║  ✓ Webcast Proxy Testing  ✓ All Live Actions                ║
╚══════════════════════════════════════════════════════════════╝
    """)
    print(f"🔐 SignerPy v{SIGNERPY_VERSION}: ✅ Production signatures ready\n")
    
    while True:
        print("📋 MAIN MENU:")
        print(" [0] ⚙️  Setup (Room ID, Mode, Target)")
        print(" [1] 🌐 Proxy Manager")
        print(" [2] 🚀 Start Bot")
        print(" [Q] Quit\n")
        
        choice = input(" Select: ").strip().upper()
        
        if choice == 'Q':
            if bot.running: bot.stop()
            print("👋 Bye!"); break
        
        elif choice == '0':
            room = input(" Room ID: ").strip()
            if room.isdigit() and len(room) >= 15:
                bot.room_id = room; print(f" ✅ Room: {room}")
            sec = input(" sec_uid (or Enter to skip): ").strip()
            if sec: bot.streamer_sec_uid = sec; print(" ✅ sec_uid set")
            print("\n Mode: 1-Views 2-Likes 3-Shares 4-Follows 5-ALL")
            mode_map = {'1':'views','2':'likes','3':'shares','4':'follows','5':'all'}
            mc = input(" Select (1-5): ").strip()
            if mc in mode_map: bot.mode = mode_map[mc]; print(f" ✅ Mode: {bot.mode}")
            try:
                bot.threads = max(1, min(500, int(input(" Threads (1-500): ") or "10")))
                bot.target = int(input(" Target: ") or "1000")
            except: pass
            input("Press Enter...")
        
        elif choice == '1':
            os.system('cls' if os.name == 'nt' else 'clear')
            print("\n🌐 PROXY MANAGER:")
            print(" [1] Scrape HTTP")
            print(" [2] Load & Test")
            print(" [0] Back\n")
            pc = input(" Select: ").strip()
            if pc == '1':
                proxies = ProxyScraper.scrape('HTTP')
                print(f" Scraped {len(proxies)} proxies")
                test = input(" Test against webcast? (y/n): ").strip().lower()
                if test == 'y':
                    working, _ = ProxyTester.test_proxy_batch(proxies[:200], 'HTTP')
                    bot.set_proxies(working)
                    with open('proxies_working.txt', 'w') as f:
                        for p in working: f.write(p + '\n')
                    print(f" ✅ Saved {len(working)} working proxies")
                input("Press Enter...")
            elif pc == '2':
                try:
                    with open('proxies_working.txt') as f:
                        proxies = [l.strip() for l in f if ':' in l.strip()]
                    bot.set_proxies(proxies)
                    print(f" ✅ Loaded {len(proxies)} proxies")
                except: print(" ❌ File not found")
                input("Press Enter...")
        
        elif choice == '2':
            if not bot.room_id: print(" ❌ Set Room ID first!"); input("Press Enter..."); continue
            bot.start()
            try:
                while bot.running:
                    time.sleep(1)
                    if bot.views >= bot.target: print(f"\n ✅ Target: {bot.views} views"); bot.stop(); break
            except KeyboardInterrupt: bot.stop()
            input("Press Enter...")

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: print("\n👋 Exiting...")
    except Exception as e: print(f"❌ {e}"); import traceback; traceback.print_exc()
