import re

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLineEdit, QScrollArea, QLabel, QHBoxLayout, QGridLayout,
                             QMessageBox, QSizePolicy, QSpacerItem, QAction, QApplication)
from PyQt5.QtCore import Qt, QRectF, QPoint, QTimer, QEvent
from PyQt5.QtGui import QFont, QColor, QPen, QPainter

from client_profile import ClientProfileWindow
from database import execute_query, add_subscription_to_existing_user
from freeze_and_block import RevokeSubscriptionWindow, FreezeSubscriptionWindow
from hover_button import HoverButton
from subscription import SubscriptionWidget
from utils import WorkerThread, ClickableLabel, RoundedMenu, center

from PyQt5.QtWidgets import QWidget, QLabel, QGridLayout
from PyQt5.QtCore import Qt

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLineEdit, QScrollArea, QLabel, QHBoxLayout, QGridLayout,
                             QMessageBox)
from PyQt5.QtCore import Qt, QRectF, QPoint
from PyQt5.QtGui import QFont, QColor, QPen, QPainter

from client_profile import ClientProfileWindow
from database import execute_query
from hover_button import HoverButton
from utils import WorkerThread, ClickableLabel

from PyQt5.QtWidgets import QWidget, QLabel, QGridLayout
from PyQt5.QtCore import Qt


