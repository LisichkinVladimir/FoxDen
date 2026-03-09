""" Сервер приложения FoxDen """
import logging
import time
import threading
import traceback
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, wrappers, render_template, session, redirect, url_for
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
import config
from database import connect_database, close_connection
from leak_detector import LeakDetector
from simple_email_sender import email_sender

# ============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================================

def json_error(error_code: int, error_message: str) -> wrappers.Response:
    """ Возвращает ошибку в JSON формате """
    result = {
        "error": {
            "error_code": error_code,
            "error_message": error_message
        },
        "result": {}
    }
    return jsonify(result)

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    logging.info(f"=== Проверка прав администратора для user_id={user_id} ===")

    connect = connect_database()
    if connect is None:
        logging.error("Не удалось подключиться к БД")
        return False

    try:
        # Проверяем наличие роли администратора
        query = text("""select public.is_admin(:user_id) as is_admin""")

        logging.info(f"Выполняем запрос: {query}")
        result = connect.execute(query, {"user_id": user_id})
        count = result.fetchone()[0]
        logging.info(f"Результат запроса: count={count}")

        is_admin_result = count > 0
        logging.info(f"Пользователь {user_id} является администратором: {is_admin_result}")

        return is_admin_result
    except Exception as e:
        logging.error(f"Ошибка проверки прав администратора: {e}")
        return False
    finally:
        close_connection(connect)

# ============================================================================
# СОЗДАНИЕ ПРИЛОЖЕНИЯ FLASK
# ============================================================================

app = Flask(__name__)
app.config["JWT_ALGORITHM"] = "HS256"
app.config["JWT_SECRET_KEY"] = config.FOXDEN_TOKEN
app.secret_key = config.FOXDEN_TOKEN or 'fallback_secret_key_for_sessions'

jwt = JWTManager(app)

# Инициализация системы утечек
leak_detector = LeakDetector()

# ============================================================================
# ГЛОБАЛЬНЫЙ КЭШ ДЛЯ УВЕДОМЛЕНИЙ
# ============================================================================

last_notifications = {}

def should_send_notification(device_id, alert_type):
    """Проверяет, можно ли отправлять уведомление (не чаще 1 раза в 4 часа)"""
    key = f"{device_id}_{alert_type}"
    current_time = time.time()

    if key in last_notifications:
        # Не отправляем чаще чем раз в 4 часа
        if current_time - last_notifications[key] < 4 * 3600:
            return False

    last_notifications[key] = current_time
    return True

# ============================================================================
# ФУНКЦИЯ АВТОМАТИЧЕСКОЙ ОТПРАВКИ EMAIL
# ============================================================================

