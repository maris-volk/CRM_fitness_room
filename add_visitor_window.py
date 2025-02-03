import os
import re
import time

import bcrypt
import serial
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QLineEdit, QGridLayout, QDialog, QMessageBox, QFileDialog, QTextEdit, \
    QSizePolicy, QWidget, QPushButton
from PyQt5.QtCore import Qt, QRectF, QPoint, pyqtSignal, QByteArray, QBuffer, QTimer, QThread
from PyQt5.QtGui import QPainter, QColor, QPen, QPixmap

from database import check_phone_in_database, \
    add_subscription_to_existing_user, add_user_to_db, execute_query, check_trainer_phone_in_database, \
    check_admin_phone_in_database, check_admin_username_in_database, check_card_in_database, add_card_to_user
from hover_button import HoverButton
from subscription import SubscriptionWidget
from utils import WorkerThread, logger, resources_path, center, scan_card, ScanCardThread

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QGridLayout, QLabel, QLineEdit, QMessageBox, QSpacerItem, QSizePolicy
from PyQt5.QtCore import Qt, pyqtSignal
from hover_button import HoverButton  # Убедитесь, что у вас есть этот класс для кнопки
import re




class ScanCardThread(QThread):
    """Поток для сканирования карты."""
    card_scanned = pyqtSignal(str)
    scanner_connected = pyqtSignal()
    scanner_not_found = pyqtSignal()

    def run(self):
        baudrate = 115200
        card_number = None
        scanner_found = False

        while not scanner_found:
            available_ports = serial.tools.list_ports.comports()
            if not available_ports:
                self.scanner_not_found.emit()
                time.sleep(2)  # Проверяем снова через 2 секунды
                continue

            self.scanner_connected.emit()
            scanner_found = True

            for port_info in available_ports:
                port = port_info.device  # COM-порт (например, COM3 или /dev/ttyUSB0)
                print(f"Попытка подключения к {port}")

                try:
                    serial_port = serial.Serial(port, baudrate, timeout=1)

                    while True:
                        if serial_port.in_waiting > 0:
                            data = serial_port.read(serial_port.in_waiting).decode('utf-8').strip()
                            print(f"Полученные данные с {port}: {data}")
                            if data:
                                card_number = data
                                self.card_scanned.emit(card_number)
                                return  # Завершаем поток после успешного сканирования

                        time.sleep(0.1)

                except serial.SerialException as e:
                    print(f"Ошибка подключения к {port}: {e}")

                finally:
                    if 'serial_port' in locals() and serial_port.is_open:
                        serial_port.close()

class AddCardDialog(QDialog):
    def __init__(self, client_id, parent=None, scan_callback=None):
        super().__init__()
        self.setWindowTitle("Сканирование карты")
        self.setGeometry(300, 300, 400, 200)
        self.parent = parent
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.client_id = client_id

        self.client_id = client_id  # Сохраняем client_id
        self.scanner_connected = False
        self.scan_callback = scan_callback  # Сохраняем callback

        # Layout
        self.layout = QVBoxLayout(self)

        # Status label
        self.status_label = QLabel("Ожидание подключения сканера...", self)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.status_label)

        # Cancel button
        self.cancel_button = QPushButton("Отмена", self)
        self.cancel_button.clicked.connect(self.cancel_move)
        self.cancel_button.setStyleSheet("background-color: #d9534f; color: white; font-size: 14px;")
        self.layout.addWidget(self.cancel_button)

        # Spacer for alignment
        spacer = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
        self.layout.addItem(spacer)

        self.setLayout(self.layout)

        # Запуск потока для ожидания сканера и сканирования карты
        self.scan_thread = ScanCardThread()
        self.scan_thread.scanner_connected.connect(self.on_scanner_connected)
        self.scan_thread.scanner_not_found.connect(self.on_scanner_not_found)
        self.scan_thread.card_scanned.connect(self.on_card_scanned)
        self.scan_thread.start()


    def cancel_move(self):

        self.reject()
        self.parent.close()

    def on_scanner_connected(self):
        """Обработчик подключения сканера."""
        if not self.scanner_connected:
            self.status_label.setText("Сканер подключен. Ожидание сканирования карты...")
            self.scanner_connected = True

    def on_scanner_not_found(self):
        """Обработчик отсутствия сканера."""
        if not self.scanner_connected:
            self.status_label.setText("Сканер не найден. Подключите устройство.")

    def on_card_scanned(self, card_number):
        """Обработчик успешного сканирования карты."""
        self.status_label.setText(f"Карта отсканирована: {card_number}")
        if self.scan_callback:
            self.scan_callback(self.client_id, card_number)  # Передаем client_id и номер карты
            add_card_to_user(self.client_id, card_number)  # Привязываем карту к клиенту
        self.accept()

    def show_dialog(self):
        """Показывает диалоговое окно и ожидает завершения"""
        self.exec_()


    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(0, 0, self.width(), self.height())

        borderPen = QPen(QColor(117, 169, 167))
        borderPen.setWidth(5)
        painter.setPen(borderPen)

        backgroundBrush = QColor(255, 255, 255)
        painter.setBrush(backgroundBrush)

        painter.drawRoundedRect(rect, 18, 18)
        painter.end()

    def mousePressEvent(self, event):
        self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPos() - self.oldPos)
        self.move(self.pos() + delta)
        self.oldPos = event.globalPos()


