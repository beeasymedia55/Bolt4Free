import requests
from user_agent import generate_user_agent
from time import time, sleep
import random
from colorama import init, Fore
import threading
import os
import re

init(autoreset=True)

print(f'''
{Fore.CYAN}
   🔥 TIKTOK LIVE STAY-ALIVE BOOSTER (FIXED) 🔥
{Fore.WHITE}
   [STATUS] Suche Room-ID mit Multi-Grabber...
''')

class KAITO_STAY_ALIVE_FIXED():
    def __init__(self):
        self.dn, self.bad = 0, 0
        self.lock = threading.Lock()
        
        # 1. Daten laden
        self.bot_data = self.load_bot_data("session.txt", "accounts.txt")
        if not self.bot_data:
            print(f"{Fore.RED}[!] Keine Sessions gefunden. Abbruch.")
            exit()

        # 2. Inputs
        self.usersa = input(" « + » Target Username (ohne @) : ").strip().replace('@', '')
        self.hits_per_loop = int(input(' « ? » Hits pro Durchgang : '))
        self.threads_max = int(input(' « ? » Threads : '))
        
        self.room = None
        self.get_roomid_ultra()

    def load_bot_data(self, session_file, account_file):
        sessions = []
        accounts = []
        if os.path.exists(session_file):
            with open(session_file, "r") as f:
                sessions = [line.strip().split(':')[0] for line in f if line.strip()]
        if os.path.exists(account_file):
            with open(account_file, "r") as f:
                for line in f:
                    parts = line.strip().split(':')
                    accounts.append(parts[2] if len(parts) >= 3 else "Unknown")
        
        combined = []
        for sess, acc in zip(sessions, accounts):
            combined.append({"session": sess, "username": acc})
        return combined

    def get_roomid_ultra(self):
        """Versucht die Room-ID über mehrere Wege zu finden"""
        print(f"{Fore.YELLOW}[*] Starte ID-Suche für @{self.usersa}...")
        
        # Header für alle Anfragen
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "Accept": "text/html,application/json",
            "Referer": "https://www.tiktok.com/"
        }

        # Methode 1: Offizielle API (mit Session)
        try:
            sess = self.bot_data[0]['session']
            api_headers = headers.copy()
            api_headers["Cookie"] = f"sessionid={sess}"
            url = f"https://www.tiktok.com/api-live/user/room/?aid=1988&uniqueId={self.usersa}"
            res = requests.get(url, headers=api_headers, timeout=10).json()
            self.room = res.get("data", {}).get("user", {}).get("roomId")
            if self.room:
                print(f"{Fore.GREEN}[+] Methode 1 (API) erfolgreich: {self.room}")
                return
        except: pass

        # Methode 2: HTML Quelltext Scraper (Günstiger für IPs)
        try:
            url = f"https://www.tiktok.com/@{self.usersa}/live"
            html = requests.get(url, headers=headers, timeout=10).text
            
            # Suche nach verschiedenen RoomID-Mustern im HTML
            match = re.search(r'room_id=(\d+)', html)
            if not match:
                match = re.search(r'"roomId":"(\d+)"', html)
            if not match:
                match = re.search(r'\"roomid\":\"(\d+)\"', html.lower())
                
            if match:
                self.room = match.group(1)
                print(f"{Fore.GREEN}[+] Methode 2 (Scraper) erfolgreich: {self.room}")
                return
        except: pass

        # Methode 3: JSON-Meta-Daten Fallback
        try:
            url = f"https://www.tiktok.com/@{self.usersa}"
            html = requests.get(url, headers=headers, timeout=10).text
            match = re.search(r'\"roomId\":\"(\d+)\"', html)
            if match:
                self.room = match.group(1)
                print(f"{Fore.GREEN}[+] Methode 3 (Meta) erfolgreich: {self.room}")
                return
        except: pass

        if not self.room:
            print(f"{Fore.RED}[!] FEHLER: Stream wird als OFFLINE angezeigt.")
            print(f"{Fore.WHITE}Tipp: Prüfe ob @{self.usersa} wirklich live ist oder ob deine IP geblockt wurde.")
            exit()

    def send_stay_alive_enter(self, bot_info):
        sess = bot_info["session"]
        user = bot_info["username"]
        
        # Frische Hardware-IDs für jeden Hit
        did = str(random.randint(1000000000000000000, 9999999999999999999))
        iid = str(random.randint(1000000000000000000, 9999999999999999999))
        
        headers = {
            "Cookie": f"sessionid={sess};",
            "User-Agent": generate_user_agent(),
            "Accept": "*/*",
        }

        params = {
            "aid": "1988",
            "device_id": did,
            "install_id": iid,
            "room_id": self.room,
            "device_platform": "android",
            "app_name": "tiktok_web",
            "identity_type": "0"
        }

        try:
            url = "https://webcast.tiktok.com/webcast/room/enter/?" + "&".join([f"{k}={v}" for k, v in params.items()])
            resp = requests.post(url, headers=headers, timeout=7)
            
            if '"status_code":0' in resp.text:
                with self.lock:
                    self.dn += 1
                    print(f'[{Fore.CYAN}LIVE{Fore.RESET}] {Fore.GREEN}@{user}{Fore.WHITE} joined! Total: {self.dn}')
            else:
                with self.lock: self.bad += 1
        except:
            with self.lock: self.bad += 1

    def start_endless(self):
        print(f"\n{Fore.MAGENTA}>>> STAY ALIVE AKTIVIERT <<<\n")
        while True:
            threads = []
            for i in range(self.hits_per_loop):
                current_bot = self.bot_data[i % len(self.bot_data)]
                while threading.active_count() > self.threads_max:
                    sleep(0.01)
                t = threading.Thread(target=self.send_stay_alive_enter, args=(current_bot,))
                t.start()
                threads.append(t)
            
            for t in threads:
                t.join()
            sleep(0.5)

if __name__ == '__main__':
    bot = KAITO_STAY_ALIVE_FIXED()
    bot.start_endless()
