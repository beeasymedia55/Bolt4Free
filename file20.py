#!/usr/bin/env python3
"""
TikTok Live Engagement Engine - Views, Likes, Shares, Comments
Supports: Authenticated (accounts) + Anonymous (guest) modes
pip install requests pysigner faker sqlite3 fake-useragent
"""

import requests
import json
import time
import random
import string
import threading
from itertools import cycle
from concurrent.futures import ThreadPoolExecutor
import sqlite3
import argparse
import base64
import hashlib
import urllib.parse
from fake_useragent import UserAgent
import pysigner

# ──────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────
TIKTOK_API_BASE = "https://api22-normal-c-useast1a.tiktokv.com"
TIKTOK_WEB_BASE = "https://www.tiktok.com"

ENGAGEMENT_TYPES = ['view', 'like', 'share', 'comment']

ANDROID_DEVICES = [
    {'device_id': 'android_7255253607933979658', 'iid': '72552536079339796580',
     'openudid': 'f1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6', 'model': 'SM-G998B',
     'os_version': '13', 'resolution': '1440*3200', 'dpi': '560'},
    {'device_id': 'android_8355253607933979669', 'iid': '83552536079339796690',
     'openudid': 'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d7', 'model': 'Pixel 8 Pro',
     'os_version': '14', 'resolution': '1344*2992', 'dpi': '420'},
    {'device_id': 'android_9455253612938979670', 'iid': '94552536129389796700',
     'openudid': 'b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e8', 'model': 'OnePlus 12',
     'os_version': '14', 'resolution': '1440*3168', 'dpi': '510'}
]

COMMENT_TEMPLATES = [
    {"text": "🔥🔥🔥", "type": "emoji"},
    {"text": "Let's goooooo!", "type": "hype"},
    {"text": "Best stream ever! 😍", "type": "praise"},
    {"text": "Hello from the bot army 🤖", "type": "meta"},
    {"text": "Can everyone type L in chat?", "type": "interaction"},
    {"text": "Go viral! 🚀", "type": "viral"},
    {"text": "niceee", "type": "simple"},
    {"text": "😂😂 10/10", "type": "funny"},
    {"text": "Keep it up!", "type": "support"},
    {"text": "i love this content", "type": "love"},
    {"text": "WOW WOW WOW", "type": "excited"},
    {"text": "first time here! cool stream", "type": "new"},
    {"text": "subbed! 🔔", "type": "subscribe"},
    {"text": "POG", "type": "twitch"},
    {"text": "💯💯", "type": "hundred"}
]

# ──────────────────────────────────────────────
# CORE BOT ENGINE
# ──────────────────────────────────────────────
class TikTokLiveBot:
    def __init__(self, proxies_file=None, accounts_db=None):
        self.ua = UserAgent()
        self.device_pool = cycle(ANDROID_DEVICES)
        self.proxies = []
        if proxies_file:
            with open(proxies_file) as f:
                self.proxies = [line.strip() for line in f if line.strip()]
        self.proxy_pool = cycle(self.proxies) if self.proxies else None
        
        # Account management
        self.accounts = []
        if accounts_db:
            self.conn = sqlite3.connect(accounts_db)
            self.accounts = self.conn.execute("SELECT * FROM accounts").fetchall()
        
        self.signers = {}
    
    def get_headers(self, authenticated=False, token=None):
        """Generate headers for web or mobile requests"""
        device = next(self.device_pool)
        ua = self.ua.random if authenticated else self.ua.android
        
        headers = {
            'User-Agent': ua,
            'Accept': '*/*',
            'Accept-Encoding': 'gzip',
            'Accept-Language': 'en,en-US;q=0.9',
            'Content-Type': 'application/json; charset=utf-8',
            'Origin': TIKTOK_WEB_BASE,
            'Referer': f'{TIKTOK_WEB_BASE}/',
        }
        
        if authenticated and token:
            headers['Authorization'] = f'Bearer {token}'
        
        return headers
    
    def get_session(self, proxy=None):
        """Create session with optional proxy"""
        session = requests.Session()
        if proxy:
            session.proxies = {'http': proxy, 'https': proxy}
        return session
    
    def generate_signature(self, params):
        """Generate X-Bogus signature"""
        signer = pysigner.TikTokSigner()
        try:
            return signer.sign(params).get('X-Bogus', '')
        except:
            query = '&'.join([f"{k}={urllib.parse.quote(str(v))}" for k,v in sorted(params.items())])
            return hashlib.md5(query.encode()).hexdigest()
    
    def generate_device_params(self):
        """Generate Android fingerprint params"""
        device = next(self.device_pool)
        return {
            'device_id': device['device_id'],
            'iid': device['iid'],
            'openudid': device['openudid'],
            'device_platform': 'android',
            'os_version': device['os_version'],
            'resolution': device['resolution'],
            'dpi': device['dpi'],
            'aid': '1180',
            'app_version': '35.7.0',
            'app_name': 'trill',
            'channel': 'googleplay',
            '_rticket': int(time.time() * 1000)
        }

