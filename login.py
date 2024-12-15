# login.py

import sys

from PyQt5.QtWidgets import (
    QVBoxLayout, QLabel, QLineEdit, QDialog, QDesktopWidget, QMessageBox
)
from PyQt5.QtCore import Qt, QRectF, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen

from database import authenticate_user
from hover_button import HoverButton
import logging

from utils import WorkerThread  # Убедитесь, что WorkerThread правильно импортируется

logger = logging.getLogger(__name__)


class LoginWidget(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Авторизация")
        self.setGeometry(300, 300, 400, 300)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setObjectName("myParentWidget")
        self.login_button = None
        self.current_user_id = None  # Добавляем атрибут для хранения user_id
        self.role = None  # Добавляем атрибут для хранения роли пользователя
        self.setStyleSheet("""
            QWidget#myParentWidget {
                background-color: transparent;
            }

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
                border-radius: 0px;
                background-color: transparent;
                border: 0px;
                font-family: 'Unbounded';
                font-size: 22.5px;
                font-weight: 500;
                text-align: center;
            }

            QLabel {
                font-family: 'Unbounded';
                font-size: 20px;
                font-weight: 500;
                text-align: center;
                margin-bottom: 5px;
            }
        """)

        self.initUI()

        self.oldPos = self.pos()
        self.radius = 18
        self.borderWidth = 5

        self.center_window()

    def center_window(self):
        screen = QDesktopWidget().screenGeometry()
        window = self.geometry()
        x = (screen.width() - window.width()) // 2
        y = (screen.height() - window.height()) // 2
        self.move(x, y)

    def initUI(self):
        layout = QVBoxLayout(self)

        # Заголовок
        title_label = QLabel("Авторизация", self)
        title_label.setObjectName("titleLabel")
        layout.addWidget(title_label, alignment=Qt.AlignCenter)

        # Поля ввода
        self.username_input = QLineEdit(self)
        self.username_input.setPlaceholderText("Логин")
        layout.addWidget(self.username_input)

        self.password_input = QLineEdit(self)
        self.password_input.setPlaceholderText("Пароль")
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)

        # Кнопка входа
        self.login_button = HoverButton("Войти", 190, 35, 15, '#5DEBE6', False, '#5DEBE6', '', 8)
        self.login_button.setFixedSize(180, 35)
        self.login_button.clicked.connect(self.authenticate_and_login)
        layout.addWidget(self.login_button, alignment=Qt.AlignCenter)

        self.setLayout(layout)

    def authenticate_and_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        if not username or not password:
            if not username:
                self.username_input.setStyleSheet("border-color:red;")
            if not password:
                self.password_input.setStyleSheet("border-color:red;")
            return

        # Сброс стилей при вводе
        self.username_input.setStyleSheet("border-color:#75A9A7;")
        self.password_input.setStyleSheet("border-color:#75A9A7;")
        self.login_button.set_border_color("Gold")
        self.login_button.set_hover_border_color("Yellow")
        self.login_button.set_font_color("Gold")

        # Запуск потока для аутентификации
        self.auth_thread = WorkerThread(authenticate_user, username, password)
        self.auth_thread.result_signal.connect(self.handle_authentication_result)
        self.auth_thread.start()

    def handle_authentication_result(self, result):
        user_id, role = result  # Распаковываем кортеж, возвращаемый authenticate_user
        print(role)
        if user_id:
            # Если аутентификация успешна, сохраняем user_id и роль
            self.current_user_id = user_id
            self.role = role
            self.login_button.set_border_color("#00FF00")
            self.login_button.set_hover_border_color("#00FF00")
            self.login_button.set_font_color("#14B814")
            QTimer.singleShot(400, self.accept)  # Закрыть диалог после задержки
            logger.info(f"Пользователь с ID {self.current_user_id} успешно вошёл в систему.")
        else:
            # Если аутентификация не удалась
            self.username_input.setStyleSheet("border-color:red;")
            self.password_input.setStyleSheet("border-color:red;")
            self.login_button.set_border_color('#5DEBE6')
            self.login_button.set_hover_border_color('#5DEBE6')
            self.login_button.set_font_color('#5DEBE6')
            QMessageBox.warning(self, "Ошибка авторизации", "Неверный логин или пароль.")
            logger.warning("Не удалось аутентифицировать пользователя")

    def paintEvent(self, event):
        # Кастомная отрисовка для скругленных углов и границы
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
        # Сохранение начальной позиции для перетаскивания окна
        self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        # Перемещение окна при перетаскивании
        delta = event.globalPos() - self.oldPos
        self.move(self.pos() + delta)
        self.oldPos = event.globalPos()

    def closeEvent(self, event):
        # Обработка события закрытия окна
        sys.exit()
