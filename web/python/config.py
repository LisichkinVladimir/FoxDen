""" Модуль настроек FoxDen """
import logging
import sys
import os

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

BOT_TOKEN = os.getenv("FOXDEN_SECRET_KEY")
if BOT_TOKEN is None:
    logging.error("FOXDEN_SECRET_KEY is None")
else:
    logging.info("FOXDEN_SECRET_KEY is not None")

def main():
    """ Config main """
    raise SystemError("This file cannot be operable")

if __name__ == "__main__":
    main()
