"""
FoxDen Email Notification System
Простая и надежная система отправки email уведомлений об утечках
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import os
from datetime import datetime
from typing import List, Dict, Any
import time

logger = logging.getLogger(__name__)


class FoxDenEmailSender:
    """
    Класс для отправки email уведомлений в системе FoxDen
    Использует SMTP с поддержкой TLS/SSL
    """

    def __init__(self):
        # Загружаем конфигурацию из переменных окружения
        self._load_config()

        # Проверяем настройки
        self._validate_config()

        # Статистика отправки
        self.stats = {
            'sent': 0,
            'failed': 0,
            'last_success': None,
            'last_error': None
        }

        logger.info(f"FoxDen Email Sender initialized for {self.username}")

    def _load_config(self):
        """Загружает конфигурацию из переменных окружения"""
        # Основные настройки SMTP
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.username = os.getenv('SMTP_USERNAME', '')
        self.password = os.getenv('SMTP_PASSWORD', '')

        # Настройки отправителя
        self.sender_email = os.getenv('SMTP_SENDER_EMAIL', self.username or 'noreply@foxden.ru')
        self.sender_name = os.getenv('SMTP_SENDER_NAME', 'FoxDen System')

        # Дополнительные настройки
        self.use_tls = os.getenv('SMTP_USE_TLS', 'True').lower() == 'true'
        self.use_ssl = os.getenv('SMTP_USE_SSL', 'False').lower() == 'true'
        self.timeout = int(os.getenv('SMTP_TIMEOUT', '30'))

        # Максимальное количество попыток отправки
        self.max_retries = int(os.getenv('SMTP_MAX_RETRIES', '3'))
        self.retry_delay = int(os.getenv('SMTP_RETRY_DELAY', '5'))

        # Проверка включения системы
        self.enabled = bool(self.username and self.password and self.smtp_server)

    def _validate_config(self):
        """Проверяет корректность конфигурации"""
        if not self.enabled:
            logger.warning("FoxDen Email Sender is DISABLED")
            logger.warning("To enable, set SMTP_USERNAME and SMTP_PASSWORD in .env file")
            return

        # Проверяем email отправителя
        if '@' not in self.sender_email or '.' not in self.sender_email:
            logger.warning(f"Invalid sender email: {self.sender_email}")

        # Логируем настройки (без пароля)
        logger.info("SMTP Configuration:")
        logger.info(f"  Server: {self.smtp_server}:{self.smtp_port}")
        logger.info(f"  Username: {self.username}")
        logger.info(f"  Sender: {self.sender_name} <{self.sender_email}>")
        logger.info(f"  TLS: {self.use_tls}, SSL: {self.use_ssl}")
        logger.info(f"  Timeout: {self.timeout}s, Retries: {self.max_retries}")

    def send_leak_alert(self, user_email: str, device_info: Dict[str, Any],
                       leak_alerts: List[Dict[str, Any]]) -> bool:
        """
        Отправляет уведомление об утечке пользователю

        Args:
            user_email: Email адрес пользователя
            device_info: Информация об устройстве (счетчике)
            leak_alerts: Список обнаруженных утечек
        
        Returns:
            bool: True если отправка успешна, False если ошибка
        """
        # Проверяем включена ли система
        if not self.enabled:
            logger.info(f"[EMAIL DISABLED] Would send leak alert to: {user_email}")
            logger.info(f"[EMAIL DISABLED] Device: {device_info.get('serial_number', 'Unknown')}")
            logger.info(f"[EMAIL DISABLED] Alerts: {len(leak_alerts)}")
            return True  # Возвращаем True чтобы система продолжала работу

        # Валидация email
        if not self._validate_email(user_email):
            logger.error(f"Invalid email address: {user_email}")
            return False

        # Проверяем есть ли утечки для отправки
        if not leak_alerts:
            logger.warning("No leak alerts to send")
            return False

        try:
            # Создаем email сообщение
            msg = self._create_leak_email(user_email, device_info, leak_alerts)

            # Отправляем с повторными попытками
            success = self._send_with_retry(msg, user_email)

            # Обновляем статистику
            if success:
                self.stats['sent'] += 1
                self.stats['last_success'] = datetime.now()
                logger.info(f"Leak alert sent to {user_email}")
            else:
                self.stats['failed'] += 1
                self.stats['last_error'] = datetime.now()
                logger.error(f"Failed to send leak alert to {user_email}")

            return success

        except Exception as e:
            logger.error(f"Unexpected error sending leak alert: {e}")
            self.stats['failed'] += 1
            return False

    def _create_leak_email(self, user_email: str, device_info: Dict[str, Any],
                          leak_alerts: List[Dict[str, Any]]) -> MIMEMultipart:
        """Создает MIME сообщение об утечке"""
        msg = MIMEMultipart('alternative')

        # Заголовки письма
        subject = self._create_subject(device_info, leak_alerts)
        msg['Subject'] = Header(subject, 'utf-8')
        msg['From'] = f"{self.sender_name} <{self.sender_email}>"
        msg['To'] = user_email
        msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')

        # Создаем текстовую и HTML версии
        text_content = self._create_text_content(device_info, leak_alerts)
        html_content = self._create_html_content(device_info, leak_alerts)

        msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))

        return msg

    def _send_with_retry(self, msg: MIMEMultipart, user_email: str) -> bool:
        """Отправляет email с повторными попытками"""
        for attempt in range(self.max_retries):
            try:
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt + 1}/{self.max_retries} for {user_email}")
                    time.sleep(self.retry_delay)

                return self._send_email(msg)

            except (smtplib.SMTPException, TimeoutError, ConnectionError) as e:
                logger.warning(f"Attempt {attempt + 1} failed for {user_email}: {e}")

                if attempt == self.max_retries - 1:
                    logger.error(f"All {self.max_retries} attempts failed for {user_email}")
                    return False

        return False

    def _send_email(self, msg: MIMEMultipart) -> bool:
        """Отправляет email через SMTP сервер"""
        try:
            # Выбираем тип соединения
            if self.use_ssl:
                # SSL соединение (обычно порт 465)
                server = smtplib.SMTP_SSL(
                    host=self.smtp_server,
                    port=self.smtp_port,
                    timeout=self.timeout
                )
            else:
                # Обычное соединение с возможным STARTTLS
                server = smtplib.SMTP(
                    host=self.smtp_server,
                    port=self.smtp_port,
                    timeout=self.timeout
                )
                server.ehlo()

                # Включаем TLS если нужно
                if self.use_tls and server.has_extn('STARTTLS'):
                    server.starttls()
                    server.ehlo()

            # Авторизация
            server.login(self.username, self.password)

            # Отправка
            server.send_message(msg)
            server.quit()

            return True

        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP authentication failed: {e}")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return False
        except TimeoutError as e:
            logger.error(f"SMTP connection timeout: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during email sending: {e}")
            return False

    def _validate_email(self, email: str) -> bool:
        """Простая валидация email адреса"""
        if not email or '@' not in email or '.' not in email:
            return False
        return True

    def _create_subject(self, device_info: Dict[str, Any],
                       leak_alerts: List[Dict[str, Any]]) -> str:
        """Создает тему письма"""
        serial = device_info.get('serial_number', 'Счетчик')

        # Определяем максимальную серьезность
        severities = [alert.get('severity', 'medium') for alert in leak_alerts]

        if 'critical' in severities:
            return f"КРИТИЧЕСКАЯ УТЕЧКА: {serial} - ТРЕБУЕТСЯ НЕМЕДЛЕННОЕ ВНИМАНИЕ!"
        elif 'high' in severities:
            return f"ВНИМАНИЕ: Обнаружена утечка на счетчике {serial}"
        else:
            return f"Уведомление: Аномалия потребления на счетчике {serial}"

    def _create_text_content(self, device_info: Dict[str, Any],
                           leak_alerts: List[Dict[str, Any]]) -> str:
        """Создает текстовую версию письма"""
        serial = device_info.get('serial_number', 'Неизвестный счетчик')
        indicator = device_info.get('indicator', 0)
        detected_at = leak_alerts[0].get('detected_at', 'Неизвестно') if leak_alerts else 'Неизвестно'

        text = """FOXDEN - СИСТЕМА МОНИТОРИНГА УТЕЧЕК ВОДЫ
{'=' * 60}

