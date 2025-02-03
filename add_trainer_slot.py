# add_slot_window.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLineEdit, QScrollArea, QLabel, QPushButton, QHBoxLayout,
                             QGridLayout, QMessageBox, QSpacerItem, QSizePolicy)
from PyQt5.QtCore import Qt, QPoint, QTime, pyqtSignal, QEvent, QRectF
from PyQt5.QtGui import QPainter, QPen, QColor

from database import execute_query
from hover_button import HoverButton

# client_widget.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt

from utils import center


class ClientWidget(QWidget):
    """виджет клиента."""
    slot_added = pyqtSignal(dict)

    def __init__(self, selected_client=None):
        super().__init__()
        self.selected_client = selected_client  # Установка выбранного клиента
        self.confirm_clicked = False
        self.setObjectName('client_widget')
        self.init_ui(self.selected_client)

    def init_ui(self, client_data):
        layout = QVBoxLayout(self)
        name_label = QLabel(client_data['name'])
        phone_label = QLabel(client_data['phone'])

        name_label.setStyleSheet("font-weight: bold; font-size: 16px; font-family: 'Unbounded'; margin-bottom: 0px;")
        phone_label.setStyleSheet("color: #555; font-size: 14px; font-family: 'Unbounded';")
        layout.addWidget(name_label)
        layout.addWidget(phone_label)

        self.setStyleSheet("""
            QWidget#client_widget {
                background-color: white;
                border: 3px solid #75A9A7;
                border-radius: 12px;
                margin: 5px;
                padding: 5px;
            }
            
        """)


