import os
from sqlalchemy import create_engine
from sqlalchemy.engine.base import Connection

def connect_database()-> Connection:
    try:
        db_user = os.environ.get('foxden_db_user')
        db_password = os.environ.get('foxden_db_password')
        db_database = os.environ.get('foxden_db_database')
        DATABASE_URL = f"postgresql+psycopg2://{db_user}:{db_password}@localhost:5432/{db_database}"
        print(f"DATABASE_URL = {DATABASE_URL}")

        # Использовать f строку для формирования корректной строки подключения
        engine = create_engine(DATABASE_URL)
        print("Успешно подключились к БД")
        return engine.connect()
    except Exception as ex:
        print(f"Failed to connect: {ex}")
        return None
