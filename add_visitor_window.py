import re
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QLineEdit, QGridLayout, QDialog, QMessageBox
from PyQt5.QtCore import Qt, QRectF, QPoint
from PyQt5.QtGui import QPainter, QColor, QPen

from database import check_phone_in_database,  \
 add_subscription_to_existing_user, add_user_to_db
from hover_button import HoverButton
from subscription import SubscriptionWidget
from utils import WorkerThread, logger


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

            if not client_id:
                raise Exception("Ошибка при добавлении нового пользователя.")

            if subscription_data:
                # добавление абонемента
                subscription_id = add_subscription_to_existing_user(client_id, subscription_data)
                if not subscription_id:
                    raise Exception("Ошибка при добавлении абонемента.")
                return "Клиент успешно добавлен с абонементом."
            else:
                return "Клиент успешно добавлен без абонемента."
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
        """
        оработка завершения добавления пользователя.
        """
        QMessageBox.information(self, "Результат", message)

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

        # переключение на страницу расписания
        self.main_window.from_add_client = True
        self.main_window.update_days(self.main_window.current_week, self.main_window.selected_trainer_id)
        self.main_window.switch_to_page(self.main_window.schedule_page)
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
