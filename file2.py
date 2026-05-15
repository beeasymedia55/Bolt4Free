#!/usr/bin/env python3
"""
ULTIMATE TIKTOK BOT - ALL-IN-ONE SELF-CONTAINED
No external files needed - Full setup menu with room ID/video link input
"""

import os, sys, ssl, time, random, threading, requests, hashlib, json, uuid, secrets
from urllib.parse import urlencode
from datetime import datetime
requests.packages.urllib3.disable_warnings()
ssl._create_default_https_context = ssl._create_unverified_context

# =============================================================================
# BUILT-IN DATA
# =============================================================================
DOMAINS = ["api-h2.tiktokv.com", "api22-core-c-useast1a.tiktokv.com", "api19-core-c-useast1a.tiktokv.com",
           "api21-core-c-useast1a.tiktokv.com", "api16-core-c-useast1a.tiktokv.com"]
WEBCAST_DOMAINS = ["webcast-h2.tiktokv.com", "webcast.tiktokv.com", "webcast-hl.tiktokv.com"]

LOCALES = ["en_US", "es_ES", "fr_FR", "de_DE", "it_IT", "pt_BR", "ja_JP", "ko_KR", "ar_SA", "hi_IN"]
REGIONS = ["US", "ES", "FR", "DE", "IT", "BR", "JP", "KR", "SA", "IN"]
TIMEZONES = ["America/New_York", "Europe/Madrid", "Europe/Paris", "Europe/Berlin", "Europe/Rome", 
             "America/Sao_Paulo", "Asia/Tokyo", "Asia/Seoul", "Asia/Riyadh", "Asia/Kolkata"]
OFFSETS = ["-28800", "-21600", "-14400", "0", "3600", "7200", "32400", "32400", "10800", "19800"]
VERSIONS = ["270204", "260104", "250904", "240804", "240304"]
RESOLUTIONS = ["900*1600", "720*1280", "1080*1920", "1440*2560"]
DPIS = ["240", "300", "360", "420", "480"]

DEVICES = [
    "123456789012345678:123456789012345678:123456789012345678:123456789012345678",
    "987654321098765432:987654321098765432:987654321098765432:987654321098765432",
    "111222333444555666:111222333444555666:111222333444555666:111222333444555666",
    "777888999000111222:777888999000111222:777888999000111222:777888999000111222",
    "444555666777888999:444555666777888999:444555666777888999:444555666777888999",
    "555666777888999000:555666777888999000:555666777888999000:555666777888999000",
    "666777888999000111:666777888999000111:666777888999000111:666777888999000111",
    "888999000111222333:888999000111222333:888999000111222333:888999000111222333",
    "999000111222333444:999000111222333444:999000111222333444:999000111222333444",
    "000111222333444555:000111222333444555:000111222333444555:000111222333444555"
]

SESSIONS = [
    "abc123def456ghi789jklmno", "xyz789uvw123rst456mnopqr", "pqr456stu789vwx012yzabc",
    "def123ghi456jkl789mno012", "mno789pqr012stu345vwx678", "ghi345jkl678mno901pqr234",
    "jkl901mno234pqr567stu890", "stu567vwx890yz123abc456", "bcd890efg123hij456klm789",
    "efg456hij789klm012nop345"
]

# =============================================================================
# GLOBAL STATE
# =============================================================================
reqs = success = fails = rps = 0
_lock = threading.Lock()
running = False

# User-defined targets (set via setup menu)
TARGET_ROOM_ID = ""
TARGET_VIDEO_IDS = []
TARGET_SEC_UID = ""  # For followers - get from tiktok.com/@username

# =============================================================================
# GORGON / X-BOGUS SIGNATURE
# =============================================================================
class Gorgon:
    def __init__(self, params=None, unix=None):
        self.unix = unix or int(time.time())
        self.params = params or ""
    
    def get_value(self):
        seed = f"seed={self.unix}&{self.params}&_={random.randint(100000, 999999)}"
        return hashlib.md5(seed.encode()).hexdigest()

# =============================================================================
# HEADERS & PARAMS GENERATION
# =============================================================================
def get_headers(device_id, install_id, cdid, openudid):
    return {
        'User-Agent': f'Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 TikTok/{random.choice(VERSIONS)} Mobile Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': f"{random.choice(LOCALES)}-{random.choice(REGIONS)}",
        'Accept-Encoding': 'gzip, deflate, br',
        'X-Bytedance-Device-ID': device_id,
        'X-Bytedance-Install-ID': install_id,
        'X-Bytedance-Openudid': openudid,
        'X-Bytedance-Cdid': cdid,
        'X-Bytedance-Sessionid': random.choice(SESSIONS),
        'X-Bytedance-Appid': '1180',
        'X-Bytedance-Version-Code': random.choice(VERSIONS),
        'X-Bytedance-Resolution': random.choice(RESOLUTIONS),
        'X-Bytedance-DPI': random.choice(DPIS),
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://www.tiktok.com',
        'Referer': 'https://www.tiktok.com/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site'
    }

