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

# ===== CONFIGURATION & MENU =====
CONFIG = {
    "language": "en",
    "proxies": [],
    "target_room_id": "",
    "join_delay": 5  # Default seconds between joins
}

def show_menu():
    print("\n" + "="*30)
    print("   TIKTOK AUTOMATOR MENU")
    print("="*30)
    print(f"1. Set Language    (Current: {CONFIG['language']})")
    print(f"2. Load Proxies    (Loaded: {len(CONFIG['proxies'])})")
    print(f"3. Set Room ID     (Current: {CONFIG['target_room_id'] if CONFIG['target_room_id'] else 'None'})")
    print(f"4. Set Join Delay  (Current: {CONFIG['join_delay']}s)")
    print("5. START BOT")
    print("="*30)
    
    choice = input("Select an option: ")
    
    if choice == "1":
        CONFIG["language"] = input("Enter language code (en/ar/tr): ").strip()
        show_menu()
    elif choice == "2":
        if os.path.exists("proxies.txt"):
            with open("proxies.txt", "r") as f:
                CONFIG["proxies"] = [line.strip() for line in f if line.strip()]
            print(f"[+] Loaded {len(CONFIG['proxies'])} proxies.")
        else:
            print("[-] proxies.txt not found! Create it and add one proxy per line.")
        show_menu()
    elif choice == "3":
        CONFIG["target_room_id"] = input("Enter Numeric Room ID: ").strip()
        show_menu()
    elif choice == "4":
        try:
            CONFIG["join_delay"] = int(input("Enter delay in seconds between joins: "))
        except ValueError:
            print("[-] Invalid number.")
        show_menu()
    elif choice == "5":
        print("[+] Initializing bot sequence...")
    else:
        print("Invalid choice.")
        show_menu()

def get_random_proxy():
    if CONFIG["proxies"]:
        proxy = random.choice(CONFIG["proxies"])
        return {"http": proxy, "https": proxy}
    return None

# ===== TIKTOK API FUNCTIONS =====

TM_HEADERS = {
    "Application-Name": "web",
    "Application-Version": "4.0.0",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "*/*",
    "Origin": "https://temp-mail.io",
    "Referer": "https://temp-mail.io/",
    "X-Cors-Header": "iaWg3pchvFx48fY",
    "Content-Type": "application/json"
}
TM_CREATE_URL = "https://api.internal.temp-mail.io/api/v3/email/new"
TM_MESSAGES_URL = "https://api.internal.temp-mail.io/api/v3/email/{email}/messages"

def make_tiktok_params():
    dd = str(random.randint(1, 10**19))
    return {
        "passport-sdk-version": "6031990",
        "device_platform": "android",
        "os": "android",
        "ssmix": "a",
        "_rticket": str(int(time.time() * 1000)),
        "cdid": str(uuid.uuid4()),
        "channel": "googleplay",
        "aid": "1233",
        "app_name": "musical_ly",
        "version_code": "370805",
        "version_name": "37.8.5",
        "device_brand": "OnePlus",
        "language": CONFIG["language"],
        "app_language": CONFIG["language"],
        "locale": CONFIG["language"],
        "region": "US",
        "sys_region": "US",
        "timezone_name": "Asia/Baghdad",
        "residence": "US",
        "device_id": str(random.randint(7000000000000000000, 7999999999999999999)),
        "iid": str(random.randint(7000000000000000000, 7999999999999999999)),
        "openudid": binascii.hexlify(os.urandom(8)).decode(),
    }, dd

def xor_encrypt(text: str, key: int = 5) -> str:
    return ''.join(hex(ord(c) ^ key)[2:] for c in text)

def generate_password(length=12):
    password = [random.choice(string.ascii_lowercase), random.choice(string.ascii_uppercase), random.choice(string.digits), "_"]
    all_chars = string.ascii_letters + string.digits + "!@#$%^&*"
    password += [random.choice(all_chars) for _ in range(length - 4)]
    random.shuffle(password)
    return ''.join(password)

def generate_birthdate():
    return f"{random.randint(1990, 2004):04d}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"

def create_temp_email():
    payload = {"min_name_length": 10, "max_name_length": 10}
    resp = requests.post(TM_CREATE_URL, headers=TM_HEADERS, json=payload, proxies=get_random_proxy())
    resp.raise_for_status()
    data = resp.json()
    return data["email"], data["token"]