class AddVisitorWindow(QDialog):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.subscription_data = None
        self.subscription_button_state = False
        self.setWindowTitle("Добавление нового посетителя")
        self.setGeometry(300, 300, 426, 426)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("""
            QDialog {}
            QLineEdit {
                font-family: 'Unbounded';
                font-size: 22.5px;
                padding: 15px 20.4px 15px 15px;
                border-radius: 18px;
                border: solid #75A9A7;
                border-width: 0px 0px 2.7px 2.7px;
                background-color: transparent;
                margin-left: 65px;
                margin-right: 65px;
                margin-top: 10px;
                margin-bottom: 10px;
            }
            QLabel {
                font-family: 'Unbounded';
                font-size: 22.5px;
                font-weight: 500;
                text-align: center;
                background-color: transparent;
                border: 0px;
            }
        """)
        self.initUI()
        self.oldPos = self.pos()
        self.radius = 18
        self.borderWidth = 5
        self.setWindowModality(Qt.ApplicationModal)

    def initUI(self):
        layout = QVBoxLayout(self)
        grid_layout = QGridLayout()

        # Title (centered)
        title_label = QLabel("Новый посетитель", self)
        title_label.setObjectName("titleLabel")
        grid_layout.addWidget(title_label, 0, 1)  # Center title

        # Close button (top-right)
        self.close_button = HoverButton("X", 30, 30, 35, '#8F2D31', True, '#8F2D31', 'red', 5, 'red')
        self.close_button.setObjectName("closeButton")
        self.close_button.clicked.connect(self.close)
        grid_layout.addWidget(self.close_button, 0, 2)

        # Set column stretch
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 3)
        grid_layout.setColumnStretch(2, 1)
        layout.addLayout(grid_layout)

        phone_input = QLineEdit(self)
        phone_input.setPlaceholderText("Номер телефона")
        layout.addWidget(phone_input)

        last_name_input = QLineEdit(self)
        last_name_input.setPlaceholderText("Фамилия")
        layout.addWidget(last_name_input)

        first_name_input = QLineEdit(self)
        first_name_input.setPlaceholderText("Имя")
        layout.addWidget(first_name_input)

        patronymic_input = QLineEdit(self)
        patronymic_input.setPlaceholderText("Отчество")
        layout.addWidget(patronymic_input)

        button_grid_layout = QGridLayout()

        # Labels
        trainer_label = QLabel("Тренер", self)
        trainer_label.setAlignment(Qt.AlignCenter)
        button_grid_layout.addWidget(trainer_label, 0, 0, alignment=Qt.AlignCenter)

        subscription_label = QLabel("Абонемент", self)
        subscription_label.setAlignment(Qt.AlignCenter)
        button_grid_layout.addWidget(subscription_label, 0, 1, alignment=Qt.AlignCenter)

        trainer_button = HoverButton("+", 30, 30, 40, '#75A9A7', True, '', '', 5, '#5DEBE6')
        button_grid_layout.addWidget(trainer_button, 1, 0, alignment=Qt.AlignCenter)

        self.subscription_button = HoverButton("+", 30, 30, 40, '#75A9A7', True, '', '', 5, '#5DEBE6')
        self.subscription_button.clicked.connect(self.show_add_subscription)
        trainer_button.clicked.connect(lambda: self.validate_and_open_trainer_schedule(
            first_name_input, last_name_input, patronymic_input, phone_input
        ))

        button_grid_layout.addWidget(self.subscription_button, 1, 1, alignment=Qt.AlignCenter)

        layout.addLayout(button_grid_layout)

        layout.addStretch(1)

        confirm_button = HoverButton("Подтвердить", 190, 35, 15, '#5DEBE6', False, '#5DEBE6', '', 8)
        confirm_button.setContentsMargins(10, 30, 10, 30)
        confirm_button.setFixedSize(180, 35)  # Fixed size for alignment
        confirm_button.clicked.connect(lambda: self.validate_and_add_user(
            first_name_input, last_name_input, patronymic_input, phone_input))
        layout.addWidget(confirm_button, alignment=Qt.AlignCenter)

        layout.addStretch(1)

        self.setLayout(layout)

    def show_add_subscription(self):
        if not hasattr(self, 'add_visitor_window') or not self.add_visitor_window.isVisible():
            self.add_visitor_window = SubscriptionWidget()
            self.add_visitor_window.show()
            self.add_visitor_window.raise_()
            self.add_visitor_window.confirmed.connect(self.on_subscription_confirmed)

    def on_subscription_confirmed(self, subscription_data):
        # получение данных из окна абонемента
        self.subscription_data = subscription_data
        print(self.subscription_data, 123)
        if self.subscription_data is None:
            self.subscription_button_state = False
        else:
            self.subscription_button_state = True
        if self.subscription_button_state:
            self.subscription_button.set_font_color("#50c878")
            self.subscription_button.set_border_color("#50c878")
            self.subscription_button.set_hover_border_color("#55ff55")
            self.subscription_button.set_hover_text_color("#55ff55")
        else:
            self.subscription_button.set_font_color('#75A9A7')
            self.subscription_button.set_border_color('#75A9A7')
            self.subscription_button.set_hover_border_color('#5DEBE6')
            self.subscription_button.set_hover_text_color('#5DEBE6')


    def showEvent(self, event):
        super().showEvent(event)

        title_label = self.findChild(QLabel)
        title_width = title_label.width()
        title_pos = title_label.pos()



    def validate_and_add_user(self, first_name_input, last_name_input, patronymic_input, phone_input):
        first_name = first_name_input.text().strip()
        last_name = last_name_input.text().strip()
        patronymic = patronymic_input.text().strip()
        phone_number = phone_input.text().strip()

        valid = True

        if not first_name:
            first_name_input.setStyleSheet("border-color:red;")
            valid = False
        else:
            first_name_input.setStyleSheet("border-color:#75A9A7;")

        if not last_name:
            last_name_input.setStyleSheet("border-color:red;")
            valid = False
        else:
            last_name_input.setStyleSheet("border-color:#75A9A7;")

        if not re.match(r"^\+\d{10,15}$", phone_number):
            phone_input.setStyleSheet("border-color:red;")
            valid = False


        else:
            phone_input.setStyleSheet("border-color:#75A9A7;")
            if not valid:
                return

            self.add_user_thread = WorkerThread(
                self.handle_user_and_subscription,
                first_name,
                last_name,
                patronymic,
                phone_number,
                self.subscription_data
            )
            self.add_user_thread.result_signal.connect(self.on_user_added)
            self.add_user_thread.error_signal.connect(self.on_error)
            self.add_user_thread.start()

    def validate_and_open_trainer_schedule(self, first_name_input, last_name_input, patronymic_input, phone_input):
        id = None
        first_name = first_name_input.text().strip()
        last_name = last_name_input.text().strip()
        patronymic = patronymic_input.text().strip()
        phone_number = phone_input.text().strip()

        valid = True

        if not first_name:
            first_name_input.setStyleSheet("border-color:red;")
            valid = False
        else:
            first_name_input.setStyleSheet("border-color:#75A9A7;")

        if not last_name:
            last_name_input.setStyleSheet("border-color:red;")
            valid = False
        else:
            last_name_input.setStyleSheet("border-color:#75A9A7;")

        if not re.match(r"^\+\d{10,15}$", phone_number):
            phone_input.setStyleSheet("border-color:red;")
            valid = False

        if not self.subscription_data:
            valid = False
        else:
            phone_input.setStyleSheet("border-color:#75A9A7;")
            if not valid:
                return

            self.add_user_thread = WorkerThread(
                self.handle_user_and_subscription_for_add_trainer,
                first_name,
                last_name,
                patronymic,
                phone_number,
                self.subscription_data
            )
            self.add_user_thread.result_signal.connect(self.on_trainer_added)
            self.add_user_thread.error_signal.connect(self.on_error)
            self.add_user_thread.start()


    def handle_user_and_subscription(self, first_name, last_name, patronymic, phone_number, subscription_data):
        """
        Обрабатывает логику добавления пользователя и абонемента.
        """
        try:
            # проверка наличия пользователя с данным номером телефона
            client_id = check_phone_in_database(phone_number)
            if client_id:
                return "Клиент с таким номером телефона уже существует."

            # добавление нового пользователя
            client_id = add_user_to_db(first_name, last_name, patronymic, phone_number)
            self.client_id = client_id

            if not client_id:
                raise Exception("Ошибка при добавлении нового пользователя.")

            if subscription_data:
                # добавление абонемента
                subscription_id = add_subscription_to_existing_user(client_id, subscription_data)
                if not subscription_id:
                    raise Exception("Ошибка при добавлении абонемента.")
                return
            else:
                return
        except Exception as e:
            logger.error(f"Ошибка при добавлении пользователя/абонемента: {e}")
            raise e

    def handle_user_and_subscription_for_add_trainer(self, first_name, last_name, patronymic, phone_number, subscription_data):
        """
        обработка логики добавления пользователя и абонемента.
        """
        try:
            # проверка наличия пользователя с данным номером телефона
            client_id = check_phone_in_database(phone_number)
            if client_id:
                return {
                    "status": "error",
                    "message": "Клиент с таким номером телефона уже существует."
                }

            # добавление нового пользователя
            client_id = add_user_to_db(first_name, last_name, patronymic, phone_number)

            if not client_id:
                return {
                    "status": "error",
                    "message": "Ошибка при добавлении нового пользователя."
                }

            if subscription_data:
                # добавление абонемента
                subscription_id = add_subscription_to_existing_user(client_id, subscription_data)
                if not subscription_id:
                    return {
                        "status": "error",
                        "message": "Ошибка при добавлении абонемента."
                    }

                return {
                    "status": "success",
                    "message": "Клиент успешно добавлен с абонементом.",
                    "client_data": {
                        "client_id": client_id,
                        "first_name": first_name,
                        "last_name": last_name,
                        "patronymic": patronymic,
                        "phone_number": phone_number,
                        "subscription_data": subscription_data
                    }
                }
            else:
                return {
                    "status": "success",
                    "message": "Клиент успешно добавлен без абонемента.",
                    "client_data": {
                        "client_id": client_id,
                        "first_name": first_name,
                        "last_name": last_name,
                        "patronymic": patronymic,
                        "phone_number": phone_number,
                        "subscription_data": None
                    }
                }
        except Exception as e:
            logger.error(f"Ошибка при добавлении пользователя/абонемента: {e}")
            return {
                "status": "error",
                "message": str(e)
            }

    def on_user_added(self, message):
        """Обработка завершения добавления пользователя"""


        self.show_add_card_dialog(self.client_id)
        # Получаем client_id после успешного добавления




    def on_trainer_added(self, result):
        """
        обработка результата добавления нового пользователя с тренером.
        """
        # проверка статуса результата
        if result.get("status") == "error":
            QMessageBox.critical(self, "Ошибка", result.get("message", "Произошла неизвестная ошибка."))
            return

        # получение данных клиента
        client_data = result.get("client_data")
        if not client_data:
            QMessageBox.critical(self, "Ошибка", "Не удалось получить данные о клиенте.")
            return

        # передача данных в главное окно
        self.main_window.selected_client = {
            "cliend_id": client_data["client_id"],
            "first_name": client_data["first_name"],
            "last_name": client_data["last_name"],
            "patronymic": client_data["patronymic"],
            "phone_number": client_data["phone_number"]
        }
        self.main_window.subscription_data = client_data["subscription_data"]
        self.client_id = client_data["client_id"]
        self.show_add_card_dialog(client_data["client_id"])

        # переключение на страницу расписания
        self.main_window.from_add_client = True
        self.main_window.update_days(self.main_window.current_week, self.main_window.selected_trainer_id)
        self.main_window.switch_to_page(self.main_window.schedule_page)
        self.close()

    def show_add_card_dialog(self,id):
        """Диалоговое окно для сканирования карты клиента"""
        self.add_card_dialog = AddCardDialog(client_id=id, scan_callback=self.scan_card_for_client,parent=self)
        self.add_card_dialog.show_dialog(

        )

    def scan_card_for_client(self, client_id, card_number):
        """Обрабатываем сканирование карты клиента"""
        print(f"Карта {card_number} привязана к клиенту с ID {client_id}")
        self.handle_scan_result(card_number)

    def handle_scan_result(self, card_number):
        """Обработка результата сканирования карты"""
        if check_card_in_database(card_number):
            QMessageBox.warning(self, "Ошибка", "Эта карта уже зарегистрирована у другого пользователя.")
        else:
            add_card_to_user(self.client_id, card_number)
            QMessageBox.information(self, "Успех", f"Карта {card_number} успешно добавлена.")
            self.close()

    def on_error(self, error_message):
        """
        Обработка ошибок.
        """
        QMessageBox.critical(self, "Ошибка", error_message)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(0, 0, self.width(), self.height())

        borderPen = QPen(QColor(117, 169, 167))
        borderPen.setWidth(self.borderWidth)
        painter.setPen(borderPen)

        backgroundBrush = QColor(255, 255, 255)
        painter.setBrush(backgroundBrush)

        if self.radius > 0:
            painter.drawRoundedRect(rect, self.radius, self.radius)
        else:
            painter.drawRect(rect)

        painter.end()


    def mousePressEvent(self, event):
        self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPos() - self.oldPos)
        self.move(self.pos() + delta)
        self.oldPos = event.globalPos()


