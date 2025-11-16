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

FOXDEN_TOKEN = os.getenv("foxden_secret_key")
if FOXDEN_TOKEN is None:
    logging.error("foxden_secret_key is None")
else:
    logging.info("foxden_secret_key is not None")

def main():
    """ Config main """
    raise SystemError("This file cannot be operable")

if __name__ == "__main__":
    main()