# ──────────────────────────────────────────────
# ENGAGEMENT FUNCTIONS - WITHOUT ACCOUNTS (GUEST)
# ──────────────────────────────────────────────
class GuestEngagement(TikTokLiveBot):
    """Anonymous engagement - no login required"""
    
    def _guest_join(self, session, room_id):
        """Join live room as guest viewer"""
        url = f"{TIKTOK_API_BASE}/aweme/v1/webcast/join/"
        params = self.generate_device_params()
        params.update({
            'room_id': room_id,
            'enter_from': 'live_center',
            'enter_method': random.choice(['scan', 'feed', 'share'])
        })
        
        x_bogus = self.generate_signature(params)
        
        headers = self.get_headers()
        headers['X-Bogus'] = x_bogus
        
        payload = {
            "room_id": int(room_id),
            "user_id": f"guest_{random.randint(1000000, 9999999)}",
            "enter_method": params['enter_method']
        }
        
        resp = session.post(url, json=payload, headers=headers, timeout=15)
        return resp.status_code in [200, 204, 0]
    
    def _guest_like(self, session, room_id):
        """Like as guest (limited effectiveness)"""
        url = f"{TIKTOK_API_BASE}/aweme/v1/webcast/like/"
        params = self.generate_device_params()
        params.update({'room_id': room_id})
        
        x_bogus = self.generate_signature(params)
        headers = self.get_headers()
        headers['X-Bogus'] = x_bogus
        
        payload = {
            "room_id": int(room_id),
            "like_count": random.randint(1, 3),
            "timestamp": int(time.time())
        }
        
        resp = session.post(url, json=payload, headers=headers, timeout=10)
        return resp.ok
    
    def _guest_share(self, session, room_id):
        """Share as guest - triggers viral boost"""
        url = f"{TIKTOK_API_BASE}/aweme/v1/webcast/share/"
        params = self.generate_device_params()
        params.update({
            'room_id': room_id,
            'share_type': random.choice(['copy', 'whatsapp', 'twitter', 'instagram', 'sms'])
        })
        
        x_bogus = self.generate_signature(params)
        headers = self.get_headers()
        headers['X-Bogus'] = x_bogus
        
        payload = {
            "room_id": int(room_id),
            "share_type": params['share_type']
        }
        
        resp = session.post(url, json=payload, headers=headers, timeout=10)
        return resp.ok
    
    def _guest_comment(self, session, room_id):
        """Comment as guest (only works sometimes)"""
        url = f"{TIKTOK_API_BASE}/aweme/v1/webcast/comment/"
        params = self.generate_device_params()
        params.update({'room_id': room_id})
        
        x_bogus = self.generate_signature(params)
        headers = self.get_headers()
        headers['X-Bogus'] = x_bogus
        
        comment = random.choice(COMMENT_TEMPLATES)
        payload = {
            "room_id": int(room_id),
            "content": comment['text'],
            "comment_type": comment['type']
        }
        
        resp = session.post(url, json=payload, headers=headers, timeout=10)
        return resp.ok
    
    def _guest_heartbeat(self, session, room_id):
        """Keep guest view counted"""
        url = f"{TIKTOK_API_BASE}/aweme/v1/webcast/enter/"
        while True:
            try:
                params = self.generate_device_params()
                params.update({'room_id': room_id, 'status': 1})
                x_bogus = self.generate_signature(params)
                headers = self.get_headers()
                headers['X-Bogus'] = x_bogus
                
                session.post(url, json={"room_id": int(room_id), "status": 1},
                           headers=headers, timeout=5)
                time.sleep(random.uniform(27, 35))
            except:
                break
    
    def guest_engagement_cycle(self, room_id, duration=1800):
        """Single guest doing all engagement types"""
        proxy = next(self.proxy_pool) if self.proxy_pool else None
        session = self.get_session(proxy)
        
        try:
            if not self._guest_join(session, room_id):
                return False, 0, 0, 0, 0
            
            hb_thread = threading.Thread(target=self._guest_heartbeat, args=(session, room_id))
            hb_thread.daemon = True
            hb_thread.start()
            
            likes = shares = comments = 0
            end_time = time.time() + duration
            
            while time.time() < end_time:
                action = random.choices(
                    ['like', 'share', 'comment', 'sleep'],
                    weights=[30, 5, 10, 55],
                    k=1
                )[0]
                
                if action == 'like' and self._guest_like(session, room_id):
                    likes += 1
                elif action == 'share' and self._guest_share(session, room_id):
                    shares += 1
                elif action == 'comment' and self._guest_comment(session, room_id):
                    comments += 1
                
                time.sleep(random.uniform(1, 8))
            
            return True, 1, likes, shares, comments
            
        except Exception as e:
            print(f"[!] Guest error: {e}")
            return False, 0, 0, 0, 0

