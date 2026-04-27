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
{Fore.LIGHTRED_EX}
   ❤ LIVE LIKE BOT ❤
{Fore.CYAN}
░▀▄░░▄▀
▄▄▄██▄▄▄▄▄░▀█▀▐░▌
█▒░▒░▒░█▀█░░█░▐░▌
█░▒░▒░▒█▀█░░█░░█
█▄▄▄▄▄▄███══════
{Fore.YELLOW}
  MODUS: LIVE LIKES (AUTO-SESSION)
''')

class KAITO_LIKER():
    def __init__(self):
        self.dn, self.bad = 0, 0
        self.lock = threading.Lock()
        
        # Sessions laden (Format aus Acc3main.py)
        self.sessions = self.load_list("session.txt")
        
        if not self.sessions:
            print(f"{Fore.RED}[!] session.txt leer oder fehlt!")
            exit()

        self.usersa = input(" « + » Target Username (ohne @) : ").strip()
        self.amount = int(input(' « ? » Wie viele Like-Pakete senden? '))
        
        self.Platforms = ["android", "windows", "iphone", "web"]
        self.room = None
        self.get_roomid()

    def load_list(self, filename):
        if os.path.exists(filename):
            with open(filename, "r") as f:
                return [line.strip().split(':')[0] for line in f if line.strip()]
        return []

    def get_roomid(self):
        """Original Grabber Logik"""
        session_id = self.sessions[0]
        headers = {
            "Cookie": f"sessionid={session_id};",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
            "Referer": f"https://www.tiktok.com/@{self.usersa}/live",
        }
        url = f"https://www.tiktok.com/api-live/user/room/?aid=1988&uniqueId={self.usersa}"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            rez = response.json()
            if rez.get("data") and rez["data"].get("user"):
                self.room = rez["data"]["user"].get("roomId")
            
            if not self.room: # Regex Fallback
                html = requests.get(f"https://www.tiktok.com/@{self.usersa}/live", headers=headers).text
                match = re.search(r'room_id=(\d+)', html) or re.search(r'"roomId":"(\d+)"', html)
                if match: self.room = match.group(1)

            if self.room:
                print(f"{Fore.GREEN}[+] Room ID: {self.room}")
            else:
                print(f"{Fore.RED}[!] User nicht live oder Session tot.")
                exit(0)
        except Exception as e:
            print(f"{Fore.RED}[!] Error Grabbing: {e}")
            exit(0)

    def sent_like(self, session_id):
        """Umgewandelte Logik von Share zu Like"""
        device_id = str(random.randint(1000000000000000000, 9999999999999999999))
        headers = {
            "Cookie": f"sessionid={session_id};",
            "User-Agent": generate_user_agent(),
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        }
        
        try:
            # Ein Paket von 2-5 Likes pro Request
            count = random.randint(2, 5)
            platform = random.choice(self.Platforms)
            
            # Endpunkt für LIKES
            url = (f"https://webcast.tiktok.com/webcast/room/like/?"
                   f"aid=1988&device_id={device_id}&device_platform={platform}&"
                   f"room_id={self.room}&count={count}")
            
            req = requests.post(url, headers=headers, timeout=7)
            
            if '"status_code":0' in req.text:
                with self.lock:
                    self.dn += count # Zählt die tatsächlichen Likes
                    print(f'\r[{Fore.LIGHTRED_EX}❤{Fore.RESET}] {Fore.GREEN}Likes [{self.dn}] {Fore.WHITE}| {Fore.RED}Errors [{self.bad}] {Fore.CYAN}| Target: {self.usersa}', end='')
            else:
                with self.lock:
                    self.bad += 1
        except:
            with self.lock:
                self.bad += 1

    def start(self):
        threads = []
        for i in range(self.amount):
            current_sess = self.sessions[i % len(self.sessions)]
            
            while threading.active_count() > 100:
                sleep(0.1)
            
            t = threading.Thread(target=self.sent_like, args=(current_sess,))
            t.start()
            threads.append(t)
            
        for t in threads:
            t.join()
        print(f"\n\n{Fore.GREEN}[FERTIG] Alle Likes gesendet.")

if __name__ == '__main__':
    bot = KAITO_LIKER()
    bot.start()
