from urllib.parse import urlencode
from pystyle import *
from random import choice
import os, sys, ssl, re, time, random, threading, requests, hashlib, json, base64
from console.utils import set_title
from urllib3.exceptions import InsecureRequestWarning
from colorama import init, Fore

init(autoreset=True)

# --- Initialisierung ---
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context

_lock = threading.Lock()
success = 0
fails = 0
reqs = 0

# --- Banner ---
def Banner():
    os.system('cls' if os.name == 'nt' else 'clear')
    Banner1 = r"""
████████╗██╗██╗  ██╗████████╗ ██████╗ ██╗  ██╗    ██████╗  ██████╗ ████████╗
╚══██╔══╝██║██║ ██╔╝╚══██╔══╝██╔═══██╗██║ ██╔╝    ██╔══██╗██╔═══██╗╚══██╔══╝
   ██║   ██║█████╔╝    ██║   ██║   ██║█████╔╝     ██████╔╝██║   ██║   ██║   
   ██║   ██║██╔═██╗    ██║   ██║   ██║██╔═██╗     ██╔══██╗██║   ██║   ██║   
   ██║   ██║██║  ██╗   ██║   ╚██████╔╝██║  ██╗    ██████╔╝╚██████╔╝   ██║   
   ╚═╝   ╚═╝╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝    ╚═════╝  ╚═════╝    ╚═╝                                                                            
    """
    print(Center.XCenter(Colorate.Vertical(Colors.yellow_to_green, Banner1, 2)))
    print(Center.XCenter(f"{Fore.CYAN}Stay Alive & Viewer Booster + Proxy Support - Cracked by PronsMods\n"))

# --- INTERNE DATEN ---
__domains = ["api-h2.tiktokv.com", "api22-core-c-useast1a.tiktokv.com", "api16-core-c-useast1a.tiktokv.com"]
__localesLanguage = ["de_DE", "en_US", "en_GB", "fr_FR", "es_ES", "tr_TR", "it_IT"]
__regions = ["DE", "US", "GB", "FR", "ES", "TR", "IT"]
__tzname = ["Europe/Berlin", "America/New_York", "Europe/London", "Europe/Paris"]
__versionCode = ["190303", "190205", "270204"]

# Deine bereitgestellten Proxys
__raw_proxies = [
    "31.59.20.176:6754:hxidjrjw:nylyfhelpvdx",
    "198.23.239.134:6540:hxidjrjw:nylyfhelpvdx",
    "45.38.107.97:6014:hxidjrjw:nylyfhelpvdx",
    "107.172.163.27:6543:hxidjrjw:nylyfhelpvdx",
    "198.105.121.200:6462:hxidjrjw:nylyfhelpvdx",
    "216.10.27.159:6837:hxidjrjw:nylyfhelpvdx",
    "142.111.67.146:5611:hxidjrjw:nylyfhelpvdx",
    "191.96.254.138:6185:hxidjrjw:nylyfhelpvdx",
    "31.58.9.4:6077:hxidjrjw:nylyfhelpvdx",
    "104.239.107.47:5699:hxidjrjw:nylyfhelpvdx"
]

def format_proxies():
    formatted = []
    for p in __raw_proxies:
        ip, port, user, pw = p.split(':')
        formatted.append({"http": f"http://{user}:{pw}@{ip}:{port}", "https": f"http://{user}:{pw}@{ip}:{port}"})
    return formatted

__proxies = format_proxies()

# --- DATEIEN LADEN ---
try:
    with open("sessions.txt", "r") as f: __session_id = f.read().splitlines()
    with open("devices.txt", "r") as f: devices_data = f.read().splitlines()
except FileNotFoundError as e:
    print(f"{Fore.RED}[!] Datei fehlt: {e.filename}")
    sys.exit()

class Gorgon:
    def __init__(self, params: str, data: str = None, unix: int = None):
        self.params, self.data, self.unix = params, data, unix
    def get_value(self):
        g_str = f"{self.params}{self.data if self.data else ''}{self.unix}"
        return hashlib.md5(g_str.encode()).hexdigest()

def getRoomID(username):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        res = requests.get(f"https://www.tiktok.com/@{username}/live", headers=headers, timeout=10)
        m = re.search(r'room_id=(\d+)', res.text) or re.search(r'"roomId":"(\d+)"', res.text)
        if m:
            rid = m.group(1)
            with open("room_id.txt", "w") as f: f.write(rid)
            print(f"{Fore.GREEN}[+] ID: {rid}"); return rid
    except: pass
    return None

def sendLiveViews(did, iid, cdid, udid):
    global success, fails
    while True:
        try:
            sess, lang, reg, dom = random.choice(__session_id), random.choice(__localesLanguage), random.choice(__regions), random.choice(__domains)
            proxy = random.choice(__proxies)
            with open("room_id.txt", "r") as f: room_id = f.read().strip()
            
            _ts = int(time.time())
            params = urlencode({
                "room_id": room_id, "device_id": did, "install_id": iid,
                "aid": "1988", "device_platform": "android", "language": lang,
                "region": reg, "version_code": "270204"
            })
            payload = f"room_id={room_id}&hold_living_room=1&is_login=1"
            headers = {
                "User-Agent": "com.ss.android.ugc.trill/2613",
                "X-Gorgon": Gorgon(params, payload, _ts).get_value(),
                "X-Khronos": str(_ts), "Cookie": f"sessionid={sess}"
            }

            resp = requests.post(f"https://{dom}/webcast/room/enter/?{params}", data=payload, headers=headers, proxies=proxy, timeout=10, verify=False)
            
            if '"status_code":0' in resp.text:
                with _lock:
                    success += 1
                    print(f"[{Fore.CYAN}JOIN{Fore.RESET}] {Fore.GREEN}{reg}/{lang} {Fore.WHITE}| {Fore.YELLOW}Proxy: {proxy['http'].split('@')[1]} {Fore.WHITE}| Total: {success}")
            else: fails += 1
            time.sleep(15) # Stay-alive delay
        except:
            fails += 1; time.sleep(2)

if __name__ == "__main__":
    Banner()
    print("[0] Grab ID\n[1] Start Views")
    mode = input("\nWahl: ")
    if mode == "0":
        getRoomID(input("User: ").replace('@','')); sys.exit()
    
    threads = int(input("Threads: "))
    while True:
        if threading.active_count() <= threads:
            try:
                did, iid, cdid, udid = random.choice(devices_data).split(':')
                threading.Thread(target=sendLiveViews, args=(did, iid, cdid, udid), daemon=True).start()
            except: pass
        time.sleep(0.01)
