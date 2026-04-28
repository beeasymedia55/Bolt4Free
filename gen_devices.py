import random
import string
import os

def gen_id(length):
    return ''.join(random.choices(string.digits, k=length))

def gen_hex(length):
    return ''.join(random.choices("0123456789abcdef", k=length))

def generate_device_line():
    # did: Device ID (19 Stellen)
    did = gen_id(19)
    # iid: Install ID (19 Stellen)
    iid = gen_id(19)
    # cdid: Client Device ID (UUID Format / 36 Zeichen)
    cdid = f"{gen_hex(8)}-{gen_hex(4)}-{gen_hex(4)}-{gen_hex(4)}-{gen_hex(12)}"
    # openudid: Open User ID (16 Zeichen hex)
    udid = gen_hex(16)
    
    return f"{did}:{iid}:{cdid}:{udid}"

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("--- TikTok Device Generator ---")
    try:
        count = int(input("Wie viele Devices möchtest du generieren? "))
    except:
        count = 10

    with open("devices.txt", "a") as f:
        for _ in range(count):
            line = generate_device_line()
            f.write(line + "\n")
            print(f"[+] Generiert: {line[:20]}...")

    print(f"\n[ Fertig! {count} Devices wurden zu devices.txt hinzugefügt. ]")

if __name__ == "__main__":
    main()
