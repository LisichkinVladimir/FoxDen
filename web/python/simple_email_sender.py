"""
Простая система email-уведомлений для FoxDen System
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class SimpleEmailSender:
    """Простая система email-уведомлений без БД"""

    def __init__(self):
        # Читаем настройки из переменных окружения
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', 587))
        self.username = os.getenv('SMTP_USERNAME', '')
        self.password = os.getenv('SMTP_PASSWORD', '')
        self.sender_email = os.getenv('SMTP_SENDER_EMAIL', 'noreply@foxden.ru')
        self.sender_name = os.getenv('SMTP_SENDER_NAME', 'FoxDen System')

        self.enabled = bool(self.username and self.password)

        if not self.enabled:
            logger.info("Email notifications disabled. To enable, set SMTP_USERNAME and SMTP_PASSWORD environment variables.")

    def send_leak_alert(self, user_email, device_info, leak_alerts):
        """Отправляет уведомление об утечке"""
        if not self.enabled:
            # Режим тестирования - только логируем
            logger.info(f"[EMAIL TEST] Would send to: {user_email}")
            logger.info(f"[EMAIL TEST] Device: {device_info.get('serial_number')}")
            logger.info(f"[EMAIL TEST] Alerts: {len(leak_alerts)}")
            for alert in leak_alerts:
                logger.info(f"[EMAIL TEST] - {alert.get('message')}")
            return True

        try:
            # Создаем письмо
            msg = MIMEMultipart('alternative')
            msg['Subject'] = self._create_subject(device_info, leak_alerts)
            msg['From'] = f"{self.sender_name} <{self.sender_email}>"
            msg['To'] = user_email

            # Текстовая и HTML версии
            text_content = self._create_text_content(device_info, leak_alerts)
            html_content = self._create_html_content(device_info, leak_alerts)

            msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))

            # Отправка
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)

            logger.info(f"Leak alert email sent to {user_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def _create_subject(self, device_info, leak_alerts):
        """Создает тему письма"""
        if any(a.get('severity') == 'critical' for a in leak_alerts):
            return f"🚨 КРИТИЧЕСКАЯ УТЕЧКА: {device_info.get('serial_number', 'Счетчик')}"
        elif any(a.get('severity') == 'high' for a in leak_alerts):
            return f"⚠️ УТЕЧКА: {device_info.get('serial_number', 'Счетчик')}"
        else:
            return f"📢 Обнаружена утечка: {device_info.get('serial_number', 'Счетчик')}"

    def _create_text_content(self, device_info, leak_alerts):
        """Создает текстовую версию письма"""
        text = f"""FOXDEN - УВЕДОМЛЕНИЕ ОБ УТЕЧКЕ
{'=' * 50}

Обнаружены утечки на счетчике: {device_info.get('serial_number', 'Неизвестный')}
Текущее показание: {device_info.get('indicator', 0):.3f} м³
Время обнаружения: {leak_alerts[0].get('detected_at', 'Неизвестно')}

{'=' * 50}
ДЕТАЛИ УТЕЧЕК:
{'=' * 50}
"""
        for i, alert in enumerate(leak_alerts, 1):
            text += f"\n{i}. {alert.get('message', 'Нет сообщения')}"
            text += f"\n   Серьезность: {alert.get('severity', 'unknown').upper()}"
            text += f"\n   Рекомендация: {alert.get('recommendation', 'Проверьте систему')}\n"

        text += f"""
{'=' * 50}
РЕКОМЕНДУЕМЫЕ ДЕЙСТВИЯ:
1. Проверьте все краны и смесители
2. Убедитесь что туалетный бачок не течет
3. Проверьте стиральную и посудомоечную машины
4. Осмотрите видимые трубопроводы
5. При необходимости вызовите сантехника

{'=' * 50}
Это автоматическое сообщение от системы FoxDen.
"""
        return text

    def _create_html_content(self, device_info, leak_alerts):
        """Создает HTML версию письма"""
        alerts_html = ""
        for i, alert in enumerate(leak_alerts, 1):
            color = '#e74c3c' if alert.get('severity') == 'critical' else '#f39c12' if alert.get('severity') == 'high' else '#f1c40f'
            alerts_html += f"""
            <div style="margin: 10px 0; padding: 15px; border-left: 4px solid {color}; background: #f8f9fa;">
                <div><strong>{i}. {alert.get('message', '')}</strong></div>
                <div style="color: {color}; margin: 5px 0; font-weight: bold;">{alert.get('severity', '').upper()}</div>
                <div>{alert.get('recommendation', '')}</div>
            </div>
            """

        return f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"></head>
        <body style="font-family: Arial, sans-serif;">
            <div style="max-width: 600px; margin: 0 auto;">
                <div style="background: #2c3e50; color: white; padding: 20px; text-align: center;">
                    <h1>🦊 FoxDen System</h1>
                    <h2>Уведомление об утечке</h2>
                </div>
                
                <div style="padding: 20px; background: #f9f9f9;">
                    <h3>Счетчик: {device_info.get('serial_number', 'Неизвестный')}</h3>
                    <p>Текущее показание: <strong>{device_info.get('indicator', 0):.3f} м³</strong></p>
                    <p>Обнаружено: {leak_alerts[0].get('detected_at', '')}</p>
                    
                    <h4>Обнаруженные утечки:</h4>
                    {alerts_html}
                    
                    <div style="margin-top: 20px; padding: 15px; background: #e8f4fc;">
                        <h4>Рекомендуемые действия:</h4>
                        <ul>
                            <li>Проверьте все краны и смесители</li>
                            <li>Убедитесь что туалетный бачок не течет</li>
                            <li>Проверьте стиральную и посудомоечную машины</li>
                            <li>Осмотрите видимые трубопроводы</li>
                        </ul>
                    </div>
                </div>
                
                <div style="margin-top: 20px; text-align: center; color: #666; font-size: 12px;">
                    <p>© {datetime.now().year} FoxDen System</p>
                </div>
            </div>
        </body>
        </html>
        """