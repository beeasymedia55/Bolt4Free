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

# ===== إعدادات عامة =====
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
    "_rticket": "1752875703408",
    "cdid": "a90f0ed5-8028-413e-a00d-77e931779d00",
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
    "current_region": "DE",
    "app_type": "normal",
    "sys_region": "US",
    "last_install_time": "1752871588",
    "mcc_mnc": "46692",
    "timezone_name": "Asia/Baghdad",
    "carrier_region_v2": "DE",
    "residence": "DE",
    "app_language": "en",
    "carrier_region": "DE",
    "timezone_offset": "10800",
    "host_abi": "arm64-v8a",
    "locale": "en-GB",
    "ac2": "wifi",
    "uoo": "0",
    "op_region": "DE",
    "build_number": "37.8.5",
    "region": "GB",
    "ts": "1752875702",
    "iid": "7528525992324908807",
    "device_id": "7528525775047132680",
    "openudid": "7a59d727a58ee91e",
    "support_webview": "1",
    "reg_store_region": "de",
    "user_selected_region": "0",
    "okhttp_version": "4.2.210.6-tiktok",
    "use_store_region_cookie": "1",
    "app_version":"37.8.5"
    }, dd

def xor_encrypt(text: str, key: int = 5) -> str:
    return ''.join(hex(ord(c) ^ key)[2:] for c in text)

def generate_password(length=12):
    if length < 8:
        length = 8
    password = [
        random.choice(string.ascii_lowercase),
        random.choice(string.ascii_uppercase),
        random.choice(string.digits),
        "_"
    ]
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
    resp.raise_for_status()
    data = resp.json()
    return data["email"], data["token"]

def fetch_code_from_email(email: str, timeout: int = 60) -> str | None:
    url = TM_MESSAGES_URL.format(email=email)
    for _ in range(timeout):
        resp = requests.get(url, headers=TM_HEADERS)
        resp.raise_for_status()
        for msg in resp.json():
            text = msg.get("subject", "") + "\n" + msg.get("body_text", "")
            m = re.search(r"\b\d{6}\b", text)
            if m:
                return m.group()
        time.sleep(1)
    return None

def send_tiktok_code(session: requests.Session, email: str, params: dict, install_id: str, password: str) -> dict:
    url = "https://api16-normal-c-alisg.tiktokv.com/passport/email/send_code/"
    cookies = {
        "install_id": install_id,
        "passport_csrf_token": "auto",
        "passport_csrf_token_default": "auto",
    }
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
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'X-SS-STUB': m['x-ss-stub'],
        'x-tt-pba-enable': "1",
        'x-bd-kmsv': "0",
        'x-tt-dm-status': "login=1;ct=1;rt=8",
        'X-SS-REQ-TICKET': m['x-ss-req-ticket'],
        'x-bd-client-key': "#yEjw14J8W9l4SfT9U1TO60CXVvhTKWlciV4wIs/yJvoJp9e6R85bFU+QLZlj2NzfUISVioYXoQrs9gx6",
        'x-tt-passport-csrf-token': "13e1ddab691a6a5ed7cd70592d960fe7",
        'tt-ticket-guard-public-key': "BHxT6qq83FTRAnJYjUgFDzwxX14GDgGVWmXnZftx8oJntWW03KYyAqdengSdAMgufFURdqiqF23x6RFV+F4593I=",
        'sdk-version': "2",
        'tt-ticket-guard-iteration-version': "0",
        'tt-ticket-guard-client-data': "eyJyZXFfY29udGVudCI6InRpY2tldCxwYXRoLHRpbWVzdGFtcCIsInJlcV9zaWduIjoiTUVZQ0lRRExiZVFWOHVVUFlYaGRPWHpseEJ2VG5YdUtXUisxQm9WVmtYdW1oa1lQbEFJaEFNdjlNeEdadlR4d3ovc2lrQUNWaFZlSmRHm1wcTR2QkFGMm5nS0JybW1SIiwidGltZXN0YW1wIjoxNzUyODc1NzAxLCJ0c19zaWduIjoidHMuMS4zNWJlNDgzYzc5NGYxMzkyMjA1NTZlODFiMTdkY2UxYzlkZjBjODQ0OGYwYzVjMmY0NmRkMjZjZjdmODU5ODkyMGU3MGI0YmRhODJjMTM4MzZlNWNmYTE4Mzk0ZDcwMjQwZjhhZjE2MzFmMTY1YWU5NjAxMjJlZWZmZDQ1MzNkZCJ9",
        'tt-ticket-guard-version': "3",
        'passport-sdk-settings': "x-tt-token",
        'passport-sdk-sign': "x-tt-token",
        'passport-sdk-version': "6031990",
        'x-tt-bypass-dp': "1",
        'oec-vc-sdk-version': "3.0.5.i18n",
        'x-vc-bdturing-sdk-version': "2.3.8.i18n",
        'x-tt-request-tag': "n=0;nr=011;bg=0",
        'X-Ladon': m['x-ladon'],
        'X-Khronos': m['x-khronos'],
        'X-Argus': m['x-argus'],
        'X-Gorgon': m['x-gorgon'],
    }
    resp = session.post(url, params=params, data=payload, headers=headers)
    return resp.json()

