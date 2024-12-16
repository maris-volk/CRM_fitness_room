from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLineEdit, QScrollArea, QLabel, QHBoxLayout, QGridLayout,
                             QMessageBox)
from PyQt5.QtCore import Qt, QRectF, QPoint
from PyQt5.QtGui import QFont, QColor, QPen, QPainter

from database import execute_query
from hover_button import HoverButton
from utils import WorkerThread


from PyQt5.QtWidgets import QWidget, QLabel, QGridLayout
from PyQt5.QtCore import Qt


class ClientWidget(QWidget):
    def __init__(self, client_data):
        super().__init__()
        self.setObjectName('base_widget')  # Установить имя объекта
        self.init_ui(client_data)

    def init_ui(self, client_data):
        grid = QGridLayout(self)
        grid.setContentsMargins(10, 5, 10, 5)
        grid.setSpacing(5)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 2)
        grid.setColumnStretch(2, 2)

        # Цвета для оформления
        active_color = "#05A9A3"
        inactive_color = "#75A9A7"

        # Первая строка
        status_color = active_color if "В зале" in client_data['status'] else inactive_color
        status_label = QLabel(client_data['status'])
        status_label.setStyleSheet(f"color: {status_color}; font-weight: bold;")
        status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        phone_label = QLabel(client_data['phone'])
        phone_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        subscription_color = active_color if "Абонемент" in client_data['subscription'] else inactive_color
        subscription_label = QLabel(client_data['subscription'])
        subscription_label.setStyleSheet(f"color: {subscription_color};")
        subscription_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        grid.addWidget(status_label, 0, 0)
        grid.addWidget(phone_label, 0, 1)
        grid.addWidget(subscription_label, 0, 2)

        # Вторая строка
        name_label = QLabel(client_data['name'])

        name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        trainer_color = active_color if "Тренер" in client_data['trainer'] else inactive_color
        trainer_label = QLabel(client_data['trainer'])
        trainer_label.setStyleSheet(f"color: {trainer_color};")
        trainer_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        grid.addWidget(name_label, 1, 0, 1, 2)
        grid.addWidget(trainer_label, 1, 2)

        # Третья строка
        start_date_label = QLabel(f"С {client_data['start_date']}")
        start_date_label.setStyleSheet(f"color: {active_color}; font-size: 13px;")
        start_date_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        grid.addWidget(start_date_label, 2, 0)

        # Установим стиль для границы самого виджета
        self.setStyleSheet("""
            QWidget#base_widget {
                background-color: white;        /* Устанавливаем фоновый цвет */
                border: 3px solid #75A9A7;      /* Граница для каждого элемента */
                border-radius: 8px;             /* Скругление углов */
                margin-bottom: 10px;            /* Отступы между элементами */
                padding: 5px;                   /* Отступы внутри виджета */
            }
            QLabel {
                font-family: 'Unbounded';
                font-size: 14px;
                color: black;
                font-family: Unbounded;

                font-weight: 700;

            }
        """)
        name_label.setStyleSheet("color: black; font-weight: bold;font-size: 18px;margin-left:8px;")






class ClientSearchWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Список посетителей")
        self.setGeometry(300, 300, 600, 600)
        self.setWindowFlags(Qt.FramelessWindowHint)  # Remove window controls
        self.setAttribute(Qt.WA_TranslucentBackground)  # Transparent background
        self.oldPos = self.pos()
        self.radius = 18  # Corner radius
        self.borderWidth = 5  # Border thickness
        self.setWindowModality(Qt.ApplicationModal)  # Modal window blocking other windows
        self.client_list = []  # Список клиентов
        self.init_ui()
        self.load_clients()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        grid_layout = QGridLayout()

        # Заголовок
        title_label = QLabel("Список посетителей", self)
        title_label.setObjectName("titleLabel")
        title_label.setStyleSheet("""
            QLabel {
                font-family: 'Unbounded';
                font-size: 20px;
                font-weight: bold;
                color: black;
            }
        """)
        grid_layout.addWidget(title_label, 0, 1, alignment=Qt.AlignCenter)

        # Кнопка закрытия
        close_button = HoverButton("X", 30, 30, 35, '#8F2D31', True, '#8F2D31', 'red', 5, 'red')
        close_button.setObjectName("closeButton")
        close_button.clicked.connect(self.close)
        grid_layout.addWidget(close_button, 0, 2, alignment=Qt.AlignRight)

        # Растяжение колонок
        grid_layout.setColumnStretch(0, 1)  # Левая колонка (пустая)
        grid_layout.setColumnStretch(1, 3)  # Центральная колонка с заголовком
        grid_layout.setColumnStretch(2, 1)  # Правая колонка (для кнопки закрытия)

        main_layout.addLayout(grid_layout)

        # Поле для поиска
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


        # Прокручиваемая область
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
                background: #75A9A7;
            }
            QScrollBar::handle:vertical {
                background: #5DEBE6;
                border-radius: 4px;
            }
        """)
        main_layout.addWidget(self.scroll_area)

        # Контейнер для клиентов
        self.container_widget = QWidget()
        self.container_widget.setObjectName('clients_content')
        self.container_widget.setStyleSheet("""
                    QWidget#clients_content {
                        border: none;
                        background-color: white;
                    }
        """)
        self.container_layout = QVBoxLayout(self.container_widget)
        self.container_layout.setAlignment(Qt.AlignTop)
        self.container_layout.setObjectName('clients_content_layout')

        self.scroll_area.setWidget(self.container_widget)

        self.setLayout(main_layout)

    def update_client_list(self, clients):
        # Очистка текущего списка
        for i in reversed(range(self.container_layout.count())):
            widget = self.container_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)


        for client in clients:
            client_widget = ClientWidget(client)

            # Создаем QWidget-обертку
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

            self.container_layout.addWidget(frame)

    def load_clients(self):
        """
        Загружает список клиентов из БД через WorkerThread.
        """
        def fetch_clients():
            query = """
                SELECT c.client_id, 
                       c.surname || ' ' || c.first_name AS name, 
                       c.phone_number AS phone, 
                       CASE 
                           WHEN s.is_valid = TRUE THEN 
                               'Абонемент ' || TO_CHAR(s.valid_since, 'DD.MM.YY') || ' - ' || TO_CHAR(s.valid_until, 'DD.MM.YY')
                           ELSE 'Абонемент отсутствует'
                       END AS subscription,
                       COALESCE(t.surname || ' ' || t.first_name, 'Нет закрепленных тренеров') AS trainer,
                       TO_CHAR(c.membership_start_date, 'DD.MM.YY') AS start_date,
                       CASE 
                           WHEN v.in_gym = TRUE THEN '● В зале'
                           ELSE '○ Вне зала'
                       END AS status
                FROM client c
                LEFT JOIN subscription s ON c.subscription = s.subscription_id
                LEFT JOIN training_slots ts ON c.client_id = ts.client
                LEFT JOIN trainer t ON ts.trainer = t.trainer_id
                LEFT JOIN visit_fitness_room v ON c.client_id = v.client
                ORDER BY c.membership_start_date DESC;
            """
            return execute_query(query)

        self.worker_thread = WorkerThread(fetch_clients)
        self.worker_thread.result_signal.connect(self.display_clients)
        self.worker_thread.start()

    def display_clients(self, result):
        self.client_list = [
            {
                'id': r[0],
                'status': r[6],  # Статус "● В зале" или "○ Вне зала"
                'phone': r[2],
                'subscription': r[3],
                'name': r[1],
                'trainer': r[4],
                'start_date': r[5]
            } for r in result
        ]
        self.update_client_list(self.client_list)


    def filter_clients(self):
        search_text = self.search_input.text().lower()
        filtered_clients = [
            client for client in self.client_list
            if search_text in client['name'].lower() or search_text in client['phone']
        ]
        self.update_client_list(filtered_clients)

    def paintEvent(self, event):
        """
        Кастомная отрисовка окна с закругленными углами.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Прямоугольник окна
        rect = QRectF(0, 0, self.width(), self.height())

        # Устанавливаем цвет границы
        borderPen = QPen(QColor(117, 169, 167))
        borderPen.setWidth(self.borderWidth)
        painter.setPen(borderPen)

        # Устанавливаем цвет фона
        backgroundBrush = QColor(255, 255, 255)
        painter.setBrush(backgroundBrush)

        # Отрисовка закругленных углов
        if self.radius > 0:
            painter.drawRoundedRect(rect, self.radius, self.radius)
        else:
            painter.drawRect(rect)

        painter.end()

    def mousePressEvent(self, event):
        # Store initial position for window dragging
        self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        # Calculate delta and move the window
        delta = QPoint(event.globalPos() - self.oldPos)
        self.move(self.pos() + delta)
        self.oldPos = event.globalPos()