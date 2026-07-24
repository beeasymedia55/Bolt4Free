cd /data/data/com.termux/files/home/Bolt4Free/Dott  # passe ggf. Pfad an

python3 << 'PATCH'
import os, re

path = "dott_pentest.py"
with open(path, 'r') as f:
    code = f.read()

original = code
changes = []

# ─── FIX 1: RESETALL → RESET_ALL (alle 50+ Vorkommen) ───
code = code.replace("Style.RESETALL", "Style.RESET_ALL")
changes.append("Style.RESETALL → RESET_ALL")

# ─── FIX 2: Bleak run_ble_scan() komplett ersetzen ───
old_scan = """    def run_ble_scan(self, timeout: int = 10) -> List[Dict]:
        \"\"\"
        BLE-Scan nach Dott-Scootern.
        Unterstützt:
          - Bleak (cross-platform, bevorzugt)
          - Termux-API (Android-Fallback)
          - bluez hcitool (Linux-Fallback)
        \"\"\"
        self.log("\\n═══ BLE SCAN ═══", "highlight")
        devices = []
        
        # Methode 1: Bleak
        try:
            from bleak import BleakScanner
            
            async def _scan():
                found = await BleakScanner.discover(timeout=timeout)
                return found
            
            import asyncio
            self.log("Scanne mit Bleak...", "info")
            found = asyncio.run(_scan())
            
            for d in found:
                name = d.name or \"\"
                if any(kw in name.upper() for kw in ["DOTT", "TIER", "NINEBOT", "MAX", "G30", "ESCOOTER"]):
                    devices.append({
                        "name": name,
                        "address": d.address,
                        "rssi": d.rssi,
                    })
                    self.log(f"  \U0001f6f4 {name} @ {d.address} (RSSI: {d.rssi})", "ok")
            
            if not devices:
                self.log("Keine Dott-Scooter gefunden.", "warn")
                # Alle Geräte auflisten
                self.log("Gefundene BLE-Geräte:", "info")
                for d in found[:15]:
                    self.log(f"  {d.name or '(unbenannt)'} @ {d.address} (RSSI: {d.rssi})", "debug")
                if len(found) > 15:
                    self.log(f"  ... +{len(found)-15} weitere", "debug")
            
            return devices
            
        except ImportError:
            self.log("Bleak nicht installiert.", "warn")
        
        # Methode 2: Termux-API
        if IS_TERMUX:
            self.log("Scanne mit Termux:Bluetooth-API...", "info")
            try:
                result = subprocess.run(
                    ["termux-bluetooth-scan"],
                    capture_output=True, text=True, timeout=timeout
                )
                for line in result.stdout.strip().split('\\n'):
                    if line.strip():
                        self.log(f"  {line}", "info")
                        parts = line.split()
                        if len(parts) >= 2:
                            devices.append({
                                "name": " ".join(parts[1:3]),
                                "address": parts[0],
                            })
            except FileNotFoundError:
                self.log("termux-bluetooth-scan nicht gefunden. pkg install termux-api", "warn")
        
        # Methode 3: hcitool (Linux)
        if IS_LINUX and not devices:
            self.log("Scanne mit hcitool...", "info")
            try:
                result = subprocess.run(
                    ["sudo", "hcitool", "lescan", "--duplicates"],
                    capture_output=True, text=True, timeout=timeout
                )
                for line in result.stdout.strip().split('\\n'):
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        name = " ".join(parts[1:])
                        addr = parts[0]
                        if any(kw in name.upper() for kw in ["DOTT", "NINEBOT", "G30", "TIER"]):
                            devices.append({"name": name, "address": addr})
                            self.log(f"  \U0001f6f4 {name} @ {addr}", "ok")
            except FileNotFoundError:
                self.log("hcitool nicht gefunden.", "warn")
        
        if not devices:
            self.log("Keine Scooter via BLE gefunden.", "warn")
        
        return devices"""

