""" Сервер приложения FoxDen """
import logging
from datetime import datetime
from flask import Flask, request, jsonify, wrappers, render_template, session, redirect, url_for
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

@app.route('/')
def hello_world():
    """ Стартовая страница сервера """
    if 'username' in session:
        return render_template('index.html', username=session['username'])
    else:
        return render_template('index.html', username=None)

@app.route('/login', methods=['POST'])
def login():
    """ Обработка формы входа """
    username = request.form.get('username')
    password = request.form.get('password')

    # Подключиться к БД
    connect = connect_database()
    if connect is None:
        return render_template('index.html', username=None, error="Ошибка подключения к БД")

    try:
        query = text("SELECT * FROM public.users WHERE name=:username AND psw=md5(:password)")
        result = connect.execute(query, {"username": username, "password": password})
        user = result.fetchone()

        # Если нашел
        if user:
            session['username'] = username
            session['userid'] = user.id
            logging.info("User %s successfully logged in", username)
            return redirect(url_for('hello_world'))
        else:
            logging.warning("Failed login attempt for user: %s", username)
            return render_template('index.html', username=None, error="Неверный логин или пароль")
    
    except SQLAlchemyError as ex:
        logging.error("Database error in login: %s", ex)
        return render_template('index.html', username=None, error="Ошибка базы данных")
    finally:
        if connect:
            close_connection(connect)

@app.route('/logout')
def logout():
    """ Выход из системы """
    username = session.pop('username', None)
    session.pop('userid', None)
    logging.info("User %s logged out", username)
    return redirect(url_for('hello_world'))

@app.route('/dashboard')
def dashboard():
    """ Панель управления счетчиками """
    if 'username' not in session:
        return redirect(url_for('hello_world'))

    connect = connect_database()
    if connect is None:
        return render_template('error.html', error="Ошибка подключения к БД")

    try:
        # Получаем список всех счетчиков
        query = text("select * from public.get_devices(:user_id)")

        result = connect.execute(query, {"user_id": session['userid']})
        devices = result.fetchall()

        # Получаем последние показания для каждого счетчика
        # """ TODO
        # device_readings = {}
        # for device in devices:
        #     query = text("""
        #         SELECT moment, indicator_value 
        #         FROM public.device_readings 
        #         WHERE device_id = :device_id 
        #         ORDER BY moment DESC 
        #         LIMIT 10
        #     """)
        #     readings_result = connect.execute(query, {"device_id": device.id})
        #     device_readings[device.id] = readings_result.fetchall()
        # """
        return render_template(
            'dashboard.html', 
            username=session['username'],
            devices=devices,
            #device_readings=device_readings,
            current_time=datetime.now()
        )

    except SQLAlchemyError as ex:
        logging.error("Database error in dashboard: %s", ex)
        return render_template('error.html', error="Ошибка получения данных")
    finally:
        if connect:
            close_connection(connect)

# @app.route('/api/device_readings')
# def get_device_readings():
#     """ API для получения показаний конкретного счетчика """
#     device_id = request.args.get('device_id')
#     if not device_id:
#         return json_error(400, "Device ID is required"), 400

#     connect = connect_database()
#     if connect is None:
#         return json_error(500, "Database connection error"), 500

#     try:
#         query = text("""
#             SELECT dr.moment, dr.indicator_value, d.serial_number, d.series
#             FROM public.device_readings dr
#             JOIN public.devices d ON dr.device_id = d.id
#             WHERE dr.device_id = :device_id
#             ORDER BY dr.moment DESC
#         """)
#         result = connect.execute(query, {"device_id": device_id})
#         readings = result.fetchall()

#         readings_data = []
#         for reading in readings:
#             readings_data.append({
#                 'moment': reading.moment.isoformat() if reading.moment else None,
#                 'indicator_value': float(reading.indicator_value) if reading.indicator_value else 0,
#                 'serial_number': reading.serial_number,
#                 'series': reading.series
#             })

#         return jsonify({
#             "error": {},
#             "result": {
#                 "readings": readings_data
#             }
#         })

#     except SQLAlchemyError as ex:
#         logging.error("Database error in get_device_readings: %s", ex)
#         return json_error(500, "Database error"), 500
#     finally:
#         if connect:
#             close_connection(connect)

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
        return json_error(500, "Database connection error"), 500

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
        return json_error(500, "Database connection error"), 500

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

if __name__ == '__main__':
    logging.info("Starting FoxDen server...")
    app.run(debug=True)