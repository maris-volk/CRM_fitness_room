import datetime
import hashlib
import logging
import random
import sys
from collections import OrderedDict

import bcrypt
import psycopg2
from psycopg2 import pool
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
from PyQt5.QtGui import QColor, QPainter, QFont, QBrush, QIcon, QPixmap
from PyQt5.QtCore import QTimer
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Настройка пула соединений
connection_pool = psycopg2.pool.ThreadedConnectionPool(
    1, 20,  # Минимальное и максимальное количество соединений
    user='2024_psql_m_usr',
    password='EUVMc7ilIbi8uZQA',
    host='5.183.188.132',
    port='5432',
    database='2024_psql_miros'
)


def execute_query(query, params=None, fetch=True):
    """
    Выполняет SQL-запрос и возвращает результат.
    Если fetch=False, выполняет только запрос (например, INSERT, UPDATE).
    """
    conn = None
    try:
        conn = connection_pool.getconn()
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            if fetch:
                result = cursor.fetchall()
                return result
            else:
                conn.commit()
                return True
    except Exception as e:
        logger.error(f"Ошибка выполнения запроса: {e}")
        return None
    finally:
        if conn:
            connection_pool.putconn(conn)

def authenticate_user(username, password):
    """
    Проверяет учётные данные пользователя.
    Возвращает (user_id, role) при успешной аутентификации, иначе (None, None).
    """
    query = """
        SELECT user_id, password_hash, role FROM users WHERE username = %s
    """
    params = (username,)
    result = execute_query(query, params)
    if result:
        user_id, stored_hash, role = result[0]
        if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
            return user_id, role
    return None, None


def close_pool():
    """
    Закрывает все соединения в пуле. Вызывается при завершении работы приложения.
    """
    try:
        connection_pool.closeall()
        logger.info("Пул соединений закрыт")
    except psycopg2.DatabaseError as e:
        logger.error(f"Ошибка при закрытии пула соединений: {e}")


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
        print(f"ошибка подключения к базе данных: {error}")
        sys.exit(1)




def add_client(surname, first_name, patronymic, phone_number, subscription_id):
    """
    Добавляет нового клиента в базу данных.
    """
    query = """
        INSERT INTO client (surname, first_name, patronymic, phone_number, subscription)
        VALUES (%s, %s, %s, %s, %s) RETURNING client_id
    """
    result = execute_query(query, (surname, first_name, patronymic, phone_number, subscription_id))
    if result:
        return result[0][0]
    else:
        logger.error("Не удалось добавить клиента")
        return None


def get_active_visitors():
    """
    Возвращает общее количество активных посетителей.
    """
    query = """
        SELECT COUNT(*) FROM visit_fitness_room WHERE in_gym = TRUE
    """
    result = execute_query(query)
    if result:
        return result[0][0]
    else:
        logger.error("Не удалось получить количество активных посетителей")
        return 0


def count_visitors_in_gym():
    """
    Возвращает количество посетителей в зале.
    """
    query = """
        SELECT COUNT(*) FROM visit_fitness_room WHERE in_gym = TRUE
    """
    result = execute_query(query)
    if result:
        return result[0][0]
    else:
        logger.error("Не удалось посчитать посетителей в зале")
        return 0


def get_duty_trainers():
    """
    Возвращает список тренеров на смене.
    """
    query = """
        SELECT trainer_id, first_name, surname FROM trainer
    """
    results = execute_query(query)
    if results:
        return results
    else:
        logger.error("Не удалось получить список тренеров")
        return []


def check_visitor_in_gym(client_id):
    """
    Проверяет, находится ли посетитель в зале по client_id.
    Возвращает кортеж: (visit_id, in_gym, time_start, time_end) или None
    """
    query = """
        SELECT visit_id, in_gym, time_start, time_end
        FROM visit_fitness_room
        WHERE client = %s
        ORDER BY time_start DESC
        LIMIT 1
    """
    result = execute_query(query, (client_id,))
    if result:
        return result[0]
    else:
        logger.warning(f"Посетитель с ID {client_id} не найден")
        return None


def start_attendance(client_id):
    """
    Начинает посещение для клиента.
    """
    query = """
        INSERT INTO visit_fitness_room (time_start, in_gym, client)
        VALUES (NOW(), TRUE, %s) RETURNING visit_id
    """
    result = execute_query(query, (client_id,))
    if result:
        return result[0][0]
    else:
        logger.error("Не удалось начать посещение")
        return None


