""" Инициализация параметров ESP32 через Bluetooth """
import sys
import asyncio
from typing import Optional
from qasync import QEventLoop, asyncSlot
from bleak import BleakScanner, BleakClient
from bleak.exc import BleakError
from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QStyle, QDialogButtonBox,
    QLineEdit, QFrame, QScrollArea, QListWidget, QDialog
)
from PyQt6.QtGui import QFont

WIFI_SSID_CHARACTERISTIC_UUID = "feb5483e-36e1-4688-b7f5-ea07361b26a8"
WIFI_PASSWORD_CHARACTERISTIC_UUID = "6908c973-cf32-4b0b-bbb5-65bcdf79f94b"
SERVER_NAME_UUID = "3c7925e8-badf-4d38-aab6-5e930db08008"
ESP_MAC_ADDRESS = "a52070f7-802e-486c-9412-6aff410d5d0a"

Characteristics = [
    {
        'uuid': WIFI_SSID_CHARACTERISTIC_UUID,
        'name': 'Имя WiFi сети (SSID)',
        'value': None,
        'description': 'Введите название вашей WiFi сети',
        'placeholder': 'Например: Home_WiFi_2.4G',
        'can_changed': True
    },
    {
        'uuid': WIFI_PASSWORD_CHARACTERISTIC_UUID,
        'name': 'Пароль WiFi',
        'value': None,
        'description': 'Введите пароль от WiFi сети',
        'placeholder': 'Введите пароль',
        'echo_mode': QLineEdit.EchoMode.Password,
        'can_changed': True
    },
    {
        'uuid': SERVER_NAME_UUID,
        'name': 'Адрес сервера',
        'value': None,
        'description': 'Введите адрес сервера FoxDen',
        'placeholder': 'Например: http://foxden-server.local/',
        'can_changed': True
    },
    {
        'uuid': ESP_MAC_ADDRESS,
        'name': 'ESP32 MAC адрес',
        'value': None,
        'description': 'MAC адрес сервера FoxDen',
        'placeholder': 'Например: cf1b28bbc4e08a9a2e867c8c893527a5fde080ab75b381184508cb85bd763921',
        'can_changed': False
    }
]