def send_automatic_leak_email(device_id, current_value, serial_number):
    """
    Автоматически отправляет email при обнаружении утечки
    Вызывается сразу после добавления изменений
    """
    try:
        logging.info("[AUTO EMAIL] Проверка утечек для устройства %s (%s)", device_id, serial_number)

        connect = connect_database()
        if connect is None:
            logging.error("[AUTO EMAIL] Не удалось подключиться к БД")
            return False

        try:
            # 1. Получаем информацию об устройстве и пользователе
            query = text("""
                SELECT 
                    d.serial_number,
                    d.step_increment,
                    d.indicator,
                    d.user_id,
                    u.email,
                    u.name as username
                FROM devices d
                JOIN users u ON d.user_id = u.id
                WHERE d.id = :device_id 
                AND d.state = true 
                AND u.state = true
            """)
            result = connect.execute(query, {"device_id": device_id})
            device_row = result.fetchone()

            if not device_row:
                logging.warning("[AUTO EMAIL] Устройство %s не найдено", device_id)
                return False

            # Извлекаем данные
            step_increment = float(device_row[1]) if device_row[1] is not None else 10.0
            serial_num = device_row[0] if device_row[0] else serial_number
            user_email = device_row[4] if device_row[4] else None

            if not user_email:
                logging.error("[AUTO EMAIL] Email пользователя не найден для устройства %s", device_id)
                return False

            # 2. Получаем изменения устройства за последние 24 часа
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

            # Преобразуем в формат для анализатора
            changes = []
            for row in changes_rows:
                if row and hasattr(row, 'moment') and row.moment:
                    changes.append({'moment': row.moment})

            if len(changes) < 3:
                logging.info("[AUTO EMAIL] Мало изменений (%s) для анализа утечек", len(changes))
                return False

            # 3. Анализируем утечки
            leak_alerts = leak_detector.analyze_device(
                device_changes=changes,
                step_increment=step_increment,
                current_value=current_value,
                serial_number=serial_num
            )

            if not leak_alerts:
                logging.info("[AUTO EMAIL] Утечки не обнаружены для устройства %s", device_id)
                return False

            logging.warning("[AUTO EMAIL] ОБНАРУЖЕНА УТЕЧКА! Устройство %s: %s предупреждений", serial_num, len(leak_alerts))

            # 4. Фильтруем уведомления по кэшу
            alerts_to_send = []
            for alert in leak_alerts:
                alert_type = alert.get('type', 'unknown')
                if should_send_notification(device_id, alert_type):
                    alerts_to_send.append(alert)
                    logging.info("[AUTO EMAIL] Отправим уведомление типа: %s", alert_type)
                else:
                    logging.info("[AUTO EMAIL] Пропускаем %s (отправлялось недавно)", alert_type)

            if not alerts_to_send:
                logging.info("[AUTO EMAIL] Все уведомления недавно отправлялись")
                return False

            # 5. Формируем данные устройства для письма
            device_info = {
                'id': device_id,
                'serial_number': serial_num,
                'indicator': current_value,
                'step_increment': step_increment,
                'total_changes': len(changes)
            }

            # 6. Отправляем email
            logging.info("[AUTO EMAIL] ОТПРАВКА EMAIL на %s об утечке на %s", user_email, serial_num)

            success = email_sender.send_leak_alert(
                user_email=user_email,
                device_info=device_info,
                leak_alerts=alerts_to_send
            )

            if success:
                logging.info("[AUTO EMAIL] EMAIL УСПЕШНО ОТПРАВЛЕН на %s", user_email)

                # Логируем в файл
                try:
                    log_file = "leak_notifications.log"
                    with open(log_file, "a", encoding="utf-8") as f:
                        f.write(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ")
                        f.write(f"Устройство {serial_num} - Email отправлен на {user_email} - ")
                        f.write(f"Текущее значение: {current_value} - ")
                        f.write(f"Утечек: {len(alerts_to_send)}\n")
                except Exception as log_error:
                    logging.warning("[AUTO EMAIL] Ошибка записи лога: %s", log_error)

                return True
            else:
                logging.error("[AUTO EMAIL] НЕ УДАЛОСЬ ОТПРАВИТЬ EMAIL на %s", user_email)
                return False

        except Exception as e:
            logging.error("[AUTO EMAIL] Ошибка при отправке email: %s", e)
            logging.error(traceback.format_exc())
            return False
        finally:
            close_connection(connect)

    except Exception as e:
        logging.error("[AUTO EMAIL] Критическая ошибка: %s", e)
        logging.error(traceback.format_exc())
        return False

def check_single_device_for_leaks(device_id, serial_number, current_value):
    """
    Проверяет одно устройство на утечки и отправляет email если нужно
    Возвращает информацию об утечках для отображения в dashboard
    """
    try:
        connect = connect_database()
        if connect is None:
            return {"error": "Не удалось подключиться к БД"}

        try:
            # Получаем информацию об устройстве
            query = text("""
                SELECT 
                    d.step_increment,
                    d.user_id,
                    u.email
                FROM devices d
                JOIN users u ON d.user_id = u.id
                WHERE d.id = :device_id 
                AND d.state = true 
                AND u.state = true
            """)
            result = connect.execute(query, {"device_id": device_id})
            device_row = result.fetchone()

            if not device_row:
                return {"error": "Устройство не найдено"}

            step_increment = float(device_row[0]) if device_row[0] is not None else 10.0
            user_email = device_row[2] if device_row[2] else None

            # Получаем изменения устройства за последние 24 часа
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

            # Преобразуем в формат для анализатора
            changes = []
            for row in changes_rows:
                if row and hasattr(row, 'moment') and row.moment:
                    changes.append({'moment': row.moment})

            if len(changes) < 3:
                return {"info": f"Мало изменений ({len(changes)}) для анализа утечек"}

            # Анализируем утечки
            leak_alerts = leak_detector.analyze_device(
                device_changes=changes,
                step_increment=step_increment,
                current_value=current_value,
                serial_number=serial_number
            )

            if not leak_alerts:
                return {"info": "Утечки не обнаружены"}

            result_data = {
                "success": True,
                "leak_count": len(leak_alerts),
                "alerts": leak_alerts,
                "device_id": device_id,
                "serial_number": serial_number
            }

            # Автоматически отправляем email если есть утечки и email пользователя
            if user_email and leak_alerts:
                # Фильтруем уведомления по кэшу
                alerts_to_send = []
                for alert in leak_alerts:
                    alert_type = alert.get('type', 'unknown')
                    if should_send_notification(device_id, alert_type):
                        alerts_to_send.append(alert)

                if alerts_to_send:
                    device_info = {
                        'id': device_id,
                        'serial_number': serial_number,
                        'indicator': current_value,
                        'step_increment': step_increment,
                        'total_changes': len(changes)
                    }

                    success = email_sender.send_leak_alert(
                        user_email=user_email,
                        device_info=device_info,
                        leak_alerts=alerts_to_send
                    )

                    if success:
                        result_data["email_sent"] = True
                        result_data["email_address"] = user_email
                        logging.info("[DASHBOARD CHECK] Email отправлен на %s об утечке на %s", user_email, serial_number)

            return result_data

        except Exception as e:
            logging.error("[DASHBOARD CHECK] Ошибка проверки устройства %s: %s", device_id, e)
            return {"error": f"Ошибка проверки: {e}"}
        finally:
            close_connection(connect)

    except Exception as e:
        logging.error("[DASHBOARD CHECK] Критическая ошибка: %s", e)
        return {"error": f"Критическая ошибка: {e}"}

# ============================================================================
# ФОНОВЫЙ МОНИТОРИНГ
# ============================================================================

class BackgroundMonitor:
    """ Фоновый мониторинг """
    def __init__(self, check_interval_minutes=15):
        self.check_interval = check_interval_minutes * 60
        self.leak_detector = LeakDetector()
        self.running = False
        self.thread = None
        self.last_checks = {}

    def start(self):
        """Запускает фоновый мониторинг"""
        if self.running:
            logging.warning("Мониторинг уже запущен")
            return

        self.running = True
        self.thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.thread.start()
        logging.info("Фоновый мониторинг запущен. Интервал проверок: %s минут", self.check_interval/60)

    def stop(self):
        """Останавливает фоновый мониторинг"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logging.info("Фоновый мониторинг остановлен")

    def _monitoring_loop(self):
        """Основной цикл мониторинга"""
        while self.running:
            try:
                self.check_all_devices()
            except Exception as e:
                logging.error("Ошибка в цикле мониторинга: %s", e)

            # Ждем перед следующей проверкой
            for _ in range(int(self.check_interval)):
                if not self.running:
                    break
                time.sleep(1)

    def check_all_devices(self):
        """Проверяет ВСЕ активные устройства на утечки"""
        logging.info("Начинаем периодическую проверку ВСЕХ устройств")

        connect = connect_database()
        if connect is None:
            logging.error("Не удалось подключиться к БД")
            return

        try:
            # Используем функцию get_devices для получения всех устройств
            # и затем проверяем каждое отдельно
            query_users = text("SELECT id, email FROM users WHERE state = true AND email IS NOT NULL")
            users_result = connect.execute(query_users)
            users = users_result.fetchall()

            if not users:
                logging.info("Нет активных пользователей с email")
                return

            total_devices = 0
            total_leaks = 0

            for user in users:
                user_id = user[0]
                user_email = user[1]

                try:
                    # Получаем ВСЕ устройства пользователя через функцию
                    query_devices = text("SELECT * FROM public.get_devices(:user_id)")
                    devices_result = connect.execute(query_devices, {"user_id": user_id})
                    devices = devices_result.fetchall()

                    for device in devices:
                        total_devices += 1
                        try:
                            leak_count = self.check_single_device(connect, device, user_email)
                            if leak_count > 0:
                                total_leaks += leak_count
                        except Exception as e:
                            logging.error("Ошибка проверки устройства %s: %s", device[0] if device else 'unknown', e)

                except Exception as e:
                    logging.error("Ошибка получения устройств пользователя %s: %s", user_id, e)

            logging.info("Периодическая проверка завершена. Проверено устройств: %s, найдено утечек: %s",
                        total_devices, total_leaks)

        except Exception as e:
            logging.error("Ошибка при проверке устройств: %s", e)
        finally:
            close_connection(connect)

    def check_single_device(self, connect, device, user_email):
        """Проверяет одно устройство на утечки и возвращает количество утечек"""
        if len(device) < 8:
            return 0

        device_id = device[0]

        # Проверяем, не проверяли ли это устройство недавно
        current_time = time.time()
        if device_id in self.last_checks:
            time_since_last = current_time - self.last_checks[device_id]
            if time_since_last < 1800:  # 30 минут
                return 0

        self.last_checks[device_id] = current_time

        step_increment = float(device[6]) if len(device) > 6 and device[6] is not None else 10.0
        current_value = float(device[7]) if len(device) > 7 and device[7] is not None else 0.0
        serial_number = device[4] if len(device) > 4 and device[4] else f'Устройство {device_id}'

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
        changes = [{'moment': row.moment} for row in changes_rows if row and hasattr(row, 'moment') and row.moment]

        if len(changes) < 3:
            return 0

        # Анализируем утечки
        leak_alerts = self.leak_detector.analyze_device(
            device_changes=changes,
            step_increment=step_increment,
            current_value=current_value,
            serial_number=serial_number
        )

        if not leak_alerts:
            return 0

        logging.warning("Устройство %s: обнаружено %s утечек", device_id, len(leak_alerts))

        # Формируем данные устройства
        device_info = {
            'id': device_id,
            'serial_number': serial_number,
            'indicator': current_value,
            'step_increment': step_increment
        }

        # Отправляем email
        try:
            success = email_sender.send_leak_alert(
                user_email=user_email,
                device_info=device_info,
                leak_alerts=leak_alerts
            )

            if success:
                logging.info("Фоновое уведомление отправлено на %s", user_email)
            else:
                logging.error("Не удалось отправить фоновое уведомление на %s", user_email)

        except Exception as e:
            logging.error("Ошибка отправки email для устройства %s: %s", device_id, e)

        return len(leak_alerts)

# Глобальный экземпляр мониторинга
background_monitor = BackgroundMonitor()

def start_background_monitoring(check_interval_minutes=15):
    """Запускает фоновый мониторинг"""
    background_monitor.check_interval = check_interval_minutes * 60
    background_monitor.start()
    return background_monitor

# ============================================================================
# ОСНОВНЫЕ МАРШРУТЫ
# ============================================================================

@app.route('/')
def hello_world():
    """ Стартовая страница сервера """
    user_is_admin = False
    if 'username' in session and 'userid' in session:
        user_is_admin = is_admin(session['userid'])
        logging.info(f"User {session['username']} (ID: {session['userid']}) is_admin: {user_is_admin}")
        return render_template('index.html', username=session['username'], is_admin=user_is_admin)
    else:
        return render_template('index.html', username=None, is_admin=False)

@app.route('/login', methods=['POST'])
def login():
    """ Обработка формы входа """
    username = request.form.get('username')
    password = request.form.get('password')

    connect = connect_database()
    if connect is None:
        return render_template('index.html', username=None, error="Ошибка подключения к БД")

    try:
        query = text("SELECT * FROM public.get_user(:username, :password)")
        result = connect.execute(query, {"username": username, "password": password})
        user = result.fetchone()

        if user:
            session['username'] = username
            session['userid'] = user.id
            logging.info("User %s successfully logged in", username)
            return redirect(url_for('hello_world'))
        else:
            logging.warning("Failed login attempt for user: %s", username)
            return render_template('index.html', username=None, error="Неверный логин или пароль")

    except SQLAlchemyError as ex:
        logging.error("Database error in login: %s", ex)
        return render_template('index.html', username=None, error="Ошибка базы данных")
    finally:
        if connect:
            close_connection(connect)

@app.route('/logout')
def logout():
    """ Выход из системы """
    username = session.pop('username', None)
    session.pop('userid', None)
    logging.info("User %s logged out", username)
    return redirect(url_for('hello_world'))

@app.route('/dashboard')
def dashboard():
    """ Панель управления счетчиками """
    if 'username' not in session:
        return redirect(url_for('hello_world'))

    connect = connect_database()
    if connect is None:
        return render_template('error.html', error="Ошибка подключения к БД")

    try:
        # Получаем список ВСЕХ счетчиков пользователя
        query = text("select * from public.get_devices(:user_id)")
        result = connect.execute(query, {"user_id": session['userid']})
        devices = result.fetchall()

        # Подготавливаем данные для шаблона
        devices_data = []

        for device in devices:
            device_id = device[0] if len(device) > 0 else None
            step_increment = float(device[6]) if len(device) > 6 and device[6] is not None else 10.0
            current_value = float(device[7]) if len(device) > 7 and device[7] is not None else 0.0

            # Получаем изменения для графиков
            cumulative_labels = []
            cumulative_values = []
            daily_labels = []
            daily_values = []
            monthly_labels = []
            monthly_values = []
            total_changes = 0
            leak_alerts = []

            try:
                query_changes = text("select moment from public.get_device_changes(:device_id)")
                changes_result = connect.execute(query_changes, {"device_id": device_id})
                changes_rows = changes_result.fetchall()
                changes = []
                for row in changes_rows:
                    if hasattr(row, 'moment') and row.moment:
                        changes.append({
                            'moment': row.moment
                        })

                total_changes = len(changes)
                if changes:
                    leak_alerts = leak_detector.analyze_device(
                        device_changes=changes,
                        step_increment=step_increment,
                        current_value=current_value,
                        serial_number=device[4] if len(device) > 4 else 'Без номера'
                    )

                    # 1. НАКОПИТЕЛЬНЫЙ ГРАФИК - ИСПРАВЛЕННАЯ ВЕРСИЯ
                    if total_changes > 0:
                        # Создаем равномерные точки
                        cumulative_labels = []
                        cumulative_values = []

                        # Создаем начальное значение
                        initial_value = current_value - (total_changes * step_increment)

                        # Для первого графика: создаем последовательные точки
                        for i in range(min(total_changes, 30)):
                            cumulative_labels.append(f'Точка {i+1}')
                            cumulative_values.append(initial_value + (i * step_increment))

                        # Последняя точка - текущее значение
                        if total_changes > 1:
                            cumulative_labels[-1] = 'Текущее'
                            cumulative_values[-1] = current_value
                    else:
                        # Если нет изменений, создаем две точки для демонстрации
                        cumulative_labels = ['Начало', 'Текущее']
                        cumulative_values = [current_value - step_increment, current_value]

                    # 2. ГРАФИК ПО ДНЯМ (последние 14 дней)
                    daily_counts = {}
                    for change in changes:
                        if 'moment' in change and change['moment']:
                            try:
                                day_key = change['moment'].strftime('%d.%m')
                                daily_counts[day_key] = daily_counts.get(day_key, 0) + 1
                            except:
                                pass

                    # Берем последние 14 дней для графика
                    if daily_counts:
                        daily_items = list(daily_counts.items())[-14:] if daily_counts else []
                        for day, count in daily_items:
                            daily_labels.append(day)
                            daily_values.append(count * step_increment)
                    else:
                        # Создаем тестовые данные, если нет реальных
                        daily_labels = ['01.01', '02.01', '03.01', '04.01']
                        daily_values = [step_increment * 2, step_increment * 3, step_increment * 1.5, step_increment * 2.5]

                    # Всегда должно быть минимум 2 точки
                    if len(daily_values) == 1:
                        daily_labels.append('День 2')
                        daily_values.append(daily_values[0] * 1.5)

                    # 3. ГРАФИК ПО МЕСЯЦАМ (последние 12 месяцев)
                    monthly_counts = {}
                    for change in changes:
                        if 'moment' in change and change['moment']:
                            try:
                                month_key = change['moment'].strftime('%Y-%m')
                                monthly_counts[month_key] = monthly_counts.get(month_key, 0) + 1
                            except:
                                pass

                    # Берем все месяцы с изменениями
                    if monthly_counts:
                        monthly_items = []
                        for month, count in monthly_counts.items():
                            # Форматируем месяц
                            try:
                                date_obj = datetime.strptime(month, '%Y-%m')
                                month_label = date_obj.strftime('%b %Y')
                            except:
                                month_label = month
                            monthly_labels.append(month_label)
                            monthly_values.append(count * step_increment)
                    else:
                        # Создаем тестовые данные
                        monthly_labels = ['Янв', 'Фев', 'Мар', 'Апр']
                        monthly_values = [step_increment * 5, step_increment * 8, step_increment * 3, step_increment * 6]

                    # Всегда должно быть минимум 2 точки
                    if len(monthly_values) == 1:
                        monthly_labels.append('След.мес')
                        monthly_values.append(monthly_values[0] * 1.2)

            except Exception as e:
                logging.warning("No access to device_changes for device %s: %s", device_id, e)
                # Если нет доступа, показываем пустые графики
                cumulative_labels = ['Нет данных']
                cumulative_values = [current_value]
                daily_labels = ['Нет данных']
                daily_values = [0]
                monthly_labels = ['Нет данных']
                monthly_values = [0]

            # Формируем данные устройства
            device_data = {
                'id': device_id,
                'type_id': device[1] if len(device) > 1 else None,
                'pin': device[3] if len(device) > 3 else None,
                'mac_address': device[2] if len(device) > 2 else None,  # Добавляем MAC адрес
                'serial_number': device[4] if len(device) > 4 else 'Без номера',
                'scale_unit_id': device[5] if len(device) > 5 else None,
                'step_increment': step_increment,
                'indicator': current_value,
                'state': bool(device[9]) if len(device) > 9 else False,
                'total_changes': total_changes,
                'cumulative_labels': cumulative_labels,
                'cumulative_values': cumulative_values,
                'daily_labels': daily_labels,
                'daily_values': daily_values,
                'monthly_labels': monthly_labels,
                'monthly_values': monthly_values,
                'leak_alerts': leak_alerts,
                'has_leaks': len(leak_alerts) > 0,
                'check_url': f"/check_device/{device_id}"
            }

            devices_data.append(device_data)

        # Проверяем, является ли пользователь администратором
        user_is_admin = is_admin(session['userid'])

        return render_template(
            'dashboard.html', 
            username=session['username'],
            devices=devices_data,
            current_time=datetime.now(),
            is_admin=user_is_admin  # Передаем флаг администратора в шаблон
        )

    except SQLAlchemyError as ex:
        logging.error("Database error in dashboard: %s", ex)
        return render_template('error.html', error="Ошибка получения данных")
    finally:
        if connect:
            close_connection(connect)

@app.route('/connect_device', methods=['POST'])
def connect_device():
    """ Метод подключения устройств """
    mac_address = None
    if request.is_json:
        data = request.get_json()
        if 'mac_address' in data:
            mac_address = data['mac_address']
    else:
        if 'mac_address' in request.args:
            mac_address = request.args['mac_address']
    if mac_address is None:
        return json_error(400, "Invalid request parameters"), 400

    connect = connect_database()
    if connect is None:
        return json_error(500, "Database connection error"), 500

    try:
        logging.info("Connection attempt for MAC: %s", mac_address)
        query = text("select * from public.find_device(:mac_address)")
        result = connect.execute(query, {"mac_address": mac_address})
        rows = result.fetchall()

        if rows is None or len(rows) == 0:
            return json_error(401, "Unauthorized"), 401

        devices = []
        for row in rows:
            logging.info("row.id: %s row.pin %s", row.id, row.pin)
            if row.id:
                devices.append({"id": row.id, "pin:": row.pin})

        if not devices:
            return json_error(401, "Unauthorized"), 401

        access_token = create_access_token(identity=mac_address)
        result_data = {
            "error": {},
            "result": {
                "devices": devices,
                "access_token": access_token
            }
        }
        return jsonify(result_data)

    except SQLAlchemyError as ex:
        logging.error("Database error in connect_device: %s", ex)
        return json_error(500, "Database error"), 500
    except Exception as ex:
        logging.error("Unexpected error in connect_device: %s", ex)
        return json_error(500, "Internal server error"), 500
    finally:
        if connect:
            close_connection(connect)

# ============================================================================
# КЛЮЧЕВОЙ МАРШРУТ - АВТОМАТИЧЕСКАЯ ОТПРАВКА ПРИ ИЗМЕНЕНИЯХ
# ============================================================================
@app.route('/debug_admin')
def debug_admin():
    """Диагностика прав администратора"""
    result = "<h1>Диагностика администратора</h1>"

    # Проверяем сессию
    result += "<h2>Данные сессии:</h2>"
    result += f"<p>session.get('username'): {session.get('username')}</p>"
    result += f"<p>session.get('userid'): {session.get('userid')}</p>"
    result += f"<p>Все ключи в session: {list(session.keys())}</p>"

    if 'username' not in session:
        result += "<p style='color:red'>❌ Пользователь не авторизован!</p>"
        return result

    # Проверяем функцию is_admin
    user_id = session.get('userid')
    result += f"<h2>Проверка is_admin для user_id={user_id}:</h2>"

    try:
        is_admin_result = is_admin(user_id)
        result += f"<p>is_admin вернул: <strong>{is_admin_result}</strong></p>"
    except Exception as e:
        result += f"<p style='color:red'>Ошибка в is_admin: {e}</p>"

    # Прямой SQL запрос для проверки
    result += "<h2>Прямой SQL запрос:</h2>"
    connect = connect_database()
    if connect:
        try:
            query = text("""
                SELECT 
                    u.id, 
                    u.name, 
                    r.code, 
                    r.name as role_name
                FROM users u
                LEFT JOIN user_roles ur ON ur.user_id = u.id
                LEFT JOIN roles r ON ur.role_id = r.id
                WHERE u.id = :user_id
            """)
            result_rows = connect.execute(query, {"user_id": user_id})
            rows = result_rows.fetchall()

            if rows:
                result += "<table border='1' cellpadding='5'>"
                result += "<tr><th>ID</th><th>Имя</th><th>Код роли</th><th>Название роли</th></tr>"
                for row in rows:
                    result += f"<tr>"
                    result += f"<td>{row[0]}</td>"
                    result += f"<td>{row[1]}</td>"
                    result += f"<td>{row[2] if row[2] else 'Нет'}</td>"
                    result += f"<td>{row[3] if row[3] else 'Нет'}</td>"
                    result += f"</tr>"
                result += "</table>"
            else:
                result += "<p>Пользователь не найден</p>"

        except Exception as e:
            result += f"<p style='color:red'>Ошибка SQL: {e}</p>"
        finally:
            close_connection(connect)
    else:
        result += "<p style='color:red'>❌ Не удалось подключиться к БД</p>"

    # Проверяем, что рендерится в шаблоне
    result += "<h2>Проверка шаблона:</h2>"
    result += "<p>Перейдите на <a href='/'>главную страницу</a> и проверьте:</p>"
    result += "<ul>"
    result += "<li>Есть ли кнопка 'Администрирование'?</li>"
    result += "<li>Посмотрите исходный код страницы (Ctrl+U) и найдите 'btn-admin'</li>"
    result += "</ul>"

    return result

@app.route('/add_device_changes', methods=['POST'])
@jwt_required()
def add_device_changes():
    """ Запись об изменении показания устройства с АВТОМАТИЧЕСКОЙ отправкой email """
    changes = None
    mac_address = get_jwt_identity()

    if request.is_json:
        data = request.get_json()
    else:
        data = request.args

    if 'changes' not in data:
        if 'device_id' in data and 'moment' in data:
            changes = [
                {
                    'device_id': data.get('device_id'),
                    'moment': data.get('moment')
                }
            ]
    else:
        change_list = data.get('changes')
        if isinstance(change_list, list):
            changes = []
            for change in change_list:
                if 'device_id' in change and 'moment' in change:
                    changes.append(
                        {
                            'device_id': change.get('device_id'),
                            'moment': change.get('moment')
                        }
                    )

    if changes is None or not changes:
        return json_error(400, "Missing required parameters: device_id and moment"), 400

    connect = connect_database()
    if connect is None:
        return json_error(500, "Database connection error"), 500

    try:
        # Получаем информацию об устройстве перед добавлением изменений
        device_info = {}
        for change in changes:
            device_id = change.get('device_id')
            query_device = text("""
                SELECT d.serial_number, d.step_increment 
                FROM devices d
                WHERE d.id = :device_id AND d.state = true
            """)
            result = connect.execute(query_device, {"device_id": device_id})
            row = result.fetchone()

            if row:
                device_info[device_id] = {
                    'serial_number': row[0] if row[0] else f'Устройство {device_id}',
                    'step_increment': float(row[1]) if row[1] else 10.0
                }

        # Выполняем добавление изменений
        query = text("call public.add_device_changes(:mac_address, :device_id, :moment)")
        logging.info("start add_device_changes")
        if connect.in_transaction():
            logging.info("in transaction before")
            connect.commit()
        with connect.begin():
            for change in changes:
                device_id = change.get('device_id')
                connect.execute(query, {
                    "mac_address": mac_address,
                    "device_id": device_id,
                    "moment": change.get('moment')
                })
        if connect.in_transaction():
            logging.info("in transaction after")
            connect.commit()
        logging.info("add_device_changes commit")

        # АВТОМАТИЧЕСКАЯ ОТПРАВКА EMAIL В ОТДЕЛЬНОМ ПОТОКЕ
        if device_id in device_info:
            # Получаем ОБНОВЛЕННОЕ значение после добавления изменения
            query_updated = text("SELECT indicator FROM devices WHERE id = :device_id")
            result_updated = connect.execute(query_updated, {"device_id": device_id})
            row_updated = result_updated.fetchone()

            if row_updated:
                updated_value = float(row_updated[0]) if row_updated[0] else 0.0
                serial_number = device_info[device_id]['serial_number']

                # Запускаем проверку утечек в отдельном потоке
                thread = threading.Thread(
                    target=send_automatic_leak_email,
                    args=(device_id, updated_value, serial_number)
                )
                thread.daemon = True
                thread.start()

                logging.info("Запущена автоматическая проверка утечек для устройства %s", device_id)
                logging.info("Текущее значение: %s, Серийный номер: %s", updated_value, serial_number)

        result_data = {
            "error": {},
            "result": {
                "success": True,
                "message": "Изменения добавлены и запущена проверка утечек"
            }
        }
        return jsonify(result_data)

    except SQLAlchemyError as ex:
        logging.error("Database error in add_device_changes: %s", ex)
        return json_error(500, "Database error"), 500
    except Exception as ex:
        logging.error("Unexpected error in add_device_changes: %s", ex)
        return json_error(500, "Internal server error"), 500
    finally:
        if connect:
            close_connection(connect)

# ============================================================================
# НОВЫЙ МАРШРУТ - ПРОВЕРКА КОНКРЕТНОГО УСТРОЙСТВА
# ============================================================================

@app.route('/check_device/<int:device_id>')
def check_single_device_route(device_id):
    """ Проверяет конкретное устройство на утечки """
    if 'username' not in session:
        return redirect(url_for('hello_world'))

    # Получаем информацию об устройстве
    connect = connect_database()
    if connect is None:
        return jsonify({"error": "Ошибка подключения к БД"})

    try:
        query = text("SELECT * FROM public.get_devices(:user_id)")
        result = connect.execute(query, {"user_id": session['userid']})
        devices = result.fetchall()

        # Ищем нужное устройство
        target_device = None
        for device in devices:
            if device[0] == device_id:
                target_device = device
                break

        if not target_device:
            return jsonify({"error": "Устройство не найдено"})

        serial_number = target_device[4] if len(target_device) > 4 else f'Устройство {device_id}'
        current_value = float(target_device[7]) if len(target_device) > 7 and target_device[7] is not None else 0.0

        # Проверяем утечки
        result = check_single_device_for_leaks(device_id, serial_number, current_value)

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": f"Ошибка: {e}"})
    finally:
        if connect:
            close_connection(connect)

@app.route('/check_all_devices')
def check_all_devices_route():
    """ Проверяет ВСЕ устройства пользователя на утечки """
    if 'username' not in session:
        return redirect(url_for('hello_world'))

    connect = connect_database()
    if connect is None:
        return jsonify({"error": "Ошибка подключения к БД"})

    try:
        query = text("SELECT * FROM public.get_devices(:user_id)")
        result = connect.execute(query, {"user_id": session['userid']})
        devices = result.fetchall()

        results = []
        total_leaks = 0

        for device in devices:
            device_id = device[0] if len(device) > 0 else None
            serial_number = device[4] if len(device) > 4 else f'Устройство {device_id}'
            current_value = float(device[7]) if len(device) > 7 and device[7] is not None else 0.0

            # Проверяем утечки
            result = check_single_device_for_leaks(device_id, serial_number, current_value)

            if 'leak_count' in result and result['leak_count'] > 0:
                total_leaks += result['leak_count']

            results.append({
                "device_id": device_id,
                "serial_number": serial_number,
                "result": result
            })

        return jsonify({
            "success": True,
            "total_devices": len(devices),
            "total_leaks": total_leaks,
            "results": results
        })

    except Exception as e:
        return jsonify({"error": f"Ошибка: {e}"})
    finally:
        if connect:
            close_connection(connect)

# ============================================================================
# ТЕСТОВЫЙ МАРШРУТ ДЛЯ ПРОВЕРКИ ВСЕХ УСТРОЙСТВ
# ============================================================================

@app.route('/test_all_leaks')
def test_all_leaks():
    """
    Тестовый маршрут для проверки ВСЕХ устройств на утечки
    """
    if 'username' not in session:
        return redirect(url_for('hello_world'))

    try:
        # Используем API для проверки всех устройств
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Тест всех устройств</title>
            <script>
                function checkAllDevices() {{
                    document.getElementById('results').innerHTML = '<p>Проверяем все устройства...</p>';
                    
                    fetch('/check_all_devices')
                        .then(response => response.json())
                        .then(data => {{
                            let html = '<h3>Результаты проверки:</h3>';
                            html += '<p>Всего устройств: ' + data.total_devices + '</p>';
                            html += '<p>Всего утечек: ' + data.total_leaks + '</p>';
                            html += '<hr>';
                            
                            data.results.forEach(device => {{
                                html += '<div style="margin: 10px; padding: 10px; border: 1px solid #ccc; border-radius: 5px;">';
                                html += '<strong>Устройство:</strong> ' + device.serial_number + '<br>';
                                
                                if (device.result.error) {{
                                    html += '<span style="color: red;">Ошибка: ' + device.result.error + '</span>';
                                }} else if (device.result.info) {{
                                    html += '<span style="color: blue;">' + device.result.info + '</span>';
                                }} else if (device.result.leak_count > 0) {{
                                    html += '<span style="color: red; font-weight: bold;">Обнаружено утечек: ' + device.result.leak_count + '</span><br>';
                                    
                                    if (device.result.email_sent) {{
                                        html += '<span style="color: green;">Email отправлен на: ' + device.result.email_address + '</span>';
                                    }}
                                }} else {{
                                    html += '<span style="color: green;">Утечек не обнаружено</span>';
                                }}
                                
                                html += '</div>';
                            }});
                            
                            document.getElementById('results').innerHTML = html;
                        }})
                        .catch(error => {{
                            document.getElementById('results').innerHTML = '<p style="color: red;">Ошибка: ' + error + '</p>';
                        }});
                }}
            </script>
        </head>
        <body style="padding: 40px; font-family: Arial;">
            <h1 style="color: blue;">ТЕСТ ВСЕХ УСТРОЙСТВ НА УТЕЧКИ</h1>
            <p>Эта страница проверяет ВСЕ ваши устройства на наличие утечек.</p>
            <p>При обнаружении утечек автоматически отправляется email.</p>
            
            <button onclick="checkAllDevices()" style="
                padding: 15px 30px;
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 16px;
                cursor: pointer;
                margin: 20px 0;
            ">
                ПРОВЕРИТЬ ВСЕ УСТРОЙСТВА
            </button>
            
            <div id="results" style="margin-top: 20px; padding: 20px; background: #f5f5f5; border-radius: 5px;"></div>
            
            <br><br>
            <a href="/dashboard">Вернуться на панель управления</a>
        </body>
        </html>
        """
    except Exception as e:
        return f"Ошибка: {e}"

# ============================================================================
# АДМИНИСТРАТИВНЫЕ МАРШРУТЫ
# ============================================================================

@app.route('/admin')
def admin_panel():
    """Панель администрирования"""
    if 'username' not in session:
        logging.warning("Попытка доступа к админке без авторизации")
        return redirect(url_for('hello_world'))

    user_id = session.get('userid')
    username = session.get('username')

    logging.info(f"Проверка прав администратора для пользователя {username} (ID: {user_id})")

    # Проверяем права администратора
    if not is_admin(user_id):
        logging.warning(f"Пользователь {username} (ID: {user_id}) не имеет прав администратора")
        return render_template('error.html', error="У вас нет прав доступа к этой странице")

    logging.info(f"Пользователь {username} (ID: {user_id}) имеет права администратора, открываем панель")

    connect = connect_database()
    if connect is None:
        logging.error("Не удалось подключиться к БД для админ-панели")
        return render_template('error.html', error="Ошибка подключения к БД")

    try:
        # Получаем всех пользователей
        query_users = text("""
            SELECT u.id, u.name, u.email, u.surname, u.state,
                   (SELECT COUNT(*) FROM devices d WHERE d.user_id = u.id) as device_count
            FROM users u
            ORDER BY u.name
        """)
        users_result = connect.execute(query_users)
        users = []
        for row in users_result:
            users.append({
                'id': row[0],
                'name': row[1],
                'email': row[2],
                'surname': row[3],
                'state': row[4],
                'device_count': row[5]
            })

        logging.info(f"Загружено {len(users)} пользователей")

        # Получаем типы устройств
        query_types = text("SELECT id, name FROM device_types WHERE state = true ORDER BY name")
        types_result = connect.execute(query_types)
        device_types = [{'id': row[0], 'name': row[1]} for row in types_result]

        # Получаем единицы измерения
        query_units = text("SELECT id, name FROM units ORDER BY name")
        units_result = connect.execute(query_units)
        units = [{'id': row[0], 'name': row[1]} for row in units_result]

        return render_template(
            'admin.html',
            username=username,
            total_users=len(users),
            users=users,
            device_types=device_types,
            units=units
        )

    except Exception as e:
        logging.error(f"Ошибка в admin_panel: {e}")
        return render_template('error.html', error=f"Ошибка: {e}")
    finally:
        close_connection(connect)

@app.route('/api/user/<int:user_id>')
def get_user_api(user_id):
    """API для получения данных пользователя"""
    if 'username' not in session or not is_admin(session['userid']):
        return jsonify({"error": "Доступ запрещен"}), 403

    connect = connect_database()
    if connect is None:
        return jsonify({"error": "Ошибка подключения к БД"}), 500

    try:
        # Получаем данные пользователя
        query_user = text("""
            SELECT id, name, email, surname, state
            FROM users
            WHERE id = :user_id
        """)
        user_result = connect.execute(query_user, {"user_id": user_id})
        user_row = user_result.fetchone()

        if not user_row:
            return jsonify({"error": "Пользователь не найден"}), 404

        # Получаем устройства пользователя
        query_devices = text("""
            SELECT d.id, d.serial_number, d.mac_address, d.pin, d.step_increment,
                   d.indicator, d.state, dt.name as type_name, d.type_id,
                   u.name as unit_name, d.scale_unit_id
            FROM devices d
            LEFT JOIN device_types dt ON d.type_id = dt.id
            LEFT JOIN units u ON d.scale_unit_id = u.id
            WHERE d.user_id = :user_id
            ORDER BY d.serial_number
        """)
        devices_result = connect.execute(query_devices, {"user_id": user_id})

        devices = []
        for row in devices_result:
            devices.append({
                'id': row[0],
                'serial_number': row[1],
                'mac_address': row[2],
                'pin': row[3],
                'step_increment': float(row[4]) if row[4] else None,
                'indicator': float(row[5]) if row[5] else None,
                'state': row[6],
                'type_name': row[7],
                'type_id': row[8],
                'unit_name': row[9],
                'scale_unit_id': row[10]
            })

        return jsonify({
            'id': user_row[0],
            'name': user_row[1],
            'email': user_row[2],
            'surname': user_row[3],
            'state': user_row[4],
            'devices': devices
        })

    except Exception as e:
        logging.error(f"Ошибка в get_user_api: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        close_connection(connect)

@app.route('/api/device/<int:device_id>')
def get_device_api(device_id):
    """API для получения данных устройства"""
    if 'username' not in session or not is_admin(session['userid']):
        return jsonify({"error": "Доступ запрещен"}), 403

    connect = connect_database()
    if connect is None:
        return jsonify({"error": "Ошибка подключения к БД"}), 500

    try:
        query = text("""
            SELECT id, type_id, mac_address, pin, serial_number,
                   scale_unit_id, step_increment, indicator, user_id, state
            FROM devices
            WHERE id = :device_id
        """)
        result = connect.execute(query, {"device_id": device_id})
        row = result.fetchone()

        if not row:
            return jsonify({"error": "Устройство не найдено"}), 404

        return jsonify({
            'id': row[0],
            'type_id': row[1],
            'mac_address': row[2],
            'pin': row[3],
            'serial_number': row[4],
            'scale_unit_id': row[5],
            'step_increment': float(row[6]) if row[6] else None,
            'indicator': float(row[7]) if row[7] else None,
            'user_id': row[8],
            'state': row[9]
        })

    except Exception as e:
        logging.error(f"Ошибка в get_device_api: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        close_connection(connect)

@app.route('/api/save_user', methods=['POST'])
def save_user_api():
    """API для сохранения пользователя"""
    if 'username' not in session or not is_admin(session['userid']):
        return jsonify({"error": "Доступ запрещен"}), 403

    data = request.json
    connect = connect_database()
    if connect is None:
        return jsonify({"error": "Ошибка подключения к БД"}), 500

    try:
        user_id = data.get('user_id')
        name = data.get('username')
        email = data.get('email')
        surname = data.get('full_name')
        state = data.get('state') in [True, 'true', 'on', 1]

        if user_id:
            # Обновляем существующего пользователя
            query = text("""call public.update_user(:user_id, :name, :email, :surname, :state)""")
            connect.execute(query, {
                "user_id": user_id,
                "name": name,
                "email": email,
                "surname": surname,
                "state": state
            })
            connect.commit()
        else:
            # Создаем нового пользователя с временным паролем
            temp_password = "changeme"
            query = text("""select public.add_user(:name, :email, :surname, :password, :state) as id""")
            result = connect.execute(query, {
                "name": name,
                "email": email,
                "surname": surname,
                "password": temp_password,
                "state": state
            })
            user_id = result.fetchone()[0]
            connect.commit()

        return jsonify({"success": True, "user_id": user_id})

    except Exception as e:
        connect.rollback()
        logging.error(f"Ошибка в save_user_api: {e}")
        return jsonify({"error": "Ошибка сохранения данных"}), 500
    finally:
        close_connection(connect)

@app.route('/api/save_device', methods=['POST'])
def save_device_api():
    """API для сохранения устройства"""
    if 'username' not in session or not is_admin(session['userid']):
        return jsonify({"error": "Доступ запрещен"}), 403

    data = request.json
    connect = connect_database()
    if connect is None:
        return jsonify({"error": "Ошибка подключения к БД"}), 500

    try:
        device_id = data.get('device_id')
        type_id = data.get('type_id')
        mac_address = data.get('mac_address')
        pin = data.get('pin')
        serial_number = data.get('serial_number')
        scale_unit_id = data.get('scale_unit_id')
        step_increment = float(data.get('step_increment', 0))
        indicator = float(data.get('indicator', 0))
        user_id = data.get('user_id')
        state = data.get('state') in [True, 'true', 'on', 1]

        if device_id:
            # Обновляем существующее устройство
            query = text("""call public.update_device(:device_id, :type_id, :mac_address, :pin,
                         :serial_number, :scale_unit_id, :step_increment, :indicator, :state)
            """)
            connect.execute(query, {
                "device_id": device_id,
                "type_id": type_id,
                "mac_address": mac_address,
                "pin": pin,
                "serial_number": serial_number,
                "scale_unit_id": scale_unit_id,
                "step_increment": step_increment,
                "indicator": indicator,
                "state": state
            })
        else:
            # Создаем новое устройство
            query = text("""select public.add_device(:type_id, :mac_address, :pin, :serial_number,
                       :scale_unit_id, :step_increment, :indicator, :user_id, :state)
            """)
            connect.execute(query, {
                "type_id": type_id,
                "mac_address": mac_address,
                "pin": pin,
                "serial_number": serial_number,
                "scale_unit_id": scale_unit_id,
                "step_increment": step_increment,
                "indicator": indicator,
                "user_id": user_id,
                "state": state
            })

        connect.commit()
        return jsonify({"success": True})

    except Exception as e:
        connect.rollback()
        logging.error(f"Ошибка в изменения данных об устройстве: {e}")
        return jsonify({"error": "Ошибка в изменения данных об устройстве"}), 500
    finally:
        close_connection(connect)

@app.route('/api/change_password', methods=['POST'])
def change_password_api():
    """API для изменения пароля пользователя"""
    if 'username' not in session or not is_admin(session['userid']):
        return jsonify({"error": "Доступ запрещен"}), 403

    data = request.json
    user_id = data.get('user_id')
    password = data.get('password')

    if not user_id or not password:
        return jsonify({"error": "Не указан пользователь или пароль"}), 400

    connect = connect_database()
    if connect is None:
        return jsonify({"error": "Ошибка подключения к БД"}), 500

    try:
        query = text("""call public.change_password(:user_id, :password)""")
        connect.execute(query, {
            "user_id": user_id,
            "password": password
        })
        connect.commit()

        return jsonify({"success": True})

    except Exception as e:
        connect.rollback()
        logging.error(f"Ошибка в change_password_api: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        close_connection(connect)

# ============================================================================
# ДОПОЛНИТЕЛЬНЫЕ МАРШРУТЫ
# ============================================================================

@app.route('/email_stats')
def email_stats():
    """Возвращает статистику отправки email"""
    try:
        stats = email_sender.get_stats()
        return jsonify(stats)
    except:
        return jsonify({"error": "Не удалось получить статистику"})

# ============================================================================
# ТЕСТОВЫЙ EMAIL С РЕАЛЬНЫМИ ДАННЫМИ
# ============================================================================

@app.route('/send_real_test_email')
def send_real_test_email():
    """Отправляет тестовый email с реальными данными из БД"""
    if 'username' not in session:
        return redirect(url_for('hello_world'))

    try:
        connect = connect_database()
        if connect is None:
            return jsonify({"error": "Не удалось подключиться к БД"})

        # Получаем данные пользователя
        user_query = text("""
            SELECT u.email, u.name 
            FROM users u 
            WHERE u.id = :user_id AND u.state = true
        """)
        user_result = connect.execute(user_query, {"user_id": session['userid']})
        user_row = user_result.fetchone()

        if not user_row:
            return jsonify({"error": "Пользователь не найден"})

        user_email = user_row[0]
        user_name = user_row[1]

        if not user_email:
            return jsonify({"error": "У пользователя нет email"})

        # Получаем данные первого устройства пользователя
        device_query = text("""
            SELECT d.id, d.serial_number, d.step_increment, d.indicator
            FROM devices d 
            WHERE d.user_id = :user_id AND d.state = true
            LIMIT 1
        """)
        device_result = connect.execute(device_query, {"user_id": session['userid']})
        device_row = device_result.fetchone()

        if not device_row:
            # Если нет реального устройства, создаем тестовые данные
            device_info = {
                'id': 999,
                'serial_number': 'TEST-DEVICE',
                'step_increment': 10.0,
                'indicator': 123.456
            }

            # Получаем статистику из БД
            stats_query = text("""
                SELECT 
                    COUNT(*) as total_devices,
                    COUNT(CASE WHEN state = true THEN 1 END) as active_devices,
                    COUNT(DISTINCT user_id) as total_users
                FROM devices
            """)
            stats_result = connect.execute(stats_query)
            stats_row = stats_result.fetchone()
        else:
            device_info = {
                'id': device_row[0],
                'serial_number': device_row[1],
                'step_increment': float(device_row[2]),
                'indicator': float(device_row[3])
            }

            # Получаем статистику изменений для этого устройства
            stats_query = text("""
                SELECT COUNT(*) as total_changes
                FROM device_changes 
                WHERE device_id = :device_id
            """)
            stats_result = connect.execute(stats_query, {"device_id": device_info['id']})
            stats_row = stats_result.fetchone()

        # Создаем тестовые алерты с реальной информацией
        test_alerts = [{
            'message': 'Тестовое уведомление системы FoxDen',
            'severity': 'medium',
            'type': 'test',
            'detected_at': datetime.now().strftime('%d.%m.%Y %H:%M'),
            'recommendation': 'Это тестовое сообщение для проверки работы системы. Все системы работают нормально.',
            'details': {
                'user': user_name,
                'device_count': stats_row[0] if stats_row else 1,
                'current_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'system_status': 'работает нормально'
            }
        }]

        # Отправляем email
        success = email_sender.send_leak_alert(
            user_email=user_email,
            device_info=device_info,
            leak_alerts=test_alerts
        )

        close_connection(connect)

        if success:
            # Логируем отправку
            try:
                log_file = "test_emails.log"
                with open(log_file, "a", encoding="utf-8") as f:
                    f.write(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ")
                    f.write(f"Тестовое письмо отправлено на {user_email} - ")
                    f.write(f"Устройство: {device_info['serial_number']} - ")
                    f.write(f"Показание: {device_info['indicator']}\n")
            except Exception as log_error:
                logging.warning("Ошибка записи лога тестового email: %s", log_error)

            return jsonify({
                "success": True,
                "message": f"Тестовое письмо отправлено на {user_email}",
                "email": user_email,
                "device": device_info['serial_number'],
                "indicator": device_info['indicator']
            })
        else:
            return jsonify({
                "error": "Не удалось отправить тестовое письмо",
                "email": user_email
            })

    except Exception as e:
        logging.error("Ошибка отправки тестового письма: %s", e)
        return jsonify({"error": f"Ошибка: {str(e)}"})

@app.route('/get_logs')
def get_logs():
    """Возвращает содержимое лог-файлов"""
    if 'username' not in session:
        return redirect(url_for('hello_world'))

    log_file = request.args.get('file', 'leak_notifications.log')

    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return f"<pre>{content}</pre>"
    except FileNotFoundError:
        return f"Файл {log_file} не найден"

# ============================================================================
# ЗАПУСК СЕРВЕРА
# ============================================================================

if __name__ == '__main__':
    logging.info("Запуск FoxDen сервера...")

    # Проверка email системы
    if email_sender.enabled:
        logging.info("Email система доступна")
    else:
        logging.warning("Email система отключена. Настройте .env файл")

    # Запускаем фоновый мониторинг
    if email_sender.enabled:
        monitor = start_background_monitoring(15)  # Проверка каждые 15 минут
        logging.info("Фоновый мониторинг утечек запущен")

    # Запускаем сервер
    if config.DEBUG_MODE:
        logging.info("Сервер запускается на http://127.0.0.1:5000")
        app.run(debug=config.DEBUG_MODE, host='127.0.0.1', port=5000)
    else:
        logging.info("Сервер запускается в боевом режиме")
        app.run()