ОБНАРУЖЕНЫ ПРОБЛЕМЫ НА СЧЕТЧИКЕ: {serial}
Текущее показание: {indicator:.3f} м³
Время обнаружения: {detected_at}

{'=' * 60}
ДЕТАЛЬНАЯ ИНФОРМАЦИЯ ОБ УТЕЧКАХ:
{'=' * 60}
"""

        for i, alert in enumerate(leak_alerts, 1):
            message = alert.get('message', 'Обнаружена аномалия потребления')
            severity = alert.get('severity', 'medium').upper()
            recommendation = alert.get('recommendation', 'Рекомендуется проверить систему')

            text += f"\n{i}. {message}"
            text += f"\n   Уровень серьезности: {severity}"
            text += f"\n   Рекомендация: {recommendation}"

            # Добавляем детали если есть
            if 'details' in alert:
                details = alert['details']
                if alert.get('type') == 'long_continuous_usage':
                    text += f"\n   Продолжительность: {details.get('total_duration_minutes', 0):.1f} минут"
                    text += f"\n   Объем утечки: {details.get('total_volume', 0):.3f} м³"
                elif alert.get('type') == 'night_usage':
                    text += f"\n   Ночных изменений: {details.get('night_changes_count', 0)}"
                    text += f"\n   Объем за ночь: {details.get('night_volume', 0):.3f} м³"
                    text += f"\n   Период: {details.get('period', '00:00-06:00')}"

            text += "\n"

        text += f"""
{'=' * 60}
РЕКОМЕНДУЕМЫЕ ДЕЙСТВИЯ:
1. Проверьте все краны, смесители и соединения труб
2. Убедитесь, что бачок унитаза не течет
3. Отключите стиральную и посудомоечную машины, проверьте их соединения
4. Осмотрите видимые трубопроводы на предмет влажности или капель
5. Проверьте счетчик на наличие видимых повреждений
6. При необходимости вызовите сантехника

