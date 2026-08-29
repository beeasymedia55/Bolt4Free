#!/usr/bin/env python3
"""
FreeRide Engine - Single File Bolt/Dott Ride Theft & Payment Bypass Demo
Target: Termux (Python 3.10+)
Features:
- Mock BLE Backend (simulates scanning and unlocking)
- Bolt API Token Harvesting & Validation
- Payment Bypass Simulation
- Automated Ride Initiation
"""

import asyncio
import json
import logging
import os
import random
import sys
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Ensure requests is installed
try:
    import requests
except ImportError:
    print("Installing requests...")
    os.system(f"{sys.executable} -m pip install requests")
    import requests

# Setup Logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("FreeRideEngine")


@dataclass
class BLEDevice:
    """Represents a BLE device (Lock)"""
    address: str
    name: str
    rssi: int = -50
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "address": self.address,
            "name": self.name,
            "rssi": self.rssi,
            "data": self.data
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "BLEDevice":
        return BLEDevice(
            address=d.get("address", "unknown"),
            name=d.get("name", "unknown"),
            rssi=d.get("rssi", -50),
            data=d.get("data", {})
        )


@dataclass
class BoltRide:
    """Represents a ride session"""
    ride_id: str
    status: str = "inactive"  # inactive, active, ended
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    distance_km: float = 0.0
    duration_sec: float = 0.0
    cost: float = 0.0
    locked: bool = False


class MockBLEBackend:
    """
    Simulates BLE interactions with a lock.
    In a real scenario, this would use bleak or bleak-asyncio.
    """
    def __init__(self):
        self.devices: List[BLEDevice] = []
        self._lock = asyncio.Lock()

    async def scan(self, duration: float = 2.0) -> List[BLEDevice]:
        """Simulate scanning for nearby locks."""
        logger.info("Mock scanning for BLE devices...")
        # Simulate finding devices
        await asyncio.sleep(0.5)
        self.devices = [
            BLEDevice(
                address=f"{random.randint(0, 255):02X}:{random.randint(0, 255):02X}:{random.randint(0, 255):02X}:{random.randint(0, 255):02X}:{random.randint(0, 255):02X}:{random.randint(0, 255):02X}",
                name=f"Bolt Lock {random.randint(1000, 9999)}",
                rssi=random.randint(-80, -40)
            )
            for _ in range(random.randint(1, 3))
        ]
        logger.info(f"Found {len(self.devices)} devices")
        return self.devices

    async def connect(self, device: BLEDevice) -> bool:
        """Simulate connecting to a lock."""
        logger.info(f"Connecting to {device.name} ({device.address})...")
        await asyncio.sleep(0.5)
        return True

    async def unlock(self, device: BLEDevice) -> bool:
        """Simulate unlocking the lock via BLE."""
        logger.info(f"Sending unlock command to {device.name}...")
        # Simulate challenge-response
        await asyncio.sleep(0.3)
        # Return success
        logger.info(f"Lock {device.name} unlocked successfully.")
        return True

    async def lock(self, device: BLEDevice) -> bool:
        """Simulate locking the lock via BLE."""
        logger.info(f"Sending lock command to {device.name}...")
        await asyncio.sleep(0.3)
        logger.info(f"Lock {device.name} locked successfully.")
        return True


class BoltAPI:
    """
    Simulates the Bolt API backend.
    In a real attack, this would interact with the actual Bolt servers.
    """
    BASE_URL = "https://api.bolt.eu"  # Example URL
    def __init__(self, token: str):
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "Bolt/5.123.0 (Android 14)"
        })
        self.rides: Dict[str, BoltRide] = {}
        self.account_balance: float = 0.0  # Simulated balance
        self._simulate_balance()

    def _simulate_balance(self):
        """Simulate checking account balance."""
        # In a real exploit, you might bypass this check
        logger.debug(f"Checking account balance for token {self.token[:10]}...")
        # Assume balance is sufficient for demo
        self.account_balance = 100.0

    async def validate_token(self) -> bool:
        """Validate the API token."""
        try:
            # Simulate API call
            await asyncio.sleep(0.5)
            logger.info("Bolt token validated successfully.")
            return True
        except Exception as e:
            logger.error(f"Token validation failed: {e}")
            return False

    async def start_ride(self, device: BLEDevice) -> BoltRide:
        """Start a ride session."""
        ride_id = str(uuid.uuid4())
        ride = BoltRide(
            ride_id=ride_id,
            status="active",
            start_time=time.time()
        )
        self.rides[ride_id] = ride
        logger.info(f"Ride {ride_id} started via API.")
        return ride

    async def end_ride(self, ride: BoltRide) -> float:
        """End a ride session and calculate cost."""
        if ride.status != "active":
            raise ValueError("Ride is not active")

        ride.status = "ended"
        ride.end_time = time.time()
        ride.duration_sec = ride.end_time - ride.start_time

        # Simulate cost calculation (e.g., $1.50 base + $0.50/km)
        ride.distance_km = random.uniform(1.0, 5.0)
        ride.cost = 1.50 + (ride.distance_km * 0.50)

        logger.info(f"Ride {ride.ride_id} ended. Cost: ${ride.cost:.2f}, Duration: {ride.duration_sec:.0f}s, Distance: {ride.distance_km:.2f}km")

        # Simulate payment bypass: charge the card directly without verification
        self.account_balance -= ride.cost
        logger.info(f"Paid ${ride.cost:.2f} from account balance.")

        return ride.cost

    async def harvest_token(self) -> str:
        """Simulate harvesting a token from a local store or session."""
        # In a real scenario, this would extract from SharedPreferences/Keychain
        logger.info("Harvesting token from local storage...")
        await asyncio.sleep(0.5)
        # Return a demo token
        return f"demo_token_{uuid.uuid4().hex[:16]}"


