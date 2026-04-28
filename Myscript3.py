import hashlib
import json
import os
import random
import re
import ssl
import threading
import time
from copy import deepcopy
from urllib.parse import quote, urlencode

import requests
from colorama import Fore, init
from pystyle import Colorate, Colors, Center
from urllib3.exceptions import InsecureRequestWarning

init(autoreset=True)

# --- Initialisierung & Bypass ---
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context

_lock = threading.Lock()
success, fails = 0, 0

# --- X-GORGON ENGINE (Optimiert) ---
class XGorgon:
    def __init__(self):
        self.length = 0x14
        self.hex_str = [0x05, 0x00, 0x50, 0x0c, 0x47, 0x1e, 0x00, 0x8a]

    def __encryption(self):
        tmp = ''; hex_zu = []
        for i in range(256): hex_zu.append(i)
        for i in range(256):
            if i == 0: A = 0
            elif tmp: A = tmp
            else: A = hex_zu[i - 1]
            B = self.hex_str[i % 8]
            if A == 85 and i != 1:
                if tmp != 85: A = 0
            C = (A + i + B) % 256
            if C < i: tmp = C
            else: tmp = ''
            D = hex_zu[C]
            hex_zu[i] = D
        return hex_zu

    def __initialize(self, input, hex_zu):
        tmp_add = []
        for i in range(self.length):
            A = input[i]
            B = 0 if not tmp_add else tmp_add[-1]
            C = (hex_zu[i + 1] + B) % 256
            tmp_add.append(C)
            input[i] = hex_zu[(A + hex_zu[C]) % 256]
        return input

    def calculate(self, params: str, stub: str = None, cookie: str = None):
        gorgon = []
        url_md5 = hashlib.md5(params.encode("utf-8")).hexdigest()
        for i in range(4): gorgon.append(int(url_md5[2*i : 2*i+2], 16))
        
        if stub:
            for i in range(4): gorgon.append(int(stub[2*i : 2*i+2], 16))
        else:
            for i in range(4): gorgon.append(0)
            
        if cookie:
            c_md5 = hashlib.md5(cookie.encode("utf-8")).hexdigest()
            for i in range(4): gorgon.append(int(c_md5[2*i : 2*i+2], 16))
        else:
            for i in range(4): gorgon.append(0)
            
        for i in range(4): gorgon.append(0)
        
        hex_zu = self.__encryption()
        gorgon = self.__initialize(gorgon, hex_zu)
        
        res = "030000000000"
        for i in range(self.length):
            tmp = hex(gorgon[i])[2:]
            res += tmp if len(tmp) == 2 else '0' + tmp
        return res

# --- CORE FUNCTIONS ---
def Banner():
    os.system('cls' if os.name == 'nt' else 'clear')
    banner = r"""
██████╗ ██████╗  ██████╗ ███╗   ██╗███████╗███╗   ███╗ ██████╗ ██████╗ 
██╔══██╗██╔══██╗██╔═══██╗████╗  ██║██╔════╝████╗ ████║██╔═══██╗██╔══██╗
██████╔╝██████╔╝██║   ██║██╔██╗ ██║███████╗██╔████╔██║██║   ██║██║  ██║
██╔═══╝ ██╔══██╗██║   ██║██║╚██╗██║╚════██║██║╚██╔╝██║██║   ██║██║  ██║
██║     ██║  ██║╚██████╔╝██║ ╚████║███████║██║ ╚═╝ ██║╚██████╔╝██████╔╝
╚═╝     ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝╚══════╝╚═╝     ╚═╝ ╚═════╝ ╚═════╝ 
    """
    print(Center.XCenter(Colorate.Vertical(Colors.blue_to_cyan, banner, 2)))

def get_room_id(target):
    # Wenn target nur aus Zahlen besteht, ist es direkt die ID
    if target.isdigit():
        return target
    
    # Ansonsten Username grabben
    username = target.replace('@', '')
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get(f"https://www.tiktok.com/@{username}/live", headers=headers, timeout=10)
        rid = re.search(r'room_id=(\d+)', r.text) or re.search(r'"roomId":"(\d+)"', r.text)
        if rid:
            return rid.group(1)
    except: pass
    return None

