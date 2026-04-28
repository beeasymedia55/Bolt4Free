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

# --- Initialization ---
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

# --- NEW: Room ID Grabber Logic ---
def grab_and_save_room_id(username):
    """Scrapes the room_id from a TikTok username and writes it to room_id.txt"""
    print(f"{Fore.YELLOW}[*] Fetching Room ID for @{username}...")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
            "Referer": "https://www.tiktok.com/"
        }
        response = requests.get(f"https://www.tiktok.com/@{username}/live", headers=headers, timeout=15)
        
        # Method 1: Regex for room_id in URL/HTML
        room_id = re.search(r'room_id=(\d+)', response.text)
        
        # Method 2: Check JSON state if Method 1 fails
        if not room_id:
            room_id = re.search(r'"roomId":"(\d+)"', response.text)
            
        if room_id:
            final_id = room_id.group(1)
            with open("room_id.txt", "w") as f: # We overwrite to ensure the bot uses the current live
                f.write(final_id)
            print(f"{Fore.GREEN}[+] Successfully grabbed Room ID: {final_id}")
            print(f"{Fore.GREEN}[+] Saved to room_id.txt")
            return final_id
        else:
            print(f"{Fore.RED}[!] Could not find Room ID. Is the user actually LIVE?")
            return None
    except Exception as e:
        print(f"{Fore.RED}[!] Error grabbing Room ID: {e}")
        return None

# --- Action Functions ---

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

def sendLiveViews(did, iid, room_id):
    global success, errors
    try:
        params = {"room_id": room_id, "device_id": did, "iid": iid, "version_code": "26.1.3"}
        url = "https://webcast16-normal-c-useast1a.tiktokv.com/webcast/ranklist/audience/?" + urlencode(params)
        resp = requests.get(url, headers=TikTokSigner.get_headers(did, iid), timeout=10)
        if resp.status_code == 200:
            with _lock:
                success += 1
                print(f"{Fore.YELLOW}[LIVE VIEW SENT] Room: {room_id} | Total: {success}")
    except:
        with _lock: errors += 1

# --- Main UI ---

def Main():
    global success
    os.system('cls' if os.name == 'nt' else 'clear')
    print(f"{Fore.MAGENTA}TikTok Ultimate Bot + Room Grabber")
    print("---------------------------------------")
    print("0. GRAB Room ID from Username")
    print("1. Video Views")
    print("2. Video Shares")
    print("3. Live Stream Views (Ensure Room ID is set)")
    print("---------------------------------------")
    
    choice = input("Choice: ")

    if choice == "0":
        user = input("Enter TikTok Username (without @): ")
        grab_and_save_room_id(user)
        input("\nPress Enter to return to menu...")
        return Main()

    threads_count = int(input("Threads: "))
    amount_target = int(input("Target Amount: "))
    
    # Reload data
    aweme_ids = load_list("video_links.txt")
    devices = load_list("devices.txt")
    room_ids = load_list("room_id.txt")
    
    if not devices:
        print(f"{Fore.RED}Error: devices.txt is missing!")
        return

    print(f"\n{Fore.WHITE}Botting started...\n")

    while success < amount_target:
        if threading.active_count() <= threads_count:
            device = random.choice(devices)
            try:
                did, iid, cdid, openudid = device.split(':')
                
                if choice == "1" and aweme_ids:
                    threading.Thread(target=sendViews, args=(did, iid, cdid, openudid, random.choice(aweme_ids))).start()
                elif choice == "3" and room_ids:
                    threading.Thread(target=sendLiveViews, args=(did, iid, room_ids[0])).start()
                
            except:
                continue
            
            time.sleep(0.01)

if __name__ == "__main__":
    Main()
