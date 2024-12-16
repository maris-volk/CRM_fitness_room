import calendar
import datetime
import locale
import logging
from functools import partial

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtChart import QChartView, QBarSeries, QBarSet, QChart, QBarCategoryAxis, QValueAxis
from PyQt5.QtCore import QTimer, Qt, QMargins, pyqtSignal, QThread, QSize
from PyQt5.QtGui import QColor, QPainter, QFont, QBrush, QIcon, QPixmap
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QStackedWidget, QGridLayout, \
    QSizePolicy, QScrollArea, QMessageBox

from add_visitor_window import AddVisitorWindow
from chart import ChartWidget
from database import get_active_visitors, get_duty_trainers, count_visitors_in_gym, check_visitor_in_gym, \
    end_attendance, \
    start_attendance, execute_query
from hover_button import HoverButton, TrainerButton
from search_client import ClientSearchWindow
from utils import scan_card, WorkerThread, ResizablePhoto, FillPhoto
from subscription import SubscriptionWidget, SelectionGroupWidget

logger = logging.getLogger(__name__)


class MainWindow(QWidget):
    def __init__(self, current_user_id):
        super().__init__()
        self.current_user_id = current_user_id

        # Установка локали
        try:
            import locale
            locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
        except locale.Error:
            logger.warning("Локаль 'ru_RU.UTF-8' не доступна. Используется стандартная локаль.")
            import locale
            locale.setlocale(locale.LC_TIME, '')

        self.setWindowTitle("Fitness Gym Attendance Tracker")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet("background-color: white;")

        # Сразу загружаем данные об админе в конструкторе
        self.load_admin_data()

        self.initUI()

        # Таймер для регулярного обновления данных
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.fetch_and_update_data)
        self.timer.start(10000)  # обновление каждые 10 секунд

        # Первоначальная загрузка данных
        self.fetch_and_update_data()

    def load_admin_data(self):
        """
        Синхронно загружает данные об администраторе из БД.
        """
        query = """
            SELECT
                u.username,
                a.surname,
                a.first_name,
                a.patronymic,
                a.photo,
                u.role
            FROM
                public.users u
            JOIN
                public.administrators a ON u.user_id = a.user_id
            WHERE
                u.user_id = %s;
        """
        params = (self.current_user_id,)
        result = execute_query(query, params)
        if result and len(result) > 0:
            username, surname, first_name, patronymic, photo, role = result[0]
            full_name = f"{surname} {first_name}"

            # Определение роли
            if role == 'managing_director':
                display_role = "Управляющий"
            else:
                display_role = "Администратор"

            self.admin_full_name = full_name
            self.admin_role = display_role
            self.admin_photo_data = photo
        else:
            logger.error("Администратор не найден в базе данных")
            self.admin_full_name = "Администратор не найден"
            self.admin_role = ""
            self.admin_photo_data = None

    def fetch_data(self):
        try:
            total_visitors = get_active_visitors()
            visitors_in_gym = count_visitors_in_gym()
            duty_trainers = get_duty_trainers()
            return (total_visitors, visitors_in_gym, duty_trainers)
        except Exception as e:
            logger.error(f"Ошибка при получении данных: {e}")
            return None

    def fetch_and_update_data(self):
        self.fetch_data_thread = WorkerThread(self.fetch_data)
        self.fetch_data_thread.result_signal.connect(self.update_data)
        self.fetch_data_thread.start()

    def update_data(self, result):
        if result is None:
            logger.error("Нет данных для обновления")
            return
        total_visitors, visitors_in_gym, duty_trainers = result

        self.visitors_label.setText(f"{total_visitors} посетителей\n{visitors_in_gym} в зале")
        self.trainers_label.setText(f"{len(duty_trainers)} тренеров\n{len(duty_trainers)} на смене")
        self.update_duty_trainers_ui(duty_trainers)

    def show_add_visitor_window(self):
        if not hasattr(self, 'add_visitor_window') or not self.add_visitor_window.isVisible():
            self.add_visitor_window = AddVisitorWindow()
            self.add_visitor_window.show()
            self.add_visitor_window.raise_()

    def show_view_visitors_window(self):
        if not hasattr(self, 'view_visitors_window') or not self.view_visitors_window.isVisible():
            self.view_visitors_window = ClientSearchWindow()
            self.view_visitors_window.show()
            self.view_visitors_window.raise_()

    def scan_card_for_attendance(self):
        self.scan_thread = WorkerThread(self._scan_card_and_update_attendance)
        self.scan_thread.result_signal.connect(self.handle_scan_result)
        self.scan_thread.start()

    def _scan_card_and_update_attendance(self):
        card_number = scan_card()
        if card_number:
            attendance_data = check_visitor_in_gym(card_number)
            return (card_number, attendance_data)
        return None

    def handle_scan_result(self, result):
        if result is None:
            logger.error("Ошибка при сканировании карты или получении данных")
            QMessageBox.critical(self, "Ошибка", "Произошла ошибка при сканировании карты.")
            return

        card_number, attendance_data = result
        if attendance_data:
            visit_id, in_gym, time_start, time_end = attendance_data
            if in_gym:
                end_attendance(visit_id)
                logger.info(f"Посещение ID {visit_id} завершено.")
                QMessageBox.information(self, "Статус посещения", "Посещение завершено.")
            else:
                start_attendance(visit_id)
                logger.info(f"Посещение клиента ID {visit_id} начато.")
                QMessageBox.information(self, "Статус посещения", "Посещение начато.")
            self.fetch_and_update_data()
        else:
            logger.warning("Посетитель не найден или произошла ошибка при проверке.")
            QMessageBox.warning(self, "Проблема", "Посетитель не найден или произошла ошибка.")

    def initUI(self):
        main_layout = QVBoxLayout(self)
        self.stack = QStackedWidget()

        self.main_page = QWidget()
        self.init_main_page()
        self.stack.addWidget(self.main_page)

        self.schedule_page = QWidget()
        self.init_schedule_page()
        self.stack.addWidget(self.schedule_page)

        # Верхняя панель
        top_panel = QFrame()
        top_panel.setObjectName("top_panel")
        top_panel.setStyleSheet("""
        QFrame#top_panel{
            background-color: white;
            border-bottom: 3px solid #628F8D;
            height: 131px;
        }
        QLabel{
            font-family: 'Unbounded';
            font-size: 22px;
            border: none;
            weight:400;
            }
        """)
        top_layout = QGridLayout(top_panel)

        self.visitors_label = QLabel()
        self.trainers_label = QLabel()
        self.visitors_label.setText("0 посетителей\n0 в зале")
        self.trainers_label.setText("0 тренеров\n0 на смене")

        schedule_label = QLabel("Расписание тренеров")
        schedule_label.setCursor(Qt.PointingHandCursor)
        schedule_label.mousePressEvent = lambda event: self.switch_to_page(self.schedule_page)

        profile_button = QPushButton()
        profile_button.setFixedSize(51, 51)
        profile_button.setIcon(QIcon("Group.png"))
        profile_button.setIconSize(QSize(51, 51))
        profile_button.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
            }
            QPushButton:pressed {
                background-color: lightgray; 
            }
        """)

        top_layout.addWidget(self.visitors_label, 0, 0, Qt.AlignLeft)
        top_layout.addWidget(self.trainers_label, 0, 1, Qt.AlignCenter)
        top_layout.addWidget(schedule_label, 0, 2, Qt.AlignCenter)
        top_layout.addWidget(profile_button, 0, 3, Qt.AlignRight)
        top_layout.setContentsMargins(130, 0, 130, 20)

        label_style = """
                   font-family: 'Unbounded';
                   font-size: 22px;
                   border: none;
                   weight:400;
               """
        for widget in top_layout.children():
            if isinstance(widget, QLabel):
                widget.setStyleSheet(label_style)

        main_layout.addWidget(top_panel)
        main_layout.addWidget(self.stack)

    def init_main_page(self):
        layout = QVBoxLayout(self.main_page)

        grid_layout = QGridLayout()
        grid_layout.setContentsMargins(50, 20, 50, 20)
        grid_layout.setSpacing(20)
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 3)  # Центральная колонка получает больше пространства
        grid_layout.setColumnStretch(2, 1)

        # Левая панель
        left_panel = QVBoxLayout()
        left_panel.setSpacing(30)
        new_visitor_button = HoverButton("Новый посетитель")
        new_visitor_button.clicked.connect(self.show_add_visitor_window)
        scan_card_button = HoverButton("Сканировать карту")
        scan_card_button.clicked.connect(self.scan_card_for_attendance)
        visitor_list_button = HoverButton("Список посетителей")
        visitor_list_button.clicked.connect(self.show_view_visitors_window)
        left_panel.addWidget(new_visitor_button)
        left_panel.addSpacing(20)
        left_panel.addWidget(scan_card_button)
        left_panel.addSpacing(20)
        left_panel.addWidget(visitor_list_button)
        left_panel.addStretch()

        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        left_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Центральная панель
        central_panel = QVBoxLayout()
        central_panel.setSpacing(20)
        duty_trainers_label = QLabel("Тренеры на смене:")
        font = QFont("Unbounded", 28, QFont.Bold)
        duty_trainers_label.setFont(font)
        duty_trainers_label.setStyleSheet("""
            font-family: Unbounded;
            font-size: 28px;
            font-weight: 700;
            line-height: 35px;
            text-align: left;
        """)

        center_frame = QFrame()
        center_frame_layout = QHBoxLayout(center_frame)
        center_frame_layout.setAlignment(Qt.AlignLeft)
        self.trainer_widgets = []
        self.load_duty_trainers()

        central_panel.addWidget(duty_trainers_label, stretch=0)
        central_panel.addWidget(center_frame, stretch=0)
        self.chart_widget = ChartWidget()
        self.chart_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.chart_widget.setMinimumHeight(400)  # Установите желаемую минимальную высоту
        central_panel.addWidget(self.chart_widget, stretch=3)  # Диаграмма получает больший коэффициент растяжки
        central_panel.addStretch(1)

        central_widget = QWidget()
        central_widget.setLayout(central_panel)
        central_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Правая панель
        right_panel = QVBoxLayout()
        right_panel.setSpacing(20)
        right_panel.setAlignment(Qt.AlignTop)

        self.photo_placeholder = FillPhoto("")
        self.photo_placeholder.setFixedSize(325, 433)

        self.name_label = QLabel("")
        self.role_label = QLabel("")
        self.name_label.setStyleSheet("""
            font-family: 'Unbounded';
            font-size: 36px;
        """)
        self.role_label.setStyleSheet("""
            font-family: 'Unbounded';
            font-size: 22px;
        """)

        # Применяем загруженные данные об администраторе
        self.name_label.setText(self.admin_full_name)
        self.role_label.setText(self.admin_role)
        if self.admin_photo_data:
            self.photo_placeholder.setPhotoData(self.admin_photo_data)
        else:
            self.photo_placeholder.setText("Фото не установлено")

        right_panel.addWidget(self.photo_placeholder, alignment=Qt.AlignLeft)
        right_panel.addWidget(self.name_label, alignment=Qt.AlignLeft)
        right_panel.addWidget(self.role_label, alignment=Qt.AlignLeft)
        right_panel.addStretch()

        right_widget = QWidget()
        right_widget.setLayout(right_panel)
        right_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)

        grid_layout.addWidget(left_widget, 0, 0, 1, 1)
        grid_layout.addWidget(central_widget, 0, 1, 1, 1, alignment=Qt.AlignHCenter)
        grid_layout.addWidget(right_widget, 0, 2, 1, 1, alignment=Qt.AlignTop)

        layout.addLayout(grid_layout)

    def load_duty_trainers(self):
        self.duty_trainers_thread = WorkerThread(get_duty_trainers)
        self.duty_trainers_thread.result_signal.connect(self.update_duty_trainers_ui)
        self.duty_trainers_thread.start()

    def update_duty_trainers_ui(self, duty_trainers):
        if duty_trainers:
            center_frame = self.main_page.findChild(QFrame)
            if center_frame:
                center_layout = center_frame.layout()
                for widget in self.trainer_widgets:
                    center_layout.removeWidget(widget)
                    widget.setParent(None)
                self.trainer_widgets.clear()

                for trainer in duty_trainers[:3]:
                    trainer_widget = self.create_trainer_widget(trainer)
                    center_layout.addWidget(trainer_widget)
                    self.trainer_widgets.append(trainer_widget)
        else:
            logger.error("Не удалось загрузить тренеров на смене.")

    def create_trainer_widget(self, trainer):
        trainer_id, first_name, surname, patronymic, phone_number, description, photo = trainer

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        photo_label = QLabel()
        photo_label.setFixedSize(93, 93)
        photo_label.setStyleSheet("""
            background-color: gray;
            border-radius: 18px;
            border: 2.7px solid #75A9A7;
            padding: 0px 2px 0px 3px;
            margin-top: 0px;
        """)
        if photo:
            pixmap = QPixmap()
            pixmap.loadFromData(photo)
            pixmap = pixmap.scaled(93, 93, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            photo_label.setPixmap(pixmap)
        else:
            photo_label.setText(f"{surname} {first_name}")
            photo_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(photo_label)
        name_label = QLabel(f"{surname} {first_name}")
        name_label.setFont(QFont("Unbounded", 12, QFont.Bold))
        name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(name_label)

        trainer_widget = QWidget()
        trainer_widget.setLayout(layout)
        trainer_widget.setFixedSize(100, 130)
        trainer_widget.setStyleSheet("""
            QWidget {
                border: 1px solid #75A9A7;
                border-radius: 10px;
                background-color: #f0f0f0;
            }
        """)

        return trainer_widget
    def init_schedule_page(self):
        self.current_date = datetime.date.today()
        month_calendar = calendar.monthcalendar(self.current_date.year, self.current_date.month)
        self.previous_total_weeks = len(month_calendar)
        self.current_week = self.get_current_week_of_month(self.current_date)
        layout = QVBoxLayout(self.schedule_page)

        layout.setObjectName("schedule_page")

        # Секция с тренерами
        self.trainers_layout = QHBoxLayout()
        trainers = [
            {"name": "Анатолий", "image": "anatoliy.png"},
            {"name": "Михаил", "image": "mikhail.png"},
            {"name": "Анна", "image": "anna.png"},
            {"name": "Маша", "image": "masha.png"},
            {"name": "Сергей", "image": "sergey.png"},
        ]

        self.trainer_buttons = []

        for trainer in trainers:
            trainer_widget = self.create_trainer_widget(trainer["name"], trainer["image"])
            self.trainers_layout.addWidget(trainer_widget)
            self.trainer_buttons.append(trainer_widget)

        layout.addLayout(self.trainers_layout)

        # Секция расписания (изначально скрыта)
        self.schedule_group = QWidget()
        self.schedule_group.setVisible(False)
        self.schedule_layout = QVBoxLayout(self.schedule_group)
        self.schedule_layout.setAlignment(Qt.AlignTop)

        # Навигация по месяцам
        prev_month_button = QPushButton("<")
        prev_month_button.setFixedSize(30, 30)
        prev_month_button.clicked.connect(lambda: self.change_month(-1))

        self.month_label = QLabel()
        self.month_label.setObjectName('month')
        self.month_label.setStyleSheet(
            """
            QLabel#month {
                font-family: 'Unbounded';
                font-size: 25px;
                font-weight: 500;
                text-align: center;
                background-color: transparent;
                border: 0px;
            }
            """
        )
        self.month_label.setAlignment(Qt.AlignCenter)

        next_month_button = QPushButton(">")
        next_month_button.setFixedSize(30, 30)
        next_month_button.clicked.connect(lambda: self.change_month(1))

        month_navigation_layout = QHBoxLayout()
        month_navigation_layout.addWidget(prev_month_button, alignment=Qt.AlignLeft)
        month_navigation_layout.addWidget(self.month_label, alignment=Qt.AlignCenter)
        month_navigation_layout.addWidget(next_month_button, alignment=Qt.AlignRight)

        self.schedule_layout.addLayout(month_navigation_layout)

        # Виджет для выбора недель
        self.week_buttons_group = SelectionGroupWidget(
            idd=1,
            options=[],  # Кнопки добавляются динамически
            group_type="week",
        )
        self.week_buttons_group.setObjectName("smt")
        self.week_buttons_group.setStyleSheet("""
           QLabel {
                font-family: 'Unbounded';
                font-size: 15px;
                font-weight: 500;
                text-align: center;
                background-color: transparent;
                border: 0px;
           }
        """)
        self.week_buttons_group.clicked.connect(self.update_week_selection)
        self.schedule_layout.addWidget(self.week_buttons_group, alignment=Qt.AlignCenter)

        # Фрейм с днями недели
        self.week_frame = self.create_week_frame()
        self.week_frame.setVisible(False)
        self.schedule_layout.addWidget(self.week_frame, alignment=Qt.AlignCenter)

        layout.addWidget(self.schedule_group)

        # Кнопка возврата на главную страницу
        back_button = QPushButton("Вернуться на главную страницу")
        back_button.setStyleSheet("margin-top: 20px; font-size: 14px;")
        back_button.clicked.connect(lambda: self.switch_to_page(self.main_page))
        layout.addWidget(back_button, alignment=Qt.AlignCenter)

        # Инициализация кнопок недель и отображение дней
        self.update_weeks_and_days()

    def get_current_week_of_month(self, date):
        """Возвращает номер текущей недели для заданной даты."""
        month_calendar = calendar.monthcalendar(date.year, date.month)
        for week_index, week in enumerate(month_calendar):
            if date.day in week:
                return week_index + 1
        return 1

    def select_trainer(self, selected_button, trainer_name):
        """Обрабатывает выбор тренера и обновляет состояния кнопок."""
        for button in self.trainer_buttons:
            button.is_selected = button == selected_button
            button.update_styles()

        # Показываем расписание
        self.show_schedule_for_trainer(trainer_name)

    def show_schedule_for_trainer(self, trainer_name):
        """Показывает расписание для выбранного тренера."""
        print(f"Выбран тренер: {trainer_name}")  # Убедитесь, что вывод остается только здесь
        self.schedule_group.setVisible(True)
        self.week_frame.setVisible(True)
        self.update_month_label()
        self.month_label.setText(f"{self.month_label.text()} - {trainer_name}")
        self.update_weeks_and_days()

    def create_trainer_widget(self, name, image_path):
        """Создаёт виджет тренера на основе TrainerButton."""
        trainer_button = TrainerButton(name, image_path="Group.png",avatar_width=60,avatar_height=60,font_size=20, border_width_normal=4, border_color_normal='#75A9A7',
    border_width_hover=4, border_color_hover="#88F9F5",
    border_width_selected=5, border_color_selected="#88F9F5"
)


        # Подключаем обработчик для выбора тренера
        trainer_button.clicked.connect(lambda: self.select_trainer(trainer_button, name))
        return trainer_button

    def update_weeks_and_days(self):
        """Обновляет кнопки недель и дни недели."""
        # Получаем календарь для текущего месяца
        month_calendar = calendar.monthcalendar(self.current_date.year, self.current_date.month)
        total_weeks = len(month_calendar)

        # Если текущая неделя является последней в предыдущем месяце, переключаемся на последнюю
        if hasattr(self, 'previous_total_weeks') and self.current_week == self.previous_total_weeks:
            self.current_week = total_weeks

        # Если текущая неделя превышает количество недель в новом месяце, переключаемся на последнюю
        if self.current_week > total_weeks:
            self.current_week = total_weeks

        # Обновляем кнопки недель
        week_options = [f"{i + 1} неделя" for i in range(total_weeks)]
        self.week_buttons_group.update_options(week_options)

        # Устанавливаем ширину виджета недель
        self.week_buttons_group.setFixedWidth(980)

        # Устанавливаем выбранную неделю
        self.week_buttons_group.set_selected_option(f"{self.current_week} неделя")

        # Обновляем дни для выбранной недели
        self.update_days(self.current_week)

    def update_week_selection(self):
        """Обрабатывает выбор недели через SelectionGroupWidget."""
        selected_week = self.week_buttons_group.selected_option
        if selected_week:
            self.current_week = int(selected_week.split()[0])  # Сохраняем выбранную неделю
            self.update_days(self.current_week)

    def create_week_frame(self):
        """Создает фрейм с днями недели."""
        week_frame = QFrame()
        week_frame.setStyleSheet("border: 2px solid #75A9A7; border-radius: 15px; padding: 10px;")
        week_layout = QGridLayout(week_frame)
        week_layout.setSpacing(15)

        days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

        for i, day in enumerate(days):
            day_widget = self.create_day_widget(day)
            week_layout.addWidget(day_widget, 0, i)

        return week_frame

    def create_day_widget(self, day_name, is_enabled=True):
        """Создает виджет дня недели с прокручиваемой областью."""
        # Основной фрейм дня
        day_frame = QFrame()
        day_frame.setObjectName('day_f')
        day_frame.setFixedWidth(160)
        day_frame.setFixedHeight(250)

        # Стили для активных и неактивных дней
        if is_enabled:
            day_frame.setStyleSheet("""
                QFrame#day_f {
                    border: 2px solid #75A9A7;
                    border-radius: 10px;
                    background-color: #75A9A7;
                    padding: 0px;
                    margin: 0px;
                }
            """)
        else:
            day_frame.setStyleSheet("""
                QFrame#day_f {
                    border: 2px solid #d3d3d3;
                    border-radius: 10px;
                    background-color: #d3d3d3;  /* Серый фон для неактивного дня */
                    padding: 0px;
                    margin: 0px;
                }
            """)

        # Макет основного фрейма
        day_layout = QVBoxLayout(day_frame)
        day_layout.setAlignment(Qt.AlignTop)
        day_layout.setContentsMargins(0, 0, 0, 0)
        day_layout.setSpacing(0)

        # Название дня
        day_label = QLabel(day_name)
        day_label.setObjectName('day_l')
        day_label.setWordWrap(True)
        day_label.setAlignment(Qt.AlignCenter)
        day_label.setStyleSheet(f"""
            QLabel#day_l {{
                font-family: 'Unbounded';
                font-size: 12px;
                font-weight: 500;
                text-align: center;
                color: {'black' if is_enabled else '#a0a0a0'};
                background-color: transparent;
                padding: 0px;
                margin-bottom: 7px;
                border: 0px;
            }}
        """)
        day_layout.addWidget(day_label)

        # Прокручиваемая область
        scroll_area = QScrollArea()
        scroll_area.setFixedWidth(day_frame.width() - 4)
        scroll_area.setObjectName('scroll')
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                padding: 0px;
                margin: 0px;
                border: 0px;
                background-color: {'white' if is_enabled else '#d3d3d3'}; /* Фон прокручиваемой области */
           
            }}
            QScrollBar:vertical {{
                width: 8px;
                border: none;
                background: {'#75A9A7' if is_enabled else '#d3d3d3'}; /* Фон скроллбара */
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
                background: #d3d3d3; /* Серый фон для неактивного скроллбара */
            }}
        """)

        # Контейнер для элементов внутри прокручиваемой области
        container_widget = QWidget()
        container_widget.setObjectName('scroll_content')
        container_widget.setStyleSheet("border: 0px; padding: 0px; margin: 0px;")
        container_layout = QVBoxLayout(container_widget)
        container_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)  # Элементы по центру
        container_layout.setSpacing(10)  # Расстояние между элементами
        container_layout.setContentsMargins(0, 0, 0, 0)

        # Пример элементов внутри дня
        for i in range(4):  # Замените цикл вашими элементами
            item_label = QLabel(f"Элемент {i + 1}")
            item_label.setAlignment(Qt.AlignCenter)
            item_label.setStyleSheet(f"""
                QLabel {{
                    font-family: 'Unbounded';
                    font-size: 12px;
                    color: {'black' if is_enabled else '#a0a0a0'};
                    background-color: transparent; /* Убираем фон у элемента */
                    padding: 2px 0;
                    margin: 0px;
                }}
            """)
            container_layout.addWidget(item_label)

        # Добавляем кнопку "+" внутрь прокручиваемой области
        add_button = HoverButton("+", 30, 30, 30, '#75A9A7', True, '', '', 5, '#5DEBE6')
        if not is_enabled:
            add_button.disable_button()
        container_layout.addWidget(add_button, alignment=Qt.AlignCenter)

        container_widget.setLayout(container_layout)
        scroll_area.setWidget(container_widget)

        # Добавляем прокручиваемую область в макет дня
        day_layout.addWidget(scroll_area)

        return day_frame

    def change_month(self, delta):
        """Изменяет текущий месяц и сохраняет выбранную неделю."""
        # Сохраняем количество недель в текущем месяце перед переключением
        month_calendar = calendar.monthcalendar(self.current_date.year, self.current_date.month)
        self.previous_total_weeks = len(month_calendar)

        # Обновляем текущий месяц
        year = self.current_date.year
        month = self.current_date.month + delta
        if month > 12:
            month = 1
            year += 1
        elif month < 1:
            month = 12
            year -= 1

        self.current_date = datetime.date(year, month, 1)

        # Обновляем виджеты
        self.update_month_label()
        self.update_weeks_and_days()

    def update_month_label(self):
        """Обновляет текст заголовка месяца на русском языке, добавляя год только при необходимости."""
        current_year = datetime.date.today().year
        month_name = self.current_date.strftime("%B").capitalize()  # Название месяца с заглавной буквы
        if self.current_date.year != current_year:
            self.month_label.setText(f"{month_name} {self.current_date.year}")
        else:
            self.month_label.setText(month_name)

    def update_days(self, week_number):
        """Обновляет отображение дней недели."""
        self.week_frame.setVisible(True)
        for i in reversed(range(self.week_frame.layout().count())):
            self.week_frame.layout().itemAt(i).widget().deleteLater()

        month_calendar = calendar.monthcalendar(self.current_date.year, self.current_date.month)
        if week_number - 1 < len(month_calendar):
            days_in_week = month_calendar[week_number - 1]
        else:
            days_in_week = [0] * 7

        days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        today = datetime.date.today()

        for i, day in enumerate(days):
            if days_in_week[i] == 0:  # День не относится к месяцу
                day_widget = self.create_day_widget(day, is_enabled=False)
            else:
                day_date = datetime.date(self.current_date.year, self.current_date.month, days_in_week[i])
                if day_date < today:  # День уже прошёл
                    day_widget = self.create_day_widget(f"{day}", is_enabled=False)
                else:  # Будущий или текущий день
                    day_widget = self.create_day_widget(f"{day}", is_enabled=True)
            self.week_frame.layout().addWidget(day_widget)

    def increment_main_page_counter(self):
        # Увеличение счетчика на главной странице
        current_value = int(self.main_page_counter.text().split(": ")[1])
        self.main_page_counter.setText(f"Счетчик: {current_value + 1}")

    def switch_to_page(self, page):
        # Переключение между страницами
        self.stack.setCurrentWidget(page)
