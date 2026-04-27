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
░▀▄░░▄▀
▄▄▄██▄▄▄▄▄░▀█▀▐░▌
█▒░▒░▒░█▀█░░█░▐░▌
█░▒░▒░▒█▀█░░█░░█
█▄▄▄▄▄▄███══════
{Fore.YELLOW}
  LIVE SHARE BOT - FIX VERSION (AUTO-SESSION)
''')

class KAITO_FIX():
    def __init__(self):
        self.dn, self.bad = 0, 0
        self.lock = threading.Lock()
        
        # Sessions laden
        self.sessions = self.load_list("session.txt")
        
        if not self.sessions:
            print(f"{Fore.RED}[!] session.txt nicht gefunden oder leer!")
            exit()

        self.usersa = input(" « + » Target Username (ohne @) : ").strip()
        self.amount = int(input(' « ? » Wie viele Shares insgesamt? '))
        
        self.Channel = ["tiktok_web", "googleplay", "App%20Store"]
        self.Platforms = ["android", "windows", "iphone", "web", "web_pc"]
        
        self.room = None
        self.get_roomid()

    def load_list(self, filename):
        if os.path.exists(filename):
            with open(filename, "r") as f:
                # Extrahiert den ersten Teil (sessionid) vor dem Doppelpunkt
                return [line.strip().split(':')[0] for line in f if line.strip()]
        return []

    def get_roomid(self):
        """Verbesserter Grabber mit Fehlerprüfung"""
        # Wir versuchen es mit der ersten Session
        session_id = self.sessions[0]
        
        headers = {
            "Cookie": f"sessionid={session_id};",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Referer": f"https://www.tiktok.com/@{self.usersa}/live",
        }
        
        url = f"https://www.tiktok.com/api-live/user/room/?aid=1988&uniqueId={self.usersa}"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.text:
                rez = response.json()
                # Sicherheitscheck: Existieren die Keys 'data' und 'user'?
                if rez.get("data") and rez["data"].get("user"):
                    self.room = rez["data"]["user"].get("roomId")
            
            # Fallback auf Regex, falls API fehlschlägt oder roomId fehlt
            if not self.room:
                print(f"{Fore.YELLOW}[*] API leer, versuche HTML-Regex...")
                html_resp = requests.get(f"https://www.tiktok.com/@{self.usersa}/live", headers=headers, timeout=10)
                room_match = re.search(r'room_id=(\d+)', html_resp.text) or re.search(r'"roomId":"(\d+)"', html_resp.text)
                if room_match:
                    self.room = room_match.group(1)

            if self.room:
                print(f"{Fore.GREEN}[+] Room ID erfolgreich: {self.room}")
            else:
                print(f"{Fore.RED}[!] Room ID konnte nicht gefunden werden. User offline oder Session tot.")
                exit(0)
                
        except Exception as e:
            print(f"{Fore.RED}[!] Kritischer Fehler beim Grabbing: {e}")
            exit(0)

    def sent_share(self, session_id):
        device_id = str(random.randint(1000000000000000000, 9999999999999999999))
        headers = {
            "Cookie": f"sessionid={session_id};",
            "User-Agent": generate_user_agent(),
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        
        try:
            platform = random.choice(self.Platforms)
            appName = random.choice(self.Channel)
            
            url = (f"https://webcast.tiktok.com/webcast/room/share/?"
                   f"aid=1988&app_name={appName}&device_id={device_id}&"
                   f"device_platform={platform}&room_id={self.room}&share_type=2")
            
            req = requests.post(url, headers=headers, timeout=7)
            
            if req and '"status_code":0' in req.text:
                with self.lock:
                    self.dn += 1
                    print(f'\r[{Fore.MAGENTA}${Fore.RESET}] {Fore.GREEN}Done [{self.dn}] {Fore.WHITE}| {Fore.RED}Fail [{self.bad}] {Fore.CYAN}| Target: {self.usersa}', end='')
            else:
                with self.lock:
                    self.bad += 1
        except:
            with self.lock:
                self.bad += 1

    def start(self):
        threads = []
        for i in range(self.amount):
            # Session Rotation
            current_sess = self.sessions[i % len(self.sessions)]
            
            while threading.active_count() > 100:
                sleep(0.1)
            
            t = threading.Thread(target=self.sent_share, args=(current_sess,))
            t.start()
            threads.append(t)
            
        for t in threads:
            t.join()
        print(f"\n\n{Fore.GREEN}[FERTIG] Prozess beendet.")

if __name__ == '__main__':
    bot = KAITO_FIX()
    bot.start()
