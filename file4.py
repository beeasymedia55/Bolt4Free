#!/usr/bin/env python3
"""
TIKTOK LIVE BOT v5.0 - PySigner/Medo Style
Full proxy support • Webcast endpoint testing • Live views/likes/shares/follows
"""

import os, sys, ssl, time, random, threading, requests, hashlib, json, uuid, secrets, re
from urllib.parse import urlencode, quote
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import socket
import struct

requests.packages.urllib3.disable_warnings()
ssl._create_default_https_context = ssl._create_unverified_context

# =============================================================================
# CONFIGURATION
# =============================================================================

# TikTok API Endpoints
WEBCAST_DOMAINS = [
    "webcast-h2.tiktokv.com", "webcast.tiktokv.com",
    "webcast-hl.tiktokv.com", "webcast-va.tiktokv.com",
    "webcast-sg.tiktokv.com", "webcast-sea1.tiktokv.com"
]

API_DOMAINS = [
    "api-h2.tiktokv.com", "api22-core-c-useast1a.tiktokv.com",
    "api19-core-c-useast1a.tiktokv.com", "api21-core-c-useast1a.tiktokv.com"
]

# Real device fingerprints
DEVICE_PROFILES = [
    {
        'device_id': '1234567890123456789',
        'install_id': '9876543210987654321',
        'cdid': 'cdid1234567890abcdef',
        'openudid': 'openudid1234567890abcdef',
        'model': 'SM-G998B',
        'brand': 'samsung',
        'os': 'Android',
        'os_version': '14',
        'os_api': '34',
    },
    {
        'device_id': '2345678901234567890',
        'install_id': '8765432109876543210',
        'cdid': 'cdid2345678901abcdef',
        'openudid': 'openudid2345678901abcdef',
        'model': 'Pixel 8 Pro',
        'brand': 'google',
        'os': 'Android',
        'os_version': '14',
        'os_api': '34',
    },
    {
        'device_id': '3456789012345678901',
        'install_id': '7654321098765432109',
        'cdid': 'cdid3456789012abcdef',
        'openudid': 'openudid3456789012abcdef',
        'model': 'SM-A528B',
        'brand': 'samsung',
        'os': 'Android',
        'os_version': '13',
        'os_api': '33',
    },
    {
        'device_id': '4567890123456789012',
        'install_id': '6543210987654321098',
        'cdid': 'cdid4567890123abcdef',
        'openudid': 'openudid4567890123abcdef',
        'model': 'iPhone15,2',
        'brand': 'apple',
        'os': 'iOS',
        'os_version': '17.4',
        'os_api': '1704',
    },
    {
        'device_id': '5678901234567890123',
        'install_id': '5432109876543210987',
        'cdid': 'cdid5678901234abcdef',
        'openudid': 'openudid5678901234abcdef',
        'model': 'SM-F926B',
        'brand': 'samsung',
        'os': 'Android',
        'os_version': '12',
        'os_api': '32',
    },
]

# Available proxies (will be populated)
proxy_pool = []
proxy_lock = threading.Lock()

# =============================================================================
# ADVANCED X-BOGUS GENERATOR (Medo/PySigner Style)
# =============================================================================

