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

# ===== ORIGINAL SETTINGS (Aus deiner Acc3main.py) =====
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

def make_tiktok_params(reg_choice):
    # MCC Codes für die Auswahl
    mcc_map = {"1": "26201", "2": "310004", "3": "46692"}
    region_map = {"1": "DE", "2": "US", "3": "TW"}
    
    selected_region = region_map.get(reg_choice, "TW")
    selected_mcc = mcc_map.get(reg_choice, "46692")

    dd = str(random.randint(1, 10**19))
    # EXAKTE STRUKTUR deiner Acc3main.py
    return {
        "passport-sdk-version": "6031990",
        "device_platform": "android",
        "os": "android",
        "ssmix": "a",
        "_rticket": str(int(time.time() * 1000)),
        "cdid": "a90f0ed5-8028-413e-a00d-77e931779d00", # Deine Original-ID
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
        "current_region": selected_region,
        "app_type": "normal",
        "sys_region": "US",
        "last_install_time": "1752871588",
        "mcc_mnc": selected_mcc,
        "timezone_name": "Asia/Baghdad",
        "carrier_region_v2": selected_region,
        "residence": selected_region,
        "app_language": "en",
        "carrier_region": selected_region,
        "timezone_offset": "10800",
        "host_abi": "arm64-v8a",
        "locale": "en-GB",
        "ac2": "wifi",
        "uoo": "0",
        "op_region": selected_region,
        "build_number": "37.8.5",
        "region": "GB",
        "ts": str(int(time.time())),
        "iid": "7528525992324908807", # Deine Original-ID
        "device_id": "7528525775047132680", # Deine Original-ID
        "openudid": "7a59d727a58ee91e", # Deine Original-ID
        "support_webview": "1",
        "reg_store_region": selected_region.lower(),
        "user_selected_region": "0",
        "okhttp_version": "4.2.210.6-tiktok",
        "use_store_region_cookie": "1",
        "app_version": "37.8.5"
    }, "7528525775047132680"

# Hilfsfunktionen 1:1 übernommen
def xor_encrypt(text: str, key: int = 5) -> str:
    return ''.join(hex(ord(c) ^ key)[2:] for c in text)

def generate_password(length=12):
    if length < 8: length = 8
    password = [random.choice(string.ascii_lowercase), random.choice(string.ascii_uppercase), random.choice(string.digits), "_"]
    all_chars = string.ascii_letters + string.digits + "!@#$%^&*()-=+"
    password += [random.choice(all_chars) for _ in range(length - len(password))]
    random.shuffle(password)
    return ''.join(password)

def generate_birthdate(start_year: int = 1990, end_year: int = 2004) -> str:
    year = random.randint(start_year, end_year)
    month = random.randint(1, 12)
    day = random.randint(1, 28)
    return f"{year:04d}-{month:02d}-{day:02d}"

def create_temp_email() -> tuple[str, str]:
    payload = {"min_name_length": 10, "max_name_length": 10}
    resp = requests.post(TM_CREATE_URL, headers=TM_HEADERS, json=payload)
    data = resp.json()
    return data["email"], data["token"]

def fetch_code_from_email(email: str, timeout: int = 60) -> str | None:
    url = TM_MESSAGES_URL.format(email=email)
    for _ in range(timeout):
        resp = requests.get(url, headers=TM_HEADERS)
        for msg in resp.json():
            text = msg.get("subject", "") + "\n" + msg.get("body_text", "")
            m = re.search(r"\b\d{6}\b", text)
            if m: return m.group()
        time.sleep(1)
    return None

def send_tiktok_code(session, email, params, install_id, password):
    url = "https://api16-normal-c-alisg.tiktokv.com/passport/email/send_code/"
    cookies = {"install_id": install_id, "passport_csrf_token": "auto"}
    session.cookies.update(cookies)
    payload = {
        'rules_version': "v2",
        'password': xor_encrypt(password),
        'account_sdk_source': "app",
        'mix_mode': "1",
        'multi_login': "1",
        'type': "34",
        'email': xor_encrypt(email),
        'email_theme': "2"
    }        
    m = SignerPy.sign(params=params, payload=payload, cookie=cookies)
    headers = {
        'User-Agent': "com.zhiliaoapp.musically/2023708050 (Linux; U; Android 9; en_GB; NE2211; Build/SKQ1.220617.001;tt-ok/3.12.13.16)",
        'X-SS-STUB': m['x-ss-stub'],
        'X-SS-REQ-TICKET': m['x-ss-req-ticket'],
        'X-Ladon': m['x-ladon'],
        'X-Khronos': m['x-khronos'],
        'X-Argus': m['x-argus'],
        'X-Gorgon': m['x-gorgon'],
    }
    resp = session.post(url, params=params, data=payload, headers=headers)
    try: return resp.json()
    except: return None

def verify_tiktok_email(session, email, code, birthdate, params):
    url = "https://api16-normal-c-alisg.tiktokv.com/passport/email/register_verify_login/"
    payload = {
        'birthday': birthdate,
        'fixed_mix_mode': "1",
        'code': xor_encrypt(code),
        'account_sdk_source': "app",
        'mix_mode': "1",
        'multi_login': "1",
        'type': "34",
        'email': xor_encrypt(email),
    }
    m = SignerPy.sign(params=params, payload=payload)
    headers = {
        'User-Agent': "com.zhiliaoapp.musically/2023708050 (Linux; U; Android 9; en_GB; NE2211; Build/SKQ1.220617.001;tt-ok/3.12.13.16)",
        'X-SS-STUB': m['x-ss-stub'],
        'X-SS-REQ-TICKET':  m['x-ss-req-ticket'],
        'X-Ladon': m['x-ladon'],
        'X-Khronos': m['x-khronos'],
        'X-Argus': m['x-argus'],
        'X-Gorgon': m['x-gorgon'],
    }
    return session.post(url, params=params, data=payload, headers=headers)

# ===== MAIN PROGRAM =====
if __name__ == "__main__":
    print("-" * 30)
    print("1. DE | 2. US | 3. TW (Original)")
    print("-" * 30)
    reg_choice = input("Wähle Region: ")

    while True:
        try:
            email, tm_token = create_temp_email()
            password = generate_password(12)
            birthdate = generate_birthdate()
            session = requests.Session()
            params, install_id = make_tiktok_params(reg_choice)

            print(f"[*] Email: {email} | Sende Code...")
            resp_send = send_tiktok_code(session, email, params, install_id, password)
            
            if not resp_send or resp_send.get("message") == "error":
                print("[-] TikTok blockiert (error). Warte 5s...")
                time.sleep(5)
                continue

            code = fetch_code_from_email(email)
            if not code:
                print("[-] Kein Code.")
                continue

            print(f"[+] Code: {code} | Registriere...")
            response_obj = verify_tiktok_email(session, email, code, birthdate, params)
            resp_verify = response_obj.json()

            data = resp_verify.get("data", {})
            if data.get("session_key"):
                x_tt_token = data.get("token") or response_obj.headers.get("X-Tt-Token")        
                with open("accounts.txt", "a") as f:
                    f.write(f"{email}:{password}:{data.get('name')}\n")
                with open("session.txt", "a") as f:
                    f.write(f"{data.get('session_key')}:{x_tt_token}:{tm_token}\n")
                print(f"[+] Erfolg: {data.get('name')}")
            else:
                print(f"[-] Fehler: {resp_verify.get('message')}")
        except Exception as e:
            print(f"[-] Loop Fehler: {e}")
        time.sleep(2)
