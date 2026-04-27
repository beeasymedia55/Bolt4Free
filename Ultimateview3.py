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
   🔥 TIKTOK LIVE STAY-ALIVE BOOSTER 🔥
{Fore.WHITE}
   [MODUS] Endlosschleife / Stay Alive
   [INFO] Zeigt aktiven Account-Join an
''')

class KAITO_STAY_ALIVE():
    def __init__(self):
        self.dn, self.bad = 0, 0
        self.lock = threading.Lock()
        
        # 1. Daten laden und verknüpfen
        self.bot_data = self.load_bot_data("session.txt", "accounts.txt")
        if not self.bot_data:
            print(f"{Fore.RED}[!] session.txt oder accounts.txt fehlt!")
            exit()

        # 2. Inputs
        self.usersa = input(" « + » Target Username (ohne @) : ").strip().replace('@', '')
        self.hits_per_loop = int(input(' « ? » Hits pro Durchgang : '))
        self.threads_max = int(input(' « ? » Threads (Gleichzeitig) : '))
        
        self.room = None
        self.get_roomid()

    def load_bot_data(self, session_file, account_file):
        """Koppelt Session-Key mit dem Usernamen aus der Datei"""
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

    def get_roomid(self):
        """Hole Room-ID für das Ziel"""
        print(f"{Fore.YELLOW}[*] Verbinde mit Stream von {self.usersa}...")
        headers = {
            "Cookie": f"sessionid={self.bot_data[0]['session']};",
            "User-Agent": generate_user_agent(),
        }
        url = f"https://www.tiktok.com/api-live/user/room/?aid=1988&uniqueId={self.usersa}"
        try:
            res = requests.get(url, headers=headers, timeout=10).json()
            self.room = res["data"]["user"]["roomId"]
            print(f"{Fore.GREEN}[+] Raum gefunden! ID: {self.room}")
        except:
            print(f"{Fore.RED}[!] Stream nicht gefunden. Offline?")
            exit()

    def send_stay_alive_enter(self, bot_info):
        """Sendet das Enter-Signal für einen spezifischen Account"""
        sess = bot_info["session"]
        user = bot_info["username"]
        
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
                    print(f'[{Fore.CYAN}LIVE{Fore.RESET}] {Fore.GREEN}Account {Fore.YELLOW}@{user}{Fore.GREEN} joined! | Total Hits: {self.dn}')
            else:
                with self.lock:
                    self.bad += 1
        except:
            with self.lock:
                self.bad += 1

    def start_endless(self):
        """Startet die Endlosschleife"""
        print(f"\n{Fore.MAGENTA}>>> STAY ALIVE AKTIVIERT (Strg+C zum Beenden) <<<\n")
        
        loop_count = 0
        while True:
            loop_count += 1
            threads = []
            
            # Ein Batch von "Hits" abarbeiten
            for i in range(self.hits_per_loop):
                current_bot = self.bot_data[i % len(self.bot_data)]
                
                while threading.active_count() > self.threads_max:
                    sleep(0.05)
                
                t = threading.Thread(target=self.send_stay_alive_enter, args=(current_bot,))
                t.start()
                threads.append(t)
            
            for t in threads:
                t.join()
            
            print(f"{Fore.BLUE}[INFO] Loop {loop_count} beendet. Starte nächsten Batch...")
            sleep(1) # Kurze Pause zwischen den Batches zum Schutz der IP

if __name__ == '__main__':
    bot = KAITO_STAY_ALIVE()
    bot.start_endless()
