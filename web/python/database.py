import os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.engine.base import Connection

# 1. Добавить в Windows две системные переменные среды https://remontka.pro/environment-variables-windows/
# 2. Реализовать чтение из переменных среды
# db_user = os.environ.get('foxden_db_user')
# db_password =

# Использовать f строку для формирования корректной строки подключения
engine = create_engine('postgresql://user:password@host:port/database')
session = Session(engine, future=True)

def connect_database()-> Connection:
    try:
        return engine.connect()
    except Exception as ex:
        print(f"Failed to connect: {ex}")
        return None
