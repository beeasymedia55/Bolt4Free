import requests
import json
import time
import random
import string
import threading
import os
import sys
import re
import base64
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import uuid
import hashlib
import urllib.parse
import argparse
import urllib.request
import urllib.error
import urllib.parse
import io
import socket
import struct
import time as time_module

# ------------------------------
# LOGGING SETUP
# ------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('hybrid_bot.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ------------------------------
# CONFIGURATION
# ------------------------------
class Settings:
    def __init__(self):
        self.TIKTOK_API = "https://api22-normal-c-useast1a.tiktokv.com"
        self.TIKTOK_WEB = "https://www.tiktok.com"
        self.proxy_file = 'tiktok_proxies.txt'
        self.session_file = 'session.txt'
        self.default_viewers = 500
        self.default_duration = 600
        self.default_workers = 100
        self.hb_min = 25
        self.hb_max = 35
        self.stagger_min = 0.05
        self.stagger_max = 0.3
        self.auto_test_proxies = True
        
    def save(self, filename='hybrid_settings.json'):
        data = {
            'proxy_file': self.proxy_file,
            'session_file': self.session_file,
            'default_viewers': self.default_viewers,
            'default_duration': self.default_duration,
            'default_workers': self.default_workers,
            'hb_min': self.hb_min,
            'hb_max': self.hb_max,
            'stagger_min': self.stagger_min,
            'stagger_max': self.stagger_max
        }
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)

    def load(self, filename='hybrid_settings.json'):
        if os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)
                for k, v in data.items():
                    if hasattr(self, k):
                        setattr(self, k, v)
            except:
                pass

settings = Settings()
settings.load()

# ------------------------------
# DEVICE POOL
# ------------------------------
ANDROID_DEVICES = [
    {'device_id': '7255253607933979658', 'iid': '72552536079339796580', 'openudid': 'f1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6', 'model': 'SM-G998B', 'brand': 'samsung', 'os_version': '13', 'resolution': '1440*3200', 'dpi': '560', 'os_api': '33', 'ua': 'com.zhiliaoapp.musically/20231212205426 (Linux; U; Android 13; en; SM-G998B Build/TP1A.220624.014; Cronet/112.0.5615.140)'},
    {'device_id': '8355253607933979669', 'iid': '83552536079339796690', 'openudid': 'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d7', 'model': 'Pixel 8 Pro', 'brand': 'google', 'os_version': '14', 'resolution': '1344*2992', 'dpi': '420', 'os_api': '34', 'ua': 'com.zhiliaoapp.musically/20231212205426 (Linux; U; Android 14; en; Pixel 8 Pro Build/TP1A.220624.014; Cronet/112.0.5615.140)'},
    {'device_id': '9455253612938979670', 'iid': '94552536129389796700', 'openudid': 'b2c3d4e5f6a7b8c9d0e1f2a3b4c5d8', 'model': 'OnePlus 12', 'brand': 'oneplus', 'os_version': '14', 'resolution': '1440*3168', 'dpi': '510', 'os_api': '34', 'ua': 'com.zhiliaoapp.musically/20231212205426 (Linux; U; Android 14; en; OnePlus 12 Build/TP1A.220624.014; Cronet/112.0.5615.140)'},
    {'device_id': '1155253612938979671', 'iid': '11552536129389796710', 'openudid': 'c3d4e5f6a7b8c9d0e1f2a3b4c5d9', 'model': 'Xiaomi 14 Pro', 'brand': 'xiaomi', 'os_version': '14', 'resolution': '1440*3200', 'dpi': '522', 'os_api': '34', 'ua': 'com.zhiliaoapp.musically/20231212205426 (Linux; U; Android 14; en; Xiaomi 14 Pro Build/TP1A.220624.014; Cronet/112.0.5615.140)'},
]

