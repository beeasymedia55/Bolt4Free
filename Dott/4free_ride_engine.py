#!/usr/bin/env python3
"""
FreeRide Engine: Termux/Android Optimized Version
Target: Bolt / Dott / Segway / Generic BLE E-Scooters
Date: 2026-08-29
Author: NoTrack

Features:
- Auto-detects BLE backend (bleak-android, pybluez, or mock)
- Async BLE scanning and connection
- Mock API integration for testing
- Colored terminal output
- Configurable parameters

Usage:
    python3 3free_ride_engine.py
"""

import asyncio
import json
import logging
import os
import platform
import secrets
import sys
import time
import uuid
from typing import Optional, Dict, Any, List, Tuple

# Colorama for nice terminal output
try:
    from colorama import Fore, Style, init as colorama_init
    colorama_init()
except ImportError:
    # Fallback if colorama is not installed
    class FakeColor:
        RESET_ALL = ""
        GREEN = ""
        RED = ""
        YELLOW = ""
        BLUE = ""
        CYAN = ""
        MAGENTA = ""
        WHITE = ""
    Fore = Style = FakeColor()

# --- Configuration ---
CONFIG = {
    "bolt_api_base": "https://us.bolt.eu/api/v1",
    "bolt_user_token": None,  # Set this or harvest it
    "bolt_device_id": str(uuid.uuid4()),
    "bolt_user_id": "default_user",
    "scan_duration": 10,
    "retry_attempts": 3,
    "retry_delay": 2,
    "log_file": "freeride_engine.log",
    "ble_timeout": 10,
    "debug_mode": True,
    "mock_mode": True,  # Set to False if you have real BLE hardware
    "ble_backend": "auto",  # Options: "auto", "bleak-android", "pybluez", "mock"
}

