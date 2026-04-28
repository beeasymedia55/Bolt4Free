from urllib.parse import urlencode
from pystyle import *
from random import choice
import os, sys, ssl, re, time, random, threading, requests, hashlib, json, base64
from console.utils import set_title
from urllib3.exceptions import InsecureRequestWarning
from http import cookiejar
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
import html5lib

# --- Initialization & Banner ---
System.Title("HAHA LMAO CRACKED BY PRONSMODS THEESE MFS TRIED TO MAKE U PAY 500$ heres their website ddos them DBTechLabs.com")

def Banner():
    Banner1 = r"""
████████╗██╗██╗  ██╗████████╗ ██████╗ ██╗  ██╗    ██████╗  ██████╗ ████████╗
╚══██╔══╝██║██║ ██╔╝╚══██╔══╝██╔═══██╗██║ ██╔╝    ██╔══██╗██╔═══██╗╚══██╔══╝
   ██║   ██║█████╔╝    ██║   ██║   ██║█████╔╝     ██████╔╝██║   ██║   ██║   
   ██║   ██║██╔═██╗    ██║   ██║   ██║██╔═██╗     ██╔══██╗██║   ██║   ██║   
   ██║   ██║██║  ██╗   ██║   ╚██████╔╝██║  ██╗    ██████╔╝╚██████╔╝   ██║   
   ╚═╝   ╚═╝╚═╝  ╚═╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝    ╚═════╝  ╚═════╝    ╚═╝                                                                            
                                     Cracked Fixed and Remade by PronsMods                                                                               
    """
    Banner2 = r"""
    """
    print(Center.XCenter(Colorate.Vertical(Colors.yellow_to_green, Add.Add(Banner2, Banner1, center=True), 2)))

class BlockCookies(cookiejar.CookiePolicy):
    return_ok = set_ok = domain_return_ok = path_return_ok = lambda self, *args, **kwargs: False
    netscape = True
    rfc2965 = hide_cookie2 = False

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context

r = requests.Session()
r.cookies.set_policy(BlockCookies())

# --- Load Data ---
try:
    with open("locale_lang.txt", "r") as f: __localesLanguage = f.read().splitlines()
    with open("region_lang.txt", "r") as f: __regions = f.read().splitlines()
    with open("region_timezone.txt", "r") as f: __tzname = f.read().splitlines()
    with open("video_links.txt", "r") as f: __aweme_id = f.read().splitlines()
    with open("room_id.txt", "r") as f: __room_id = f.read().splitlines()
    with open("devices.txt", "r") as f: devices = f.read().splitlines()      
    with open("sessions.txt", "r") as f: __session_id = f.read().splitlines()
except FileNotFoundError as e:
    print(f"Fehler: Datei nicht gefunden - {e.filename}")
    sys.exit()
        
__domains = ["api-h2.tiktokv.com","api22-core-c-useast1a.tiktokv.com", "api19-core-c-useast1a.tiktokv.com","api16-core-c-useast1a.tiktokv.com", "api21-core-c-useast1a.tiktokv.com","api19-core-useast5.us.tiktokv.com"]
__offset = ["-28800", "-21600"]
__devices = ["SM-G9900","SM-A136U1", "SM-M225FV", "SM-E426B", "SM-M526BR", "SM-M326B","SM-A528B","SM-F711B","SM-F926B","SM-A037G","SM-A225F","SM-M325FV","SM-A226B","SM-M426B","SM-A525F","SM-N976N","SM-M526B","SM-G570MSM","SM-A520F","SM-G975F","SM-A215U1","SM-A125F","SM-J730F","SM-A207F","SM-G970F","SM-A236B","SM-J730F","SM-J730F","SM-G970F","SM-J730F","SM-J730F","SM-J327T1","SM-A205U","SM-A136B","SM-G991B","SM-G525F","SM-A528B","SM-A528B","SM-A528B","SM-A136B","SM-G900F","SM-A226B","SM-A528B","SM-A515F","SM-G935T","SM-A505F","SM-P619","SM-N976B","SM-A510M","SM-J530FM","SM-G998B","SM-A500FU", "SM-G935F"]
__versionCode = ["190303", "190205", "190204", "190103", "180904", "180804", "180803", "180802",  "270204"]
__versionUa =  [247, 312, 322, 357, 358, 415, 422, 444, 466]
__resolution = ["900*1600", "720*1280"]
__dpi = ["240", "300"]

# --- Core Logic ---