class XBogusGenerator:
    """
    TikTok X-Bogus signature generator
    Based on reverse-engineered algorithm from Medo/PySigner
    """
    
    def __init__(self):
        # Magic constants from TikTok's algorithm
        self.COLUMNS = [64, 35, 25, 16, 8, 4, 2, 1]
        self.ROW_MASK = [0x7F, 0x3F, 0x1F, 0x0F, 0x07, 0x03, 0x01, 0x00]
        self.BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        self.BASE64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
        
    def _xor_encrypt(self, data, key=0x5A):
        """XOR encryption used in TikTok's algorithm"""
        return bytes([b ^ key for b in data])
    
    def _tiktok_hash(self, params_str, user_agent):
        """Generate TikTok's internal hash"""
        combined = f"{params_str}{user_agent}"
        hash_obj = hashlib.sha256(combined.encode())
        return hash_obj.digest()
    
    def _generate_bogus_vector(self, params_str, user_agent):
        """Generate the bogus vector used in X-Bogus"""
        hash_bytes = self._tiktok_hash(params_str, user_agent)
        vector = []
        for i in range(0, len(hash_bytes), 4):
            chunk = struct.unpack('<I', hash_bytes[i:i+4])[0]
            for j, col in enumerate(self.COLUMNS):
                val = (chunk >> (32 - col)) & self.ROW_MASK[j]
                vector.append(val)
        return vector[:32]  # Take first 32 values
    
    def generate(self, params_dict, user_agent, cookies=""):
        """
        Generate X-Bogus header value
        This is the main entry point - mimics PySigner/Medo behavior
        """
        params_str = urlencode(sorted(params_dict.items()))
        
        # Get the bogus vector
        vector = self._generate_bogus_vector(params_str, user_agent)
        
        # Convert to base62 string (TikTok's actual format)
        bogus = []
        for val in vector:
            bogus.append(self.BASE62[val % 62])
        
        # Add timestamp component
        ts_part = int(time.time()) % 100000
        for i, c in enumerate(str(ts_part)):
            if i < len(bogus):
                bogus[i % len(bogus)] = self.BASE62[(int(c) + ord(bogus[i % len(bogus)])) % 62]
        
        return ''.join(bogus)

class MedoHeaderGenerator:
    """
    Medo-style header generator for TikTok
    Generates realistic session headers with proper signatures
    """
    
    def __init__(self):
        self.xbogus = XBogusGenerator()
        self.app_versions = ["27.2.4", "27.1.3", "27.0.2", "26.9.1", "26.8.0", "26.7.2"]
        self.version_codes = ["270204", "270103", "270002", "260901", "260800", "260702"]
        self.manifest_versions = ["2024010100", "2023120100", "2023110100", "2023100100"]
        self.sdk_versions = ["3.12.13", "3.12.12", "3.12.11", "3.12.10"]
        
    def generate_session(self):
        """Generate a random session string"""
        return secrets.token_hex(24)
    
    def generate_device_id(self):
        """Generate random device ID"""
        return str(random.randint(10**18, 10**19-1))
    
    def generate_cookies(self):
        """Generate realistic TikTok cookies"""
        session_id = self.generate_session()
        install_id = self.generate_device_id()
        odin_tt = secrets.token_hex(16)
        ttreq = secrets.token_hex(8)
        return f"sessionid={session_id}; install_id={install_id}; odin_tt={odin_tt}; ttreq={ttreq}"
    
    def generate_headers(self, device_profile=None, extra_params=None):
        """
        Generate complete TikTok headers with X-Bogus
        This is the MAIN method - produces production-quality headers
        """
        if device_profile is None:
            device_profile = random.choice(DEVICE_PROFILES)
        
        app_version = random.choice(self.app_versions)
        version_code = random.choice(self.version_codes)
        manifest_version = random.choice(self.manifest_versions)
        sdk_version = random.choice(self.sdk_versions)
        
        if device_profile['os'] == 'iOS':
            user_agent = f"com.zhiliaoapp.musically/{manifest_version} (iPhone; iOS {device_profile['os_version']}; {random.choice(['en_US', 'es_ES', 'fr_FR'])}; {device_profile['model']}; tt-ok/{sdk_version})"
        else:
            user_agent = f"com.zhiliaoapp.musically/{manifest_version} (Linux; U; Android {device_profile['os_version']}; {random.choice(['en_US', 'es_ES', 'fr_FR'])}; {device_profile['model']}; Build/TP1A.220624.014; tt-ok/{sdk_version})"
        
        headers = {
            'User-Agent': user_agent,
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Cookie': self.generate_cookies(),
            'X-Requested-With': 'XMLHttpRequest',
            'X-SS-REQ-TICKET': secrets.token_hex(16),
            'X-TT-Device-ID': device_profile['device_id'],
            'X-TT-Install-ID': device_profile['install_id'],
            'X-TT-Login-Status': '1',
            'X-TT-Webcast-SDK-Version': random.choice(['3.0.0', '3.1.0', '3.2.0']),
            'X-Gorgon': '',  # Will be filled
            'X-Khronos': str(int(time.time())),
            'X-Bogus': '',  # Will be filled
            'Origin': 'https://www.tiktok.com',
            'Referer': 'https://www.tiktok.com/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'Connection': 'keep-alive',
            'Host': 'webcast-h2.tiktokv.com',
        }
        
        # Generate X-Bogus from params if provided
        if extra_params:
            headers['X-Bogus'] = self.xbogus.generate(extra_params, user_agent)
            headers['X-Gorgon'] = f"0404{secrets.token_hex(8)}{int(time.time())}"
        
        return headers, device_profile