# --- Logging Setup ---
logging.basicConfig(
    level=logging.DEBUG if CONFIG["debug_mode"] else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(CONFIG["log_file"]),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("FreeRideEngine")

# --- BLE Backend Detection ---
PLATFORM = platform.system()
BLE_BACKEND = None

if CONFIG["ble_backend"] == "auto":
    if PLATFORM == "Android":
        try:
            import bleak_android
            BLE_BACKEND = "bleak-android"
        except ImportError:
            try:
                import pybluez
                BLE_BACKEND = "pybluez"
            except ImportError:
                BLE_BACKEND = "mock"
    elif PLATFORM == "Linux":
        try:
            import bleak
            BLE_BACKEND = "bleak"
        except ImportError:
            BLE_BACKEND = "mock"
    else:
        BLE_BACKEND = "mock"
else:
    BLE_BACKEND = CONFIG["ble_backend"]

logger.info(f"Using BLE backend: {BLE_BACKEND}")

# --- Mock BLE Classes (if real backend not available) ---
class MockBleakClient:
    def __init__(self, address, timeout=10):
        self.address = address
        self.timeout = timeout
        self.is_connected = False
        self.services = MockServices()

    async def connect(self):
        self.is_connected = True
        logger.info(f"Mock connected to {self.address}")
        return True

    async def disconnect(self):
        self.is_connected = False
        logger.info(f"Mock disconnected from {self.address}")
        return True

    async def read_gatt_char(self, uuid):
        logger.debug(f"Mock read characteristic {uuid}")
        return b"\x00\x01\x02\x03"

    async def write_gatt_char(self, uuid, data):
        logger.debug(f"Mock write characteristic {uuid} with data {data.hex()}")
        return True

class MockServices:
    def __init__(self):
        self.characteristics = {
            "0000fff0-0000-1000-8000-00805f9b34fb": {
                "0000fff1-0000-1000-8000-00805f9b34fb": "mock_characteristic"
            }
        }

    def get(self, service_uuid):
        return self.characteristics.get(service_uuid, {})

class MockScanner:
    def __init__(self):
        self.devices = []

    async def discover(self, timeout=10):
        logger.info("Mock scanning for BLE devices...")
        await asyncio.sleep(1)
        return [
            {"address": "AA:BB:CC:DD:EE:FF", "name": "Mock Scooter", "rssi": -50}
        ]

# --- Real BLE Backend Wrapper ---
class RealBleClient:
    def __init__(self, address, timeout=10):
        self.address = address
        self.timeout = timeout
        self.client = None
        self.services = None
        self.is_connected = False

    async def connect(self):
        try:
            if BLE_BACKEND == "bleak-android":
                from bleak import BleakClient
                self.client = BleakClient(self.address, timeout=self.timeout)
            elif BLE_BACKEND == "pybluez":
                import pybluez
                self.client = pybluez.BluetoothSocket(pybluez.RFCOMM)
                self.client.connect((self.address, 1))
            await asyncio.sleep(0.5)  # Simulate connection delay
            self.is_connected = True
            self.services = {}  # Placeholder for real services
            logger.info(f"Connected to device at {self.address}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to {self.address}: {e}")
            return False

    async def disconnect(self):
        try:
            if self.client:
                if BLE_BACKEND == "bleak-android":
                    await self.client.disconnect()
                elif BLE_BACKEND == "pybluez":
                    self.client.close()
            self.is_connected = False
            logger.info(f"Disconnected from {self.address}")
        except Exception as e:
            logger.error(f"Failed to disconnect from {self.address}: {e}")

    async def read_gatt_char(self, uuid):
        try:
            if BLE_BACKEND == "bleak-android":
                return await self.client.read_gatt_char(uuid)
            elif BLE_BACKEND == "pybluez":
                # Simplified read for pybluez
                return b"\x00\x01\x02\x03"
        except Exception as e:
            logger.error(f"Failed to read characteristic {uuid}: {e}")
            return b""

    async def write_gatt_char(self, uuid, data):
        try:
            if BLE_BACKEND == "bleak-android":
                await self.client.write_gatt_char(uuid, data)
            elif BLE_BACKEND == "pybluez":
                # Simplified write for pybluez
                pass
            return True
        except Exception as e:
            logger.error(f"Failed to write characteristic {uuid}: {e}")
            return False

# --- API Classes ---
class BoltAPI:
    """Bolt API interaction class."""
    def __init__(self, token: str):
        self.token = token
        self.base_url = CONFIG["bolt_api_base"]
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "Bolt/10.0.0 Android/14"
        })

    def get_user_profile(self) -> Dict[str, Any]:
        """Get user profile to validate token."""
        try:
            resp = self.session.get(f"{self.base_url}/users/me")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to get user profile: {e}")
            return {}

    def initiate_ride(self, vehicle_id: str, location: Dict[str, float]) -> Dict[str, Any]:
        """Initiate a ride for a specific vehicle."""
        payload = {
            "vehicle_id": vehicle_id,
            "location": location,
            "device_id": CONFIG["bolt_device_id"],
            "user_id": CONFIG["bolt_user_id"]
        }
        try:
            resp = self.session.post(f"{self.base_url}/rides", json=payload)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.error(f"Failed to initiate ride: {e}")
            return {}

    def end_ride(self, ride_id: str) -> bool:
        """End a ride."""
        try:
            resp = self.session.post(f"{self.base_url}/rides/{ride_id}/end")
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to end ride: {e}")
            return False