def get_proxies():
    # Beispiel-Liste (Nutzt deine Liste aus der Konversation)
    __raw = [
        "31.59.20.176:6754:hxidjrjw:nylyfhelpvdx", "198.23.239.134:6540:hxidjrjw:nylyfhelpvdx",
        "45.38.107.97:6014:hxidjrjw:nylyfhelpvdx", "107.172.163.27:6543:hxidjrjw:nylyfhelpvdx"
    ]
    return [{"http": f"http://{p.split(':')[2]}:{p.split(':')[3]}@{p.split(':')[0]}:{p.split(':')[1]}",
             "https": f"http://{p.split(':')[2]}:{p.split(':')[3]}@{p.split(':')[0]}:{p.split(':')[1]}"} for p in __raw]

xg = XGorgon()

def run_task(action, room_id, did, iid, cdid, udid, use_proxy, use_accounts):
    global success, fails
    prox_list = get_proxies() if use_proxy else None
    
    while True:
        try:
            cookie = ""
            if use_accounts:
                file_name = "sessions.txt" if os.path.exists("sessions.txt") else "accounts.txt"
                if os.path.exists(file_name):
                    sess = random.choice(open(file_name).read().splitlines())
                    cookie = f"sessionid={sess}"

            params = urlencode({
                "room_id": room_id, "device_id": did, "install_id": iid,
                "aid": "1988", "device_platform": "android", "app_name": "tiktok_web",
                "version_code": "300303", "device_type": "Pixel 7"
            })

            if action == "like":
                uri, payload = "/webcast/room/like/?", f"room_id={room_id}&count={random.randint(30, 80)}&basis=1"
            else:
                uri, payload = "/webcast/room/enter/?", f"room_id={room_id}&hold_living_room=1&is_login=1"

            stub = hashlib.md5(payload.encode()).hexdigest()
            ts = str(int(time.time()))
            gorgon = xg.calculate(params, stub, cookie)
            
            headers = {
                "User-Agent": "com.ss.android.ugc.trill/300303 (Linux; U; Android 13; de_DE; Pixel 7)",
                "X-Gorgon": gorgon, "X-Khronos": ts, "Cookie": cookie,
                "X-SS-STUB": stub.upper(),
                "x-tt-dm-status": "login" if cookie else "guest",
                "Content-Type": "application/x-www-form-urlencoded"
            }

            proxy = random.choice(prox_list) if use_proxy else None
            r = requests.post(f"https://api-h2.tiktokv.com{uri}{params}", data=payload, headers=headers, proxies=proxy, timeout=7, verify=False)
            
            if '"status_code":0' in r.text:
                with _lock:
                    success += 1
                    print(f"[{Fore.CYAN}{action.upper()}{Fore.RESET}] HIT! Total: {success}")
            else: fails += 1
            
            time.sleep(random.uniform(4, 7))
        except:
            fails += 1; time.sleep(2)

# --- EXECUTION ---
if __name__ == "__main__":
    Banner()
    
    target = input(f"{Fore.WHITE}Input Username or Room ID: ")
    room_id = get_room_id(target)
    
    if not room_id:
        print(f"{Fore.RED}[!] Room ID konnte nicht gefunden werden. Ist der User Live?"); exit()
    
    print(f"{Fore.GREEN}[+] Target Room ID: {room_id}")

    print(f"\n{Fore.YELLOW}[1] Live Like (Hearts)\n[2] Live Viewers (Enter)")
    mode = input(f"\n{Fore.WHITE}Wahl: ")
    action = "like" if mode == "1" else "enter"

    use_accs = input("Accounts/Sessions nutzen? (y/n): ").lower() == 'y'
    use_prx = input("Proxys nutzen? (y/n): ").lower() == 'y'
    threads = int(input("Threads: "))

    devices = open("devices.txt").read().splitlines()
    
    print(f"\n{Fore.CYAN}>>> BOOSTER AKTIVIERT <<<\n")
    for _ in range(threads):
        d = random.choice(devices).split(':')
        threading.Thread(target=run_task, args=(action, room_id, d[0], d[1], d[2], d[3], use_prx, use_accs), daemon=True).start()

    while True: time.sleep(1)
