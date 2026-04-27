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
  LIVE SHARE BOT - ORIGINAL LOGIC (AUTO-SESSION)
''')

class KAITO_UNCUT():
    def __init__(self):
        self.dn, self.bad = 0, 0
        self.lock = threading.Lock()
        
        # Lade Sessions aus session.txt (Format: session_key:x_tt_token:tm_token)
        self.sessions = self.load_list("session.txt")
        
        if not self.sessions:
            print(f"{Fore.RED}[!] session.txt nicht gefunden oder leer!")
            exit()

        self.usersa = input(" « + » Target Username (ohne @) : ")
        self.amount = int(input(' « ? » Wie viele Shares insgesamt? '))
        
        self.Channel = ["tiktok_web", "googleplay", "App%20Store"]
        self.Platforms = ["android", "windows", "iphone", "web", "web_pc"]
        
        # Room ID mit der ersten gültigen Session laden
        self.get_roomid()

    def load_list(self, filename):
        if os.path.exists(filename):
            with open(filename, "r") as f:
                # Extrahiert nur den Session-Key (erster Teil vor dem Doppelpunkt)
                return [line.strip().split(':')[0] for line in f if line.strip()]
        return []

    def get_roomid(self):
        """Originaler Grabber aus Share-Live.py mit deiner Session-Logik"""
        session_id = self.sessions[0]
        
        headers = {
            "Cookie": f"sessionid={session_id};",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
            "Accept": "*/*",
            "Referer": f"https://www.tiktok.com/@{self.usersa}/live",
        }
        
        # Originaler Endpunkt aus Share-Live.py
        url = f"https://www.tiktok.com/api-live/user/room/?aid=1988&uniqueId={self.usersa}"
        
        try:
            response = requests.get(url, headers=headers)
            rez = response.json()
            if "data" in rez and "user" in rez["data"]:
                self.room = rez["data"]["user"]["roomId"]
                print(f"{Fore.GREEN}[+] Room ID gefunden: {self.room}")
            else:
                # Falls die API-Antwort anders strukturiert ist (Fallback auf Regex)
                print(f"{Fore.YELLOW}[*] API-Check fehlgeschlagen, versuche Regex-Grabber...")
                html = requests.get(f"https://www.tiktok.com/@{self.usersa}/live", headers=headers).text
                room_id = re.search(r'room_id=(\d+)', html) or re.search(r'"roomId":"(\d+)"', html)
                if room_id:
                    self.room = room_id.group(1)
                    print(f"{Fore.GREEN}[+] Room ID via Regex gefunden: {self.room}")
                else:
                    raise Exception("User ist nicht live")
        except Exception as e:
            print(f"{Fore.RED}[!] Fehler: {e}. Ist der User online?")
            exit(0)

    def sent_share(self, session_id):
        """Originale Share-Logik aus Share-Live.py"""
        device_id = str(random.randint(1000000000000000000, 9999999999999999999))
        
        headers = {
            "Cookie": f"sessionid={session_id};",
            "User-Agent": generate_user_agent(),
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Connection": "close",
        }
        
        try:
            platform = random.choice(self.Platforms)
            appName = random.choice(self.Channel)
            
            # Originaler Share-Endpunkt
            url = (f"https://webcast.tiktok.com/webcast/room/share/?"
                   f"aid=1988&app_name={appName}&device_id={device_id}&"
                   f"device_platform={platform}&room_id={self.room}&share_type=2")
            
            req = requests.post(url, headers=headers, timeout=10)
            
            if '"status_code":0' in req.text:
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
            # Rotiert durch die Sessions aus deiner Datei
            current_sess = self.sessions[i % len(self.sessions)]
            
            # Thread-Limitierung wie im Original
            while threading.active_count() > 150:
                sleep(0.1)
            
            t = threading.Thread(target=self.sent_share, args=(current_sess,))
            t.start()
            threads.append(t)
            
        for t in threads:
            t.join()
        print(f"\n\n{Fore.GREEN}[FINISH] {self.dn} Shares erfolgreich gesendet!")

if __name__ == '__main__':
    bot = KAITO_UNCUT()
    bot.start()