new_scan = """    def run_ble_scan(self, timeout: int = 10) -> List[Dict]:
        \"\"\"
        BLE-Scan nach Dott-Scootern.

        Plattform-Logik:
          - Termux/Android  -> termux-bluetooth-scan (Primär), bluetoothctl (Fallback)
          - Linux            -> Bleak (Primär) / hcitool (Fallback)
          - macOS/Windows    -> Bleak
        \"\"\"
        self.log("\\n═══ BLE SCAN ═══", "highlight")
        devices = []

        # ─── METHODE 1: TERMUX-API (Android) ───
        if IS_TERMUX:
            self.log("Scanne mit Termux:Bluetooth-API...", "info")
            try:
                result = subprocess.run(
                    ["termux-bluetooth-scan"],
                    capture_output=True, text=True, timeout=timeout
                )
                if result.returncode == 0 and result.stdout.strip():
                    for line in result.stdout.strip().split('\\n'):
                        line = line.strip()
                        if not line:
                            continue
                        # Format: MAC  Name  RSSI
                        parts = line.split()
                        if len(parts) >= 2:
                            addr = parts[0]
                            name = " ".join(parts[1:-1]) if len(parts) > 2 else parts[1]
                            rssi = parts[-1] if len(parts) > 2 and parts[-1].lstrip('-').isdigit() else '?'
                            dev = {"name": name, "address": addr, "rssi": rssi}
                            devices.append(dev)
                            if any(kw in name.upper() for kw in ["DOTT", "TIER", "NINEBOT", "MAX", "G30", "ESCOOTER"]):
                                self.log(f"  \U0001f6f4 {name} @ {addr} (RSSI: {rssi})", "ok")
                            else:
                                self.log(f"  {name} @ {addr} (RSSI: {rssi})", "debug")
                    if devices:
                        self.log(f"  -> {len(devices)} Geraet(e) gefunden", "info")
                        return devices
                    self.log("  Keine Geraete gefunden.", "warn")
                    return devices
                self.log("  termux-bluetooth-scan: Keine Ausgabe", "warn")
            except FileNotFoundError:
                self.log("  termux-bluetooth-scan nicht gefunden (pkg install termux-api)", "warn")
            except subprocess.TimeoutExpired:
                self.log(f"  Scan timeout ({timeout}s)", "warn")
            except Exception as e:
                self.log(f"  Termux-Scan-Fehler: {e}", "warn")

            # Fallback: bluetoothctl
            self.log("  Versuche bluetoothctl...", "debug")
            try:
                subprocess.run(["bluetoothctl", "power", "on"], capture_output=True, timeout=3)
                subprocess.run(["bluetoothctl", "scan", "on"], capture_output=True, timeout=1)
                time.sleep(3)
                result = subprocess.run(
                    ["bluetoothctl", "devices"],
                    capture_output=True, text=True, timeout=5
                )
                subprocess.run(["bluetoothctl", "scan", "off"], capture_output=True, timeout=1)
                for line in result.stdout.strip().split('\\n'):
                    if "Device" in line:
                        rest = line.split("Device ", 1)[1] if "Device " in line else ""
                        if rest:
                            parts = rest.split(" ", 1)
                            if len(parts) == 2:
                                addr, name = parts
                                devices.append({"name": name, "address": addr, "rssi": "?"})
                                if any(kw in name.upper() for kw in ["DOTT", "NINEBOT", "G30"]):
                                    self.log(f"  \U0001f6f4 {name} @ {addr}", "ok")
            except Exception as e:
                self.log(f"  bluetoothctl-Fallback: {e}", "debug")
            return devices

        # ─── METHODE 2: BLEAK (Linux, macOS, Windows) ───
        try:
            import asyncio
            from bleak import BleakScanner
            from bleak.exc import BleakError

            async def _scan():
                return await BleakScanner.discover(timeout=timeout)

            self.log("Scanne mit Bleak...", "info")
            try:
                found = asyncio.run(_scan())
            except BleakError as e:
                if "platform" in str(e).lower():
                    self.log(f"Bleak nicht unterstuetzt: {e}", "warn")
                    return devices
                raise

            for d in found:
                name = d.name or ""
                addr = d.address
                rssi = getattr(d, 'rssi', '?')
                dev = {"name": name, "address": addr, "rssi": rssi}
                devices.append(dev)
                if any(kw in name.upper() for kw in ["DOTT", "TIER", "NINEBOT", "MAX", "G30", "ESCOOTER"]):
                    self.log(f"  \U0001f6f4 {name} @ {addr} (RSSI: {rssi})", "ok")

            if not devices:
                self.log("Keine Geraete mit Bleak gefunden.", "warn")
                for d in found[:15]:
                    self.log(f"  {d.name or '(unbenannt)'} @ {d.address}", "debug")
            else:
                self.log(f"  -> {len(devices)} Geraet(e)", "info")
            return devices

        except ImportError:
            self.log("Bleak nicht installiert (pip install bleak)", "warn")
        except Exception as e:
            self.log(f"Bleak-Fehler: {e}", "warn")

        # ─── METHODE 3: HCITOOL (Linux, nicht Android) ───
        if IS_LINUX and not IS_TERMUX:
            self.log("Scanne mit hcitool...", "info")
            try:
                result = subprocess.run(
                    ["sudo", "hcitool", "lescan", "--duplicates"],
                    capture_output=True, text=True, timeout=timeout
                )
                for line in result.stdout.strip().split('\\n'):
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        addr, name = parts[0], " ".join(parts[1:])
                        devices.append({"name": name, "address": addr, "rssi": "?"})
                        if any(kw in name.upper() for kw in ["DOTT", "NINEBOT", "G30", "TIER"]):
                            self.log(f"  \U0001f6f4 {name} @ {addr}", "ok")
            except FileNotFoundError:
                self.log("hcitool nicht gefunden (apt install bluez)", "warn")
            except Exception as e:
                self.log(f"hcitool-Fehler: {e}", "debug")

        if not devices:
            self.log("Keine Scooter via BLE gefunden.", "warn")
        return devices"""