class BLEManager:
    """BLE device management and interaction."""
    def __init__(self):
        self.client: Optional[Any] = None
        self.is_mock = BLE_BACKEND == "mock"
        if self.is_mock:
            self.client = MockBleakClient("AA:BB:CC:DD:EE:FF")
            self.services = MockServices()
        else:
            self.client = None
            self.services = None

    async def scan_for_devices(self, timeout: int = 10) -> List[Dict[str, Any]]:
        """Scan for BLE devices."""
        if self.is_mock:
            logger.info("Mock mode: Simulating scan...")
            scanner = MockScanner()
            return await scanner.discover(timeout)
        else:
            logger.info(f"Scanning for BLE devices for {timeout} seconds...")
            try:
                if BLE_BACKEND == "bleak-android":
                    from bleak import BleakScanner
                    devices = await BleakScanner.discover(timeout=timeout)
                    return devices
                elif BLE_BACKEND == "pybluez":
                    import pybluez
                    devices = pybluez.discover_devices(duration=timeout)
                    return [{"address": addr, "name": "Device " + addr, "rssi": -50} for addr in devices]
            except Exception as e:
                logger.error(f"BLE Scan failed: {e}")
                logger.warning("Falling back to mock mode.")
                self.is_mock = True
                self.client = MockBleakClient("AA:BB:CC:DD:EE:FF")
                return [{"address": "AA:BB:CC:DD:EE:FF", "name": "Mock Scooter", "rssi": -50}]

    async def connect_to_device(self, address: str) -> bool:
        """Connect to a BLE device."""
        if self.is_mock:
            logger.info(f"Mock connection to {address}")
            self.current_vehicle_id = address
            return True

        self.client = RealBleClient(address)
        try:
            await self.client.connect()
            self.current_vehicle_id = address
            return True
        except Exception as e:
            logger.error(f"Failed to connect to {address}: {e}")
            return False

    async def disconnect(self):
        """Disconnect from the current BLE device."""
        if self.client and self.client.is_connected:
            await self.client.disconnect()
            logger.info("Disconnected from BLE device")

    async def get_characteristic(self, service_uuid: str, characteristic_uuid: str) -> Any:
        """Get a specific characteristic by UUID."""
        if self.is_mock:
            return self.services.get(service_uuid, {}).get(characteristic_uuid, None)
        else:
            # Placeholder for real service/characteristic retrieval
            return None

    async def read_characteristic(self, characteristic: Any) -> bytes:
        """Read data from a characteristic."""
        if self.is_mock:
            return b"\x00\x01\x02\x03"
        if not characteristic:
            return b""
        try:
            return await self.client.read_gatt_char(characteristic)
        except Exception as e:
            logger.error(f"Failed to read characteristic: {e}")
            return b""

    async def write_characteristic(self, characteristic: Any, data: bytes) -> bool:
        """Write data to a characteristic."""
        if self.is_mock:
            logger.info(f"Mock write: {data.hex()}")
            return True
        if not characteristic:
            return False
        try:
            await self.client.write_gatt_char(characteristic, data)
            return True
        except Exception as e:
            logger.error(f"Failed to write characteristic: {e}")
            return False

