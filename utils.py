import datetime
import hashlib
import random
import sys
import hashlib

import bcrypt
from barcode import Code128
from barcode.writer import ImageWriter
import hashlib
import datetime
from barcode import Code128
from barcode.writer import ImageWriter
import psycopg2
from io import BytesIO
import psycopg2
import serial
import time
import serial.tools.list_ports
import psycopg2  # Для подключения к базе данных PostgreSQL
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, \
    QGraphicsDropShadowEffect, QSpacerItem, QTableWidgetItem, QLineEdit, QTableWidget, QHeaderView, QListWidget
from PyQt5.QtChart import QChartView, QBarSeries, QBarSet, QChart, QBarCategoryAxis, QValueAxis
from PyQt5.QtCore import Qt, QMargins, QDir, pyqtSignal, QThread, QSettings
from PyQt5.QtGui import QColor, QPainter, QFont, QBrush, QIcon, QFontDatabase
from PyQt5.QtCore import QTimer
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import datetime

from database import connect_to_db


class WorkerThread(QThread):
    result_signal = pyqtSignal(object)

    def __init__(self, func, *args):
        super().__init__()
        self.func = func
        self.args = args
        self._is_running = False

    def run(self):
        if self._is_running:

            return

        self._is_running = True
        try:
            result = self.func(*self.args)
            self.result_signal.emit(result)
        finally:
            self._is_running = False

def load_fonts_from_dir(directory):
    families = set()
    for fi in QDir(directory).entryInfoList(["*.ttf", "*.woff", "*.woff2"]):
        _id = QFontDatabase.addApplicationFont(fi.absoluteFilePath())
        families |= set(QFontDatabase.applicationFontFamilies(_id))
    return families


class TariffCalculator:
    def __init__(self):
        self.settings = QSettings("fdfdfdsdddf", "fefsdsdsddfdf")
        self.tariffs = self.load_tariffs()

    def load_tariffs(self):
        """Загружаем тарифы из базы данных или из кэша."""
        tariffs = self.settings.value("tariffs", None)
        if tariffs is None:
            return self.load_tariffs_from_db()  # Синхронная загрузка тарифов
        else:
            return tariffs

    def load_tariffs_from_db(self):
        """Загружаем тарифы из базы данных."""
        tariffs = {}
        query = "SELECT k_type, k_time, k_period_or_n FROM tariff"

        # Подключаемся к базе данных здесь
        connection = connect_to_db()
        cursor = connection.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()

        for row in rows:
            k_type, k_time, k_period_or_n = row
            tariffs[k_type] = {'k_time': k_time, 'k_period_or_n': k_period_or_n}

        # Закрываем соединение с БД
        cursor.close()
        connection.close()

        # Кэшируем тарифы в QSettings
        self.settings.setValue("tariffs", tariffs)
        print(444444,tariffs)

        return tariffs

    def calculate_price(self, period, k_class, k_time, base_price):
        """Расчет цены с использованием выбранных опций."""
        # Формируем ключ для тарифа в зависимости от выбранных опций
        k_type = self.generate_k_type(period, k_class, k_time)

        tariff = self.tariffs.get(k_type)
        if tariff:
            price = base_price * tariff['k_time'] * tariff['k_period_or_n']
            return price
        else:
            raise ValueError(f"Тариф {k_type} не найден")

    def generate_k_type(self, period, k_class, k_time):
        """Генерируем ключ для тарифа на основе выбранных опций."""
        period_map = {"Месяц": "mnth", "Полгода": "hyr", "Год": "yr"}
        class_map = {"8": "8", "12": "12", "безлимит": "unlim"}
        time_map = {"<16ч": "evn", ">16ч": "mrn", "безлимит": "unlim"}

        period_key = period_map.get(period)
        class_key = class_map.get(k_class)
        time_key = time_map.get(k_time)

        if period_key and class_key and time_key:
            return f"{class_key}_{time_key}_{period_key}"
        else:
            raise ValueError("Неверные параметры для тарифа.")


def format_datetime(date_obj):
    """Форматирует объект даты в строку 'ДД.ММ.ГГ'"""
    if isinstance(date_obj, datetime.date):
        return date_obj.strftime("%d.%m.%y")
    return ""

def calculate_age(birth_date):
    """Вычисляет возраст на основе даты рождения"""
    today = datetime.date.today()
    delta = today - birth_date
    return delta.days // 365

def get_day_of_week(date_obj):
    """Возвращает день недели для заданной даты"""
    return date_obj.strftime("%A")  # Например, 'Monday'

def get_time_slot(time):
    """Определяет временной интервал по времени"""
    if isinstance(time, datetime.time):
        if time < datetime.time(10, 0):
            return "08-10"
        elif time < datetime.time(12, 0):
            return "10-12"
        elif time < datetime.time(14, 0):
            return "12-14"
        elif time < datetime.time(16, 0):
            return "14-16"
        elif time < datetime.time(18, 0):
            return "16-18"
        elif time < datetime.time(20, 0):
            return "18-20"
        else:
            return "20-22"
    return ""

def is_valid_visitor_data(data):
    """Проверяет, валидны ли данные о посетителе (например, ID или имя)"""
    if isinstance(data, dict):
        required_fields = ["name", "id", "subscription_status"]
        return all(field in data and bool(data[field]) for field in required_fields)
    return False


def scan_card():
    baudrate = 115200  # Скорость передачи данных может отличаться
    card_number = None

    # Получаем список всех доступных портов
    available_ports = serial.tools.list_ports.comports()

    for port_info in available_ports:
        port = port_info.device  # Имя устройства (например, COM3 или /dev/ttyUSB0)
        print(f"Попытка подключения к {port}")

        try:
            serial_port = serial.Serial(port, baudrate, timeout=1)  # Добавлен таймаут для ускорения процесса

            while True:
                if serial_port.in_waiting > 0:
                    data = serial_port.read(serial_port.in_waiting).decode('utf-8')  # Чтение и декодирование данных
                    print(f"Полученные данные с {port}: {data}")
                    card_number = data.strip()  # Обрезка лишних пробелов или символов
                    break
                time.sleep(0.1)

            if card_number:
                break  # Если карта найдена, выходим из цикла

        except serial.SerialException as e:
            print(f"Ошибка подключения к {port}: {e}")

        finally:
            if 'serial_port' in locals() and serial_port.is_open:
                serial_port.close()

    if card_number:
        print(f"Карта найдена: {card_number}")
    else:
        print("Сканер не найден на доступных портах")

    return card_number