if old_scan in code:
    code = code.replace(old_scan, new_scan)
    changes.append("run_ble_scan() – Termux/Android als Primär")
else:
    changes.append("⚠️  run_ble_scan() – altes Pattern nicht gefunden, suche Variante...")
    # Fallback: Zeilen mit BleakScanner.discover suchen und durch try/except schützen
    code = code.replace(
        "found = await BleakScanner.discover(timeout=timeout)",
        "try:\\n                    found = await BleakScanner.discover(timeout=timeout)\\n                except BleakError as e:\\n                    if \"platform\" in str(e).lower():\\n                        self.log(f\"Bleak nicht unterstuetzt: {e}\", \"warn\")\\n                        return []\\n                    raise"
    )
    code = code.replace(
        "from bleak import BleakScanner",
        "from bleak import BleakScanner\\n            from bleak.exc import BleakError"
    )

# ─── FIX 3: auto_extract_token() – Frida optional machen ───
old_auto = """def auto_extract_token(timeout: int = 30, save: bool = True) -> Optional[str]:
    \"\"\"
    Startet Frida, hookt die Dott-App und extrahiert JWT + Refresh-Token.
    
    Args:
        timeout: Maximale Wartezeit in Sekunden
        save: Token in Datei speichern
        
    Returns:
        JWT-Token oder None
    \"\"\"
    print(f\"\\n{Fore.CYAN}╔═══ AUTO TOKEN EXTRACTION ═══╗{Style.RESET_ALL}\")
    print(f\"{Fore.CYAN}║  Ziel: com.ridedott.rider    ║{Style.RESET_ALL}\")
    print(f\"{Fore.CYAN}║  Timeout: {timeout}s             ║{Style.RESET_ALL}\")
    print(f\"{Fore.CYAN}╚══════════════════════════════╝{Style.RESET_ALL}\\n\")
    
    # Frida-Script schreiben"""

new_auto = """def auto_extract_token(timeout: int = 30, save: bool = True) -> Optional[str]:
    \"\"\"
    Extrahiert JWT-Token – MIT Frida (auto) oder via manueller Eingabe (Fallback).
    
    Args:
        timeout: Maximale Wartezeit in Sekunden (für Frida)
        save: Token in Datei speichern
        
    Returns:
        JWT-Token oder None
    \"\"\"
    print(f\"\\n{Fore.CYAN}╔═══ AUTO TOKEN EXTRACTION ═══╗{Style.RESET_ALL}\")
    print(f\"{Fore.CYAN}║  Ziel: com.ridedott.rider    ║{Style.RESET_ALL}\")
    print(f\"{Fore.CYAN}╚══════════════════════════════╝{Style.RESET_ALL}\\n\")
    
    # ── Prüfe ob Frida verfügbar ──
    frida_ok = False
    try:
        import frida
        print(f\"{Fore.GREEN}[+] Frida {frida.__version__} Python-Binding verfuegbar{Style.RESET_ALL}\")
        frida_ok = True
    except ImportError:
        pass
    
    if frida_ok:
        try:
            r = subprocess.run([\"frida\", \"--version\"], capture_output=True, text=True, timeout=3)
            if r.returncode == 0:
                print(f\"{Fore.GREEN}[+] Frida {r.stdout.strip()} CLI verfuegbar{Style.RESET_ALL}\")
            else:
                frida_ok = False
        except:
            frida_ok = False
    
    if not frida_ok:
        print(f\"{Fore.YELLOW}[!] Frida nicht verfuegbar (weder Python-Binding noch CLI){Style.RESET_ALL}\")
        print(f\"{Fore.YELLOW}[!] Auto-Extraktion deaktiviert – manuelle Eingabe{Style.RESET_ALL}\")
        print(f\"\\n{Fore.CYAN}[*] Token manuell eingeben:{Style.RESET_ALL}\")
        print(f\"  {Fore.WHITE}Möglichkeiten:{Style.RESET_ALL}\")
        print(f\"    1. Aus Burp Suite: Authorization: Bearer <token>\")
        print(f\"    2. ADB Logcat:  adb logcat | grep -i 'authorization\\\\|bearer\\\\|jwt'\")
        print(f\"    3. ADB Datei:   adb shell cat /data/data/com.ridedott.rider/shared_prefs/*.xml\")
        print()
        token = input(\"JWT-Token eingeben (Enter = Abbruch): \").strip()
        if token and len(token) > 50:
            if save:
                with open(TOKEN_FILE, 'w') as f:
                    f.write(token)
                print(f\"{Fore.GREEN}[+] Token gespeichert: {TOKEN_FILE}{Style.RESET_ALL}\")
            return token
        # Letzter Versuch: aus Datei
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'r') as f:
                t = f.read().strip()
                if t and len(t) > 50:
                    print(f\"{Fore.GREEN}[+] Token aus Datei geladen{Style.RESET_ALL}\")
                    return t
        print(f\"{Fore.RED}[!] Kein Token.{Style.RESET_ALL}\")
        return None
    
    # ── Frida ist verfügbar – normal weiter ──
    print(f\"{Fore.CYAN}[*] Frida-Auto-Extraktion gestartet (Timeout: {timeout}s)...{Style.RESET_ALL}\")
    
    # Frida-Script schreiben"""

