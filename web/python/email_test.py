"""
ПРОСТОЙ ТЕСТ ОТПРАВКИ EMAIL ДЛЯ FOXDEN
Отправляет с fox.den.emailsander@gmail.com на vladimir2.01.0.za@gmail.com
"""
import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,  # Подробный вывод
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Вывод в консоль
        logging.FileHandler('email_test.log')  # И в файл
    ]
)
logger = logging.getLogger(__name__)

def load_config():
    """Загружает настройки из .env файла"""
    load_dotenv()
    
    config = {
        'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
        'smtp_port': int(os.getenv('SMTP_PORT', '587')),
        'username': os.getenv('SMTP_USERNAME', ''),
        'password': os.getenv('SMTP_PASSWORD', ''),
        'sender_email': os.getenv('SMTP_SENDER_EMAIL', ''),
        'sender_name': os.getenv('SMTP_SENDER_NAME', 'FoxDen'),
    }
    
    return config

def check_config(config):
    """Проверяет конфигурацию"""
    print("\n" + "="*60)
    print("ПРОВЕРКА НАСТРОЕК EMAIL")
    print("="*60)
    
    issues = []
    
    # Проверяем обязательные поля
    if not config['username']:
        issues.append("❌ SMTP_USERNAME не установлен")
    if not config['password']:
        issues.append("❌ SMTP_PASSWORD не установлен")
    
    # Показываем текущие настройки (скрываем пароль)
    masked_password = config['password'][:4] + "****" + config['password'][-4:] if config['password'] else "НЕ УСТАНОВЛЕН"
    
    print(f"\n📋 ТЕКУЩИЕ НАСТРОЙКИ:")
    print(f"   SMTP Сервер: {config['smtp_server']}:{config['smtp_port']}")
    print(f"   Пользователь: {config['username']}")
    print(f"   Пароль: {masked_password}")
    print(f"   Отправитель: {config['sender_name']} <{config['sender_email']}>")
    
    if issues:
        print(f"\n⚠️  ПРОБЛЕМЫ:")
        for issue in issues:
            print(f"   {issue}")
        return False
    
    print("\n✅ Все обязательные настройки установлены")
    return True

def send_test_email():
    """Отправляет тестовое письмо"""
    
    # 1. Загружаем конфигурацию
    config = load_config()
    
    # 2. Проверяем настройки
    if not check_config(config):
        return False
    
    # 3. Настройки отправки
    from_email = config['sender_email']
    to_email = "vladimir2.01.0.za@gmail.com"  # КУДА ОТПРАВЛЯЕМ
    smtp_server = config['smtp_server']
    smtp_port = config['smtp_port']
    username = config['username']
    password = config['password']
    
    print(f"\n" + "="*60)
    print(f"ОТПРАВКА ТЕСТОВОГО ПИСЬМА")
    print("="*60)
    print(f"📧 ОТ: {from_email}")
    print(f"📧 КОМУ: {to_email}")
    print(f"🌐 СЕРВЕР: {smtp_server}:{smtp_port}")
    print("\n⏳ Пожалуйста, подождите...")
    
    try:
        # 4. Создаем сообщение
        subject = "🎉 УРА! Тест FoxDen Email System УСПЕШЕН!"
        
        body = f"""
        🦊 FOX DEN EMAIL SYSTEM - ТЕСТОВОЕ ПИСЬМО
        {'=' * 50}
        
        🎯 ЦЕЛЬ: Проверка работы системы отправки email
        
        📊 РЕЗУЛЬТАТ: ✅ УСПЕШНО!
        
        📋 ИНФОРМАЦИЯ ОТПРАВКИ:
        • Время: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
        • От кого: {config['sender_name']} <{from_email}>
        • Кому: {to_email}
        • Сервер: {smtp_server}:{smtp_port}
        • Аккаунт: {username}
        
        🎉 ПОЗДРАВЛЯЕМ!
        Ваша система FoxDen успешно настроена и готова к работе!
        
        🔧 СЛЕДУЮЩИЕ ШАГИ:
        1. Убедиться, что это письмо получено
        2. Проверить папку "Спам", если письма нет во "Входящих"
        3. Настроить отправку уведомлений об утечках
        
        {'=' * 50}
        Это автоматическое тестовое сообщение.
        Система FoxDen - мониторинг потребления ресурсов.
        {'=' * 50}
        """
        
        # 5. Формируем MIME сообщение
        msg = MIMEMultipart()
        msg['From'] = f"{config['sender_name']} <{from_email}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))
        
        # 6. Подключаемся к SMTP серверу
        logger.info(f"Подключение к {smtp_server}:{smtp_port}")
        server = smtplib.SMTP(smtp_server, smtp_port, timeout=30)
        
        # 7. Включаем TLS шифрование
        logger.info("Включение TLS шифрования...")
        server.ehlo()
        server.starttls()
        server.ehlo()
        
        # 8. Логинимся
        logger.info(f"Авторизация как {username}")
        server.login(username, password)
        
        # 9. Отправляем письмо
        logger.info(f"Отправка письма на {to_email}")
        server.send_message(msg)
        
        # 10. Закрываем соединение
        server.quit()
        
        # 11. УСПЕХ!
        print("\n" + "="*60)
        print("✅ ТЕСТ УСПЕШНО ЗАВЕРШЕН!")
        print("="*60)
        print(f"✓ Письмо отправлено с: {from_email}")
        print(f"✓ Письмо отправлено на: {to_email}")
        print(f"✓ Время отправки: {datetime.now().strftime('%H:%M:%S')}")
        
        print("\n🔍 ГДЕ ИСКАТЬ ПИСЬМО:")
        print("1. 📥 Папка 'Входящие' в Gmail vladimir2.01.0.za@gmail.com")
        print("2. 🗑️ Папка 'Спам' или 'Нежелательная почта'")
        print("3. 🔍 Используйте поиск по слову 'FoxDen'")
        print("4. 📱 Проверьте мобильное приложение Gmail")
        
        print("\n⚠️  ВАЖНО: Gmail может отложить доставку на 1-2 минуты")
        print("   Обновите страницу почты через 2 минуты если не видите письмо")
        
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"\n❌ ОШИБКА АВТОРИЗАЦИИ: {e}")
        print("\n🔧 ВОЗМОЖНЫЕ ПРИЧИНЫ И РЕШЕНИЯ:")
        print("1. ❌ Неправильный пароль")
        print("   ✅ Решение: Используйте ПАРОЛЬ ПРИЛОЖЕНИЯ из Google")
        print("   🔗 Как получить: https://support.google.com/accounts/answer/185833")
        
        print("\n2. ❌ 2-факторная аутентификация не включена")
        print("   ✅ Решение: Включите 2FA в настройках Google аккаунта")
        
        print("\n3. ❌ Разрешение для 'ненадежных приложений' отключено")
        print("   ✅ Решение 1: Временно включите в настройках Google")
        print("   ✅ Решение 2: Или используйте пароль приложения")
        
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        logger.error(f"Ошибка отправки: {e}", exc_info=True)
    
    return False