class AddSlotWindow(QWidget):
    slot_added = pyqtSignal(dict)

    def __init__(self, selected_client=None, subscription_data=None, existing_slots=None, selected_date=None, trainer_id=None):
        super().__init__()
        print(selected_client)
        self.selected_client = selected_client
        self.trainer_id = trainer_id
        self.subscription_data = subscription_data
        self.selected_date = selected_date
        self.existing_slots = existing_slots or []  # список [(start_time, end_time)]
        self.setGeometry(300, 300, 670, 670)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.oldPos = self.pos()
        self.radius = 18
        self.borderWidth = 5
        self.client_list = []
        self.confirm_clicked = False
        center(self)
        self.init_ui()


    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # создание сеточного макета для заголовка и кнопки закрытия
        grid_layout = QGridLayout()

        # заголовок
        title_label = QLabel("Добавление слота", self)
        title_label.setObjectName("titleLabel")
        title_label.setStyleSheet("""
                    QLabel {
                        font-family: 'Unbounded';
                        font-size: 23px;
                        font-weight: 500;
                        text-align: center;
                        background-color: transparent;
                        border: 0px;
                    }
                """)
        title_label.setAlignment(Qt.AlignCenter)
        grid_layout.addWidget(title_label, 0, 1, alignment=Qt.AlignCenter)

        # кнопка закрытия
        close_button = HoverButton("X", 30, 30, 35, '#8F2D31', True, '#8F2D31', 'red', 5, 'red')
        close_button.setObjectName("closeButton")
        close_button.clicked.connect(self.close)
        grid_layout.addWidget(close_button, 0, 2, alignment=Qt.AlignRight | Qt.AlignTop)

        # растяжения колонок
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 3)
        grid_layout.setColumnStretch(2, 1)

        main_layout.addLayout(grid_layout)
        # поле поиска
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск...")
        self.search_input.setStyleSheet("""
        
            font-family: 'Unbounded';
            font-size: 22.5px;
            padding: 15px 20.4px 15px 15px;
            border-radius: 18px;
            border: solid #75A9A7;
            border-width: 0px 0px 2.7px 2.7px;
            background-color: transparent;
        """)
        self.search_input.textChanged.connect(self.filter_clients)
        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_input)
        search_layout.setContentsMargins(10, 5, 10, 5)  # Отступы для строки поиска
        main_layout.addLayout(search_layout)

        # область для списка клиентов
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName('scroll_clients')
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("""
            QScrollArea#scroll_clients {
                border: none;
                background-color: white;
            }
            QScrollBar:vertical {
                width: 8px;
                background: white;
            }
            QScrollBar::handle:vertical {
                background: #75A9A7;
                border-radius: 4px;
            }
        """)
        main_layout.addWidget(self.scroll_area)

        self.client_container = QWidget()
        self.client_container.setObjectName('clients_content')
        self.client_container.setStyleSheet("""
            QWidget#clients_content {
                border: none;
                background-color: white;
            }
        """)
        self.client_layout = QVBoxLayout(self.client_container)
        self.client_layout.setAlignment(Qt.AlignTop)
        self.client_layout.setObjectName('clients_content_layout')
        self.scroll_area.setWidget(self.client_container)

        # метка для информации о выбранном клиенте
        if self.selected_client and self.subscription_data:
            formatted_client = self.format_client_data(self.selected_client,self.subscription_data)
            self.selected_client = formatted_client
            self.client_info_label = QLabel(
                f"Выбран клиент:<br><span style='color:#75A9A7; font-weight:500'>{self.selected_client['name']}</span> ({self.selected_client['phone']})"
            )
        else:
            self.client_info_label = QLabel("Клиент не выбран", self)

        self.client_info_label.setAlignment(Qt.AlignCenter)
        self.client_info_label.setStyleSheet("""
            font-family: 'Unbounded';
            font-size: 16px;
            color: #333;
            margin-bottom: 10px;
        """)
        main_layout.addWidget(self.client_info_label)

        time_layout = QHBoxLayout()

        start_time_label = QLabel("Время начала:", self)
        start_time_label.setStyleSheet("""
            font-family: 'Unbounded';
            font-size: 14px;
            color: black;
        """)
        self.start_time_input = QLineEdit()
        self.start_time_input.setPlaceholderText("Время начала (чч:мм)")
        self.start_time_input.setInputMask("99:99")
        self.start_time_input.setObjectName("start_time_input")


        end_time_label = QLabel("Время конца:", self)
        end_time_label.setStyleSheet("""
            font-family: 'Unbounded';
            font-size: 14px;
            color: black;
        """)
        self.end_time_input = QLineEdit()
        self.end_time_input.setPlaceholderText("Время конца (чч:мм)")
        self.end_time_input.setInputMask("99:99")
        self.end_time_input.setObjectName("end_time_input")

        self.start_time_input.textChanged.connect(lambda: self.validate_partial_input("start"))
        self.end_time_input.textChanged.connect(lambda: self.validate_partial_input("end"))
        self.start_time_input.textChanged.connect(self.on_time_input_changed)
        self.end_time_input.textChanged.connect(self.on_time_input_changed)


        for input_field in [self.start_time_input, self.end_time_input]:
            input_field.setStyleSheet("""

                font-size: 14px;
                color: black;
                font-family: 'Unbounded';
                padding: 15px 20.4px 15px 15px;
                border-radius: 18px;
                border: solid #75A9A7;
                border-width: 0px 0px 2.7px 2.7px;
            """)

        time_layout.addWidget(start_time_label)
        time_layout.addWidget(self.start_time_input)
        time_layout.addWidget(end_time_label)
        time_layout.addWidget(self.end_time_input)
        main_layout.addLayout(time_layout)

        confirm_button = HoverButton("Подтвердить", 200, 50, 18, '#53d0cc', False, '#53d0cc', '', 12, '')

        top_spacer = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)

        bottom_spacer = QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)

        main_layout.addItem(top_spacer)

        main_layout.addWidget(confirm_button, alignment=Qt.AlignCenter)

        main_layout.addItem(bottom_spacer)
        confirm_button.pressed.connect(self.on_confirm_pressed)

        confirm_button.clicked.connect(self.confirm_slot)


        self.load_clients(self.selected_date)


    def on_time_input_changed(self):
        """изменение времени в любом из полей."""
        self.start_time_input.blockSignals(True)
        self.end_time_input.blockSignals(True)
        try:
            if self.start_time_input.hasFocus():
                start_time_str = self.start_time_input.text()
                self.update_end_time(start_time_str)
            elif self.end_time_input.hasFocus():
                end_time_str = self.end_time_input.text()
                self.update_start_time(end_time_str)
        finally:
            self.start_time_input.blockSignals(False)
            self.end_time_input.blockSignals(False)

    def update_end_time(self, start_time_str):
        """обновляет время окончания на основе времени начала."""
        start_time = QTime.fromString(start_time_str, "hh:mm")
        if not start_time.isValid():
            self.end_time_input.setText("")
            return

        # добавление 45 минут
        if start_time < QTime(8, 0):
            start_time = QTime(8, 0)
            self.start_time_input.setText(start_time.toString("hh:mm"))

        end_time = start_time.addSecs(45 * 60)

        if end_time > QTime(22, 0):
            end_time = QTime(22, 0)
            if start_time > QTime(21, 15):
                self.start_time_input.setText(QTime(21, 15).toString("hh:mm"))
        self.end_time_input.setText(end_time.toString("hh:mm"))

    def validate_times(self, field):
        """проверка и корректировка введенного время в зависимости от поля."""

        def correct_time(input_text, default_time):
            time = QTime.fromString(input_text, "hh:mm")
            if not time.isValid():
                try:

                    hours, minutes = map(int, input_text.split(":"))
                    temp_hours = hours
                    hours = max(8, min(hours, 22))
                    if default_time == QTime(8,0):
                        if (temp_hours < 8):
                            minutes = 0
                        else:
                            minutes = min(minutes, 59)
                    else:
                        minutes = min(minutes, 59)
                    return QTime(hours, minutes)
                except (ValueError, IndexError):
                    return default_time
            else:
                temp = time.hour()
                hours = max(8, min(time.hour(), 22))
                if default_time == QTime(8, 0):
                    if (temp < 8):
                        minutes = 0
                    else:
                        minutes = min(time.minute(), 59)
                else:
                    minutes = min(time.minute(), 59)

                return QTime(hours, minutes)

        default_start = QTime(8, 0)
        default_end = default_start.addSecs(45 * 60)

        start_time_text = self.start_time_input.text()
        end_time_text = self.end_time_input.text()

        start_time = correct_time(start_time_text, default_start)
        end_time = correct_time(end_time_text, default_end)

        if field == "start":
            if start_time >= end_time:
                end_time = start_time.addSecs(45 * 60)
                if end_time > QTime(22, 0):
                    end_time = QTime(22, 0)
                self.end_time_input.setText(end_time.toString("hh:mm"))
            self.start_time_input.setText(start_time.toString("hh:mm"))
        elif field == "end":
            if end_time <= start_time:
                start_time = end_time.addSecs(-45 * 60)
                if start_time < QTime(8, 0):
                    start_time = QTime(8, 0)
                self.start_time_input.setText(start_time.toString("hh:mm"))
            self.end_time_input.setText(end_time.toString("hh:mm"))

    def update_start_time(self, end_time_str):
        """обновление время начала на основе времени окончания."""
        end_time = QTime.fromString(end_time_str, "hh:mm")
        if not end_time.isValid():
            self.start_time_input.setText("")
            return

        if end_time > QTime(22, 0):
            end_time = QTime(22, 0)
            self.end_time_input.setText(end_time.toString("hh:mm"))

        # - 45 минут
        start_time = end_time.addSecs(-45 * 60)
        # время начала 8:00
        if start_time < QTime(8, 0):
            start_time = QTime(8, 0)
            if end_time < QTime(8, 45):
                self.end_time_input.setText(QTime(8, 45).toString("hh:mm"))

        self.start_time_input.setText(start_time.toString("hh:mm"))



    def format_client_data(self, client_data, sub_data = None):
        """Приводит данные клиента к ожидаемому формату."""
        if sub_data:

            return {
                "client_id":client_data.get('client_id', None),
                "name": f"{client_data.get('last_name', '')} {client_data.get('first_name', '')}".strip(),
                "phone": client_data.get('phone_number', 'Не указан'),
                "tariff":sub_data.get('tariff', ''),
            }
        else:
            return {
                "name": f"{client_data.get('last_name', '')} {client_data.get('first_name', '')}".strip(),
                "phone": client_data.get('phone_number', 'Не указан'),
            }

    def on_confirm_pressed(self):
        """устанавливает флаг при нажатии кнопки подтверждения."""
        self.confirm_clicked = True

    def validate_partial_input(self, field):
        if not self.confirm_clicked:
            input_field = self.start_time_input if field == "start" else self.end_time_input
            text = input_field.text()

            if len(text) >= 5:
                self.validate_times(field)

    def load_clients(self, selected_date):
        """
        Загружает клиентов с активными абонементами на выбранную дату.
        :param selected_date: Дата, на которую добавляется слот.
        """
        # SQL-запрос для получения клиентов с активным абонементом на выбранную дату
        query = """
            SELECT 
                c.client_id,
                c.first_name,
                c.surname,
                c.phone_number,
                s.tariff,
                s.is_valid,
                s.valid_until,
                COUNT(ts.slot_id) AS daily_slots
            FROM 
                client c
            JOIN 
                subscription s ON c.subscription = s.subscription_id
            LEFT JOIN 
                training_slots ts ON ts.client = c.client_id AND DATE(ts.start_time) = %s
            WHERE 
                s.is_valid = TRUE
                AND s.valid_until >= %s
                AND (s.frozen_from IS NULL OR s.frozen_until IS NULL OR %s NOT BETWEEN s.frozen_from AND s.frozen_until)
            GROUP BY 
                c.client_id, c.first_name, c.surname, c.phone_number, s.tariff, s.is_valid, s.valid_until
        """
        result = execute_query(query, (selected_date, selected_date, selected_date))

        self.client_list = []
        if result:
            for row in result:
                self.client_list.append({
                    "client_id": row[0],
                    "name": f"{row[2]} {row[1]}",  # Объединяем фамилию и имя
                    "phone": row[3],
                    "tariff": row[4],
                    "is_valid": row[5],
                    "valid_until": row[6]
                })

        # обновляем виджет списка клиентов
        self.update_client_list(self.client_list)

    def update_client_list(self, clients):
        """Обновляет список клиентов."""
        for i in reversed(range(self.client_layout.count())):
            widget = self.client_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        for client in clients:
            client_widget = ClientWidget(client)
            client_widget.mousePressEvent = lambda event, c=client: self.select_client(c)
            frame = QWidget()
            frame.setObjectName("clientFrame")
            frame.setStyleSheet("""
                                QWidget#clientFrame {
                                border: 3px solid #75A9A7; /* Рамка для обертки */
                                border-radius: 12px;  /* Если нужны скругленные углы */
                          /* Отступ между элементами */
                            }
                    """)
            frame_layout = QVBoxLayout(frame)
            frame_layout.addWidget(client_widget)
            frame_layout.setContentsMargins(0, 0, 0, 0)  # Важно! Убираем отступы
            self.client_layout.addWidget(frame)

    def filter_clients(self):
        search_text = self.search_input.text().lower()
        filtered_clients = [c for c in self.client_list if search_text in c['name'].lower()]
        self.update_client_list(filtered_clients)

    def select_client(self, client):
        self.selected_client = client
        # только имя и фамилию в строку поиска
        self.search_input.setText(f"{client['name']}")
        # метка информации о клиенте с цветом имени
        self.client_info_label.setText(
            f"Выбран клиент:<br><span style='color:#75A9A7; font-weight:500'>{client['name']}</span> ({client['phone']})"
        )

    def confirm_slot(self):
        start_time = self.start_time_input.text()
        end_time = self.end_time_input.text()

        # выбран ли клиент
        if not self.selected_client:
            QMessageBox.warning(self, "Ошибка", "Клиент не выбран.")
            self.confirm_clicked = False  # Сброс флага
            return

        formatted_client = self.format_client_data(self.selected_client,self.subscription_data)

        # поля времени заполнены
        if not start_time or not end_time:
            QMessageBox.warning(self, "Ошибка", "Укажите время начала и конца.")
            self.confirm_clicked = False  # Сброс флага
            return

        # проверка корректности введённых времён
        start_qtime = QTime.fromString(start_time, "hh:mm")
        end_qtime = QTime.fromString(end_time, "hh:mm")

        if not start_qtime.isValid() or not end_qtime.isValid():
            QMessageBox.warning(self, "Ошибка", "Время введено некорректно.")
            self.confirm_clicked = False  # Сброс флага
            return

        # время начала должно быть меньше времени конца
        if start_qtime >= end_qtime:
            QMessageBox.warning(self, "Ошибка", "Время начала должно быть меньше времени конца.")
            self.confirm_clicked = False  # Сброс флага
            return

        for slot_start, slot_end in self.existing_slots:
            if start_qtime < slot_end and end_qtime > slot_start:
                QMessageBox.warning(self, "Ошибка", "Время слота пересекается с другим слотом.")
                return

            # проверка ограничений абонемента
        print(self.subscription_data)
        if self.subscription_data:
            tariff = self.subscription_data.get("tariff", "unlim_unlim_mnth")
            if not self.is_time_within_tariff(tariff, start_qtime, end_qtime):
                QMessageBox.warning(self, "Ошибка", f"Время слота не соответствует тарифу ({tariff}).")
                return

        if not self.can_add_slot(self.selected_client, start_qtime, end_qtime):
            return


            # Отправка данных
        query = """
                INSERT INTO training_slots (trainer, client, start_time, end_time)
                VALUES (%s, %s, %s, %s)
                RETURNING slot_id;
            """
        slot_id = execute_query(query, (
            self.trainer_id,  # Передаем trainer_id
            self.selected_client["client_id"],
            f"{self.selected_date} {start_time}:00",
            f"{self.selected_date} {end_time}:00"
        ), fetch=True)

        if slot_id and slot_id[0][0]:
            slot_id = slot_id[0][0]
            QMessageBox.information(self, "Успешно", "Слот успешно добавлен!")
            slot_data = {
                "slot_id": slot_id,
                "client": self.selected_client["name"],
                "client_id": self.selected_client["client_id"],
                "start_time": start_qtime,
                "end_time": end_qtime,
                "date":self.selected_date
            }
            self.slot_added.emit(slot_data)  # Отправляем сигнал с данными слота

        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось добавить слот в базу данных.")

        self.close()



    def can_add_slot(self, client, start_time, end_time):

        print(client)
        client_id = client["client_id"]
        tariff = client["tariff"]

        # проверка на тип абонемента
        if "8" in tariff or "12" in tariff:  # Если абонемент не безлимитный
            # проверка количества слотов клиента на указанную дату
            query = """
                SELECT COUNT(*)
                FROM training_slots
                WHERE client = %s AND start_time::date = %s
            """
            slot_count = execute_query(query, (client_id, self.selected_date))[0][0]
            if slot_count >= 1:
                QMessageBox.warning(self, "Ошибка", "Абонемент позволяет только один слот в день.")
                return False

        return True

    def is_time_within_tariff(self, tariff, start_time, end_time):

        if "mrn" in tariff:
            return start_time < QTime(16, 0) and end_time <= QTime(16, 0)
        elif "evn" in tariff:
            return start_time >= QTime(16, 0) and end_time > QTime(16, 0)
        elif "unlim" in tariff:
            return True
        else:
            return False

    def paintEvent(self, event):
        """
        Кастомная отрисовка окна с закругленными углами.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # прямоугольник окна
        rect = QRectF(0, 0, self.width(), self.height())

        # цвет границы
        borderPen = QPen(QColor(117, 169, 167))
        borderPen.setWidth(self.borderWidth)
        painter.setPen(borderPen)

        # цвет фона
        backgroundBrush = QColor(255, 255, 255)
        painter.setBrush(backgroundBrush)

        # отрисовка закругленных углов
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