def end_attendance(visit_id):
    """
    Завершает посещение для указанного visit_id.
    """
    query = """
        UPDATE visit_fitness_room
        SET time_end = NOW(), in_gym = FALSE
        WHERE visit_id = %s
    """
    success = execute_query(query, (visit_id,), fetch=False)
    if success is None:
        logger.error(f"Не удалось завершить посещение ID {visit_id}")
    else:
        logger.info(f"Посещение ID {visit_id} успешно завершено")


def get_max_visitors_per_hour(start_date, end_date):
    """
    Возвращает количество посетителей по часам за указанный период.
    """
    query = """
        SELECT
            EXTRACT(HOUR FROM time_start) AS hour,
            COUNT(*) AS visitor_count
        FROM visit_fitness_room
        WHERE time_start BETWEEN %s AND %s
        GROUP BY EXTRACT(HOUR FROM time_start)
        ORDER BY hour
    """
    results = execute_query(query, (start_date, end_date))
    if results:
        # Создаём упорядоченный словарь для часов
        visitors_per_hour = OrderedDict()
        for row in results:
            hour = int(row[0])
            count = row[1]
            # Форматируем часы в виде "08-10", "10-12" и т.д.
            next_hour = hour + 2
            if next_hour > 23:
                next_hour = 23
            visitors_per_hour[f"{hour:02d}-{next_hour:02d}"] = count
        return visitors_per_hour
    else:
        logger.error("Нет данных для посетителей по часам")
        return {}


def get_average_visitors_per_weekday(start_date, end_date):
    """
    Возвращает среднее количество посетителей по дням недели за указанный период.
    """
    query = """
        SELECT
            TRIM(TO_CHAR(time_start, 'Day')) AS weekday,
            COUNT(*) AS visitor_count
        FROM visit_fitness_room
        WHERE time_start BETWEEN %s AND %s
        GROUP BY TRIM(TO_CHAR(time_start, 'Day'))
        ORDER BY 
            CASE TRIM(TO_CHAR(time_start, 'Day'))
                WHEN 'Monday' THEN 1
                WHEN 'Tuesday' THEN 2
                WHEN 'Wednesday' THEN 3
                WHEN 'Thursday' THEN 4
                WHEN 'Friday' THEN 5
                WHEN 'Saturday' THEN 6
                WHEN 'Sunday' THEN 7
            END
    """
    results = execute_query(query, (start_date, end_date))
    if results:
        # Создаём словарь для подсчёта количества дней
        day_counts = {}
        for row in results:
            weekday = row[0].strip()
            count = row[1]
            day_counts[weekday] = count

        # Вычисляем количество недель в периоде
        total_days = (end_date - start_date).days + 1
        total_weeks = total_days / 7

        average_visitors = {day: count / total_weeks for day, count in day_counts.items()}

        # Упорядочиваем по стандартному порядку недели
        weekdays_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        ordered_average_visitors = OrderedDict()
        for day in weekdays_order:
            ordered_average_visitors[day] = round(average_visitors.get(day, 0), 2)
        return ordered_average_visitors
    else:
        logger.error("Нет данных для средних посетителей по дням недели")
        return {}


def get_average_visitors_per_week_in_month(month, year):
    """
    Возвращает количество посетителей по неделям внутри указанного месяца и года.
    Неделя 1: дни 1-7
    Неделя 2: дни 8-14
    Неделя 3: дни 15-21
    Неделя 4: дни 22-28
    Неделя 5: дни 29-end
    """
    start_date = datetime.date(year, month, 1)
    if month == 12:
        end_date = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        end_date = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)

    query = """
        SELECT
            FLOOR((EXTRACT(day FROM time_start) - 1) / 7) + 1 AS week_number,
            COUNT(*) AS visitor_count
        FROM visit_fitness_room
        WHERE time_start BETWEEN %s AND %s
        GROUP BY week_number
        ORDER BY week_number
    """
    results = execute_query(query, (start_date, end_date))
    if results:
        week_visitors = OrderedDict()
        for row in results:
            week = int(row[0])
            count = row[1]
            week_visitors[f"Week {week}"] = count
        return week_visitors
    else:
        logger.error("Нет данных для посетителей по неделям месяца")
        return {}