# class FillPhotoClicked(QLabel):
#     """Виджет для фото с возможностью выбора при клике и автоматическим масштабированием"""
#
#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.setAlignment(Qt.AlignCenter)
#         self.setStyleSheet("""
#             background-color: white;
#             border-radius: 10px;
#             border: 3px solid #75A9A7;
#             font-size: 14px;
#             color: #555555;
#         """)
#         self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # Позволяет растягиваться
#         self.setFixedSize(120, 120)  # Стандартный размер
#         self.setText("Нажмите\nдля\nзагрузки")
#         self.photo_data = None
#         self.pixmap_original = QPixmap()  # Оригинальное изображение
#
#     def mousePressEvent(self, event):
#         """При клике открывает выбор файла"""
#         self.upload_photo()
#
#     def upload_photo(self):
#         """Открывает диалог выбора фото и загружает его в виджет"""
#         file_path, _ = QFileDialog.getOpenFileName(self, "Выбрать изображение", "", "Images (*.png *.jpg *.jpeg)")
#         if file_path:
#             with open(file_path, "rb") as file:
#                 self.photo_data = file.read()
#             self.setPhoto(file_path)
#
#     def setPhoto(self, image_path):
#         """Устанавливает фото из файла"""
#         pixmap = QPixmap(image_path)
#         if not pixmap.isNull():
#             self.pixmap_original = pixmap
#             self.updateScaledPhoto(fill=True)  # Масштабирование с заполнением
#             self.setText("")  # Убираем текст
#             logger.info(f"Фото загружено: {image_path}")
#         else:
#             self.showError("Ошибка\nзагрузки")
#             logger.error(f"Ошибка загрузки фото: {image_path}")
#
#     def setPhotoData(self, photo_data):
#         """Устанавливает фото из байтовых данных"""
#         if photo_data:
#             pixmap = QPixmap()
#             if pixmap.loadFromData(photo_data):
#                 self.pixmap_original = pixmap
#                 self.updateScaledPhoto(fill=True)
#                 self.setText("")  # Убираем текст
#                 logger.info("Фото загружено из байтовых данных.")
#             else:
#                 self.showError("Ошибка\nзагрузки")
#                 logger.error("Ошибка загрузки фото из байтовых данных.")
#         else:
#             self.showError("Нажмите\nдля\nзагрузки")
#             logger.warning("Фото не установлено: данные отсутствуют.")
#
#     def resizeEvent(self, event):
#         """Масштабирует изображение при изменении размера виджета"""
#         if not self.pixmap_original.isNull():
#             self.updateScaledPhoto(fill=True)
#             logger.debug("Фото масштабировано при изменении размера виджета.")
#         else:
#             logger.debug("Нет фото для масштабирования при изменении размера виджета.")
#
#     def updateScaledPhoto(self, fill=False):
#         """Масштабирует изображение с заполнением всего пространства"""
#         if not self.pixmap_original.isNull():
#             if fill:
#                 # Заполняем весь виджет без сохранения пропорций
#                 scaled_pixmap = self.pixmap_original.scaled(
#                     self.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation
#                 )
#             else:
#                 # Сохраняем пропорции, но увеличиваем до минимального размера виджета
#                 scaled_pixmap = self.pixmap_original.scaled(
#                     self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
#                 )
#             self.setPixmap(scaled_pixmap)
#
#     def showError(self, message):
#         """Показывает сообщение об ошибке вместо изображения"""
#         self.setPixmap(QPixmap())
#         self.setText(message)
#         self.setStyleSheet("""
#             background-color: white;
#             border-radius: 10px;
#             border: 3px solid #75A9A7;
#             font-size: 14px;
#             color: red;
#         """)
#
#     def clearPhoto(self):
#         """Удаляет фото и сбрасывает состояние"""
#         self.pixmap_original = QPixmap()
#         self.setPixmap(QPixmap())
#         self.setText("Нажмите\nдля\nзагрузки")
#         self.photo_data = None