def verify_tiktok_email(session: requests.Session, email: str, code: str, birthdate: str):
    url = "https://api16-normal-c-alisg.tiktokv.com/passport/email/register_verify_login/"
    params = {
        "passport-sdk-version": "6031990",
        "device_platform": "android",
        "os": "android",
        "ssmix": "a",
        "_rticket": "1752875715998",
        "cdid": "a90f0ed5-8028-413e-a00d-77e931779d00",
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
        "current_region": "DE",
        "app_type": "normal",
        "sys_region": "US",
        "last_install_time": "1752871588",
        "mcc_mnc": "46692",
        "timezone_name": "Asia/Baghdad",
        "carrier_region_v2": "DE",
        "residence": "DE",
        "app_language": "en",
        "carrier_region": "DE",
        "timezone_offset": "10800",
        "host_abi": "arm64-v8a",
        "locale": "en-GB",
        "ac2": "wifi",
        "uoo": "0",
        "op_region": "DE",
        "build_number": "37.8.5",
        "region": "GB",
        "ts": "1752875714",
        "iid": "7528525992324908807",
        "device_id": "7528525775047132680",
        "openudid": "7a59d727a58ee91e",
        "support_webview": "1",
        "reg_store_region": "de",
        "user_selected_region": "0",
        "okhttp_version": "4.2.210.6-tiktok",
        "use_store_region_cookie": "1",
        "app_version":"37.8.5"
    }
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
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'X-SS-STUB': m['x-ss-stub'],
        'x-tt-pba-enable': "1",
        'x-bd-kmsv': "0",
        'x-tt-dm-status': "login=1;ct=1;rt=8",
        'X-SS-REQ-TICKET':  m['x-ss-req-ticket'],
        'x-bd-client-key': "#yEjw14J8W9l4SfT9U1TO60CXVvhTKWlciV4wIs/yJvoJp9e6R85bFU+QLZlj2NzfUISVioYXoQrs9gx6",
        'x-tt-passport-csrf-token': "13e1ddab691a6a5ed7cd70592d960fe7",
        'tt-ticket-guard-public-key': "BHxT6qq83FTRAnJYjUgFDzwxX14GDgGVWmXnZftx8oJntWW03KYyAqdengSdAMgufFURdqiqF23x6RFV+F4593I=",
        'sdk-version': "2",
        'tt-ticket-guard-iteration-version': "0",
        'X-Tt-Token': "0370c890e123ee06efe9bfd83298e202d701f5742061f9f4abf220abb27fdc3f7d8a2389a8db93c3ea4e1a4e24cdf19e194ed15acffd5e582ca1177dc53e71281973c50f7f5a498c43e00a210bb650575fb5c2488922fbbc51cdb25cdb4b960d90767--0a4e0a2088aefe8e956071b58d7e88474a1b08e4021225bcf93fb9044dc0b2164e4680d71220e811fecf461dd5e810309dae1c0fa532912e69b7449d6ce777d95fe44c8dc8b41801220674696b746f6b-3.0.0",
        'tt-ticket-guard-version': "3",
        'passport-sdk-settings': "x-tt-token",
        'passport-sdk-sign': "x-tt-token",
        'passport-sdk-version': "6031990",
        'x-tt-bypass-dp': "1",
        'oec-vc-sdk-version': "3.0.5.i18n",
        'x-vc-bdturing-sdk-version': "2.3.8.i18n",
        'x-tt-request-tag': "n=0;nr=011;bg=0",
        'X-Ladon': m['x-ladon'],
        'X-Khronos': m['x-khronos'],
        'X-Argus': m['x-argus'],
        'X-Gorgon': m['x-gorgon'],
    }
    resp = session.post(url, params=params, data=payload, headers=headers)
    # Return the whole response object so we can get data and headers
    return resp

# ===== التدفق الرئيسي =====
if __name__ == "__main__":
    while True:
        # 1) إنشاء بريد مؤقت
        email, tm_token = create_temp_email()
        print(f"[+] Temporary email: {email}")

        # 2) توليد كلمة مرور وتاريخ ميلاد
        password = generate_password(12)
        birthdate = generate_birthdate()
        print(f"[+] Generated password: {password}")
        print(f"[+] Generated birthdate: {birthdate}")

        # 3) إرسال طلب رمز تيكـتوك
        session = requests.Session()
        params, install_id = make_tiktok_params()
        print("[*] Sending TikTok verification code...")
        resp_send = send_tiktok_code(session, email, params, install_id, password)
        if not resp_send:
            print("[-] Empty response from send_code. Skipping...")
            continue
        print(f"[+] send_code response: {resp_send}")

        # 4) الانتظار وجلب رمز التحقق من البريد
        print("[*] Waiting for email code...")
        code = fetch_code_from_email(email, timeout=10)
        if not code:
            print("[-] Failed to retrieve code from email. Skipping...")
            continue
        print(f"[+] Received code: {code}")

        # 5) التحقق وتسجيل الحساب
        print("[*] Verifying and registering...")
        # Now receiving the response object
        response_obj = verify_tiktok_email(session, email, code, birthdate)
        
        if not response_obj:
            print("[-] Empty response from verify. Skipping...")
            continue
            
        resp_verify = response_obj.json()
        print(f"[+] verify response: {resp_verify}")

        # 6) حفظ معلومات الحساب في ملف
        data = resp_verify.get("data", {})
        session_key = data.get("session_key")
        
        # Pulling token from JSON or the response headers
        x_tt_token = data.get("token") or response_obj.headers.get("X-Tt-Token")        
        username = data.get("name")
        
        if session_key:
            with open("accounts.txt", "a") as f:
                f.write(f"{email}:{password}:{username}\n")
            with open("session.txt", "a") as f:
                # Corrected: using variable x_tt_token (with underscore)
                f.write(f"{session_key}:{x_tt_token}:{tm_token}\n")
            print(f"[+] Success! Account saved: {username}")
        else:
            print("[-] Registration failed or blocked by IP.")
            print(f"Error Message: {resp_verify.get('message', 'No message')}")
        
        # Avoid rapid looping
        time.sleep(2)
