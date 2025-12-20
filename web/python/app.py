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

        # Подготавливаем данные для шаблона
        devices_data = []
        
        for device in devices:
            device_id = device[0] if len(device) > 0 else None
            step_increment = float(device[6]) if len(device) > 6 and device[6] is not None else 10.0
            current_value = float(device[7]) if len(device) > 7 and device[7] is not None else 0.0
            
            # Получаем изменения для графиков
            cumulative_labels = []
            cumulative_values = []
            daily_labels = []
            daily_values = []
            monthly_labels = []
            monthly_values = []
            total_changes = 0
            
            try:
                query_changes = text("""
                    SELECT moment 
                    FROM public.device_changes 
                    WHERE device_id = :device_id 
                    ORDER BY moment ASC
                """)
                changes_result = connect.execute(query_changes, {"device_id": device_id})
                changes = changes_result.fetchall()
                total_changes = len(changes)
                
                if changes:
                    # 1. НАКОПИТЕЛЬНЫЙ ГРАФИК
                    initial_value = current_value - (total_changes * step_increment)
                    cumulative = initial_value
                    
                    # Берем последние 15 изменений для читаемости
                    recent_changes = changes[-15:] if len(changes) > 15 else changes
                    
                    for i, change in enumerate(recent_changes):
                        if len(recent_changes) <= 8:
                            label = change.moment.strftime('%H:%M') if hasattr(change, 'moment') and change.moment else f'Точка {i+1}'
                        else:
                            if i % 3 == 0 or i == len(recent_changes) - 1:
                                label = f'Т {i+1}'
                            else:
                                label = ''
                        
                        cumulative += step_increment
                        cumulative_labels.append(label)
                        cumulative_values.append(round(cumulative, 3))
                    
                    # 2. ГРАФИК ПО ДНЯМ (последние 30 дней)
                    daily_counts = {}
                    for change in changes:
                        if hasattr(change, 'moment') and change.moment:
                            day_key = change.moment.strftime('%d.%m')
                            daily_counts[day_key] = daily_counts.get(day_key, 0) + 1
                    
                    # Берем последние 14 дней для графика
                    daily_items = list(daily_counts.items())[-14:]
                    for day, count in daily_items:
                        daily_labels.append(day)
                        daily_values.append(count * step_increment)
                    
                    # 3. ГРАФИК ПО МЕСЯЦАМ (последние 12 месяцев)
                    monthly_counts = {}
                    for change in changes:
                        if hasattr(change, 'moment') and change.moment:
                            month_key = change.moment.strftime('%Y-%m')
                            monthly_counts[month_key] = monthly_counts.get(month_key, 0) + 1
                    
                    # Берем все месяцы с изменениями
                    for month, count in monthly_counts.items():
                        # Форматируем месяц
                        try:
                            date_obj = datetime.strptime(month, '%Y-%m')
                            month_label = date_obj.strftime('%b %Y')
                        except:
                            month_label = month
                        monthly_labels.append(month_label)
                        monthly_values.append(count * step_increment)
                    
                    # Если мало данных, добавляем текущий месяц
                    if not monthly_labels:
                        current_month = datetime.now().strftime('%b %Y')
                        monthly_labels.append(current_month)
                        monthly_values.append(0)
                
            except Exception as e:
                logging.warning(f"No access to device_changes for device {device_id}: {e}")
                # Если нет доступа, показываем пустые графики
                cumulative_labels = ['Нет доступа']
                cumulative_values = [current_value]
                daily_labels = ['Нет данных']
                daily_values = [0]
                monthly_labels = ['Нет данных']
                monthly_values = [0]
            
            # Формируем данные устройства
            device_data = {
                'id': device_id,
                'type_id': device[1] if len(device) > 1 else None,
                'pin': device[3] if len(device) > 3 else None,
                'serial_number': device[4] if len(device) > 4 else 'Без номера',
                'scale_unit_id': device[5] if len(device) > 5 else None,
                'step_increment': step_increment,
                'indicator': current_value,
                'state': bool(device[9]) if len(device) > 9 else False,
                'total_changes': total_changes,
                'cumulative_labels': cumulative_labels,
                'cumulative_values': cumulative_values,
                'daily_labels': daily_labels,
                'daily_values': daily_values,
                'monthly_labels': monthly_labels,
                'monthly_values': monthly_values
            }
            
            devices_data.append(device_data)

        return render_template(
            'dashboard.html', 
            username=session['username'],
            devices=devices_data,
            current_time=datetime.now()
        )

    except SQLAlchemyError as ex:
        logging.error("Database error in dashboard: %s", ex)
        return render_template('error.html', error="Ошибка получения данных")
    finally:
        if connect:
            close_connection(connect)


def prepare_chart_data(changes, step_increment, current_value):
    """ Подготовка данных для графика """
    if not changes:
        return {
            'time_labels': ['Нет данных'],
            'values': [current_value],
            'has_data': False
        }
    
    time_labels = []
    cumulative_values = []
    
    # Начинаем с начального значения
    initial_value = current_value - (len(changes) * step_increment)
    cumulative = initial_value
    
    # Берем только последние 20 изменений для читаемости графика
    recent_changes = changes[-20:] if len(changes) > 20 else changes
    
    for i, change in enumerate(recent_changes):
        if hasattr(change, 'moment') and change.moment:
            # Форматируем дату для подписи
            if len(recent_changes) <= 10:
                label = change.moment.strftime('%d.%m %H:%M')
            else:
                # Если много точек, показываем только каждую 3-ю
                if i % 3 == 0 or i == len(recent_changes) - 1:
                    label = change.moment.strftime('%d.%m')
                else:
                    label = ''
            
            cumulative += step_increment
            time_labels.append(label)
            cumulative_values.append(float(cumulative))
    
    return {
        'time_labels': time_labels,
        'values': cumulative_values,
        'initial_value': float(initial_value),
        'has_data': True
    }
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
            logging.info(f"row.id: {row.id} row.pin {row.pin}")
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
    changes = None
    mac_address = get_jwt_identity()

    if request.is_json:
        data = request.get_json()
    else:
        data = request.args

    if 'changes' not in data:
        if 'device_id' in data and 'moment' in data:
            changes = [
                {
                    'device_id': data.get('device_id'),
                    'moment': data.get('moment')
                }
            ]
    else:
        change_list = data.get('changes')
        if isinstance(change_list, list):
            changes = []
            for change in change_list:
                if 'device_id' in change and 'moment' in change:
                    changes.append(
                        {
                            'device_id': change.get('device_id'),
                            'moment': change.get('moment')
                        }
                    )

    if changes is None or not changes:
        return json_error(400, "Missing required parameters: device_id and moment"), 400

    connect = connect_database()
    if connect is None:
        return json_error(500, "Database connection error"), 500

    try:
        query = text("call public.add_device_changes(:mac_address, :device_id, :moment)")
        with connect.begin():
            for change in changes:
                connect.execute(query, {
                    "mac_address": mac_address,
                    "device_id": change.get('device_id'),
                    "moment": change.get('moment')
                })

        result_data = {
            "error": {},
            "result": {
                "success": True
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