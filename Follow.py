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
{Fore.LIGHTMAGENTA_EX}
   👤 AUTO FOLLOW BOT 👤
{Fore.CYAN}
░▀▄░░▄▀
▄▄▄██▄▄▄▄▄░▀█▀▐░▌
█▒░▒░▒░█▀█░░█░▐░▌
█░▒░▒░▒█▀█░░█░░█
█▄▄▄▄▄▄███══════
{Fore.YELLOW}
  MODUS: ACCOUNT FOLLOWERS (AUTO-SESSION)
''')

class KAITO_FOLLOWER():
    def __init__(self):
        self.dn, self.bad = 0, 0
        self.lock = threading.Lock()
        
        # Sessions laden
        self.sessions = self.load_list("session.txt")
        
        if not self.sessions:
            print(f"{Fore.RED}[!] session.txt leer oder fehlt!")
            exit()

        self.usersa = input(" « + » Target Username (ohne @) : ").strip()
        self.amount = int(input(' « ? » Wie viele Follows senden? '))
        
        self.target_id = None
        self.sec_uid = ""
        
        self.get_user_info()

    def load_list(self, filename):
        if os.path.exists(filename):
            with open(filename, "r") as f:
                # Extrahiert den session_key (erster Teil vor dem Doppelpunkt)
                return [line.strip().split(':')[0] for line in f if line.strip()]
        return []

    def get_user_info(self):
        """Grabber für User-ID und Sec-Uid anhand des Usernames"""
        print(f"{Fore.YELLOW}[*] Suche IDs für @{self.usersa}...")
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        
        try:
            # Profilseite abrufen
            url = f"https://www.tiktok.com/@{self.usersa}"
            response = requests.get(url, headers=headers, timeout=15)
            html = response.text
            
            # User ID extrahieren
            id_match = re.search(r'"userInfo":\{"user":\{"id":"(\d+)"', html) or re.search(r'"userId":"(\d+)"', html) or re.search(r'"author_id":"(\d+)"', html)
            # Sec-Uid extrahieren
            sec_match = re.search(r'"secUid":"(.*?)"', html)
            
            if id_match:
                self.target_id = id_match.group(1)
                self.sec_uid = sec_match.group(1) if sec_match else ""
                print(f"{Fore.GREEN}[+] User ID gefunden: {self.target_id}")
            else:
                print(f"{Fore.RED}[!] User ID konnte nicht gefunden werden. Ist der Username korrekt?")
                exit(0)
                
        except Exception as e:
            print(f"{Fore.RED}[!] Fehler beim Laden der Profil-Daten: {e}")
            exit(0)

    def sent_follow(self, session_id):
        """Follow Endpoint Logik"""
        device_id = str(random.randint(1000000000000000000, 9999999999999999999))
        
        headers = {
            "Cookie": f"sessionid={session_id};",
            "User-Agent": "com.ss.android.ugc.trill/2613 (Linux; U; Android 12; en_US; Pixel 6 Pro)",
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        try:
            # Endpunkt für Follows (type=1 bedeutet Follow, type=0 wäre Unfollow)
            # aid=1233 ist die Standard TikTok Mobile App ID
            url = (f"https://api16-normal-c-useast1a.tiktokv.com/aweme/v1/commit/follow/user/?"
                   f"user_id={self.target_id}&sec_user_id={self.sec_uid}&type=1&"
                   f"device_id={device_id}&aid=1233&channel=googleplay")
            
            req = requests.post(url, headers=headers, timeout=10)
            
            # Erfolg prüfen (TikTok API gibt meist status_code: 0 bei Erfolg zurück)
            if req and '"status_code":0' in req.text:
                with self.lock:
                    self.dn += 1
                    print(f'\r[{Fore.LIGHTMAGENTA_EX}👤{Fore.RESET}] {Fore.GREEN}Followed [{self.dn}] {Fore.WHITE}| {Fore.RED}Fail [{self.bad}] {Fore.CYAN}| Target: @{self.usersa}', end='')
            else:
                with self.lock:
                    self.bad += 1
        except:
            with self.lock:
                self.bad += 1

    def start(self):
        threads = []
        for i in range(self.amount):
            # Session Rotation (Verteilt die Follows auf deine Accounts)
            current_sess = self.sessions[i % len(self.sessions)]
            
            while threading.active_count() > 100:
                sleep(0.1)
            
            t = threading.Thread(target=self.sent_follow, args=(current_sess,))
            t.start()
            threads.append(t)
            
        for t in threads:
            t.join()
        print(f"\n\n{Fore.GREEN}[FERTIG] Alle Follows gesendet.")

if __name__ == '__main__':
    bot = KAITO_FOLLOWER()
    bot.start()