def create_env_template():
    """Создает шаблон .env файла если его нет"""
    if not os.path.exists('.env'):
        print("\n📄 Создаю шаблон .env файла...")
        
        template = """# НАСТРОЙКИ EMAIL ДЛЯ FOX.DEN.EMAILSANDER@GMAIL.COM
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=fox.den.emailsander@gmail.com
SMTP_PASSWORD=ВСТАВЬТЕ_ПАРОЛЬ_ПРИЛОЖЕНИЯ_ЗДЕСЬ

SMTP_SENDER_EMAIL=fox.den.emailsander@gmail.com
SMTP_SENDER_NAME=FoxDen Email System

FOXDEN_SECRET_KEY=test_secret_key_foxden_2024
"""
        
        with open('.env', 'w', encoding='utf-8') as f:
            f.write(template)
        
        print("✅ Файл .env создан. Отредактируйте его и добавьте пароль приложения.")
        return True
    return False

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🦊 FOX DEN EMAIL SYSTEM - ТЕСТ ОТПРАВКИ")
    print("="*60)
    print("Отправитель: fox.den.emailsander@gmail.com")
    print("Получатель: vladimir2.01.0.za@gmail.com")
    
    # Создаем шаблон .env если его нет
    if not os.path.exists('.env'):
        create_env_template()
        print("\n📋 Отредактируйте файл .env и запустите скрипт снова.")
        input("Нажмите Enter для выхода...")
        exit(0)
    
    # Запускаем тест
    success = send_test_email()
    
    if not success:
        print("\n" + "="*60)
        print("😞 ТЕСТ НЕ ПРОЙДЕН")
        print("="*60)
        print("Проверьте файл email_test.log для подробной информации.")
        
        # Показываем помощь
        print("\n📚 СПРАВКА ПО НАСТРОЙКЕ GMAIL:")
        print("1. Войдите в Gmail: fox.den.emailsander@gmail.com")
        print("2. Включите 2-факторную аутентификацию")
        print("3. Создайте пароль приложения:")
        print("   • Зайдите в 'Управление аккаунтом Google'")
        print("   • 'Безопасность' → 'Пароли приложений'")
        print("   • Выберите 'Почта' и 'Другое' (назовите 'FoxDen')")
        print("   • Скопируйте 16-значный пароль")
        print("4. Вставьте этот пароль в файл .env в поле SMTP_PASSWORD")
    
    # Ждем перед закрытием
    input("\nНажмите Enter для выхода...")