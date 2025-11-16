""" Работа с БД Postgresql """
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.engine.base import Connection

def connect_database()-> Connection:
    """ Подключение к БД """
    try:
        db_user = os.environ.get('foxden_db_user')
        db_password = os.environ.get('foxden_db_password')
        db_database = os.environ.get('foxden_db_database')
        # Использовать f строку для формирования корректной строки подключения
        database_url = f"postgresql+psycopg2://{db_user}:{db_password}@localhost:5432/{db_database}"

        engine = create_engine(database_url)
        connect = engine.connect()
        logging.info("Успешно подключились к БД")
        return connect
    except Exception as ex:
        logging.info(f"Ошибка подключения к БД: {ex}")
        return None

def main():
    """ Config main """
    raise SystemError("This file cannot be operable")

if __name__ == "__main__":
    main()
