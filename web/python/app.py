""" Сервер приложения FoxDen """
from flask import Flask, request, abort
app = Flask(__name__)

@app.route('/')
def hello_world():
    """ Стартовая страница сервера """
    return 'Вас приветствует FoxDen!'

@app.route('/connect_device', methods=['POST'])
def connect_device():
    """ Метод подключения устройств """
    mac_address = request.args['mac_address']
    # Подключиться используя SQLAlchemy к базе FoxDen - connect_database()
    # Если подключения не получилось - abort(401)  # Generates a 401 Unauthorized
    # Сделать запрос к таблице devices проверив есть ли устройство с переданным mac адресом
    # через вызов select public.find_device(mac_address)
    # Если есть - вернуть id устройства иначе Generates a 401 Unauthorized
    return f"connect device from {mac_address}"

if __name__ == 'main':
    app.run(debug=True)