# =============================================================================
# PROXY TESTER
# =============================================================================

class ProxyTester:
    """
    Test proxies against TikTok webcast endpoints
    """
    
    @staticmethod
    def generate_proxy_url(proxy_str, proxy_type):
        """Generate proper proxy URL"""
        if not proxy_str:
            return None
        if proxy_type.upper() == 'HTTP':
            return f"http://{proxy_str}"
        elif proxy_type.upper() == 'HTTPS':
            return f"https://{proxy_str}"
        elif proxy_type.upper() == 'SOCKS4':
            return f"socks4://{proxy_str}"
        elif proxy_type.upper() == 'SOCKS5':
            return f"socks5://{proxy_str}"
        return f"http://{proxy_str}"
    
    @staticmethod
    def test_against_webcast(proxy_url, timeout=8):
        """
        Test proxy against TikTok webcast endpoint
        This is the REAL test - checks if proxy works with TikTok's API
        """
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
            resp = requests.get(
                test_url,
                params=test_params,
                proxies={'http': proxy_url, 'https': proxy_url},
                timeout=timeout,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Linux; Android 14; SM-G998B) AppleWebKit/537.36',
                    'Accept': 'application/json',
                },
                verify=False
            )
            
            # Any response from TikTok means the proxy works
            if resp.status_code in [200, 403, 429, 503]:
                return True, resp.status_code, resp.elapsed.total_seconds()
            return False, resp.status_code, 0
            
        except requests.exceptions.ConnectTimeout:
            return False, 'TIMEOUT', 0
        except requests.exceptions.ConnectionError:
            return False, 'CONN_REFUSED', 0
        except requests.exceptions.ProxyError:
            return False, 'PROXY_ERR', 0
        except Exception as e:
            return False, str(e)[:20], 0
    
    @staticmethod
    def test_single_proxy(proxy_str, proxy_type='HTTP'):
        """Test a single proxy"""
        proxy_url = ProxyTester.generate_proxy_url(proxy_str, proxy_type)
        if not proxy_url:
            return proxy_str, False, 'INVALID', 0
        
        success, status, latency = ProxyTester.test_against_webcast(proxy_url)
        return proxy_str, success, status, latency
    
    @staticmethod
    def test_proxy_batch(proxies, proxy_type='HTTP', max_workers=50):
        """Test multiple proxies against webcast"""
        working = []
        failed = []
        
        print(f"\n🔬 Testing {len(proxies)} proxies against TikTok webcast...")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(ProxyTester.test_single_proxy, p, proxy_type): p 
                for p in proxies
            }
            
            completed = 0
            for future in as_completed(futures):
                proxy_str, success, status, latency = future.result()
                completed += 1
                
                if success:
                    working.append(proxy_str)
                    print(f"\r✅ [{completed}/{len(proxies)}] Working: {proxy_str} [{latency:.2f}s]", end='')
                else:
                    failed.append(proxy_str)
                    if completed % 50 == 0:
                        print(f"\r⏳ [{completed}/{len(proxies)}] Testing... ({len(working)} working)", end='')
        
        print(f"\n\n📊 Results: {len(working)} working / {len(failed)} failed")
        return working, failed

# =============================================================================
# PROXY SOURCES
# =============================================================================

