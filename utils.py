import datetime
import hashlib
import logging
import os
import random
import sys
import hashlib
import traceback

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
    QGraphicsDropShadowEffect, QSpacerItem, QTableWidgetItem, QLineEdit, QTableWidget, QHeaderView, QListWidget, \
    QSizePolicy, QMenu, QAction, QWidgetAction, QMessageBox, QDialog
from PyQt5.QtChart import QChartView, QBarSeries, QBarSet, QChart, QBarCategoryAxis, QValueAxis
from PyQt5.QtCore import Qt, QMargins, QDir, pyqtSignal, QThread, QSettings, QRectF, QPointF, QPoint
from PyQt5.QtGui import QColor, QPainter, QFont, QBrush, QIcon, QFontDatabase, QPixmap, QPainterPath, QRegion, QCursor, \
    QPen
from PyQt5.QtCore import QTimer
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import datetime

from client_profile import ClientProfileWindow
from database import connect_to_db, get_all_admins, check_today_visits, register_visit, deactivate_subscription, \
    get_subscription_info, get_client_id_by_card
from hover_button import HoverButton

logger = logging.getLogger(__name__)


class RoundedMenu(QMenu):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont("Unbounded", 10))  # Устанавливаем шрифт
        self.radius = 10  # Радиус закругления углов
        self.setStyleSheet(f"""
            QMenu {{
                background: white;
                border: 2px solid #05A9A3;
                border-top-left-radius: 0px;  
                border-top-right-radius: 0px;  
                border-bottom-left-radius: {self.radius}px;
                border-bottom-right-radius: {self.radius}px;
                padding: 5px;
            }}
        """)

    def add_colored_action(self, text, color, callback):
        """
        Создает пункт меню с собственной шириной, зависящей только от его содержимого.
        """
        action_widget = HoverLabel(text, color, callback, self)

        widget_action = QWidgetAction(self)
        widget_action.setDefaultWidget(action_widget)
        self.addAction(widget_action)

        # Устанавливаем минимальную ширину по максимальному содержимому
        action_width = action_widget.sizeHint().width() + 20  # Немного добавляем отступ
        if action_width > self.width():
            self.setMinimumWidth(action_width)

    def resizeEvent(self, event):
        """
        Устанавливает форму меню с закругленными углами снизу и прямым верхом.
        """
        path = QPainterPath()
        rect = QRectF(self.rect()).adjusted(0, 0, -1, -1)  # Убираем 1px для устранения выступов
        radius = self.radius

        # Создаем путь с закругленными только нижними углами
        path.moveTo(rect.topLeft())
        path.lineTo(rect.topRight())
        path.lineTo(rect.bottomRight().x(), rect.bottomRight().y() - radius)
        path.quadTo(rect.bottomRight(), rect.bottomRight() - QPointF(radius, 0))
        path.lineTo(rect.bottomLeft().x() + radius, rect.bottomLeft().y())
        path.quadTo(rect.bottomLeft(), rect.bottomLeft() - QPointF(0, radius))
        path.lineTo(rect.topLeft())

        # Применяем маску для закругленных углов
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def enterEvent(self, event):
        """
        Устанавливает флаг, что курсор наведён на меню.
        """
        self.parent().hovered = True
        super().enterEvent(event)

    def leaveEvent(self, event):
        """
        Устанавливает флаг, что курсор покинул меню.
        """

        self.parent().hovered = False
        super().leaveEvent(event)