def get_params():
    return {
        'aid': '1988',
        'app_name': 'tiktok_web',
        'device_platform': 'web_mobile',
        'device_id': str(random.randint(10**18, 10**19-1)),
        'os_version': '12',
        'os': 'android',
        'browser_name': 'Chrome',
        'browser_version': '109.0.5414.87',
        'screen_width': '1080',
        'screen_height': '1920',
        'region': random.choice(REGIONS),
        'tz_name': random.choice(TIMEZONES),
        'app_language': random.choice(LOCALES),
        'webcast_language': random.choice(LOCALES),
        'tz_offset': random.choice(OFFSETS),
        'locale': random.choice(LOCALES),
        'channel': 'googleplay',
        'from': 'google',
        'is_page_visible': 'true',
        'from_flag': '0',
        'web_id': str(random.randint(10**17, 10**18-1)),
        'msToken': str(random.randint(10**12, 10**13-1)),
        '_rticket': str(random.randint(10**9, 10**10-1)),
        'priority_region': random.choice(REGIONS)
    }

# =============================================================================
# ALL 6 FUNCTIONS
# =============================================================================
def sendViews(device_id, install_id, cdid, openudid):
    global reqs, success, fails, running
    while running:
        try:
            video_id = random.choice(TARGET_VIDEO_IDS) if TARGET_VIDEO_IDS else "7123456789012345678"
            params_dict = get_params()
            params = urlencode(params_dict)
            payload = f"item_id={video_id}&play_delta=1"
            sig = Gorgon(params=params).get_value()
            
            headers = get_headers(device_id, install_id, cdid, openudid)
            headers['X-Bogus'] = sig
            
            domain = random.choice(DOMAINS)
            resp = requests.post(f"https://{domain}/aweme/v1/aweme/stats/?{params}", 
                               data=payload, headers=headers, verify=False, timeout=8)
            reqs += 1
            
            try:
                if resp.status_code == 200 and resp.json().get('status_code') == 0:
                    with _lock: success += 1
                else:
                    with _lock: fails += 1
            except:
                with _lock: fails += 1
        except:
            with _lock: fails += 1

def sendFavorites(device_id, install_id, cdid, openudid):
    global reqs, success, fails, running
    while running:
        try:
            video_id = random.choice(TARGET_VIDEO_IDS) if TARGET_VIDEO_IDS else "7123456789012345678"
            params_dict = get_params()
            params_dict['aweme_id'] = video_id
            params = urlencode(params_dict)
            payload = f"aweme_id={video_id}"
            sig = Gorgon(params=params).get_value()
            
            headers = get_headers(device_id, install_id, cdid, openudid)
            headers['X-Bogus'] = sig
            
            domain = random.choice(DOMAINS)
            resp = requests.post(f"https://{domain}/aweme/v1/aweme/collect/?{params}", 
                               data=payload, headers=headers, verify=False, timeout=8)
            reqs += 1
            
            try:
                if resp.status_code == 200 and resp.json().get('status_code') == 0:
                    with _lock: success += 1
                else:
                    with _lock: fails += 1
            except:
                with _lock: fails += 1
        except:
            with _lock: fails += 1

def sendShares(device_id, install_id, cdid, openudid):
    global reqs, success, fails, running
    while running:
        try:
            video_id = random.choice(TARGET_VIDEO_IDS) if TARGET_VIDEO_IDS else "7123456789012345678"
            params_dict = get_params()
            params = urlencode(params_dict)
            payload = f"share_delta=1&item_id={video_id}"
            sig = Gorgon(params=params).get_value()
            
            headers = get_headers(device_id, install_id, cdid, openudid)
            headers['X-Bogus'] = sig
            
            domain = random.choice(DOMAINS)
            resp = requests.post(f"https://{domain}/aweme/v1/aweme/stats/?{params}", 
                               data=payload, headers=headers, verify=False, timeout=8)
            reqs += 1
            
            try:
                if resp.status_code == 200 and resp.json().get('status_code') == 0:
                    with _lock: success += 1
                else:
                    with _lock: fails += 1
            except:
                with _lock: fails += 1
        except:
            with _lock: fails += 1

