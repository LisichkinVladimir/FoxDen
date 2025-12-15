import asyncio
from bleak import BleakScanner, BleakClient

async def scan_for_devices():
    """Scans for nearby Bluetooth LE devices."""
    print("Scanning for 5 seconds...")
    devices = await BleakScanner.discover()
    print("Scan complete. Devices found:")
    for device in devices:
        print(f"Address: {device.address}, Name: {device.name}")
        if device.name == 'FoxDen Bluetooth':
            await connect_and_read(device.address)
            break

WIFI_SSID_CHARACTERISTIC_UUID = "feb5483e-36e1-4688-b7f5-ea07361b26a8"
WIFI_PASSWORD_CHARACTERISTIC_UUID = "6908c973-cf32-4b0b-bbb5-65bcdf79f94b"

async def connect_and_read(address):
    """Connects to a BLE device and reads a specific characteristic."""
    try:
        # Use async with for automatic connection and disconnection
        async with BleakClient(address) as client:
            print(f"Connected to {address}: {client.is_connected}")

            wifi_ssid = await client.read_gatt_char(WIFI_SSID_CHARACTERISTIC_UUID)
            wifi_ssid_str = ''.join(map(chr, wifi_ssid))
            print(f"WIFI SSID: {wifi_ssid_str}")

            wifi_password = await client.read_gatt_char(WIFI_PASSWORD_CHARACTERISTIC_UUID)
            wifi_password_str = ''.join(map(chr, wifi_password))
            print(f"WIFI Password: {wifi_password_str}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Call the Bluetooth device scanning function when the script is run
    asyncio.run(scan_for_devices())