class HoverLabel(QWidget):
    """
    Кастомный пункт меню, который занимает минимально возможное место в ширину,
    сохраняет нормальную высоту, меняет курсор только при наведении на текст
    и подсвечивается при наведении.
    """

    def __init__(self, text, color, callback, parent=None):
        super().__init__(parent)
        self.callback = callback

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)  # Отступы для комфортной высоты
        layout.setSpacing(0)

        self.label = QLabel(text)
        self.label.setFont(QFont("Unbounded", 12))
        self.label.setStyleSheet(f"color: {color}; font-weight: bold;")
        self.label.setCursor(QCursor(Qt.PointingHandCursor))  # Курсор меняется только на тексте
        self.label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.label)
        self.setLayout(layout)

        self.setGraphicsEffect(self.create_shadow_effect())
        self.graphicsEffect().setEnabled(False)

        self.label.mousePressEvent = self.mousePressEvent  # Привязываем событие клика к лейблу

    def create_shadow_effect(self):
        """
        Создаёт эффект свечения при наведении.
        """
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)  # Радиус размытия
        shadow.setXOffset(0)  # Смещение по X
        shadow.setYOffset(0)  # Смещение по Y
        shadow.setColor(QColor(5, 169, 163, 100))  # Полупрозрачный цвет свечения
        return shadow

    def enterEvent(self, event):
        """
        Активирует свечение при наведении.
        """
        self.graphicsEffect().setEnabled(True)

    def leaveEvent(self, event):
        """
        Отключает свечение при уходе курсора.
        """
        self.graphicsEffect().setEnabled(False)

    def mousePressEvent(self, event):
        """
        Выполняет действие при нажатии (если кликнули по тексту).
        """
        if self.callback:
            self.callback()


def resources_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class ClickableLabelForSlots(QLabel):
    def __init__(self, text, client_id, role=None,parent=None):
        super().__init__(text, parent)
        self.role = role
        self.client_id = client_id
        self.setCursor(Qt.PointingHandCursor)  # Делаем курсор в виде указателя (рука)

    def mousePressEvent(self, event):
        """Открывает окно профиля клиента при клике"""
        if self.client_id:
            self.client_profile_window = ClientProfileWindow(self.client_id,self.role)
            self.client_profile_window.show()


class LoadAdminsThread(QThread):
    result_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)

    def run(self):
        try:
            admins = get_all_admins()
            self.result_signal.emit(admins)
        except Exception as e:
            self.error_signal.emit(str(e))


def correct_to_nominative_case(month_name):
    """Корректирует родительный падеж месяца в именительный, с большой буквы."""
    # Месяцы в родительном падеже
    months_genitive = {
        "января": "январь",
        "февраля": "февраль",
        "марта": "март",
        "апреля": "апрель",
        "мая": "май",
        "июня": "июнь",
        "июля": "июль",
        "августа": "август",
        "сентября": "сентябрь",
        "октября": "октябрь",
        "ноября": "ноябрь",
        "декабря": "декабрь"
    }

    # Возвращаем месяц в именительном падеже с большой буквы
    return months_genitive.get(month_name.lower(), month_name).capitalize()


def center(self):
    """Центрирует окно на экране"""

    screen_geometry = QApplication.primaryScreen().availableGeometry()  # Получаем размеры экрана
    screen_center = screen_geometry.center()  # Находим центр экрана
    window_geometry = self.frameGeometry()  # Получаем геометрию окна
    window_geometry.moveCenter(screen_center)  # Центрируем окно по экрану
    self.move(window_geometry.topLeft())  # Перемещаем окно в вычисленную позицию


class ClickableLabel(QLabel):
    # Создаем сигнал, который будет срабатывать при клике на метку
    clicked = pyqtSignal()

    def __init__(self, text='', parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, event):
        # При клике на метку генерируется сигнал
        self.clicked.emit()


class WorkerThread(QThread):
    result_signal = pyqtSignal(object)  # Сигнал для передачи результата
    error_signal = pyqtSignal(str)  # Сигнал для передачи ошибок
    finished_signal = pyqtSignal()  # Сигнал для завершения потока

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._stop_requested = False  # Флаг для остановки потока

    def run(self):
        try:
            if not self._stop_requested:  # Проверяем, остановлен ли поток
                result = self.func(*self.args, **self.kwargs)
                self.result_signal.emit(result)  # Отправляем результат
        except Exception as e:
            self.error_signal.emit(str(e))  # Отправляем сообщение об ошибке
        finally:
            self.finished_signal.emit()  # Сигнал о завершении потока

    def stop(self):
        self._stop_requested = True


class ScanCardDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__()
        self.setWindowTitle("Сканирование карты")

        self.oldPos = self.pos()
        self.radius = 18
        self.borderWidth = 5
        self.setGeometry(300, 300, 400, 200)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.card_number = None  # Инициализация атрибута
        self.initUI()

    def accept(self):
        """Вызывается при успешном сканировании карты."""
        if self.card_number:
            super().accept()
        else:
            QMessageBox.warning(self, "Ошибка", "Карта не была отсканирована.")

    def reject(self):
        """Вызывается при нажатии кнопки "Отмена"."""
        self.card_number = None  # Сбрасываем состояние
        super().reject()

    def initUI(self):
        layout = QVBoxLayout(self)

        self.label = QLabel("Ожидание сканирования карты...", self)
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        self.cancel_button = HoverButton("Отмена")
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.cancel_button)

        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        layout.addItem(spacer)

        self.setLayout(layout)

        # Запускаем сканирование в отдельном потоке
        self.start_scan()

    def start_scan(self):
        self.scan_thread = WorkerThread(self.scan_card)
        self.scan_thread.result_signal.connect(self.process_card)
        self.scan_thread.error_signal.connect(self.show_error)
        self.scan_thread.start()

    def scan_card(self):
        """Сканирование карты с последовательного порта с тайм-аутом"""
        baudrate = 115200
        card_number = None
        timeout_seconds = 5  # Максимальное время ожидания сканирования
        start_time = time.time()

        available_ports = serial.tools.list_ports.comports()
        for port_info in available_ports:
            port = port_info.device
            try:
                serial_port = serial.Serial(port, baudrate, timeout=1)

                while time.time() - start_time < timeout_seconds:
                    if self.scan_thread._stop_requested:  # Проверяем, не остановлен ли поток
                        return None

                    if serial_port.in_waiting > 0:
                        data = serial_port.read(serial_port.in_waiting).decode('utf-8')
                        card_number = data.strip()
                        break
                    time.sleep(0.1)  # Ждем данные

                if card_number:
                    break  # Если получили карту, выходим из цикла портов

            except serial.SerialException as e:
                print(f"Ошибка работы с портом {port}: {e}")
                continue

            finally:
                if 'serial_port' in locals() and serial_port.is_open:
                    serial_port.close()

        return card_number

    def process_card(self, card_number):
        """Проверка и регистрация визита"""
        if not card_number:
            QMessageBox.warning(self, "Ошибка", "Карта не была отсканирована.")
            self.reject()
            return

        self.card_number = card_number  # Сохраняем номер карты
        self.db_thread = WorkerThread(self.handle_card_processing, card_number)
        self.db_thread.result_signal.connect(self.visit_registered)
        self.db_thread.error_signal.connect(self.show_error)
        self.db_thread.start()

    def handle_card_processing(self, card_number):
        """Обработка логики регистрации визита"""
        client_id = get_client_id_by_card(card_number)
        if not client_id:
            raise Exception("Эта карта не привязана ни к одному клиенту.")

        subscription_info = get_subscription_info(client_id)
        if not subscription_info:
            raise Exception("У клиента нет активного абонемента.")

        subscription_id, tariff, valid_since, valid_until, is_valid, visit_ids = subscription_info

        # Автоматическая деактивация просроченного абонемента
        today = datetime.date.today()
        if valid_until < today and is_valid:
            deactivate_subscription(subscription_id)
            raise Exception("Абонемент просрочен и был деактивирован.")

        if not is_valid:
            raise Exception("Абонемент недействителен.")

        tariff_type = tariff.split('_')[1]
        max_visits = int(tariff.split('_')[0]) if tariff.split('_')[0].isdigit() else None

        current_hour = datetime.datetime.now().hour
        if tariff_type == "mrn" and current_hour >= 16:
            raise Exception("Абонемент клиента действует только до 16:00.")
        elif tariff_type == "evn" and current_hour < 16:
            raise Exception("Абонемент клиента действует только после 16:00.")

        last_visit_today = check_today_visits(client_id)
        if last_visit_today and max_visits and len(visit_ids) >= max_visits:
            raise Exception("Клиент уже исчерпал лимит посещений.")

        visit_id = register_visit(client_id, subscription_id)

        if max_visits and len(visit_ids) + 1 >= max_visits:
            deactivate_subscription(subscription_id)

        return f"Посещение зафиксировано. ID визита: {visit_id}"

    def visit_registered(self, message):
        QMessageBox.information(self, "Успех", message)
        self.accept()

    def show_error(self, error_message):
        QMessageBox.critical(self, "Ошибка", error_message)
        self.reject()