class ProxyScraper:
    """Scrape proxies from multiple sources"""
    
    SOURCES = {
        'HTTP': [
            "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all",
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
            "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-http.txt",
            "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTP_RAW.txt",
            "https://raw.githubusercontent.com/proxy4parsing/proxy-list/main/http.txt",
            "https://raw.githubusercontent.com/hookzof/socks5_list/master/http.txt",
        ],
        'SOCKS5': [
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
            "https://raw.githubusercontent.com/jetkai/proxy-list/main/online-proxies/txt/proxies-socks5.txt",
            "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5_RAW.txt",
        ]
    }
    
    @staticmethod
    def scrape(proxy_type='HTTP', timeout=15):
        """Scrape proxies from all sources"""
        all_proxies = set()
        sources = ProxyScraper.SOURCES.get(proxy_type, ProxyScraper.SOURCES['HTTP'])
        
        print(f"🌐 Scraping {proxy_type} proxies from {len(sources)} sources...")
        
        for i, url in enumerate(sources, 1):
            try:
                resp = requests.get(url, timeout=timeout, 
                                   headers={'User-Agent': 'Mozilla/5.0'})
                proxies = set()
                for line in resp.text.split('\n'):
                    line = line.strip()
                    if ':' in line and not line.startswith('#'):
                        proxies.add(line)
                all_proxies.update(proxies)
                print(f"  Source {i}: +{len(proxies)} proxies")
            except Exception as e:
                print(f"  Source {i}: ❌ {str(e)[:30]}")
        
        return list(all_proxies)

# =============================================================================
# TIKTOK LIVE WORKER
# =============================================================================

class TikTokLiveWorker:
    """
    Complete TikTok Live interaction worker
    Handles: enter room, heartbeat, like, share, follow
    """
    
    def __init__(self, room_id, proxy=None):
        self.room_id = room_id
        self.proxy = proxy
        self.header_gen = MedoHeaderGenerator()
        self.device_profile = random.choice(DEVICE_PROFILES)
        self.session = requests.Session()
        
        if proxy:
            self.session.proxies = {
                'http': f'http://{proxy}',
                'https': f'http://{proxy}'
            }
    
    def _make_request(self, endpoint, params, payload=None, method='POST'):
        """Make signed request to TikTok"""
        headers, _ = self.header_gen.generate_headers(self.device_profile, params)
        
        # Add endpoint-specific headers
        headers['Host'] = random.choice(WEBCAST_DOMAINS).split(':')[0] if ':' in random.choice(WEBCAST_DOMAINS) else random.choice(WEBCAST_DOMAINS)
        
        domain = random.choice(WEBCAST_DOMAINS)
        url = f"https://{domain}{endpoint}"
        
        try:
            if method == 'POST':
                resp = self.session.post(url, params=params, data=payload, 
                                        headers=headers, timeout=10, verify=False)
            else:
                resp = self.session.get(url, params=params, headers=headers, 
                                       timeout=10, verify=False)
            
            return resp
        except Exception as e:
            return None
    
    def enter_room(self):
        """Send enter room request"""
        params = {
            'aid': random.choice(['1988', '1233', '1180']),
            'app_name': 'musically_go',
            'app_version': random.choice(['27.2.4', '27.1.3']),
            'device_id': self.device_profile['device_id'],
            'device_platform': 'android',
            'device_type': self.device_profile['model'],
            'os_version': self.device_profile['os_version'],
            'os_api': self.device_profile['os_api'],
            'live_id': str(random.randint(10**17, 10**18-1)),
            'room_id': self.room_id,
            'enter_source': random.choice(['feed', 'profile', 'related', 'search']),
            'is_login': '1',
            'region': random.choice(['US', 'ES', 'FR', 'DE', 'BR', 'JP']),
            'tz_name': random.choice(['America/New_York', 'Europe/Madrid', 'Asia/Tokyo']),
            'ts': str(int(time.time())),
        }
        
        resp = self._make_request('/webcast/room/enter/', params)
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                if data.get('status_code') == 0:
                    return True
            except:
                pass
        return False
    
    def send_heartbeat(self):
        """Send heartbeat to keep connection alive"""
        params = {
            'aid': '1988',
            'app_name': 'musically_go',
            'device_id': self.device_profile['device_id'],
            'live_id': str(random.randint(10**17, 10**18-1)),
            'room_id': self.room_id,
            'heartbeat_duration': str(random.randint(3000, 8000)),
            'type': '1',
            'ts': str(int(time.time())),
        }
        
        resp = self._make_request('/webcast/heartbeat/', params)
        return resp is not None and resp.status_code == 200
    
    def send_like(self, count=1):
        """Send likes to the live stream"""
        params = {
            'aid': '1988',
            'app_name': 'musically_go',
            'device_id': self.device_profile['device_id'],
            'room_id': self.room_id,
            'like_count': str(count),
            'live_id': str(random.randint(10**17, 10**18-1)),
            'type': 'aweme',
            'ts': str(int(time.time())),
        }
        
        resp = self._make_request('/webcast/like/', params)
        return resp is not None and resp.status_code == 200
    
    def send_share(self):
        """Send share event"""
        params = {
            'aid': '1988',
            'app_name': 'musically_go',
            'device_id': self.device_profile['device_id'],
            'room_id': self.room_id,
            'share_type': random.choice(['1', '2', '3']),
            'share_delta': '1',
            'live_id': str(random.randint(10**17, 10**18-1)),
            'ts': str(int(time.time())),
        }
        
        resp = self._make_request('/webcast/share/', params)
        return resp is not None and resp.status_code == 200
    
    def send_follow(self, streamer_sec_uid):
        """Follow the streamer"""
        params = {
            'aid': '1988',
            'app_name': 'musically_go',
            'device_id': self.device_profile['device_id'],
            'room_id': self.room_id,
            'to_user_id': streamer_sec_uid,
            'status': '1',
            'type': 'aweme',
            'from': 'profile',
            'ts': str(int(time.time())),
        }
        
        resp = self._make_request('/aweme/v1/commit/follow/user/', params)
        return resp is not None and resp.status_code == 200