class ClientWidget(QWidget):
    def __init__(self, client_data, parent_window, role):
        super().__init__()
        self.parent_window = parent_window
        self.name_label = None
        self.role = role
        self.setObjectName('base_widget')  # Установить имя объекта
        self.init_ui(client_data)

    def init_ui(self, client_data):
        print(client_data)
        self.client_id = client_data['id']
        self.menu = None

        grid = QGridLayout(self)
        grid.setContentsMargins(10, 5, 10, 5)
        grid.setSpacing(5)

        # Цвета для оформления
        active_color = "#05A9A3"
        inactive_color = "#75A9A7"

        # Первая строка: статус и телефон
        status_color = active_color if "В зале" in client_data['status'] else inactive_color
        self.status_label = QLabel(client_data['status'])
        self.status_label.setStyleSheet(f"color: {status_color}; font-weight: bold;")
        self.status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        phone_text = client_data['phone']
        if len(phone_text) > 14:
            phone_text = phone_text[:14] + "..."
        phone_label = QLabel(phone_text)
        phone_label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)  # Минимальная ширина, зависящая от текста

        phone_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Абонемент
        subscription_text = client_data.get('subscription', 'Абонемент отсутствует')
        if not isinstance(subscription_text, str):
            subscription_text = str(subscription_text)
        subscription_color = active_color if "Абонемент" in subscription_text else inactive_color
        self.subscription_label = ClickableLabel(subscription_text)
        self.subscription_label.setStyleSheet(f"color: {subscription_color};")
        self.subscription_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Вторая строка: имя
        name_text = client_data['name']
        max_length = 16  # Базовое ограничение
        if not client_data['name'].isupper():
            max_length += 2  # Увеличиваем ограничение, если имя не написано капсом

        if len(name_text) > max_length:
            name_text = name_text[:max_length] + "..."
        self.name_label = ClickableLabel(name_text)

        # Устанавливаем политику размера
        self.name_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)  # Фиксированная ширина
        self.name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # Устанавливаем минимальную ширину на основе содержимого

        # Добавляем в сетку

        status_and_phone_widget = QWidget()
        status_and_phone_layout = QHBoxLayout(status_and_phone_widget)
        status_and_phone_layout.setContentsMargins(0, 0, 0, 0)
        status_and_phone_layout.setSpacing(5)  # Отступ между статусом и телефоном

        # Устанавливаем выравнивание элементов внутри макета
        status_and_phone_layout.setAlignment(Qt.AlignLeft)

        # Добавляем статус и телефон
        status_and_phone_layout.addWidget(self.status_label)
        status_and_phone_layout.addWidget(phone_label)

        # Добавляем макет в сетку
        grid.addWidget(status_and_phone_widget, 0, 0)
        grid.addWidget(self.name_label, 1, 0)
        grid.addWidget(self.subscription_label, 0, 1)

        if self.role == 'Управляющий':
            delete_button = HoverButton("✖", 30, 30, 30, 'red', True, 'red', 'white', 5, 'red')
            delete_button.clicked.connect(self.delete_client)
            grid.addWidget(delete_button, 0, 2, 3, 1,
                           alignment=Qt.AlignLeft)  # rowSpan = 3, чтобы кнопка занимала всю высоту

        # Тренер
        trainer_color = active_color if "Тренер" in client_data['trainer'] else inactive_color
        trainer_label = QLabel(client_data['trainer'])
        trainer_label.setStyleSheet(f"color: {trainer_color};")
        trainer_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        grid.addWidget(trainer_label, 1, 1)

        # Третья строка: дата начала
        start_date_label = QLabel(f"С {client_data['start_date']}")
        start_date_label.setStyleSheet(f"color: {active_color}; font-size: 13px;")
        start_date_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        grid.addWidget(start_date_label, 2, 0)

        # Настраиваем ширину колонок
        grid.setColumnStretch(0, 0)  # Первая колонка с минимальным растяжением
        grid.setColumnStretch(1, 2)  # Вторая колонка растягивается больше

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
        self.name_label.setStyleSheet("color: black; font-weight: bold;font-size: 18px;margin-left:8px;")
        self.name_label.clicked.connect(
            lambda client_id=self.client_id: self.show_client_profile(self.client_id))
        self.subscription_label.mousePressEvent = lambda event: self.handle_subscription_click(self.client_id,
                                                                                               client_data, event)

    def delete_client(self):
        # Удаляем клиента из базы данных
        query = "DELETE FROM client WHERE client_id = %s"
        execute_query(query, (self.client_id,))

        # Удаляем виджет клиента из списка
        self.parent_window.remove_client_widget(self.client_id)

    def show_client_profile(self, client_id):
        print(f"Открытие профиля клиента с ID: {client_id}")
        self.profile_window = ClientProfileWindow(client_id, self.role)
        self.profile_window.status_updated.connect(self.update_status)
        self.profile_window.show()
        self.profile_window.raise_()
        print("Профиль клиента открыт.")

    def update_status(self, new_status):
        """
        статус клиента в основном виджете после завершения посещения.
        """
        self.status_label.setText(new_status)
        status_color = "#75A9A7" if "Вне зала" in new_status else "#05A9A3"
        self.status_label.setStyleSheet(f"color: {status_color}; font-weight: bold; font-family: 'Unbounded';")

    def open_subscription_widget(self, user_id):
        self.subscription_window = SubscriptionWidget()
        self.subscription_window.confirmed.connect(
            lambda subscription_data: self.add_subscription(user_id, subscription_data)
        )
        self.subscription_window.show()

    def add_subscription(self, user_id, subscription_data):
        """
        Обрабатывает добавление абонемента для существующего пользователя.
        """
        subscription_id = add_subscription_to_existing_user(user_id, subscription_data)

        if subscription_id:
            subscription_data = self.fetch_subscription_data(subscription_id)
            if subscription_data:

                QMessageBox.information(self, "Успех", f"Абонемент успешно добавлен! ID: {subscription_id}")
                self.update_client_widget(subscription_data)
                self.parent_window.update_client_in_list(self.client_id, subscription_data)

                # Обновляем информацию о клиенте в родительском окне

            else:
                QMessageBox.critical(self, "Ошибка", "Не удалось загрузить данные об абонементе.")

    def fetch_subscription_data(self, subscription_id):
        """
        Извлекает данные об абонементе из базы данных по его ID.
        """
        query = """
            SELECT 
                s.tariff,
                TO_CHAR(s.valid_since, 'DD.MM.YY') AS valid_since,
                TO_CHAR(s.valid_until, 'DD.MM.YY') AS valid_until,
                s.is_valid,
                s.price
            FROM subscription s
            WHERE s.subscription_id = %s
        """
        params = (subscription_id,)
        result = execute_query(query, params, fetch=True)

        if result:
            row = result[0]
            subscription_data = {
                "tariff": row[0],
                "start_date": row[1],  # Год уже в формате "YY" благодаря SQL
                "end_date": row[2],  # Год уже в формате "YY" благодаря SQL
                "is_valid": row[3],
                "price": row[4]
            }
            return subscription_data
        else:
            return None

    def update_client_widget(self, subscription_data):
        """
        Обновляет надпись на виджете клиента на основе данных об абонементе.
        """
        if subscription_data is None:
            # Если данных нет, отображаем, что абонемент отсутствует
            self.subscription_label.setText("Абонемент отсутствует")
        else:
            # Извлекаем данные из словаря
            tariff = subscription_data.get("tariff", "Неизвестно")
            start_date = subscription_data.get("start_date", "неизвестно")
            end_date = subscription_data.get("end_date", "неизвестно")
            is_valid = subscription_data.get("is_valid", False)

            # Формируем строку абонемента
            subscription_text = f"Абонемент {start_date} - {end_date}"

            # Применяем стиль в зависимости от статуса
            style = "color: #05A9A3; font-weight: bold;" if is_valid else "color: #75A9A7; font-weight: bold;"

            # Устанавливаем текст и стиль
            self.subscription_label.setText(subscription_text)
            self.subscription_label.setStyleSheet(style)

    def handle_subscription_click(self, id, client_data, event):
        """
        Обрабатывает нажатие на лейбл с абонементом.
        """
        if client_data.get("subscription") == "Абонемент отсутствует":
            # Открываем окно для добавления нового абонемента
            self.open_subscription_widget(id)
        else:
            # Показываем контекстное меню
            self.show_context_menu(event)

    def show_context_menu(self, event):
        """
        Отображает контекстное меню под лейблом, сдвигая его на треть влево.
        Если курсор не наведён в течение 2 секунд, меню исчезает.
        """
        # Проверяем, существует ли уже открытое меню и не закрыто ли оно
        if hasattr(self, "context_menu") and self.context_menu and self.context_menu.isVisible():
            return  # Прерываем, если меню уже открыто

        label_rect = self.subscription_label.rect()

        # Смещаем позицию на треть влево
        bottom_center_x = label_rect.center().x() - (label_rect.width() // 3)
        bottom_y = label_rect.bottom()

        # Получаем глобальные координаты
        pos = self.subscription_label.mapToGlobal(QPoint(bottom_center_x, bottom_y))

        # Создаём меню
        self.context_menu = RoundedMenu(self)
        self.context_menu.add_colored_action("Лишить абонемента", "#FF0000", self.remove_subscription)
        self.context_menu.add_colored_action("Заморозить", "#e5e619", self.freeze_subscription)

        # Подключаем сигнал закрытия меню
        self.context_menu.aboutToHide.connect(self.on_menu_close)

        # Запускаем таймер на автоматическое закрытие, если курсор не наведён
        self.hovered = False
        self.context_menu.installEventFilter(self)  # Устанавливаем фильтр событий для отслеживания наведения

        # Отображаем меню
        self.context_menu.exec_(pos)

    def on_menu_close(self):
        """
        Удаляет ссылку на меню при его закрытии.
        """
        self.context_menu = None  # Освобождаем ссылку на меню

    def close_if_not_hovered(self):
        """
        Закрывает меню, если курсор не наведён.
        """
        if hasattr(self, "context_menu") and self.context_menu and self.context_menu.isVisible():
            self.context_menu.close()

    def eventFilter(self, obj, event):
        """
        Отслеживает события наведения и покидания меню.
        """
        if obj == self.context_menu:
            if event.type() == QEvent.Enter:
                self.hovered = True
            elif event.type() == QEvent.Leave:
                self.hovered = False
        return super().eventFilter(obj, event)

    def remove_subscription(self):
        """
        Открывает окно для ввода причины лишения абонемента и обновляет виджет клиента.
        """
        revoke_window = RevokeSubscriptionWindow(self.client_id, self.parent_window, parent=self)
        if revoke_window.exec_():  # Предполагается, что окно возвращает результат (успешно или отмена)
            # Обновление виджета после лишения абонемента
            self.update_client_widget(None)  # Передаём None, чтобы обновить как "Абонемент отсутствует"
            self.parent_window.update_client_in_list(self.client_id, None)  # Обновляем в списке клиентов

    def freeze_subscription(self):
        freeze_window = FreezeSubscriptionWindow(self.client_id, self.parent_window, parent=self)
        if freeze_window.exec_():
            # обновленные данные после заморозки
            updated_subscription_data = self.fetch_subscription_data(self.client_id)
            if updated_subscription_data:
                self.update_client_widget(updated_subscription_data)
                self.parent_window.update_client_in_list(self.client_id, updated_subscription_data)


class ClientSearchWindow(QWidget):
    def __init__(self, role=None):
        super().__init__()

        self.setWindowTitle("Список посетителей")
        if role == "Управляющий":
            self.setGeometry(300, 300, 700, 650)

        else:
            self.setGeometry(300, 300, 670, 650)
        self.role = role

        self.setWindowFlags(Qt.FramelessWindowHint)  # Remove window controls
        self.setAttribute(Qt.WA_TranslucentBackground)  # Transparent background
        self.oldPos = self.pos()
        self.radius = 18  # Corner radius
        self.borderWidth = 5  # Border thickness
        self.setWindowModality(Qt.ApplicationModal)  # Modal window blocking other windows
        self.client_list = []  # Список клиентов
        self.init_ui()
        center(self)
        self.load_clients()

    def remove_client_widget(self, client_id):
        """
        Удаляет виджет клиента по его ID.
        """
        for i in range(self.container_layout.count()):
            widget = self.container_layout.itemAt(i).widget()
            if widget:
                client_widget = widget.findChild(ClientWidget)
                if client_widget and client_widget.client_id == client_id:
                    widget.deleteLater()  # Удаляет виджет из контейнера
                    break

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
                background: white;
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
            client_widget = ClientWidget(client, self, self.role)

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

    def update_client_in_list(self, client_id, subscription_data):
        """
        Обновляет данные о клиенте в виджете списка клиентов.
        """
        for i in range(self.container_layout.count()):
            widget = self.container_layout.itemAt(i).widget()
            if widget:
                client_widget = widget.findChild(ClientWidget)
                if client_widget and client_widget.client_id == client_id:
                    client_widget.update_client_widget(subscription_data)

                    # Обновляем данные в client_list
                    for client in self.client_list:
                        if client['id'] == client_id:
                            client[
                                'subscription'] = f"Абонемент {subscription_data.get('start_date', 'неизвестно')} - {subscription_data.get('end_date', 'неизвестно')}" if subscription_data else "Абонемент отсутствует"
                            break
                    return

    def load_clients(self):
        """
        Загружает список клиентов из БД через WorkerThread.
        """
        print('a')

        def fetch_clients():
            print('b')
            query = """
            WITH nearest_slots AS (
            SELECT DISTINCT ON (ts.client) 
                   ts.client,
                   ts.start_time AS nearest_slot_start,
                   ts.end_time AS nearest_slot_end,
                   ts.trainer
            FROM training_slots ts
            WHERE ts.start_time >= NOW()
            ORDER BY ts.client, ts.start_time ASC
        ),
        latest_visit AS (
            SELECT DISTINCT ON (v.client) 
                   v.client,
                   v.in_gym
            FROM visit_fitness_room v
            ORDER BY v.client, v.time_start DESC
        )
        SELECT 
               c.client_id, 
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
                   WHEN lv.in_gym = TRUE THEN '● В зале'
                   ELSE '○ Вне зала'
               END AS status,
               COALESCE(TO_CHAR(ns.nearest_slot_start, 'DD.MM.YYYY HH24:MI'), 'Нет ближайших слотов') AS nearest_slot_start,
               COALESCE(TO_CHAR(ns.nearest_slot_end, 'DD.MM.YYYY HH24:MI'), '') AS nearest_slot_end
        FROM client c
        LEFT JOIN subscription s ON c.subscription = s.subscription_id
        LEFT JOIN nearest_slots ns ON c.client_id = ns.client
        LEFT JOIN trainer t ON ns.trainer = t.trainer_id
        LEFT JOIN latest_visit lv ON c.client_id = lv.client
        ORDER BY c.membership_start_date DESC;

            """
            result = execute_query(query)
            print(result)
            return result

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
        search_text = self.search_input.text().strip().lower()

        for i in range(self.container_layout.count()):
            widget = self.container_layout.itemAt(i).widget()
            if widget:
                client_widget = widget.findChild(ClientWidget)
                if client_widget:
                    # Преобразуем ID клиента в строку, чтобы избежать ошибки
                    client_id_str = str(client_widget.client_id)

                    # Фильтруем по имени и телефону
                    match = (
                            search_text in client_widget.name_label.text().lower() or
                            search_text in client_widget.parent_window.client_list[i]['phone'].lower() or
                            search_text in client_id_str
                    )
                    widget.setVisible(match)  # Скрываем/показываем виджет вместо удаления

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

    def show_client_profile(self, client_id):
        print(f"Открытие профиля клиента с ID: {client_id}")
        self.profile_window = ClientProfileWindow(client_id, self.role)
        self.profile_window.show()
        self.profile_window.raise_()
        print("Профиль клиента открыт.")

    def mousePressEvent(self, event):
        # Store initial position for window dragging
        self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        # Calculate delta and move the window
        delta = QPoint(event.globalPos() - self.oldPos)
        self.move(self.pos() + delta)
        self.oldPos = event.globalPos()