def load_fonts_from_dir(directory):
    families = set()
    for fi in QDir(directory).entryInfoList(["*.ttf", "*.woff", "*.woff2"]):
        _id = QFontDatabase.addApplicationFont(fi.absoluteFilePath())
        families |= set(QFontDatabase.applicationFontFamilies(_id))
    return families


# class ResizablePhoto(QLabel):
#     def __init__(self, image_path, parent=None):
#         super().__init__(parent)
#         self.image_path = image_path
#         self.setScaledContents(True)  # Включаем автоматическое масштабирование содержимого
#         self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # Позволяем растягиваться
#
#     def resizeEvent(self, event):
#         """Обрабатывает изменение размера виджета и масштабирует изображение."""
#         pixmap = QPixmap(self.image_path)
#         scaled_pixmap = pixmap.scaled(self.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
#         self.setPixmap(scaled_pixmap)
#         super().resizeEvent(event)
class FillPhoto(QLabel):
    def __init__(self, image_path="", parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            background-color: lightgray;
            border-radius: 10px;
            border: 3px solid #75A9A7;
            font-size: 20px;
            color: #555555;
        """)
        self.setPixmap(QPixmap())  # Устанавливаем пустой QPixmap по умолчанию
        if image_path:
            self.setPhoto(image_path)
        else:
            self.setText("Фото не установлено")

    def setPhoto(self, image_path):
        """
        Устанавливает фото из файла.
        :param image_path: Путь к изображению
        """
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            self.setPixmap(pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            self.setText("")  # Убираем текст, если фото загружено
            logger.info(f"Фото успешно загружено из файла: {image_path}")
        else:
            self.setText("Не удалось загрузить фото")
            self.setStyleSheet("""
                background-color: lightgray;
                border-radius: 10px;
                border: 3px solid #75A9A7;
                font-size: 20px;
                color: red;
            """)
            logger.error(f"Не удалось загрузить фото из файла: {image_path}")

    def setPhotoData(self, photo_data):
        """
        Устанавливает фото из байтовых данных.
        :param photo_data: Байтовые данные изображения
        """
        if photo_data:
            pixmap = QPixmap()
            if pixmap.loadFromData(photo_data):
                pixmap = pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.setPixmap(pixmap)
                self.setText("")  # Убираем текст, если фото загружено
                logger.info("Фото успешно загружено из байтовых данных.")
            else:
                self.setText("Не удалось загрузить фото")
                self.setStyleSheet("""
                    background-color: lightgray;
                    border-radius: 10px;
                    border: 3px solid #75A9A7;
                    font-size: 20px;
                    color: red;
                """)
                logger.error("Не удалось загрузить фото из байтовых данных.")
        else:
            self.setText("Фото не установлено")
            self.setStyleSheet("""
                background-color: lightgray;
                border-radius: 10px;
                border: 3px solid #75A9A7;
                font-size: 20px;
                color: #555555;
            """)
            logger.warning("Фото не установлено: данные отсутствуют.")

    def resizeEvent(self, event):
        """
        Обеспечивает масштабирование изображения при изменении размера виджета.
        """
        pixmap = self.pixmap()
        if pixmap and not pixmap.isNull():
            self.setPixmap(pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            logger.debug("Фото масштабировано при изменении размера виджета.")
        else:
            logger.debug("Нет фото для масштабирования при изменении размера виджета.")


class ResizablePhoto(QLabel):
    def __init__(self, image_path="", parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            background-color: lightgray;
            border-radius: 10px;
            border: 3px solid #75A9A7;
            font-size: 20px;
            color: #555555;
        """)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # Позволяем растягиваться
        self.pixmap_original = QPixmap()  # Изначально пустое изображение

        if self.image_path:
            self.setPhoto(self.image_path)
        else:
            self.setText("Фото не установлено")

    def setPhoto(self, image_path):
        """
        Устанавливает фото из файла.
        :param image_path: Путь к изображению
        """
        pixmap = QPixmap(image_path)
        if not pixmap.isNull():
            self.pixmap_original = pixmap
            self.updateScaledPhoto()
            self.setText("")  # Убираем текст, если фото загружено
            logger.info(f"Фото успешно загружено из файла: {image_path}")
        else:
            self.showError("Не удалось загрузить фото")
            logger.error(f"Не удалось загрузить фото из файла: {image_path}")

    def setPhotoData(self, photo_data):
        """
        Устанавливает фото из байтовых данных.
        :param photo_data: Байтовые данные изображения
        """
        if photo_data:
            pixmap = QPixmap()
            if pixmap.loadFromData(photo_data):
                self.pixmap_original = pixmap
                self.updateScaledPhoto()
                self.setText("")  # Убираем текст, если фото загружено
                logger.info("Фото успешно загружено из байтовых данных.")
            else:
                self.showError("Не удалось загрузить фото")
                logger.error("Не удалось загрузить фото из байтовых данных.")
        else:
            self.showError("Фото не установлено")
            logger.warning("Фото не установлено: данные отсутствуют.")

    def resizeEvent(self, event):
        """
        Обеспечивает масштабирование изображения при изменении размера виджета.
        """
        if not self.pixmap_original.isNull():
            self.updateScaledPhoto()
            logger.debug("Фото масштабировано при изменении размера виджета.")
        else:
            logger.debug("Нет фото для масштабирования при изменении размера виджета.")

    def updateScaledPhoto(self):
        """
        Масштабирует изображение в соответствии с размером виджета.
        """
        if not self.pixmap_original.isNull():
            scaled_pixmap = self.pixmap_original.scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.setPixmap(scaled_pixmap)

    def showError(self, message):
        """
        Показывает сообщение об ошибке вместо изображения.
        """
        self.setText(message)
        self.setStyleSheet("""
            background-color: lightgray;
            border-radius: 10px;
            border: 3px solid #75A9A7;
            font-size: 20px;
            color: red;
        """)