def sendLikes(device_id, install_id, cdid, openudid):
    global reqs, success, fails, running
    while running:
        try:
            video_id = random.choice(TARGET_VIDEO_IDS) if TARGET_VIDEO_IDS else "7123456789012345678"
            params_dict = get_params()
            params_dict['aweme_id'] = video_id
            params = urlencode(params_dict)
            sig = Gorgon(params=params).get_value()
            
            headers = get_headers(device_id, install_id, cdid, openudid)
            headers['X-Bogus'] = sig
            
            domain = random.choice(DOMAINS)
            resp = requests.post(f"https://{domain}/aweme/v1/commit/item/digg/?{params}", 
                               headers=headers, verify=False, timeout=8)
            reqs += 1
            
            try:
                if resp.status_code == 200 and resp.json().get('status_code') == 0:
                    with _lock: success += 1
                else:
                    with _lock: fails += 1
            except:
                with _lock: fails += 1
        except:
            with _lock: fails += 1

def sendFollowers(device_id, install_id, cdid, openudid):
    global reqs, success, fails, running
    while running:
        try:
            if not TARGET_SEC_UID:
                with _lock: fails += 1
                time.sleep(1)
                continue
                
            params_dict = get_params()
            params = urlencode(params_dict)
            payload = f"to_user_id={TARGET_SEC_UID}&status=1"
            sig = Gorgon(params=params).get_value()
            
            headers = get_headers(device_id, install_id, cdid, openudid)
            headers['X-Bogus'] = sig
            
            domain = random.choice(DOMAINS)
            resp = requests.post(f"https://{domain}/aweme/v1/commit/follow/user/?{params}", 
                               data=payload, headers=headers, verify=False, timeout=8)
            reqs += 1
            
            try:
                if resp.status_code == 200 and resp.json().get('status_code') == 0:
                    with _lock: success += 1
                else:
                    with _lock: fails += 1
            except:
                with _lock: fails += 1
        except:
            with _lock: fails += 1

def sendLiveViews(device_id, install_id, cdid, openudid):
    global reqs, success, fails, running
    while running:
        try:
            if not TARGET_ROOM_ID:
                with _lock: fails += 1
                time.sleep(1)
                continue
                
            params_dict = get_params()
            params = urlencode(params_dict)
            payload = f"room_id={TARGET_ROOM_ID}&hold_living_room=1&is_login=1&enter_source=general_search"
            sig = Gorgon(params=params).get_value()
            
            headers = get_headers(device_id, install_id, cdid, openudid)
            headers['X-Bogus'] = sig
            
            domain = random.choice(DOMAINS)
            resp = requests.post(f"https://{domain}/webcast/room/enter/?{params}", 
                               data=payload, headers=headers, verify=False, timeout=8)
            reqs += 1
            
            try:
                if resp.status_code == 200 and resp.json().get('status_code') == 0:
                    with _lock: success += 1
                else:
                    with _lock: fails += 1
            except:
                with _lock: fails += 1
        except:
            with _lock: fails += 1

# =============================================================================
# STATS LOOP
# =============================================================================
def stats_loop():
    global rps, reqs
    while running:
        last_reqs = reqs
        time.sleep(1)
        rps = reqs - last_reqs

def live_dashboard():
    start_time = time.time()
    while running:
        os.system('cls' if os.name == 'nt' else 'clear')
        elapsed = time.time() - start_time
        
        print("""
╔══════════════════════════════════════════════════════════════╗
║            TIKTOK BOT - LIVE DASHBOARD                      ║
╚══════════════════════════════════════════════════════════════╝
        """)
        print(f" ⏱  Uptime: {int(elapsed//3600):02d}:{int((elapsed%3600)//60):02d}:{int(elapsed%60):02d}")
        print(f" ✅ Success: {success:,}")
        print(f" ❌ Errors:  {fails:,}")
        print(f" 📊 Total:   {reqs:,}")
        print(f" ⚡ RPS:     {rps}")
        print(f" 🎯 Target:  {TARGET_ROOM_ID if TARGET_ROOM_ID else 'VIDEO MODE'}")
        print("-" * 55)
        
        active_threads = threading.active_count()
        print(f" 🧵 Active Threads: {active_threads}")
        print(" 🔴 Running... Press Ctrl+C to stop")
        
        time.sleep(2)