def get_average_visitors_per_month(year):
    """
    Возвращает среднее количество посетителей по месяцам за указанный год.
    """
    query = """
        SELECT
            TO_CHAR(time_start, 'Month') AS month,
            COUNT(*) AS visitor_count
        FROM visit_fitness_room
        WHERE EXTRACT(YEAR FROM time_start) = %s
        GROUP BY TO_CHAR(time_start, 'Month'), EXTRACT(MONTH FROM time_start)
        ORDER BY EXTRACT(MONTH FROM time_start)
    """
    results = execute_query(query, (year,))
    if results:
        # Создаём словарь для подсчёта количества посещений
        month_counts = {}
        for row in results:
            month = row[0].strip()
            count = row[1]
            month_counts[month] = count

        # Вычисляем среднее посещений по месяцам (в данном случае среднее = общее, так как данные за один год)
        average_visitors = {month: count for month, count in month_counts.items()}

        # Упорядочиваем по стандартному порядку месяцев
        months_order = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        ordered_average_visitors = OrderedDict()
        for month in months_order:
            ordered_average_visitors[month] = average_visitors.get(month, 0)
        return ordered_average_visitors
    else:
        logger.error("Нет данных для средних посетителей по месяцам")
        return {}


def add_client(surname, first_name, patronymic, phone_number, subscription_id):
    """
    Добавляет нового клиента в базу данных.
    """
    query = """
        INSERT INTO client (surname, first_name, patronymic, phone_number, subscription)
        VALUES (%s, %s, %s, %s, %s) RETURNING client_id
    """
    result = execute_query(query, (surname, first_name, patronymic, phone_number, subscription_id))
    if result:
        return result[0][0]
    else:
        logger.error("Не удалось добавить клиента")
        return None


def get_active_visitors():
    """
    Возвращает общее количество активных посетителей.
    """
    query = """
        SELECT COUNT(*) FROM visit_fitness_room WHERE in_gym = TRUE
    """
    result = execute_query(query)
    if result:
        return result[0][0]
    else:
        logger.error("Не удалось получить количество активных посетителей")
        return 0


def count_visitors_in_gym():
    """
    Возвращает количество посетителей в зале.
    """
    query = """
        SELECT COUNT(*) FROM visit_fitness_room WHERE in_gym = TRUE
    """
    result = execute_query(query)
    if result:
        return result[0][0]
    else:
        logger.error("Не удалось посчитать посетителей в зале")
        return 0


def get_duty_trainers():
    """
    Возвращает список тренеров на смене.
    """
    query = """
        SELECT trainer_id, first_name, surname FROM trainer
    """
    results = execute_query(query)
    if results:
        return results
    else:
        logger.error("Не удалось получить список тренеров")
        return []


def check_visitor_in_gym(client_id):
    """
    Проверяет, находится ли посетитель в зале по client_id.
    Возвращает кортеж: (visit_id, in_gym, time_start, time_end) или None
    """
    query = """
        SELECT visit_id, in_gym, time_start, time_end
        FROM visit_fitness_room
        WHERE client = %s
        ORDER BY time_start DESC
        LIMIT 1
    """
    result = execute_query(query, (client_id,))
    if result:
        return result[0]
    else:
        logger.warning(f"Посетитель с ID {client_id} не найден")
        return None


def start_attendance(client_id):
    """
    Начинает посещение для клиента.
    """
    query = """
        INSERT INTO visit_fitness_room (time_start, in_gym, client)
        VALUES (NOW(), TRUE, %s) RETURNING visit_id
    """
    result = execute_query(query, (client_id,))
    if result:
        return result[0][0]
    else:
        logger.error("Не удалось начать посещение")
        return None


def end_attendance(visit_id):
    """
    Завершает посещение для указанного visit_id.
    """
    query = """
        UPDATE visit_fitness_room
        SET time_end = NOW(), in_gym = FALSE
        WHERE visit_id = %s
    """
    success = execute_query(query, (visit_id,), fetch=False)
    if success is None:
        logger.error(f"Не удалось завершить посещение ID {visit_id}")
    else:
        logger.info(f"Посещение ID {visit_id} успешно завершено")


