#!/usr/bin/env python3
"""
████████╗██╗██╗  ██╗████████╗ ██████╗ ██╗  ██╗
╚══██╔══╝██║██║ ██╔╝╚══██╔══╝██╔═══██╗██║ ██╔╝
   ██║   ██║█████╔╝    ██║   ██║   ██║█████╔╝ 
   ██║   ██║██╔═██╗    ██║   ██║   ██║██╔═██╗ 
   ██║   ██║██║  ██╗   ██║   ╚██████╔╝██║  ██╗
   ╚═╝   ╚═╝╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝
   TikTok Live Engagement Engine v4.0 - SignerPy
═══════════════════════════════════════════════════════
"""

import requests
import json
import time
import random
import string
import threading
import os
import sys
import signal
import logging
from itertools import cycle
from concurrent.futures import ThreadPoolExecutor, as_completed
import sqlite3
import argparse
import base64
import hashlib
import urllib.parse
from datetime import datetime
from fake_useragent import UserAgent
try:
    from signerpy import TikTokSigner
    SIGNER_AVAILABLE = True
except ImportError:
    SIGNER_AVAILABLE = False
    print("[!] SignerPy not installed. Run: pip install signerpy")

# ──────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────
TIKTOK_API_BASE = "https://api22-normal-c-useast1a.tiktokv.com"
TIKTOK_WEB_BASE = "https://www.tiktok.com"
VERSION = "4.0.0"
BANNER = """
╔══════════════════════════════════════════════════════════╗
║              TIKTOK LIVE ENGAGEMENT ENGINE              ║
║                   Version 4.0 - SignerPy               ║
║                  Views | Likes | Shares | Comments      ║
╚══════════════════════════════════════════════════════════╝
"""

# ──────────────────────────────────────────────
# ANDROID DEVICE FINGERPRINTS
# ──────────────────────────────────────────────
ANDROID_DEVICES = [
    {
        'device_id': 'android_7255253607933979658',
        'iid': '72552536079339796580',
        'openudid': 'f1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6',
        'model': 'SM-G998B', 'brand': 'samsung',
        'os_version': '13', 'resolution': '1440*3200', 'dpi': '560', 'os_api': '33'
    },
    {
        'device_id': 'android_8355253607933979669',
        'iid': '83552536079339796690',
        'openudid': 'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d7',
        'model': 'Pixel 8 Pro', 'brand': 'google',
        'os_version': '14', 'resolution': '1344*2992', 'dpi': '420', 'os_api': '34'
    },
    {
        'device_id': 'android_9455253612938979670',
        'iid': '94552536129389796700',
        'openudid': 'b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e8',
        'model': 'OnePlus 12', 'brand': 'oneplus',
        'os_version': '14', 'resolution': '1440*3168', 'dpi': '510', 'os_api': '34'
    },
    {
        'device_id': 'android_1155253612938979671',
        'iid': '11552536129389796710',
        'openudid': 'c3d4e5f6a7b8c9d0e1f2a3b4c5d6e8f9',
        'model': 'Xiaomi 14 Pro', 'brand': 'xiaomi',
        'os_version': '14', 'resolution': '1440*3200', 'dpi': '522', 'os_api': '34'
    },
    {
        'device_id': 'android_1255253612938979672',
        'iid': '12552536129389796720',
        'openudid': 'd4e5f6a7b8c9d0e1f2a3b4c5d6e8f9a0',
        'model': 'Pixel 7', 'brand': 'google',
        'os_version': '13', 'resolution': '1080*2400', 'dpi': '420', 'os_api': '33'
    },
    {
        'device_id': 'android_1355253612938979673',
        'iid': '13552536129389796730',
        'openudid': 'e5f6a7b8c9d0e1f2a3b4c5d6e8f9a0b1',
        'model': 'SM-S928B', 'brand': 'samsung',
        'os_version': '14', 'resolution': '1440*3200', 'dpi': '560', 'os_api': '34'
    }
]

COMMENT_TEMPLATES = [
    "🔥🔥🔥", "Let's goooooo!", "Best stream ever! 😍",
    "Hello from the bot army 🤖", "Can everyone type L in chat?",
    "Go viral! 🚀", "niceee", "😂😂 10/10", "Keep it up!",
    "i love this content", "WOW WOW WOW", "first time here! cool stream",
    "subbed! 🔔", "POG", "💯💯", "this is fire", "insane stream!",
    "❤️❤️❤️❤️", "chat, spam the like button", "very cool!",
    "legendary stream", "👏👏👏", "best content on tiktok",
    "i wish i could stream like this", "take my like!",
    "this blew my mind", "how does this not have more views?",
    "underrated streamer", "100/100", "sending love from uk",
    "yo this is sick", "never seen anything like this",
    "deserves way more attention", "straight fire content",
    "the algorithm blessed me today", "found a gem"
]

