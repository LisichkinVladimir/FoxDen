""" Модуль настроек FoxDen """
import logging
import sys
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # Вывод в консоль
        logging.FileHandler('foxden.log')   # Запись в файл
    ]
)
logger = logging.getLogger(__name__)
logging.getLogger().addHandler(logging.StreamHandler())

# Получаем секретный ключ из переменных окружения
FOXDEN_TOKEN = os.getenv("FOXDEN_SECRET_KEY", "default_fallback_secret_key_for_development")

if FOXDEN_TOKEN == "default_fallback_secret_key_for_development":
    logging.warning("Using default secret key - not secure for production!")
else:
    logging.info("Secret key loaded successfully")

# Настройки базы данных
DB_CONFIG = {
    'user': os.getenv('FOXDEN_DB_USER', 'foxden_user'),
    'password': os.getenv('FOXDEN_DB_PASSWORD', 'foxden_password'),
    'database': os.getenv('FOXDEN_DB_NAME', 'foxden_db'),
    'host': os.getenv('FOXDEN_DB_HOST', 'localhost'),
    'port': os.getenv('FOXDEN_DB_PORT', '5432')
}

def main():
    """ Config main """
    raise SystemExit("This file cannot be operable")

if __name__ == "__main__":
    main()
