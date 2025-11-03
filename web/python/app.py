""" Сервер приложения FoxDen """
from flask import Flask, request, abort
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
    mac_address = request.args['mac_address']
    # Подключиться используя SQLAlchemy к базе FoxDen - connect_database()
    connect = connect_database()
    if connect is None:
        abort(401)
    # Сделать запрос к таблице devices проверив есть ли устройство с переданным mac адресом
    query = f"select public.find_device(\'{mac_address}\') as id"
    print(f"query = {query}")
    result = connect.execute(text(query))
    rows = result.fetchall()

    if rows is None or (len(rows) < 1 and rows[0].id is None):
        abort(401)
    else:
        # Если есть - вернуть id устройства иначе Generates a 401 Unauthorized
        return f"connect device from {mac_address} id {rows[0].id}"

if __name__ == 'main':
    app.run(debug=True)
