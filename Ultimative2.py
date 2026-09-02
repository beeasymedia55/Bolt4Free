import requests
import json
import time
import random
import string
import threading
import os
import sys
import hashlib
import urllib.parse
import base64
import logging
from itertools import cycle
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import re
import json

# ------------------------------
# LOGGING SETUP
# ------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('viewer_bot.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ------------------------------
# CONFIGURATION DATA CLASSES
# ------------------------------
class Settings:
    """Centralized configuration container."""
    def __init__(self):
        self.TIKTOK_API = "https://api22-normal-c-useast1a.tiktokv.com"
        self.TIKTOK_WEB = "https://www.tiktok.com"
        
        # Proxy Settings
        self.proxy_file = 'tiktok_proxies.txt'
        self.auto_test_proxies = True
        
        # Attack Parameters
        self.default_viewers = 1000
        self.default_duration = 600
        self.default_workers = 150
        
        # Timing & Heartbeat
        self.hb_min_interval = 25
        self.hb_max_interval = 35
        self.stagger_delay_min = 0.05
        self.stagger_delay_max = 0.3
        
        # Device Fingerprinting
        self.cycle_devices = True
        self.device_pool_size = 8
        
        # Signature Tuning
        self.signature_mode = 'simplified' # 'simplified', 'strict'
        
        # Anti-Ban
        self.max_failures_per_proxy = 3
        self.cooldown_time = 300 # seconds
        
        self.save() # Save defaults
        
    def save(self, filename='settings.json'):
        data = {
            'proxy_file': self.proxy_file,
            'default_viewers': self.default_viewers,
            'default_duration': self.default_duration,
            'default_workers': self.default_workers,
            'hb_min_interval': self.hb_min_interval,
            'hb_max_interval': self.hb_max_interval,
            'stagger_delay_min': self.stagger_delay_min,
            'stagger_delay_max': self.stagger_delay_max,
            'cycle_devices': self.cycle_devices,
            'signature_mode': self.signature_mode,
            'max_failures_per_proxy': self.max_failures_per_proxy,
            'cooldown_time': self.cooldown_time
        }
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
            
    def load(self, filename='settings.json'):
        if os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                for k, v in data.items():
                    if hasattr(self, k):
                        setattr(self, k, v)
            except Exception as e:
                log.warning(f"Could not load settings: {e}")

settings = Settings()
settings.load()

