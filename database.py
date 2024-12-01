import datetime
import hashlib
import random
import sys
import bcrypt
import psycopg2
from barcode import Code128
from barcode.writer import ImageWriter
from io import BytesIO
import serial
import time
import serial.tools.list_ports
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, \
    QGraphicsDropShadowEffect, QSpacerItem, QTableWidgetItem, QLineEdit, QTableWidget, QHeaderView, QListWidget
from PyQt5.QtChart import QChartView, QBarSeries, QBarSet, QChart, QBarCategoryAxis, QValueAxis
from PyQt5.QtCore import Qt, QMargins
from PyQt5.QtGui import QColor, QPainter, QFont, QBrush, QIcon
from PyQt5.QtCore import QTimer
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Функция для подключения к базе данных PostgreSQL
def connect_to_db():
    try:
        connection = psycopg2.connect(
            dbname="2024_psql_miros",
            user="2024_psql_m_usr",
            password="EUVMc7ilIbi8uZQA",
            host="5.183.188.132",
            port="5432"
        )
        return connection
    except Exception as error:
        print(f"Ошибка подключения к базе данных: {error}")
        sys.exit(1)

def authenticate_user(username, password):
    try:
        connection = connect_to_db()
        cursor = connection.cursor()

        # Получаем хеш пароля для указанного имени пользователя
        query = "SELECT password_hash FROM users WHERE username = %s;"
        cursor.execute(query, (username,))
        result = cursor.fetchone()

        if result is None:
            return False  # Пользователь не найден

        stored_password_hash = result[0]

        # Проверка пароля
        if bcrypt.checkpw(password.encode('utf-8'), stored_password_hash.encode('utf-8')):
            return True  # Аутентификация успешна

    except Exception as error:
        print(f"Ошибка при аутентификации пользователя: {error}")
    finally:
        if connection:
            cursor.close()
            connection.close()

    return False
# Получение всех активных посетителей с действующей подпиской
def get_active_visitors():
    try:
        connection = connect_to_db()
        cursor = connection.cursor()
        query = "SELECT first_name, last_name FROM visitor WHERE subscription_end >= CURRENT_DATE;"
        cursor.execute(query)
        result = cursor.fetchall()
        cursor.close()
        connection.close()
        return result
    except Exception as error:
        print(f"Ошибка при получении данных о посетителях: {error}")
        return []

# Получение посетителей, находящихся в зале (без времени выхода)
def get_visitors_in_gym():
    try:
        connection = connect_to_db()
        cursor = connection.cursor()
        query = """
        SELECT v.first_name, v.last_name
        FROM visitor v
        JOIN attendance_log a ON v.visitor_id = a.visitor_id
        WHERE a.check_out_time IS NULL;
        """
        cursor.execute(query)
        result = cursor.fetchall()
        cursor.close()
        connection.close()
        return result
    except Exception as error:
        print(f"Ошибка при получении данных о посетителях в зале: {error}")
        return []

# Получение тренеров, которые на дежурстве в данный момент
def get_duty_trainers():
    try:
        connection = connect_to_db()
        cursor = connection.cursor()
        query = """
            SELECT first_name, last_name 
            FROM trainer 
            WHERE duty_start <= CURRENT_TIME 
              AND duty_end >= CURRENT_TIME;
        """
        cursor.execute(query)
        result = cursor.fetchall()
        cursor.close()
        connection.close()
        return result
    except Exception as error:
        print(f"Ошибка при получении данных о тренерах: {error}")
        return []

# Добавление нового посетителя в базу данных
def add_new_visitor(first_name, last_name, phone_number, email, subscription_start, subscription_end):
    # Генерация пароля и его хэширование
    password = str(random.randint(100000, 999999))  # Простой 6-значный пароль
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    # Подключение к базе данных
    connection = connect_to_db()
    cursor = connection.cursor()

    # Вставка данных о новом посетителе в таблицу
    query = """
    INSERT INTO visitor (first_name, last_name, phone_number, email, card_number, subscription_start, subscription_end, barcode_image, password_hash, password_expiration)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW() + interval '1 year')
    """
    cursor.execute(query, (
        first_name, last_name, phone_number, email, None, subscription_start, subscription_end, None, password_hash
    ))

    connection.commit()
    cursor.close()
    connection.close()

    # Отправка email с паролем
    subject = "Ваш пароль для входа"
    message = f"Здравствуйте, {first_name}!\n\nВаш код для входа в приложение: {password}\n\nС уважением,\nКоманда"


    print(f"Пользователь {first_name} {last_name} успешно добавлен, и пароль отправлен на {email}")
    return password