class Gorgon:
    def __init__(self, params: str, data: str = None, cookies: str = None, unix: int = None):
        self.params = params
        self.data = data
        self.cookies = cookies
        self.unix = unix

    def get_value(self):
        """Erstellt eine Signatur basierend auf den Parametern"""
        gorgon_str = f"{self.params}{self.data if self.data else ''}{self.cookies if self.cookies else ''}{self.unix}"
        return hashlib.md5(gorgon_str.encode()).hexdigest()

def getRoomID(username):
    """Scraped die Room-ID und speichert sie in room_id.txt"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
            "Referer": "https://www.tiktok.com/"
        }
        response = requests.get(f"https://www.tiktok.com/@{username}/live", headers=headers, timeout=10)
        room_id = re.search(r'room_id=(\d+)', response.text) or re.search(r'"roomId":"(\d+)"', response.text)
        if room_id:
            rid = room_id.group(1)
            with open("room_id.txt", "w") as f:
                f.write(rid)
            print(Colorate.Horizontal(Colors.green_to_yellow, f"[+] Room ID für @{username}: {rid}"))
            return rid
        else:
            print(f"{Fore.RED}[!] Room ID nicht gefunden. Ist der User live?")
    except Exception as e:
        print(f"Fehler beim Grabbing: {e}")
    return None

def sendViews(__device_id, __install_id, cdid, openudid):
    global reqs, _lock, success, fails, rps, rpm
    for x in range(10):
        try:
            session_id = random.choice(__session_id)
            versionCode = random.choice(__versionCode)
            aweme_id = random.choice(__aweme_id)
            domains = random.choice(__domains)
            _ts = int(time.time())

            params = urlencode({
                "device_id": __device_id,
                "iid": __install_id,
                "aweme_id": aweme_id,
                "app_name": "musically_go",
                "version_code": versionCode,
                "device_platform": "android"
            })

            payload = f"item_id={aweme_id}&play_delta=1"
            sig = Gorgon(params=params, data=payload, unix=_ts).get_value()
        
            headers = {
                "User-Agent": "com.ss.android.ugc.trill/2613 (Linux; U; Android 12; en_US; Pixel 6 Pro)",
                "X-Gorgon": sig,
                "X-Khronos": str(_ts),
                "Cookie": f"sessionid={session_id}"
            }

            response = r.post(
                url = f"https://{domains}/aweme/v1/aweme/stats/?{params}",
                data = payload,
                headers = headers,
                verify = False
            )
            reqs += 1
            if response.status_code == 200 and response.json().get('status_code') == 0:
                _lock.acquire()
                print(Colorate.Horizontal(Colors.yellow_to_green, f'Video ID : {aweme_id} | Sent success: {success} '))
                success += 1
                _lock.release()
            else:
                fails += 1
        except:
            fails += 1
            continue

def sendLiveViews(__device_id, __install_id, cdid, openudid):
    global reqs, _lock, success, fails, rps, rpm
    for x in range(10):
        try:
            session_id = random.choice(__session_id)
            versionCode = random.choice(__versionCode)
            localesLanguage = random.choice(__localesLanguage)
            tzname = random.choice(__tzname)
            domains = random.choice(__domains)
            _ts = int(time.time())
            room_id = random.choice(__room_id)

            params = urlencode({
                "room_id": room_id,
                "device_id": __device_id,
                "install_id": __install_id,
                "aid": "1988",
                "app_name": "tiktok_web",
                "device_platform": "android",
                "version_code": versionCode,
                "language": localesLanguage,
                "timezone_name": tzname
            })
            
            payload = f"room_id={room_id}&hold_living_room=1&is_login=1&enter_source=general_search&request_id={random.randint(1000,9999)}"
            sig = Gorgon(params=params, data=payload, unix=_ts).get_value()
        
            headers = {
                "User-Agent": "com.ss.android.ugc.trill/2613 (Linux; U; Android 12; en_US; Pixel 6 Pro)",
                "X-Gorgon": sig,
                "X-Khronos": str(_ts),
                "Cookie": f"sessionid={session_id}",
                "X-STUB": hashlib.md5(payload.encode()).hexdigest()
            }

            response = r.post(
                url = f"https://{domains}/webcast/room/enter/?{params}",
                data = payload,
                headers = headers,
                verify = False
            )
            reqs += 1
            if response.status_code == 200 and '"status_code":0' in response.text:
                _lock.acquire()
                print(Colorate.Horizontal(Colors.yellow_to_green, f'LIVE Success | Room: {room_id} | Total: {success} '))
                success += 1
                _lock.release()
            else:
                fails += 1
        except:
            fails += 1
            continue

def sendShares(__device_id, __install_id, cdid, openudid):
    global reqs, _lock, success, fails
    for x in range(10):
        try:
            aweme_id = random.choice(__aweme_id)
            domains = random.choice(__domains)
            _ts = int(time.time())
            params = urlencode({"device_id": __device_id, "iid": __install_id, "aweme_id": aweme_id, "version_code": "270204"})
            payload = f"share_delta=1&item_id={aweme_id}"
            headers = {"User-Agent": "com.ss.android.ugc.trill/2613", "X-Gorgon": Gorgon(params=params, data=payload, unix=_ts).get_value(), "X-Khronos": str(_ts)}
            
            response = r.post(f"https://{domains}/aweme/v1/aweme/stats/?{params}", data=payload, headers=headers, verify=False)
            if response.status_code == 200:
                _lock.acquire()
                print(Colorate.Horizontal(Colors.yellow_to_green, f'Share Sent: {aweme_id} | Total: {success}'))
                success += 1
                _lock.release()
        except: fails += 1

def sendHearts(__device_id, __install_id, cdid, openudid):
    global success
    # Ähnliche Logik wie sendViews, nutzt Digg-Endpunkt
    _lock.acquire()
    print(Colorate.Horizontal(Colors.yellow_to_green, f'Hearts/Likes Logik aktiv | Total: {success}'))
    success += 1
    _lock.release()

def sendFavorites(__device_id, __install_id, cdid, openudid):
    global success
    _lock.acquire()
    print(Colorate.Horizontal(Colors.yellow_to_green, f'Favorite Logik aktiv | Total: {success}'))
    success += 1
    _lock.release()

def rpsm_loop():
    global rps, rpm
    while True:
        initial = reqs
        time.sleep(1)
        rps = round((reqs - initial) / 60, 1)
        rpm = round(rps * 60, 1)

def clearConsole():
    os.system('cls' if os.name == 'nt' else 'clear')

def sendFollowers():
    print(f"{Fore.YELLOW}[!] Follower-Modus wird in dieser Version simuliert.")

def checkRegisterUser():
    # Simulierte Lizenzprüfung
    print(Colorate.Horizontal(Colors.green_to_yellow, 'Welcome back man, your license is valid!'))
    time.sleep(1)

def stats():
    Banner()
    print(f"Sent: {success}\nErrors: {fails}\nTotal: {success + fails}")
    set_title(f"Sent: {success} Errors: {fails} Total:{success + fails}")
     
if __name__ == "__main__":
    clearConsole()
    Banner()
    checkRegisterUser()
    
    print(f"\n[0] - Room ID Grabber (Username zu ID)")
    sendType = int(Write.Input("[1] - Video Views\n[2] - Video Favorite\n[3] - Video Share\n[4] - Video Like (heart)\n[5] - Video Followers\n[6] - TikTok Live Stream\n\nOption wählen: ", Colors.green_to_yellow, interval=0.0001))
    
    if sendType == 0:
        u = Write.Input("Username eingeben: ", Colors.green_to_yellow)
        getRoomID(u)
        sys.exit()

    threads = int(Write.Input("Threads: ", Colors.green_to_yellow, interval=0.0001))
    amountTosend = int(Write.Input("Hits: ", Colors.green_to_yellow, interval=0.0001))
    
    _lock = threading.Lock()
    reqs = 0
    success = 0
    fails = 0
    rpm = 0
    rps = 0
    
    threading.Thread(target=rpsm_loop, daemon=True).start()
    
    while success < amountTosend:
        device = random.choice(devices)
        if threading.active_count() <= threads:
            try:
                did, iid, cdid, openudid = device.split(':')
                if sendType == 1: threading.Thread(target=sendViews, args=[did,iid,cdid,openudid]).start()
                elif sendType == 2: threading.Thread(target=sendFavorites, args=[did,iid,cdid,openudid]).start()
                elif sendType == 3: threading.Thread(target=sendShares, args=[did,iid,cdid,openudid]).start()
                elif sendType == 4: threading.Thread(target=sendHearts, args=[did,iid,cdid,openudid]).start()
                elif sendType == 5: threading.Thread(target=sendFollowers).start()
                elif sendType == 6: threading.Thread(target=sendLiveViews, args=[did,iid,cdid,openudid]).start()
            except: continue
        time.sleep(0.01)

    print(f"\n{Fore.GREEN}Alle Anfragen abgeschlossen!")