# ------------------------------
# DEVICE POOL
# ------------------------------
ANDROID_DEVICES = [
    {'device_id': 'android_7255253607933979658', 'iid': '72552536079339796580', 'openudid': 'f1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6', 'model': 'SM-G998B', 'brand': 'samsung', 'os_version': '13', 'resolution': '1440*3200', 'dpi': '560', 'os_api': '33', 'ua': 'com.zhiliaoapp.musically/20231212205426 (Linux; U; Android 13; en; SM-G998B Build/TP1A.220624.014; Cronet/112.0.5615.140)'},
    {'device_id': 'android_8355253607933979669', 'iid': '83552536079339796690', 'openudid': 'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d7', 'model': 'Pixel 8 Pro', 'brand': 'google', 'os_version': '14', 'resolution': '1344*2992', 'dpi': '420', 'os_api': '34', 'ua': 'com.zhiliaoapp.musically/20231212205426 (Linux; U; Android 14; en; Pixel 8 Pro Build/TP1A.220624.014; Cronet/112.0.5615.140)'},
    {'device_id': 'android_9455253612938979670', 'iid': '94552536129389796700', 'openudid': 'b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e8', 'model': 'OnePlus 12', 'brand': 'oneplus', 'os_version': '14', 'resolution': '1440*3168', 'dpi': '510', 'os_api': '34', 'ua': 'com.zhiliaoapp.musically/20231212205426 (Linux; U; Android 14; en; OnePlus 12 Build/TP1A.220624.014; Cronet/112.0.5615.140)'},
    {'device_id': 'android_1155253612938979671', 'iid': '11552536129389796710', 'openudid': 'c3d4e5f6a7b8c9d0e1f2a3b4c5d6e8f9', 'model': 'Xiaomi 14 Pro', 'brand': 'xiaomi', 'os_version': '14', 'resolution': '1440*3200', 'dpi': '522', 'os_api': '34', 'ua': 'com.zhiliaoapp.musically/20231212205426 (Linux; U; Android 14; en; Xiaomi 14 Pro Build/TP1A.220624.014; Cronet/112.0.5615.140)'},
    {'device_id': 'android_1255253612938979672', 'iid': '12552536129389796720', 'openudid': 'd4e5f6a7b8c9d0e1f2a3b4c5d6e8f9a0', 'model': 'Pixel 7', 'brand': 'google', 'os_version': '13', 'resolution': '1080*2400', 'dpi': '420', 'os_api': '33', 'ua': 'com.zhiliaoapp.musically/20231212205426 (Linux; U; Android 13; en; Pixel 7 Build/TP1A.220624.014; Cronet/112.0.5615.140)'},
    {'device_id': 'android_1355253612938979673', 'iid': '13552536129389796730', 'openudid': 'e5f6a7b8c9d0e1f2a3b4c5d6e8f9a0b1', 'model': 'SM-S928B', 'brand': 'samsung', 'os_version': '14', 'resolution': '1440*3200', 'dpi': '560', 'os_api': '34', 'ua': 'com.zhiliaoapp.musically/20231212205426 (Linux; U; Android 14; en; SM-S928B Build/TP1A.220624.014; Cronet/112.0.5615.140)'},
    {'device_id': 'android_1455253612938979674', 'iid': '14552536129389796740', 'openudid': 'f6a7b8c9d0e1f2a3b4c5d6e8f9a0b1c2', 'model': 'Moto G Power', 'brand': 'motorola', 'os_version': '13', 'resolution': '1080*2400', 'dpi': '400', 'os_api': '33', 'ua': 'com.zhiliaoapp.musically/20231212205426 (Linux; U; Android 13; en; Moto G Power Build/TP1A.220624.014; Cronet/112.0.5615.140)'},
    {'device_id': 'android_1555253612938979675', 'iid': '15552536129389796750', 'openudid': 'a7b8c9d0e1f2a3b4c5d6e8f9a0b1c2d3', 'model': 'Xperia 1 V', 'brand': 'sony', 'os_version': '13', 'resolution': '1644*3840', 'dpi': '643', 'os_api': '33', 'ua': 'com.zhiliaoapp.musically/20231212205426 (Linux; U; Android 13; en; Xperia 1 V Build/TP1A.220624.014; Cronet/112.0.5615.140)'},
]

# ------------------------------
# SIGNATURE GENERATION
# ------------------------------
def generate_x_bogus(params, device_id='7255253607933979658'):
    """Generate TikTok X-Bogus signature (simplified)"""
    keys = sorted(params.keys())
    query = '&'.join([f"{k}={urllib.parse.quote(str(params[k]))}" for k in keys])
    
    # Build signature string
    sig_base = f"{query}&device_id={device_id}"
    sig = hashlib.md5(sig_base.encode()).hexdigest()
    
    # X-Bogus format: 3 chars header + hash + 3 chars footer
    header = ''.join(random.choices(string.ascii_letters + string.digits, k=3))
    footer = ''.join(random.choices(string.ascii_letters + string.digits, k=3))
    
    return f"{header}{sig[:27]}{footer}"

def generate_x_ss_stub(params):
    """Generate X-SS-STUB signature"""
    keys = sorted(params.keys())
    query = json.dumps({k: params[k] for k in keys}, separators=(',', ':'))
    return hashlib.sha256(query.encode()).hexdigest()

