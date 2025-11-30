""" Сервер приложения FoxDen """
import logging
from flask import Flask, request, jsonify, wrappers, render_template, session, redirect, url_for, abort
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
import config
from database import connect_database, close_connection

app = Flask(__name__)
app.config["JWT_ALGORITHM"] = "HS256"
app.config["JWT_SECRET_KEY"] = config.FOXDEN_TOKEN
app.secret_key = config.FOXDEN_TOKEN or 'fallback_secret_key_for_sessions'

jwt = JWTManager(app)

def json_error(error_code: int, error_message: str) -> wrappers.Response:
    """ Возвращает ошибку в JSON формате """
    result = {
        "error": {
            "error_code": error_code,
            "error_message": error_message
        },
        "result": {}
    }
    return jsonify(result)

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
        return json_error(400, "Invalid request parameters"), 400

    connect = connect_database()
    if connect is None:
        return json_error(401, "Unauthorized"), 401

    try:
        logging.info("Connection attempt for MAC: %s", mac_address)
        # Используем параметризованный запрос для безопасности
        query = text("select * from public.find_device(:mac_address)")
        result = connect.execute(query, {"mac_address": mac_address})
        rows = result.fetchall()

        if rows is None or len(rows) == 0:
            return json_error(401, "Unauthorized"), 401

        devices = []
        for row in rows:
            logging.info("row.id: {row.id} row.pin {row.pin}")
            if row.id:
                devices.append({"id": row.id, "pin:": row.pin})

        if not devices:
            return json_error(401, "Unauthorized"), 401

        access_token = create_access_token(identity=mac_address)
        result_data = {
            "error": {},
            "result": {
                "devices": devices,
                "access_token": access_token
            }
        }
        return jsonify(result_data)

    except SQLAlchemyError as ex:
        logging.error("Database error in connect_device: %s", ex)
        return json_error(500, "Database error"), 500
    except Exception as ex:  # pylint: disable=W0718
        logging.error("Unexpected error in connect_device: %s", ex)
        return json_error(500, "Internal server error"), 500
    finally:
        if connect:
            close_connection(connect)

@app.route('/add_device_changes', methods=['POST'])
@jwt_required()
def add_device_changes():
    """ Запись об изменении показания устройства """
    device_id = None
    moment = None
    mac_address = get_jwt_identity()

    if request.is_json:
        data = request.get_json()
        device_id = data.get('device_id')
        moment = data.get('moment')
    else:
        device_id = request.args.get('device_id')
        moment = request.args.get('moment')

    if device_id is None or moment is None:
        return json_error(400, "Missing required parameters: device_id and moment"), 400

    connect = connect_database()
    if connect is None:
        return json_error(401, "Unauthorized"), 401

    try:
        query = text("call public.add_device_changes(:mac_address, :device_id, :moment)")
        with connect.begin():
            connect.execute(query, {
                "mac_address": mac_address,
                "device_id": device_id,
                "moment": moment
            })

        result_data = {
            "error": {},
            "result": {
                "success": True,
                "device_id": device_id
            }
        }
        return jsonify(result_data)
    except SQLAlchemyError as ex:
        logging.error("Database error in add_device_changes: %s", ex)
        return json_error(500, "Database error"), 500
    except Exception as ex:  # pylint: disable=W0718
        logging.error("Unexpected error in add_device_changes: %s", ex)
        return json_error(500, "Internal server error"), 500
    finally:
        if connect:
            close_connection(connect)

@app.route('/')
def hello_world():
    """ Стартовая страница сервера """
    if 'username' in session:
        return render_template('index.html', username=session['username'])
    else:
        return render_template('index.html', username=None)

@app.route('/logout')
def logout():
    """ Выход из системы """
    username = session.pop('username', None)
    logging.info("User %s logged out", username)
    return redirect(url_for('hello_world'))

@app.route('/login', methods=['POST'])
def login():
    """ Обработка формы входа """
    username = request.form.get('username')
    password = request.form.get('password')

    # Подключится к БД
    connect = connect_database()
    if connect is None:
        return abort(401, "Unauthorized")
    query = text("select * from public.users where name=:username and psw=md5(:password)")
    result = connect.execute(query, {"username": username, "password": password})
    rows = result.fetchall()

    # Если нашел
    if rows and len(rows) == 1:
        session['username'] = username
        logging.info("User %s successfully logged in", username)
        return redirect(url_for('hello_world'))
    else:
        logging.warning("Failed login attempt for user: %s", username)
        return render_template('index.html', username=None, error="Неверный логин или пароль")

@app.route('/dashboard')
def dashboard():
    """ Панель управления """
    if 'username' not in session:
        return redirect(url_for('hello_world'))

    return """
    <h1>Панель управления FoxDen</h1>
    <p>Добро пожаловать, {username}!</p>
    <p>Это защищенная страница только для авторизованных пользователей.</p>
    <a href="/">На главную</a> |
    <a href="/logout">Выйти</a>
    """.format(username=session['username'])

if __name__ == '__main__':
    logging.info("Starting FoxDen server...")
    app.run(debug=True)
