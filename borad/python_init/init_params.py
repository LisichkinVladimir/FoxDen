""" Инициализация параметров ESP32 """
import sys
import asyncio
from qasync import QEventLoop, asyncSlot
from bleak import BleakScanner, BleakClient, BleakError
from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QTextEdit, QGroupBox,
    QStatusBar
)
from PyQt6.QtGui import QFont

WIFI_SSID_CHARACTERISTIC_UUID = "feb5483e-36e1-4688-b7f5-ea07361b26a8"
WIFI_PASSWORD_CHARACTERISTIC_UUID = "6908c973-cf32-4b0b-bbb5-65bcdf79f94b"
SERVER_NAME_UUID = "3c7925e8-badf-4d38-aab6-5e930db08008"

Characteristics = [
    {
        'uuid': WIFI_SSID_CHARACTERISTIC_UUID,
        'name': 'SSID WiFi',
        'value': None
    },
    {
        'uuid': WIFI_PASSWORD_CHARACTERISTIC_UUID,
        'name': 'Пароль WiFi',
        'value': None
    },
    {
        'uuid': SERVER_NAME_UUID,
        'name': 'Имя сервера',
        'value': None
    }
]

class ConnectionWidget(QWidget):
    """Виджет подключения к BLE устройству"""

    connection_changed = pyqtSignal(bool)  # Сигнал изменения состояния подключения
    data_received = pyqtSignal(dict)       # Сигнал при получении данных

    def __init__(self):
        super().__init__()
        self.client = None
        self.address = None
        self.is_connected = False
        self.init_ui()

    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        layout = QVBoxLayout()

        # Заголовок
        title_label = QLabel("Настройка ESP32 через Bluetooth")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Группа управления подключением
        connection_group = QGroupBox("Управление подключением")
        connection_layout = QVBoxLayout()

        # Индикатор состояния
        self.status_widget = QWidget()
        self.status_widget.setFixedHeight(20)
        self.status_widget.setStyleSheet("background-color: gray; border-radius: 10px;")
        connection_layout.addWidget(self.status_widget)

        self.status_label = QLabel("Не подключено")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        connection_layout.addWidget(self.status_label)

        # Панель кнопок
        button_layout = QHBoxLayout()

        self.connect_btn = QPushButton("Подключиться")
        self.connect_btn.setFixedHeight(40)
        self.connect_btn.clicked.connect(self.on_connect_clicked)
        self.connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)

        self.disconnect_btn = QPushButton("Отключиться")
        self.disconnect_btn.setFixedHeight(40)
        self.disconnect_btn.clicked.connect(self.on_disconnect_clicked)
        self.disconnect_btn.setEnabled(False)
        self.disconnect_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)

        button_layout.addWidget(self.connect_btn)
        button_layout.addWidget(self.disconnect_btn)
        connection_layout.addLayout(button_layout)

        connection_group.setLayout(connection_layout)
        layout.addWidget(connection_group)

        # Группа информации об устройстве
        info_group = QGroupBox("Информация об устройстве")
        info_layout = QVBoxLayout()

        self.device_info_label = QLabel("Устройство не найдено")
        self.device_info_label.setWordWrap(True)
        info_layout.addWidget(self.device_info_label)

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Группа полученных данных
        data_group = QGroupBox("Полученные параметры")
        data_layout = QVBoxLayout()

        self.data_text = QTextEdit()
        self.data_text.setReadOnly(True)
        self.data_text.setMinimumHeight(150)
        self.data_text.setPlaceholderText("Здесь будут отображены параметры после подключения...")
        data_layout.addWidget(self.data_text)

        data_group.setLayout(data_layout)
        layout.addWidget(data_group)

        self.setLayout(layout)

    def update_status(self, connected: bool, device_info: str = ""):
        """Обновление статуса подключения"""
        self.is_connected = connected

        if connected:
            self.status_widget.setStyleSheet("background-color: #4CAF50; border-radius: 10px;")
            self.status_label.setText(f"Подключено: {device_info}")
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
        else:
            self.status_widget.setStyleSheet("background-color: #f44336; border-radius: 10px;")
            self.status_label.setText("Не подключено")
            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(False)

        self.connection_changed.emit(connected)

    def update_device_info(self, info: str):
        """Обновление информации об устройстве"""
        self.device_info_label.setText(info)

    def update_data_display(self, data: dict):
        """Обновление отображения полученных данных"""
        text = ""
        for item in data:
            if item['value']:
                text += f"<b>{item['name']}:</b> {item['value']}<br>"
            else:
                text += f"<b>{item['name']}:</b> Не получено<br>"

        self.data_text.setHtml(text)

    @asyncSlot()
    async def on_connect_clicked(self):
        """Обработчик нажатия кнопки подключения"""
        self.connect_btn.setText("Поиск...")
        self.connect_btn.setEnabled(False)

        try:
            # Поиск устройств
            self.update_device_info("Идёт поиск устройств...")
            address = await self.scan_for_devices()

            if address:
                self.update_device_info(f"Найдено устройство\nАдрес: {address}")

                # Подключение и чтение данных
                success = await self.connect_and_read(address)
                if success:
                    self.update_status(True, address)
                    self.update_data_display(Characteristics)
                else:
                    self.update_device_info("Ошибка подключения или чтения данных")
                    self.update_status(False)
            else:
                self.update_device_info("Устройство 'FoxDen Bluetooth' не найдено")
                self.update_status(False)

        except Exception as e:
            self.update_device_info(f"Ошибка: {str(e)}")
            self.update_status(False)
        finally:
            self.connect_btn.setText("Подключиться")
            self.connect_btn.setEnabled(True)

    @asyncSlot()
    async def on_disconnect_clicked(self):
        """Обработчик нажатия кнопки отключения"""
        try:
            if self.client and self.client.is_connected:
                await self.client.disconnect()
                self.client = None
                self.address = None

            self.update_status(False)
            self.update_device_info("Устройство отключено")
            self.data_text.clear()

            # Сброс значений характеристик
            for item in Characteristics:
                item['value'] = None

        except Exception as e:
            self.update_device_info(f"Ошибка подключения: {str(e)}")

    async def scan_for_devices(self, timeout: float = 15) -> str:
        """Поиск ближайших BLE устройств"""
        self.update_device_info(f"Сканирование... ({timeout} сек)")

        devices = await BleakScanner.discover(timeout)

        for device in devices:
            print(f"Найдено: {device.name} - {device.address}")
            if device.name == 'FoxDen Bluetooth':
                return device.address

        return None

    async def connect_and_read(self, address) -> bool:
        """Подключение к BLE устройству и чтение характеристик"""
        try:
            self.client = BleakClient(address)
            await self.client.connect()

            if self.client.is_connected:
                print(f"Подключено к {address}")

                # Чтение всех характеристик
                for characteristic_info in Characteristics:
                    try:
                        characteristic = await self.client.read_gatt_char(characteristic_info['uuid'])
                        characteristic_str = ''.join(map(chr, characteristic))
                        characteristic_info['value'] = characteristic_str
                        print(f"{characteristic_info['name']}: {characteristic_str}")
                    except BleakError as e:
                        print(f"Ошибка чтения {characteristic_info['name']}: {e}")
                        characteristic_info['value'] = None
                return True

        except BleakError as e:
            print(f"Ошибка подключения: {e}")
            return False

class MainWindow(QMainWindow):
    """ Основное окно приложения """
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Настройка ESP32 - FoxDen")
        self.setFixedSize(QSize(600, 700))

        # Создание центрального виджета
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Основной layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Виджет подключения
        self.connection_widget = ConnectionWidget()
        self.connection_widget.connection_changed.connect(self.on_connection_changed)
        self.connection_widget.data_received.connect(self.on_data_received)
        main_layout.addWidget(self.connection_widget)

        # Строка состояния
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готово к работе")

    def on_connection_changed(self, connected: bool):
        """Обработчик изменения состояния подключения"""
        if connected:
            self.status_bar.showMessage("Устройство подключено", 3000)
        else:
            self.status_bar.showMessage("Устройство отключено", 3000)

    def on_data_received(self, data: dict):
        """Обработчик получения данных"""
        self.status_bar.showMessage("Данные успешно получены", 3000)
        print("Получены данные:", data)

async def main_async():
    """Асинхронная основная функция"""
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow()
    window.show()

    with loop:
        loop.run_forever()

def main():
    """Точка входа в приложение"""
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
