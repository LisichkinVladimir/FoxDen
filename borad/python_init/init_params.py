import asyncio
from bleak import BleakScanner, BleakClient

async def scan_for_devices():
    """Scans for nearby Bluetooth LE devices."""
    print("Scanning for 20 seconds...")
    devices = await BleakScanner.discover(20)
    print("Scan complete. Devices found:")
    for device in devices:
        print(f"Address: {device.address}, Name: {device.name}")
        if device.name == 'FoxDen Bluetooth':
            await connect_and_read(device.address)
            break

WIFI_SSID_CHARACTERISTIC_UUID = "feb5483e-36e1-4688-b7f5-ea07361b26a8"
WIFI_PASSWORD_CHARACTERISTIC_UUID = "6908c973-cf32-4b0b-bbb5-65bcdf79f94b"
SERVER_NAME_UUID = "3c7925e8-badf-4d38-aab6-5e930db08008"

Characteristics = [
    {
        'uuid': WIFI_SSID_CHARACTERISTIC_UUID,
        'name': 'WIFI SSID',
        'value': None
    },
    {
        'uuid': WIFI_PASSWORD_CHARACTERISTIC_UUID,
        'name': 'WIFI Password',
        'value': None
    },
    {
        'uuid': SERVER_NAME_UUID,
        'name': 'Web server name',
        'value': None
    }
]

async def connect_and_read(address):
    """Connects to a BLE device and reads a specific characteristic."""
    try:
        # Use async with for automatic connection and disconnection
        async with BleakClient(address) as client:
            print(f"Connected to {address}: {client.is_connected}")

            for characteristic_info in Characteristics:
                characteristic = await client.read_gatt_char(characteristic_info['uuid'])
                characteristic_str = ''.join(map(chr, characteristic))
                print(f"{characteristic_info['name']}: {characteristic_str}")
                characteristic_info['value'] = characteristic_str

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Call the Bluetooth device scanning function when the script is run
    asyncio.run(scan_for_devices())