def fetch_code_from_email(email: str, timeout: int = 60):
    url = TM_MESSAGES_URL.format(email=email)
    for _ in range(timeout):
        try:
            resp = requests.get(url, headers=TM_HEADERS, proxies=get_random_proxy())
            for msg in resp.json():
                text = msg.get("subject", "") + "\n" + msg.get("body_text", "")
                m = re.search(r"\b\d{6}\b", text)
                if m: return m.group()
        except: pass
        time.sleep(1)
    return None

def send_tiktok_code(session, email, params, install_id, password):
    url = "https://api16-normal-c-alisg.tiktokv.com/passport/email/send_code/"
    session.cookies.update({"install_id": install_id, "passport_csrf_token": "auto"})
    payload = {
        'rules_version': "v2", 'password': xor_encrypt(password),
        'account_sdk_source': "app", 'mix_mode': "1", 'type': "34",
        'email': xor_encrypt(email), 'email_theme': "2"
    }        
    m = SignerPy.sign(params=params, payload=payload)
    headers = {
        'User-Agent': "com.zhiliaoapp.musically/2023708050 (Linux; U; Android 9; en_GB; NE2211)",
        'X-SS-STUB': m['x-ss-stub'], 'X-Khronos': m['x-khronos'],
        'X-Gorgon': m['x-gorgon'], 'X-Argus': m['x-argus']
    }
    session.proxies.update(get_random_proxy() or {})
    resp = session.post(url, params=params, data=payload, headers=headers)
    return resp.json()

def verify_tiktok_email(session, email, code, birthdate, params):
    url = "https://api16-normal-c-alisg.tiktokv.com/passport/email/register_verify_login/"
    payload = {
        'birthday': birthdate, 'code': xor_encrypt(code),
        'account_sdk_source': "app", 'mix_mode': "1",
        'type': "34", 'email': xor_encrypt(email),
    }
    m = SignerPy.sign(params=params, payload=payload)
    headers = {
        'User-Agent': "com.zhiliaoapp.musically/2023708050 (Linux; U; Android 9; en_GB; NE2211)",
        'X-SS-STUB': m['x-ss-stub'], 'X-Khronos': m['x-khronos'],
        'X-Gorgon': m['x-gorgon'], 'X-Argus': m['x-argus']
    }
    return session.post(url, params=params, data=payload, headers=headers)

def join_live_stream(session, room_id, device_params):
    url = "https://webcast16-normal-c-alisg.tiktokv.com/webcast/room/enter/"
    webcast_params = device_params.copy()
    webcast_params.update({"room_id": room_id, "enter_source": "live_cell", "enter_type": "click"})
    
    m = SignerPy.sign(params=webcast_params, payload={})
    headers = {'User-Agent': "com.zhiliaoapp.musically/2023708050", 'X-Gorgon': m['x-gorgon']}
    
    try:
        resp = session.get(url, params=webcast_params, headers=headers)
        return resp.json()
    except: return None

# ===== MAIN EXECUTION =====
if __name__ == "__main__":
    show_menu()
    
    while True:
        try:
            # 1. Create Email
            email, tm_token = create_temp_email()
            print(f"\n[+] Email: {email}")

            password = generate_password()
            birthdate = generate_birthdate()
            session = requests.Session()
            params, install_id = make_tiktok_params()

            # 2. Send Code
            print("[*] Sending code...")
            send_tiktok_code(session, email, params, install_id, password)

            # 3. Fetch Code
            code = fetch_code_from_email(email)
            if not code:
                print("[-] No code received.")
                continue
            print(f"[+] Code: {code}")

            # 4. Register
            response_obj = verify_tiktok_email(session, email, code, birthdate, params)
            resp_verify = response_obj.json()
            
            data = resp_verify.get("data", {})
            if data.get("session_key"):
                username = data.get("name", "Unknown")
                print(f"[+] Registration Success: {username}")
                
                with open("accounts.txt", "a") as f:
                    f.write(f"{email}:{password}:{username}\n")

                # 5. Live Entry with Delay
                if CONFIG["target_room_id"]:
                    print(f"[*] Waiting {CONFIG['join_delay']}s before joining live...")
                    time.sleep(CONFIG["join_delay"])
                    
                    join_res = join_live_stream(session, CONFIG["target_room_id"], params)
                    if join_res and join_res.get("status_code") == 0:
                        print(f"[SUCCESS] {username} is now in the live stream.")
                    else:
                        print(f"[FAILED] Could not enter room.")
            else:
                print(f"[-] Reg Error: {resp_verify.get('message')}")

        except Exception as e:
            print(f"[-] System Error: {e}")
        
        time.sleep(2)
