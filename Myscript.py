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

# --- Initialisierung & SSL Bypass ---
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context

_lock = threading.Lock()
success, fails = 0, 0

# --- X-GORGON ENGINE (Optimiert nach beeasymedia55 Standards) ---
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

# --- TOOLS ---
def Banner():
    os.system('cls' if os.name == 'nt' else 'clear')
    banner = r"""
████████╗██╗██╗  ██╗████████╗ ██████╗ ██╗  ██╗
╚══██╔══╝██║██║ ██╔╝╚══██╔══╝██╔═══██╗██║ ██╔╝
   ██║   ██║█████╔╝    ██║   ██║   ██║█████╔╝ 
   ██║   ██║██╔═██╗    ██║   ██║   ██║██╔═██╗ 
   ██║   ██║██║  ██╗   ██║   ╚██████╔╝██║  ██╗
   ╚═╝   ╚═╝╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝
    """
    print(Center.XCenter(Colorate.Vertical(Colors.purple_to_blue, banner, 2)))
    print(Center.XCenter(f"{Fore.WHITE}BeeEasy Multi-Tool | X-Gorgon & X-Ladon Integrated\n"))

__raw_proxies = [
    "31.59.20.176:6754:hxidjrjw:nylyfhelpvdx", "198.23.239.134:6540:hxidjrjw:nylyfhelpvdx",
    "45.38.107.97:6014:hxidjrjw:nylyfhelpvdx", "107.172.163.27:6543:hxidjrjw:nylyfhelpvdx",
    "198.105.121.200:6462:hxidjrjw:nylyfhelpvdx", "216.10.27.159:6837:hxidjrjw:nylyfhelpvdx",
    "142.111.67.146:5611:hxidjrjw:nylyfhelpvdx", "191.96.254.138:6185:hxidjrjw:nylyfhelpvdx",
    "31.58.9.4:6077:hxidjrjw:nylyfhelpvdx", "104.239.107.47:5699:hxidjrjw:nylyfhelpvdx"
]

def get_proxies():
    return [{"http": f"http://{p.split(':')[2]}:{p.split(':')[3]}@{p.split(':')[0]}:{p.split(':')[1]}",
             "https": f"http://{p.split(':')[2]}:{p.split(':')[3]}@{p.split(':')[0]}:{p.split(':')[1]}"} for p in __raw_proxies]

xg = XGorgon()

def getRoomID(username):
    try:
        r = requests.get(f"https://www.tiktok.com/@{username}/live", headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        rid = re.search(r'room_id=(\d+)', r.text) or re.search(r'"roomId":"(\d+)"', r.text)
        if rid:
            open("room_id.txt", "w").write(rid.group(1))
            print(f"{Fore.GREEN}[+] Room ID: {rid.group(1)}"); return rid.group(1)
    except: pass
    return None

def live_action(action_type, did, iid, cdid, udid, use_proxy):
    global success, fails
    prox_list = get_proxies() if use_proxy else None
    
    while True:
        try:
            sess = random.choice(open("sessions.txt").read().splitlines())
            proxy = random.choice(prox_list) if use_proxy else None
            room_id = open("room_id.txt", "r").read().strip()
            
            # Neue Parameter Struktur basierend auf BeeEasy Repos
            params = urlencode({
                "room_id": room_id, "device_id": did, "install_id": iid,
                "aid": "1988", "device_platform": "android", "language": "de-DE",
                "version_code": "300303", "app_name": "tiktok_web", "device_type": "Pixel 7"
            })

            if action_type == "enter":
                uri, payload = "/webcast/room/enter/?", f"room_id={room_id}&hold_living_room=1&is_login=1"
            elif action_type == "like":
                uri, payload = "/webcast/room/like/?", f"room_id={room_id}&count={random.randint(20,50)}&basis=1"
            elif action_type == "share":
                uri, payload = "/webcast/share/?", f"room_id={room_id}&target=1"

            stub = hashlib.md5(payload.encode()).hexdigest()
            ts = str(int(time.time()))
            gorgon = xg.calculate(params, stub, sess)
            
            # Erweiterte Header für bessere Bypass-Rate
            headers = {
                "User-Agent": "com.ss.android.ugc.trill/300303 (Linux; U; Android 13; de_DE; Pixel 7)",
                "X-Gorgon": gorgon, "X-Khronos": ts, "Cookie": f"sessionid={sess}",
                "X-SS-STUB": stub.upper(),
                "X-Ladon": hashlib.sha256(ts.encode()).hexdigest(), # Neu: Ladon Simulation
                "x-tt-dm-status": "login",
                "Content-Type": "application/x-www-form-urlencoded"
            }

            r = requests.post(f"https://api-h2.tiktokv.com{uri}{params}", data=payload, headers=headers, proxies=proxy, timeout=7, verify=False)
            
            if '"status_code":0' in r.text:
                with _lock:
                    success += 1
                    print(f"[{Fore.MAGENTA}{action_type.upper()}{Fore.RESET}] {Fore.GREEN}SUCCESS {Fore.WHITE}| Total: {success}")
            else: 
                fails += 1
            time.sleep(10)
        except:
            fails += 1; time.sleep(2)

if __name__ == "__main__":
    Banner()
    print(f"[0] Get Room ID\n[1] Viewers (Enter)\n[2] Likes\n[3] Shares")
    mode = input(f"\n{Fore.YELLOW}Wahl: ")
    if mode == "0":
        getRoomID(input("Username: ").replace('@','')); exit()
        
    use_prx = input("Proxys nutzen? (y/n): ").lower() == 'y'
    threads = int(input("Threads: "))
    
    act = {"1": "enter", "2": "like", "3": "share"}.get(mode)
    devices = open("devices.txt").read().splitlines()
    
    for _ in range(threads):
        d = random.choice(devices).split(':')
        threading.Thread(target=live_action, args=(act, d[0], d[1], d[2], d[3], use_prx), daemon=True).start()
    
    while True: time.sleep(1)