class ParameterInputWidget(QWidget):
    """Виджет для ввода одного параметра"""
    def __init__(self, param_info):
        super().__init__()
        self.param_info = param_info
        self.init_ui()

    def init_ui(self):
        """ Инициализация пользовательского интерфейса"""
        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(0, 0, 0, 0)

        # Название параметра
        name_label = QLabel(self.param_info['name'])
        name_font = QFont()
        name_font.setBold(True)
        name_font.setPointSize(10)
        name_label.setFont(name_font)
        layout.addWidget(name_label)

        # Описание параметра
        if 'description' in self.param_info:
            desc_label = QLabel(self.param_info['description'])
            desc_label.setStyleSheet("color: #666666; font-size: 9pt;")
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)

        # Поле ввода
        self.input_field = QLineEdit()
        self.input_field.setMinimumHeight(35)
        self.input_field.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #d1d1d1;
                border-radius: 4px;
                font-size: 10pt;
                background-color: white;
            }
            QLineEdit:focus {
                border: 2px solid #2196F3;
            }
            QLineEdit:hover {
                border: 1px solid #999999;
            }
        """)

        if 'placeholder' in self.param_info:
            self.input_field.setPlaceholderText(self.param_info['placeholder'])

        if 'echo_mode' in self.param_info:
            self.input_field.setEchoMode(self.param_info['echo_mode'])

        layout.addWidget(self.input_field)

        self.setLayout(layout)

    def get_value(self):
        """Получить значение из поля ввода"""
        return self.input_field.text().strip()

    def set_value(self, value):
        """Установить значение в поле ввода"""
        self.input_field.setText(value)

class SelectDialog(QDialog):
    """ Класс выбора сети """

    def __init__(self, address: list):
        super().__init__()
        self.setWindowTitle("Выберете Bluetooth сеть")
        self.setMinimumSize(400, 200)

        self.list_widget = QListWidget(self)
        for item in address:
            self.list_widget.addItem(item['address'] + '-' + item['name'])

        self.list_widget.itemDoubleClicked.connect(self.on_item_dbl_clicked)

        QBtn = (
                    QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
                )

        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.addWidget(self.list_widget)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)

    def on_item_dbl_clicked(self, item):
        """
        Handler function called when an item is clicked.
        The 'item' argument is the QListWidgetItem that was clicked.
        """
        print(f"Selected item text: {item.text()}")
        self.accept()

class ConnectionWidget(QWidget):
    """Виджет подключения к BLE устройству и настройки параметров"""

    connection_changed = pyqtSignal(bool)  # Сигнал изменения состояния подключения
    data_received = pyqtSignal(dict)       # Сигнал при получении данных

    def __init__(self):
        super().__init__()
        self.client: Optional[BleakClient] = None
        self.address: Optional[str] = None
        self.is_connected: bool = False
        self.parameter_widgets = {}
        self.init_ui()

    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # === ЗАГОЛОВОК ===
        title_label = QLabel("Настройка ESP32 FoxDen")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #2c3e50; padding-bottom: 10px;")
        main_layout.addWidget(title_label)

        # === СТАТУС ПОДКЛЮЧЕНИЯ ===
        status_frame = QFrame()
        status_frame.setFrameShape(QFrame.Shape.StyledPanel)
        status_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 8px;
                border: 1px solid #dee2e6;
            }
        """)

        status_layout = QHBoxLayout(status_frame)
        status_layout.setContentsMargins(15, 10, 15, 10)

        # Индикатор статуса
        self.status_indicator = QLabel("●")
        self.status_indicator.setFont(QFont("Arial", 20))
        self.status_indicator.setStyleSheet("color: #dc3545;")  # Красный по умолчанию

        # Текст статуса
        self.status_label = QLabel("Устройство не подключено")
        self.status_label.setStyleSheet("font-size: 11pt; color: #495057;")

        status_layout.addWidget(self.status_indicator)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        main_layout.addWidget(status_frame)

        # === УПРАВЛЕНИЕ ПОДКЛЮЧЕНИЕМ ===
        control_frame = QFrame()
        control_frame.setFrameShape(QFrame.Shape.StyledPanel)
        control_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #dee2e6;
            }
        """)

        control_layout = QVBoxLayout(control_frame)
        control_layout.setContentsMargins(15, 15, 15, 15)

        # Кнопки управления
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.connect_btn = QPushButton("🔍 Найти и подключить")
        self.connect_btn.setFixedHeight(45)
        self.connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 11pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
            QPushButton:disabled {
                background-color: #6c757d;
                color: #ced4da;
            }
        """)
        self.connect_btn.clicked.connect(self.on_connect_clicked)

        self.disconnect_btn = QPushButton("✖ Отключить")
        self.disconnect_btn.setFixedHeight(45)
        self.disconnect_btn.setEnabled(False)
        self.disconnect_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 11pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:pressed {
                background-color: #bd2130;
            }
            QPushButton:disabled {
                background-color: #6c757d;
                color: #ced4da;
            }
        """)
        self.disconnect_btn.clicked.connect(self.on_disconnect_clicked)

        button_layout.addWidget(self.connect_btn)
        button_layout.addWidget(self.disconnect_btn)
        control_layout.addLayout(button_layout)

        main_layout.addWidget(control_frame)

        # === ПАРАМЕТРЫ ДЛЯ НАСТРОЙКИ ===
        params_frame = QFrame()
        params_frame.setFrameShape(QFrame.Shape.StyledPanel)
        params_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 8px;
                border: 1px solid #dee2e6;
            }
        """)

        params_layout = QVBoxLayout(params_frame)
        params_layout.setContentsMargins(15, 15, 15, 15)
        params_layout.setSpacing(15)

        # Создаем виджеты для каждого параметра
        for param in Characteristics:
            param_widget = ParameterInputWidget(param)
            self.parameter_widgets[param['uuid']] = param_widget
            if param['uuid'] == ESP_MAC_ADDRESS:
                param_widget.input_field.setReadOnly(True)
            params_layout.addWidget(param_widget)

        main_layout.addWidget(params_frame)

        # === КНОПКА СОХРАНЕНИЯ ===
        save_layout = QHBoxLayout()
        save_layout.setSpacing(10)

        self.save_btn = QPushButton("💾 Сохранить настройки")
        self.save_btn.setFixedHeight(50)
        self.save_btn.setEnabled(False)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 12pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0069d9;
            }
            QPushButton:pressed {
                background-color: #0062cc;
            }
            QPushButton:disabled {
                background-color: #6c757d;
                color: #ced4da;
            }
        """)
        self.save_btn.clicked.connect(self.on_save_clicked)

        self.exit_btn = QPushButton("Выйти из программы")
        style = self.exit_btn.style()
        assert style is not None
        icon = style.standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton)
        self.exit_btn.setIcon(icon)
        self.exit_btn.setFixedHeight(50)
        self.exit_btn.setEnabled(True)
        self.exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 12pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0069d9;
            }
            QPushButton:pressed {
                background-color: #0062cc;
            }
            QPushButton:disabled {
                background-color: #6c757d;
                color: #ced4da;
            }
        """)
        self.exit_btn.clicked.connect(self.on_exit_clicked)

        save_layout.addWidget(self.save_btn)
        save_layout.addWidget(self.exit_btn)
        main_layout.addLayout(save_layout)
        #main_layout.addWidget(self.save_btn)

        # Добавляем растягивающийся элемент в конце
        main_layout.addStretch()

    def update_status(self, connected: bool):
        """Обновление статуса подключения"""
        self.is_connected = connected

        if connected:
            self.status_indicator.setStyleSheet("color: #28a745;")  # Зеленый
            self.status_label.setText("Подключено к ESP32")
            self.connect_btn.setEnabled(False)
            self.disconnect_btn.setEnabled(True)
            self.save_btn.setEnabled(True)
        else:
            self.status_indicator.setStyleSheet("color: #dc3545;")  # Красный
            self.status_label.setText("Устройство не подключено")
            self.connect_btn.setEnabled(True)
            self.disconnect_btn.setEnabled(False)
            self.save_btn.setEnabled(False)

        self.connection_changed.emit(connected)

    @asyncSlot()
    async def on_connect_clicked(self):
        """Обработчик нажатия кнопки подключения"""
        self.connect_btn.setText("Поиск...")
        self.connect_btn.setEnabled(False)
        self.status_label.setText("Поиск устройств...")

        try:
            # Поиск устройств
            address = await self.scan_for_devices()

            if address:
                if len(address) == 1:
                    self.status_label.setText("Найдено устройство...")
                    address = address[0]['address']
                else:
                    self.status_label.setText("Найдено несколько устройств...")
                    selectDialog = SelectDialog(address)
                    select_address = None
                    if selectDialog.exec():
                        selected_item = selectDialog.list_widget.currentItem()
                        if selected_item is not None:
                            name = selected_item.text()
                            for item in address:
                                if item['address'] in name:
                                    select_address = item['address']
                                    break
                    if select_address is None:
                        return
                    else:
                        address = select_address

                # Подключение и чтение данных
                success = await self.connect_and_read(address)
                if success:
                    self.update_status(True)
                else:
                    self.status_label.setText("Ошибка подключения")
                    self.update_status(False)
            else:
                self.status_label.setText("Устройство не найдено")
                self.update_status(False)

        except Exception as e:
            self.status_label.setText("Ошибка поиска")
            self.update_status(False)
            print(f"Ошибка: {e}")
        finally:
            self.connect_btn.setText("🔍 Найти и подключить")

    @asyncSlot()
    async def on_disconnect_clicked(self):
        """Обработчик нажатия кнопки отключения"""
        try:
            if self.client and self.client.is_connected:
                await self.client.disconnect()
            self.client = None
            self.address = None

            self.update_status(False)

        except (BleakError, OSError) as e:
            self.status_label.setText("Ошибка отключения")
            print(f"Ошибка отключения: {e}")

    @asyncSlot()
    async def on_save_clicked(self):
        """Обработчик нажатия кнопки сохранения"""
        # Получаем значения из всех полей
        values = {}
        for param in Characteristics:
            widget = self.parameter_widgets[param['uuid']]
            value = widget.get_value()
            param['value'] = value
            values[param['name']] = value
        # Проверяем, все ли поля заполнены
        missing_fields = [name for name, value in values.items() if not value]

        if missing_fields:
            self.status_label.setText("Заполните все поля")
            return

        # Здесь будет код для сохранения на устройство
        self.status_label.setText("Сохранение настроек...")
        success = await self.ble_write()
        if success:
            self.status_label.setText("Параметры сохранены")
        else:
            self.status_label.setText("Ошибка сохранения параметров")

    @asyncSlot()
    async def on_exit_clicked(self):
        """Выход из программы"""
        try:
            if self.client and self.client.is_connected:
                await self.client.disconnect()
            self.client = None
            self.address = None
        except (BleakError, OSError) as e:
            print(f"Ошибка отключения: {e}")

        self.close()
        instance = QApplication.instance()
        assert instance is not None
        instance.quit()

    async def scan_for_devices(self, timeout: float = 30) -> list:
        """Поиск ближайших BLE устройств"""
        self.status_label.setText("Сканирование...")
        devices = await BleakScanner.discover(timeout)
        my_services = []
        for device in devices:
            if device.name and 'FoxDen' in device.name:
                my_services.append({'address': device.address, 'name': device.name})

        return my_services

    async def connect_and_read(self, address) -> bool:
        """Подключение к BLE устройству и чтение характеристик"""
        try:
            self.client = BleakClient(address, timeout = 15.0)
            await self.client.connect()

            if self.client.is_connected:
                print(f"Успешно подключено к {address}")

                # Чтение текущих значений с устройства
                for characteristic_info in Characteristics:
                    try:
                        characteristic = await self.client.read_gatt_char(characteristic_info['uuid'])
                        characteristic_str = ''.join(map(chr, characteristic))

                        # Устанавливаем значение в соответствующее поле
                        widget = self.parameter_widgets[characteristic_info['uuid']]
                        widget.set_value(characteristic_str)
                        characteristic_info['value'] = characteristic_str

                        print(f"Прочитано {characteristic_info['name']}: {characteristic_str}")
                    except (BleakError, OSError) as e:
                        print(f"Не удалось прочитать {characteristic_info['name']}: {e}")
                        return False

                return True
            else:
                return False

        except (BleakError, OSError) as e:
            print(f"Ошибка подключения: {e}")
            return False

    async def ble_write(self) -> bool:
        """Запись параметров в """
        if self.client is None:
            return False
        if not self.client.is_connected:
            return False
        for characteristic_info in Characteristics:
            if not characteristic_info['can_changed']:
                continue
            characteristic_data = bytearray(characteristic_info['value'], 'utf-8')
            try:
                response = await self.client.write_gatt_char(
                    char_specifier = characteristic_info['uuid'],
                    data = characteristic_data,
                    response = True
                )
                if response:
                    print(f"Write successful. Device response: {response}")
                else:
                    print("Write successful (no response data returned).")
            except (BleakError, OSError) as e:
                print(f"Error during write operation: {e}")
                return False
        return True

class MainWindow(QMainWindow):
    """ Основное окно приложения """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FoxDen - Настройка ESP32")
        self.setFixedSize(QSize(450, 710))

        # Устанавливаем стиль окна
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
        """)

        # Создание центрального виджета с прокруткой
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("border: none; background-color: #f5f5f5;")

        # Создаем контейнер для виджета
        container = QWidget()
        self.connection_widget = ConnectionWidget()
        self.connection_widget.connection_changed.connect(self.on_connection_changed)

        container_layout = QVBoxLayout(container)
        container_layout.addWidget(self.connection_widget)
        container_layout.setContentsMargins(0, 0, 0, 0)

        scroll_area.setWidget(container)
        self.setCentralWidget(scroll_area)

    def on_connection_changed(self, connected: bool):
        """Обработчик изменения состояния подключения"""
        if connected:
            self.connection_widget.status_label.setText("Подключено к ESP32")
        else:
            self.connection_widget.status_label.setText("Устройство не подключено")

    @asyncSlot()
    async def closeEvent(self, event):
        event.accept()
        client = self.connection_widget.client
        try:
            if client and client.is_connected:
                await client.disconnect()
        except (BleakError, OSError) as e:
            print(f"Ошибка отключения: {e}")


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
