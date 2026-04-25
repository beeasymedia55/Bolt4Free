import requests
import time
import random
import os
import uuid
import binascii
import SignerPy
import json
from concurrent.futures import ThreadPoolExecutor

# ===== CONFIGURATION =====
CONFIG = {
    "proxies": [],
    "target_room_id": "",
    "join_delay": 2,
    "bot_farm": [] 
}

class TikTokBot:
    def __init__(self, email, password, username, session_key, tt_token, device_id):
        self.email = email
        self.password = password
        self.username = username
        self.session_key = session_key
        self.tt_token = tt_token
        self.device_id = device_id
        
        # Initialize specialized session
        self.session = requests.Session()
        self.session.cookies.set("sessionid", session_key, domain=".tiktok.com")
        
        # KEY FIX: All values MUST be in lists [value] to satisfy SignerPy's internal index [0] calls
        self.params = {
            "device_id": [str(device_id)],
            "iid": [str(device_id)],
            "device_platform": ["android"],
            "aid": ["1233"],
            "app_name": ["musical_ly"],
            "version_code": ["370805"],
            "version_name": ["37.8.5"],
            "os_version": ["9"],
            "device_brand": ["OnePlus"],
            "device_type": ["NE2211"],
            "language": ["en"],
            "sdk_version": ["2"],
            "openudid": [binascii.hexlify(os.urandom(8)).decode()],
        }

# ===== LOAD DATA FROM FILES =====

def load_bots():
    CONFIG["bot_farm"] = []
    if not os.path.exists("accounts.txt") or not os.path.exists("session.txt"):
        print("[-] Error: accounts.txt or session.txt missing!")
        return

    try:
        with open("accounts.txt", "r") as f:
            acc_lines = f.readlines()
        with open("session.txt", "r") as f:
            sess_lines = f.readlines()
            
        for a_line, s_line in zip(acc_lines, sess_lines):
            acc_data = a_line.strip().split(":")
            sess_data = s_line.strip().split(":")
            
            if len(acc_data) >= 3 and len(sess_data) >= 2:
                dev_id = str(random.randint(7000000000000000000, 7999999999999999999))
                bot = TikTokBot(
                    email=acc_data[0],
                    password=acc_data[1],
                    username=acc_data[2],
                    session_key=sess_data[0],
                    tt_token=sess_data[1],
                    device_id=dev_id
                )
                CONFIG["bot_farm"].append(bot)
        
        print(f"[+] Successfully loaded {len(CONFIG['bot_farm'])} bots.")
    except Exception as e:
        print(f"[-] Error loading files: {e}")

def get_proxy():
    if CONFIG["proxies"]:
        p = random.choice(CONFIG["proxies"])
        return {"http": p, "https": p}
    return None

# ===== ENDPOINTS & INTERACTIONS =====

def webcast_enter(bot):
    url = "https://webcast16-normal-c-alisg.tiktokv.com/webcast/room/enter/"
    params = bot.params.copy()
    params.update({
        "room_id": [str(CONFIG["target_room_id"])],
        "enter_source": ["live_cell"],
        "enter_type": ["click"]
    })
    
    # payload must be a string '{}', not a dict {}
    m = SignerPy.sign(params=params, payload='{}')
    headers = {
        'User-Agent': "com.zhiliaoapp.musically/2023708050 (Linux; U; Android 9; en_GB; NE2211)",
        'X-Gorgon': m['x-gorgon'],
        'X-Khronos': m['x-khronos'],
        'X-Argus': m['x-argus'],
        'X-Ladon': m['x-ladon'],
        'X-Tt-Token': bot.tt_token
    }
    try:
        bot.session.proxies = get_proxy() or {}
        res = bot.session.get(url, params=params, headers=headers).json()
        return res.get("status_code") == 0
    except: return False

def webcast_like(bot):
    url = "https://webcast16-normal-c-alisg.tiktokv.com/webcast/room/like/"
    params = bot.params.copy()
    params.update({
        "room_id": [str(CONFIG["target_room_id"])],
        "count": ["15"]
    })
    
    m = SignerPy.sign(params=params, payload='{}')
    headers = {
        'User-Agent': "com.zhiliaoapp.musically/2023708050 (Linux; U; Android 9; en_GB; NE2211)",
        'X-Gorgon': m['x-gorgon'], 
        'X-Argus': m['x-argus'],
        'X-Tt-Token': bot.tt_token
    }
    try:
        bot.session.post(url, params=params, headers=headers)
        print(f"[❤] {bot.username} liked.")
    except: pass

def webcast_share(bot):
    url = "https://webcast16-normal-c-alisg.tiktokv.com/webcast/room/share/"
    params = bot.params.copy()
    params.update({
        "room_id": [str(CONFIG["target_room_id"])],
        "share_type": ["1"]
    })
    
    m = SignerPy.sign(params=params, payload='{}')
    headers = {
        'User-Agent': "com.zhiliaoapp.musically/2023708050 (Linux; U; Android 9; en_GB; NE2211)",
        'X-Gorgon': m['x-gorgon'], 
        'X-Argus': m['x-argus'],
        'X-Tt-Token': bot.tt_token
    }
    try:
        bot.session.post(url, params=params, headers=headers)
        print(f"[↗] {bot.username} shared.")
    except: pass

# ===== FULL MANAGEMENT INTERFACE =====

def main_menu():
    while True:
        print("\n" + "="*40)
        print(f"   TIKTOK LIVE BOT MANAGER | BOTS: {len(CONFIG['bot_farm'])}")
        print("="*40)
        print(f"TARGET: {CONFIG['target_room_id'] if CONFIG['target_room_id'] else 'NOT SET'}")
        print("-" * 40)
        print("1. Load/Refresh Bots from Files")
        print("2. Set Target Room ID")
        print("3. Mass Enter (Viewers)")
        print("4. Mass Like (Hearts)")
        print("5. Mass Share (Algorithm)")
        print("6. Auto-Nuke (Enter + Like + Share)")
        print("7. Exit")
        print("="*40)
        
        cmd = input("Command > ")
        
        if cmd == "1":
            load_bots()
        elif cmd == "2":
            CONFIG["target_room_id"] = input("Enter Room ID: ").strip()
        elif cmd == "3":
            if not CONFIG["target_room_id"]: 
                print("[-] Set Room ID first!"); continue
            for bot in CONFIG["bot_farm"]:
                success = webcast_enter(bot)
                print(f"[>] {bot.username}: {'Entered' if success else 'Failed'}")
                time.sleep(CONFIG["join_delay"])
        elif cmd == "4":
            with ThreadPoolExecutor(max_workers=10) as executor:
                executor.map(webcast_like, CONFIG["bot_farm"])
        elif cmd == "5":
            with ThreadPoolExecutor(max_workers=10) as executor:
                executor.map(webcast_share, CONFIG["bot_farm"])
        elif cmd == "6":
            if not CONFIG["target_room_id"]: 
                print("[-] Set Room ID first!"); continue
            print("[*] Running Full Interaction Cycle...")
            for bot in CONFIG["bot_farm"]:
                webcast_enter(bot)
                time.sleep(0.5)
            with ThreadPoolExecutor(max_workers=10) as executor:
                executor.map(webcast_like, CONFIG["bot_farm"])
                executor.map(webcast_share, CONFIG["bot_farm"])
        elif cmd == "7":
            break

if __name__ == "__main__":
    if os.path.exists("proxies.txt"):
        with open("proxies.txt", "r") as f:
            CONFIG["proxies"] = [l.strip() for l in f if l.strip()]
            
    main_menu()