def get_max_visitors_per_hour(start_date, end_date):
    """
    Возвращает количество посетителей по часам за указанный период.
    """
    query = """
        SELECT
            EXTRACT(HOUR FROM time_start) AS hour,
            COUNT(*) AS visitor_count
        FROM visit_fitness_room
        WHERE time_start BETWEEN %s AND %s
        GROUP BY EXTRACT(HOUR FROM time_start)
        ORDER BY hour
    """
    results = execute_query(query, (start_date, end_date))
    if results:
        # Создаём упорядоченный словарь для часов
        visitors_per_hour = OrderedDict()
        for row in results:
            hour = int(row[0])
            count = row[1]
            # Форматируем часы в виде "08-10", "10-12" и т.д.
            next_hour = hour + 2
            if next_hour > 23:
                next_hour = 23
            visitors_per_hour[f"{hour:02d}-{next_hour:02d}"] = count
        return visitors_per_hour
    else:
        logger.error("Нет данных для посетителей по часам")
        return {}


def get_average_visitors_per_weekday(start_date, end_date):
    """
    Возвращает среднее количество посетителей по дням недели за указанный период.
    """
    query = """
        SELECT
            TRIM(TO_CHAR(time_start, 'Day')) AS weekday,
            COUNT(*) AS visitor_count
        FROM visit_fitness_room
        WHERE time_start BETWEEN %s AND %s
        GROUP BY TRIM(TO_CHAR(time_start, 'Day'))
        ORDER BY 
            CASE TRIM(TO_CHAR(time_start, 'Day'))
                WHEN 'Monday' THEN 1
                WHEN 'Tuesday' THEN 2
                WHEN 'Wednesday' THEN 3
                WHEN 'Thursday' THEN 4
                WHEN 'Friday' THEN 5
                WHEN 'Saturday' THEN 6
                WHEN 'Sunday' THEN 7
            END
    """
    results = execute_query(query, (start_date, end_date))
    if results:
        # Создаём словарь для подсчёта количества дней
        day_counts = {}
        for row in results:
            weekday = row[0].strip()
            count = row[1]
            day_counts[weekday] = count

        # Вычисляем количество недель в периоде
        total_days = (end_date - start_date).days + 1
        total_weeks = total_days / 7

        average_visitors = {day: count / total_weeks for day, count in day_counts.items()}

        # Упорядочиваем по стандартному порядку недели
        weekdays_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        ordered_average_visitors = OrderedDict()
        for day in weekdays_order:
            ordered_average_visitors[day] = round(average_visitors.get(day, 0), 2)
        return ordered_average_visitors
    else:
        logger.error("Нет данных для средних посетителей по дням недели")
        return {}


def get_visitors_per_week_in_month(month, year):
    """
    Возвращает количество посетителей по неделям внутри указанного месяца и года.
    Неделя 1: дни 1-7
    Неделя 2: дни 8-14
    Неделя 3: дни 15-21
    Неделя 4: дни 22-28
    Неделя 5: дни 29-end
    """
    start_date = datetime.date(year, month, 1)
    if month == 12:
        end_date = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
    else:
        end_date = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)

    query = """
        SELECT
            FLOOR((EXTRACT(day FROM time_start) - 1) / 7) + 1 AS week_number,
            COUNT(*) AS visitor_count
        FROM visit_fitness_room
        WHERE time_start BETWEEN %s AND %s
        GROUP BY week_number
        ORDER BY week_number
    """
    results = execute_query(query, (start_date, end_date))
    if results:
        week_visitors = OrderedDict()
        for row in results:
            week = int(row[0])
            count = row[1]
            week_visitors[f"Week {week}"] = count
        return week_visitors
    else:
        logger.error("Нет данных для посетителей по неделям месяца")
        return {}


# 2. Подсчет количества активных клиентов
def get_active_visitors():
    """
    Подсчитывает количество активных клиентов с действующей подпиской.

    :return: Количество активных клиентов.
    """
    try:
        query = """
            SELECT COUNT(*)
            FROM client c
            INNER JOIN subscription s ON c.subscription = s.subscription_id
            WHERE s.is_valid = TRUE
              AND s.valid_until >= CURRENT_DATE;
        """
        result = execute_query(query)
        return result[0][0] if result else 0

    except Exception as e:
        logger.error(f"Ошибка при подсчете активных клиентов: {e}")
        return 0


