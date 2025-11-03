""" Работа с БД Postgresql """
import os
from sqlalchemy import create_engine
from sqlalchemy.engine.base import Connection

def connect_database()-> Connection:
    """ Подключение к БД """
    try:
        db_user = os.environ.get('foxden_db_user')
        db_password = os.environ.get('foxden_db_password')
        db_database = os.environ.get('foxden_db_database')
        database_url = f"postgresql+psycopg2://{db_user}:{db_password}@localhost:5432/{db_database}"

        # Использовать f строку для формирования корректной строки подключения
        engine = create_engine(database_url)
        print("Успешно подключились к БД")
        return engine.connect()
    except Exception as ex:
        print(f"Ошибка подключения к БД: {ex}")
        return None