{'=' * 60}
КОНТАКТНАЯ ИНФОРМАЦИЯ:
• Система: {self.sender_name}
• Email для связи: {self.sender_email}
• Время отправки: {datetime.now().strftime('%d.%m.%Y %H:%M')}

{'=' * 60}
Это автоматическое сообщение от системы мониторинга FoxDen.
Не отвечайте на это письмо.
"""
        return text

    def _create_html_content(self, device_info: Dict[str, Any],
                           leak_alerts: List[Dict[str, Any]]) -> str:
        """Создает HTML версию письма"""
        serial = device_info.get('serial_number', 'Неизвестный счетчик')
        indicator = device_info.get('indicator', 0)
        detected_at = leak_alerts[0].get('detected_at', 'Неизвестно') if leak_alerts else 'Неизвестно'

        # Генерируем HTML для каждого алерта
        alerts_html = ""
        for i, alert in enumerate(leak_alerts, 1):
            severity = alert.get('severity', 'medium')
            message = alert.get('message', '')
            recommendation = alert.get('recommendation', '')

            # Цвета в зависимости от серьезности
            if severity == 'critical':
                border_color = '#e74c3c'
                bg_color = '#ffeaea'
                severity_text = 'КРИТИЧЕСКИЙ'
            elif severity == 'high':
                border_color = '#f39c12'
                bg_color = '#fff0e6'
                severity_text = 'ВЫСОКИЙ'
            else:
                border_color = '#f1c40f'
                bg_color = '#fff8e1'
                severity_text = 'СРЕДНИЙ'

            alerts_html += f"""
            <div style="margin: 12px 0; padding: 15px; border-left: 5px solid {border_color}; 
                        background: {bg_color}; border-radius: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="font-weight: bold; font-size: 16px; color: #2c3e50;">
                        {i}. {message}
                    </div>
                    <div style="background: {border_color}; color: white; padding: 4px 12px; 
                                border-radius: 12px; font-size: 12px; font-weight: bold;">
                        {severity_text}
                    </div>
                </div>
                <div style="margin-top: 10px; padding: 8px 12px; background: #e8f4fc; 
                            border-radius: 4px; border-left: 3px solid #3498db;">
                    <div style="font-weight: bold; color: #2c3e50;">Рекомендация:</div>
                    <div>{recommendation}</div>
                </div>
            </div>
            """

        return f"""
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FoxDen - Уведомление об утечке</title>
    <style>
        body {{ 
            font-family: Arial, sans-serif; 
            line-height: 1.6; 
            color: #333; 
            margin: 0;
            padding: 0;
            background-color: #f5f7fa;
        }}
        .container {{ 
            max-width: 650px; 
            margin: 0 auto; 
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 5px 20px rgba(0,0,0,0.1);
        }}
        .header {{ 
            background: linear-gradient(135deg, #2c3e50, #34495e); 
            color: white; 
            padding: 25px 30px; 
            text-align: center; 
        }}
        .header h1 {{ 
            margin: 0 0 10px 0; 
            font-size: 28px;
        }}
        .header h2 {{ 
            margin: 0; 
            font-size: 18px; 
            font-weight: normal;
            opacity: 0.9;
        }}
        .content {{ 
            padding: 30px; 
        }}
        .device-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            border: 1px solid #e1e8ed;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }}
        .device-card h3 {{
            color: #2c3e50;
            margin-top: 0;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }}
        .action-box {{
            background: #e8f4fc;
            padding: 20px;
            border-radius: 8px;
            margin: 25px 0;
            border-left: 5px solid #3498db;
        }}
        .action-box h4 {{
            color: #2c3e50;
            margin-top: 0;
        }}
        .footer {{
            text-align: center; 
            color: #666; 
            font-size: 13px; 
            padding: 20px; 
            border-top: 1px solid #eee;
            background: #f8f9fa;
        }}
        .info-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        .info-table td {{
            padding: 10px;
            border-bottom: 1px solid #eee;
        }}
        .info-table tr:last-child td {{
            border-bottom: none;
        }}
        .info-label {{
            font-weight: bold;
            color: #495057;
            white-space: nowrap;
        }}
        @media (max-width: 600px) {{
            .container {{ margin: 10px; }}
            .content {{ padding: 20px; }}
            .header {{ padding: 20px; }}
            .header h1 {{ font-size: 24px; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>FoxDen System</h1>
            <h2>Система мониторинга утечек воды</h2>
        </div>
        
        <div class="content">
            <div class="device-card">
                <h3>Информация о счетчике</h3>
                <table class="info-table">
                    <tr>
                        <td class="info-label">Серийный номер:</td>
                        <td><strong>{serial}</strong></td>
                    </tr>
                    <tr>
                        <td class="info-label">Текущее показание:</td>
                        <td style="font-size: 24px; font-weight: bold; color: #27ae60;">{indicator:.3f} м³</td>
                    </tr>
                    <tr>
                        <td class="info-label">Время обнаружения:</td>
                        <td>{detected_at}</td>
                    </tr>
                    <tr>
                        <td class="info-label">Количество утечек:</td>
                        <td><strong>{len(leak_alerts)}</strong></td>
                    </tr>
                </table>
            </div>
            
            <h3 style="color: #2c3e50; margin-top: 30px;">Обнаруженные проблемы:</h3>
            {alerts_html}
            
            <div class="action-box">
                <h4>Рекомендуемые действия:</h4>
                <ol style="margin-left: 20px; line-height: 1.8;">
                    <li>Проверьте все краны, смесители и соединения труб</li>
                    <li>Убедитесь, что бачок унитаза не течет</li>
                    <li>Отключите стиральную и посудомоечную машины, проверьте соединения</li>
                    <li>Осмотрите видимые трубопроводы на предмет влажности или капель</li>
                    <li>Проверьте счетчик на наличие видимых повреждений</li>
                    <li>При необходимости вызовите сантехника</li>
                </ol>
            </div>
            
            <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; 
                       border: 1px solid #e1e8ed; margin-top: 25px;">
                <h4 style="margin-top: 0; color: #2c3e50;">Контактная информация</h4>
                <p><strong>Система:</strong> {self.sender_name}</p>
                <p><strong>Email:</strong> {self.sender_email}</p>
                <p><strong>Время отправки:</strong> {datetime.now().strftime('%d.%m.%Y %H:%M')}</p>
            </div>
        </div>
        
        <div class="footer">
            <p>© {datetime.now().year} FoxDen System - Система мониторинга потребления ресурсов</p>
            <p>Это автоматическое сообщение. Пожалуйста, не отвечайте на него.</p>
        </div>
    </div>
</body>
</html>
"""

    def get_stats(self) -> Dict[str, Any]:
        """Возвращает статистику отправки"""
        return {
            **self.stats,
            'enabled': self.enabled,
            'config': {
                'smtp_server': self.smtp_server,
                'smtp_port': self.smtp_port,
                'username': self.username[:3] + '***' if self.username else None,
                'sender': f"{self.sender_name} <{self.sender_email}>"
            }
        }

    def test_connection(self) -> bool:
        """Тестирует подключение к SMTP серверу"""
        if not self.enabled:
            logger.warning("Email sender is disabled - cannot test connection")
            return False

        try:
            if self.use_ssl:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=10)
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10)
                if self.use_tls:
                    server.starttls()

            server.ehlo()
            server.quit()

            logger.info("SMTP connection test: SUCCESS")
            return True

        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return False

    def send_test_email(self, to_email: str = None) -> bool:
        """Отправляет тестовое письмо"""
        if not self.enabled:
            logger.warning("Email sender is disabled - cannot send test")
            return False

        test_email = to_email or self.sender_email

        test_device = {
            'serial_number': 'TEST-001',
            'indicator': 123.456,
            'type': 'water_meter'
        }

        test_alerts = [{
            'message': 'Тестовое уведомление об утечке',
            'severity': 'medium',
            'recommendation': 'Это тестовое сообщение для проверки работы системы email уведомлений FoxDen',
            'detected_at': datetime.now().strftime('%d.%m.%Y %H:%M'),
            'type': 'test',
            'details': {
                'test_mode': True,
                'system_version': 'FoxDen 1.0'
            }
        }]

        logger.info(f"Sending test email to: {test_email}")
        return self.send_leak_alert(test_email, test_device, test_alerts)


# Глобальный экземпляр для использования во всем приложении
email_sender = FoxDenEmailSender()