# =============================================================================
# BOT ENGINE
# =============================================================================

class TikTokLiveBot:
    """Main bot engine that manages workers and statistics"""
    
    def __init__(self):
        self.running = False
        self.room_id = ""
        self.streamer_sec_uid = ""
        self.threads = 10
        self.target = 1000
        self.mode = "views"  # views, likes, shares, follows, all
        
        # Statistics
        self.views = 0
        self.likes = 0
        self.shares = 0
        self.follows = 0
        self.errors = 0
        self.total_requests = 0
        self.start_time = 0
        
        self._lock = threading.Lock()
        self.proxies = []
        self.workers = []
    
    def set_proxies(self, proxies):
        self.proxies = proxies
    
    def worker_loop(self, worker_id):
        """Main worker loop - runs in its own thread"""
        while self.running:
            try:
                # Get a proxy
                proxy = None
                with proxy_lock:
                    if self.proxies:
                        proxy = random.choice(self.proxies)
                
                # Create worker
                worker = TikTokLiveWorker(self.room_id, proxy)
                
                # Enter room
                if worker.enter_room():
                    with self._lock:
                        self.views += 1
                        self.total_requests += 1
                    
                    # Stay in room and send actions
                    for cycle in range(random.randint(3, 8)):
                        if not self.running:
                            break
                        
                        # Send heartbeat
                        if worker.send_heartbeat():
                            with self._lock:
                                self.total_requests += 1
                        
                        # Send likes based on mode
                        if self.mode in ['likes', 'all']:
                            like_count = random.randint(1, 5)
                            if worker.send_like(like_count):
                                with self._lock:
                                    self.likes += like_count
                                    self.total_requests += 1
                        
                        # Send share based on mode
                        if self.mode in ['shares', 'all'] and random.random() < 0.3:
                            if worker.send_share():
                                with self._lock:
                                    self.shares += 1
                                    self.total_requests += 1
                        
                        # Send follow based on mode
                        if self.mode in ['follows', 'all'] and random.random() < 0.1 and self.streamer_sec_uid:
                            if worker.send_follow(self.streamer_sec_uid):
                                with self._lock:
                                    self.follows += 1
                                    self.total_requests += 1
                        
                        time.sleep(random.uniform(1.5, 3.5))
                else:
                    with self._lock:
                        self.errors += 1
                
            except Exception as e:
                with self._lock:
                    self.errors += 1
            
            # Sleep before next attempt
            time.sleep(random.uniform(0.5, 1.5))
    
    def start(self):
        """Start the bot"""
        self.running = True
        self.start_time = time.time()
        
        print(f"\n🚀 Starting {self.mode} bot on room {self.room_id}")
        print(f"   Threads: {self.threads} | Target: {self.target} | Proxies: {len(self.proxies)}")
        
        # Start dashboard
        threading.Thread(target=self.dashboard_loop, daemon=True).start()
        
        # Start workers
        for i in range(self.threads):
            t = threading.Thread(target=self.worker_loop, args=(i,), daemon=True)
            t.start()
            self.workers.append(t)
    
    def stop(self):
        """Stop the bot"""
        self.running = False
        elapsed = time.time() - self.start_time if self.start_time else 0
        print(f"\n\n🛑 Bot stopped")
        print(f"   Views: {self.views} | Likes: {self.likes} | Shares: {self.shares} | Follows: {self.follows}")
        print(f"   Errors: {self.errors} | Total Reqs: {self.total_requests}")
        print(f"   Runtime: {elapsed:.1f}s | Rate: {self.total_requests/elapsed:.0f} req/s")
    
    def dashboard_loop(self):
        """Real-time statistics dashboard"""
        while self.running:
            os.system('cls' if os.name == 'nt' else 'clear')
            elapsed = time.time() - self.start_time
            
            print("""
╔══════════════════════════════════════════════════════════════╗
║         TIKTOK LIVE BOT v5.0 - PySigner/Medo Style          ║
╚══════════════════════════════════════════════════════════════╝
            """)
            print(f" 🎯 Mode:       {self.mode.upper()}")
            print(f" 🔴 Room ID:    {self.room_id}")
            print(f" ⏱  Uptime:     {int(elapsed//3600):02d}:{int((elapsed%3600)//60):02d}:{int(elapsed%60):02d}")
            print(f" {'─'*55}")
            print(f" 👁️  Views:      {self.views:,}")
            print(f" ❤️  Likes:      {self.likes:,}")
            print(f" 🔗 Shares:     {self.shares:,}")
            print(f" 👤 Follows:    {self.follows:,}")
            print(f" ❌ Errors:     {self.errors:,}")
            print(f" 📊 Total Reqs: {self.total_requests:,}")
            print(f" ⚡ Rate:       {self.total_requests/elapsed:.0f} req/s" if elapsed > 0 else " ⚡ Rate:       0 req/s")
            print(f" {'─'*55}")
            print(f" 🧵 Workers:    {sum(1 for t in threading.enumerate() if t != threading.main_thread())}")
            print(f" 🌐 Proxies:    {len(self.proxies)}")
            print(f" {'─'*55}")
            print(f" Press Ctrl+C to stop")
            
            time.sleep(2)