# ------------------------------
# VIEWER BOT ENGINE
# ------------------------------
class ProxyManager:
    """Manages proxy health and quality scores."""
    def __init__(self):
        self.proxy_stats = {} # proxy -> {'failures': 0, 'score': 1.0}
        self.cooldowns = {}   # proxy -> timestamp
    
    def record_failure(self, proxy):
        if proxy not in self.proxy_stats:
            self.proxy_stats[proxy] = {'failures': 0, 'score': 1.0}
        self.proxy_stats[proxy]['failures'] += 1
        if self.proxy_stats[proxy]['failures'] >= settings.max_failures_per_proxy:
            self.cooldowns[proxy] = time.time()
            log.warning(f"Proxy {proxy} exceeded max failures, cooling down.")

    def record_success(self, proxy):
        if proxy not in self.proxy_stats:
            self.proxy_stats[proxy] = {'failures': 0, 'score': 1.0}
        self.proxy_stats[proxy]['score'] = min(1.0, self.proxy_stats[proxy]['score'] + 0.1)
        self.proxy_stats[proxy]['failures'] = max(0, self.proxy_stats[proxy]['failures'] - 1)

    def is_cooldown_active(self, proxy):
        if proxy in self.cooldowns:
            if time.time() - self.cooldowns[proxy] < settings.cooldown_time:
                return True
            else:
                # Remove old cooldown
                del self.cooldowns[proxy]
        return False

    def get_best_proxy(self, proxy_list):
        # Filter out cooldown proxies
        available = [p for p in proxy_list if p != 'direct' and not self.is_cooldown_active(p)]
        if not available:
            return 'direct'
        
        # Sort by score descending
        available.sort(key=lambda p: self.proxy_stats.get(p, {'score': 1.0})['score'], reverse=True)
        return available[0]

