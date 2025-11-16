""" Сервер приложения FoxDen """
import logging
from flask import Flask, request, jsonify, wrappers
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from sqlalchemy import text
import config
from database import connect_database

app = Flask(__name__)
app.config["JWT_ALGORITHM"] = "HS256"
app.config["JWT_SECRET_KEY"] = config.FOXDEN_TOKEN
jwt = JWTManager(app)

def json_error(error_code: int, error_message: str)->wrappers.Response:
    """ Возвращает ошибку в JSON формате """
    result = {
            "error": {
                "error_code": error_code, 
                "error_message": error_message
            },
            "result": {}
        }
    return jsonify(result)

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
        return json_error(400, "Invalid request parameters"), 400

    # Подключение к БД
    connect = connect_database()
    if connect is None:
        # Unauthorized - у клиента отсутствуют действительные учетные данные аутентификации
        return json_error(401, "Unauthorized"), 401

    # Поиск в таблице devices устройства с переданным mac адресом
    logging.info("Connection attempt for MAC: %s", mac_address)
    query = f"select public.find_device(\'{mac_address}\') as id"
    result = connect.execute(text(query))
    rows = result.fetchall()
    if rows is None or len(rows) == 0:
        return json_error(401, "Unauthorized"), 401
    # Если есть - вернуть id устройств
    devices = []
    for row in rows:
        logging.info("row.id: %d", row.id)
        if row.id:  # Проверяем, что id не None
            devices.append(row.id)
    if not devices:
        return json_error(401, "Unauthorized"), 401
    # Генерация JWT access_token
    access_token = create_access_token(identity=mac_address)
    result = {
            "error": {}, 
            "result": {
                "devices": devices,
                "access_token": access_token
            }
        }
    return jsonify(result)

@jwt_required()
@app.route('/add_device_changes', methods=['POST'])
# Protect a route with jwt_required, which will kick out requests https://flask-jwt-extended.readthedocs.io/en/stable/basic_usage.html
def add_device_changes():
    """ Запись об изменении показания устройства """
    device_id = None
    moment = None

    if request.is_json:
        data = request.get_json()
        device_id = data.get('device_id')
        moment = data.get('moment')
    else:
        device_id = request.args.get('device_id')
        moment = request.args.get('moment')

    # Проверка обязательных параметров
    if device_id is None or moment is None:
        return json_error(400, "Missing required parameters: device_id and moment"), 400

    # Подключение к БД
    connect = connect_database()
    if connect is None:
        return json_error(401, "Unauthorized"), 401
    try:
        mac_address = get_jwt_identity()
        # Вызов хранимой процедуры add_device_changes
        query = text("call public.add_device_changes(:mac_address, :device_id, :moment)")
        connect.execute(query, {"mac_address": mac_address, "device_id": device_id, "moment": moment})

        result_data = {
            "error": {}, 
            "result": {
                "success": True,
                "device_id": device_id
            }
        }
        return jsonify(result_data)
    except Exception as e:
        logging.error("Error executing add_device_changes: %s", str(e))
        return json_error(500, "Internal server error"), 500

if __name__ == '__main__':
    app.run(debug=True)