# ──────────────────────────────────────────────
# LOGGING SETUP
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('tiktok_bot.log'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# CORE ENGINE
# ──────────────────────────────────────────────
class TikTokBotCore:
    def __init__(self):
        self.ua = UserAgent()
        self.device_pool = cycle(ANDROID_DEVICES)
        self.proxies = []
        self.proxy_pool = None
        self.signer = TikTokSigner() if SIGNER_AVAILABLE else None
        self.running = False
        self.stats_lock = threading.Lock()
        self.stats = {
            'views': 0, 'likes': 0, 'shares': 0, 'comments': 0,
            'successful_joins': 0, 'failed_joins': 0,
            'active_viewers': 0, 'total_requests': 0
        }
        self.db_conn = None
    
    def load_proxies(self, filename):
        """Load proxies from file"""
        if not filename or not os.path.exists(filename):
            log.error(f"Proxy file not found: {filename}")
            return False
        
        with open(filename) as f:
            self.proxies = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        
        if not self.proxies:
            log.error("No proxies found in file!")
            return False
        
        self.proxy_pool = cycle(self.proxies)
        log.info(f"Loaded {len(self.proxies)} proxies")
        return True
    
    def init_db(self, db_file='tiktok_accounts.db'):
        """Initialize SQLite database"""
        self.db_conn = sqlite3.connect(db_file, check_same_thread=False)
        self.db_conn.execute('''CREATE TABLE IF NOT EXISTS accounts
            (username TEXT PRIMARY KEY, email TEXT, password TEXT, 
             device_id TEXT, proxy TEXT, user_id TEXT, 
             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        self.db_conn.execute('''CREATE TABLE IF NOT EXISTS sessions
            (id INTEGER PRIMARY KEY AUTOINCREMENT, room_id TEXT, 
             username TEXT, action TEXT, count INTEGER, 
             timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        self.db_conn.execute('''CREATE TABLE IF NOT EXISTS stats
            (id INTEGER PRIMARY KEY AUTOINCREMENT, campaign_id TEXT,
             views INTEGER, likes INTEGER, shares INTEGER, comments INTEGER,
             timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        self.db_conn.commit()
        log.info(f"Database initialized: {db_file}")
    
    def get_device(self):
        """Get random Android device fingerprint"""
        return next(self.device_pool)
    
    def get_session(self, proxy=None):
        """Create requests session"""
        session = requests.Session()
        session.verify = True
        if proxy:
            session.proxies = {'http': proxy, 'https': proxy}
        
        # Timeout config
        session.timeout = (10, 30)
        return session
    
    def get_headers(self, device=None, authenticated=False, token=None):
        """Generate Android headers"""
        if not device:
            device = self.get_device()
        
        headers = {
            'User-Agent': f'com.zhiliaoapp.musically/20231212205426 (Linux; U; Android {device["os_version"]}; en; {device["model"]} Build/TP1A.220624.014; Cronet/112.0.5615.140)',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip',
            'Accept-Language': 'en,en-US;q=0.9',
            'Content-Type': 'application/json; charset=utf-8',
            'Connection': 'keep-alive',
            'Host': 'api22-normal-c-useast1a.tiktokv.com',
            'X-Tt-Token': ''.join(random.choices('0123456789abcdef', k=32)),
            'X-Khronos': str(int(time.time())),
        }
        
        if authenticated and token:
            headers['Authorization'] = f'Bearer {token}'
        
        return headers
    
    def sign_request(self, url, params):
        """Sign request with SignerPy"""
        if not self.signer:
            return {'X-Bogus': self._fallback_sign(params)}
        
        try:
            device_id = params.get('device_id', '7255253607933979658')
            iid = params.get('iid', '72552536079339796580')
            
            result = self.signer.sign(
                url=url, params=params,
                device_id=device_id, iid=iid
            )
            return {
                'X-Bogus': result.get('X-Bogus', ''),
                'X-SS-STUB': result.get('X-SS-STUB', ''),
                'X-Ladon': result.get('X-Ladon', ''),
            }
        except Exception as e:
            log.debug(f"SignerPy error: {e}")
            return {'X-Bogus': self._fallback_sign(params)}
    
    def _fallback_sign(self, params):
        """Fallback signature"""
        query = '&'.join([f"{k}={urllib.parse.quote(str(v))}" 
                         for k, v in sorted(params.items())])
        return hashlib.md5(query.encode()).hexdigest()
    
    def generate_device_params(self, room_id=None):
        """Generate full device params"""
        device = self.get_device()
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
            'cdid': ''.join(random.choices(string.hexdigits, k=32)).lower(),
            'req_id': ''.join(random.choices(string.hexdigits, k=32)).upper(),
        }
        
        if room_id:
            params['room_id'] = room_id
        
        return params
    
    def log_action(self, room_id, username, action, count=1):
        """Log action to database"""
        if self.db_conn:
            try:
                self.db_conn.execute(
                    "INSERT INTO sessions (room_id, username, action, count) VALUES (?, ?, ?, ?)",
                    (room_id, username, action, count)
                )
                self.db_conn.commit()
            except:
                pass
    
    def update_stats(self, views=0, likes=0, shares=0, comments=0, active=0):
        """Thread-safe stats update"""
        with self.stats_lock:
            self.stats['views'] += views
            self.stats['likes'] += likes
            self.stats['shares'] += shares
            self.stats['comments'] += comments
            if active:
                self.stats['active_viewers'] += active
            self.stats['total_requests'] += 1
    
    def print_stats(self):
        """Print current stats"""
        with self.stats_lock:
            print(f"\r[📊] Views: {self.stats['views']:,} | "
                  f"Likes: {self.stats['likes']:,} | "
                  f"Shares: {self.stats['shares']:,} | "
                  f"Comments: {self.stats['comments']:,} | "
                  f"Active: {self.stats['active_viewers']} | "
                  f"Total Reqs: {self.stats['total_requests']:,}", end='')

# ──────────────────────────────────────────────
# GUEST ENGAGEMENT
# ──────────────────────────────────────────────
class GuestEngagement(TikTokBotCore):
    def join_room(self, session, room_id):
        """Join live room as guest"""
        url = f"{TIKTOK_API_BASE}/aweme/v1/webcast/join/"
        params = self.generate_device_params(room_id)
        params.update({
            'enter_from': random.choice(['live_center', 'feed', 'share', 'scan']),
            'enter_method': random.choice(['scan', 'feed', 'share', 'push']),
            'priority_region': 'US',
            'mcc_mnc': '310410'
        })
        
        signatures = self.sign_request(url, params)
        headers = self.get_headers()
        headers.update(signatures)
        
        payload = {
            "room_id": int(room_id),
            "user_id": f"guest_{random.randint(10000000, 99999999)}",
            "enter_method": params['enter_method'],
            "device_id": params['device_id'],
            "iid": params['iid'],
            "priority_region": "US"
        }
        
        resp = session.post(url, json=payload, headers=headers, timeout=15)
        success = resp.status_code in [200, 204, 0]
        
        if success:
            self.update_stats(active=1)
            with self.stats_lock:
                self.stats['successful_joins'] += 1
        else:
            with self.stats_lock:
                self.stats['failed_joins'] += 1
        
        return success
    
    def send_like(self, session, room_id):
        """Send like as guest"""
        url = f"{TIKTOK_API_BASE}/aweme/v1/webcast/like/"
        params = self.generate_device_params(room_id)
        
        signatures = self.sign_request(url, params)
        headers = self.get_headers()
        headers.update(signatures)
        
        like_count = random.choices([1, 2, 3, 5, 10], weights=[30, 25, 20, 15, 10])[0]
        payload = {
            "room_id": int(room_id),
            "like_count": like_count,
            "timestamp": int(time.time())
        }
        
        resp = session.post(url, json=payload, headers=headers, timeout=10)
        if resp.status_code in [200, 204]:
            self.update_stats(likes=like_count)
            return True
        return False
    
    def send_share(self, session, room_id):
        """Share as guest"""
        url = f"{TIKTOK_API_BASE}/aweme/v1/webcast/share/"
        params = self.generate_device_params(room_id)
        share_type = random.choice(['copy', 'whatsapp', 'twitter', 'instagram', 'sms', 'messenger', 'telegram'])
        params.update({'share_type': share_type})
        
        signatures = self.sign_request(url, params)
        headers = self.get_headers()
        headers.update(signatures)
        
        payload = {
            "room_id": int(room_id),
            "share_type": share_type
        }
        
        resp = session.post(url, json=payload, headers=headers, timeout=10)
        if resp.status_code in [200, 204]:
            self.update_stats(shares=1)
            return True
        return False
    
    def send_comment(self, session, room_id):
        """Comment as guest"""
        url = f"{TIKTOK_API_BASE}/aweme/v1/webcast/comment/"
        params = self.generate_device_params(room_id)
        
        signatures = self.sign_request(url, params)
        headers = self.get_headers()
        headers.update(signatures)
        
        comment = random.choice(COMMENT_TEMPLATES)
        payload = {
            "room_id": int(room_id),
            "content": comment,
            "comment_type": "text"
        }
        
        resp = session.post(url, json=payload, headers=headers, timeout=10)
        if resp.status_code in [200, 204]:
            self.update_stats(comments=1)
            return True
        return False
    
    def heartbeat(self, session, room_id):
        """Maintain guest presence"""
        url = f"{TIKTOK_API_BASE}/aweme/v1/webcast/enter/"
        hb_count = 0
        
        while self.running:
            try:
                params = self.generate_device_params(room_id)
                params.update({'status': 1, 'live_id': random.randint(1, 99999)})
                
                signatures = self.sign_request(url, params)
                headers = self.get_headers()
                headers.update(signatures)
                
                session.post(url, json={
                    "room_id": int(room_id),
                    "status": 1,
                    "device_id": params['device_id'],
                    "live_id": params['live_id']
                }, headers=headers, timeout=5)
                
                hb_count += 1
                if hb_count % 10 == 0:
                    with self.stats_lock:
                        self.stats['active_viewers'] += 0  # keep alive
                
                time.sleep(random.uniform(25, 35))
            except:
                time.sleep(5)
    
    def run_guest(self, room_id, duration=1800):
        """Single guest lifecycle"""
        proxy = next(self.proxy_pool) if self.proxy_pool else None
        session = self.get_session(proxy)
        
        if not self.join_room(session, room_id):
            return False
        
        # Start heartbeat
        hb_thread = threading.Thread(target=self.heartbeat, args=(session, room_id))
        hb_thread.daemon = True
        hb_thread.start()
        
        # Perform actions
        end_time = time.time() + duration
        while self.running and time.time() < end_time:
            action = random.choices(
                ['like', 'share', 'comment', 'sleep'],
                weights=[30, 5, 10, 55], k=1
            )[0]
            
            if action == 'like':
                self.send_like(session, room_id)
            elif action == 'share':
                self.send_share(session, room_id)
            elif action == 'comment':
                self.send_comment(session, room_id)
            
            time.sleep(random.uniform(3, 12))
        
        self.update_stats(active=-1)
        return True

# ──────────────────────────────────────────────
# AUTHENTICATED ENGAGEMENT
# ──────────────────────────────────────────────
class AuthenticatedEngagement(TikTokBotCore):
    def login_account(self, account):
        """Login with account credentials"""
        username, email, password, device_id, proxy = account[:5]
        actual_proxy = proxy or next(self.proxy_pool) if self.proxy_pool else None
        
        session = self.get_session(actual_proxy)
        
        login_url = f"{TIKTOK_API_BASE}/passport/web/login/"
        params = self.generate_device_params()
        params.update({'username': username, 'type': 'password'})
        
        signatures = self.sign_request(login_url, params)
        headers = self.get_headers(authenticated=True)
        headers.update(signatures)
        headers.pop('Authorization', None)  # Not yet auth'd
        
        payload = {
            "username": username,
            "password": password,
            "device_id": device_id or params['device_id'],
            "type": "password",
            "mix_mode": 1,
            "account_type": 1
        }
        
        try:
            resp = session.post(login_url, json=payload, headers=headers, timeout=20)
            
            if resp.status_code == 200:
                data = resp.json()
                token = data.get('data', {}).get('token', {}).get('access_token', '')
                user_id = data.get('data', {}).get('user_id', '')
                
                if token:
                    session.headers['Authorization'] = f'Bearer {token}'
                    log.info(f"Logged in as @{username}")
                    return session, user_id, token
            else:
                log.debug(f"Login failed for @{username}: {resp.status_code}")
        except Exception as e:
            log.debug(f"Login error @{username}: {e}")
        
        return None, None, None
    
    def join_live(self, session, room_id, user_id):
        """Join live as authenticated user"""
        url = f"{TIKTOK_API_BASE}/aweme/v1/webcast/join/"
        params = self.generate_device_params(room_id)
        params.update({'user_id': user_id})
        
        signatures = self.sign_request(url, params)
        if signatures.get('X-Bogus'):
            session.headers.update({'X-Bogus': signatures['X-Bogus']})
        
        payload = {
            "room_id": int(room_id),
            "user_id": user_id,
            "enter_method": "feed",
            "device_id": params['device_id'],
            "iid": params['iid']
        }
        
        resp = session.post(url, json=payload, timeout=15)
        return resp.status_code in [200, 204, 0]
    
    def send_like(self, session, room_id, user_id):
        """Send authenticated like"""
        url = f"{TIKTOK_API_BASE}/aweme/v1/webcast/like/"
        params = self.generate_device_params(room_id)
        params.update({'user_id': user_id})
        
        signatures = self.sign_request(url, params)
        if signatures.get('X-Bogus'):
            session.headers.update({'X-Bogus': signatures['X-Bogus']})
        
        like_count = random.choices([1, 2, 3, 5, 10, 20], weights=[25, 20, 20, 15, 10, 10])[0]
        payload = {
            "room_id": int(room_id),
            "user_id": user_id,
            "like_count": like_count,
            "timestamp": int(time.time())
        }
        
        resp = session.post(url, json=payload, timeout=10)
        if resp.status_code in [200, 204]:
            self.update_stats(likes=like_count)
            return True
        return False
    
    def send_share(self, session, room_id, user_id):
        """Send authenticated share"""
        url = f"{TIKTOK_API_BASE}/aweme/v1/webcast/share/"
        params = self.generate_device_params(room_id)
        params.update({'user_id': user_id})
        
        signatures = self.sign_request(url, params)
        if signatures.get('X-Bogus'):
            session.headers.update({'X-Bogus': signatures['X-Bogus']})
        
        share_type = random.choice(['copy', 'whatsapp', 'twitter', 'instagram', 'sms', 'messenger'])
        payload = {
            "room_id": int(room_id),
            "user_id": user_id,
            "share_type": share_type
        }
        
        resp = session.post(url, json=payload, timeout=10)
        if resp.status_code in [200, 204]:
            self.update_stats(shares=1)
            return True
        return False
    
    def send_comment(self, session, room_id, user_id):
        """Send authenticated comment"""
        url = f"{TIKTOK_API_BASE}/aweme/v1/webcast/comment/"
        params = self.generate_device_params(room_id)
        params.update({'user_id': user_id})
        
        signatures = self.sign_request(url, params)
        if signatures.get('X-Bogus'):
            session.headers.update({'X-Bogus': signatures['X-Bogus']})
        
        comment = random.choice(COMMENT_TEMPLATES)
        payload = {
            "room_id": int(room_id),
            "user_id": user_id,
            "content": comment,
            "comment_type": "text"
        }
        
        resp = session.post(url, json=payload, timeout=10)
        if resp.status_code in [200, 204]:
            self.update_stats(comments=1)
            return True
        return False
    
    def run_account(self, account, room_id, duration=1800):
        """Full authenticated account lifecycle"""
        session, user_id, token = self.login_account(account)
        if not session or not user_id:
            return False
        
        # Join live
        if not self.join_live(session, room_id, user_id):
            log.warning(f"@{account[0]} failed to join live")
            return False
        
        log.info(f"@{account[0]} joined live")
        self.update_stats(active=1)
        
        # Perform actions
        end_time = time.time() + duration
        while self.running and time.time() < end_time:
            action = random.choices(
                ['like', 'share', 'comment', 'sleep'],
                weights=[40, 5, 20, 10], k=1
            )[0]
            
            if action == 'like':
                self.send_like(session, room_id, user_id)
            elif action == 'share':
                self.send_share(session, room_id, user_id)
            elif action == 'comment':
                self.send_comment(session, room_id, user_id)
            
            time.sleep(random.uniform(2, 18))
        
        self.update_stats(active=-1)
        return True

# ──────────────────────────────────────────────
# ACCOUNT FACTORY
# ──────────────────────────────────────────────
class TikTokAccountFactory(TikTokBotCore):
    def __init__(self, proxies_file, db_file='tiktok_accounts.db'):
        super().__init__()
        self.load_proxies(proxies_file)
        self.init_db(db_file)
        self.name_prefixes = ['livebot', 'streamer', 'tiktoker', 'viral', 'content',
                              'creator', 'influencer', 'gamer', 'music', 'dance',
                              'comedy', 'foodie', 'travel', 'fashion', 'fitness']
    
    def generate_credentials(self):
        prefix = random.choice(self.name_prefixes)
        suffix = random.randint(10000, 999999)
        username = f"{prefix}_{suffix}"
        email = f"{username}@{random.choice(['tempmail.lol', 'mailnator.com', '10minutemail.com'])}"
        password = ''.join(random.choices(
            string.ascii_letters + string.digits + '!@#$%^&*', k=16
        ))
        return username, email, password
    
    def create_account(self):
        """Create single TikTok account"""
        proxy = next(self.proxy_pool)
        username, email, password = self.generate_credentials()
        device_id = f"android_{random.randint(7000000000000000000, 7999999999999999999)}"
        
        session = self.get_session(proxy)
        
        register_url = f"{TIKTOK_API_BASE}/passport/web/register/"
        
        params = {
            'device_id': device_id,
            'iid': f"{random.randint(7000000000000000000, 7999999999999999999)}0",
            'openudid': ''.join(random.choices(string.hexdigits, k=32)).lower(),
            'aid': '1180',
            'app_version': '35.7.0',
            'app_name': 'trill',
            'os_version': random.choice(['13', '14']),
            'device_platform': 'android',
            'tz_name': 'America/New_York',
            'sys_region': 'US',
        }
        
        if self.signer:
            signatures = self.signer.sign(
                url=register_url, params=params,
                device_id=device_id, iid=params['iid']
            )
        else:
            signatures = {'X-Bogus': self._fallback_sign(params)}
        
        headers = {
            'User-Agent': 'com.zhiliaoapp.musically/20231212205426 (Linux; U; Android 13; en; SM-G998B Build/TP1A.220624.014; Cronet/112.0.5615.140)',
            'X-Bogus': signatures.get('X-Bogus', ''),
            'X-SS-STUB': signatures.get('X-SS-STUB', ''),
            'Content-Type': 'application/json; charset=utf-8',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip',
            'Connection': 'keep-alive'
        }
        
        payload = {
            "username": username,
            "email": email,
            "password": password,
            "device_id": device_id,
            "region": "US",
            "language": "en",
            "account_type": 1,
            "app_version": "35.7.0",
            "sdk_version": "35.7.0"
        }
        
        try:
            resp = session.post(register_url, json=payload, headers=headers, timeout=25)
            
            if resp.status_code == 200:
                data = resp.json()
                if 'user_id' in data.get('data', {}):
                    user_id = data['data']['user_id']
                    self.db_conn.execute(
                        "INSERT OR REPLACE INTO accounts VALUES (?,?,?,?,?,?, datetime('now'))",
                        (username, email, password, device_id, proxy, user_id)
                    )
                    self.db_conn.commit()
                    return True, username, proxy
            
            log.debug(f"Account creation failed ({resp.status_code}): {username}")
            return False, username, proxy
            
        except Exception as e:
            log.debug(f"Account creation error: {e}")
            return False, username, proxy
    
    def create_bulk(self, count):
        """Bulk account creation"""
        log.info(f"Creating {count} accounts...")
        success = 0
        failed = 0
        
        with ThreadPoolExecutor(max_workers=30) as executor:
            futures = {executor.submit(self.create_account): i for i in range(count)}
            
            for i, future in enumerate(as_completed(futures), 1):
                ok, username, proxy = future.result()
                if ok:
                    success += 1
                else:
                    failed += 1
                
                if i % 50 == 0:
                    rate = success / i * 100
                    log.info(f"Progress: {i}/{count} | Success: {success} ({rate:.1f}%) | Failed: {failed}")
        
        log.info(f"Account creation complete: {success} success, {failed} failed")
        return success

# ──────────────────────────────────────────────
# ORCHESTRATOR
# ──────────────────────────────────────────────
class AttackOrchestrator:
    def __init__(self, guest_bot, auth_bot, account_factory=None):
        self.guest = guest_bot
        self.auth = auth_bot
        self.factory = account_factory
        self.guest.running = True
        self.auth.running = True
        self.stats_thread = None
    
    def stats_printer(self):
        """Print stats periodically"""
        while self.guest.running or self.auth.running:
            time.sleep(5)
            self.guest.print_stats()
    
    def guest_attack(self, room_id, count, duration, workers=100):
        """Launch guest viewers"""
        log.info(f"Launching {count} guest viewers on {room_id}")
        start = time.time()
        successful = 0
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(self.guest.run_guest, room_id, duration)
                for _ in range(count)
            ]
            
            for i, future in enumerate(as_completed(futures), 1):
                if future.result():
                    successful += 1
                if i % 100 == 0:
                    elapsed = time.time() - start
                    rate = successful / i * 100
                    log.info(f"Guests: {i}/{count} | Success: {rate:.1f}% | Rate: {i/elapsed:.1f}/s")
        
        elapsed = time.time() - start
        log.info(f"Guest attack complete: {successful}/{count} ({successful/count*100:.1f}%) in {elapsed:.1f}s")
        return successful
    
    def auth_attack(self, room_id, accounts, duration, workers=50):
        """Launch authenticated accounts"""
        count = len(accounts)
        log.info(f"Launching {count} authenticated accounts on {room_id}")
        start = time.time()
        successful = 0
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(self.auth.run_account, acc, room_id, duration)
                for acc in accounts
            ]
            
            for i, future in enumerate(as_completed(futures), 1):
                if future.result():
                    successful += 1
                if i % 25 == 0:
                    elapsed = time.time() - start
                    rate = successful / i * 100
                    log.info(f"Auth: {i}/{count} | Success: {rate:.1f}% | Rate: {i/elapsed:.1f}/s")
        
        elapsed = time.time() - start
        log.info(f"Auth attack complete: {successful}/{count} ({successful/count*100:.1f}%) in {elapsed:.1f}s")
        return successful
    
    def combined_attack(self, room_id, guest_count, auth_count, duration, guest_workers=100, auth_workers=50):
        """Full combined attack"""
        log.info("=" * 60)
        log.info("COMBINED ATTACK INITIATED")
        log.info(f"Room: {room_id}")
        log.info(f"Guests: {guest_count}")
        log.info(f"Auth Accounts: {auth_count}")
        log.info(f"Duration: {duration}s")
        log.info("=" * 60)
        
        # Start stats printer
        self.stats_thread = threading.Thread(target=self.stats_printer, daemon=True)
        self.stats_thread.start()
        
        # Phase 1: Guests join
        guest_thread = threading.Thread(
            target=self.guest_attack,
            args=(room_id, guest_count, duration, guest_workers)
        )
        guest_thread.start()
        
        # Slight delay then auth accounts
        time.sleep(10)
        
        # Load accounts from DB
        accounts = []
        if auth_count > 0 and self.factory and self.factory.db_conn:
            accounts = self.factory.db_conn.execute(
                "SELECT * FROM accounts ORDER BY RANDOM() LIMIT ?",
                (auth_count,)
            ).fetchall()
        
        auth_thread = None
        if accounts:
            auth_thread = threading.Thread(
                target=self.auth_attack,
                args=(room_id, accounts, duration, auth_workers)
            )
            auth_thread.start()
        
        # Wait for completion
        guest_thread.join()
        if auth_thread:
            auth_thread.join()
        
        log.info("=" * 60)
        log.info("ATTACK COMPLETE")
        self.guest.print_stats()
        log.info("")
        log.info("=" * 60)

# ──────────────────────────────────────────────
# MENU SYSTEM
# ──────────────────────────────────────────────
class MenuSystem:
    def __init__(self):
        self.guest = None
        self.auth = None
        self.factory = None
        self.orchestrator = None
        self.config = {
            'room_id': None,
            'proxies_file': None,
            'accounts_db': 'tiktok_accounts.db',
            'guest_count': 1000,
            'auth_count': 0,
            'duration': 3600,
            'guest_workers': 100,
            'auth_workers': 50,
            'auto_setup': False
        }
    
    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def print_header(self):
        self.clear_screen()
        print(BANNER)
        print(f"                     [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")
        print(f"                     SignerPy: {'✅ READY' if SIGNER_AVAILABLE else '❌ NOT INSTALLED'}")
        print()
    
    def print_menu(self, options, title="MENU"):
        """Print formatted menu"""
        print(f"  ╔═══ {title} ═══╗")
        print()
        for key, (desc, _) in options.items():
            print(f"     [{key}] {desc}")
        print()
        print(f"  ╚{'═' * 30}╝")
        print()
    
    def get_choice(self, prompt="Select option: "):
        return input(f"  {prompt}").strip().lower()
    
    def get_input(self, prompt, default=None, cast=str):
        """Get user input with default"""
        if default:
            prompt = f"{prompt} [{default}]: "
        else:
            prompt = f"{prompt}: "
        
        val = input(f"  {prompt}").strip()
        if not val and default:
            return default
        try:
            return cast(val)
        except:
            return default
    
    def initialize_bots(self):
        """Initialize bot engines"""
        if not self.config['proxies_file']:
            log.error("No proxy file configured!")
            return False
        
        if not os.path.exists(self.config['proxies_file']):
            log.error(f"Proxy file not found: {self.config['proxies_file']}")
            return False
        
        self.guest = GuestEngagement()
        self.guest.load_proxies(self.config['proxies_file'])
        self.guest.init_db(self.config['accounts_db'])
        self.guest.running = True
        
        self.auth = AuthenticatedEngagement()
        self.auth.load_proxies(self.config['proxies_file'])
        self.auth.init_db(self.config['accounts_db'])
        self.auth.running = True
        
        self.factory = TikTokAccountFactory(self.config['proxies_file'], self.config['accounts_db'])
        
        self.orchestrator = AttackOrchestrator(self.guest, self.auth, self.factory)
        return True
    
    def menu_main(self):
        """Main menu"""
        while True:
            self.print_header()
            
            options = {
                '1': ("🚀 Launch Attack", self.menu_attack),
                '2': ("👤 Account Management", self.menu_accounts),
                '3': ("⚙️ Configuration", self.menu_config),
                '4': ("📊 View Statistics", self.menu_stats),
                '5': ("📦 Auto Setup Wizard", self.auto_setup),
                '6': ("ℹ️ About & Help", self.menu_about),
                'q': ("❌ Quit", None)
            }
            
            self.print_menu(options, "MAIN MENU")
            choice = self.get_choice()
            
            if choice == 'q':
                print("\n  Exiting...\n")
                if self.guest:
                    self.guest.running = False
                if self.auth:
                    self.auth.running = False
                sys.exit(0)
            elif choice in options:
                self.print_header()
                options[choice][1]()
    
    def menu_attack(self):
        """Attack menu"""
        while True:
            self.print_header()
            print(f"  📺 Room ID: {self.config['room_id'] or 'NOT SET'}")
            print(f"  👻 Guests: {self.config['guest_count']:,}")
            print(f"  👤 Auth Accounts: {self.config['auth_count']:,}")
            print(f"  ⏱ Duration: {self.config['duration']}s ({self.config['duration']//60}m)")
            print()
            
            options = {
                '1': ("Combined Attack (Guests + Auth)", self.run_combined),
                '2': ("Pure Guest Attack", self.run_guests_only),
                '3': ("Pure Authenticated Attack", self.run_auth_only),
                '4': ("Set Room ID", self.set_room_id),
                '5': ("Set Attack Parameters", self.set_attack_params),
                'b': ("🔙 Back to Main", None)
            }
            
            self.print_menu(options, "ATTACK MENU")
            choice = self.get_choice()
            
            if choice == 'b':
                return
            elif choice == '4':
                self.set_room_id()
            elif choice == '5':
                self.set_attack_params()
            elif choice in ['1', '2', '3']:
                self.execute_attack(choice)
    
    def run_combined(self):
        """Run combined attack"""
        if not self.verify_ready():
            return
        
        self.initialize_bots()
        print("\n  [+] Starting Combined Attack...")
        self.orchestrator.combined_attack(
            self.config['room_id'],
            self.config['guest_count'],
            self.config['auth_count'],
            self.config['duration'],
            self.config['guest_workers'],
            self.config['auth_workers']
        )
        input("\n  Press Enter to continue...")
    
    def run_guests_only(self):
        """Run guest-only attack"""
        if not self.verify_ready():
            return
        
        self.initialize_bots()
        print("\n  [+] Starting Guest Attack...")
        
        # Start stats printer
        stats_thread = threading.Thread(
            target=self.orchestrator.stats_printer, daemon=True
        )
        stats_thread.start()
        
        self.orchestrator.guest_attack(
            self.config['room_id'],
            self.config['guest_count'],
            self.config['duration'],
            self.config['guest_workers']
        )
        input("\n  Press Enter to continue...")
    
    def run_auth_only(self):
        """Run authenticated-only attack"""
        if not self.verify_ready():
            return
        
        self.initialize_bots()
        
        # Load accounts
        accounts = self.factory.db_conn.execute(
            "SELECT * FROM accounts ORDER BY RANDOM() LIMIT ?",
            (self.config['auth_count'],)
        ).fetchall()
        
        if not accounts:
            print("\n  [!] No accounts in database! Create accounts first.")
            input("\n  Press Enter to continue...")
            return
        
        print(f"\n  [+] Starting Authenticated Attack with {len(accounts)} accounts...")
        
        stats_thread = threading.Thread(
            target=self.orchestrator.stats_printer, daemon=True
        )
        stats_thread.start()
        
        self.orchestrator.auth_attack(
            self.config['room_id'],
            accounts,
            self.config['duration'],
            self.config['auth_workers']
        )
        input("\n  Press Enter to continue...")
    
    def verify_ready(self):
        """Verify attack readiness"""
        if not self.config['room_id']:
            print("\n  [!] No Room ID configured! Set it first.")
            input("\n  Press Enter to continue...")
            return False
        
        if not self.config['proxies_file'] or not os.path.exists(self.config['proxies_file']):
            print(f"\n  [!] Proxy file not found: {self.config['proxies_file']}")
            input("\n  Press Enter to continue...")
            return False
        
        if self.config['auth_count'] > 0 and not os.path.exists(self.config['accounts_db']):
            print(f"\n  [!] Auth accounts requested but no DB found: {self.config['accounts_db']}")
            print("  Create accounts first or set auth count to 0.")
            input("\n  Press Enter to continue...")
            return False
        
        return True
    
    def set_room_id(self):
        """Set room ID"""
        self.print_header()
        print("  Enter the TikTok Live Room ID")
        print("  (Find it in browser network tab or from URL params)")
        print()
        
        room_id = self.get_input("Room ID", self.config['room_id'])
        if room_id:
            self.config['room_id'] = room_id
            print(f"\n  [+] Room ID set to: {room_id}")
        else:
            print("\n  [!] Invalid Room ID")
        
        input("\n  Press Enter to continue...")
    
    def set_attack_params(self):
        """Set attack parameters"""
        self.print_header()
        print("  Attack Configuration")
        print()
        
        self.config['guest_count'] = self.get_input(
            "Guest viewers count", self.config['guest_count'], int
        )
        self.config['auth_count'] = self.get_input(
            "Authenticated accounts count", self.config['auth_count'], int
        )
        self.config['duration'] = self.get_input(
            "Duration (seconds)", self.config['duration'], int
        )
        self.config['guest_workers'] = self.get_input(
            "Guest worker threads (50-500)", self.config['guest_workers'], int
        )
        self.config['auth_workers'] = self.get_input(
            "Auth worker threads (10-100)", self.config['auth_workers'], int
        )
        
        print("\n  [+] Configuration updated!")
        input("\n  Press Enter to continue...")
    
    def menu_accounts(self):
        """Account management menu"""
        while True:
            self.print_header()
            
            # Count accounts
            db_exists = os.path.exists(self.config['accounts_db'])
            count = 0
            if db_exists:
                try:
                    conn = sqlite3.connect(self.config['accounts_db'])
                    count = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
                    conn.close()
                except:
                    pass
            
            print(f"  📂 Database: {self.config['accounts_db']}")
            print(f"  👤 Accounts: {count:,}")
            print()
            
            options = {
                '1': ("Create Accounts", self.create_accounts),
                '2': ("View Account List", self.view_accounts),
                '3': ("Delete All Accounts", self.delete_accounts),
                '4': ("Export Accounts to File", self.export_accounts),
                '5': ("Import Accounts from File", self.import_accounts),
                '6': ("Set Database File", self.set_db_file),
                'b': ("🔙 Back to Main", None)
            }
            
            self.print_menu(options, "ACCOUNT MANAGEMENT")
            choice = self.get_choice()
            
            if choice == 'b':
                return
            elif choice in options:
                options[choice][1]()
    
    def create_accounts(self):
        """Create accounts menu"""
        self.print_header()
        print("  Account Creation")
        print()
        
        count = self.get_input("How many accounts to create?", 1000, int)
        
        if count < 1:
            return
        
        if not self.config['proxies_file'] or not os.path.exists(self.config['proxies_file']):
            print(f"\n  [!] Proxy file not found: {self.config['proxies_file']}")
            input("\n  Press Enter to continue...")
            return
        
        print(f"\n  [+] Creating {count} accounts (this may take a while)...")
        
        factory = TikTokAccountFactory(self.config['proxies_file'], self.config['accounts_db'])
        factory.create_bulk(count)
        
        input("\n  Press Enter to continue...")
    
    def view_accounts(self):
        """View accounts in database"""
        self.print_header()
        
        if not os.path.exists(self.config['accounts_db']):
            print("  [!] No account database found.")
            input("\n  Press Enter to continue...")
            return
        
        try:
            conn = sqlite3.connect(self.config['accounts_db'])
            accounts = conn.execute(
                "SELECT username, created_at FROM accounts ORDER BY created_at DESC LIMIT 50"
            ).fetchall()
            total = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
            conn.close()
            
            print(f"  Total accounts: {total}")
            print(f"  Showing last 50:")
            print()
            for i, (username, created) in enumerate(accounts, 1):
                print(f"    {i:3}. @{username:<20} Created: {created}")
            print()
        except Exception as e:
            print(f"  [!] Error: {e}")
        
        input("  Press Enter to continue...")
    
    def delete_accounts(self):
        """Delete all accounts"""
        self.print_header()
        print("  ⚠️  WARNING: This will delete ALL accounts!")
        print()
        
        confirm = input('  Type "DELETE" to confirm: ').strip()
        if confirm != "DELETE":
            print("\n  Cancelled.")
            input("\n  Press Enter to continue...")
            return
        
        if os.path.exists(self.config['accounts_db']):
            conn = sqlite3.connect(self.config['accounts_db'])
            conn.execute("DELETE FROM accounts")
            conn.commit()
            conn.close()
            print("\n  [+] All accounts deleted.")
        else:
            print("\n  [!] No database found.")
        
        input("\n  Press Enter to continue...")
    
    def export_accounts(self):
        """Export accounts to CSV"""
        self.print_header()
        
        if not os.path.exists(self.config['accounts_db']):
            print("  [!] No account database found.")
            input("\n  Press Enter to continue...")
            return
        
        filename = self.get_input("Export filename", "accounts_export.csv")
        
        try:
            conn = sqlite3.connect(self.config['accounts_db'])
            accounts = conn.execute("SELECT * FROM accounts").fetchall()
            conn.close()
            
            with open(filename, 'w') as f:
                f.write("username,email,password,device_id,proxy,user_id,created_at\n")
                for acc in accounts:
                    f.write(",".join(str(x) for x in acc) + "\n")
            
            print(f"\n  [+] Exported {len(accounts)} accounts to {filename}")
        except Exception as e:
            print(f"\n  [!] Export error: {e}")
        
        input("\n  Press Enter to continue...")
    
    def import_accounts(self):
        """Import accounts from CSV"""
        self.print_header()
        
        filename = self.get_input("Import filename", "accounts_export.csv")
        
        if not os.path.exists(filename):
            print(f"\n  [!] File not found: {filename}")
            input("\n  Press Enter to continue...")
            return
        
        try:
            conn = sqlite3.connect(self.config['accounts_db'])
            imported = 0
            with open(filename) as f:
                next(f)  # skip header
                for line in f:
                    parts = line.strip().split(',')
                    if len(parts) >= 6:
                        conn.execute(
                            "INSERT OR REPLACE INTO accounts VALUES (?,?,?,?,?,?, datetime('now'))",
                            parts[:6]
                        )
                        imported += 1
            conn.commit()
            conn.close()
            
            print(f"\n  [+] Imported {imported} accounts")
        except Exception as e:
            print(f"\n  [!] Import error: {e}")
        
        input("\n  Press Enter to continue...")
    
    def set_db_file(self):
        """Set database file"""
        self.print_header()
        
        db = self.get_input("Database filename", self.config['accounts_db'])
        if db:
            self.config['accounts_db'] = db
            print(f"\n  [+] Database set to: {db}")
        
        input("\n  Press Enter to continue...")
    
    def menu_config(self):
        """Configuration menu"""
        while True:
            self.print_header()
            
            print(f"  Current Configuration:")
            print(f"  ─────────────────────────────────────────────")
            print(f"  Proxies file:     {self.config['proxies_file'] or 'NOT SET'}")
            print(f"  Account DB:       {self.config['accounts_db']}")
            print(f"  Default guests:   {self.config['guest_count']:,}")
            print(f"  Default auth:     {self.config['auth_count']:,}")
            print(f"  Default duration: {self.config['duration']}s")
            print(f"  Guest workers:    {self.config['guest_workers']}")
            print(f"  Auth workers:     {self.config['auth_workers']}")
            print()
            
            options = {
                '1': ("Set Proxies File", self.set_proxies_file),
                '2': ("Set Account DB", self.set_db_file),
                '3': ("Set Defaults", self.set_attack_params),
                'b': ("🔙 Back to Main", None)
            }
            
            self.print_menu(options, "CONFIGURATION")
            choice = self.get_choice()
            
            if choice == 'b':
                return
            elif choice in options:
                options[choice][1]()
    
    def set_proxies_file(self):
        """Set proxies file"""
        self.print_header()
        print("  Enter path to proxy list file")
        print("  Format: http://user:pass@ip:port (one per line)")
        print()
        
        pf = self.get_input("Proxies file", "proxies.txt")
        if pf and os.path.exists(pf):
            # Validate
            with open(pf) as f:
                lines = [l.strip() for l in f if l.strip()]
            print(f"\n  [+] Found {len(lines)} proxies in {pf}")
            self.config['proxies_file'] = pf
        elif pf:
            print(f"\n  [!] File not found: {pf}")
        else:
            print("\n  [!] Invalid file")
        
        input("\n  Press Enter to continue...")
    
    def menu_stats(self):
        """View statistics"""
        self.print_header()
        
        print("  📊 Campaign Statistics")
        print("  ─────────────────────────────────────────────")
        print()
        
        if os.path.exists(self.config['accounts_db']):
            try:
                conn = sqlite3.connect(self.config['accounts_db'])
                
                # Account stats
                total_accounts = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
                print(f"  Total accounts:       {total_accounts}")
                
                # Session stats
                sessions = conn.execute("""
                    SELECT action, SUM(count), COUNT(*) 
                    FROM sessions GROUP BY action
                """).fetchall()
                
                if sessions:
                    print()
                    print("  Live Session History:")
                    for action, total, cnt in sessions:
                        print(f"    {action:<15} Total: {total:,} (in {cnt} sessions)")
                
                # Recent activity
                recent = conn.execute("""
                    SELECT room_id, action, SUM(count), MAX(timestamp)
                    FROM sessions 
                    GROUP BY room_id, action
                    ORDER BY MAX(timestamp) DESC LIMIT 10
                """).fetchall()
                
                if recent:
                    print()
                    print("  Recent Activity:")
                    for room, action, total, ts in recent:
                        print(f"    Room {room[:12]}... | {action:<10} | {total:>5} | {ts}")
                
                conn.close()
            except Exception as e:
                print(f"  [!] Error loading stats: {e}")
        else:
            print("  No database found. Run an attack first.")
        
        print()
        input("  Press Enter to continue...")
    
    def auto_setup(self):
        """Auto setup wizard"""
        self.print_header()
        print("  ⚙️  AUTO SETUP WIZARD")
        print("  ─────────────────────────────────────────────")
        print()
        print("  This will guide you through the complete setup.")
        print()
        
        # Step 1: Proxies
        print("  [Step 1/4] Proxy Configuration")
        print("  You need residential or mobile proxies.")
        print("  Recommended: BrightData, Oxylabs, or 911.re")
        print()
        
        pf = self.get_input("Path to proxy list file", "proxies.txt")
        if pf and os.path.exists(pf):
            with open(pf) as f:
                count = len([l for l in f if l.strip()])
            print(f"\n  ✅ Found {count} proxies")
            self.config['proxies_file'] = pf
        else:
            print(f"\n  ⚠️  File not found. Create {pf} with format:")
            print("     http://user:pass@ip:port")
            input("\n  Press Enter to create placeholder...")
            with open('proxies.txt', 'w') as f:
                f.write("# Add your proxies here (format: http://user:pass@ip:port)\n")
                f.write("# http://user:pass@proxy1:port\n")
            self.config['proxies_file'] = 'proxies.txt'
            print("  ✅ Created proxies.txt")
        
        # Step 2: Room ID
        print("\n  [Step 2/4] Live Room ID")
        room_id = self.get_input("Enter your TikTok Live Room ID")
        if room_id:
            self.config['room_id'] = room_id
            print(f"  ✅ Room ID set: {room_id}")
        else:
            print("  ⚠️  You can set this later in Attack Menu")
        
        # Step 3: Accounts
        print("\n  [Step 3/4] Account Strategy")
        print("  1. Pure Guest (no accounts needed)")
        print("  2. Create accounts first")
        print()
        account_choice = self.get_input("Choose [1/2]", "1")
        
        if account_choice == '2':
            count = self.get_input("How many accounts to create?", 5000, int)
            print(f"\n  [!] Creating {count} accounts...")
            
            if not SIGNER_AVAILABLE:
                print("  [!] SignerPy required for account creation!")
                print("  Install: pip install signerpy")
            else:
                self.initialize_bots()
                self.orchestrator.factory.create_bulk(count)
        else:
            print("  ✅ Using guest mode")
        
        # Step 4: Attack
        print("\n  [Step 4/4] Launch Attack")
        print("  1. Start attack now")
        print("  2. Configure more first")
        print()
        
        attack_choice = self.get_input("Choose [1/2]", "2")
        
        if attack_choice == '1':
            if self.config['room_id']:
                self.initialize_bots()
                
                if self.factory and self.factory.db_conn:
                    total = self.factory.db_conn.execute(
                        "SELECT COUNT(*) FROM accounts"
                    ).fetchone()[0]
                    self.config['auth_count'] = min(total, 500)
                
                self.orchestrator.combined_attack(
                    self.config['room_id'],
                    self.config['guest_count'],
                    self.config['auth_count'],
                    self.config['duration']
                )
            else:
                print("  ⚠️  No Room ID set. Go to Attack Menu to configure.")
        
        print("\n  ✅ Setup complete!")
        input("\n  Press Enter to continue...")
    
    def menu_about(self):
        """About screen"""
        self.print_header()
        print(f"  TikTok Live Engagement Engine v{VERSION}")
        print(f"  Built with SignerPy for authentic signatures")
        print()
        print("  Features:")
        print("  • Guest (anon) engagement - no accounts needed")
        print("  • Authenticated engagement - full TikTok features")
        print("  • Account creation factory")
        print("  • SignerPy X-Bogus / X-SS-STUB signatures")
        print("  • Android device fingerprint rotation")
        print("  • Residential proxy support")
        print("  • Advanced rate limiting evasion")
        print()
        print("  Requirements:")
        print("  • Residential/Mobile proxies (critical)")
        print("  • SignerPy for best results")
        print("  • Python 3.8+")
        print()
        print("  Legal: For authorized testing only.")
        print()
        input("  Press Enter to continue...")
    
    def run(self):
        """Run menu system"""
        try:
            self.menu_main()
        except KeyboardInterrupt:
            print("\n\n  [!] Interrupted by user")
            if self.guest:
                self.guest.running = False
            if self.auth:
                self.auth.running = False
            sys.exit(0)

# ──────────────────────────────────────────────
# COMMAND LINE ARGUMENTS
# ──────────────────────────────────────────────
def parse_args():
    parser = argparse.ArgumentParser(
        description=f"TikTok Live Engagement Engine v{VERSION}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive menu
  python tiktok_mega.py
  
  # Quick guest attack
  python tiktok_mega.py --room-id 123456789 --proxies proxies.txt --guests 5000
  
  # Combined attack
  python tiktok_mega.py --room-id 123456789 --proxies proxies.txt --guests 2000 --auth 500 --duration 7200
  
  # Create accounts
  python tiktok_mega.py --create-accounts 10000 --proxies proxies.txt
  
  # Auth-only with existing DB
  python tiktok_mega.py --room-id 123456789 --proxies proxies.txt --accounts tiktok_accounts.db --auth 1000
        """
    )
    
    parser.add_argument('--room-id', help='TikTok Live Room ID')
    parser.add_argument('--proxies', help='Proxy list file')
    parser.add_argument('--accounts', help='Accounts database file')
    parser.add_argument('--guests', type=int, default=0, help='Number of guest viewers')
    parser.add_argument('--auth', type=int, default=0, help='Number of authenticated accounts')
    parser.add_argument('--duration', type=int, default=3600, help='Attack duration in seconds')
    parser.add_argument('--guest-workers', type=int, default=100, help='Guest worker threads')
    parser.add_argument('--auth-workers', type=int, default=50, help='Auth worker threads')
    parser.add_argument('--create-accounts', type=int, help='Create N accounts')
    parser.add_argument('--pure-guests', action='store_true', help='Guest only mode')
    parser.add_argument('--pure-auth', action='store_true', help='Auth only mode')
    parser.add_argument('--menu', action='store_true', help='Force interactive menu')
    
    return parser.parse_args()

# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    args = parse_args()
    
    # Check for menu mode
    if args.menu or len(sys.argv) == 1:
        menu = MenuSystem()
        menu.run()
        return
    
    # Quick setup from args
    if args.create_accounts:
        if not args.proxies:
            print("[!] --proxies required for account creation")
            return
        
        print(f"[*] Creating {args.create_accounts} accounts...")
        factory = TikTokAccountFactory(args.proxies, args.accounts or 'tiktok_accounts.db')
        factory.create_bulk(args.create_accounts)
        return
    
    if not args.room_id:
        print("[!] --room-id required")
        return
    
    if not args.proxies:
        print("[!] --proxies required")
        return
    
    if not args.guests and not args.auth:
        print("[!] Specify --guests, --auth, or both")
        return
    
    # Initialize bots
    guest_bot = GuestEngagement()
    guest_bot.load_proxies(args.proxies)
    guest_bot.init_db(args.accounts or 'tiktok_accounts.db')
    guest_bot.running = True
    
    auth_bot = AuthenticatedEngagement()
    auth_bot.load_proxies(args.proxies)
    auth_bot.init_db(args.accounts or 'tiktok_accounts.db')
    auth_bot.running = True
    
    factory = TikTokAccountFactory(args.proxies, args.accounts or 'tiktok_accounts.db')
    
    orchestrator = AttackOrchestrator(guest_bot, auth_bot, factory)
    
    # Determine mode
    pure_guests = args.pure_guests or (args.guests > 0 and args.auth == 0)
    pure_auth = args.pure_auth or (args.auth > 0 and args.guests == 0)
    
    if pure_guests:
        # Start stats printer
        stats_thread = threading.Thread(target=orchestrator.stats_printer, daemon=True)
        stats_thread.start()
        
        orchestrator.guest_attack(
            args.room_id,
            args.guests,
            args.duration,
            args.guest_workers
        )
    elif pure_auth:
        accounts = factory.db_conn.execute(
            "SELECT * FROM accounts ORDER BY RANDOM() LIMIT ?",
            (args.auth,)
        ).fetchall()
        
        if not accounts:
            print("[!] No accounts in database!")
            return
        
        stats_thread = threading.Thread(target=orchestrator.stats_printer, daemon=True)
        stats_thread.start()
        
        orchestrator.auth_attack(
            args.room_id,
            accounts,
            args.duration,
            args.auth_workers
        )
    else:
        orchestrator.combined_attack(
            args.room_id,
            args.guests,
            args.auth,
            args.duration,
            args.guest_workers,
            args.auth_workers
        )
    
    print("\n[*] Attack complete!")

if __name__ == "__main__":
    main()