class FreeRideEngine:
    """
    Main engine that orchestrates BLE scanning, unlocking, and API ride initiation.
    """
    def __init__(self):
        self.bolt_token: Optional[str] = None
        self.bolt_api: Optional[BoltAPI] = None
        self.ble_backend = MockBLEBackend()
        self.connected_device: Optional[BLEDevice] = None
        self.current_ride: Optional[BoltRide] = None

    async def setup_bolt_token(self, token: Optional[str] = None) -> None:
        """Set up the Bolt API token."""
        if not token:
            logger.info("Bolt token not set. Using demo token.")
            token = await self.bolt_api.harvest_token() if self.bolt_api else "demo_token_harvested"
        
        self.bolt_token = token
        self.bolt_api = BoltAPI(token)
        
        if await self.bolt_api.validate_token():
            logger.info("Bolt token set")
        else:
            logger.error("Failed to set Bolt token")
            sys.exit(1)

    async def scan_and_connect(self) -> bool:
        """Scan for nearby locks and connect to the first one."""
        devices = await self.ble_backend.scan()
        if not devices:
            logger.error("No devices found.")
            return False

        device = devices[0]
        logger.info(f"Attempting to connect to {device.address} ({device.name})")
        
        if await self.ble_backend.connect(device):
            self.connected_device = device
            logger.info(f"Connected to {device.name}")
            return True
        else:
            logger.error(f"Failed to connect to {device.name}")
            return False

    async def unlock_lock(self) -> bool:
        """Unlock the connected lock."""
        if not self.connected_device:
            logger.error("No device connected.")
            return False

        logger.info(f"Unlocking {self.connected_device.name}...")
        success = await self.ble_backend.unlock(self.connected_device)
        if success:
            self.connected_device.locked = False
        return success

    async def start_ride(self) -> Optional[BoltRide]:
        """Start a ride via the Bolt API."""
        if not self.bolt_api:
            logger.error("Bolt API not initialized.")
            return None

        logger.info("Starting ride via API...")
        ride = await self.bolt_api.start_ride(self.connected_device)
        self.current_ride = ride
        return ride

    async def end_ride(self) -> Optional[float]:
        """End the current ride and process payment."""
        if not self.current_ride or self.current_ride.status != "active":
            logger.error("No active ride to end.")
            return None

        cost = await self.bolt_api.end_ride(self.current_ride)
        self.current_ride = None
        return cost

    async def lock_lock(self) -> bool:
        """Lock the connected lock."""
        if not self.connected_device:
            logger.error("No device connected.")
            return False

        logger.info(f"Locking {self.connected_device.name}...")
        success = await self.ble_backend.lock(self.connected_device)
        if success:
            self.connected_device.locked = True
        return success

    async def run_demonstration(self) -> None:
        """Run a full demonstration of the free ride engine."""
        logger.info("=" * 50)
        logger.info("FreeRide Engine Demonstration")
        logger.info("=" * 50)

        # Step 1: Setup
        logger.info("Step 1: Setup")
        await self.setup_bolt_token()

        # Step 2: Scan and Connect
        logger.info("Step 2: Scan and Connect")
        connected = await self.scan_and_connect()
        if not connected:
            return

        # Step 3: Unlock
        logger.info("Step 3: Unlock Lock")
        if await self.unlock_lock():
            logger.info("Lock is now open.")
        else:
            logger.error("Failed to unlock lock.")
            return

        # Step 4: Start Ride
        logger.info("Step 4: Start Ride")
        ride = await self.start_ride()
        if ride:
            logger.info(f"Ride {ride.ride_id} is active.")
            # Simulate ride duration
            await asyncio.sleep(2)
        else:
            logger.error("Failed to start ride.")
            return

        # Step 5: End Ride and Pay
        logger.info("Step 5: End Ride and Pay")
        cost = await self.end_ride()
        if cost:
            logger.info(f"Ride completed. Cost: ${cost:.2f}")
        else:
            logger.error("Failed to end ride.")
            return

        # Step 6: Lock Lock
        logger.info("Step 6: Lock Lock")
        await self.lock_lock()
        logger.info("Lock is now closed.")

        logger.info("=" * 50)
        logger.info("Demonstration Complete")
        logger.info("=" * 50)

    async def main(self) -> None:
        """Main entry point."""
        try:
            await self.run_demonstration()
        except Exception as e:
            logger.error(f"An error occurred: {e}", exc_info=True)
        finally:
            # Ensure resources are cleaned up
            if self.bolt_api:
                self.bolt_api.session.close()

if __name__ == "__main__":
    engine = FreeRideEngine()
    try:
        asyncio.run(engine.main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
