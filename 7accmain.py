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
import json

# ===== GLOBAL SETTINGS =====
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

# Regionale Konfigurationen - Optimiert für Stabilität
REGION_CONFIG = {
    "1": {"name": "Deutschland", "cc": "DE", "tz": "Europe/Berlin", "lang": "de", "mcc": "26201", "offset": "7200", "locale": "de-DE"},
    "2": {"name": "USA", "cc": "US", "tz": "America/New_York", "lang": "en", "mcc": "310004", "offset": "-14400", "locale": "en-US"},
    "3": {"name": "Taiwan", "cc": "TW", "tz": "Asia/Taipei", "lang": "zh-Hant", "mcc": "46692", "offset": "28800", "locale": "zh-TW"}
}

def make_tiktok_params(selected_region):
    conf = REGION_CONFIG[selected_region]
    dd = str(random.randint(1, 10**19))
    # Wir nutzen die Struktur, die bei TW funktioniert hat, und tauschen nur die Regionalwerte
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
        "manifest_version_code": "2023708050",
        "update_version_code": "2023708050",
        "ab_version": "37.8.5",
        "resolution": "1080*1920",
        "dpi": "420",
        "device_type": "NE2211",
        "device_brand": "OnePlus",
        "language": conf["lang"],
        "os_api": "28",
        "os_version": "9",
        "ac": "wifi",
        "is_pad": "0",
        "current_region": conf["cc"],
        "app_type": "normal",
        "sys_region": conf["cc"],
        "last_install_time": str(int(time.time()) - 3600),
        "mcc_mnc": conf["mcc"],
        "timezone_name": conf["tz"],
        "carrier_region_v2": conf["cc"],
        "residence": conf["cc"],
        "app_language": conf["lang"],
        "carrier_region": conf["cc"],
        "timezone_offset": conf["offset"],
        "host_abi": "arm64-v8a",
        "locale": conf["locale"],
        "ac2": "wifi",
        "uoo": "0",
        "op_region": conf["cc"],
        "build_number": "37.8.5",
        "region": conf["cc"],
        "ts": str(int(time.time())),
        "iid": str(random.randint(7000000000000000000, 7999999999999999999)),
        "device_id": str(random.randint(7000000000000000000, 7999999999999999999)),
        "openudid": binascii.hexlify(os.urandom(8)).decode(),
        "support_webview": "1",
        "reg_store_region": conf["cc"].lower(),
        "user_selected_region": "0",
        "okhttp_version": "4.2.210.6-tiktok",
        "use_store_region_cookie": "1",
        "app_version": "37.8.5"
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
    try:
        payload = {"min_name_length": 10, "max_name_length": 10}
        resp = requests.post(TM_CREATE_URL, headers=TM_HEADERS, json=payload, timeout=10)
        return resp.json()["email"], resp.json()["token"]
    except:
        return None, None

def fetch_code_from_email(email, timeout=60):
    url = TM_MESSAGES_URL.format(email=email)
    for _ in range(timeout):
        try:
            resp = requests.get(url, headers=TM_HEADERS, timeout=10)
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
        'account_sdk_source': "app", 'mix_mode': "1", 'type': "34",
        'email': xor_encrypt(email), 'email_theme': "2"
    }        
    m = SignerPy.sign(params=params, payload=payload, cookie=cookies)
    headers = {
        'User-Agent': "com.zhiliaoapp.musically/2023708050 (Linux; U; Android 9; en_GB; NE2211)",
        'X-SS-STUB': m['x-ss-stub'], 'X-Khronos': m['x-khronos'],
        'X-Argus': m['x-argus'], 'X-Gorgon': m['x-gorgon'], 'X-Ladon': m['x-ladon']
    }
    try:
        resp = session.post(url, params=params, data=payload, headers=headers, timeout=15)
        return resp.json()
    except:
        return None

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
        'X-Argus': m['x-argus'], 'X-Gorgon': m['x-gorgon'], 'X-Ladon': m['x-ladon']
    }
    try:
        return session.post(url, params=params, data=payload, headers=headers, timeout=15)
    except:
        return None

if __name__ == "__main__":
    os.system('clear')
    print("="*40)
    print("   TIKTOK MULTI-REGION GENERATOR")
    print("="*40)
    print(" [1] DEUTSCHLAND (DE)")
    print(" [2] USA (US)")
    print(" [3] TAIWAN (TW) - Empfohlen")
    print("="*40)
    choice = input(" Wähle Region: ").strip()

    if choice not in REGION_CONFIG:
        print(" Ungültig!")
        exit()

    print(f"\n[*] Modus: {REGION_CONFIG[choice]['name']} aktiv.")

    while True:
        try:
            email, tm_token = create_temp_email()
            if not email:
                print("[-] Fehler beim Erstellen der Mail. Retry...")
                time.sleep(2); continue
                
            print(f"\n[+] Mail: {email}")

            password = generate_password()
            birthdate = generate_birthdate()
            session = requests.Session()
            params, install_id = make_tiktok_params(choice)

            print("[*] Sende Verification Code...")
            resp_send = send_tiktok_code(session, email, params, install_id, password)
            
            if not resp_send or resp_send.get("message") == "error":
                print("[-] TikTok blockiert die Anfrage. IP wechseln oder 10s warten...")
                time.sleep(10); continue

            code = fetch_code_from_email(email, timeout=20)
            if not code:
                print("[-] Kein Code erhalten.")
                continue

            print(f"[+] Code gefunden: {code}")
            response_obj = verify_tiktok_email(session, email, code, birthdate, params)
            
            if response_obj and response_obj.status_code == 200:
                resp_verify = response_obj.json()
                data = resp_verify.get("data", {})
                session_key = data.get("session_key")
                x_tt_token = data.get("token") or response_obj.headers.get("X-Tt-Token")
                
                if session_key:
                    with open("accounts.txt", "a") as f:
                        f.write(f"{email}:{password}:{data.get('name')}\n")
                    with open("session.txt", "a") as f:
                        f.write(f"{session_key}:{x_tt_token}:{tm_token}\n")
                    print(f"[SUCCESS] Bot erstellt für {REGION_CONFIG[choice]['cc']}!")
                else:
                    print(f"[-] Fehler: {resp_verify.get('message')}")
            else:
                print("[-] Verifizierung fehlgeschlagen (Bad Request).")

        except Exception as e:
            print(f"[-] Fehler im Loop: {e}")
        
        time.sleep(2)
