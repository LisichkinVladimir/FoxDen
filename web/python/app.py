""" Сервер приложениея FoxDen """
from flask import Flask, request
app = Flask(__name__)

@app.route('/')
def hello_world():
    """ Стартовая страница сервера """
    return 'Вас приветствует FoxDen!'

@app.route('/connect_device', methods=['POST'])
def connect_device():
    """ Метод подключения устройств """
    mac_address = request.args['mac_address']
    # Подключиться используя SQLlchemy к базе FoxDen
    # Сделать запрос к таблице devices проверив есть ли устройство с переданным mac адресом
    # Если есть - вернуть OK иначе послать на хутор
    return f"connect device from {mac_address}"

if __name__ == 'main':
    app.run(debug=True)