# Проверка, находится ли посетитель в зале
def check_visitors_in_gym(card_number):
    try:
        connection = connect_to_db()
        cursor = connection.cursor()
        query = """
        SELECT v.visitor_id, a.check_in_time, a.check_out_time
        FROM visitor v
        LEFT JOIN attendance_log a ON v.visitor_id = a.visitor_id
        WHERE v.card_number = %s
        ORDER BY a.check_in_time DESC
        LIMIT 1;
        """
        cursor.execute(query, (card_number,))
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        return result  # Возвращаем данные о последнем посещении
    except Exception as error:
        print(f"Ошибка при проверке посетителя в зале: {error}")
        return None

# Начало посещения
def start_attendance(visitor_id):
    try:
        connection = connect_to_db()
        cursor = connection.cursor()
        query = """
        INSERT INTO attendance_log (visitor_id, check_in_time)
        VALUES (%s, CURRENT_TIMESTAMP)
        """
        cursor.execute(query, (visitor_id,))
        connection.commit()
        cursor.close()
        connection.close()
        print("Посещение началось")
    except Exception as error:
        print(f"Ошибка при начале посещения: {error}")

# Завершение посещения
def end_attendance(visitor_id):
    try:
        connection = connect_to_db()
        cursor = connection.cursor()
        query = """
        UPDATE attendance_log
        SET check_out_time = CURRENT_TIMESTAMP
        WHERE visitor_id = %s AND check_out_time IS NULL;
        """
        cursor.execute(query, (visitor_id,))
        connection.commit()
        cursor.close()
        connection.close()
        print("Посещение завершено")
    except Exception as error:
        print(f"Ошибка при завершении посещения: {error}")

# Фильтрация посетителей по имени, фамилии или телефону
def get_filtered_visitors(filter_text):
    try:
        connection = connect_to_db()
        cursor = connection.cursor()
        query = """
        SELECT first_name, last_name 
        FROM visitor 
        WHERE first_name ILIKE %s OR last_name ILIKE %s OR phone_number ILIKE %s;
        """
        filter_param = f"%{filter_text}%"
        cursor.execute(query, (filter_param, filter_param, filter_param))
        result = cursor.fetchall()
        cursor.close()
        connection.close()
        return result
    except Exception as error:
        print(f"Ошибка при фильтрации посетителей: {error}")
        return []

# Получение всех посетителей
def get_all_visitors():
    try:
        connection = connect_to_db()
        cursor = connection.cursor()
        query = "SELECT first_name, last_name FROM visitor;"
        cursor.execute(query)
        result = cursor.fetchall()
        cursor.close()
        connection.close()
        return result
    except Exception as error:
        print(f"Ошибка при получении данных о посетителях: {error}")
        return []

# Функция для проверки последнего посещения посетителя по номеру карты
def check_visitor_in_gym(card_number):
    try:
        connection = connect_to_db()
        cursor = connection.cursor()
        query = """
        SELECT v.visitor_id, a.check_in_time, a.check_out_time
        FROM visitor v
        LEFT JOIN attendance_log a ON v.visitor_id = a.visitor_id
        WHERE v.card_number = %s
        ORDER BY a.check_in_time DESC
        LIMIT 1;
        """
        cursor.execute(query, (card_number,))
        result = cursor.fetchone()
        cursor.close()
        connection.close()
        return result  # Возвращаем данные о последнем посещении конкретного посетителя
    except Exception as error:
        print(f"Ошибка при проверке конкретного посетителя в зале: {error}")
        return None

def check_visitors_in_gym():
    try:
        connection = connect_to_db()
        cursor = connection.cursor()
        query = """
        SELECT v.first_name, v.last_name
        FROM visitor v
        JOIN attendance_log a ON v.visitor_id = a.visitor_id
        WHERE a.check_out_time IS NULL;
        """
        cursor.execute(query)
        result = cursor.fetchall()
        cursor.close()
        connection.close()
        return result  # Возвращаем всех посетителей, которые находятся в зале (без времени выхода)
    except Exception as error:
        print(f"Ошибка при получении данных о посетителях в зале: {error}")
        return []



