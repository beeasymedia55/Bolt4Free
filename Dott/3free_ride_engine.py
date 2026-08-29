"""
FreeRide Engine: Full Featured Un-Cut Version
Target: Bolt / Dott / Segway / Generic BLE E-Scooters
Date: 2026-08-29
Author: NoTrack
Dependencies: pip install bleak requests colorama
"""

import asyncio
import json
import logging
import os
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
    Fore = Style = type('FakeColor', (), {'RESET_ALL': '', 'GREEN': '', 'RED': '', 'YELLOW': '', 'BLUE': ''})()

# Bleak imports with fallback for version compatibility
try:
    from bleak import BleakClient, BleakScanner, BleakGATTCharacteristicCollection
    HAS_OLD_BLEAK = True
except ImportError:
    HAS_OLD_BLEAK = False

# Requests for API interactions
try:
    import requests
except ImportError:
    print("Requests module not found. Install with: pip install requests")
    sys.exit(1)

# Configuration
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
}

# Logging setup
logging.basicConfig(
    level=logging.DEBUG if CONFIG["debug_mode"] else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(CONFIG["log_file"]),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("FreeRideEngine")

class BleakCompat:
    """Wrapper to handle Bleak API changes between versions."""
    @staticmethod
    def get_characteristics(service_uuid: str, services: Any) -> Dict[str, Any]:
        """
        Get characteristics from a service, handling both old and new Bleak APIs.
        """
        service = services.get(service_uuid)
        if not service:
            return {}
        
        if HAS_OLD_BLEAK and hasattr(service, 'characteristics'):
            return service.characteristics
        elif isinstance(service, dict):
            return service
        else:
            return {}

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
        self.client: Optional[BleakClient] = None
        self.services: Optional[Any] = None
    
    async def scan_for_devices(self, timeout: int = 10) -> List[Dict[str, Any]]:
        """Scan for BLE devices."""
        logger.info(f"Scanning for BLE devices for {timeout} seconds...")
        devices = await BleakScanner.discover(timeout=timeout)
        return devices
    
    async def connect_to_device(self, address: str) -> bool:
        """Connect to a BLE device."""
        try:
            self.client = BleakClient(address, timeout=CONFIG["ble_timeout"])
            await self.client.connect()
            logger.info(f"Connected to device at {address}")
            self.services = self.client.services
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
        if not self.services:
            return None
        
        characteristics = BleakCompat.get_characteristics(service_uuid, self.services)
        return characteristics.get(characteristic_uuid)
    
    async def read_characteristic(self, characteristic: Any) -> bytes:
        """Read data from a characteristic."""
        if not characteristic:
            return b""
        try:
            return await self.client.read_gatt_char(characteristic.uuid)
        except Exception as e:
            logger.error(f"Failed to read characteristic: {e}")
            return b""
    
    async def write_characteristic(self, characteristic: Any, data: bytes) -> bool:
        """Write data to a characteristic."""
        if not characteristic:
            return False
        try:
            await self.client.write_gatt_char(characteristic.uuid, data)
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
        await self.ble_manager.disconnect()
        print(f"\n{Fore.BLUE}=== Demonstration Complete ==={Style.RESET_ALL}\n")

async def main():
    """Main entry point."""
    engine = FreeRideEngine(bolt_token=CONFIG["bolt_user_token"])
    await engine.run_demonstration()

if __name__ == "__main__":
    asyncio.run(main())
