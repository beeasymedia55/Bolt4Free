import requests
from user_agent import generate_user_agent
from time import time, sleep
import random
from colorama import init, Fore
import threading
import os

init(autoreset=True)

print(f'''
{Fore.CYAN}
░▀▄░░▄▀
▄▄▄██▄▄▄▄▄░▀█▀▐░▌
█▒░▒░▒░█▀█░░█░▐░▌
█░▒░▒░▒█▀█░░█░░█
█▄▄▄▄▄▄███══════
{Fore.YELLOW}
  LIVE SHARE BOT - AUTO SESSION MODE
''')

class KAITO_AUTO():
    def __init__(self):
        self.dn, self.bad = 0, 0
        self.lock = threading.Lock()
        
        # Lade Daten aus deinen .txt Dateien
        self.sessions = self.load_list("session.txt")
        self.accounts = self.load_list("accounts.txt")
        
        if not self.sessions:
            print(f"{Fore.RED}[!] Keine Sessions in session.txt gefunden!")
            exit()

        self.usersa = input(" « + » Target Username : ")
        self.amount = int(input(' « ? » Wie viele Shares insgesamt? '))
        
        self.Channel = ["tiktok_web", "googleplay", "App%20Store"]
        self.Platforms = ["android", "windows", "iphone", "web", "web_pc"]
        
        # Hole Room ID (Original Logik aus Share-Live.py)
        self.get_roomid()

    def load_list(self, filename):
        if os.path.exists(filename):
            with open(filename, "r") as f:
                return [line.strip() for line in f if line.strip()]
        return []

    def get_roomid(self):
        # Nutzt die erste verfügbare Session für den Grabber
        sess_data = self.sessions[0].split(':')
        session_id = sess_data[0]
        
        headers = {
            "Cookie": f"sessionid={session_id};",
            "User-Agent": generate_user_agent(),
            "Accept": "*/*",
            "Referer": f"https://www.tiktok.com/@{self.usersa}/live",
        }
        url = f"https://www.tiktok.com/api-live/user/room/?aid=1988&uniqueId={self.usersa}"
        try:
            rez = requests.get(url, headers=headers).json()
            self.room = rez["data"]["user"]["roomId"]
            print(f"{Fore.GREEN}[+] Room ID gefunden: {self.room}")
        except:
            print(f"{Fore.RED}[!] Room ID konnte nicht geladen werden. Ist der User live?")
            exit(0)

    def sent_share(self, session_id):
        device_id = str(random.randint(1000000000000000000, 9999999999999999999))
        
        # Original Headers & Cookies aus Share-Live.py
        Headers = {
            "Cookie": f"sessionid={session_id};",
            "User-Agent": generate_user_agent(),
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Connection": "close",
        }
        
        try:
            platform = random.choice(self.Platforms)
            appName = random.choice(["tiktok_web", "musically_go"])
            osVersion = random.randint(1, 12)
            channelLol = random.choice(self.Channel)
            
            # Original Endpoint
            url = (f"https://webcast.tiktok.com/webcast/room/share/?"
                   f"aid=1988&app_name={appName}&device_id={device_id}&"
                   f"device_platform={platform}&room_id={self.room}&share_type=2")
            
            req = requests.post(url, headers=Headers, timeout=10)
            
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
        # Verteile Shares auf die verfügbaren Sessions
        for i in range(self.amount):
            # Nutzt Sessions rotierend aus der session.txt
            current_sess = self.sessions[i % len(self.sessions)].split(':')[0]
            
            while threading.active_count() > 200: # Max Threads
                sleep(0.1)
            
            t = threading.Thread(target=self.sent_share, args=(current_sess,))
            t.start()
            threads.append(t)
            
        for t in threads:
            t.join()
        print(f"\n\n{Fore.GREEN}Fertig! {self.dn} Shares gesendet.")

if __name__ == '__main__':
    bot = KAITO_AUTO()
    bot.start()