class TikTokViewerBot:
    def __init__(self, settings_obj):
        self.settings = settings_obj
        self.proxies = self._load_proxies(self.settings.proxy_file)
        self.proxy_pool = cycle(self.proxies)
        self.device_pool = cycle(ANDROID_DEVICES)
        self.proxy_manager = ProxyManager()
        self.session_pool = {}
        self.lock = threading.Lock()
        self.stats = {
            'views_injected': 0,
            'active_viewers': 0,
            'success_joins': 0,
            'failed_joins': 0,
            'heartbeats_sent': 0,
            'start_time': datetime.now()
        }
        self.running = True
        
        if len(self.proxies) == 0:
            log.warning("No proxies found! Using direct connection (will be blocked quickly)")
        else:
            log.info(f"Loaded {len(self.proxies)} proxies")
        
    def _load_proxies(self, filename):
        """Load proxy list"""
        proxies = []
        if filename and os.path.exists(filename):
            with open(filename) as f:
                proxies = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        if not proxies:
            proxies = ['direct']
        return proxies

    def _get_session(self, proxy):
        """Get or create a requests session for a proxy"""
        if proxy not in self.session_pool:
            session = requests.Session()
            session.headers.update({
                'Accept': '*/*',
                'Accept-Encoding': 'gzip',
                'Accept-Language': 'en,en-US;q=0.9',
                'Content-Type': 'application/json; charset=utf-8',
                'Connection': 'keep-alive',
                'Host': 'api22-normal-c-useast1a.tiktokv.com',
            })
            
            if proxy != 'direct':
                session.proxies = {
                    'http': proxy,
                    'https': proxy
                }
            self.session_pool[proxy] = session
        return self.session_pool[proxy]
    
    def _get_android_headers(self, device):
        """Generate Android app headers"""
        return {
            'User-Agent': device['ua'],
            'X-Tt-Token': ''.join(random.choices('0123456789abcdef', k=32)),
            'X-Khronos': str(int(time.time())),
        }
    
    def _generate_params(self, room_id, device, extra=None):
        """Generate full request params with device fingerprint"""
        ts = int(time.time())
        params = {
            'device_id': device['device_id'],
            'iid': device['iid'],
            'openudid': device['openudid'],
            'device_platform': 'android',
            'os_version': device['os_version'],
            'resolution': device['resolution'],
            'dpi': device['dpi'],
            'os_api': device['os_api'],
            'aid': '1180',
            'app_version': '35.7.0',
            'app_name': 'trill',
            'channel': 'googleplay',
            'build_number': '357000',
            'tz_name': 'America/New_York',
            'sys_region': 'US',
            'app_language': 'en',
            'language': 'en',
            'region': 'US',
            '_rticket': ts * 1000,
            'ts': ts,
            'room_id': room_id,
            'cdid': ''.join(random.choices(string.hexdigits, k=32)).lower(),
            'req_id': ''.join(random.choices(string.hexdigits, k=32)).upper(),
            'mcc_mnc': '310410',
        }
        if extra:
            params.update(extra)
        return params
    
    def _sign_headers(self, params):
        """Add signed headers to request"""
        device_id = params.get('device_id', '7255253607933979658')
        url_params = {k: v for k, v in params.items() if k not in ['device_platform', 'os_version', 'resolution', 'dpi', 'os_api', 'aid', 'app_version', 'app_name', 'channel', 'build_number']}
        
        return {
            'X-Bogus': generate_x_bogus(url_params, device_id),
            'X-SS-STUB': generate_x_ss_stub(url_params),
            'X-Ladon': ''.join(random.choices(string.hexdigits, k=32)).lower(),
        }
    
    def _join_live_room(self, session, room_id, device, proxy):
        """Join a live room - this adds +1 to viewer count"""
        url = f"{self.settings.TIKTOK_API}/aweme/v1/webcast/join/"
        
        params = self._generate_params(room_id, device, {
            'enter_from': random.choice(['live_center', 'feed', 'share', 'scan', 'push']),
            'enter_method': random.choice(['scan', 'feed', 'share', 'push']),
            'priority_region': 'US',
            'live_id': random.randint(100000, 999999),
        })
        
        signed = self._sign_headers(params)
        headers = self._get_android_headers(device)
        headers.update(signed)
        
        payload = {
            "room_id": int(room_id),
            "user_id": f"viewer_{random.randint(10000000, 99999999)}",
            "enter_method": params['enter_method'],
            "device_id": params['device_id'],
            "iid": params['iid'],
            "live_id": params['live_id'],
            "priority_region": "US"
        }
        
        try:
            resp = session.post(url, json=payload, headers=headers, timeout=12)
            if resp.status_code in [200, 204, 0]:
                with self.lock:
                    self.stats['success_joins'] += 1
                    self.stats['active_viewers'] += 1
                    self.stats['views_injected'] += 1
                self.proxy_manager.record_success(proxy)
                return True
            else:
                with self.lock:
                    self.stats['failed_joins'] += 1
                self.proxy_manager.record_failure(proxy)
                return False
        except Exception as e:
            with self.lock:
                self.stats['failed_joins'] += 1
            self.proxy_manager.record_failure(proxy)
            return False
    
    def _heartbeat(self, session, room_id, device, proxy):
        """Send periodic heartbeats to keep viewer counted"""
        url = f"{self.settings.TIKTOK_API}/aweme/v1/webcast/enter/"
        
        while self.running:
            try:
                params = self._generate_params(room_id, device, {
                    'status': 1,
                    'live_id': random.randint(1, 99999),
                })
                signed = self._sign_headers(params)
                headers = self._get_android_headers(device)
                headers.update(signed)
                
                payload = {
                    "room_id": int(room_id),
                    "status": 1,
                    "device_id": params['device_id'],
                    "live_id": params['live_id']
                }
                
                session.post(url, json=payload, headers=headers, timeout=8)
                
                with self.lock:
                    self.stats['heartbeats_sent'] += 1
                
                # Use settings for interval
                time.sleep(random.uniform(self.settings.hb_min_interval, self.settings.hb_max_interval))
            except:
                time.sleep(5)
    
    def _leave_room(self, session, room_id, device):
        """Leave the live room gracefully"""
        url = f"{self.settings.TIKTOK_API}/aweme/v1/webcast/leave/"
        params = self._generate_params(room_id, device)
        signed = self._sign_headers(params)
        headers = self._get_android_headers(device)
        headers.update(signed)
        
        payload = {
            "room_id": int(room_id),
            "device_id": params['device_id']
        }
        try:
            session.post(url, json=payload, headers=headers, timeout=8)
        except:
            pass
        
        with self.lock:
            self.stats['active_viewers'] -= 1
    
    def simulate_viewer(self, room_id, duration_seconds=600):
        """Simulate a single viewer: join -> heartbeat -> leave"""
        # Get best proxy instead of cycling
        proxy = self.proxy_manager.get_best_proxy(self.proxies)
        if proxy == 'direct':
            proxy = next(self.proxy_pool) # Fallback
        
        session = self._get_session(proxy)
        device = next(self.device_pool)
        
        # Join the live room
        if not self._join_live_room(session, room_id, device, proxy):
            return False
        
        # Start heartbeat thread
        hb_thread = threading.Thread(
            target=self._heartbeat,
            args=(session, room_id, device, proxy),
            daemon=True
        )
        hb_thread.start()
        
        # Stay for specified duration
        end_time = time.time() + duration_seconds
        while self.running and time.time() < end_time:
            time.sleep(1)
        
        # Leave
        self._leave_room(session, room_id, device)
        return True
    
    def print_stats(self):
        """Print current stats"""
        elapsed = (datetime.now() - self.stats['start_time']).total_seconds()
        rate = self.stats['views_injected'] / elapsed if elapsed > 0 else 0
        
        print(f"\r[📺] Views: {self.stats['views_injected']:,} | "
              f"Active: {self.stats['active_viewers']} | "
              f"Joins: {self.stats['success_joins']:,} ✓ / {self.stats['failed_joins']:,} ✗ | "
              f"Heartbeats: {self.stats['heartbeats_sent']:,} | "
              f"Rate: {rate:.1f}/s | "
              f"Elapsed: {int(elapsed)}s", end='', flush=True)
    
    def launch_attack(self, room_id, viewer_count=None, duration_seconds=None, workers=None):
        """Launch the viewer injection attack"""
        # Apply settings defaults if not specified
        if viewer_count is None: viewer_count = self.settings.default_viewers
        if duration_seconds is None: duration_seconds = self.settings.default_duration
        if workers is None: workers = self.settings.default_workers
        
        log.info(f"{'='*60}")
        log.info(f"🚀 TIKTOK LIVE VIEWER INJECTION")
        log.info(f"📡 Room ID: {room_id}")
        log.info(f"👥 Target Viewers: {viewer_count:,}")
        log.info(f"⏱ Duration: {duration_seconds}s ({duration_seconds//60}m)")
        log.info(f"⚖️ Workers: {workers}")
        log.info(f"🔎 Proxies: {len(self.proxies)}")
        log.info(f"{'='*60}")
        
        self.stats['start_time'] = datetime.now()
        
        # Start stats printer thread
        stats_thread = threading.Thread(target=self._stats_loop, daemon=True)
        stats_thread.start()
        
        # Deploy viewers
        successful = 0
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {}
            
            for i in range(viewer_count):
                future = executor.submit(self.simulate_viewer, room_id, duration_seconds)
                futures[future] = i
            
            # Stagger joins
            stagger = random.uniform(self.settings.stagger_delay_min, self.settings.stagger_delay_max)
            time.sleep(stagger)
            
            # Collect results
            for future in as_completed(futures):
                if future.result():
                    successful += 1
        
        elapsed = time.time() - start_time
        self.running = False
        
        print() # Newline after stats
        log.info(f"{'='*60}")
        log.info(f"✅ ATTACK COMPLETE")
        log.info(f"📊 Final Statistics:")
        
        with self.lock:
            log.info(f" Views Injected: {self.stats['views_injected']:,}")
            log.info(f" Successful Joins: {self.stats['success_joins']:,}")
            log.info(f" Failed Joins: {self.stats['failed_joins']:,}")
            log.info(f" Heartbeats Sent: {self.stats['heartbeats_sent']:,}")
            log.info(f" Peak Active: {max(1, self.stats['active_viewers'])}")
            log.info(f" Duration: {elapsed:.1f}s")
            log.info(f" Average Rate: {self.stats['views_injected']/elapsed:.1f} viewers/s")
            total_joins = self.stats['success_joins'] + self.stats['failed_joins']
            success_rate = (self.stats['success_joins'] / (total_joins + 0.001)) * 100
            log.info(f" Success Rate: {success_rate:.1f}%")
        
        log.info(f"{'='*60}")
        return successful
    
    def _stats_loop(self):
        """Print stats periodically"""
        while self.running:
            self.print_stats()
            time.sleep(2)
    
    def stop(self):
        """Stop all operations"""
        self.running = False
        log.info("Stopping all viewers...")