# ──────────────────────────────────────────────
# ENGAGEMENT FUNCTIONS - WITH ACCOUNTS
# ──────────────────────────────────────────────
class AuthenticatedEngagement(TikTokLiveBot):
    """Authenticated engagement - full TikTok features"""
    
    def _login_account(self, account):
        """Login with stored credentials"""
        username, email, password, device_id, proxy = account[:5]
        proxy = proxy or next(self.proxy_pool) if self.proxy_pool else None
        
        session = self.get_session(proxy)
        
        login_url = f"{TIKTOK_API_BASE}/passport/web/login/"
        params = self.generate_device_params()
        params.update({'username': username})
        
        x_bogus = self.generate_signature(params)
        headers = self.get_headers(authenticated=False)
        headers['X-Bogus'] = x_bogus
        
        payload = {
            "username": username,
            "password": password,
            "device_id": device_id or params['device_id']
        }
        
        resp = session.post(login_url, json=payload, headers=headers, timeout=15)
        
        if resp.status_code == 200:
            data = resp.json()
            token = data.get('data', {}).get('token', {}).get('access_token')
            user_id = data.get('data', {}).get('user_id')
            if token:
                session.headers['Authorization'] = f'Bearer {token}'
                return session, user_id, token
        
        return None, None, None
    
    def _like(self, session, room_id, user_id):
        """Send authenticated like"""
        url = f"{TIKTOK_API_BASE}/aweme/v1/webcast/like/"
        payload = {
            "room_id": int(room_id),
            "user_id": user_id,
            "like_count": random.randint(1, 5),
            "timestamp": int(time.time())
        }
        resp = session.post(url, json=payload, timeout=10)
        return resp.ok
    
    def _share(self, session, room_id, user_id):
        """Send authenticated share"""
        url = f"{TIKTOK_API_BASE}/aweme/v1/webcast/share/"
        payload = {
            "room_id": int(room_id),
            "user_id": user_id,
            "share_type": random.choice(['copy', 'whatsapp', 'twitter', 'instagram', 'sms'])
        }
        resp = session.post(url, json=payload, timeout=10)
        return resp.ok
    
    def _comment(self, session, room_id, user_id):
        """Post authenticated comment"""
        url = f"{TIKTOK_API_BASE}/aweme/v1/webcast/comment/"
        comment = random.choice(COMMENT_TEMPLATES)
        payload = {
            "room_id": int(room_id),
            "user_id": user_id,
            "content": comment['text'],
            "comment_type": comment['type']
        }
        resp = session.post(url, json=payload, timeout=10)
        return resp.ok
    
    def authenticated_engagement_cycle(self, account, room_id, duration=1800):
        """Single authenticated account doing all engagement"""
        session, user_id, token = self._login_account(account)
        if not session or not user_id:
            return False, 0, 0, 0, 0
        
        username = account[0]
        print(f"[+] @{username} authenticated")
        
        views = 1
        likes = shares = comments = 0
        end_time = time.time() + duration
        
        while time.time() < end_time:
            action = random.choices(
                ['like', 'share', 'comment', 'view', 'sleep'],
                weights=[35, 5, 15, 5, 10],
                k=1
            )[0]
            
            if action == 'like' and self._like(session, room_id, user_id):
                likes += 1
                print(f"   @{username} liked ({likes})")
            elif action == 'share' and self._share(session, room_id, user_id):
                shares += 1
                print(f"   @{username} shared ({shares})")
            elif action == 'comment' and self._comment(session, room_id, user_id):
                comments += 1
                print(f"   @{username} commented ({comments})")
            
            time.sleep(random.uniform(2, 15))
            views += 1  # Every interaction counts as view
        
        return True, views, likes, shares, comments

