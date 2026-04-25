import requests
from urllib.parse import urlencode
import re
import time
import random
import string
import os
import uuid
import binascii
import SignerPy
from concurrent.futures import ThreadPoolExecutor

# ===== CONFIGURATION & BOT FARM =====
CONFIG = {
    "language": "en",
    "proxies": [],
    "target_room_id": "",
    "join_delay": 2,
    "active_bots": []  # Stores (session, params, username)
}

class TikTokBot:
    def __init__(self, session, params, username, device_id):
        self.session = session
        self.params = params
        self.username = username
        self.device_id = device_id

# ===== CORE UTILITIES =====

def get_random_proxy():
    if CONFIG["proxies"]:
        proxy = random.choice(CONFIG["proxies"])
        return {"http": proxy, "https": proxy}
    return None

def xor_encrypt(text: str, key: int = 5) -> str:
    return ''.join(hex(ord(c) ^ key)[2:] for c in text)

def generate_password(length=12):
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choice(chars) for _ in range(length))

def make_tiktok_params():
    di = str(random.randint(7000000000000000000, 7999999999999999999))
    return {
        "passport-sdk-version": "6031990",
        "device_platform": "android",
        "ssmix": "a",
        "aid": "1233",
        "app_name": "musical_ly",
        "device_brand": "OnePlus",
        "language": CONFIG["language"],
        "device_id": di,
        "iid": di,
        "openudid": binascii.hexlify(os.urandom(8)).decode(),
    }, di

# ===== API ACTIONS =====

def send_tiktok_code(session, email, params, password):
    url = "https://api16-normal-c-alisg.tiktokv.com/passport/email/send_code/"
    payload = {
        'rules_version': "v2", 'password': xor_encrypt(password),
        'type': "34", 'email': xor_encrypt(email),
    }        
    m = SignerPy.sign(params=params, payload=payload)
    headers = {'User-Agent': "TikTok 37.8.5 Android", 'X-Gorgon': m['x-gorgon'], 'X-Khronos': m['x-khronos']}
    session.proxies.update(get_random_proxy() or {})
    return session.post(url, params=params, data=payload, headers=headers).json()

def verify_and_register(session, email, code, params):
    url = "https://api16-normal-c-alisg.tiktokv.com/passport/email/register_verify_login/"
    payload = {'birthday': "1995-01-01", 'code': xor_encrypt(code), 'type': "34", 'email': xor_encrypt(email)}
    m = SignerPy.sign(params=params, payload=payload)
    headers = {'User-Agent': "TikTok 37.8.5 Android", 'X-Gorgon': m['x-gorgon']}
    return session.post(url, params=params, data=payload, headers=headers).json()

# ===== INTERACTION METHODS =====

def interact_enter(bot):
    url = "https://webcast16-normal-c-alisg.tiktokv.com/webcast/room/enter/"
    p = bot.params.copy()
    p.update({"room_id": CONFIG["target_room_id"], "enter_source": "live_cell"})
    m = SignerPy.sign(params=p, payload={})
    try:
        res = bot.session.get(url, params=p, headers={'X-Gorgon': m['x-gorgon']}).json()
        return res.get("status_code") == 0
    except: return False

def interact_like(bot):
    url = "https://webcast16-normal-c-alisg.tiktokv.com/webcast/room/like/"
    p = bot.params.copy()
    p.update({"room_id": CONFIG["target_room_id"], "count": "15"})
    m = SignerPy.sign(params=p, payload={})
    try:
        bot.session.post(url, params=p, headers={'X-Gorgon': m['x-gorgon']})
        print(f"[❤] {bot.username} sent likes!")
    except: pass

def interact_share(bot):
    url = "https://webcast16-normal-c-alisg.tiktokv.com/webcast/room/share/"
    p = bot.params.copy()
    p.update({"room_id": CONFIG["target_room_id"], "share_type": "1"})
    m = SignerPy.sign(params=p, payload={})
    try:
        bot.session.post(url, params=p, headers={'X-Gorgon': m['x-gorgon']})
        print(f"[↗] {bot.username} shared stream!")
    except: pass

# ===== MANAGEMENT INTERFACE =====

def bot_manager_loop():
    while True:
        print(f"\n--- BOT MANAGER (Active: {len(CONFIG['active_bots'])}) ---")
        print("1. Generate More Bots")
        print("2. Mass Enter Live")
        print("3. Mass Like (Boost Hearts)")
        print("4. Mass Share (Boost Algorithm)")
        print("5. Set Target Room ID")
        print("6. Exit")
        
        cmd = input("Command > ")
        
        if cmd == "1":
            amount = int(input("How many bots to create? "))
            generate_sequence(amount)
        elif cmd == "2":
            if not CONFIG["target_room_id"]: print("Set Room ID first!"); continue
            for bot in CONFIG["active_bots"]:
                success = interact_enter(bot)
                status = "Entered" if success else "Failed"
                print(f"[*] {bot.username}: {status}")
                time.sleep(CONFIG["join_delay"])
        elif cmd == "3":
            with ThreadPoolExecutor(max_workers=5) as executor:
                executor.map(interact_like, CONFIG["active_bots"])
        elif cmd == "4":
            with ThreadPoolExecutor(max_workers=5) as executor:
                executor.map(interact_share, CONFIG["active_bots"])
        elif cmd == "5":
            CONFIG["target_room_id"] = input("New Room ID: ")
        elif cmd == "6":
            break

def generate_sequence(count):
    for i in range(count):
        print(f"[*] Creating bot {i+1}/{count}...")
        try:
            # Temp Mail Logic (Simplified for brevity, use previous TM_CREATE_URL logic)
            # Assuming create_temp_email and fetch_code are available as per previous version
            email, _ = create_temp_email() 
            password = generate_password()
            session = requests.Session()
            params, device_id = make_tiktok_params()
            
            send_tiktok_code(session, email, params, password)
            code = fetch_code_from_email(email)
            
            if code:
                reg_res = verify_and_register(session, email, code, params)
                if reg_res.get("data", {}).get("session_key"):
                    user = reg_res["data"].get("name", f"Bot_{random.randint(100,999)}")
                    new_bot = TikTokBot(session, params, user, device_id)
                    CONFIG["active_bots"].append(new_bot)
                    print(f"[+] Bot Ready: {user}")
                else:
                    print(f"[-] Reg Failed: {reg_res.get('message')}")
        except Exception as e:
            print(f"[-] Error: {e}")

if __name__ == "__main__":
    # Load Proxies if available
    if os.path.exists("proxies.txt"):
        with open("proxies.txt", "r") as f:
            CONFIG["proxies"] = [l.strip() for l in f if l.strip()]
    
    bot_manager_loop()