# ------------------------------
# ROOM ID EXTRACTION
# ------------------------------
def extract_room_id_from_url(url):
    """Extract room_id from TikTok live URL"""
    patterns = [
        r'room_id=(\d+)',
        r'/live/(\d+)',
        r'live\.tiktok\.com/(\d+)'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_live_room_info(username, proxies=None):
    """Get live room info from TikTok profile"""
    url = f"{settings.TIKTOK_WEB}/@{username}/live"
    session = requests.Session()
    if proxies:
        proxy = random.choice(proxies) if isinstance(proxies, list) else proxies
        if proxy != 'direct':
            session.proxies = {'http': proxy, 'https': proxy}
    
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,*/*',
        'Accept-Language': 'en-US,en;q=0.9',
    })
    
    try:
        api_url = f"{settings.TIKTOK_API}/aweme/v1/webcast/user/"
        params = {'user_id': username, 'aid': '1988'}
        resp = session.get(api_url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            if 'room_id' in data:
                return data['room_id']
        
        resp = session.get(url, timeout=10)
        room_id_match = re.search(r'room_id["\']?\s*[:=]\s*["\']?(\d+)', resp.text)
        if room_id_match:
            return room_id_match.group(1)
    except Exception as e:
        log.error(f"Error fetching live info: {e}")
    return None

# ------------------------------
# MENU SYSTEM
# ------------------------------
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_menu(title, items):
    print(f"\n{'='*40}")
    print(f" {title}")
    print(f"{'='*40}")
    for i, item in enumerate(items, 1):
        print(f"{i}. {item}")
    print(f"{len(items)+1}. Back to Main Menu")
    print("="*40)

def test_proxy(proxy, settings):
    """Test a single proxy's connectivity to TikTok API"""
    session = requests.Session()
    session.proxies = {'http': proxy, 'https': proxy}
    try:
        resp = session.get(settings.TIKTOK_WEB, timeout=5)
        if resp.status_code == 200:
            return True
    except:
        pass
    return False

def proxy_management_menu(bot):
    while True:
        items = [
            f"Current Proxy File: {settings.proxy_file}",
            f"Loaded Proxies: {len(bot.proxies)}",
            "Test All Proxies",
            "Change Proxy File",
            "Add Single Proxy",
            "Clear Proxies",
            "View Proxy Health"
        ]
        print_menu("Proxy Management", items)
        try:
            choice = int(input(">> ").strip())
        except ValueError:
            continue
            
        if choice == 1:
            print(f"\nFile: {settings.proxy_file}")
        elif choice == 2:
            print(f"\nTotal: {len(bot.proxies)}")
            if bot.proxies:
                for i, p in enumerate(bot.proxies[:5]):
                    print(f"  {i+1}: {p}")
                if len(bot.proxies) > 5:
                    print(f"  ... and {len(bot.proxies)-5} more")
        elif choice == 3:
            print("\nTesting proxies... (This may take a moment)")
            tested = 0
            working = 0
            for proxy in bot.proxies:
                if proxy == 'direct':
                    continue
                if test_proxy(proxy, settings):
                    working += 1
                tested += 1
                if tested % 50 == 0:
                    print(f"  Tested {tested}...")
            print(f"\nTest Complete: {working}/{tested} proxies working.")
        elif choice == 4:
            new_file = input("Enter proxy file path (relative to script): ").strip()
            if os.path.exists(new_file):
                settings.proxy_file = new_file
                settings.save()
                bot.proxies = bot._load_proxies(new_file)
                bot.proxy_pool = cycle(bot.proxies)
                print(f"Switched to {new_file}")
            else:
                print("File not found.")
        elif choice == 5:
            proxy = input("Enter proxy (host:port): ").strip()
            if proxy:
                bot.proxies.append(proxy)
                bot.proxy_pool = cycle(bot.proxies)
                # Save to file
                with open(settings.proxy_file, 'a') as f:
                    f.write(f"\n{proxy}")
                print(f"Added {proxy}")
        elif choice == 6:
            bot.proxies = []
            bot.proxy_pool = cycle(bot.proxies)
            # Clear file
            with open(settings.proxy_file, 'w') as f:
                f.write("")
            print("Proxies cleared.")
        elif choice == 7:
            print("\nProxy Health Stats:")
            for proxy, stats in bot.proxy_manager.proxy_stats.items():
                cooldown_active = bot.proxy_manager.is_cooldown_active(proxy)
                status = "COOLDOWN" if cooldown_active else "Active"
                print(f"  {proxy}: Score={stats['score']:.2f}, Failures={stats['failures']}, Status={status}")
        elif choice == len(items) + 1:
            break

def timing_settings_menu():
    while True:
        items = [
            f"Heartbeat Min: {settings.hb_min_interval}s",
            f"Heartbeat Max: {settings.hb_max_interval}s",
            f"Stagger Delay Min: {settings.stagger_delay_min}s",
            f"Stagger Delay Max: {settings.stagger_delay_max}s",
            "Set Fast Mode (Low Lag)",
            "Set Stable Mode (High Survivability)"
        ]
        print_menu("Timing & Heartbeat Settings", items)
        try:
            choice = int(input(">> ").strip())
        except ValueError:
            continue
            
        if choice == 1:
            val = float(input("New Min Interval (s): "))
            if val < settings.hb_max_interval:
                settings.hb_min_interval = val
                settings.save()
                print(f"Set Min to {val}")
        elif choice == 2:
            val = float(input("New Max Interval (s): "))
            if val > settings.hb_min_interval:
                settings.hb_max_interval = val
                settings.save()
                print(f"Set Max to {val}")
        elif choice == 3:
            val = float(input("New Min Stagger (s): "))
            settings.stagger_delay_min = val
            settings.save()
        elif choice == 4:
            val = float(input("New Max Stagger (s): "))
            settings.stagger_delay_max = val
            settings.save()
        elif choice == 5:
            settings.hb_min_interval = 10
            settings.hb_max_interval = 15
            settings.stagger_delay_min = 0.01
            settings.stagger_delay_max = 0.05
            settings.save()
            print("Set Fast Mode.")
        elif choice == 6:
            settings.hb_min_interval = 30
            settings.hb_max_interval = 45
            settings.stagger_delay_min = 0.2
            settings.stagger_delay_max = 0.5
            settings.save()
            print("Set Stable Mode.")
        elif choice == len(items) + 1:
            break

def attack_defaults_menu():
    while True:
        items = [
            f"Default Viewers: {settings.default_viewers}",
            f"Default Duration: {settings.default_duration}s",
            f"Default Workers: {settings.default_workers}"
        ]
        print_menu("Attack Defaults", items)
        try:
            choice = int(input(">> ").strip())
        except ValueError:
            continue
            
        if choice == 1:
            val = int(input("Default Viewers: "))
            settings.default_viewers = val
            settings.save()
        elif choice == 2:
            val = int(input("Default Duration (s): "))
            settings.default_duration = val
            settings.save()
        elif choice == 3:
            val = int(input("Default Workers: "))
            settings.default_workers = val
            settings.save()
        elif choice == len(items) + 1:
            break

def launch_attack_menu(bot):
    print("\n--- Launch Attack ---")
    room_id = input("Room ID (or URL): ").strip()
    
    # Extract room ID if URL provided
    if not room_id.isdigit():
        room_id = extract_room_id_from_url(room_id)
        if not room_id:
            # Try username extraction
            if '@' in room_id:
                username = room_id.replace('@', '')
                room_id = get_live_room_info(username, bot.proxies)
            if not room_id:
                print("Could not resolve Room ID.")
                return

    print(f"Target: {room_id}")
    viewer_count = int(input(f"Viewers [{settings.default_viewers}]: ") or settings.default_viewers)
    duration = int(input(f"Duration [s] [{settings.default_duration}]: ") or settings.default_duration)
    workers = int(input(f"Workers [{settings.default_workers}]: ") or settings.default_workers)
    
    input("\nPress Enter to start attack...")
    bot.launch_attack(room_id, viewer_count, duration, workers)

def main_menu():
    bot = TikTokViewerBot(settings)
    
    while True:
        clear_screen()
        print("""
╔══════════════════════════════════════╗
║     TIKTOK LIVE VIEWER INJECTION     ║
║          Ultimate Edition v2.0       ║
║         Enhanced Anti-Ban System     ║
╚══════════════════════════════════════╝
""")
        items = [
            "Launch Attack",
            "Proxy Management",
            "Timing & Heartbeat Settings",
            "Attack Defaults",
            "Save & Exit"
        ]
        print_menu("Main Menu", items)
        try:
            choice = int(input(">> ").strip())
        except ValueError:
            continue
            
        if choice == 1:
            launch_attack_menu(bot)
        elif choice == 2:
            proxy_management_menu(bot)
        elif choice == 3:
            timing_settings_menu()
        elif choice == 4:
            attack_defaults_menu()
        elif choice == 5:
            settings.save()
            print("Settings saved. Exiting.")
            break

if __name__ == "__main__":
    main_menu()
