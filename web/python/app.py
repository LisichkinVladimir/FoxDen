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
    if not 'mac_address' in request.args:
        # Bad Request - сервер не может понять запрос из-за неправильного синтаксиса
        error_message = {"error": {"error_code": 400, "error_message": "Invalid request parameters."}}
        abort(400, description=jsonify(error_message))
    mac_address = request.args['mac_address']
    # pin = Получить пин из параметров проверить наличие ключа pin в request.args
    # Подключиться к базе данных
    connect = connect_database()
    if connect is None:
        # Unauthorized - у клиента отсутствуют действительные учетные данные аутентификации
        abort(401)
    # Сделать запрос к таблице devices проверив есть ли устройство с переданным mac адресом
    # добавить параметр pin
    query = f"select public.find_device(\'{mac_address}\') as id"
    result = connect.execute(text(query))
    rows = result.fetchall()

    if rows is None or len(rows) == 0 or (len(rows) > 0 and rows[0].id is None):
        abort(401)
    else:
        # Если есть - вернуть id устройства
        # использовать jsonify для того что бы вернуть JSON объект {"error": {}, result: {"device_id": }}
        return f"connect device from {mac_address} id {rows[0].id}"

if __name__ == 'main':
    app.run(debug=True)