class FreeRideEngine:
    """Main engine for free riding."""
    def __init__(self, bolt_token: str = None):
        self.bolt_token = bolt_token
        self.bolt_api = BoltAPI(bolt_token) if bolt_token else None
        self.ble_manager = BLEManager()
        self.current_ride_id: Optional[str] = None
        self.current_vehicle_id: Optional[str] = None
        self.is_ride_active = False

    def setup_bolt_token(self, token: str):
        """Set the Bolt API token."""
        self.bolt_token = token
        self.bolt_api = BoltAPI(token)
        logger.info("Bolt token set")

    async def scan_and_connect(self, device_address: str = None) -> bool:
        """Scan for devices and connect to one."""
        if device_address:
            return await self.ble_manager.connect_to_device(device_address)

        devices = await self.ble_manager.scan_for_devices()
        if not devices:
            logger.warning("No BLE devices found")
            return False

        # Try to connect to the first device
        for device in devices:
            logger.info(f"Attempting to connect to {device.address} ({device.name})")
            if await self.ble_manager.connect_to_device(device.address):
                self.current_vehicle_id = device.address
                return True

        return False

    async def unlock_scooter(self, service_uuid: str, characteristic_uuid: str) -> bool:
        """Unlock the scooter via BLE."""
        characteristic = await self.ble_manager.get_characteristic(service_uuid, characteristic_uuid)
        if not characteristic:
            logger.error("Characteristic not found")
            return False

        # Send unlock command (example: 0x01 for unlock)
        unlock_data = bytes([0x01])
        success = await self.ble_manager.write_characteristic(characteristic, unlock_data)

        if success:
            logger.info("Unlock command sent successfully")
        else:
            logger.error("Failed to send unlock command")

        return success

    async def start_ride(self, location: Dict[str, float] = None) -> bool:
        """Start a ride via Bolt API."""
        if not self.bolt_api:
            logger.error("Bolt token not set")
            return False

        if not self.current_vehicle_id:
            logger.error("No vehicle connected")
            return False

        if location is None:
            location = {"latitude": 40.7128, "longitude": -74.0060}  # Default: NYC

        ride_data = self.bolt_api.initiate_ride(self.current_vehicle_id, location)
        if ride_data:
            self.current_ride_id = ride_data.get("id")
            self.is_ride_active = True
            logger.info(f"Ride started: {self.current_ride_id}")
            return True
        else:
            logger.error("Failed to start ride")
            return False

    async def stop_ride(self) -> bool:
        """Stop the current ride."""
        if not self.current_ride_id:
            logger.warning("No active ride to stop")
            return False

        success = self.bolt_api.end_ride(self.current_ride_id)
        if success:
            logger.info(f"Ride {self.current_ride_id} ended successfully")
            self.is_ride_active = False
            self.current_ride_id = None
        else:
            logger.error("Failed to end ride")

        return success

    async def run_demonstration(self):
        """Run a full demonstration of the free ride process."""
        print(f"\n{Fore.BLUE}=== FreeRide Engine Demonstration ==={Style.RESET_ALL}\n")

        # Step 1: Setup
        print(f"{Fore.YELLOW}Step 1: Setup{Style.RESET_ALL}")
        if not self.bolt_token:
            print(f"{Fore.RED}Bolt token not set. Using demo token.{Style.RESET_ALL}")
            self.bolt_token = "demo_token_12345"
            self.setup_bolt_token(self.bolt_token)

        # Step 2: Scan and Connect
        print(f"\n{Fore.YELLOW}Step 2: Scan and Connect{Style.RESET_ALL}")
        connected = await self.scan_and_connect()
        if not connected:
            print(f"{Fore.RED}Failed to connect to a device.{Style.RESET_ALL}")
            return

        print(f"{Fore.GREEN}Connected to device: {self.current_vehicle_id}{Style.RESET_ALL}")

        # Step 3: Unlock Scooter
        print(f"\n{Fore.YELLOW}Step 3: Unlock Scooter{Style.RESET_ALL}")
        # Example service and characteristic UUIDs (replace with actual ones)
        service_uuid = "0000fff0-0000-1000-8000-00805f9b34fb"
        characteristic_uuid = "0000fff1-0000-1000-8000-00805f9b34fb"
        unlocked = await self.unlock_scooter(service_uuid, characteristic_uuid)
        if not unlocked:
            print(f"{Fore.RED}Failed to unlock scooter.{Style.RESET_ALL}")
            return
        print(f"{Fore.GREEN}Scooter unlocked successfully.{Style.RESET_ALL}")

        # Step 4: Start Ride
        print(f"\n{Fore.YELLOW}Step 4: Start Ride{Style.RESET_ALL}")
        location = {"latitude": 40.7128, "longitude": -74.0060}
        ride_started = await self.start_ride(location)
        if not ride_started:
            print(f"{Fore.RED}Failed to start ride.{Style.RESET_ALL}")
            return
        print(f"{Fore.GREEN}Ride started successfully.{Style.RESET_ALL}")

        # Step 5: Simulate Ride Duration
        print(f"\n{Fore.YELLOW}Step 5: Simulating Ride Duration{Style.RESET_ALL}")
        await asyncio.sleep(5)  # Simulate 5-second ride
        print(f"{Fore.GREEN}Ride duration simulated.{Style.RESET_ALL}")

        # Step 6: Stop Ride
        print(f"\n{Fore.YELLOW}Step 6: Stop Ride{Style.RESET_ALL}")
        ride_stopped = await self.stop_ride()
        if ride_stopped:
            print(f"{Fore.GREEN}Ride stopped successfully.{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Failed to stop ride.{Style.RESET_ALL}")

        # Cleanup
        if not self.ble_manager.is_mock:
            await self.ble_manager.disconnect()
        print(f"\n{Fore.BLUE}=== Demonstration Complete ==={Style.RESET_ALL}\n")

async def main():
    """Main entry point."""
    engine = FreeRideEngine(bolt_token=CONFIG["bolt_user_token"])
    await engine.run_demonstration()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Interrupted by user.{Style.RESET_ALL}")
