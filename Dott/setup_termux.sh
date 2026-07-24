#!/data/data/com.termux/files/usr/bin/bash

echo "╔══════════════════════════════════════════════╗"
echo "║   DOTT PENTEST SUITE – TERMUX INSTALL       ║"
echo "╚══════════════════════════════════════════════╝"

echo "[*] System-Update..."
pkg update -y && pkg upgrade -y

echo "[*] Installiere Basispakete..."
pkg install -y python python-pip git termux-api \
    bluez bluez-tools libbluetooth-dev \
    openssl clang binutils nmap curl wget

echo "[*] Installiere Python-Module..."
pip install --upgrade pip
pip install requests colorama bleak urllib3

echo "[*] Klone Repository..."
git clone https://github.com/your-repo/dott-pentest.git ~/dott-pentest
cd ~/dott-pentest

echo "[*] Token-Datei anlegen..."
echo "" > ~/.dott_token.txt

echo ""
echo "✅ Installation abgeschlossen!"
echo ""
echo "JETZT AUSFÜHREN:"
echo "  cd ~/dott-pentest"
echo "  python3 dott_pentest.py --termux-setup"
echo "  python3 dott_pentest.py --auto-token --city berlin --fuzz"
echo ""
echo "FÜR BLE:"
echo "  termux-bluetooth-scan   # Bluetooth-Scanner testen"
echo "  python3 dott_pentest.py --ble-scan"