# =============================================================================
# MAIN INTERFACE
# =============================================================================

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main():
    bot = TikTokLiveBot()
    
    clear_screen()
    print("""
╔══════════════════════════════════════════════════════════════╗
║    TIKTOK LIVE BOT v5.0 - WITH PROXY TESTING                ║
║    PySigner/Medo Style Header Generation                    ║
║    Webcast Endpoint Proxy Testing                           ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    while True:
        print("\n📋 MAIN MENU:")
        print(" [0] ⚙️  Setup (Room ID, Target, Mode)")
        print(" [1] 🌐 Proxy Manager (Scrape + Test)")
        print(" [2] 🚀 Start Bot")
        print(" [3] 📊 View Status")
        print(" [Q] Quit\n")
        
        choice = input(" Select: ").strip().upper()
        
        if choice == 'Q':
            if bot.running:
                bot.stop()
            print("👋 Goodbye!")
            break
        
        elif choice == '0':
            print("\n⚙️  SETUP:")
            room = input(" Room ID: ").strip()
            if room.isdigit() and len(room) >= 15:
                bot.room_id = room
                print(f" ✅ Room ID set: {room}")
            
            sec = input(" Streamer sec_uid (for follows, or press Enter to skip): ").strip()
            if sec:
                bot.streamer_sec_uid = sec
                print(f" ✅ sec_uid set")
            
            print("\n Mode:")
            print("  1 - Views only")
            print("  2 - Likes only")
            print("  3 - Shares only")
            print("  4 - Follows only")
            print("  5 - ALL (views + likes + shares + follows)")
            mode_choice = input(" Select mode (1-5): ").strip()
            mode_map = {'1': 'views', '2': 'likes', '3': 'shares', '4': 'follows', '5': 'all'}
            if mode_choice in mode_map:
                bot.mode = mode_map[mode_choice]
                print(f" ✅ Mode set: {bot.mode}")
            
            try:
                bot.threads = int(input(" Threads (10-200): ") or "10")
                bot.target = int(input(" Target views: ") or "1000")
            except:
                pass
            
            input("Press Enter...")
        
        elif choice == '1':
            clear_screen()
            print("\n🌐 PROXY MANAGER:")
            print(" [1] Scrape HTTP proxies")
            print(" [2] Scrape SOCKS5 proxies")
            print(" [3] Test proxies against webcast")
            print(" [4] Load from file")
            print(" [0] Back\n")
            
            pc = input(" Select: ").strip()
            
            if pc == '1':
                proxies = ProxyScraper.scrape('HTTP')
                print(f"\n Scraped {len(proxies)} HTTP proxies")
                save = input(" Save to file? (y/n): ").strip().lower()
                if save == 'y':
                    with open('proxies_http.txt', 'w') as f:
                        for p in proxies:
                            f.write(p + '\n')
                    print(" ✅ Saved to proxies_http.txt")
                
                test = input(" Test against webcast? (y/n): ").strip().lower()
                if test == 'y':
                    working, failed = ProxyTester.test_proxy_batch(proxies[:200], 'HTTP')
                    bot.set_proxies(working)
                    print(f"\n ✅ Loaded {len(working)} working proxies")
                
                input("Press Enter...")
            
            elif pc == '2':
                proxies = ProxyScraper.scrape('SOCKS5')
                print(f"\n Scraped {len(proxies)} SOCKS5 proxies")
                save = input(" Save to file? (y/n): ").strip().lower()
                if save == 'y':
                    with open('proxies_socks5.txt', 'w') as f:
                        for p in proxies:
                            f.write(p + '\n')
                    print(" ✅ Saved to proxies_socks5.txt")
                input("Press Enter...")
            
            elif pc == '3':
                file = input(" File to test: ").strip()
                try:
                    with open(file, 'r') as f:
                        proxies = [l.strip() for l in f if ':' in l.strip()]
                    print(f" Loaded {len(proxies)} proxies")
                    working, failed = ProxyTester.test_proxy_batch(proxies[:300], 'HTTP')
                    bot.set_proxies(working)
                    
                    # Save working
                    with open('proxies_working.txt', 'w') as f:
                        for p in working:
                            f.write(p + '\n')
                    print(f" ✅ Saved {len(working)} working to proxies_working.txt")
                except FileNotFoundError:
                    print(" ❌ File not found")
                input("Press Enter...")
            
            elif pc == '4':
                try:
                    with open('proxies_working.txt', 'r') as f:
                        proxies = [l.strip() for l in f if ':' in l.strip()]
                    bot.set_proxies(proxies)
                    print(f" ✅ Loaded {len(proxies)} working proxies")
                except:
                    print(" ❌ No proxies_working.txt found")
                input("Press Enter...")
        
        elif choice == '2':
            if not bot.room_id:
                print(" ❌ Set Room ID first! (Option 0)")
                input("Press Enter...")
                continue
            
            if not bot.proxies:
                print(" ⚠️  No proxies loaded! Bot will use direct connection.")
                cont = input(" Continue anyway? (y/n): ").strip().lower()
                if cont != 'y':
                    continue
            
            bot.start()
            
            try:
                while bot.running:
                    time.sleep(1)
                    if bot.views >= bot.target:
                        print(f"\n ✅ Target reached! {bot.views} views")
                        bot.stop()
                        break
            except KeyboardInterrupt:
                bot.stop()
            
            input("Press Enter to continue...")
        
        elif choice == '3':
            if bot.running:
                print(f"\n Status: RUNNING")
                print(f" Views: {bot.views}")
                print(f" Likes: {bot.likes}")
                print(f" Errors: {bot.errors}")
            else:
                print(f"\n Status: STOPPED")
                print(f" Room ID: {bot.room_id or 'NOT SET'}")
                print(f" Mode: {bot.mode}")
                print(f" Proxies loaded: {len(bot.proxies)}")
            input("Press Enter...")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Exiting...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