# Пример использования
class TariffCalculator:
    def __init__(self):
        # Убираем QSettings, чтобы не использовать кэширование
        self.tariffs = self.load_tariffs_from_db()

    def load_tariffs_from_db(self):
        """Загружаем тарифы из базы данных."""
        tariffs = {}
        query = "SELECT k_type, k_time, k_period_or_n FROM tariff"

        # Подключаемся к базе данных
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

        return tariffs

    def calculate_price(self, period, k_class, k_time, base_price):
        """Расчет цены с использованием выбранных опций."""
        # Формируем ключ для тарифа в зависимости от выбранных опций
        k_type = self.generate_k_type(period, k_class, k_time)

        # Используем тарифы, загруженные из базы
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
        time_map = {"<16ч": "mrn", ">16ч": "evn", "безлимит": "unlim"}

        period_key = period_map.get(period)
        class_key = class_map.get(k_class)
        time_key = time_map.get(k_time)

        if period_key and class_key and time_key:
            return f"{class_key}_{time_key}_{period_key}"
        else:
            raise ValueError("Неверные параметры для тарифа.")


# class TariffCalculator:
#     def __init__(self):
#         self.settings = QSettings("fdfdfdsdddf", "fefsdsdsddfdf")
#         self.tariffs = self.load_tariffs()
#
#     def load_tariffs(self):
#         """Загружаем тарифы из базы данных или из кэша."""
#         tariffs = self.settings.value("tariffs", None)
#         if tariffs is None:
#             return self.load_tariffs_from_db()  # Синхронная загрузка тарифов
#         else:
#             return tariffs
#
#     def load_tariffs_from_db(self):
#         """Загружаем тарифы из базы данных."""
#         tariffs = {}
#         query = "SELECT k_type, k_time, k_period_or_n FROM tariff"
#
#         # Подключаемся к базе данных здесь
#         connection = connect_to_db()
#         cursor = connection.cursor()
#         cursor.execute(query)
#         rows = cursor.fetchall()
#
#         for row in rows:
#             k_type, k_time, k_period_or_n = row
#             tariffs[k_type] = {'k_time': k_time, 'k_period_or_n': k_period_or_n}
#
#         # Закрываем соединение с БД
#         cursor.close()
#         connection.close()
#
#         # Кэшируем тарифы в QSettings
#         self.settings.setValue("tariffs", tariffs)
#         print(444444,tariffs)
#
#         return tariffs
#
#     def calculate_price(self, period, k_class, k_time, base_price):
#         """Расчет цены с использованием выбранных опций."""
#         # Формируем ключ для тарифа в зависимости от выбранных опций
#         k_type = self.generate_k_type(period, k_class, k_time)
#
#         tariff = self.tariffs.get(k_type)
#         if tariff:
#             price = base_price * tariff['k_time'] * tariff['k_period_or_n']
#             return price
#         else:
#             raise ValueError(f"Тариф {k_type} не найден")
#
#     def generate_k_type(self, period, k_class, k_time):
#         """Генерируем ключ для тарифа на основе выбранных опций."""
#         period_map = {"Месяц": "mnth", "Полгода": "hyr", "Год": "yr"}
#         class_map = {"8": "8", "12": "12", "безлимит": "unlim"}
#         time_map = {"<16ч": "mrn", ">16ч": "evn", "безлимит": "unlim"}
#
#         period_key = period_map.get(period)
#         class_key = class_map.get(k_class)
#         time_key = time_map.get(k_time)
#
#         if period_key and class_key and time_key:
#             return f"{class_key}_{time_key}_{period_key}"
#         else:
#             raise ValueError("Неверные параметры для тарифа.")
#

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


class ScanCardThread(QThread):
    """Поток для сканирования карты, чтобы не блокировать UI."""
    card_scanned = pyqtSignal(str)
    scanner_not_found = pyqtSignal()

    def run(self):
        baudrate = 115200
        card_number = None

        # Получаем список всех доступных портов
        available_ports = serial.tools.list_ports.comports()

        if not available_ports:
            self.scanner_not_found.emit()
            return

        for port_info in available_ports:
            port = port_info.device  # COM-порт (например, COM3 или /dev/ttyUSB0)
            print(f"Попытка подключения к {port}")

            try:
                serial_port = serial.Serial(port, baudrate, timeout=1)

                while True:
                    if serial_port.in_waiting > 0:
                        data = serial_port.read(serial_port.in_waiting).decode('utf-8')
                        print(f"Полученные данные с {port}: {data}")
                        card_number = data.strip()
                        break
                    time.sleep(0.1)

                if card_number:
                    self.card_scanned.emit(card_number)
                    break  # Выход после успешного сканирования

            except serial.SerialException as e:
                print(f"Ошибка подключения к {port}: {e}")

            finally:
                if 'serial_port' in locals() and serial_port.is_open:
                    serial_port.close()

        if not card_number:
            self.scanner_not_found.emit()


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
