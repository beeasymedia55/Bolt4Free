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
   🚀 TIKTOK LIVE VIEWER BOOSTER 🚀
{Fore.WHITE}
   [!] Nutzt Sessions + Random Hardware IDs
   [!] Endpunkt: webcast/room/enter
''')

class KAITO_VIEWER():
    def __init__(self):
        self.dn, self.bad = 0, 0
        self.lock = threading.Lock()
        
        # Lade Sessions (für "Authentic Views")
        self.sessions = self.load_list("session.txt")
        
        if not self.sessions:
            print(f"{Fore.YELLOW}[!] Keine session.txt gefunden. Nutze reinen Gast-Modus.")
            self.sessions = [None] # Gast-Modus ermöglichen

        self.usersa = input(" « + » Target Username (ohne @) : ").strip()
        self.amount = int(input(' « ? » Wie viele "Enter"-Events senden? '))
        self.threads_max = int(input(' « ? » Threads (Empfohlen: 50-100): '))
        
        self.room = None
        self.get_roomid()

    def load_list(self, filename):
        if os.path.exists(filename):
            with open(filename, "r") as f:
                return [line.strip().split(':')[0] for line in f if line.strip()]
        return []

    def get_roomid(self):
        """Hole Room-ID (Nutzt erste Session oder Gast-Request)"""
        sess = self.sessions[0] if self.sessions[0] else ""
        headers = {
            "Cookie": f"sessionid={sess};" if sess else "",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        }
        url = f"https://www.tiktok.com/api-live/user/room/?aid=1988&uniqueId={self.usersa}"
        try:
            res = requests.get(url, headers=headers).json()
            self.room = res["data"]["user"]["roomId"]
            print(f"{Fore.GREEN}[+] Target Room ID: {self.room}")
        except:
            print(f"{Fore.RED}[!] Konnte Room ID nicht finden. Ist der User live?")
            exit()

    def send_enter(self, session_id=None):
        """Simuliert das Betreten des Raums mit neuen IDs"""
        # Generiere zufällige Hardware-IDs für jeden Viewer
        device_id = str(random.randint(7000000000000000000, 7999999999999999999))
        install_id = str(random.randint(7000000000000000000, 7999999999999999999))
        
        headers = {
            "User-Agent": generate_user_agent(),
            "Accept-Encoding": "gzip, deflate",
            "Accept": "*/*",
            "Connection": "keep-alive",
        }
        
        if session_id:
            headers["Cookie"] = f"sessionid={session_id};"

        # Parameter für den Room-Enter
        params = {
            "aid": "1988", # Webcast API ID
            "app_name": "tiktok_web",
            "device_id": device_id,
            "device_platform": "android",
            "install_id": install_id,
            "room_id": self.room,
            "identity_type": "0", # 0 = Gast/Zuschauer
            "last_install_time": str(int(time()))
        }

        try:
            url = "https://webcast.tiktok.com/webcast/room/enter/?" + "&".join([f"{k}={v}" for k, v in params.items()])
            
            # Post-Request ohne Payload (nur Params)
            resp = requests.post(url, headers=headers, timeout=10)
            
            if '"status_code":0' in resp.text:
                with self.lock:
                    self.dn += 1
                    print(f'\r[{Fore.CYAN}VIEW{Fore.RESET}] {Fore.GREEN}Join Success [{self.dn}] {Fore.WHITE}| {Fore.RED}Fail [{self.bad}]', end='')
            else:
                with self.lock:
                    self.bad += 1
        except:
            with self.lock:
                self.bad += 1

    def start(self):
        print(f"{Fore.YELLOW}[*] Starte Viewer-Boost für {self.usersa}...")
        threads = []
        for i in range(self.amount):
            # Nutzt abwechselnd vorhandene Sessions und Gast-Modus
            current_sess = self.sessions[i % len(self.sessions)]
            
            while threading.active_count() > self.threads_max:
                sleep(0.05)
            
            t = threading.Thread(target=self.send_enter, args=(current_sess,))
            t.start()
            threads.append(t)
            
        for t in threads:
            t.join()
        print(f"\n\n{Fore.GREEN}[FERTIG] Alle Enter-Signale gesendet.")

if __name__ == '__main__':
    bot = KAITO_VIEWER()
    bot.start()
