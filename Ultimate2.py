import os
import sys
import re
import time
import random
import threading
import requests
import hashlib
import json
from urllib.parse import urlencode
from colorama import init, Fore, Style

# --- Initialisierung ---
init(autoreset=True)
_lock = threading.Lock()
success = 0
errors = 0

class TikTokSigner:
    @staticmethod
    def get_headers(did, iid, session=None):
        headers = {
            "User-Agent": "com.ss.android.ugc.trill/2613 (Linux; U; Android 12; en_US; Pixel 6 Pro)",
            "Accept-Encoding": "gzip",
            "Connection": "keep-alive",
            "x-common-params-v2": "version_code=26.1.3&app_name=musically_go&device_platform=android",
            "x-did": did,
            "x-iid": iid
        }
        if session:
            headers["Cookie"] = f"sessionid={session}"
        return headers

def load_list(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        return []

# --- Room ID Grabber ---
def grab_and_save_room_id(username):
    print(f"{Fore.YELLOW}[*] Suche Room ID für @{username}...")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
            "Referer": "https://www.tiktok.com/"
        }
        response = requests.get(f"https://www.tiktok.com/@{username}/live", headers=headers, timeout=15)
        
        room_id = re.search(r'room_id=(\d+)', response.text)
        if not room_id:
            room_id = re.search(r'"roomId":"(\d+)"', response.text)
            
        if room_id:
            final_id = room_id.group(1)
            with open("room_id.txt", "w") as f:
                f.write(final_id)
            print(f"{Fore.GREEN}[+] Room ID gefunden und gespeichert: {final_id}")
            return final_id
        else:
            print(f"{Fore.RED}[!] Keine Room ID gefunden. Ist der User LIVE?")
            return None
    except Exception as e:
        print(f"{Fore.RED}[!] Fehler beim Grabbing: {e}")
        return None

# --- Action Funktionen ---

def sendViews(did, iid, cdid, openudid, aweme_id):
    global success, errors
    try:
        params = {"device_id": did, "iid": iid, "aweme_id": aweme_id, "app_name": "musically_go", "version_code": "26.1.3", "device_platform": "android"}
        url = "https://api16-core-c-useast1a.tiktokv.com/aweme/v1/commit/item/play/?" + urlencode(params)
        resp = requests.post(url, headers=TikTokSigner.get_headers(did, iid), timeout=10)
        if resp.status_code == 200:
            with _lock:
                success += 1
                print(f"{Fore.GREEN}[VIEW SUCCESS] Total: {success}")
    except:
        with _lock: errors += 1

# --- NEU: Live Interaktionen ---

def sendLiveEnter(did, iid, room_id):
    global success, errors
    try:
        params = {"room_id": room_id, "device_id": did, "iid": iid, "version_code": "26.1.3", "device_platform": "android", "aid": "1233"}
        url = "https://webcast16-normal-c-useast1a.tiktokv.com/webcast/room/enter/?" + urlencode(params)
        resp = requests.post(url, headers=TikTokSigner.get_headers(did, iid), timeout=10)
        if resp.status_code == 200:
            with _lock:
                success += 1
                print(f"{Fore.CYAN}[LIVE ENTER] Room: {room_id} | Total: {success}")
    except:
        with _lock: errors += 1

def sendLiveLike(did, iid, room_id):
    global success, errors
    try:
        params = {"room_id": room_id, "device_id": did, "iid": iid, "version_code": "26.1.3", "count": random.randint(1, 3)}
        url = "https://webcast16-normal-c-useast1a.tiktokv.com/webcast/room/like/?" + urlencode(params)
        resp = requests.post(url, headers=TikTokSigner.get_headers(did, iid), timeout=10)
        if resp.status_code == 200:
            with _lock:
                success += 1
                print(f"{Fore.LIGHTRED_EX}[LIVE LIKE] Room: {room_id} | Total: {success}")
    except:
        with _lock: errors += 1

def sendLiveShare(did, iid, room_id):
    global success, errors
    try:
        params = {"room_id": room_id, "device_id": did, "iid": iid, "version_code": "26.1.3"}
        url = "https://webcast16-normal-c-useast1a.tiktokv.com/webcast/room/share/?" + urlencode(params)
        resp = requests.post(url, headers=TikTokSigner.get_headers(did, iid), timeout=10)
        if resp.status_code == 200:
            with _lock:
                success += 1
                print(f"{Fore.BLUE}[LIVE SHARE] Room: {room_id} | Total: {success}")
    except:
        with _lock: errors += 1

# --- Main UI ---

def Main():
    global success
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"{Fore.MAGENTA}TikTok Ultimate Bot + Live Interactions")
    print("---------------------------------------")
    print("0. GRAB Room ID from Username")
    print("1. Video Views")
    print("2. Live Room Enter")
    print("3. Live Room Like")
    print("4. Live Room Share")
    print("---------------------------------------")
    
    choice = input("Choice: ")

    if choice == "0":
        user = input("Enter TikTok Username (without @): ")
        grab_and_save_room_id(user)
        input("\nDrücke Enter für Menü...")
        return Main()

    threads_count = int(input("Threads: "))
    amount_target = int(input("Target Amount: "))
    
    # Daten laden
    devices = load_list("devices.txt")
    room_ids = load_list("room_id.txt")
    aweme_ids = load_list("video_links.txt")
    
    if not devices:
        print(f"{Fore.RED}Error: devices.txt fehlt!")
        return

    print(f"\n{Fore.WHITE}Botting gestartet...\n")

    while success < amount_target:
        if threading.active_count() <= threads_count:
            device = random.choice(devices)
            try:
                # did:iid:cdid:openudid Format
                parts = device.split(':')
                did, iid = parts[0], parts[1]
                
                if choice == "1" and aweme_ids:
                    threading.Thread(target=sendViews, args=(did, iid, parts[2], parts[3], random.choice(aweme_ids))).start()
                elif choice == "2" and room_ids:
                    threading.Thread(target=sendLiveEnter, args=(did, iid, room_ids[0])).start()
                elif choice == "3" and room_ids:
                    threading.Thread(target=sendLiveLike, args=(did, iid, room_ids[0])).start()
                elif choice == "4" and room_ids:
                    threading.Thread(target=sendLiveShare, args=(did, iid, room_ids[0])).start()
                
            except:
                continue
            
            time.sleep(0.01)

if __name__ == "__main__":
    Main()
