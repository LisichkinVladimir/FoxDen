"""
Фоновая служба мониторинга утечек для FoxDen
Запускается в отдельном потоке и периодически проверяет все устройства
"""

import logging
import time
import threading
from datetime import datetime, timedelta
from sqlalchemy import text

# Импорты из основного приложения
try:
    from database import connect_database, close_connection
    from leak_detector import LeakDetector
    from simple_email_sender import email_sender
except ImportError:
    # Если запускаем отдельно, добавляем путь
    import sys
    sys.path.append('.')
    from database import connect_database, close_connection
    from leak_detector import LeakDetector
    from simple_email_sender import email_sender

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('background_monitor.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class BackgroundMonitor:
    def __init__(self, check_interval_minutes=15):
        self.check_interval = check_interval_minutes * 60  # в секундах
        self.leak_detector = LeakDetector()
        self.running = False
        self.thread = None

        # Кэш для хранения времени последних проверок
        self.last_checks = {}

    def start(self):
        """Запускает фоновый мониторинг"""
        if self.running:
            logger.warning("Мониторинг уже запущен")
            return

        self.running = True
        self.thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.thread.start()
        logger.info(f"Фоновый мониторинг запущен. Интервал проверок: {self.check_interval/60} минут")

    def stop(self):
        """Останавливает фоновый мониторинг"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Фоновый мониторинг остановлен")

    def _monitoring_loop(self):
        """Основной цикл мониторинга"""
        while self.running:
            try:
                self.check_all_devices()
            except Exception as e:
                logger.error(f"Ошибка в цикле мониторинга: {e}")

            # Ждем перед следующей проверкой
            for _ in range(int(self.check_interval)):
                if not self.running:
                    break
                time.sleep(1)

    def check_all_devices(self):
        """Проверяет все активные устройства на утечки"""
        logger.info("Начинаем периодическую проверку всех устройств")

        connect = connect_database()
        if connect is None:
            logger.error("Не удалось подключиться к БД")
            return

        try:
            # Получаем все активные устройства с информацией о пользователях
            query = text("""
                SELECT 
                    d.id as device_id,
                    d.serial_number,
                    d.step_increment,
                    d.indicator,
                    d.user_id,
                    u.email,
                    u.state as user_active
                FROM devices d
                JOIN users u ON d.user_id = u.id
                WHERE d.state = true 
                AND u.state = true
                AND u.email IS NOT NULL
                ORDER BY d.id
            """)

            result = connect.execute(query)
            devices = result.fetchall()

            logger.info(f"Найдено {len(devices)} активных устройств для проверки")

            for device in devices:
                try:
                    self.check_single_device(connect, device)
                except Exception as e:
                    logger.error(f"Ошибка проверки устройства {device.device_id}: {e}")

        except Exception as e:
            logger.error(f"Ошибка при получении устройств: {e}")
        finally:
            close_connection(connect)

        logger.info("Периодическая проверка завершена")

    def check_single_device(self, connect, device):
        """Проверяет одно устройство на утечки"""
        device_id = device.device_id

        # Проверяем, не проверяли ли это устройство недавно
        current_time = time.time()
        if device_id in self.last_checks:
            time_since_last = current_time - self.last_checks[device_id]
            if time_since_last < 1800:  # 30 минут
                logger.debug(f"Пропускаем устройство {device_id} (проверялось {int(time_since_last/60)} мин назад)")
                return

        self.last_checks[device_id] = current_time

        # Получаем изменения за последние 24 часа
        twenty_four_hours_ago = datetime.now() - timedelta(hours=24)

        query_changes = text("""
            SELECT moment FROM public.get_device_changes(:device_id)
            WHERE moment >= :start_time
            ORDER BY moment ASC
        """)

        changes_result = connect.execute(query_changes, {
            "device_id": device_id,
            "start_time": twenty_four_hours_ago
        })

        changes_rows = changes_result.fetchall()
        changes = [{'moment': row.moment} for row in changes_rows if row.moment]

        if len(changes) < 3:
            logger.debug(f"Устройство {device_id}: слишком мало изменений ({len(changes)}) для анализа")
            return

        # Анализируем утечки
        leak_alerts = self.leak_detector.analyze_device(
            device_changes=changes,
            step_increment=float(device.step_increment),
            current_value=float(device.indicator),
            serial_number=device.serial_number
        )

        if not leak_alerts:
            logger.debug(f"Устройство {device_id}: утечки не обнаружены")
            return

        logger.warning(f"Устройство {device_id}: обнаружено {len(leak_alerts)} утечек")

        # Формируем данные устройства
        device_info = {
            'id': device_id,
            'serial_number': device.serial_number,
            'indicator': float(device.indicator),
            'step_increment': float(device.step_increment)
        }

        # Отправляем email
        try:
            success = email_sender.send_leak_alert(
                user_email=device.email,
                device_info=device_info,
                leak_alerts=leak_alerts
            )

            if success:
                logger.info(f"✅ Фоновое уведомление отправлено на {device.email}")

                # Логируем в файл
                self.log_background_notification(device_id, device.serial_number, device.email, leak_alerts)
            else:
                logger.error(f"❌ Не удалось отправить фоновое уведомление на {device.email}")

        except Exception as e:
            logger.error(f"Ошибка отправки email для устройства {device_id}: {e}")

    def log_background_notification(self, device_id, serial_number, email, leak_alerts):
        """Логирует фоновое уведомление"""
        try:
            log_file = "background_leaks.log"
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            with open(log_file, "a", encoding="utf-8") as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"ФОНОВАЯ ПРОВЕРКА - Время: {current_time}\n")
                f.write(f"Устройство: {serial_number} (ID: {device_id})\n")
                f.write(f"Email: {email}\n")
                f.write(f"Найдено утечек: {len(leak_alerts)}\n")

                for i, alert in enumerate(leak_alerts, 1):
                    f.write(f"\nУтечка #{i}:\n")
                    f.write(f"  Тип: {alert.get('type', 'unknown')}\n")
                    f.write(f"  Серьезность: {alert.get('severity', 'medium')}\n")

                f.write(f"{'='*60}\n")

        except Exception as e:
            logger.error(f"Ошибка записи лога фоновой проверки: {e}")

# Глобальный экземпляр мониторинга
background_monitor = BackgroundMonitor()

def start_background_monitoring(check_interval_minutes=15):
    """Запускает фоновый мониторинг"""
    background_monitor.check_interval = check_interval_minutes * 60
    background_monitor.start()
    return background_monitor

if __name__ == "__main__":
    # Если запускаем файл отдельно
    logger.info("Запуск фонового мониторинга как отдельного приложения")

    # Проверяем email систему
    if email_sender.enabled:
        logger.info("Email система доступна")
    else:
        logger.warning("Email система отключена. Проверьте настройки в .env")

    monitor = start_background_monitoring(15)  # Проверка каждые 15 минут

    try:
        # Бесконечный цикл
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Остановка по команде пользователя")
        monitor.stop()