# ──────────────────────────────────────────────
# ORCHESTRATOR - COMBINE GUEST + AUTHENTICATED
# ──────────────────────────────────────────────
class TikTokEngagementOrchestrator:
    def __init__(self, guest_bot, auth_bot):
        self.guest = guest_bot
        self.auth = auth_bot
        self.stats = {'views': 0, 'likes': 0, 'shares': 0, 'comments': 0}
    
    def launch_guests(self, room_id, count=500, duration=1800):
        """Deploy guest (anon) engagements"""
        print(f"\n[*] Deploying {count} GUEST viewers on {room_id}")
        
        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = [
                executor.submit(self.guest.guest_engagement_cycle, room_id, duration)
                for _ in range(count)
            ]
            
            for i, f in enumerate(futures, 1):
                success, views, likes, shares, comments = f.result()
                if success:
                    self.stats['views'] += views
                    self.stats['likes'] += likes
                    self.stats['shares'] += shares
                    self.stats['comments'] += comments
                
                if i % 50 == 0:
                    print(f"[*] Guest progress: {i}/{count} | Live stats: {self.stats}")
        
        return self.stats
    
    def launch_authenticated(self, room_id, accounts, duration=1800):
        """Deploy authenticated account engagements"""
        count = len(accounts)
        print(f"\n[*] Deploying {count} AUTHENTICATED accounts on {room_id}")
        
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [
                executor.submit(self.auth.authenticated_engagement_cycle, acc, room_id, duration)
                for acc in accounts
            ]
            
            for i, f in enumerate(futures, 1):
                success, views, likes, shares, comments = f.result()
                if success:
                    self.stats['views'] += views
                    self.stats['likes'] += likes
                    self.stats['shares'] += shares
                    self.stats['comments'] += comments
                
                if i % 25 == 0:
                    print(f"[*] Auth progress: {i}/{count} | Live stats: {self.stats}")
        
        return self.stats
    
    def combined_attack(self, room_id, guest_count=2000, auth_count=500, duration=3600):
        """Full attack: guests + authenticated accounts"""
        print(f"\n{'='*60}")
        print(f"🚀 TIKTOK LIVE ENGAGEMENT ATTACK")
        print(f"📺 Room: {room_id}")
        print(f"👻 Guests: {guest_count}")
        print(f"👤 Accounts: {auth_count}")
        print(f"⏱ Duration: {duration}s")
        print(f"{'='*60}\n")
        
        # Phase 1: Guests join first (establish base viewers)
        print("[Phase 1] Deploying guest viewers...")
        guest_thread = threading.Thread(
            target=self.launch_guests, args=(room_id, guest_count, duration)
        )
        guest_thread.start()
        
        time.sleep(5)
        
        # Phase 2: Authenticated accounts engage
        print("[Phase 2] Deploying authenticated accounts...")
        auth_thread = threading.Thread(
            target=self.launch_authenticated,
            args=(room_id, self.auth.accounts[:auth_count], duration)
        )
        auth_thread.start()
        
        # Wait for completion
        guest_thread.join()
        auth_thread.join()
        
        print(f"\n{'='*60}")
        print(f"🎯 ATTACK COMPLETE")
        print(f"📊 Final Stats:")
        print(f"   Views:    {self.stats['views']:,}")
        print(f"   Likes:    {self.stats['likes']:,}")
        print(f"   Shares:   {self.stats['shares']:,}")
        print(f"   Comments: {self.stats['comments']:,}")
        print(f"{'='*60}")
        
        return self.stats

