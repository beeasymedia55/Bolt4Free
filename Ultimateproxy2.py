from urllib.parse import urlencode
from pystyle import *
from random import choice
import os, sys, ssl, re, time, random, threading, requests, hashlib, json, base64
from urllib3.exceptions import InsecureRequestWarning
from colorama import init, Fore

init(autoreset=True)

# --- Initialisierung ---
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context

_lock = threading.Lock()
success, fails, reqs = 0, 0, 0

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
    print(Center.XCenter(f"{Fore.CYAN}TikTok Live Multi-Tool (Enter/Share/Comment) - Cracked by PronsMods\n"))

# --- INTERNE DATEN ---
__domains = [
    "api-h2.tiktokv.com", "api22-core-c-useast1a.tiktokv.com", 
    "api16-core-c-useast1a.tiktokv.com", "api21-core-c-useast1a.tiktokv.com",
    "api19-core-c-useast1a.tiktokv.com"
]

__localesLanguage = ["de_DE", "en_US", "en_GB", "fr_FR", "es_ES", "tr_TR", "it_IT", "pt_BR", "ru_RU"]
__regions = ["DE", "US", "GB", "FR", "ES", "TR", "IT", "BR", "RU"]
__tzname = ["Europe/Berlin", "America/New_York", "Europe/London", "Europe/Paris"]

# Deine Proxys
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
    print(f"{Fore.RED}[!] Datei fehlt: {e.filename}"); sys.exit()

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
            print(f"{Fore.GREEN}[+] Room ID: {rid}"); return rid
    except: pass
    return None

# --- ENDPOINTS LOGIK ---

def live_action(action_type, did, iid, cdid, udid):
    global success, fails
    while True:
        try:
            sess = random.choice(__session_id)
            lang, reg, dom = random.choice(__localesLanguage), random.choice(__regions), random.choice(__domains)
            proxy = random.choice(__proxies)
            with open("room_id.txt", "r") as f: room_id = f.read().strip()
            
            _ts = int(time.time())
            params_dict = {
                "room_id": room_id, "device_id": did, "install_id": iid,
                "aid": "1988", "device_platform": "android", "language": lang,
                "region": reg, "app_name": "tiktok_web", "version_code": "270204"
            }

            # Differenzierung der Endpunkte
            if action_type == "enter":
                endpoint = f"https://{dom}/webcast/room/enter/?"
                payload = f"room_id={room_id}&hold_living_room=1&is_login=1"
            elif action_type == "share":
                endpoint = f"https://{dom}/webcast/share/?"
                payload = f"room_id={room_id}&target=1" # 1 = Share to external
            elif action_type == "comment":
                endpoint = f"https://{dom}/webcast/room/chat/?"
                comment_text = random.choice(["🔥", "Cool!", "OMG", "LFG", "Nice", "wow"])
                payload = f"room_id={room_id}&content={comment_text}"

            params = urlencode(params_dict)
            headers = {
                "User-Agent": "com.ss.android.ugc.trill/2613 (Linux; U; Android 12)",
                "X-Gorgon": Gorgon(params, payload, _ts).get_value(),
                "X-Khronos": str(_ts),
                "Cookie": f"sessionid={sess}",
                "X-STUB": hashlib.md5(payload.encode()).hexdigest(),
                "Content-Type": "application/x-www-form-urlencoded"
            }

            resp = requests.post(endpoint + params, data=payload, headers=headers, proxies=proxy, timeout=10, verify=False)
            
            if '"status_code":0' in resp.text:
                with _lock:
                    success += 1
                    print(f"[{Fore.CYAN}{action_type.upper()}{Fore.RESET}] {Fore.GREEN}Success {Fore.WHITE}| {Fore.YELLOW}Proxy OK {Fore.WHITE}| Total: {success}")
            else: fails += 1
            
            # Delay je nach Action
            time.sleep(12) if action_type == "enter" else time.sleep(5)
        except:
            fails += 1; time.sleep(2)

if __name__ == "__main__":
    Banner()
    print(f"{Fore.WHITE}[0] Grab Room ID")
    print(f"{Fore.WHITE}[1] Live Enter (Viewer Boost/Stay-Alive)")
    print(f"{Fore.WHITE}[2] Live Share (Share Boost)")
    print(f"{Fore.WHITE}[3] Live Comment (Chat Spam)")
    
    choice_mode = input(f"\n{Fore.YELLOW}Wähle Option: ")
    
    if choice_mode == "0":
        getRoomID(input("User: ").replace('@','')); sys.exit()
    
    action_map = {"1": "enter", "2": "share", "3": "comment"}
    selected_action = action_map.get(choice_mode)
    
    if not selected_action:
        print("Invalid choice"); sys.exit()

    if not os.path.exists("room_id.txt"):
        print("Führe erst Option 0 aus!"); sys.exit()

    threads = int(input("Threads: "))
    
    print(f"\n{Fore.MAGENTA}>>> {selected_action.upper()} BOOSTER GESTARTET <<<\n")
    
    while True:
        if threading.active_count() <= threads:
            try:
                did, iid, cdid, udid = random.choice(devices_data).split(':')
                threading.Thread(target=live_action, args=(selected_action, did, iid, cdid, udid), daemon=True).start()
            except: pass
        time.sleep(0.01)
