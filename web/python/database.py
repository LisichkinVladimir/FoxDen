""" Работа с БД Postgresql """
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.engine.base import Connection
from sqlalchemy.exc import SQLAlchemyError

def connect_database() -> Connection:
    """ Подключение к БД """
    try:
        db_user = os.environ.get('foxden_db_user')
        db_password = os.environ.get('foxden_db_password')
        db_database = os.environ.get('foxden_db_database')

        # Проверяем наличие обязательных параметров
        if not all([db_user, db_password, db_database]):
            missing_params = []
            if not db_user:
                missing_params.append('foxden_db_user')
            if not db_password:
                missing_params.append('foxden_db_password')
            if not db_database:
                missing_params.append('foxden_db_database')

            logging.error("Отсутствуют обязательные параметры подключения к БД: %s",
                         ', '.join(missing_params))
            return None

        # Использовать f строку для формирования корректной строки подключения
        database_url = f"postgresql+psycopg2://{db_user}:{db_password}@localhost:5432/{db_database}"

        engine = create_engine(database_url)
        connect = engine.connect()
        logging.info("Успешно подключились к БД")
        return connect

    except SQLAlchemyError as ex:
        logging.error("Ошибка подключения к БД SQLAlchemy: %s", ex)
        return None
    except Exception as ex:  # pylint: disable=W0718
        # Оставляем общий Exception, так как могут быть ошибки ОС, сети и т.д.
        logging.error("Неожиданная ошибка при подключении к БД: %s", ex)
        return None

def close_connection(connect: Connection):
    """ Закрытие соединения с БД """
    if connect:
        try:
            connect.close()
            logging.info("Соединение с БД закрыто")
        except Exception as ex:  # pylint: disable=W0718
            logging.error("Ошибка при закрытии соединения: %s", ex)

def main():
    """ Config main """
    raise SystemError("This file cannot be operable")


if __name__ == "__main__":
    main()
