from PyQt5.QtCore import Qt, QPoint, QRectF, QTime, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QColor
from PyQt5.QtWidgets import QLabel, QScrollArea, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFrame, QGridLayout, \
    QSizePolicy, QLineEdit, QMessageBox
from datetime import datetime

from database import execute_query
from hover_button import HoverButton
def some_function():
    from hover_button import HoverButton  # Импорт внутри функции
    button = HoverButton()

class ClientProfileWindow(QWidget):
    status_updated = pyqtSignal(str)

    def __init__(self, client_id, role):
        super().__init__()
        self.client_id = client_id
        self.role = role
        self.setWindowTitle("Профиль клиента")

        self.setGeometry(750, 750, 900, 560)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowModality(Qt.ApplicationModal)
        self.oldPos = self.pos()
        self.radius = 18
        self.borderWidth = 5
        from utils import center
        center(self)
        self.init_ui()

    def init_ui(self):
        # Основной вертикальный макет
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(5)

        # Верхняя часть окна: имя, фамилия, статус и кнопка закрытия
        top_layout = QHBoxLayout()
        top_layout.setSpacing(5)

        # Имя, фамилия и статус
        name_status_layout = QHBoxLayout()
        name_status_layout.setSpacing(5)
        name_status_layout.setContentsMargins(0, 0, 4, 0)
        name_status_layout.setAlignment(Qt.AlignLeft)
        self.name_label = QLabel("Имя Фамилия")
        self.name_label.setStyleSheet("font-family: 'Unbounded'; font-size: 25px; font-weight: bold;")
        self.status_label = QLabel("● В зале")
        self.status_label.setStyleSheet("font-family: 'Unbounded'; font-size: 20px; font-weight: bold; color: #05A9A3;")
        self.status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        name_status_layout.addWidget(self.name_label)
        name_status_layout.addWidget(self.status_label)
        name_status_layout.setSpacing(15)
        top_layout.addLayout(name_status_layout)

        # Кнопка закрытия
        close_button = HoverButton("X", 30, 30, 35, '#8F2D31', True, '#8F2D31', 'red', 5, 'red')
        close_button.clicked.connect(self.close)
        top_layout.addWidget(close_button, alignment=Qt.AlignRight)

        main_layout.addLayout(top_layout)

        # Основной горизонтальный макет для 2 столбцов
        horizontal_layout = QHBoxLayout()
        horizontal_layout.setSpacing(10)

        # Первый столбец (информация о клиенте)
        client_info_layout = QVBoxLayout()
        client_info_layout.setSpacing(5)
        client_info_layout.setAlignment(Qt.AlignTop)

        # Телефон и дата начала
        phone_date_layout = QHBoxLayout()
        phone_date_layout.setSpacing(5)
        phone_date_layout.setContentsMargins(0, 0, 0, 10)
        phone_date_layout.setAlignment(Qt.AlignLeft)
        self.phone_label = QLabel("+7xxxxxxxxxx")
        self.phone_label.setStyleSheet("font-family: 'Unbounded'; font-size: 20px; font-weight: bold; color: black;")
        self.start_date_label = QLabel("С 09.10.23")
        self.start_date_label.setStyleSheet(
            "font-family: 'Unbounded'; font-size: 17px; font-weight: bold; color: #05A9A3;")
        self.start_date_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        phone_date_layout.addWidget(self.phone_label)
        phone_date_layout.addWidget(self.start_date_label)
        client_info_layout.addLayout(phone_date_layout)

        # Абонемент
        self.subscription_label = QLabel("Абонемент 13.09.24 - 13.10.24\nСтандарт, 8 занятий (4 из 8)")
        self.subscription_label.setStyleSheet(
            "font-family: 'Unbounded'; font-size: 21px; font-weight: bold; color: #05A9A3;")
        self.subscription_label.setWordWrap(True)
        self.subscription_label.setContentsMargins(0, 0, 0, 10)
        client_info_layout.addWidget(self.subscription_label)

        # Закрепленные тренеры
        self.trainer_label = QLabel("Нет закрепленных тренеров")
        self.trainer_label.setStyleSheet("font-family: 'Unbounded'; font-size: 21px; font-weight: bold; color: black;")
        client_info_layout.addWidget(self.trainer_label)

        horizontal_layout.addLayout(client_info_layout)

        # Второй столбец (История посещений и добавление)
        self.history_frame = QFrame()
        self.history_frame.setObjectName('history_frame')
        self.history_frame.setStyleSheet("""
            QFrame#history_frame {
                border: 5px solid #75A9A7;
                border-radius: 14px;
                background-color: white;
                padding: 5px;
            }
        """)
        self.history_layout = QVBoxLayout(self.history_frame)
        self.history_layout.setSpacing(0)
        self.history_layout.setContentsMargins(0, 0, 0, 0)

        history_title = QLabel("История посещений")
        history_title.setStyleSheet("""
            QLabel {
                font-family: 'Unbounded';
                font-size: 20px;
                font-weight: bold;
                color: black;
            }
        """)
        self.history_layout.addWidget(history_title, alignment=Qt.AlignTop | Qt.AlignHCenter)

        self.add_visit_button = HoverButton("Добавить", 350, 60, 20, '#45DB77', True, '#45DB77', '#4BFF87', 8,
                                            '#4BFF87', 3, 700)
        self.add_visit_button.clicked.connect(self.show_add_visit_widget)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("border: 0px; padding: 0px; margin: 0px;")
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        if self.role == "Управляющий":
            self.scroll_area.setFixedHeight(460)
        else:
            self.scroll_area.setFixedHeight(410)
        self.scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: 0px;
                background-color: white;
            }}
            QScrollBar:vertical {{
                width: 8px;
                border: none;
                background: white;
            }}
            QScrollBar::handle:vertical {{
                background: #75A9A7;
                border-radius: 4px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                border: none;
            }}
            QScrollBar:vertical:disabled {{
                background: white;
            }}
        """)

        # Контейнер для записей о посещениях
        self.container_widget = QWidget()
        self.container_widget.setObjectName('scroll_content')
        self.container_widget.setStyleSheet("border: 0px; padding: 0px; margin: 0px;")
        self.container_layout = QVBoxLayout(self.container_widget)
        self.container_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        self.container_layout.setSpacing(10)
        self.container_layout.setContentsMargins(0, 0, 5, 0)
        self.container_layout.addWidget(self.add_visit_button, alignment=Qt.AlignTop | Qt.AlignHCenter)

        self.scroll_area.setWidget(self.container_widget)
        self.history_layout.addWidget(self.scroll_area)

        horizontal_layout.addWidget(self.history_frame)

        horizontal_layout.setStretch(0, 55)
        horizontal_layout.setStretch(1, 45)

        main_layout.addLayout(horizontal_layout)

        self.setLayout(main_layout)

        self.load_client_data()

    def load_client_data(self):
        # Загружаем данные о клиенте
        query = """
        WITH client_data AS (
        SELECT 
            c.client_id,
            c.surname || ' ' || c.first_name AS name,
            c.phone_number AS phone,
            c.membership_start_date AS start_date,
            s.tariff AS subscription_type,
            s.valid_since AS subscription_start,
            s.valid_until AS subscription_end,
            s.visit_ids AS visits,
            t.surname || ' ' || t.first_name AS trainer_name,
            v.in_gym AS status,
            ts.start_time AS next_training_start,
            ts.end_time AS next_training_end,
            tr.surname || ' ' || tr.first_name AS next_trainer_name,
            s.is_valid -- Добавляем столбец is_valid
        FROM client c
        LEFT JOIN subscription s ON c.subscription = s.subscription_id
        LEFT JOIN trainer t ON c.client_id = t.trainer_id
        LEFT JOIN visit_fitness_room v ON c.client_id = v.client
        LEFT JOIN LATERAL (
            SELECT ts.start_time, ts.end_time, ts.trainer
            FROM training_slots ts
            WHERE ts.client = c.client_id
              AND ts.start_time > NOW()
            ORDER BY ts.start_time ASC
            LIMIT 1
        ) ts ON true
        LEFT JOIN trainer tr ON ts.trainer = tr.trainer_id
        WHERE c.client_id = %s
    )
    SELECT 
        client_id,
        name,
        phone,
        TO_CHAR(start_date, 'DD.MM.YY') AS start_date,
        subscription_type,
        TO_CHAR(subscription_start, 'DD.MM.YY') || ' - ' || TO_CHAR(subscription_end, 'DD.MM.YY') AS subscription_period,
        COALESCE(array_length(visits, 1), 0) AS visits_count,
        trainer_name,
        CASE 
            WHEN status = TRUE THEN '● В зале'
            ELSE '○ Вне зала'
        END AS status,
        TO_CHAR(next_training_start, 'DD.MM.YY HH24:MI') AS next_training_start,
        TO_CHAR(next_training_end, 'DD.MM.YY HH24:MI') AS next_training_end,
        next_trainer_name,
        is_valid 
    FROM client_data;
        """
        result = execute_query(query, (self.client_id,))
        if result:
            client_data = result[0]
            is_valid = client_data[12]  # Индекс колонки is_valid

            # Проверяем наличие незавершённого посещения
            active_visit_query = """
                    SELECT time_start, time_end, in_gym
                    FROM visit_fitness_room
                    WHERE client = %s AND in_gym = TRUE AND time_end IS NULL
                    LIMIT 1;
                    """
            active_visit_result = execute_query(active_visit_query, (self.client_id,))
            has_active_visit = bool(active_visit_result)  # True, если есть активное посещение без time_end

            if not is_valid:
                # Абонемент не активен
                self.add_visit_button.setEnabled(False)
                self.add_visit_button.setText("Абонемент не активен")
                self.add_visit_button.set_border_color("#FF0000")
                self.add_visit_button.set_font_color("#FF0000")
                self.add_visit_button.set_hover_border_color("#FF0000")
                self.add_visit_button.set_hover_text_color("#FF0000")
            else:
                if has_active_visit:
                    # Если клиент находится в зале без завершённого посещения
                    self.add_visit_button.setEnabled(True)
                    self.add_visit_button.setText("Закончить посещение")
                    self.add_visit_button.set_border_color("#FFA500")
                    self.add_visit_button.set_font_color("#FFA500")
                    self.add_visit_button.set_hover_border_color("#FFB347")
                    self.add_visit_button.set_hover_text_color("#FFB347")
                    # Переназначаем действие кнопки на завершение посещения
                    self.add_visit_button.clicked.disconnect()
                    self.add_visit_button.clicked.connect(self.finish_visit)
                else:
                    # Клиент не в зале или посещение завершено
                    self.add_visit_button.setEnabled(True)
                    self.add_visit_button.setText("Добавить посещение")
                    self.add_visit_button.set_border_color("#45DB77")
                    self.add_visit_button.set_font_color("#45DB77")
                    self.add_visit_button.set_hover_border_color("#4BFF87")
                    self.add_visit_button.set_hover_text_color("#4BFF87")
                    # Переназначаем действие кнопки на добавление нового посещения
                    self.add_visit_button.clicked.disconnect()
                    self.add_visit_button.clicked.connect(self.show_add_visit_widget)

            self.update_ui_with_client_data(result[0])

        visit_query = """
            SELECT 
            v.visit_id,  -- Добавляем visit_id
            TO_CHAR(v.time_start, 'DD.MM.YY') AS date,
            TO_CHAR(v.time_start, 'HH24:MI') || ' - ' || TO_CHAR(v.time_end, 'HH24:MI') AS time,
            CASE 
                WHEN s.tariff IS NOT NULL THEN 'По абонементу'
                ELSE 'Разовое посещение'
            END AS type,
            CASE 
                WHEN s.tariff IS NOT NULL AND s.tariff != 'one_time' THEN 
                    TO_CHAR(s.valid_since, 'DD.MM.YY') || ' - ' || TO_CHAR(s.valid_until, 'DD.MM.YY')
                ELSE ''
            END AS period
            FROM visit_fitness_room v
            LEFT JOIN client c ON v.client = c.client_id
            LEFT JOIN subscription s ON c.subscription = s.subscription_id
            WHERE v.client = %s
            AND v.time_end IS NOT NULL
            ORDER BY v.time_start DESC;
        """

        visit_results = execute_query(visit_query, (self.client_id,))

        # Очищаем старые записи о посещениях перед добавлением новых
        for i in reversed(range(self.container_layout.count())):
            item = self.container_layout.itemAt(i)
            widget = item.widget()
            # Удаляем только записи посещений, не затрагивая кнопку "Добавить"
            if widget and widget is not self.add_visit_button:
                widget.setParent(None)
                widget.deleteLater()

        if visit_results:
            self.existing_visits = [{
                'visit_id': visit[0],  # Добавляем visit_id
                'date': visit[1],
                'time': visit[2],
                'type': visit[3],
                'period': visit[4] if visit[3] == "По абонементу" else ""
            } for visit in visit_results]

            self.container_layout.insertWidget(0, self.add_visit_button)
            for visit in self.existing_visits:
                visit_widget = self.create_visit_widget(visit)
                self.container_layout.insertWidget(1, visit_widget)
        else:
            self.existing_visits = []

    def finish_visit(self):
        # Запрос для получения текущего активного посещения
        query = """
        SELECT visit_id, time_start
        FROM visit_fitness_room
        WHERE client = %s AND in_gym = TRUE AND time_end IS NULL
        LIMIT 1;
        """
        result = execute_query(query, (self.client_id,))

        if result:
            visit_id, time_start = result[0]

            # Устанавливаем максимальное допустимое время завершения посещения (22:00 дня начала посещения)
            max_end_time = time_start.replace(hour=22, minute=0, second=0, microsecond=0)

            # Если текущее время превышает 22:00 дня начала посещения, устанавливаем конец на max_end_time
            current_time = datetime.now()
            if current_time > max_end_time:
                time_end = max_end_time
            else:
                time_end = current_time

            # Обновляем запись посещения в БД
            update_query = """
            UPDATE visit_fitness_room
            SET time_end = %s, in_gym = FALSE
            WHERE visit_id = %s
            RETURNING time_start, time_end;
            """
            update_result = execute_query(update_query, (time_end, visit_id))

            if update_result:
                self.status_updated.emit("○ Вне зала")
                QMessageBox.information(self, "Успех", "Посещение успешно завершено.")
                self.load_client_data()

            else:
                # Ошибка при обновлении
                QMessageBox.warning(self, "Ошибка", "Не удалось завершить посещение.")
        else:
            # Если нет активного посещения
            QMessageBox.warning(self, "Ошибка", "Активное посещение не найдено.")

    def update_button_for_add_visit(self):
        """
        Настраивает кнопку для добавления нового посещения.
        """
        self.add_visit_button.setText("Добавить")
        self.add_visit_button.set_border_color("#45DB77")
        self.add_visit_button.set_font_color("#45DB77")
        self.add_visit_button.set_hover_border_color("#4BFF87")
        self.add_visit_button.set_hover_text_color("#4BFF87")
        self.add_visit_button.clicked.disconnect()
        self.add_visit_button.clicked.connect(self.show_add_visit_widget)

    def update_button_for_finish_visit(self):
        """
        Настраивает кнопку для завершения текущего посещения.
        """
        self.add_visit_button.setText("Закончить посещение")
        self.add_visit_button.set_border_color("#FF0000")
        self.add_visit_button.set_font_color("#FF0000")
        self.add_visit_button.set_hover_border_color("#FF0000")
        self.add_visit_button.set_hover_text_color("#FF0000")
        self.add_visit_button.clicked.disconnect()
        self.add_visit_button.clicked.connect(self.finish_visit)

    def parse_subscription_type(self, subscription_type, visits_count):
        if not subscription_type:
            return "Абонемент отсутствует"

        parts = subscription_type.split('_')

        # Определяем тип тарифа
        if subscription_type == "one_time":
            return "Разовое посещение"

        tariff_type = None
        if "mrn" in parts:
            tariff_type = "Утренний"
        elif "evn" in parts:
            tariff_type = "Вечерний"
        elif "unlim" == parts[1]:  # Проверяем второй unlim (безлимит по времени)
            tariff_type = "Безлимит"
        else:
            tariff_type = "Одноразовый"

        # Если тариф ограничен количеством посещений
        if parts[0].isdigit() and "unlim" != parts[0]:
            total_visits = int(parts[0])
            return f"{tariff_type}, {visits_count} из {total_visits} занятий"
        else:
            return f"{tariff_type}, Безлимитные занятия"

    def update_ui_with_client_data(self, client_data):
        self.name_label.setText(client_data[1])
        status = client_data[8]
        if status == '● В зале':
            status_html = '<span style="font-size: 28px;">●</span> <span style="vertical-align: middle;">В зале</span>'
        else:
            status_html = '<span style="font-size: 28px;">○</span> <span>Вне зала</span>'
        self.status_label.setText(status_html)
        self.phone_label.setText(client_data[2])
        self.start_date_label.setText(f"С {client_data[3]}")

        subscription_type = client_data[4]
        subscription_period = client_data[5]
        visits_count = client_data[6]

        if subscription_type is not None and subscription_period is not None:
            # Получаем количество посещений по текущему абонементу
            current_subscription_visits_query = """
            SELECT COUNT(*)
            FROM visit_fitness_room v
            WHERE v.client = %s
              AND v.time_start >= (SELECT valid_since FROM subscription WHERE subscription_id = (SELECT subscription FROM client WHERE client_id = %s))
              AND v.time_end <= (SELECT valid_until FROM subscription WHERE subscription_id = (SELECT subscription FROM client WHERE client_id = %s));
            """
            current_subscription_visits = \
                execute_query(current_subscription_visits_query, (self.client_id, self.client_id, self.client_id),
                              fetch_one=True)[0]

            tariff_description = self.parse_subscription_type(subscription_type, current_subscription_visits)
            if subscription_type == "one_time":
                self.subscription_label.setText("Разовое посещение")
            else:
                self.subscription_label.setText(
                    f"Абонемент {subscription_period}\n{tariff_description}"
                )

            # Проверка заморозки
            freeze_query = """
            SELECT frozen_from, frozen_until
            FROM subscription
            WHERE subscription_id = (
                SELECT subscription FROM client WHERE client_id = %s
            );
            """
            freeze_result = execute_query(freeze_query, (self.client_id,))
            if freeze_result and freeze_result[0][0] and freeze_result[0][1]:
                frozen_from, frozen_until = freeze_result[0]
                current_date = datetime.now().date()
                if frozen_from <= current_date <= frozen_until:
                    self.add_visit_button.setText("Абонемент заморожен")
                    self.add_visit_button.set_border_color("#FFA500")
                    self.add_visit_button.set_font_color("#FFA500")
                    self.add_visit_button.set_hover_border_color("#FFA500")
                    self.add_visit_button.set_hover_text_color("#FFA500")

                    self.add_visit_button.setEnabled(False)
        else:
            self.subscription_label.setText("Абонемент отсутствует")

        trainer_name = client_data[7]
        if trainer_name:
            self.trainer_label.setText(trainer_name)
        else:
            self.trainer_label.setText("Нет закрепленных тренеров")

        next_training_start = client_data[9]
        next_training_end = client_data[10]
        next_trainer_name = client_data[11]

        if next_training_start and next_trainer_name:
            self.trainer_label.setText(f"{next_trainer_name}\nБлижайшее занятие: {next_training_start}")

    def create_visit_widget(self, visit):
        visit_widget = QWidget()
        visit_widget.setObjectName('visit_widget')
        visit_widget.setFixedHeight(60)  # Фиксированная высота

        hbox = QHBoxLayout(visit_widget)
        hbox.setContentsMargins(10, 5, 10, 5)
        hbox.setSpacing(15)

        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.setAlignment(Qt.AlignCenter)
        left_layout.setSpacing(2)
        left_layout.setContentsMargins(0, 0, 0, 0)

        date_label = QLabel(visit['date'])
        date_label.setAlignment(Qt.AlignCenter)
        date_label.setWordWrap(True)
        time_label = QLabel(visit['time'])
        time_label.setAlignment(Qt.AlignCenter)
        time_label.setWordWrap(True)

        left_layout.addWidget(date_label)
        left_layout.addWidget(time_label)

        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setAlignment(Qt.AlignCenter)
        right_layout.setSpacing(2)
        right_layout.setContentsMargins(0, 0, 0, 0)

        type_label = QLabel(visit['type'])
        type_label.setAlignment(Qt.AlignCenter)
        type_label.setWordWrap(True)
        right_layout.addWidget(type_label)

        if visit['period']:
            period_label = QLabel(visit['period'])
            period_label.setAlignment(Qt.AlignCenter)
            period_label.setWordWrap(True)
            right_layout.addWidget(period_label)

        left_column.setMaximumWidth(int(visit_widget.width() / 2))
        right_column.setMaximumWidth(int(visit_widget.width() / 2))

        hbox.addWidget(left_column, 1)
        hbox.addWidget(right_column, 1)
        if self.role == "Управляющий":
            del_btn = HoverButton("X", 30, 30, 55, '#8F2D31', True, '#8F2D31', 'red', 8, 'red')
            hbox.addWidget(del_btn, 1)
            del_btn.clicked.connect(lambda _, v=visit: self.delete_visit_by_id(v))

        visit_widget.setStyleSheet("""
            QWidget#visit_widget {
                background: white;
                border: 2px solid #75A9A7;
                border-radius: 8px;
            }
            QLabel {
                font-family: 'Unbounded';
                font-size: 14px;
                color: black;
            }
            QLabel[accessibleName="time"] {
                color: #666;
                font-size: 13px;
            }
            QLabel[accessibleName="period"] {
                color: #75A9A7;
                font-size: 13px;
            }
        """)
        type_label.setStyleSheet("color: #05A9A3; font-weight: bold;")
        date_label.setStyleSheet("color: black; font-weight: bold;")
        if visit['period']:
            period_label.setAccessibleName("period")
        time_label.setAccessibleName("time")

        type_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        if visit['period']:
            period_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        date_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        time_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        if self.role == "Управляющий":
            visit_widget.setFixedHeight(70)
            visit_widget.setFixedWidth(360)

        return visit_widget

    def delete_visit_by_id(self, visit_id):
        print(visit_id["visit_id"])
        delete_query = """
        DELETE FROM visit_fitness_room
        WHERE visit_id = %s;
        """
        execute_query(delete_query, (visit_id["visit_id"],))

        # 7. Удаляем виджет посещения из контейнера
        for i in range(self.container_layout.count()):
            item = self.container_layout.itemAt(i)
            widget = item.widget()
            if widget and isinstance(widget, QWidget) and widget.findChild(QLabel, "visit_id"):
                # Здесь мы проверяем, есть ли у виджета ID посещения, чтобы удалить нужный
                if widget.findChild(QLabel, "visit_id").text() == str(visit_id):
                    widget.setParent(None)
                    widget.deleteLater()
                    break  # Найден и удален виджет, выходим из цикла

        QMessageBox.information(self, "Удаление посещения", "Посещение успешно удалено.")
        self.load_client_data()

    def show_add_visit_widget(self):
        add_visit_widget = QWidget()

        add_visit_widget.setStyleSheet("background: white; border: 2px solid #75A9A7; border-radius: 8px;")
        layout = QHBoxLayout(add_visit_widget)

        self.start_time_edit = QLineEdit()
        self.start_time_edit.setPlaceholderText("Начало (HH:MM)")
        self.start_time_edit.setInputMask("99:99")

        self.end_time_edit = QLineEdit()
        self.end_time_edit.setPlaceholderText("Конец (HH:MM)")
        self.end_time_edit.setInputMask("99:99")

        confirm_button = HoverButton("✓", 30, 30, 35, '#45DB77', True, '#45DB77', '#4BFF87', 8, '#4BFF87')
        confirm_button.clicked.connect(self.add_visit)

        cancel_button = HoverButton("X", 30, 30, 35, '#8F2D31', True, '#8F2D31', 'red', 8, 'red')
        cancel_button.clicked.connect(self.cancel_add_visit)

        layout.addWidget(self.start_time_edit)
        layout.addWidget(self.end_time_edit)
        layout.addWidget(confirm_button)
        layout.addWidget(cancel_button)

        # "Добавить" на виджет с полями ввода
        self.add_visit_button.setParent(None)
        self.container_layout.insertWidget(0, add_visit_widget)
        self.add_visit_widget = add_visit_widget
        add_visit_widget.setFixedHeight(60)
        add_visit_widget.setFixedWidth(350)

    def cancel_add_visit(self):
        # Удаляем виджет с полями ввода
        self.add_visit_widget.setParent(None)
        # Возвращаем кнопку "Добавить" на место
        self.container_layout.insertWidget(0, self.add_visit_button)

    def add_visit(self):
        start_time = self.start_time_edit.text()
        end_time = self.end_time_edit.text()

        if self.validate_visit_time(start_time, end_time):
            # Добавляем текущую дату к времени
            current_date = datetime.now().strftime("%Y-%m-%d")
            start_timestamp = f"{current_date} {start_time}"
            end_timestamp = f"{current_date} {end_time}"
            start_datetime = datetime.strptime(start_timestamp, "%Y-%m-%d %H:%M")
            end_datetime = datetime.strptime(end_timestamp, "%Y-%m-%d %H:%M")
            current_datetime = datetime.now()

            # Добавляем посещение в базу данных
            in_gym = start_datetime <= current_datetime <= end_datetime

            # посещение в базу данных
            insert_query = """
                    INSERT INTO visit_fitness_room (client, time_start, time_end, in_gym)
                    VALUES (%s, %s, %s, %s)
                    RETURNING visit_id;
                    """
            visit_id = \
            execute_query(insert_query, (self.client_id, start_timestamp, end_timestamp, in_gym), fetch_one=True)[0]

            # тип абонемента
            subscription_type_query = """
            SELECT tariff
            FROM subscription
            WHERE subscription_id = (
                SELECT subscription FROM client WHERE client_id = %s
            );
            """
            subscription_type = execute_query(subscription_type_query, (self.client_id,), fetch_one=True)[0]

            update_subscription_query = """
            UPDATE subscription
            SET visit_ids = array_append(visit_ids, %s)
            WHERE subscription_id = (
                SELECT subscription FROM client WHERE client_id = %s
            );
            """
            execute_query(update_subscription_query, (visit_id, self.client_id))

            # виджет для нового посещения
            new_visit = {
                'date': datetime.now().strftime("%d.%m.%y"),
                'time': f"{start_time} - {end_time}",
                'type': "По абонементу",
                'period': self.subscription_label.text().split("Абонемент ")[1].split("\n")[0]
            }
            visit_widget = self.create_visit_widget(new_visit)

            self.existing_visits.append(new_visit)

            self.add_visit_widget.setParent(None)

            self.container_layout.insertWidget(1, visit_widget)

            self.container_layout.insertWidget(0, self.add_visit_button)

            # счетчик посещений (если абонемент не безлимитный)
            if "8" in subscription_type or "12" in subscription_type:
                self.update_visit_count()
        else:
            print("Ошибка: время посещения недопустимо.")



    def update_subscription_label(self, subscription_id, current_visits_count):
        """
        Обновляет текст абонемента, включая информацию о оставшихся посещениях.
        """
        # Получаем тариф
        query = """
        SELECT tariff
        FROM subscription
        WHERE subscription_id = %s;
        """
        tariff = execute_query(query, (subscription_id,), fetch_one=True)[0]

        if "8" in tariff or "12" in tariff:
            total_visits = int(tariff.split('_')[0])  # Получаем общее количество посещений (8 или 12)
            visits_left = total_visits - current_visits_count  # Оставшиеся посещения
            tariff_description = f"{visits_left} из {total_visits} занятий"
        else:
            tariff_description = "Безлимитный"

        subscription_period = self.subscription_label.text().split("\n")[0].split("Абонемент ")[1]
        self.subscription_label.setText(f"Абонемент {subscription_period}\n{tariff_description}")

    def validate_visit_time(self, start_time, end_time):
        try:
            start_qtime = QTime.fromString(start_time, "HH:mm")
            end_qtime = QTime.fromString(end_time, "HH:mm")

            if not start_qtime.isValid() or not end_qtime.isValid():
                QMessageBox.warning(self, "Ошибка", "Время введено некорректно.")
                return False

            if start_qtime >= end_qtime:
                QMessageBox.warning(self, "Ошибка", "Время начала должно быть меньше времени конца.")
                return False

            # Проверка на пересечение с другими посещениями
            for visit in self.existing_visits:
                existing_time = visit['time'].split(" - ")
                existing_start = QTime.fromString(existing_time[0], "HH:mm")
                existing_end = QTime.fromString(existing_time[1], "HH:mm")
                if (start_qtime < existing_end and end_qtime > existing_start):
                    QMessageBox.warning(self, "Ошибка", "Время посещения пересекается с другим посещением.")
                    return False

            # Проверка на одно посещение в день для ограниченных абонементов
            subscription_type = self.get_client_tariff()
            if "8" in subscription_type or "12" in subscription_type:
                current_date = datetime.now().strftime("%Y-%m-%d")
                check_daily_visit_query = """
                SELECT COUNT(*)
                FROM visit_fitness_room
                WHERE client = %s
                  AND DATE(time_start) = %s;
                """
                daily_visits_count = \
                    execute_query(check_daily_visit_query, (self.client_id, current_date), fetch_one=True)[0]
                if daily_visits_count > 0:
                    QMessageBox.warning(self, "Ошибка", "Допустимо не более одного занятия в день.")
                    return False

            # Проверка на соответствие тарифу
            if not self.is_time_within_tariff(subscription_type, start_qtime, end_qtime):
                QMessageBox.warning(self, "Ошибка", f"Время посещения не соответствует тарифу ({subscription_type}).")
                return False

            # Проверка на время работы зала
            if start_qtime < QTime(8, 0) or end_qtime > QTime(22, 0):
                QMessageBox.warning(self, "Ошибка", "Время посещения выходит за рамки работы зала.")
                return False

            return True
        except Exception as e:
            print(f"Ошибка при валидации времени: {e}")
            return False

    def get_client_tariff(self):
        """
        Получает тариф клиента из базы данных.
        :return: Название тарифа (например, "12_mrn_mnth").
        """
        query = """
        SELECT s.tariff
        FROM client c
        LEFT JOIN subscription s ON c.subscription = s.subscription_id
        WHERE c.client_id = %s;
        """
        result = execute_query(query, (self.client_id,))
        if result:
            return result[0][0]
        return "unlim_unlim_mnth"  # По умолчанию безлимитный тариф

    def is_time_within_tariff(self, tariff, start_time, end_time):
        """
        Проверяет, находится ли время в пределах допустимого для указанного тарифа.
        :param tariff: Название тарифа (например, "12_mrn_mnth").
        :param start_time: Время начала посещения (QTime).
        :param end_time: Время окончания посещения (QTime).
        :return: True, если время допустимо, иначе False.
        """
        if "mrn" in tariff:  # Утренний тариф
            return start_time < QTime(16, 0) and end_time <= QTime(16, 0)
        elif "evn" in tariff:  # Вечерний тариф
            return start_time >= QTime(16, 0) and end_time > QTime(16, 0)
        elif "unlim" in tariff:  # Безлимитный тариф
            return True
        else:
            return False

    def update_visit_count(self):
        """
        Обновляет счетчик посещений и отключает кнопку добавления, если количество посещений достигло максимума.
        """
        query = """
        SELECT s.tariff, array_length(s.visit_ids, 1) AS visits_count
        FROM client c
        LEFT JOIN subscription s ON c.subscription = s.subscription_id
        WHERE c.client_id = %s;
        """
        result = execute_query(query, (self.client_id,))
        if result:
            tariff, visits_count = result[0]
            if tariff and tariff.split('_')[0].isdigit():
                total_visits = int(tariff.split('_')[0])
                if visits_count >= total_visits:
                    self.add_visit_button.setEnabled(False)
                    self.add_visit_button.setText("Абонемент заморожен")
                    self.add_visit_button.set_border_color("#FFA500")
                    self.add_visit_button.set_font_color("#FFA500")
                    self.add_visit_button.set_hover_border_color("#FFA500")
                    self.add_visit_button.set_hover_text_color("#FFA500")
                    self.add_visit_button.setText("Лимит посещений исчерпан")
                subscription_period = self.subscription_label.text().split("\n")[0].split("Абонемент ")[1]
                tariff_description = self.parse_subscription_type(tariff, visits_count)
                self.subscription_label.setText(
                    f"Абонемент {subscription_period}\n{tariff_description}"
                )

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