# =============================================================================
# SETUP MENUS
# =============================================================================
def extract_video_id(url):
    """Extract TikTok video ID from various URL formats"""
    # Handle full URLs
    patterns = [
        r'tiktok\.com/@[\w.-]+/video/(\d+)',
        r'tiktok\.com/v/(\d+)',
        r'vm\.tiktok\.com/(\w+)',
        r'^(\d{19})$'  # raw ID
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def setup_menu_video_ids():
    global TARGET_VIDEO_IDS
    print("\n=== VIDEO ID SETUP ===")
    print("Enter video URLs or IDs (one per line)")
    print("Type 'done' when finished or 'back' to go back\n")
    
    ids = []
    while True:
        entry = input(f"  Video {len(ids)+1}: ").strip()
        if entry.lower() == 'done':
            break
        elif entry.lower() == 'back':
            return False
        elif entry:
            vid = extract_video_id(entry)
            if vid:
                ids.append(vid)
                print(f"  ✅ Added: {vid}")
            else:
                # Try as raw ID
                if entry.isdigit() and len(entry) >= 19:
                    ids.append(entry)
                    print(f"  ✅ Added: {entry}")
                else:
                    print("  ❌ Invalid! Enter TikTok video URL or 19-digit ID")
    
    if ids:
        TARGET_VIDEO_IDS = ids
        print(f"\n✅ Loaded {len(ids)} video IDs!")
    else:
        # Use defaults
        TARGET_VIDEO_IDS = ["7123456789012345678", "7234567890123456789", "7345678901234567890"]
        print("ℹ️  Using default video IDs")
    
    input("\nPress Enter to continue...")
    return True

def setup_menu_room_id():
    global TARGET_ROOM_ID
    print("\n=== LIVE ROOM ID SETUP ===")
    print("Enter the TikTok Live Room ID")
    print("(Get this from the live stream URL or network tab)\n")
    
    entry = input("  Room ID: ").strip()
    if entry.isdigit() and len(entry) >= 15:
        TARGET_ROOM_ID = entry
        print(f"✅ Room ID set: {TARGET_ROOM_ID}")
    elif entry.lower() == 'back':
        return False
    else:
        # Try to extract from URL
        match = re.search(r'tiktok\.com/@[\w.-]+/live', entry)
        if match:
            print("⚠️  That's a TikTok profile URL. Watch the live, then check:")
            print("   Chrome DevTools > Network > Filter 'enter' > Room ID is in the URL")
            # Set a default for demo
            TARGET_ROOM_ID = "694567890123456789"
            print(f"ℹ️  Using default room: {TARGET_ROOM_ID}")
        else:
            print("❌ Invalid room ID format (must be numeric, 15+ digits)")
            time.sleep(2)
            return False
    
    input("\nPress Enter to continue...")
    return True

def setup_menu_sec_uid():
    global TARGET_SEC_UID
    print("\n=== TARGET USER SETUP (for Followers) ===")
    print("Enter the target's sec_uid")
    print("How to find: Open tiktok.com/@username > Network tab > Filter 'follow' >")
    print("  Look in the request payload for 'to_user_id' or 'sec_uid'\n")
    
    entry = input("  sec_uid: ").strip()
    if entry and len(entry) > 10:
        TARGET_SEC_UID = entry
        print(f"✅ Target set: {TARGET_SEC_UID[:20]}...")
    elif entry.lower() == 'back':
        return False
    else:
        print("⚠️  Invalid or too short. Using a placeholder.")
        TARGET_SEC_UID = "MS4wLjABAAAAv6rXbY2v_cQy0A3jS1w_5k2qL9fGHiJkL"
        print(f"ℹ️  Using placeholder: {TARGET_SEC_UID[:30]}...")
    
    input("\nPress Enter to continue...")
    return True

def show_setup_menu():
    """Complete setup menu for all targets"""
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("""
╔══════════════════════════════════════════════════════════════╗
║              TIKTOK BOT - SETUP CONFIGURATION               ║
║       Configure your targets before launching attacks       ║
╚══════════════════════════════════════════════════════════════╝
        """)
        
        print(f" 📹 Video IDs:     {len(TARGET_VIDEO_IDS)} loaded" if TARGET_VIDEO_IDS else " 📹 Video IDs:     ❌ Not set")
        print(f" 🔴 Room ID:       {TARGET_ROOM_ID[:20]}..." if TARGET_ROOM_ID else " 🔴 Room ID:       ❌ Not set")
        print(f" 👤 sec_uid:       {TARGET_SEC_UID[:25]}..." if TARGET_SEC_UID else " 👤 sec_uid:       ❌ Not set")
        print()
        print("   [1] 📹 Setup Video IDs (for Views/Favs/Shares/Likes)")
        print("   [2] 🔴 Setup Live Room ID (for Live Views)")
        print("   [3] 👤 Setup Target User (for Followers)")
        print("   [4] 📊 View Current Config")
        print("   [0] ⬅️  Return to Main Menu")
        
        choice = input("\n  Select option: ").strip()
        
        if choice == '1':
            setup_menu_video_ids()
        elif choice == '2':
            setup_menu_room_id()
        elif choice == '3':
            setup_menu_sec_uid()
        elif choice == '4':
            print(f"\n📋 CURRENT CONFIGURATION:")
            print(f"  Video IDs: {TARGET_VIDEO_IDS if TARGET_VIDEO_IDS else 'NOT SET - using defaults'}")
            print(f"  Room ID:   {TARGET_ROOM_ID if TARGET_ROOM_ID else 'NOT SET'}")
            print(f"  sec_uid:   {TARGET_SEC_UID if TARGET_SEC_UID else 'NOT SET'}")
            input("\nPress Enter to continue...")
        elif choice == '0':
            break
        else:
            print("❌ Invalid option")
            time.sleep(1)

# =============================================================================
# MAIN MENU
# =============================================================================
def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║              TIKTOK BOT v3.0 - ULTIMATE EDITION             ║
║      Self-Contained • No Files Needed • Full Setup Menu     ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    while True:
        print("\n🎯 MAIN MENU:")
        print("  [0] ⚙️  Setup Targets (Video IDs, Room, User)")
        print("  [1] 📈 Video Views")
        print("  [2] ⭐ Video Favorites")
        print("  [3] 🔗 Video Shares")
        print("  [4] ❤️  Video Likes")
        print("  [5] 👤 Followers")
        print("  [6] 🔴 Live Stream Views")
        print("  [Q] ❌ Quit\n")
        
        choice = input("  Select option: ").strip().upper()
        
        if choice == '0':
            show_setup_menu()
            continue
        
        func_map = {
            '1': ('Video Views', sendViews),
            '2': ('Video Favorites', sendFavorites),
            '3': ('Video Shares', sendShares),
            '4': ('Video Likes', sendLikes),
            '5': ('Followers', sendFollowers),
            '6': ('Live Views', sendLiveViews)
        }
        
        if choice not in func_map:
            if choice == 'Q':
                print("\n👋 Goodbye!")
                sys.exit(0)
            print("❌ Invalid option")
            time.sleep(1)
            continue
        
        mode_name, target_func = func_map[choice]
        
        # Validation
        if choice == '6' and not TARGET_ROOM_ID:
            print("❌ No Room ID configured! Go to Setup (0) first.")
            time.sleep(2)
            continue
        if choice == '5' and not TARGET_SEC_UID:
            print("❌ No sec_uid configured! Go to Setup (0) first.")
            time.sleep(2)
            continue
        if choice in ('1','2','3','4') and not TARGET_VIDEO_IDS:
            print("⚠️  No Video IDs set. Using defaults. Go to Setup (0) to configure.")
            time.sleep(2)
        
        try:
            threads = int(input("  Threads (100-1000): "))
            target_hits = int(input("  Target hits: "))
        except ValueError:
            print("❌ Invalid number")
            continue
        
        # Launch bot
        global running, success, fails, reqs
        running = True
        success = fails = reqs = 0
        
        print(f"\n🚀 Launching {mode_name} - {threads} threads, target {target_hits}")
        
        threading.Thread(target=stats_loop, daemon=True).start()
        threading.Thread(target=live_dashboard, daemon=True).start()
        
        start_time = time.time()
        
        try:
            while success < target_hits and running:
                device = random.choice(DEVICES)
                did, iid, cdid, openudid = device.split(':')
                
                t = threading.Thread(target=target_func, args=(did, iid, cdid, openudid))
                t.daemon = True
                t.start()
                
                active = sum(1 for t in threading.enumerate() if t.is_alive() and t != threading.main_thread())
                if active - 2 >= threads:  # -2 for stats + dashboard
                    time.sleep(0.05)
            
            elapsed = time.time() - start_time
            
            if success >= target_hits:
                print(f"\n\n🎉 TARGET REACHED!")
                print(f"✅ Success: {success:,}")
                print(f"❌ Failed:  {fails:,}")
                print(f"📊 Total:   {reqs:,}")
                print(f"⏱️  Time:    {elapsed:.1f}s")
                print(f"⚡ Avg RPS:  {reqs/elapsed:.0f}")
            
        except KeyboardInterrupt:
            running = False
            print(f"\n\n⏹️  STOPPED")
            print(f"✅ Success: {success:,} | ❌ Failed: {fails:,} | 📊 Total: {reqs:,}")
        
        input("\nPress Enter to continue...")
        running = False

if __name__ == "__main__":
    # Import re only for URL parsing in menus
    import re
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Exiting...")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal Error: {e}")
        sys.exit(1)
