""" Инициализация параметров ESP32 """
import sys
import asyncio
from qasync import QEventLoop, asyncSlot
from bleak import BleakScanner, BleakClient
from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton


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

async def scan_for_devices(timeout: float = 25) -> str:
    """Scans for nearby Bluetooth LE devices."""
    print(f"Scanning for {timeout} seconds...")
    devices = await BleakScanner.discover(timeout)
    print("Scan complete. Devices found:")
    for device in devices:
        print(f"Address: {device.address}, Name: {device.name}")
        if device.name == 'FoxDen Bluetooth':
            return device.address
    return None

async def connect_and_read(address) -> bool:
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
            return True

    except Exception as e:
        print(f"An error occurred: {e}")
        return False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setFixedSize(QSize(500, 300))

        self.setWindowTitle("Настройка ESP")
        connectButton = QPushButton("Поключиться через Bluetooth", parent=self)
        connectButton.setFixedSize(200, 60)
        connectButton.clicked.connect(self.on_connect)

    @asyncSlot()
    async def on_connect(self):
        address = await scan_for_devices()
        print(f"{address}")
        if address:
            await connect_and_read(address)
        else:
            print("Not found FoxDen Bluetooth")


def main_app():
    """Основное окно приложения"""
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow()
    window.show()
    #sys.exit(app.exec())
    with loop:
        loop.run_forever()


if __name__ == "__main__":
    # Call the Bluetooth device scanning function when the script is run
    main_app()
