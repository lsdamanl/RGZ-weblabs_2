from flask import Blueprint, request, session, jsonify, current_app, render_template
import psycopg2
from psycopg2.extras import RealDictCursor
from os import path
import sqlite3

room = Blueprint('room', __name__)


def db_connect():
    if current_app.config['DB_TYPE'] == 'postgres':
        conn = psycopg2.connect(
            host='127.0.0.1',
            database='shipilov_dmitriy_knowledge_base',
            user='shipilov_dmitriy_knowledge_base',
            password='123'
        )
        cur = conn.cursor(cursor_factory=RealDictCursor)
    else:
        dir_path = path.dirname(path.realpath(__file__))
        db_path = path.join(dir_path, "database.db")
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
    return conn, cur

def db_close(conn, cur):
    conn.commit()
    cur.close()
    conn.close()


@room.route('/storage_room/')
def lab():
    return render_template('storage_room/room.html')


@room.route('/json-rpc', methods=['POST'])
def jsonrpc():
    request_data = request.get_json()
    if not request_data or 'method' not in request_data:
        return jsonify({
            'jsonrpc': '2.0',
            'error': {'code': -32600, 'message': 'Invalid Request'},
            'id': request_data.get('id') if request_data else None
        }), 400

    method = request_data['method']
    params = request_data.get('params', {})
    request_id = request_data.get('id')

    try:
        if method == 'get_rooms':
            result = get_rooms()
        elif method == 'booking':
            room_number = params.get('room_number')
            result = booking(room_number)
        elif method == 'cancellation':
            room_number = params.get('room_number')
            result = cancellation(room_number)
        elif method == 'release':
            room_number = params.get('room_number')
            result = release(room_number)
        else:
            raise ValueError("Method not found")

        return jsonify({'jsonrpc': '2.0', 'result': result, 'id': request_id}), 200

    except ValueError as e:
        return jsonify({
            'jsonrpc': '2.0',
            'error': {'code': -32601, 'message': str(e)},
            'id': request_id
        }), 404
    except Exception as e:
        return jsonify({
            'jsonrpc': '2.0',
            'error': {'code': -32603, 'message': 'Internal error', 'data': str(e)},
            'id': request_id
        }), 500



def get_rooms():
    login = session.get('login')
    conn, cur = db_connect()

    cur.execute("SELECT * FROM rooms")
    rooms = [dict(row) for row in cur.fetchall()]

    total_rooms = len(rooms)
    occupied_rooms = sum(1 for room in rooms if room['tenant'])
    free_rooms = total_rooms - occupied_rooms

    if not login:
        for room in rooms:
            if room['tenant']:
                room['tenant'] = 'Зарезервирована'

    db_close(conn, cur)
    return {'rooms': rooms, 'free': free_rooms, 'occupied': occupied_rooms}


def booking(room_number):
    login = session.get('login')
    if not login:
        return render_template('storage_room/room.html', error='Пожалуйста, авторизуйтесь')

    conn, cur = db_connect()

    try:

        if current_app.config['DB_TYPE'] == 'postgres':
            cur.execute("SELECT COUNT(*) as count FROM rooms WHERE tenant = %s", (login,))
        else:
            cur.execute("SELECT COUNT(*) as count FROM rooms WHERE tenant = ?", (login,))
        count = cur.fetchone()['count']

        if count >= 5:
            return render_template('storage_room/room.html', error='Вы не можете забронировать больше 5 ячеек')

        if current_app.config['DB_TYPE'] == 'postgres':
            cur.execute("SELECT tenant FROM rooms WHERE number = %s", (room_number,))
        else:
            cur.execute("SELECT tenant FROM rooms WHERE number = ?", (room_number,))
        room = cur.fetchone()

        if room and room['tenant']:
            return render_template('storage_room/room.html', error='Комната уже забронирована')

        if current_app.config['DB_TYPE'] == 'postgres':
            cur.execute("UPDATE rooms SET tenant = %s WHERE number = %s", (login, room_number))
        else:
            cur.execute("UPDATE rooms SET tenant = ? WHERE number = ?", (login, room_number))

        return render_template('storage_room/room.html', message='Успешно забронировано')

    finally:
        db_close(conn, cur)

def cancellation(room_number):
    login = session.get('login')
    if not login:
        raise ValueError('Не авторизован')

    conn, cur = db_connect()

    if current_app.config['DB_TYPE'] == 'postgres':
        cur.execute("SELECT tenant FROM rooms WHERE number = %s", (room_number,))
    else:
        cur.execute("SELECT tenant FROM rooms WHERE number = ?", (room_number,))
    room = cur.fetchone()

    if room and room['tenant'] != login:
        db_close(conn, cur)
        raise ValueError('Вы не можете снять чужую бронь')

    if current_app.config['DB_TYPE'] == 'postgres':
        cur.execute("UPDATE rooms SET tenant = NULL WHERE number = %s", (room_number,))
    else:
        cur.execute("UPDATE rooms SET tenant = NULL WHERE number = ?", (room_number,))

    db_close(conn, cur)
    return {'message': 'Бронирование отменено'}


def release(room_number):
    return cancellation(room_number)  