class FillPhotoClicked(QLabel):
    """Виджет для фото с возможностью выбора при клике"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("""
            background-color: white;
            border-radius: 10px;
            border: 3px solid #75A9A7;
            font-size: 14px;
            color: #555555;
        """)
        self.setFixedSize(120, 120)  # Высота равна двум полям ввода (Фамилия + Имя)
        self.setText("Нажмите\nдля\nзагрузки")
        self.photo_data = None

    def mousePressEvent(self, event):
        """При клике открывает выбор файла"""
        self.upload_photo()

    def upload_photo(self):
        """Открывает диалог выбора фото и загружает его в виджет"""
        file_path, _ = QFileDialog.getOpenFileName(self, "Выбрать изображение", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            with open(file_path, "rb") as file:
                self.photo_data = file.read()
            self.setPhoto(file_path)

    def convert_memoryview_to_bytes(memoryview_obj):
        """Преобразует memoryview в bytes."""
        return bytes(memoryview_obj)

    def setPhoto(self, image_data):
        """
        Загружает изображение из bytes или пути.
        """
        pixmap = QPixmap()

        if isinstance(image_data, memoryview):  # Проверяем, если это memoryview
            image_data = self.convert_memoryview_to_bytes(image_data)  # Преобразуем в bytes

        if isinstance(image_data, bytes):  # Если изображение хранится в БД как BLOB
            if not pixmap.loadFromData(QByteArray(image_data)):
                logger.error("Ошибка при загрузке фото: Неизвестный формат изображения")
                self.setPixmap(QPixmap(resources_path("group.png")))  # Ставим дефолтное изображение
                return
            self.photo_data = QByteArray(image_data)  # Сохраняем байтовые данные изображения
        elif isinstance(image_data, QPixmap):  # Если это QPixmap, конвертируем в байты
            image_data = image_data.toImage()
            byte_array = QByteArray()
            buffer = QBuffer(byte_array)
            image_data.save(buffer, "PNG")  # Сохраняем изображение как PNG в массив байтов
            pixmap.loadFromData(byte_array)  # Загружаем обратно как QPixmap
            self.photo_data = byte_array
        elif isinstance(image_data, str) and os.path.exists(image_data):  # Если путь к файлу
            pixmap = QPixmap(image_data)
        else:
            pixmap = QPixmap(resources_path("group.png"))  # Ставим дефолтное изображение

        self.setPixmap(pixmap.scaled(self.width(), self.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def clearPhoto(self):
        """Удаляет фото"""
        self.setPixmap(QPixmap())
        self.setText("Нажмите\nдля\nзагрузки")
        self.photo_data = None


from PyQt5.QtCore import pyqtSignal, QByteArray, QBuffer, QPoint, Qt
from PyQt5.QtGui import QPixmap, QPainter, QColor, QPen
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QGridLayout, QLabel, QLineEdit, QTextEdit, QMessageBox, QScrollArea, QWidget, QSizePolicy, QSpacerItem, QApplication
from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QImage
import datetime
import calendar
import re
import bcrypt
import logging
import sip

logger = logging.getLogger(__name__)

class AddTrainerWindow(QDialog):
    trainer_added = pyqtSignal(dict)
    trainer_updated = pyqtSignal(dict)

    def __init__(self, trainer_data=None):
        super().__init__()
        self.setWindowTitle("Редактирование тренера" if trainer_data else "Добавление тренера")
        self.header_text = "Редактирование тренера" if trainer_data else "Новый тренер"
        self.setGeometry(300, 300, 500, 500)
        self.center()
        self.photo_data = None if trainer_data is None else trainer_data.get("image")
        self.trainer_id = trainer_data.get("id") if trainer_data else None

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowModality(Qt.ApplicationModal)
        self.oldPos = self.pos()
        self.radius = 18
        self.borderWidth = 5

        self.setStyleSheet("""
            QDialog {}
            QLineEdit {
                font-family: 'Unbounded';
                font-size: 22.5px;
                padding: 15px 20.4px 15px 15px;
                border-radius: 18px;
                border: solid #75A9A7;
                border-width: 0px 0px 2.7px 2.7px;
                background-color: transparent;
                margin-left: 20px;
                margin-right: 20px;
                margin-top: 10px;
                margin-bottom: 10px;
            }
            QTextEdit {
                font-family: 'Unbounded';
                font-size: 22.5px;
                border-radius: 18px;
                border: solid #75A9A7;
                border-width: 0px 0px 2.7px 2.7px;
                background-color: transparent;
                margin-left: 20px;
                margin-right: 20px;
                margin-top: 10px;
                margin-bottom: 10px;
            }
            QLabel {
                font-family: 'Unbounded';
                font-size: 22.5px;
                font-weight: 500;
                text-align: center;
                background-color: transparent;
                border: 0px;
            }
        """)

        self.initUI()
        if trainer_data:
            self.fill_trainer_data(trainer_data)

    def center(self):
        frame_geometry = self.frameGeometry()
        center_point = QApplication.desktop().availableGeometry().center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())

    def fill_trainer_data(self, trainer_data):
        self.surname_input.setText(trainer_data["surname"])
        self.name_input.setText(trainer_data["name"])
        self.patronymic_input.setText(trainer_data["patronymic"])
        self.phone_input.setText(trainer_data["phone"])
        self.temp_phone_number = self.phone_input.text()
        self.description_input.setText(trainer_data["description"])

        if isinstance(trainer_data["image"], QPixmap):
            byte_array = QByteArray()
            buffer = QBuffer(byte_array)
            trainer_data["image"].toImage().save(buffer, "PNG")
            self.photo_data = byte_array.data()
            self.photo_label.setPhoto(self.photo_data)
        elif isinstance(trainer_data["image"], bytes):
            self.photo_data = trainer_data["image"]
            self.photo_label.setPhoto(self.photo_data)
        else:
            self.photo_label.clearPhoto()

    def initUI(self):
        layout = QVBoxLayout(self)
        grid_layout = QGridLayout()

        title_label = QLabel(self.header_text, self)
        grid_layout.addWidget(title_label, 0, 1, alignment=Qt.AlignCenter)

        close_button = HoverButton("X", 30, 30, 35, '#8F2D31', True, '#8F2D31', 'red', 5, 'red')
        close_button.clicked.connect(self.close)
        grid_layout.addWidget(close_button, 0, 2, alignment=Qt.AlignRight)

        layout.addLayout(grid_layout)

        self.surname_input = QLineEdit(self)
        self.surname_input.setPlaceholderText("Фамилия")

        self.name_input = QLineEdit(self)
        self.name_input.setPlaceholderText("Имя")

        self.patronymic_input = QLineEdit(self)
        self.patronymic_input.setPlaceholderText("Отчество")

        self.phone_input = QLineEdit(self)
        self.phone_input.setPlaceholderText("Номер телефона")

        self.description_input = QTextEdit(self)
        self.description_input.setPlaceholderText("Информация о тренере (необязательно)")
        self.description_input.setFixedHeight(70)

        form_layout = QGridLayout()
        form_layout.setColumnStretch(0, 2)
        form_layout.setColumnStretch(1, 1)

        form_layout.addWidget(self.surname_input, 0, 0)
        form_layout.addWidget(self.name_input, 1, 0)

        self.photo_label = FillPhotoClicked()
        form_layout.addWidget(self.photo_label, 0, 1, 2, 1, alignment=Qt.AlignCenter)

        form_layout.addWidget(self.patronymic_input, 2, 0)

        self.clear_photo_button = HoverButton("Удалить фото", 170, 35, 15, '#FF6F61', True, '#8F2D31', 'red', 8, 'red')
        self.clear_photo_button.clicked.connect(self.photo_label.clearPhoto)
        form_layout.addWidget(self.clear_photo_button, 2, 1, alignment=Qt.AlignCenter)

        form_layout.addWidget(self.phone_input, 3, 0, 1, 2)
        form_layout.addWidget(self.description_input, 4, 0, 1, 2)

        layout.addLayout(form_layout)

        confirm_button = HoverButton("Подтвердить", 190, 35, 15, '#5DEBE6', False, '#5DEBE6', '', 8)
        confirm_button.clicked.connect(self.validate_and_save)
        layout.addWidget(confirm_button, alignment=Qt.AlignCenter)

        self.setLayout(layout)

    def validate_and_save(self):
        surname = self.surname_input.text().strip()
        name = self.name_input.text().strip()
        patronymic = self.patronymic_input.text().strip()
        phone_number = self.phone_input.text().strip()
        description = self.description_input.toPlainText().strip()

        valid = True

        if not surname:
            self.surname_input.setStyleSheet("border-color:red;")
            valid = False
        else:
            self.surname_input.setStyleSheet("border-color:#75A9A7;")

        if not name:
            self.name_input.setStyleSheet("border-color:red;")
            valid = False
        else:
            self.name_input.setStyleSheet("border-color:#75A9A7;")
        if self.trainer_id:
            has_changed_ph = self.temp_phone_number != phone_number
            if has_changed_ph and check_trainer_phone_in_database(phone_number):
                self.phone_input.setStyleSheet("border-color:red;")
                QMessageBox.warning(self, "Ошибка", "Администратор с таким номером уже существует!")
                valid = False
        if not re.match(r"^\+\d{10,15}$", phone_number):
            self.phone_input.setStyleSheet("border-color:red;")
            valid = False
        else:
            if (not self.trainer_id and check_trainer_phone_in_database(phone_number)):
                self.phone_input.setStyleSheet("border-color:red;")
                QMessageBox.warning(self, "Ошибка", "Администратор с таким номером уже существует!")
                valid = False
            self.phone_input.setStyleSheet("border-color:#75A9A7;")

        if not valid:
            return


        if self.trainer_id:
            query = """
                UPDATE trainer
                SET surname=%s, first_name=%s, patronymic=%s, phone_number=%s, description=%s, photo=%s
                WHERE trainer_id=%s
                RETURNING trainer_id;
            """
            result = execute_query(query, (
                surname, name, patronymic, phone_number, description, self.photo_label.photo_data, self.trainer_id),
                                   fetch=True, fetch_one=True)

            if result:
                self.trainer_updated.emit({
                    "id": self.trainer_id,
                    "name": name,
                    "surname": surname,
                    "patronymic": patronymic,
                    "phone": phone_number,
                    "description": description,
                    "image": self.photo_label.photo_data
                })
            else:
                logger.error(f"❌ Ошибка: тренер {self.trainer_id} не найден или не обновился!")
        else:
            query = """
                INSERT INTO trainer (surname, first_name, patronymic, phone_number, description, photo)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING trainer_id;
            """
            result = execute_query(query,
                                   (surname, name, patronymic, phone_number, description, self.photo_label.photo_data))
            if result:
                trainer_id = result[0][0]
                self.trainer_added.emit({
                    "id": trainer_id,
                    "name": name,
                    "surname": surname,
                    "patronymic": patronymic,
                    "phone": phone_number,
                    "description": description,
                    "image": self.photo_label.photo_data
                })

        QMessageBox.information(self, "Успех", "Тренер успешно сохранён.")
        self.accept()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(0, 0, self.width(), self.height())

        borderPen = QPen(QColor(117, 169, 167))
        borderPen.setWidth(self.borderWidth)
        painter.setPen(borderPen)

        backgroundBrush = QColor(255, 255, 255)
        painter.setBrush(backgroundBrush)

        if self.radius > 0:
            painter.drawRoundedRect(rect, self.radius, self.radius)
        else:
            painter.drawRect(rect)

        painter.end()

    def mousePressEvent(self, event):
        self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPos() - self.oldPos)
        self.move(self.pos() + delta)
        self.oldPos = event.globalPos()


class AddAdministratorWindow(QDialog):
    admin_added = pyqtSignal(dict)
    admin_updated = pyqtSignal(dict)

    def __init__(self, admin_data=None):
        super().__init__()
        self.setWindowTitle("Редактирование администратора" if admin_data else "Добавление администратора")
        self.header_text = "Редактирование администратора" if admin_data else "Новый администратор"
        self.setGeometry(300, 300, 500, 500)
        self.center()

        self.photo_data = None
        self.admin_id = admin_data.get("id") if admin_data else None

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowModality(Qt.ApplicationModal)
        self.oldPos = self.pos()
        self.radius = 18
        self.borderWidth = 5

        self.setStyleSheet("""
            QDialog {}
            QLineEdit {
                font-family: 'Unbounded';
                font-size: 22.5px;
                padding: 15px 20.4px 15px 15px;
                border-radius: 18px;
                border: solid #75A9A7;
                border-width: 0px 0px 2.7px 2.7px;
                background-color: transparent;
                margin-left: 20px;
                margin-right: 20px;
                margin-top: 10px;
                margin-bottom: 10px;
            }
            QTextEdit {
                font-family: 'Unbounded';
                font-size: 22.5px;
                padding: 5px 20.4px 5px 15px;
                border-radius: 18px;
                border: solid #75A9A7;
                border-width: 0px 0px 2.7px 2.7px;
                background-color: transparent;
                margin-left: 20px;
                margin-right: 20px;
                margin-top: 10px;
                margin-bottom: 10px;
            }
            QLabel {
                font-family: 'Unbounded';
                font-size: 22.5px;
                font-weight: 500;
                text-align: center;
                background-color: transparent;
                border: 0px;
            }
        """)

        self.initUI()
        self.username_input_temp = None
        self.temp_phone_number = None

        if admin_data:
            self.user_id = admin_data["user_id"]
            self.fill_admin_data(admin_data)

    def center(self):
        frame_geometry = self.frameGeometry()
        center_point = QApplication.desktop().availableGeometry().center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())

    def fill_admin_data(self, admin_data):
        self.surname_input.setText(admin_data["surname"])
        self.name_input.setText(admin_data["name"])
        self.patronymic_input.setText(admin_data["patronymic"])
        self.phone_input.setText(admin_data["phone"])
        self.temp_phone_number = self.phone_input.text()
        self.description_input.setText(admin_data["description"])

        self.username_input.setText(admin_data["username"])
        self.username_input_temp = self.username_input.text()

        if isinstance(admin_data["image"], QPixmap):
            byte_array = QByteArray()
            buffer = QBuffer(byte_array)
            admin_data["image"].toImage().save(buffer, "PNG")
            self.photo_data = byte_array.data()
            self.photo_label.setPhoto(self.photo_data)
        elif isinstance(admin_data["image"], bytes):
            self.photo_data = admin_data["image"]
            self.photo_label.setPhoto(self.photo_data)
        else:
            self.photo_label.clearPhoto()

    def initUI(self):
        layout = QVBoxLayout(self)
        grid_layout = QGridLayout()

        title_label = QLabel(self.header_text, self)
        grid_layout.addWidget(title_label, 0, 1, alignment=Qt.AlignCenter)

        close_button = HoverButton("X", 30, 30, 35, '#8F2D31', True, '#8F2D31', 'red', 5, 'red')
        close_button.clicked.connect(self.close)
        grid_layout.addWidget(close_button, 0, 2, alignment=Qt.AlignRight)

        layout.addLayout(grid_layout)

        self.surname_input = QLineEdit(self)
        self.surname_input.setPlaceholderText("Фамилия")

        self.name_input = QLineEdit(self)
        self.name_input.setPlaceholderText("Имя")

        self.patronymic_input = QLineEdit(self)
        self.patronymic_input.setPlaceholderText("Отчество")

        self.phone_input = QLineEdit(self)
        self.phone_input.setPlaceholderText("Номер телефона")

        self.description_input = QTextEdit(self)
        self.description_input.setPlaceholderText("Информация об администраторе")
        self.description_input.setFixedHeight(70)

        self.username_input = QLineEdit(self)
        self.username_input.setPlaceholderText("Логин")

        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Пароль")

        form_layout = QGridLayout()
        form_layout.setColumnStretch(0, 2)
        form_layout.setColumnStretch(1, 1)

        form_layout.addWidget(self.surname_input, 0, 0)
        form_layout.addWidget(self.name_input, 1, 0)

        self.photo_label = FillPhotoClicked()
        form_layout.addWidget(self.photo_label, 0, 1, 2, 1, alignment=Qt.AlignCenter)

        form_layout.addWidget(self.patronymic_input, 2, 0)

        self.clear_photo_button = HoverButton("Удалить фото", 170, 35, 15, '#FF6F61', True, '#8F2D31', 'red', 8, 'red')
        self.clear_photo_button.clicked.connect(self.photo_label.clearPhoto)
        form_layout.addWidget(self.clear_photo_button, 2, 1, alignment=Qt.AlignCenter)

        form_layout.addWidget(self.phone_input, 3, 0, 1, 2)
        form_layout.addWidget(self.description_input, 4, 0, 1, 2)

        form_layout.addWidget(self.username_input, 5, 0)
        form_layout.addWidget(self.password_input, 5, 1)

        layout.addLayout(form_layout)

        confirm_button = HoverButton("Подтвердить", 190, 35, 15, '#5DEBE6', False, '#5DEBE6', '', 8)
        confirm_button.clicked.connect(self.validate_and_save)
        layout.addWidget(confirm_button, alignment=Qt.AlignCenter)

        self.setLayout(layout)

    def validate_and_save(self):
        surname = self.surname_input.text().strip()
        name = self.name_input.text().strip()
        patronymic = self.patronymic_input.text().strip()
        phone_number = self.phone_input.text().strip()
        description = self.description_input.toPlainText().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()

        valid = True

        if not surname:
            self.surname_input.setStyleSheet("border-color:red;")
            valid = False
        else:
            self.surname_input.setStyleSheet("border-color:#75A9A7;")

        if not name:
            self.name_input.setStyleSheet("border-color:red;")
            valid = False
        else:
            self.name_input.setStyleSheet("border-color:#75A9A7;")

        has_changed_un = self.username_input_temp != username
        has_changed_ph = self.temp_phone_number != phone_number

        if not re.match(r"^\+\d{10,15}$", phone_number):
            self.phone_input.setStyleSheet("border-color:red;")
            valid = False
        else:
            if (not self.admin_id and check_admin_phone_in_database(phone_number)) or (
                    has_changed_ph and check_admin_username_in_database(phone_number)):
                self.phone_input.setStyleSheet("border-color:red;")
                QMessageBox.warning(self, "Ошибка", "Администратор с таким номером уже существует!")
                valid = False
            self.phone_input.setStyleSheet("border-color:#75A9A7;")

        if not username:
            self.username_input.setStyleSheet("border-color:red;")
            valid = False
        elif (not self.admin_id and check_admin_username_in_database(username)) or (
                has_changed_un and check_admin_username_in_database(username)):
            self.username_input.setStyleSheet("border-color:red;")
            valid = False
            QMessageBox.warning(self, "Ошибка", "Администратор с таким логином уже существует!")
        else:
            self.username_input.setStyleSheet("border-color:#75A9A7;")

        if self.admin_id:
            if password:
                hashed_password = self.hash_password(password)
            else:
                hashed_password = None
        else:
            if password:
                hashed_password = self.hash_password(password)
            else:
                self.password_input.setStyleSheet("border-color:red;")
                valid = False

        if not valid:
            return

        if self.admin_id:
            query = """
                UPDATE administrators
                SET surname=%s, first_name=%s, patronymic=%s, phone_number=%s, description=%s, photo=%s
                WHERE admin_id=%s
                RETURNING user_id;
            """
            if isinstance(self.photo_data, QByteArray):
                self.photo_data = self.photo_data.data()
            result = execute_query(query, (
                surname, name, patronymic, phone_number, description, self.photo_label.photo_data, self.admin_id
            ), fetch=True, fetch_one=True)

            if hashed_password:
                query2 = """
                    UPDATE users
                    SET username=%s, password_hash=%s
                    WHERE user_id=%s
                    RETURNING user_id;
                """
                result2 = execute_query(query2, (username, hashed_password, result[0]), fetch=True, fetch_one=True)
            else:
                query2 = """
                    UPDATE users
                    SET username=%s
                    WHERE user_id=%s
                    RETURNING user_id;
                """
                result2 = execute_query(query2, (username, result[0]), fetch=True, fetch_one=True)

            if result and result2:
                self.admin_updated.emit({
                    "admin_id": self.admin_id,
                    "name": name,
                    "surname": surname,
                    "patronymic": patronymic,
                    "phone": phone_number,
                    "description": description,
                    "image": self.photo_label.photo_data,
                    "username": username,
                    "password_hash": hashed_password
                })
            else:
                logger.error(f"❌ Ошибка: администратор {self.admin_id} не найден или не обновился!")
        else:
            query = """
                INSERT INTO users (username, password_hash, role)
                VALUES (%s, %s, 'administrator') RETURNING user_id;
            """
            salt = bcrypt.gensalt()
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
            result1 = execute_query(query, (username, hashed_password))
            photo_data = self.photo_label.photo_data if self.photo_label.photo_data else None
            if isinstance(photo_data, QByteArray):
                self.photo_data = self.photo_data.data()

            query = """
                INSERT INTO administrators (user_id, surname, first_name, patronymic, phone_number, description, photo)
                VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING admin_id;
            """
            result = execute_query(query, (
                result1[0][0], surname, name, patronymic, phone_number, description, photo_data
            ))

            if result and result1:
                admin_id = result[0][0]
                user_id = result1[0][0]
                self.admin_added.emit({
                    "admin_id": admin_id,
                    "name": name,
                    "surname": surname,
                    "patronymic": patronymic,
                    "phone": phone_number,
                    "description": description,
                    "image": self.photo_label.photo_data,
                    "username": username,
                    "password_hash": hashed_password,
                    "user_id": user_id
                })


        QMessageBox.information(self, "Успех", "Администратор успешно сохранён.")
        self.accept()

    def hash_password(self, password: str) -> str:
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed_password.decode('utf-8')

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(0, 0, self.width(), self.height())

        borderPen = QPen(QColor(117, 169, 167))
        borderPen.setWidth(self.borderWidth)
        painter.setPen(borderPen)

        backgroundBrush = QColor(255, 255, 255)
        painter.setBrush(backgroundBrush)

        if self.radius > 0:
            painter.drawRoundedRect(rect, self.radius, self.radius)
        else:
            painter.drawRect(rect)

        painter.end()

    def mousePressEvent(self, event):
        self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPos() - self.oldPos)
        self.move(self.pos() + delta)
        self.oldPos = event.globalPos()