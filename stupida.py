from urllib.parse import urlencode, quote
from pystyle import *
from random import choice
import os, sys, ssl, re, time, random, threading, requests, hashlib, json, base64
from urllib3.exceptions import InsecureRequestWarning
from http import cookiejar
from concurrent.futures import ThreadPoolExecutor
from colorama import Fore, init 
init(autoreset=True)
# --- INITIALISIERUNG & BYPASS ---
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# --- X-GORGON ENGINE (NEU HINZUGEFÜGT) ---
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

xg = XGorgon()

# --- GLOBALE VARIABLEN ---
success = 0
fails = 0
proxies_list = []
if os.path.exists("proxies.txt"):
    proxies_list = open("proxies.txt").read().splitlines()

# --- HILFSFUNKTIONEN ---
def get_session():
    for f in ["sessions.txt", "accounts.txt"]:
        if os.path.exists(f):
            lines = open(f).read().splitlines()
            if lines: return random.choice(lines)
    return ""

def get_room_id(target):
    if target.isdigit(): return target
    try:
        r = requests.get(f"https://www.tiktok.com/@{target.replace('@','')}/live", timeout=10)
        rid = re.search(r'room_id=(\d+)', r.text) or re.search(r'"roomId":"(\d+)"', r.text)
        return rid.group(1)
    except: return None

# --- ORIGINAL BANNER ---
def Banner():
    os.system('cls' if os.name == 'nt' else 'clear')
    banner_text = r"""
████████╗██╗██╗  ██╗████████╗ ██████╗ ██╗  ██╗    ██████╗  ██████╗ ████████╗
╚══██╔══╝██║██║ ██╔╝╚══██╔══╝██╔═══██╗██║ ██╔╝    ██╔══██╗██╔═══██╗╚══██╔══╝
   ██║   ██║█████╔╝    ██║   ██║   ██║█████╔╝     ██████╔╝██║   ██║   ██║   
   ██║   ██║██╔═██╗    ██║   ██║   ██║██╔═██╗     ██╔══██╗██║   ██║   ██║   
   ██║   ██║██║  ██╗   ██║   ╚██████╔╝██║  ██╗    ██████╔╝╚██████╔╝   ██║   
   ╚═╝   ╚═╝╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝    ╚═════╝  ╚═════╝    ╚═╝   
    """
    print(Colorate.Vertical(Colors.blue_to_cyan, Center.XCenter(banner_text)))
    print(Center.XCenter(f"{Fore.WHITE}CRACKED BY PRONSMODS - UPDATED V4.0\n"))

# --- BOT FUNKTIONEN (MODERNISIERT) ---
def sendHearts(did, iid, cdid, openudid, room_id):
    global success, fails
    try:
        session = get_session()
        cookie = f"sessionid={session}" if session else ""
        
        params = urlencode({
            "room_id": room_id, "device_id": did, "install_id": iid,
            "cdid": cdid, "openudid": openudid, "aid": "1988",
            "device_platform": "android", "version_code": "300303"
        })
        payload = f"room_id={room_id}&count={random.randint(30, 80)}&basis=1"
        stub = hashlib.md5(payload.encode()).hexdigest()
        
        headers = {
            "X-Gorgon": xg.calculate(params, stub, cookie),
            "X-Khronos": str(int(time.time())),
            "X-SS-STUB": stub.upper(),
            "Cookie": cookie,
            "User-Agent": "com.ss.android.ugc.trill/300303 (Linux; U; Android 13; Pixel 7)",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        proxy = {"http": f"http://{random.choice(proxies_list)}"} if proxies_list else None
        r = requests.post(f"https://api-h2.tiktokv.com/webcast/room/like/?{params}", 
                          data=payload, headers=headers, proxies=proxy, timeout=7)
        
        if '"status_code":0' in r.text:
            success += 1
            print(f"[{Fore.CYAN}LIKE{Fore.RESET}] HIT! Total: {success}")
        else: fails += 1
    except: fails += 1

def sendViews(did, iid, cdid, openudid, room_id):
    global success, fails
    try:
        params = urlencode({
            "room_id": room_id, "device_id": did, "install_id": iid,
            "aid": "1988", "device_platform": "android", "version_code": "300303"
        })
        payload = f"room_id={room_id}&hold_living_room=1"
        stub = hashlib.md5(payload.encode()).hexdigest()
        
        headers = {
            "X-Gorgon": xg.calculate(params, stub, ""),
            "X-Khronos": str(int(time.time())),
            "X-SS-STUB": stub.upper(),
            "User-Agent": "com.ss.android.ugc.trill/300303 (Linux; U; Android 13; Pixel 7)"
        }

        r = requests.post(f"https://api-h2.tiktokv.com/webcast/room/enter/?{params}", 
                          data=payload, headers=headers, timeout=7)
        
        if '"status_code":0' in r.text:
            success += 1
            print(f"[{Fore.GREEN}VIEW{Fore.RESET}] HIT! Total: {success}")
        else: fails += 1
    except: fails += 1

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    Banner()
    
    target = input(f"{Fore.WHITE}Username oder Room ID: ")
    room_id = get_room_id(target)
    if not room_id:
        print(f"{Fore.RED}Fehler: Stream nicht gefunden!"); exit()

    print(f"\n{Fore.YELLOW}[1] Views | [2] Likes")
    choice_type = input(f"{Fore.WHITE}Wahl: ")
    
    use_accs = input("Accounts nutzen? (y/n): ").lower() == 'y'
    threads = int(input("Threads: "))

    devices = open("devices.txt").read().splitlines()
    
    print(f"\n{Fore.MAGENTA}>>> STARTE BOT AUF ROOM {room_id} <<<\n")

    def run():
        while True:
            device = random.choice(devices)
            did, iid, cdid, udid = device.split(':')
            if choice_type == "1":
                sendViews(did, iid, cdid, udid, room_id)
            else:
                sendHearts(did, iid, cdid, udid, room_id)
            time.sleep(random.uniform(2, 5))

    for _ in range(threads):
        threading.Thread(target=run, daemon=True).start()

    while True:
        time.sleep(1)