# ------------------------------
# SIGNATURE GENERATION
# ------------------------------
def generate_x_bogus(params, device_id='7255253607933979658'):
    keys = sorted(params.keys())
    query = '&'.join([f"{k}={urllib.parse.quote(str(params[k]))}" for k in keys])
    sig_base = f"{query}&device_id={device_id}"
    sig = hashlib.md5(sig_base.encode()).hexdigest()
    header = ''.join(random.choices(string.ascii_letters + string.digits, k=3))
    footer = ''.join(random.choices(string.ascii_letters + string.digits, k=3))
    return f"{header}{sig[:27]}{footer}"

def generate_x_ss_stub(params):
    keys = sorted(params.keys())
    query = json.dumps({k: params[k] for k in keys}, separators=(',', ':'))
    return hashlib.sha256(query.encode()).hexdigest()

# ------------------------------
# ACCOUNT GENERATOR
# ------------------------------
class AccountGenerator:
    def __init__(self, settings_obj):
        self.settings = settings_obj
        self.proxies = self._load_proxies(settings_obj.proxy_file)
        self.session_pool = {}
        
    def _load_proxies(self, filename):
        proxies = []
        if filename and os.path.exists(filename):
            with open(filename) as f:
                proxies = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        if not proxies:
            proxies = ['direct']
        return proxies

    def _get_session(self, proxy):
        if proxy not in self.session_pool:
            session = requests.Session()
            session.headers.update({
                'Accept': '*/*',
                'Accept-Encoding': 'gzip',
                'Accept-Language': 'en,en-US;q=0.9',
                'Connection': 'keep-alive',
            })
            if proxy != 'direct':
                session.proxies = {'http': proxy, 'https': proxy}
            self.session_pool[proxy] = session
        return self.session_pool[proxy]

    def _get_random_device(self):
        return random.choice(ANDROID_DEVICES)

    def _generate_temp_email(self, device):
        username = ''.join(random.choices(string.ascii_lowercase, k=10))
        domain = random.choice(['1secmail.com', '1secmail.net', '1secmail.org', 'wuzup.com', 'wuzup.net'])
        return f"{username}@{domain}"

    def register_account(self, proxy, device):
        session = self._get_session(proxy)
        email = self._generate_temp_email(device)
        
        url = f"{self.settings.TIKTOK_WEB}/passport/email/send/"
        params = {
            'email': email,
            'aid': '1988',
            'service': 'https://www.tiktok.com',
            'region': 'US',
            'language': 'en',
            'app_name': 'trill',
            'app_version': '35.7.0',
            'channel': 'googleplay',
            'device_id': device['device_id'],
            'iid': device['iid'],
        }
        
        try:
            headers = {
                'User-Agent': device['ua'],
                'X-Tt-Token': ''.join(random.choices('0123456789abcdef', k=32)),
                'X-Khronos': str(int(time.time())),
            }
            
            resp = session.get(url, params=params, headers=headers, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                if data.get('code') == 0:
                    log.info(f"2FA sent to {email}")
                    return {
                        'email': email,
                        'status': 'waiting_2fa',
                        'proxy': proxy,
                        'device': device,
                        'session': session
                    }
                else:
                    log.error(f"Registration failed: {data.get('message')}")
                    return None
            else:
                return None
        except Exception as e:
            log.error(f"Error registering: {e}")
            return None

    def verify_2fa(self, email, code, proxy, device):
        session = self._get_session(proxy)
        url = f"{self.settings.TIKTOK_WEB}/passport/email/verify/"
        params = {
            'email': email,
            'code': code,
            'aid': '1988',
            'service': 'https://www.tiktok.com',
            'region': 'US',
            'language': 'en',
            'app_name': 'trill',
            'app_version': '35.7.0',
            'channel': 'googleplay',
            'device_id': device['device_id'],
            'iid': device['iid'],
        }
        
        try:
            headers = {
                'User-Agent': device['ua'],
                'X-Tt-Token': ''.join(random.choices('0123456789abcdef', k=32)),
                'X-Khronos': str(int(time.time())),
            }
            
            resp = session.get(url, params=params, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('code') == 0:
                    token = resp.cookies.get('tt_chain_token')
                    session_id = resp.cookies.get('session_id')
                    return {
                        'email': email,
                        'token': token,
                        'session_id': session_id,
                        'proxy': proxy,
                        'device': device,
                        'status': 'verified'
                    }
        except:
            pass
        return None

    def save_session(self, session_data):
        if session_data['status'] == 'verified':
            line = f"{session_data['email']}:{session_data['token']}:{session_data['session_id']}"
            with open(self.settings.session_file, 'a') as f:
                f.write(line + '\n')
            log.info(f"Saved session for {session_data['email']}")

# ------------------------------
# VIEWER BOT ENGINE
# ------------------------------
class TikTokViewerBot:
    def __init__(self, settings_obj):
        self.settings = settings_obj
        self.proxies = self._load_proxies(settings_obj.proxy_file)
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
        self.sessions = self._load_sessions(settings_obj.session_file)
        self.session_cycle = cycle(self.sessions) if self.sessions else None

    def _load_proxies(self, filename):
        proxies = []
        if filename and os.path.exists(filename):
            with open(filename) as f:
                proxies = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        if not proxies:
            proxies = ['direct']
        return proxies

    def _load_sessions(self, filename):
        sessions = []
        if filename and os.path.exists(filename):
            with open(filename) as f:
                for line in f:
                    parts = line.strip().split(':')
                    if len(parts) >= 3:
                        sessions.append({
                            'email': parts[0],
                            'token': parts[1],
                            'session_id': parts[2]
                        })
        return sessions

    def _get_session(self, proxy):
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
                session.proxies = {'http': proxy, 'https': proxy}
            self.session_pool[proxy] = session
        return self.session_pool[proxy]

    def _get_android_headers(self, device, token=None):
        headers = {
            'User-Agent': device['ua'],
            'X-Khronos': str(int(time.time())),
        }
        if token:
            headers['X-Tt-Token'] = token
        return headers

    def _generate_params(self, room_id, device, extra=None):
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
        device_id = params.get('device_id', '7255253607933979658')
        url_params = {k: v for k, v in params.items() if k not in ['device_platform', 'os_version', 'resolution', 'dpi', 'os_api', 'aid', 'app_version', 'app_name', 'channel', 'build_number']}
        return {
            'X-Bogus': generate_x_bogus(url_params, device_id),
            'X-SS-STUB': generate_x_ss_stub(url_params),
            'X-Ladon': ''.join(random.choices(string.hexdigits, k=32)).lower(),
        }

    def _join_live_room(self, session, room_id, device, token=None):
        url = f"{self.settings.TIKTOK_API}/aweme/v1/webcast/join/"
        params = self._generate_params(room_id, device, {
            'enter_from': random.choice(['live_center', 'feed', 'share', 'scan', 'push']),
            'enter_method': random.choice(['scan', 'feed', 'share', 'push']),
            'priority_region': 'US',
            'live_id': random.randint(100000, 999999),
        })
        signed = self._sign_headers(params)
        headers = self._get_android_headers(device, token)
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
                return True
            else:
                with self.lock:
                    self.stats['failed_joins'] += 1
                return False
        except Exception as e:
            with self.lock:
                self.stats['failed_joins'] += 1
            return False

    def _heartbeat(self, session, room_id, device, token=None):
        url = f"{self.settings.TIKTOK_API}/aweme/v1/webcast/enter/"
        while self.running:
            try:
                params = self._generate_params(room_id, device, {
                    'status': 1,
                    'live_id': random.randint(1, 99999),
                })
                signed = self._sign_headers(params)
                headers = self._get_android_headers(device, token)
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
                time.sleep(random.uniform(self.settings.hb_min, self.settings.hb_max))
            except:
                time.sleep(5)

    def _leave_room(self, session, room_id, device, token=None):
        url = f"{self.settings.TIKTOK_API}/aweme/v1/webcast/leave/"
        params = self._generate_params(room_id, device)
        signed = self._sign_headers(params)
        headers = self._get_android_headers(device, token)
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
        if self.sessions:
            session_data = next(self.session_cycle)
            token = session_data['token']
            proxy = random.choice(self.proxies)
        else:
            proxy = random.choice(self.proxies)
            token = None
            
        session = self._get_session(proxy)
        device = random.choice(ANDROID_DEVICES)
        
        if not self._join_live_room(session, room_id, device, token):
            return False
        
        hb_thread = threading.Thread(
            target=self._heartbeat,
            args=(session, room_id, device, token),
            daemon=True
        )
        hb_thread.start()
        
        end_time = time.time() + duration_seconds
        while self.running and time.time() < end_time:
            time.sleep(1)
        
        self._leave_room(session, room_id, device, token)
        return True

    def print_stats(self):
        elapsed = (datetime.now() - self.stats['start_time']).total_seconds()
        rate = self.stats['views_injected'] / elapsed if elapsed > 0 else 0
        print(f"\r[📺] Views: {self.stats['views_injected']:,} | "
              f"Active: {self.stats['active_viewers']} | "
              f"Joins: {self.stats['success_joins']:,} ✓ / {self.stats['failed_joins']:,} ✗ | "
              f"Heartbeats: {self.stats['heartbeats_sent']:,} | "
              f"Rate: {rate:.1f}/s | "
              f"Elapsed: {int(elapsed)}s", end='', flush=True)

    def launch_attack(self, room_id, viewer_count=None, duration_seconds=None, workers=None):
        if viewer_count is None: viewer_count = self.settings.default_viewers
        if duration_seconds is None: duration_seconds = self.settings.default_duration
        if workers is None: workers = self.settings.default_workers
        
        log.info(f"{'='*60}")
        log.info(f"🚀 TIKTOK LIVE VIEWER INJECTION (HYBRID MODE)")
        log.info(f"📡 Room ID: {room_id}")
        log.info(f"👥 Target Viewers: {viewer_count:,}")
        log.info(f"⏱ Duration: {duration_seconds}s ({duration_seconds//60}m)")
        log.info(f"⚖️ Workers: {workers}")
        log.info(f"🔎 Proxies: {len(self.proxies)}")
        log.info(f"👤 Sessions: {len(self.sessions)}")
        log.info(f"{'='*60}")
        
        self.stats['start_time'] = datetime.now()
        stats_thread = threading.Thread(target=self._stats_loop, daemon=True)
        stats_thread.start()
        
        successful = 0
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {}
            for i in range(viewer_count):
                future = executor.submit(self.simulate_viewer, room_id, duration_seconds)
                futures[future] = i
            time.sleep(random.uniform(self.settings.stagger_min, self.settings.stagger_max))
            for future in as_completed(futures):
                if future.result():
                    successful += 1
        
        elapsed = time.time() - start_time
        self.running = False
        print()
        log.info(f"{'='*60}")
        log.info(f"✅ ATTACK COMPLETE")
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
        while self.running:
            self.print_stats()
            time.sleep(2)

    def stop(self):
        self.running = False
        log.info("Stopping all viewers...")

# ------------------------------
# PROXY MANAGEMENT & SCRAPER
# ------------------------------
class ProxyManager:
    def __init__(self, settings_obj):
        self.settings = settings_obj
        self.proxies = []
        self.lock = threading.Lock()
        self.testing = False
        
    def load_proxies(self, filename):
        proxies = []
        if filename and os.path.exists(filename):
            with open(filename) as f:
                proxies = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        if not proxies:
            proxies = ['direct']
        return proxies

    def save_proxies(self, filename, proxies):
        with open(filename, 'w') as f:
            for proxy in proxies:
                f.write(f"{proxy}\n")

    def add_proxy(self, proxy):
        with self.lock:
            if proxy not in self.proxies and proxy != 'direct':
                self.proxies.append(proxy)

    def clear_proxies(self):
        with self.lock:
            self.proxies = []

    def test_proxy_single(self, proxy, timeout=5):
        """Test a single proxy by connecting to a known endpoint"""
        try:
            session = requests.Session()
            session.proxies = {'http': proxy, 'https': proxy}
            resp = session.get('https://www.google.com', timeout=timeout)
            if resp.status_code == 200:
                return True
        except:
            pass
        return False

    def test_proxies_thread(self, proxies_to_test):
        """Threaded function to test a list of proxies"""
        working = []
        for proxy in proxies_to_test:
            if self.test_proxy_single(proxy):
                working.append(proxy)
        return working

    def fetch_proxies_from_sites(self, sites=None):
        """Fetch proxies from multiple sites"""
        if sites is None:
            sites = [
                'https://raw.githubusercontent.com/nicyl101/proxylist/master/proxy.txt',
                'https://raw.githubusercontent.com/hookz0d/free-proxy-list/master/proxylist.csv',
                'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies_anonymous.txt',
                'https://raw.githubusercontent.com/shadabanani/Proxy/master/https.txt',
                'https://raw.githubusercontent.com/proxy4parsing/proxy-list/main/https.txt',
                'https://raw.githubusercontent.com/mmpx12/proxy-list/master/proxy.txt',
                'https://raw.githubusercontent.com/S4nc7/Proxy-List/main/https.txt',
                'https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt'
            ]
        
        all_proxies = []
        
        for url in sites:
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    lines = resp.text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d+$', line):
                            all_proxies.append(line)
            except:
                pass
        
        # Remove duplicates
        return list(set(all_proxies))

# ------------------------------
# HYBRID MENU SYSTEM
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

def proxy_management_menu(bot, proxy_manager):
    while True:
        items = [
            f"Current Proxy File: {settings.proxy_file}",
            f"Loaded Proxies: {len(bot.proxies)}",
            "Test All Proxies (Background)",
            "Fetch & Add Proxies from Sites",
            "Change Proxy File",
            "Add Single Proxy",
            "Clear Proxies"
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
            print("\nTesting proxies in background... (This will not block the menu)")
            # Run test in a background thread
            thread = threading.Thread(target=lambda: print(f"Testing {len(bot.proxies)} proxies..."), daemon=True)
            thread.start()
            
            # Actually test them
            working = proxy_manager.test_proxies_thread(bot.proxies)
            print(f"Test Complete: {len(working)}/{len(bot.proxies)} proxies working.")
            # Update the bot's proxy list with working ones
            bot.proxies = working
            proxy_manager.save_proxies(settings.proxy_file, working)
            log.info(f"Updated proxy list with {len(working)} working proxies.")
        elif choice == 4:
            print("\nFetching proxies from sites...")
            fetched = proxy_manager.fetch_proxies_from_sites()
            print(f"Fetched {len(fetched)} proxies.")
            if fetched:
                print(f"Testing fetched proxies...")
                working = proxy_manager.test_proxies_thread(fetched)
                print(f"Found {len(working)} working proxies from sites.")
                if working:
                    bot.proxies.extend(working)
                    # Remove duplicates
                    bot.proxies = list(set(bot.proxies))
                    proxy_manager.save_proxies(settings.proxy_file, bot.proxies)
                    log.info(f"Added {len(working)} new proxies.")
            else:
                print("No proxies found from sites.")
        elif choice == 5:
            new_file = input("Enter proxy file path (relative to script): ").strip()
            if os.path.exists(new_file):
                settings.proxy_file = new_file
                settings.save()
                bot.proxies = proxy_manager.load_proxies(new_file)
                proxy_manager.save_proxies(new_file, bot.proxies)
                print(f"Switched to {new_file}")
            else:
                print("File not found.")
        elif choice == 6:
            proxy = input("Enter proxy (host:port): ").strip()
            if proxy:
                bot.proxies.append(proxy)
                with open(settings.proxy_file, 'a') as f:
                    f.write(f"{proxy}\n")
                print(f"Added {proxy}")
        elif choice == 7:
            bot.proxies = []
            with open(settings.proxy_file, 'w') as f:
                f.write("")
            print("Proxies cleared.")
        elif choice == len(items) + 1:
            break

def timing_settings_menu():
    while True:
        items = [
            f"Heartbeat Min: {settings.hb_min}s",
            f"Heartbeat Max: {settings.hb_max}s",
            f"Stagger Delay Min: {settings.stagger_min}s",
            f"Stagger Delay Max: {settings.stagger_max}s",
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
            if val < settings.hb_max:
                settings.hb_min = val
                settings.save()
                print(f"Set Min to {val}")
        elif choice == 2:
            val = float(input("New Max Interval (s): "))
            if val > settings.hb_min:
                settings.hb_max = val
                settings.save()
                print(f"Set Max to {val}")
        elif choice == 3:
            val = float(input("New Min Stagger (s): "))
            settings.stagger_min = val
            settings.save()
        elif choice == 4:
            val = float(input("New Max Stagger (s): "))
            settings.stagger_max = val
            settings.save()
        elif choice == 5:
            settings.hb_min = 10
            settings.hb_max = 15
            settings.stagger_min = 0.01
            settings.stagger_max = 0.05
            settings.save()
            print("Set Fast Mode.")
        elif choice == 6:
            settings.hb_min = 30
            settings.hb_max = 45
            settings.stagger_min = 0.2
            settings.stagger_max = 0.5
            settings.save()
            print("Set Stable Mode.")
        elif choice == len(items) + 1:
            break

def launch_attack_menu(bot):
    print("\n--- Launch Attack ---")
    room_id = input("Room ID (or URL): ").strip()
    
    # Extract room ID if URL provided
    if not room_id.isdigit():
        match = re.search(r'room_id=(\d+)', room_id)
        if match:
            room_id = match.group(1)
        else:
            match = re.search(r'/live/(\d+)', room_id)
            if match:
                room_id = match.group(1)
            else:
                print("Could not resolve Room ID.")
                return

    viewer_count = int(input(f"Viewers [{settings.default_viewers}]: ") or settings.default_viewers)
    duration = int(input(f"Duration [s] [{settings.default_duration}]: ") or settings.default_duration)
    workers = int(input(f"Workers [{settings.default_workers}]: ") or settings.default_workers)
    
    input("\nPress Enter to start attack...")
    bot.launch_attack(room_id, viewer_count, duration, workers)

def generate_accounts_menu(generator):
    print("\n--- Account Generation ---")
    num_accounts = int(input("Number of accounts to generate: "))
    generated = 0
    
    proxies = generator._load_proxies(settings.proxy_file)
    if not proxies or proxies == ['direct']:
        print("No proxies found. Using direct connection.")
        
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = []
        for _ in range(num_accounts):
            proxy = random.choice(proxies)
            device = random.choice(ANDROID_DEVICES)
            future = executor.submit(generator.register_account, proxy, device)
            futures.append(future)
        
        for future in as_completed(futures):
            result = future.result()
            if result and result['status'] == 'waiting_2fa':
                log.info(f"Generated: {result['email']} - Waiting for 2FA")
                code = input(f"Enter 2FA code for {result['email']}: ")
                verified = generator.verify_2fa(result['email'], code, result['proxy'], result['device'])
                if verified:
                    generator.save_session(verified)
                    generated += 1
                    log.info(f"Verified: {result['email']}")
                else:
                    log.error(f"Failed to verify: {result['email']}")
    
    log.info(f"Generated {generated} accounts.")

def main_menu():
    bot = TikTokViewerBot(settings)
    generator = AccountGenerator(settings)
    proxy_manager = ProxyManager(settings)
    
    # Load proxies for the manager
    proxy_manager.proxies = bot._load_proxies(settings.proxy_file)

    while True:
        clear_screen()
        print("""
╔══════════════════════════════════════╗
║   TIKTOK LIVE HYBRID BOT v2.0        ║
║   Generate Accounts & Inject Views   ║
║   Multi-Site Proxy Scraper           ║
╚══════════════════════════════════════╝
""")
        items = [
            "Launch Attack",
            "Generate Accounts",
            "Proxy Management",
            "Timing & Heartbeat Settings",
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
            generate_accounts_menu(generator)
        elif choice == 3:
            proxy_management_menu(bot, proxy_manager)
        elif choice == 4:
            timing_settings_menu()
        elif choice == 5:
            settings.save()
            print("Settings saved. Exiting.")
            break

if __name__ == "__main__":
    main_menu()
