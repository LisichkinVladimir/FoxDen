""" Сервер приложения FoxDen """
import logging
import sys
from flask import Flask, request, jsonify, abort
from sqlalchemy import text
from database import connect_database

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

app = Flask(__name__)

@app.route('/')
def hello_world():
    """ Стартовая страница сервера """
    return 'Вас приветствует FoxDen!'

@app.route('/connect_device', methods=['POST'])
def connect_device():
    """ Метод подключения устройств """
    # Получение параметра mac_address
    mac_address = None
    if request.is_json:
        data = request.get_json()
        if 'mac_address' in data:
            mac_address = data['mac_address']
    else:
        if 'mac_address' in request.args:
            mac_address = request.args['mac_address']
    if mac_address is None:
        # Bad Request - сервер не может понять запрос из-за неправильного синтаксиса
        error_message = {
                "error": {
                    "error_code": 400, "error_message": "Invalid request parameters."
                },
                "result": {}
            }
        abort(400, description=jsonify(error_message))

    # Подключение к БД
    connect = connect_database()
    if connect is None:
        # Unauthorized - у клиента отсутствуют действительные учетные данные аутентификации
        error_message = {
                "error": {
                    "error_code": 401, "error_message": "Unauthorized"
                },
                "result": {}
            }
        abort(401, description=jsonify(error_message))

    # Потск в таблице devices устройства с переданным mac адресом
    print(f"Connection attempt for MAC: {mac_address}")
    query = f"select public.find_device(\'{mac_address}\') as id"
    result = connect.execute(text(query))
    rows = result.fetchall()
    if rows is None or len(rows) == 0:
        error_message = {
                "error": {
                    "error_code": 401, "error_message": "Unauthorized"
                },
                "result": {}
            }
        abort(401, description=jsonify(error_message))
    # Если есть - вернуть id устройств
    devices = []
    for row in rows:
        print(f"row.id: {row.id}")
        if row.id:  # Проверяем, что id не None
            devices.append(row.id)
    result = {
            "error": {}, 
            "result": {
                "devices": devices 
            }
        }
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)