# ──────────────────────────────────────────────
# ACCOUNT CREATOR (for auth mode)
# ──────────────────────────────────────────────
class TikTokAccountFactory:
    def __init__(self, proxies_file, db_file='tiktok_accounts.db'):
        self.proxies = []
        with open(proxies_file) as f:
            self.proxies = [line.strip() for line in f if line.strip()]
        self.proxy_pool = cycle(self.proxies)
        self.conn = sqlite3.connect(db_file)
        self.conn.execute('''CREATE TABLE IF NOT EXISTS accounts
            (username TEXT PRIMARY KEY, email TEXT, password TEXT, 
             device_id TEXT, proxy TEXT, user_id TEXT, 
             created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        self.conn.commit()
    
    def generate_credentials(self):
        username = f"livebot_{random.randint(100000, 999999)}"
        email = f"{username}@tempmail.lol"
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=14))
        return username, email, password
    
    def create_account(self):
        proxy = next(self.proxy_pool)
        username, email, password = self.generate_credentials()
        device_id = f"android_{random.randint(7000000000000000000, 7999999999999999999)}"
        
        session = requests.Session()
        session.proxies = {'http': proxy, 'https': proxy}
        
        # Register
        url = f"{TIKTOK_API_BASE}/passport/web/register/"
        payload = {
            "username": username,
            "email": email,
            "password": password,
            "device_id": device_id,
            "region": "US",
            "language": "en"
        }
        
        signer = pysigner.TikTokSigner()
        
        resp = session.post(url, json=payload, headers={
            'User-Agent': 'Mozilla/5.0 (Linux; Android 13; SM-G998B Build/TP1A.220624.014)',
            'X-Bogus': signer.sign(payload).get('X-Bogus', ''),
            'Content-Type': 'application/json'
        }, timeout=20)
        
        if resp.status_code == 200 and 'user_id' in resp.json():
            data = resp.json()
            self.conn.execute("INSERT INTO accounts VALUES (?,?,?,?,?,?, datetime('now'))",
                            (username, email, password, device_id, proxy, data.get('user_id')))
            self.conn.commit()
            return username, proxy
        
        return None, None
    
    def create_bulk(self, count=1000):
        print(f"[*] Creating {count} accounts...")
        success = 0
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(self.create_account) for _ in range(count)]
            for i, f in enumerate(futures, 1):
                result = f.result()
                if result[0]:
                    success += 1
                if i % 100 == 0:
                    print(f"[*] Progress: {success}/{i} accounts created")
        print(f"[+] Created {success}/{count} accounts")

# ──────────────────────────────────────────────
# MAIN ENTRY POINT
# ──────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="TikTok Live Engagement Engine")
    parser.add_argument('--room-id', required=True, help="Live room ID")
    parser.add_argument('--proxies', required=True, help="Proxy list file")
    parser.add_argument('--accounts', help="Accounts database (for auth mode)")
    parser.add_argument('--guests', type=int, default=1000, help="Guest viewers")
    parser.add_argument('--auth-accounts', type=int, default=0, help="Auth accounts to use")
    parser.add_argument('--duration', type=int, default=3600, help="Attack duration (s)")
    parser.add_argument('--pure-guests', action='store_true', help="Guests only (no accounts)")
    parser.add_argument('--pure-auth', action='store_true', help="Auth only (no guests)")
    parser.add_argument('--create-accounts', type=int, help="Create N accounts and exit")
    
    args = parser.parse_args()
    
    # Account creation mode
    if args.create_accounts:
        factory = TikTokAccountFactory(args.proxies)
        factory.create_bulk(args.create_accounts)
        return
    
    # Initialize bots
    guest_bot = GuestEngagement(proxies_file=args.proxies)
    auth_bot = AuthenticatedEngagement(proxies_file=args.proxies, accounts_db=args.accounts)
    
    orchestrator = TikTokEngagementOrchestrator(guest_bot, auth_bot)
    
    if args.pure_guests:
        orchestrator.launch_guests(args.room_id, args.guests, args.duration)
    elif args.pure_auth:
        if not args.accounts:
            print("[!] Need --accounts db for authenticated mode")
            return
        orchestrator.launch_authenticated(
            args.room_id,
            auth_bot.accounts[:args.auth_accounts],
            args.duration
        )
    else:
        orchestrator.combined_attack(
            args.room_id,
            guest_count=args.guests,
            auth_count=args.auth_accounts or 0,
            duration=args.duration
        )

if __name__ == "__main__":
    main()