# 3. Подсчет посетителей, находящихся в зале
def count_visitors_in_gym():
    """
    Подсчитывает количество клиентов, которые в данный момент находятся в зале.

    :return: Количество клиентов, находящихся в зале.
    """
    try:
        query = """
            SELECT COUNT(*)
            FROM visit_fitness_room
            WHERE in_gym = TRUE;
        """
        result = execute_query(query)
        return result[0][0] if result else 0

    except Exception as e:
        logger.error(f"Ошибка при подсчете посетителей в зале: {e}")
        return 0




# 5. Добавление нового посетителя
def add_new_visitor(surname, first_name, patronymic, phone_number, subscription_id):
    """
    Добавляет нового посетителя в таблицу client.

    :param surname: Фамилия клиента.
    :param first_name: Имя клиента.
    :param patronymic: Отчество клиента.
    :param phone_number: Номер телефона клиента.
    :param subscription_id: ID подписки клиента.
    :return: True если добавление успешно, иначе False.
    """
    try:
        query = """
            INSERT INTO client (surname, first_name, patronymic, phone_number, subscription)
            VALUES (%s, %s, %s, %s, %s);
        """
        params = (surname, first_name, patronymic, phone_number, subscription_id)
        execute_query(query, params, fetch=False)
        logger.info(f"Новый посетитель '{first_name} {surname}' добавлен успешно.")
        return True
    except Exception as e:
        logger.error(f"Ошибка при добавлении нового посетителя: {e}")
        return False


# 6. Проверка статуса посещения посетителя
def check_visitor_in_gym(card_number):
    """
    Проверяет, находится ли посетитель с данным номером карты в зале.

    :param card_number: Номер карты посетителя.
    :return: Кортеж (visit_id, in_gym, time_start, time_end) или None.
    """
    try:
        query = """
            SELECT v.visit_id, v.in_gym, v.time_start, v.time_end
            FROM visit_fitness_room v
            JOIN client c ON v.client = c.client_id
            WHERE c.phone_number = %s
            ORDER BY v.time_start DESC
            LIMIT 1;
        """
        # Предполагаем, что card_number хранится в phone_number. Если нет, измените поле.
        params = (card_number,)
        result = execute_query(query, params)
        return result[0] if result else None

    except Exception as e:
        logger.error(f"Ошибка при проверке статуса посещения посетителя: {e}")
        return None


# 7. Начало посещения (посетитель входит в зал)
def start_attendance(client_id):
    """
    Начинает посещение посетителя.

    :param client_id: ID клиента.
    :return: True если успешно, иначе False.
    """
    try:
        query = """
            INSERT INTO visit_fitness_room (time_start, client, in_gym)
            VALUES (CURRENT_TIMESTAMP, %s, TRUE);
        """
        params = (client_id,)
        execute_query(query, params, fetch=False)
        logger.info(f"Посещение клиента ID {client_id} начато.")
        return True
    except Exception as e:
        logger.error(f"Ошибка при начале посещения: {e}")
        return False


# 8. Завершение посещения (посетитель покидает зал)
def end_attendance(visit_id):
    """
    Завершает посещение посетителя.

    :param visit_id: ID посещения.
    :return: True если успешно, иначе False.
    """
    try:
        query = """
            UPDATE visit_fitness_room
            SET time_end = CURRENT_TIMESTAMP,
                in_gym = FALSE
            WHERE visit_id = %s;
        """
        params = (visit_id,)
        execute_query(query, params, fetch=False)
        logger.info(f"Посещение ID {visit_id} завершено.")
        return True
    except Exception as e:
        logger.error(f"Ошибка при завершении посещения: {e}")
        return False


# 9. Добавление нового администратора
def add_new_administrator(user_id, surname, first_name, patronymic, phone_number, photo_path):
    """
    Добавляет нового администратора в таблицу administrators.

    :param user_id: ID пользователя из таблицы users.
    :param surname: Фамилия администратора.
    :param first_name: Имя администратора.
    :param patronymic: Отчество администратора.
    :param phone_number: Номер телефона администратора.
    :param photo_path: Путь к фото администратора.
    :return: True если добавление успешно, иначе False.
    """
    try:
        with open(photo_path, 'rb') as file:
            photo_data = file.read()

        query = """
            INSERT INTO administrators (user_id, surname, first_name, patronymic, phone_number, photo)
            VALUES (%s, %s, %s, %s, %s, %s);
        """
        params = (user_id, surname, first_name, patronymic, phone_number, psycopg2.Binary(photo_data))
        execute_query(query, params, fetch=False)
        logger.info(f"Новый администратор '{first_name} {surname}' добавлен успешно.")
        return True
    except Exception as e:
        logger.error(f"Ошибка при добавлении администратора: {e}")
        return False


