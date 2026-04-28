from urllib.parse import urlencode, quote
from pystyle import *
from random import choice
import os, sys, ssl, re, time, random, threading, requests, hashlib, json
from urllib3.exceptions import InsecureRequestWarning
from colorama import init, Fore

init(autoreset=True)

# --- Initialisierung ---
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context

_lock = threading.Lock()
success, fails = 0, 0

# --- Banner ---
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
    print(Center.XCenter(Colorate.Vertical(Colors.yellow_to_green, banner_text, 2)))
    print(Center.XCenter(f"{Fore.CYAN}Ultimate Live Tool - Enter | Share | Comment | LIKE - by PronsMods\n"))

# --- INTERNE KONFIGURATION ---
__domains = ["api-h2.tiktokv.com", "api22-core-c-useast1a.tiktokv.com", "api16-core-c-useast1a.tiktokv.com"]
__locales = ["de_DE", "en_US", "tr_TR", "fr_FR"]
__regions = ["DE", "US", "TR", "FR"]

# Deine Proxys (IP:Port:User:Pass)
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

def get_proxies():
    prox = []
    for p in __raw_proxies:
        ip, port, user, pw = p.split(':')
        prox.append({"http": f"http://{user}:{pw}@{ip}:{port}", "https": f"http://{user}:{pw}@{ip}:{port}"})
    return prox

__proxies = get_proxies()

class Gorgon:
    def __init__(self, params: str, data: str = None, unix: int = None):
        self.params, self.data, self.unix = params, data, unix
    def get_value(self):
        g_str = f"{self.params}{self.data if self.data else ''}{self.unix}"
        return hashlib.md5(g_str.encode()).hexdigest()

def getRoomID(username):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    try:
        res = requests.get(f"https://www.tiktok.com/@{username}/live", headers=headers, timeout=10)
        rid = re.search(r'room_id=(\d+)', res.text) or re.search(r'"roomId":"(\d+)"', res.text)
        if rid:
            with open("room_id.txt", "w") as f: f.write(rid.group(1))
            print(f"{Fore.GREEN}[+] ID gefunden: {rid.group(1)}"); return rid.group(1)
    except: pass
    return None

def live_action(action_type, did, iid, cdid, udid):
    global success, fails
    while True:
        try:
            sess = random.choice(open("sessions.txt").read().splitlines())
            proxy = random.choice(__proxies)
            with open("room_id.txt", "r") as f: room_id = f.read().strip()
            
            _ts = int(time.time())
            params_dict = {
                "room_id": room_id, "device_id": did, "install_id": iid,
                "aid": "1988", "device_platform": "android", "language": random.choice(__locales),
                "region": random.choice(__regions), "app_name": "tiktok_web"
            }

            if action_type == "enter":
                url = f"https://{random.choice(__domains)}/webcast/room/enter/?"
                payload = f"room_id={room_id}&hold_living_room=1&is_login=1"
            elif action_type == "share":
                url = f"https://{random.choice(__domains)}/webcast/share/?"
                payload = f"room_id={room_id}&target=1"
            elif action_type == "comment":
                url = f"https://{random.choice(__domains)}/webcast/room/chat/?"
                payload = f"room_id={room_id}&content={quote(random.choice(['🔥','Nice','WOW','LFG']))}"
            elif action_type == "like":
                # Basierend auf mobilen Endpunkten aus deinen Dateien
                url = f"https://{random.choice(__domains)}/webcast/room/like/?"
                payload = f"room_id={room_id}&count={random.randint(5,15)}&basis=1"

            params = urlencode(params_dict)
            full_url = url + params
            sig = Gorgon(params, payload, _ts).get_value()

            headers = {
                "User-Agent": "com.ss.android.ugc.trill/2613 (Linux; U; Android 12)",
                "X-Gorgon": sig, "X-Khronos": str(_ts), "Cookie": f"sessionid={sess}",
                "X-STUB": hashlib.md5(payload.encode()).hexdigest(),
                "Content-Type": "application/x-www-form-urlencoded"
            }

            resp = requests.post(full_url, data=payload, headers=headers, proxies=proxy, timeout=7, verify=False)
            
            if '"status_code":0' in resp.text:
                with _lock:
                    success += 1
                    print(f"[{Fore.CYAN}{action_type.upper()}{Fore.RESET}] {Fore.GREEN}OK {Fore.WHITE}| Total: {success}")
            else: fails += 1
            
            time.sleep(10) # Delay für Stabilität
        except:
            fails += 1; time.sleep(2)

if __name__ == "__main__":
    Banner()
    print("[0] Grab Room ID\n[1] Live Enter (Viewer)\n[2] Live Share\n[3] Live Comment\n[4] Live LIKE (Herz-Spam)")
    opt = input("\nWahl: ")
    
    if opt == "0":
        getRoomID(input("User: ").replace('@','')); sys.exit()
    
    mapping = {"1": "enter", "2": "share", "3": "comment", "4": "like"}
    act = mapping.get(opt)
    if not act: sys.exit()

    try:
        devices = open("devices.txt").read().splitlines()
        threads = int(input("Threads: "))
        while True:
            if threading.active_count() <= threads:
                d = random.choice(devices).split(':')
                threading.Thread(target=live_action, args=(act, d[0], d[1], d[2], d[3]), daemon=True).start()
            time.sleep(0.01)
    except FileNotFoundError:
        print("Dateien fehlen!"); sys.exit()
