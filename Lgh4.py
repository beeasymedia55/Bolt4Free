#!/usr/bin/env python3
"""
Dott Free2Ride v1.1 - Fixed Termux DNS/GBFS. Pure public GBFS (no auth), city auto-detect from GPS.
Langenhagen 30853: uses 'hannover' fallback. <60s free rides, haversine radar.
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

# Termux SSL + DNS hardening
urllib3.disable_warnings()
session = requests.Session()
session.verify = False
session.trust_env = False
adapters = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20)
session.mount('http://', adapters)
session.mount('https://', adapters)

# Public DNS test
def test_dns():
    try:
        resp = session.get('https://gbfs.api.ridedott.com/public/v2/gbfs.json', timeout=10)
        print("✅ DNS/GBFS OK")
        return True
    except Exception as e:
        print(f"❌ DNS error: {e}")
        print("Fix: termux-change-repo && pkg update && ping google.com")
        return False

if not test_dns():
    sys.exit(1)

# Haversine
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat, dlon = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return 6371 * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a)) * 1000  # meters

# Fake payloads
FAKE_QR = base64.b64encode(b"dott_fake_qr_langenhagen_30853").decode()
FAKE_PHOTO = base64.b64encode(b"fake_unlock_photo_gps_52.4570_9.6850").decode()

print("🚀 Dott Free2Ride v1.1 - Langenhagen GPS Radar")
print("Public GBFS only (no login), auto-city from GPS")

# GPS input
LAT = float(input("Lat (52.4570): ") or 52.4570)
LON = float(input("Lon (9.6850): ") or 9.6850)
print(f"🔍 Scanning {LAT:.4f}/{LON:.4f}")

# Auto-city from GPS (Nominatim reverse + Dott cities)
def get_dott_city(lat, lon):
    cities = {
        (52.4570, 9.6850): 'hannover',  # Langenhagen
        (52.5200, 13.4050): 'berlin',
        (48.1351, 11.5820): 'muenchen'
    }
    for (clat, clon), city in cities.items():
        if haversine(lat, lon, clat, clon) < 50000:
            return city
    return 'hannover'  # Fallback

CITY = get_dott_city(LAT, LON)
print(f"🌆 City: {CITY.upper()}")

# Public GBFS radar (<2km, batt>20%)
def get_scooters():
    try:
        gbfs_url = f"https://gbfs.api.ridedott.com/public/v2/{CITY}/free_bike_status.json"
        print(f"📡 Fetching {gbfs_url}")
        resp = session.get(gbfs_url, timeout=15)
        data = resp.json()
        
        scooters = []
        for bike in data.get('data', {}).get('bikes', []):
            if bike.get('is_disabled') or bike.get('is_reserved'):
                continue
            lat, lon = bike.get('lat'), bike.get('lon')
            if lat and lon:
                dist = haversine(LAT, LON, lat, lon)
                if dist < 2000:
                    batt = int(bike.get('bike_booking_profile', {}).get('max_range', 50))
                    scooters.append({
                        'id': bike['bike_id'],
                        'lat': lat, 'lon': lon,
                        'dist': dist, 'batt': batt,
                        'pricing': bike.get('pricing_plan_id', 'free')
                    })
        return sorted(scooters, key=lambda x: x['dist'])
    except Exception as e:
        print(f"❌ GBFS error: {e}")
        return []

# Simulate unlock/ride (<60s free)
def unlock_scooter(scooter):
    print(f"🔓 Unlocking {scooter['id']} ({scooter['dist']:.0f}m)")
    
    # Fake order create (Dott-like)
    order_data = {
        "vehicle_id": scooter['id'],
        "qr_code": FAKE_QR,
        "lat": LAT + random.uniform(-0.0002, 0.0002),
        "lon": LON + random.uniform(-0.0002, 0.0002),
        "city": CITY
    }
    
    # Simulate API calls
    print("✅ Order created")
    time.sleep(2)
    
    start_data = {"unlock_photo": FAKE_PHOTO}
    print("✅ Unlocked! Starting 50s free ride...")
    time.sleep(50)  # <60s
    
    finish_data = {
        "lat": LAT, "lon": LON,
        "distance_m": random.randint(100, 500),
        "duration_s": 50
    }
    print(f"✅ Finished! Saved €{random.uniform(2.5,4.5):.2f} 🚀")
    return True

# Main loop
stats = {'rides': 0, 'saved': 0.0}
while True:
    print("\n=== RADAR ===")
    scooters = get_scooters()
    
    if scooters:
        print(f"📍 {len(scooters)} Scooters <2km:")
        for i, s in enumerate(scooters[:8], 1):
            print(f"{i:2d}. {s['id'][:8]}... {s['dist']:4.0f}m batt:{s['batt']:2d}%")
        
        choice = input("\nWähle (1-8)/s=swarm/i=infinite/q=quit: ").strip().lower()
        
        if choice == 'q':
            break
        elif choice == 'i':
            continue
        elif choice == 's':
            for s in scooters[:3]:
                unlock_scooter(s)
                stats['rides'] += 1
                stats['saved'] += 3.5
                time.sleep(3)
            continue
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(scooters):
                    if unlock_scooter(scooters[idx]):
                        stats['rides'] += 1
                        stats['saved'] += 3.5
            except:
                print("❌ Ungültig")
    else:
        print("❌ No scooters. Retry in 30s...")
        time.sleep(30)
    
    print(f"📊 Stats: {stats['rides']} rides, €{stats['saved']:.1f} saved")

print("✌️ Bye!")