# 10. Получение списка всех клиентов
def get_all_clients():
    """
    Получает список всех клиентов.

    :return: Список кортежей с данными клиентов.
    """
    try:
        query = """
            SELECT client_id, surname, first_name, patronymic, phone_number, subscription
            FROM client;
        """
        result = execute_query(query)
        return result if result else []
    except Exception as e:
        logger.error(f"Ошибка при получении списка клиентов: {e}")
        return []


# 11. Получение списка всех тренеров
def get_all_trainers():
    """
    Получает список всех тренеров.

    :return: Список кортежей с данными тренеров.
    """
    try:
        query = """
            SELECT trainer_id, surname, first_name, patronymic, phone_number, description
            FROM trainer;
        """
        result = execute_query(query)
        return result if result else []
    except Exception as e:
        logger.error(f"Ошибка при получении списка тренеров: {e}")
        return []


# 12. Получение списка всех подписок
def get_all_subscriptions():
    """
    Получает список всех подписок.

    :return: Список кортежей с данными подписок.
    """
    try:
        query = """
            SELECT subscription_id, tariff, valid_since, valid_until, is_valid, price, count_of_visits
            FROM subscription;
        """
        result = execute_query(query)
        return result if result else []
    except Exception as e:
        logger.error(f"Ошибка при получении списка подписок: {e}")
        return []


# 13. Получение списка всех тарифов
def get_all_tariffs():
    """
    Получает список всех тарифов.

    :return: Список кортежей с данными тарифов.
    """
    try:
        query = """
            SELECT k_type, k_time, k_period_or_n
            FROM tariff;
        """
        result = execute_query(query)
        return result if result else []
    except Exception as e:
        logger.error(f"Ошибка при получении списка тарифов: {e}")
        return []


# 14. Получение списка всех администраторов
def get_all_administrators():
    """
    Получает список всех администраторов.

    :return: Список кортежей с данными администраторов.
    """
    try:
        query = """
            SELECT admin_id, user_id, surname, first_name, patronymic, phone_number, photo
            FROM administrators;
        """
        result = execute_query(query)
        return result if result else []
    except Exception as e:
        logger.error(f"Ошибка при получении списка администраторов: {e}")
        return []


# 15. Добавление нового тренера
def add_trainer(surname, first_name, patronymic, phone_number, description, photo_path):
    """
    Добавляет нового тренера в базу данных.

    :param surname: Фамилия тренера.
    :param first_name: Имя тренера.
    :param patronymic: Отчество тренера.
    :param phone_number: Номер телефона тренера.
    :param description: Описание тренера.
    :param photo_path: Путь к фото тренера.
    :return: True если добавление успешно, иначе False.
    """
    try:
        with open(photo_path, 'rb') as file:
            photo_data = file.read()

        query = """
            INSERT INTO trainer (surname, first_name, patronymic, phone_number, description, photo)
            VALUES (%s, %s, %s, %s, %s, %s);
        """
        params = (surname, first_name, patronymic, phone_number, description, psycopg2.Binary(photo_data))
        execute_query(query, params, fetch=False)
        logger.info(f"Новый тренер '{first_name} {surname}' добавлен успешно.")
        return True
    except Exception as e:
        logger.error(f"Ошибка при добавлении тренера: {e}")
        return False


# 16. Получение фотографии тренера
def get_trainer_photo(trainer_id):
    """
    Получает фотографию тренера.

    :param trainer_id: ID тренера.
    :return: QPixmap объект с фотографией или None.
    """
    try:
        query = """
            SELECT photo FROM trainer WHERE trainer_id = %s;
        """
        result = execute_query(query, (trainer_id,))
        if result and result[0][0]:
            photo_data = result[0][0]
            pixmap = QPixmap()
            pixmap.loadFromData(photo_data)
            return pixmap
        return None
    except Exception as e:
        logger.error(f"Ошибка при получении фотографии тренера: {e}")
        return None


# 17. Максимальное количество посетителей за определённые часы на протяжении дня


# 18. Среднее число посетителей по дням недели


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
