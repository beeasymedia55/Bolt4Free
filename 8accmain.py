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

# ===== إعدادات عامة (Original aus Acc3main) =====
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

# Diese Funktion nutzt DEINE originalen IDs, ändert aber die Region je nach Wahl
def make_tiktok_params(reg_choice):
    # DEINE originalen IDs aus Acc3main.py
    dd = "7528525775047132680" 
    iid = "7528525992324908807"
    cdid = "a90f0ed5-8028-413e-a00d-77e931779d00"
    
    # Regions-Logik
    region = "TW" # Default
    mcc = "46692"
    if reg_choice == "1": # DE
        region = "DE"
        mcc = "26201"
    elif reg_choice == "2": # US
        region = "US"
        mcc = "310004"
    elif reg_choice == "3": # TW
        region = "TW"
        mcc = "46692"

    return {
        "passport-sdk-version": "6031990",
        "device_platform": "android",
        "os": "android",
        "ssmix": "a",
        "_rticket": str(int(time.time() * 1000)), # Zeitstempel muss aktuell sein
        "cdid": cdid,
        "channel": "googleplay",
        "aid": "1233",
        "app_name": "musical_ly",
        "version_code": "370805",
        "version_name": "37.8.5",
        "manifest_version_code": "2023708050",
        "update_version_code": "2023708050",
        "ab_version": "37.8.5",
        "resolution": "900*1600",
        "dpi": "240",
        "device_type": "NE2211",
        "device_brand": "OnePlus",
        "language": "en",
        "os_api": "28",
        "os_version": "9",
        "ac": "wifi",
        "is_pad": "0",
        "current_region": region,
        "app_type": "normal",
        "sys_region": "US",
        "last_install_time": "1752871588",
        "mcc_mnc": mcc,
        "timezone_name": "Asia/Baghdad",
        "carrier_region_v2": region,
        "residence": region,
        "app_language": "en",
        "carrier_region": region,
        "timezone_offset": "10800",
        "host_abi": "arm64-v8a",
        "locale": "en-GB",
        "ac2": "wifi",
        "uoo": "0",
        "op_region": region,
        "build_number": "37.8.5",
        "region": "GB",
        "ts": str(int(time.time())),
        "iid": iid,
        "device_id": dd,
        "openudid": "7a59d727a58ee91e",
        "support_webview": "1",
        "reg_store_region": region.lower(),
        "user_selected_region": "0",
        "okhttp_version": "4.2.210.6-tiktok",
        "use_store_region_cookie": "1",
        "app_version": "37.8.5"
    }, dd

# --- Hilfsfunktionen 1:1 aus deinem Code ---
def xor_encrypt(text: str, key: int = 5) -> str:
    return ''.join(hex(ord(c) ^ key)[2:] for c in text)

def generate_password(length=12):
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choice(chars) for _ in range(length))

def generate_birthdate():
    return f"{random.randint(1990, 2004):04d}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"

def create_temp_email():
    payload = {"min_name_length": 10, "max_name_length": 10}
    resp = requests.post(TM_CREATE_URL, headers=TM_HEADERS, json=payload)
    return resp.json()["email"], resp.json()["token"]

def fetch_code_from_email(email, timeout=60):
    url = TM_MESSAGES_URL.format(email=email)
    for _ in range(timeout):
        try:
            resp = requests.get(url, headers=TM_HEADERS)
            for msg in resp.json():
                text = msg.get("subject", "") + "\n" + msg.get("body_text", "")
                m = re.search(r"\b\d{6}\b", text)
                if m: return m.group()
        except: pass
        time.sleep(1)
    return None

def send_tiktok_code(session, email, params, install_id, password):
    url = "https://api16-normal-c-alisg.tiktokv.com/passport/email/send_code/"
    cookies = {"install_id": install_id, "passport_csrf_token": "auto"}
    session.cookies.update(cookies)
    payload = {
        'rules_version': "v2", 'password': xor_encrypt(password),
        'type': "34", 'email': xor_encrypt(email),
    }        
    m = SignerPy.sign(params=params, payload=payload, cookie=cookies)
    headers = {
        'User-Agent': "com.zhiliaoapp.musically/2023708050 (Linux; U; Android 9; en_GB; NE2211)",
        'X-Gorgon': m['x-gorgon'], 'X-Khronos': m['x-khronos'],
        'X-Argus': m['x-argus'], 'X-Ladon': m['x-ladon']
    }
    resp = session.post(url, params=params, data=payload, headers=headers)
    try: return resp.json()
    except: return None

def verify_tiktok_email(session, email, code, birthdate, params):
    url = "https://api16-normal-c-alisg.tiktokv.com/passport/email/register_verify_login/"
    payload = {
        'birthday': birthdate, 'code': xor_encrypt(code),
        'type': "34", 'email': xor_encrypt(email),
    }
    m = SignerPy.sign(params=params, payload=payload)
    headers = {
        'User-Agent': "com.zhiliaoapp.musically/2023708050 (Linux; U; Android 9; en_GB; NE2211)",
        'X-Gorgon': m['x-gorgon'], 'X-Khronos': m['x-khronos'],
        'X-Argus': m['x-argus'], 'X-Ladon': m['x-ladon']
    }
    return session.post(url, params=params, data=payload, headers=headers)

# ===== MAIN LOOP =====
if __name__ == "__main__":
    print("1. DE | 2. US | 3. TW")
    choice = input("Wahl: ")
    
    while True:
        try:
            email, tm_token = create_temp_email()
            password = generate_password()
            birthdate = generate_birthdate()
            session = requests.Session()
            params, install_id = make_tiktok_params(choice)

            print(f"[*] Email: {email} | Region: {choice}")
            resp_send = send_tiktok_code(session, email, params, install_id, password)
            
            if not resp_send or resp_send.get("message") == "error":
                print("[-] Fehler: TikTok blockt. Warte 10s...")
                time.sleep(10); continue

            code = fetch_code_from_email(email)
            if code:
                print(f"[+] Code: {code}")
                response_obj = verify_tiktok_email(session, email, code, birthdate, params)
                resp_verify = response_obj.json()
                
                data = resp_verify.get("data", {})
                if data.get("session_key"):
                    with open("accounts.txt", "a") as f:
                        f.write(f"{email}:{password}:{data.get('name')}\n")
                    print("[+] Gespeichert!")
        except Exception as e:
            print(f"Error: {e}")
        time.sleep(2)
