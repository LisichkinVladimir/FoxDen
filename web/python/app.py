""" Сервер приложения FoxDen """
from flask import Flask, request, jsonify, abort
from sqlalchemy import text
from database import connect_database
app = Flask(__name__)

@app.route('/')
def hello_world():
    """ Стартовая страница сервера """
    return 'Вас приветствует FoxDen!'

@app.route('/connect_device', methods=['POST'])
def connect_device():
    """ Метод подключения устройств """
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
    connect = connect_database()
    if connect is None:
        # Unauthorized - у клиента отсутствуют действительные учетные данные аутентификации
        # TODO error_message - ошибка в JSON формате
        abort(401)
    # Сделать запрос к таблице devices проверив есть ли устройство с переданным mac адресом
    # добавить параметр pin
    query = f"select public.find_device(\'{mac_address}\') as id"
    result = connect.execute(text(query))
    rows = result.fetchall()

    if rows is None or len(rows) == 0:
        # TODO error_message - ошибка в JSON формате
        abort(401)
    # Если есть - вернуть id устройств
    # TODO цикл по всем устройствам подключенным к esp32 с данным MAC address'ом
    # for row in rows - сформировать массив devices
    # использовать jsonify для того что бы вернуть JSON объект {"error": {}, "result": {"devices": [] }}
    return f"connect device from {mac_address} id {rows[0].id}"

if __name__ == 'main':
    app.run(debug=True)