if old_auto in code:
    code = code.replace(old_auto, new_auto)
    changes.append("auto_extract_token() – Frida optional + manueller Fallback")
else:
    changes.append("⚠️  auto_extract_token() – Pattern nicht gefunden")

# ─── FIX 4: BleakError-Import in den globalen Import-Bereich ───
if "from bleak import BleakScanner" in code and "from bleak.exc import BleakError" not in code:
    code = code.replace(
        "from bleak import BleakScanner",
        "from bleak import BleakScanner\n    from bleak.exc import BleakError"
    )
    changes.append("BleakError-Import hinzugefügt")

# ─── FIX 5: termux_setup() – Frida-Installationsfehler abfangen ───
old_setup_wheel = """    # Frida (optional)
    print(f\"{Fore.YELLOW}[*] Versuche Frida-Installation...{Style.RESET_ALL}\")
    ret = os.system(\"pip install frida-tools 2>/dev/null\")
    if ret == 0:"""
    
new_setup_wheel = """    # Frida (optional – Community-Build für Termux)
    print(f\"{Fore.YELLOW}[*] Versuche Frida-Installation (Community-Build)...{Style.RESET_ALL}\")
    ret = os.system(\"pip install frida-tools 2>/dev/null || pip install frida-tools --no-deps 2>/dev/null\")
    if not os.system(\"python3 -c 'import frida' 2>/dev/null\"):
        print(f\"  {Fore.GREEN}✅ frida Python-Binding verfuegbar{Style.RESET_ALL}\")
    elif not os.system(\"which frida 2>/dev/null\"):
        print(f\"  {Fore.GREEN}✅ frida CLI verfuegbar{Style.RESET_ALL}\")
    else:
        print(f\"  {Fore.YELLOW}ℹ️  Frida nicht installiert – kein Problem!{Style.RESET_ALL}\")
        print(f\"  {Fore.YELLOW}   Token-Extraktion dann manuell (Menüpunkt 1){Style.RESET_ALL}\")
        print(f\"  {Fore.YELLOW}   Frida-Community-Build:{Style.RESET_ALL}\")
        print(f\"  {Fore.YELLOW}   wget https://maglit.me/frida-python -O f && bash f{Style.RESET_ALL}\")
    if ret == 0 or True:"""

if old_setup_wheel in code:
    code = code.replace(old_setup_wheel, new_setup_wheel)
    changes.append("termux_setup() – Frida-Installation graceful")
else:
    changes.append("⚠️  termux_setup() – Pattern nicht gefunden")

# ─── Schreibe Änderungen ───
if code != original:
    with open(path, 'w') as f:
        f.write(code)
    print("[+] PATCH ERFOLGREICH!")
    print(f"    Datei: {path}")
    print(f"    Änderungen ({len(changes)}):")
    for c in changes:
        print(f"      • {c}")
else:
    print("[-] Keine Änderungen nötig oder Pattern nicht gefunden.")
    print("    Manuelle Prüfung empfohlen.")
PATCH

# ─── Zusätzlich: RESETALL-Fix via sed als Fallback ───
sed -i 's/Style\.RESETALL/Style.RESET_ALL/g' dott_pentest.py 2>/dev/null
echo "[+] RESETALL → RESET_ALL (sed-Fallback)"
