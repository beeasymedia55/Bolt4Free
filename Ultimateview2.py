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
   [FIXED INPUT & ID LOGIC]
''')

class KAITO_VIEWER_FIX():
    def __init__(self):
        self.dn, self.bad = 0, 0
        self.lock = threading.Lock()
        
        # 1. Zuerst die Inputs abfragen (bevor Dateien geladen werden)
        print(f"{Fore.YELLOW}--- EINSTELLUNGEN ---")
        self.usersa = input(" « + » Target Username (ohne @) : ").strip().replace('@', '')
        self.amount = int(input(' « ? » Wie viele Enter-Signale? '))
        self.threads_max = int(input(' « ? » Threads (1-100): '))
        
        # 2. Dateien laden
        self.sessions = self.load_list("session.txt")
        if not self.sessions:
            print(f"{Fore.YELLOW}[!] session.txt leer. Nutze Gast-Modus (Random IDs).")
            self.sessions = [None]

        self.room = None
        self.get_roomid()

    def load_list(self, filename):
        try:
            if os.path.exists(filename):
                with open(filename, "r") as f:
                    # Extrahiert nur den session_key
                    return [line.strip().split(':')[0] for line in f if line.strip()]
            return []
        except Exception as e:
            print(f"Fehler beim Laden von {filename}: {e}")
            return []

    def get_roomid(self):
        """Hole Room-ID mit Hilfe der Web-API"""
        print(f"{Fore.YELLOW}[*] Suche Room ID für {self.usersa}...")
        
        # Session für den Grabber nutzen falls vorhanden
        sess = self.sessions[0] if self.sessions[0] else ""
        headers = {
            "Cookie": f"sessionid={sess};" if sess else "",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
        }
        
        url = f"https://www.tiktok.com/api-live/user/room/?aid=1988&uniqueId={self.usersa}"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.text:
                res = response.json()
                if res.get("data") and res["data"].get("user"):
                    self.room = res["data"]["user"].get("roomId")
            
            # Regex Fallback falls JSON fehlschlägt
            if not self.room:
                html = requests.get(f"https://www.tiktok.com/@{self.usersa}/live", headers=headers).text
                match = re.search(r'room_id=(\d+)', html) or re.search(r'"roomId":"(\d+)"', html)
                if match:
                    self.room = match.group(1)

            if self.room:
                print(f"{Fore.GREEN}[+] Room ID gefunden: {self.room}")
            else:
                print(f"{Fore.RED}[!] Konnte Room ID nicht finden. Ist der User live?")
                exit()
        except Exception as e:
            print(f"{Fore.RED}[!] Fehler beim Grabbing: {e}")
            exit()

    def send_enter(self, session_id):
        """Simuliert das Join-Event"""
        # Generiere immer frische IDs für maximale Viewer-Zählung
        did = str(random.randint(1000000000000000000, 9999999999999999999))
        iid = str(random.randint(1000000000000000000, 9999999999999999999))
        
        headers = {
            "User-Agent": generate_user_agent(),
            "Accept": "*/*",
            "Connection": "keep-alive",
        }
        if session_id:
            headers["Cookie"] = f"sessionid={session_id};"

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
                    print(f'\r[{Fore.CYAN}BOOST{Fore.RESET}] {Fore.GREEN}Viewer Sent [{self.dn}] {Fore.WHITE}| {Fore.RED}Error [{self.bad}]', end='')
            else:
                with self.lock:
                    self.bad += 1
        except:
            with self.lock:
                self.bad += 1

    def start(self):
        print(f"\n{Fore.MAGENTA}[*] Boosting gestartet...")
        threads = []
        for i in range(self.amount):
            # Nutzt Sessions falls vorhanden, sonst Gast
            current_sess = self.sessions[i % len(self.sessions)]
            
            while threading.active_count() > self.threads_max:
                sleep(0.01)
            
            t = threading.Thread(target=self.send_enter, args=(current_sess,))
            t.start()
            threads.append(t)
            
        for t in threads:
            t.join()
        print(f"\n\n{Fore.GREEN}[FERTIG] Prozess beendet.")

if __name__ == '__main__':
    try:
        bot = KAITO_VIEWER_FIX()
        bot.start()
    except KeyboardInterrupt:
        exit()
    except Exception as e:
        print(f"Fehler: {e}")
