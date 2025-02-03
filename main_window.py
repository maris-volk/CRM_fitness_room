import calendar
import datetime
import locale
import logging
import os
import threading
from functools import partial

from PyQt5 import QtWidgets, QtGui, QtCore, sip
from PyQt5.QtChart import QChartView, QBarSeries, QBarSet, QChart, QBarCategoryAxis, QValueAxis
from PyQt5.QtCore import QTimer, Qt, QMargins, pyqtSignal, QThread, QSize, QTime, QByteArray
from PyQt5.QtGui import QColor, QPainter, QFont, QBrush, QIcon, QPixmap, QPixmapCache
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, QStackedWidget, QGridLayout, \
    QSizePolicy, QScrollArea, QMessageBox, QApplication, QScrollBar, QSpacerItem
from babel.dates import format_date

from add_trainer_slot import AddSlotWindow
from add_visitor_window import AddVisitorWindow, AddTrainerWindow, AddAdministratorWindow
from chart import ChartWidget
from constants import MAX_ACTIVE_THREADS
from database import get_active_visitors, get_duty_trainers, count_visitors_in_gym, check_visitor_in_gym, \
    end_attendance, \
    start_attendance, execute_query, count_all_trainers, get_all_trainers, get_schedule_for_week, get_all_admins
from hover_button import HoverButton, TrainerButton, SvgHoverButton, CustomAddTrainerOrAdminButton
from search_client import ClientSearchWindow
from utils import scan_card, WorkerThread, ResizablePhoto, FillPhoto, ClickableLabelForSlots, resources_path, \
    correct_to_nominative_case, LoadAdminsThread, ScanCardDialog
from subscription import SubscriptionWidget, SelectionGroupWidget

logger = logging.getLogger(__name__)


class MainWindow(QWidget):
    def __init__(self, current_user_id):
        super().__init__()
        self.current_user_id = current_user_id
        self.update_complete = threading.Event()
        self.selected_client = None  # Данные о выбранном клиенте
        self.subscription_data = None
        self.from_add_client = False
        self.active_requests = {}
        self.active_threads = {}  # Словарь для хранения активных потоков

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

        self.load_admin_data()
        self.chart_widget = ChartWidget()
        self.chart_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.chart_widget.setMinimumHeight(400)

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
            all_trainers = count_all_trainers()
            duty_trainers = get_duty_trainers()
            return (total_visitors, visitors_in_gym, all_trainers, duty_trainers)
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
        total_visitors, visitors_in_gym, all_trainers, duty_trainers = result

        def get_plural_form(number, forms):
            """
            Возвращает правильную форму слова в зависимости от числа.

            :param number: Число, определяющее форму.
            :param forms: Кортеж из трёх форм слова: (ед. ч., род. падеж ед. ч., мн. ч.)
                          Например: ("посетитель", "посетителя", "посетителей").
            :return: Правильная форма слова.
            """
            number = abs(number) % 100
            if 11 <= number <= 19:
                return forms[2]
            number %= 10
            if number == 1:
                return forms[0]
            elif 2 <= number <= 4:
                return forms[1]
            else:
                return forms[2]

        visitors_label_text = (
            f"{total_visitors} {get_plural_form(total_visitors, ('посетитель', 'посетителя', 'посетителей'))}\n"
            f"{visitors_in_gym} {get_plural_form(visitors_in_gym, ('в зале', 'в зале', 'в зале'))}"
        )

        trainers_label_text = (
            f"{all_trainers} {get_plural_form(all_trainers, ('тренер', 'тренера', 'тренеров'))}\n"
            f"{len(duty_trainers)} {get_plural_form(len(duty_trainers), ('на смене', 'на смене', 'на смене'))}"
        )

        # Установка текста в QLabel
        self.visitors_label.setText(visitors_label_text)
        self.trainers_label.setText(trainers_label_text)
        self.update_duty_trainers_ui(duty_trainers)

    def show_add_visitor_window(self):
        if not hasattr(self, 'add_visitor_window') or not self.add_visitor_window.isVisible():
            self.add_visitor_window = AddVisitorWindow(main_window=self)
            self.add_visitor_window.show()
            self.add_visitor_window.raise_()

    def show_view_visitors_window(self):
        if not hasattr(self, 'view_visitors_window') or not self.view_visitors_window.isVisible():
            self.view_visitors_window = ClientSearchWindow(self.admin_role)

            self.view_visitors_window.show()
            self.view_visitors_window.raise_()

    def scan_card_for_attendance(self):
        if hasattr(self, 'scan_thread') and self.scan_thread.isRunning():
            self.scan_thread.stop()  # Останавливаем старый поток
            self.scan_thread.wait()  # Ждем завершения

        self.card_number = None  # Сбрасываем перед каждым сканированием
        self.scan_thread = WorkerThread(self._scan_card_and_update_attendance)
        self.scan_thread.result_signal.connect(self.handle_scan_result)
        self.scan_thread.start()

    def _scan_card_and_update_attendance(self):
        card_number = scan_card()

        if self.scan_thread._stop_requested:  # Проверяем, был ли поток остановлен
            return None

        if not card_number:
            return None

        attendance_data = check_visitor_in_gym(card_number)

        if self.scan_thread._stop_requested:  # Проверяем снова перед возвратом результата
            return None

        return card_number, attendance_data

    def handle_scan_result(self, result):
        if not result:
            QMessageBox.warning(self, "Ошибка", "Карта не была отсканирована.")
            return
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
        if self.admin_role == 'Управляющий':
            self.administrator_page = QWidget()
            self.init_administrators_page()
            self.stack.addWidget(self.administrator_page)

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
        top_layout = QHBoxLayout(top_panel)

        # Создание элементов
        self.visitors_label = QLabel("0 посетителей\n0 в зале")
        self.trainers_label = QLabel("0 тренеров\n0 на смене")
        schedule_label = QLabel("Расписание тренеров")
        schedule_label.setCursor(Qt.PointingHandCursor)
        schedule_label.mousePressEvent = lambda event: self.switch_to_page(self.schedule_page)

        admin_label = None
        if self.admin_role == "Управляющий":
            admin_label = QLabel("Администраторы")
            admin_label.setCursor(Qt.PointingHandCursor)
            admin_label.mousePressEvent = lambda event: self.switch_to_page(self.administrator_page)

        # Создание кнопки профиля
        self.profile_button = SvgHoverButton(resources_path("src/group.svg"), width=51, height=51,
                                             default_color='#75A9A7',
                                             hover_color="#88F9F5", attrib="stroke", need_shadow=False)
        self.profile_button.setFixedSize(51, 51)
        self.profile_button.clicked.connect(lambda: self.switch_to_page(self.schedule_page))
        self.profile_button.setIcon(QIcon(resources_path("Group.png")))
        self.profile_button.setIconSize(QSize(51, 51))
        self.profile_button.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
            }
            QPushButton:pressed {
                background-color: lightgray;
            }
        """)

        # Добавляем элементы в горизонтальный layout
        top_layout.addWidget(self.visitors_label)
        top_layout.addWidget(self.trainers_label)
        if self.admin_role == "Управляющий":
            top_layout.addWidget(admin_label)
        top_layout.addWidget(schedule_label)

        # Spacer для отступа перед кнопкой, создадим пространство между элементами и кнопкой
        # spacer = QSpacerItem(90, 0, QSizePolicy.Fixed, QSizePolicy.Minimum)
        # top_layout.addItem(spacer)
        # self.profile_button.setAl
        top_layout.addWidget(self.profile_button, Qt.AlignLeft)  # Кнопка будет выровнена вправо

        top_layout.setContentsMargins(100, 0, 100, 20)

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
        scan_card_button.clicked.connect(lambda: ScanCardDialog(self).exec_())

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


        # Надпись "Тренеры на смене"
        self.for_need_widget = QWidget()
        self.trainers_container = QVBoxLayout()
        self.trainers_container.setSpacing(10)
        self.trainers_container.setAlignment(Qt.AlignLeft)
        self.duty_trainers_label = QLabel("Тренеры на смене:")
        font = QFont("Unbounded", 28, QFont.Bold)
        self.duty_trainers_label.setFont(font)
        self.duty_trainers_label.setStyleSheet("""
                    font-family: Unbounded;
                    font-size: 28px;
                    font-weight: 700;
                    line-height: 35px;
                    text-align: left;
                """)
        self.trainers_container.addWidget(self.duty_trainers_label)
        self.trainers_grid_widget = QWidget()
        self.trainers_grid = QHBoxLayout()
        self.trainers_grid.setSpacing(10)
        self.displayed_trainers = []
        self.trainers_grid_widget.setLayout(self.trainers_grid)
        self.trainers_container.addWidget(self.trainers_grid_widget)
        self.main_trainer_widget = QWidget()
        self.main_trainer_widget.setLayout(self.trainers_container)

        central_panel.addWidget(self.main_trainer_widget)

        # Добавляем диаграмму
        central_panel.addWidget(self.chart_widget, stretch=2)  # Диаграмма получает больший коэффициент растяжки
        central_panel.addStretch(1)

        central_widget = QWidget()
        central_widget.setLayout(central_panel)
        central_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Правая панель
        right_panel = QVBoxLayout()
        right_panel.setSpacing(20)
        right_panel.setAlignment(Qt.AlignTop)

        self.photo_label = QLabel()
        self.photo_label.setFixedSize(320, 400)
        self.photo_label.setStyleSheet("""
                    background-color: #F0F0F0;
                    border: 2px solid #75A9A7;
                    border-radius: 10px;
                """)

        # Загружаем фото, если есть
        if self.admin_photo_data:
            photo_pixmap = self.load_image_from_bytes(self.admin_photo_data)
            if photo_pixmap:
                photo_pixmap = self.load_image_from_bytes(self.admin_photo_data)
                if photo_pixmap:
                    # Масштабируем изображение с заполнением всего QLabel (часть изображения обрежется)
                    scaled_pixmap = photo_pixmap.scaled(
                        self.photo_label.size(),
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation
                    )

                    # Создаем пустой QPixmap с размерами QLabel
                    final_pixmap = QPixmap(self.photo_label.size())
                    final_pixmap.fill(Qt.GlobalColor.transparent)  # Прозрачный фон

                    # Отрисовываем изображение по центру
                    painter = QPainter(final_pixmap)
                    x_offset = (self.photo_label.width() - scaled_pixmap.width()) // 2
                    y_offset = (self.photo_label.height() - scaled_pixmap.height()) // 2
                    painter.drawPixmap(x_offset, y_offset, scaled_pixmap)
                    painter.end()

                    # Устанавливаем готовое изображение в QLabel
                    self.photo_label.setPixmap(final_pixmap)

            else:
                # Если фото не смогло загрузиться
                self.photo_label.setVisible(False)
        else:
            # Если фотография отсутствует в БД
            self.photo_label.setVisible(False)

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

        self.name_label.setText(self.admin_full_name)
        self.role_label.setText(self.admin_role)
        right_panel.addWidget(self.photo_label, alignment=Qt.AlignLeft)
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

    def load_image_from_bytes(self, image_data):
        """
        Загружает изображение из байтов и кэширует его.
        :param image_data: Байтовое представление изображения.
        :return: QPixmap или None, если загрузка не удалась.
        """
        if not image_data:
            return None

        # Используем хэш-сумму данных изображения в виде строки
        cache_key = str(hash(image_data))  # Преобразуем хэш в строку

        # Проверяем, есть ли изображение в кэше
        pixmap = QPixmapCache.find(cache_key)
        if pixmap:
            return pixmap

        # Если изображения нет в кэше, загружаем его из данных
        pixmap = QPixmap()
        if pixmap.loadFromData(image_data):
            QPixmapCache.insert(cache_key, pixmap)  # Сохраняем в кэш
            return pixmap

        return None

    def get_image_data(self):
        # Пример: загрузка данных изображения из файла
        with open("path_to_image.png", "rb") as file:
            return file.read()

    def load_duty_trainers(self):
        self.duty_trainers_thread = WorkerThread(get_duty_trainers)
        self.duty_trainers_thread.result_signal.connect(self.update_duty_trainers_ui)
        self.duty_trainers_thread.start()

    def update_duty_trainers_ui(self, duty_trainers):
        # Очищаем текущие виджеты
        # self.trainers_container.addWidget(self.duty_trainers_label)
        # self.trainers_grid = QHBoxLayout()
        # self.trainers_grid.setSpacing(10)
        # self.displayed_trainers = []
        # self.trainers_container.addWidget(self.trainers_grid)
        # central_panel.addWidget(self.trainers_container)
        for widget in self.displayed_trainers:
            self.trainers_grid.removeWidget(widget)
            widget.setParent(None)


        if duty_trainers:
            # Добавляем новые виджеты
            for trainer in duty_trainers[:3]:  # Ограничиваем количество тренеров до 3
                trainer_widget = self.create_trainer_widget(trainer)
                self.trainers_grid.addWidget(trainer_widget)
                self.displayed_trainers.append(trainer_widget)

            self.duty_trainers_label.setText("Тренера на смене:")
        else:
            # Если тренеров нет, отображаем надпись
            self.duty_trainers_label.setText("Нет тренеров на смене")

    def create_trainer_widget(self, trainer):
        trainer_id, first_name, surname, patronymic, phone_number, description, photo = trainer

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        photo_label = QLabel()
        photo_label.setFixedSize(90, 90)
        photo_label.setStyleSheet("""
            border: 2.7px solid #75A9A7;
            border-radius:10px;
        """)

        if photo:
            pixmap = QPixmap()
            pixmap.loadFromData(photo)
            pixmap = pixmap.scaled(90, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            photo_label.setPixmap(pixmap)
            photo_label.setAlignment(Qt.AlignCenter)
        else:
            photo_label.setText(first_name)
            photo_label.setAlignment(Qt.AlignCenter)
            photo_label.setStyleSheet("font-size: 14px; font-weight: bold;")

        layout.addWidget(photo_label)

        name_label = QLabel(f"{first_name}")
        name_label.setFont(QFont("Unbounded", 10, QFont.Bold))
        name_label.setFixedWidth(100)
        name_label.setAlignment(Qt.AlignLeft)
        name_label.setWordWrap(True)
        name_label.adjustSize()

        layout.addWidget(name_label)

        trainer_widget = QWidget()
        trainer_widget.setLayout(layout)
        trainer_widget.setFixedSize(150, 180)  # Даем больше места

        return trainer_widget

    def load_trainers(self):

        """
        Загружает список тренеров из базы данных в отдельном потоке.
        """

        def handle_result(trainers):
            print(3211)

            for trainer in trainers:
                trainer_widget = self.create_personal_widget_to_slot(
                    id=trainer["id"],
                    name=trainer["name"],
                    surname=trainer["surname"],
                    patronymic=trainer["patronymic"],
                    phone=trainer["phone"],
                    description=trainer["description"],
                    image_data=trainer["image"]
                )

                trainer_widget.setFixedWidth(300)  # Ограничение ширины виджета
                print(trainer_widget.width())
                print(trainer_widget.height())
                trainer_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

                self.trainers_layout.addWidget(trainer_widget)
                self.trainer_buttons.append(trainer_widget)

            add_trainer_widget = CustomAddTrainerOrAdminButton(self.add_trainer_button)

            self.trainers_layout.addWidget(add_trainer_widget)
            self.trainer_buttons.append(add_trainer_widget)
            self.update_scrollbar_visibility()

        self.worker = WorkerThread(get_all_trainers)
        print(1123)
        self.worker.result_signal.connect(handle_result)
        self.worker.finished_signal.connect(self.worker.deleteLater)
        self.worker.start()

    def init_administrators_page(self):
        self.selected_admin_id = None
        layout = QVBoxLayout(self.administrator_page)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        layout.setObjectName("admin_page")

        self.admin_scroll_area = QScrollArea()
        self.admin_scroll_area.setStyleSheet("border:0px")
        self.admin_scroll_area.setWidgetResizable(True)
        self.admin_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.admin_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.admin_scroll_area.setFixedHeight(200)

        self.admin_container = QWidget()
        self.admin_layout = QHBoxLayout(self.admin_container)
        self.admin_layout.setSpacing(10)
        self.admin_layout.setContentsMargins(0, 0, 0, 0)
        self.admin_layout.setAlignment(Qt.AlignCenter)
        self.admin_buttons = []

        self.admin_scroll_area.setWidget(self.admin_container)

        self.admin_horizontal_scrollbar = QScrollBar(Qt.Horizontal)
        self.admin_horizontal_scrollbar.setFixedHeight(10)
        self.admin_horizontal_scrollbar.setStyleSheet("""
            QScrollBar:horizontal {
                height: 8px;
                background: white;
            }
            QScrollBar::handle:horizontal {
                background: #5DEBE6;
                border-radius: 4px;
            }
        """)

        self.admin_horizontal_scrollbar.valueChanged.connect(self.admin_scroll_area.horizontalScrollBar().setValue)
        self.admin_scroll_area.horizontalScrollBar().valueChanged.connect(self.admin_horizontal_scrollbar.setValue)
        self.admin_horizontal_scrollbar.hide()

        admin_section_layout = QVBoxLayout()
        admin_section_layout.addWidget(self.admin_horizontal_scrollbar)
        admin_section_layout.addWidget(self.admin_scroll_area)
        admin_section_layout.setSpacing(0)
        admin_section_layout.setContentsMargins(0, 0, 0, 0)

        layout.addLayout(admin_section_layout)

        # Кнопка добавления администратора
        self.add_admin_button = HoverButton("+", 65, 65, 65, '#75A9A7', True, '', '', 10, '#5DEBE6')
        self.add_admin_button.clicked.connect(self.open_add_admin_window)
        self.admin_layout.addWidget(self.add_admin_button, Qt.AlignCenter)

        # Загрузка администраторов
        self.load_admins()

    def open_add_admin_window(self):
        self.add_admin_window = AddAdministratorWindow()
        self.add_admin_window.admin_added.connect(self.add_admin_to_ui)
        self.add_admin_window.show()
        self.add_admin_window.raise_()

    def add_admin_to_ui(self, admin_data):
        admin_widget = self.create_personal_widget_to_slot(
            id=admin_data["admin_id"],
            name=admin_data["name"],
            surname=admin_data["surname"],
            patronymic=admin_data["patronymic"],
            phone=admin_data["phone"],
            description=admin_data["description"],
            image_data=admin_data["image"],
            username=admin_data["username"],
            password_hash=admin_data["password_hash"],
            user_id=admin_data["user_id"],
            admin=True
        )
        admin_widget.setFixedWidth(300)
        admin_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.admin_layout.insertWidget(len(self.admin_buttons) - 1, admin_widget)
        self.admin_buttons.insert(len(self.admin_buttons) - 1, admin_widget)

        self.update_scrollbar_visibility(admin=True)
        admin_widget.clicked.emit()

    def load_admins(self):
        self.load_admins_thread = LoadAdminsThread()
        self.load_admins_thread.result_signal.connect(self.handle_admins_loaded)
        self.load_admins_thread.error_signal.connect(self.handle_admins_error)
        self.load_admins_thread.start()

    def handle_admins_loaded(self, admins):
        for admin in admins:
            admin_widget = self.create_personal_widget_to_slot(
                id=admin["admin_id"],
                name=admin["first_name"],
                surname=admin["surname"],
                patronymic=admin["patronymic"],
                phone=admin["phone_number"],
                description=admin["description"],
                image_data=admin["photo"],
                username=admin["username"],
                password_hash=admin["password_hash"],
                user_id=admin["user_id"],
                admin=True
            )
            admin_widget.setFixedWidth(300)
            admin_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
            self.admin_layout.addWidget(admin_widget)
            self.admin_buttons.append(admin_widget)

        add_admin_widget = CustomAddTrainerOrAdminButton(self.add_admin_button)
        self.admin_layout.addWidget(add_admin_widget)
        self.admin_buttons.append(add_admin_widget)
        self.update_scrollbar_visibility(admin=True)

    def handle_admins_error(self, error_message):
        QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить администраторов: {error_message}")

    def delete_admin(self, admin_id):
        """
        Удаляет администратора и каскадно удаляет все его записи в базе.
        """
        message_box = QMessageBox(self)
        message_box.setWindowTitle("Удаление")
        message_box.setText("Вы подтверждаете удаление администратора?\nПользователь утратит доступ к системе.")
        message_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        message_box.button(QMessageBox.Yes).setText("Да")
        message_box.button(QMessageBox.No).setText("Нет")

        reply = message_box.exec_()

        if reply == QMessageBox.Yes:
            # Удаление администратора из базы данных
            query = "DELETE FROM administrators WHERE admin_id = %s"
            execute_query(query, (admin_id,), fetch=False)

            # Удаление связанного пользователя из таблицы users
            query = "DELETE FROM users WHERE user_id = (SELECT user_id FROM administrators WHERE admin_id = %s)"
            execute_query(query, (admin_id,), fetch=False)

            admin_to_remove = None

            # Удаление виджета администратора из UI
            for admin_widget in self.admin_buttons:
                if admin_widget.trainer_id == admin_id:
                    admin_to_remove = admin_widget
                    break

            if admin_to_remove:
                self.admin_layout.removeWidget(admin_to_remove)
                admin_to_remove.deleteLater()
                self.admin_buttons.remove(admin_to_remove)

            # Если удалённый администратор был выбран, сбрасываем выбор
            if self.selected_admin_id == admin_id:
                self.selected_admin_id = None

            # Перепривязываем события, чтобы не осталось "битых" ссылок
            valid_admins = [a for a in self.admin_buttons if hasattr(a, "admin_id")]

            for admin_widget in valid_admins:
                admin_widget.clicked.disconnect()
                admin_widget.clicked.connect(
                    lambda btn=admin_widget, aid=admin_widget.admin_id: self.select_admin(btn, aid)
                )
            self.update_scrollbar_visibility(admin=True)

    def select_admin(self, selected_button, admin_id):
        self.selected_admin_id = admin_id
        for button in self.admin_buttons:
            button.is_selected = button == selected_button
            button.update_styles()

    def update_scrollbar_visibility(self, admin=False):
        if admin:
            num_admins = len(self.admin_buttons)
            if num_admins > 5:
                self.admin_horizontal_scrollbar.show()
            else:
                self.admin_horizontal_scrollbar.hide()
        else:
            num_trainers = len(self.trainer_buttons)
            if num_trainers > 5:
                self.horizontal_scrollbar.show()
            else:
                self.horizontal_scrollbar.hide()

    def open_edit_admin_window(self, admin_data):
        self.edit_trainer_window = AddAdministratorWindow(admin_data)
        self.edit_trainer_window.admin_updated.connect(self.update_admin_in_ui)
        self.edit_trainer_window.show()
        self.edit_trainer_window.raise_()

    def update_admin_in_ui(self, admin_data):
        for admin_widget in self.admin_buttons:
            if admin_widget.trainer_id == admin_data["admin_id"]:
                admin_widget.name = admin_data["name"]
                admin_widget.surname = admin_data["surname"]
                admin_widget.patronymic = admin_data["patronymic"]
                admin_widget.phone = admin_data["phone"]
                admin_widget.description = admin_data["description"]
                admin_widget.username = admin_data["username"]

                # Обновляем аватарку
                image_data = admin_data["image"]
                pixmap = QPixmap()

                try:
                    if isinstance(image_data, bytes):  # Если фото в формате bytes
                        if not image_data:
                            raise ValueError("Данные изображения пусты.")
                        if not pixmap.loadFromData(QByteArray(image_data)):  # Конвертация в QPixmap
                            raise ValueError("Ошибка загрузки из bytes")
                    elif isinstance(image_data, str):  # Если передан путь
                        if not os.path.exists(image_data):
                            raise ValueError("Файл изображения не найден.")
                        if not pixmap.load(image_data):  # Загружаем фото
                            raise ValueError("Ошибка загрузки по пути")
                    else:
                        raise ValueError("Неизвестный формат изображения")
                except ValueError as e:
                    print(f"Ошибка при загрузке фото: {e}")
                    pixmap.load(resources_path("group.png"))  # Устанавливаем fallback-изображение

                # Масштабируем картинку перед установкой
                pixmap = pixmap.scaled(
                    admin_widget.avatar_width,
                    admin_widget.avatar_height,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )

                # Обновляем данные виджета
                admin_widget.image_path = admin_data["image"]
                admin_widget.name_label.setText(admin_data["name"])
                admin_widget.avatar_label.setPixmap(pixmap)
                admin_widget.avatar_label.repaint()  # Принудительная перерисовка
                admin_widget.update_styles()
                break

    def init_schedule_page(self):
        self.selected_trainer_id = None
        self.day_widgets = {}  # Словарь для хранения виджетов дней по дате
        self.schedule_cache = {}  # Структура: {(trainer_id, day_date): {"data": [...], "hash": "..."}}

        self.current_date = datetime.date.today()
        month_calendar = calendar.monthcalendar(self.current_date.year, self.current_date.month)
        self.previous_total_weeks = len(month_calendar)
        self.current_week = self.get_current_week_of_month(self.current_date)
        layout = QVBoxLayout(self.schedule_page)
        layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)

        layout.setObjectName("schedule_page")

        self.trainers_scroll_area = QScrollArea()
        self.trainers_scroll_area.setStyleSheet("border:0px")
        self.trainers_scroll_area.setWidgetResizable(True)
        self.trainers_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # Выключаем встроенный скролбар
        self.trainers_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.trainers_scroll_area.setFixedHeight(200)

        # Контейнер для тренеров
        self.trainers_container = QWidget()
        self.trainers_layout = QHBoxLayout(self.trainers_container)
        self.trainers_layout.setSpacing(10)
        self.trainers_layout.setContentsMargins(0, 0, 0, 0)
        self.trainers_layout.setAlignment(Qt.AlignCenter)
        self.trainer_buttons = []

        self.trainers_scroll_area.setWidget(self.trainers_container)

        self.horizontal_scrollbar = QScrollBar(Qt.Horizontal)

        self.horizontal_scrollbar.setFixedHeight(10)
        self.horizontal_scrollbar.setStyleSheet("""
            QScrollBar:horizontal {
                height: 8px;
                background: white;
            }
            QScrollBar::handle:horizontal {
                background: #5DEBE6;
                border-radius: 4px;
            }
        """)

        # === Связываем горизонтальный скролбар с QScrollArea ===
        self.horizontal_scrollbar.valueChanged.connect(self.trainers_scroll_area.horizontalScrollBar().setValue)
        self.trainers_scroll_area.horizontalScrollBar().valueChanged.connect(self.horizontal_scrollbar.setValue)
        self.horizontal_scrollbar.hide()

        # === Размещаем элементы (СНАЧАЛА СКРОЛБАР, ПОТОМ QScrollArea) ===
        trainers_section_layout = QVBoxLayout()
        trainers_section_layout.addWidget(self.horizontal_scrollbar)  # Скролбар сверху
        trainers_section_layout.addWidget(self.trainers_scroll_area)  # Список тренеров
        trainers_section_layout.setSpacing(0)
        trainers_section_layout.setContentsMargins(0, 0, 0, 0)

        layout.addLayout(trainers_section_layout)  # Добавляем в главный layout

        # === Кнопка добавления тренера ===
        self.add_trainer_button = HoverButton("+", 65, 65, 65, '#75A9A7', True, '', '', 10, '#5DEBE6')
        self.add_trainer_button.clicked.connect(self.open_add_trainer_window)

        self.load_trainers()

        # Секция расписания (изначально скрыта)
        self.schedule_group = QWidget()
        self.schedule_group.setVisible(False)
        self.schedule_layout = QVBoxLayout(self.schedule_group)
        self.schedule_layout.setAlignment(Qt.AlignTop)

        # Навигация по месяцам

        self.prev_month_button = SvgHoverButton(resources_path("src/prev.svg"), width=40, height=50,
                                                default_color='#75A9A7',
                                                hover_color="#88F9F5")
        self.prev_month_button.clicked.connect(lambda: self.change_month(-1, self.prev_month_button))

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
        self.month_label.setFixedWidth(300)
        self.month_label.setAlignment(Qt.AlignCenter)

        self.next_month_button = SvgHoverButton(resources_path("src/next.svg"), width=40, height=50,
                                                default_color='#75A9A7',
                                                hover_color="#88F9F5")

        self.next_month_button.clicked.connect(lambda: self.change_month(1, self.next_month_button))

        month_navigation_layout = QHBoxLayout()
        month_navigation_layout.setContentsMargins(0, 0, 0, 0)
        month_navigation_layout.setSpacing(20)

        month_navigation_layout.addWidget(self.prev_month_button)
        month_navigation_layout.addWidget(self.month_label)
        month_navigation_layout.addWidget(self.next_month_button)

        month_navigation_layout.setAlignment(Qt.AlignCenter)

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

        # Инициализация кнопок недель и отображение дней
        if self.selected_trainer_id is not None:
            self.update_weeks_and_days(self.selected_trainer_id)

    def get_current_week_of_month(self, date):
        """Возвращает номер текущей недели для заданной даты."""
        month_calendar = calendar.monthcalendar(date.year, date.month)
        for week_index, week in enumerate(month_calendar):
            if date.day in week:
                return week_index + 1
        return 1

    def open_add_trainer_window(self):
        """Открывает окно добавления тренера"""
        self.add_trainer_window = AddTrainerWindow()
        self.add_trainer_window.trainer_added.connect(self.add_trainer_to_ui)  # Подключаем сигнал
        self.add_trainer_window.show()
        self.add_trainer_window.raise_()

    def remove_trainer_from_ui(self, trainer_widget):
        """Удаляет тренера из UI и скрывает расписание, если он был выбран"""
        if self.selected_trainer_id == trainer_widget.trainer_id:
            self.schedule_group.setVisible(False)  # Скрываем расписание
            self.selected_trainer_id = None  # Сбрасываем выбор тренера

        trainer_widget.setParent(None)  # Убираем из родительского layout
        trainer_widget.deleteLater()

    def delete_trainer(self, trainer_id):
        """
        Удаляет тренера и каскадно удаляет все его записи в базе.
        """
        message_box = QMessageBox(self)
        message_box.setWindowTitle("Удаление")
        message_box.setText("Вы подтверждаете удаление тренера?\nВсе слоты посещений с ним будут удалены.")
        message_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        message_box.button(QMessageBox.Yes).setText("Да")
        message_box.button(QMessageBox.No).setText("Нет")

        reply = message_box.exec_()

        if reply == QMessageBox.Yes:
            query = "DELETE FROM trainer WHERE trainer_id = %s"
            execute_query(query, (trainer_id,), fetch=False)

            trainer_to_remove = None

            # Удалить виджет тренера из UI
            for trainer_widget in self.trainer_buttons:
                if trainer_widget.trainer_id == trainer_id:
                    trainer_to_remove = trainer_widget
                    break

            if trainer_to_remove:
                self.trainers_layout.removeWidget(trainer_to_remove)
                trainer_to_remove.deleteLater()
                self.trainer_buttons.remove(trainer_to_remove)

            # Если удалённый тренер был выбран, скрываем расписание
            if self.selected_trainer_id == trainer_id:
                self.schedule_group.setVisible(False)
                self.selected_trainer_id = None

            # Перепривязываем события, чтобы не осталось "битых" ссылок
            valid_trainers = [t for t in self.trainer_buttons if hasattr(t, "trainer_id")]

            for trainer_widget in valid_trainers:
                trainer_widget.clicked.disconnect()
                trainer_widget.clicked.connect(
                    lambda btn=trainer_widget, tid=trainer_widget.trainer_id: self.select_trainer(btn, tid)
                )
            self.update_scrollbar_visibility()

    def update_scrollbar_visibility(self, admin=False):
        """
        Включает горизонтальный скроллбар, если в `self.trainers_layout` больше 5 виджетов.
        """
        if admin:
            num_trainers = len(self.admin_buttons)  # Количество тренеров

            if num_trainers > 5:
                self.admin_horizontal_scrollbar.show()
            else:
                self.admin_horizontal_scrollbar.hide()
        else:
            num_trainers = len(self.trainer_buttons)  # Количество тренеров

            if num_trainers > 5:
                self.horizontal_scrollbar.show()
            else:
                self.horizontal_scrollbar.hide()

    def add_trainer_to_ui(self, trainer_data):
        """Добавляет нового тренера в UI"""
        trainer_widget = self.create_personal_widget_to_slot(
            id=trainer_data["id"],
            name=trainer_data["name"],
            surname=trainer_data["surname"],
            patronymic=trainer_data["patronymic"],
            phone=trainer_data["phone"],
            description=trainer_data["description"],
            image_data=trainer_data["image"]
        )
        trainer_widget.setFixedWidth(300)
        trainer_widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.trainers_layout.insertWidget(len(self.trainer_buttons) - 1, trainer_widget)
        self.trainer_buttons.insert(len(self.trainer_buttons) - 1, trainer_widget)
        self.update_scrollbar_visibility()
        trainer_widget.clicked.emit()

    def select_trainer(self, selected_button, trainer_id):
        """
        Обрабатывает выбор тренера и обновляет состояния кнопок.
        :param selected_button: Кнопка выбранного тренера.
        :param trainer_id: ID выбранного тренера.
        """

        # Обновление состояния кнопок
        self.selected_trainer_id = trainer_id
        for button in self.trainer_buttons:
            button.is_selected = button == selected_button
            button.update_styles()

        # Загрузка расписания выбранного тренера
        self.show_schedule_for_trainer(trainer_id)

    def show_schedule_for_trainer(self, trainer_id):
        """
        Показывает расписание для выбранного тренера.
        :param trainer_id: ID выбранного тренера.
        """
        # Установка видимости секции расписания
        self.schedule_group.setVisible(True)
        self.week_frame.setVisible(True)

        # Обновление заголовка месяца
        self.update_month_label()

        # Загрузка недель и дней для выбранного тренера
        self.update_weeks_and_days(trainer_id)

    def create_personal_widget_to_slot(self, id, name, surname, patronymic, phone, description, image_data,
                                       admin=False, username=None, user_id=None, password_hash=None):
        """Создаёт виджет тренера на основе TrainerButton.

        Аргументы:
        - trainer_id: ID тренера
        - name: Имя тренера
        - image_data: Либо `bytes` (из БД), либо `str` (путь к файлу), либо `None`
        """

        if isinstance(image_data, memoryview):  # Данные из БД переданы как memoryview
            image_data = bytes(image_data)  # Конвертация в bytes

        if isinstance(image_data, bytes):  # Фото в формате bytes
            pixmap = QPixmap()
            if pixmap.loadFromData(QByteArray(image_data)):  # Конвертируем в QPixmap
                image_path = pixmap
            else:
                image_path = resources_path("Group.png")  # Если не загружается, fallback
        elif isinstance(image_data, str) and os.path.exists(image_data):  # Локальный файл
            image_path = image_data
        elif isinstance(image_data, QByteArray):  # Локальный файл
            pixmap = QPixmap()
            if pixmap.loadFromData(image_data):  # Конвертируем в QPixmap
                image_path = pixmap
            else:
                image_path = resources_path("Group.png")  # Если не загружается, fallback
        else:
            image_path = resources_path("Group.png")  # Если фото нет, дефолтная заглушка
        # В методе create_personal_widget_to_slot
        if admin:
            button = TrainerButton(
                name=name,
                surname=surname,
                patronymic=patronymic,
                phone=phone,
                description=description,
                image_path=image_path,
                trainer_id=id,
                admin_role=self.admin_role,
                admin=admin,
                username=username,
                user_id=user_id,
                password_hash=password_hash,
                avatar_width=60,
                avatar_height=60,
                font_size=20,
                border_width_normal=4,
                border_color_normal='#75A9A7',
                border_width_hover=4,
                border_color_hover="#88F9F5",
                border_width_selected=5,
                border_color_selected="#88F9F5"
            )
            button.clicked.connect(lambda: self.select_admin(button, id))
            button.delete_clicked.connect(lambda _, tid=id: self.delete_admin(tid))
            button.edit_clicked.connect(self.open_edit_admin_window)
        else:
            button = TrainerButton(
                name=name,
                surname=surname,
                patronymic=patronymic,
                phone=phone,
                description=description,
                image_path=image_path,
                trainer_id=id,
                admin_role=self.admin_role,
                avatar_width=60,
                avatar_height=60,
                font_size=20,
                border_width_normal=4,
                border_color_normal='#75A9A7',
                border_width_hover=4,
                border_color_hover="#88F9F5",
                border_width_selected=5,
                border_color_selected="#88F9F5"
            )
            button.clicked.connect(lambda: self.select_trainer(button, id))
            button.delete_clicked.connect(lambda _, tid=id: self.delete_trainer(tid))
            button.edit_clicked.connect(self.open_edit_trainer_window)
        return button

    def open_edit_trainer_window(self, trainer_data):
        print(trainer_data)
        """Открывает окно редактирования тренера с заполненными данными."""
        self.edit_trainer_window = AddTrainerWindow(trainer_data)  # Передаём данные тренера
        self.edit_trainer_window.trainer_updated.connect(self.update_trainer_in_ui)  # Подключаем сигнал
        self.edit_trainer_window.show()
        self.edit_trainer_window.raise_()

    def update_trainer_in_ui(self, trainer_data):
        """Обновляет данные тренера в UI после редактирования."""
        for trainer_widget in self.trainer_buttons:
            if trainer_widget.trainer_id == trainer_data["id"]:
                # Обновляем текстовые данные
                trainer_widget.name = trainer_data["name"]
                trainer_widget.surname = trainer_data["surname"]
                trainer_widget.patronymic = trainer_data["patronymic"]
                trainer_widget.phone = trainer_data["phone"]
                trainer_widget.description = trainer_data["description"]

                # Обновляем изображение
                image_data = trainer_data["image"]
                pixmap = QPixmap()

                try:
                    if isinstance(image_data, bytes):  # Если фото в формате bytes
                        if not image_data:
                            raise ValueError("Данные изображения пусты.")
                        if not pixmap.loadFromData(QByteArray(image_data)):  # Конвертация в QPixmap
                            raise ValueError("Ошибка загрузки из bytes")
                    elif isinstance(image_data, str):  # Если передан путь
                        if not os.path.exists(image_data):
                            raise ValueError("Файл изображения не найден.")
                        if not pixmap.load(image_data):  # Загружаем фото
                            raise ValueError("Ошибка загрузки по пути")
                    else:
                        raise ValueError("Неизвестный формат изображения")
                except ValueError as e:
                    print(f"Ошибка при загрузке фото: {e}")
                    pixmap.load(resources_path("group.png"))  # Устанавливаем fallback-изображение

                # Масштабируем картинку перед установкой
                pixmap = pixmap.scaled(
                    trainer_widget.avatar_width,
                    trainer_widget.avatar_height,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )

                # Обновляем данные виджета
                trainer_widget.image_path = trainer_data["image"]
                trainer_widget.name_label.setText(trainer_data["name"])
                trainer_widget.avatar_label.setPixmap(pixmap)
                trainer_widget.avatar_label.repaint()  # Принудительная перерисовка
                trainer_widget.update_styles()
                break

    def update_weeks_and_days(self, trainer_id):
        """
        Обновляет кнопки недель и дни недели для выбранного тренера.
        :param trainer_id: ID выбранного тренера.
        """
        if not trainer_id:
            print("Ошибка: не выбран тренер.")
            return
        month_calendar = calendar.monthcalendar(self.current_date.year, self.current_date.month)
        total_weeks = len(month_calendar)

        if hasattr(self, 'previous_total_weeks') and self.current_week == self.previous_total_weeks:
            self.current_week = total_weeks
        if self.current_week > total_weeks:
            self.current_week = total_weeks

        week_options = [f"{i + 1} неделя" for i in range(total_weeks)]
        self.week_buttons_group.update_options(week_options)
        self.week_buttons_group.setFixedWidth(980)
        self.week_buttons_group.set_selected_option(f"{self.current_week} неделя")

        self.update_days(self.current_week, trainer_id)

    def update_week_selection(self):
        """Обрабатывает выбор недели через SelectionGroupWidget."""
        selected_week = self.week_buttons_group.selected_option
        if selected_week:
            self.current_week = int(selected_week.split()[0])
            self.update_days(self.current_week, self.selected_trainer_id)

    def create_week_frame(self):
        """Создает фрейм с днями недели."""
        week_frame = QFrame()
        week_frame.setStyleSheet("border: 2px solid #75A9A7; border-radius: 15px; padding: 10px;")
        week_layout = QGridLayout(week_frame)
        week_layout.setSpacing(15)

        days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

        for i, day in enumerate(days):
            day_widget = self.create_day_widget(day, None)
            week_layout.addWidget(day_widget, 0, i)

        return week_frame

    def extract_slots_from_scroll_area(self, scroll_area):
        """
        Извлекает список слотов (временных интервалов) из `scroll_area`.
        :param scroll_area: Объект QScrollArea, содержащий виджеты слотов.
        :return: Список слотов в формате [(start_time, end_time), ...].
        """
        container_widget = scroll_area
        if not container_widget:
            return []

        container_layout = container_widget.layout()
        slots = []
        for i in range(container_layout.count()):
            entry_widget = container_layout.itemAt(i).widget()
            if entry_widget:
                time_label = entry_widget.findChild(QLabel)
                if time_label:
                    try:
                        start_time, end_time = map(
                            lambda t: QTime.fromString(t.strip(), "hh:mm"),
                            time_label.text().split('-')
                        )
                        if start_time.isValid() and end_time.isValid():
                            slots.append((start_time, end_time))
                    except ValueError:
                        continue
        return slots

    def create_day_widget(self, day_name, day, schedule_data=None, is_enabled=True):

        schedule_data = schedule_data or []

        day_frame = QFrame()
        day_frame.setObjectName('day_f')
        day_frame.setFixedWidth(160)
        day_frame.setFixedHeight(250)

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
                    background-color: #d3d3d3;
                    padding: 0px;
                    margin: 0px;
                }
            """)

        day_layout = QVBoxLayout(day_frame)
        day_layout.setAlignment(Qt.AlignTop)
        day_layout.setContentsMargins(0, 0, 0, 0)
        day_layout.setSpacing(0)

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

        scroll_area = QScrollArea()
        scroll_area.setFixedWidth(day_frame.width() - 4)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                padding: 0px;
                margin: 0px;
                border: 0px;
                background-color: {'white' if is_enabled else 'transparent'};
            }}
            QScrollBar:vertical {{
                width: 8px;
                border: none;
                background: {'#75A9A7' if is_enabled else '#d3d3d3'};
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
                background: #d3d3d3;
            }}
        """)

        container_widget = QWidget()
        container_widget.setObjectName('scroll_content')
        container_widget.setStyleSheet("border: 0px; padding: 0px; margin: 0px;")
        container_layout = QVBoxLayout(container_widget)
        container_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        container_layout.setSpacing(10)
        container_layout.setContentsMargins(0, 0, 5, 5)

        for item in schedule_data:
            entry_widget = QWidget()
            entry_layout = QHBoxLayout(entry_widget)
            entry_layout.setContentsMargins(0, 0, 0, 0)
            entry_layout.setSpacing(5)

            info_layout = QVBoxLayout()
            info_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            info_layout.setSpacing(2)

            time_label = QLabel(f"{item['start_time'].strftime('%H:%M')} - {item['end_time'].strftime('%H:%M')}")
            time_label.setAlignment(Qt.AlignCenter)
            if self.admin_role == "Управляющий":
                time_label.setStyleSheet("""
                                                    QLabel {
                                                        font-family: 'Unbounded';
                                                        font-size: 12px;
                                                        font-weight: bold;
                                                        color: black;
                                                    }
                                                """)
            else:
                time_label.setStyleSheet("""
                                                                        QLabel {
                                                                            font-family: 'Unbounded';
                                                                            font-size: 14px;
                                                                            font-weight: bold;
                                                                            color: black;
                                                                        }
                                                                    """)
            info_layout.addWidget(time_label)

            client_label = ClickableLabelForSlots(item['client'], item.get('client_id'),self.admin_role)  # Используем ClickableLabel
            client_label.setAlignment(Qt.AlignCenter)
            client_label.setWordWrap(True)
            if self.admin_role == "Управляющий":
                client_label.setStyleSheet(f"""
                                            QLabel {{
                                                font-family: 'Unbounded';
                                                font-size: 12px;
                                                font-weight:bold;
                                                color: {'black' if is_enabled else '#a0a0a0'};
                                                text-decoration: underline;
                                            }}
                                        """)
            else:
                client_label.setStyleSheet(f"""
                                                                QLabel {{
                                                                    font-family: 'Unbounded';
                                                                    font-size: 14px;
                                                                    font-weight:bold;
                                                                    color: {'black' if is_enabled else '#a0a0a0'};
                                                                    text-decoration: underline;
                                                                }}
                                                            """)
            info_layout.addWidget(client_label)

            # --- Добавляем info_layout (время и клиент) в entry_layout (основной горизонтальный layout) ---
            entry_layout.addLayout(info_layout)

            # --- Добавляем кнопку удаления, если self.admin_role == "Управляющий" ---
            if self.admin_role == "Управляющий":
                delete_button = HoverButton("Х", 25, 25, 30, '#8F2D31', True, '#8F2D31', 'red', 5, 'red')

                delete_button.clicked.connect(
                    lambda _, slot_id=item.get('slot_id'), widget=entry_widget, day_date=day:
                    self.delete_slot(slot_id, widget, day_date)
                )

                entry_layout.addWidget(delete_button, alignment=Qt.AlignRight)  # Кнопка закрепляется справа

            container_layout.addWidget(entry_widget, alignment=Qt.AlignTop | Qt.AlignHCenter)

        add_button = HoverButton("+", 30, 30, 40, '#75A9A7', True, '', '', 5, '#5DEBE6', 10)
        add_button.setFixedHeight(40)

        if not is_enabled:
            add_button.disable_button()

        container_layout.addWidget(add_button, alignment=Qt.AlignCenter)
        add_button.clicked.connect(lambda: self.open_add_slot_window(container_layout, day))

        container_widget.setLayout(container_layout)
        scroll_area.setWidget(container_widget)

        day_layout.addWidget(scroll_area)

        return day_frame

    def open_add_slot_window(self, scroll_area, day):

        existing_slots = self.extract_slots_from_scroll_area(scroll_area)

        self.add_slot_window = AddSlotWindow(
            selected_client=self.selected_client,
            subscription_data=self.subscription_data,
            existing_slots=existing_slots,
            selected_date=day,
            trainer_id=self.selected_trainer_id  # Передаем ID тренера
        )
        self.add_slot_window.slot_added.connect(self.handle_slot_added)
        self.add_slot_window.show()

    def handle_slot_added(self, slot_data):
        """Обновляет UI после добавления слота"""
        day_date = slot_data["date"]  # Дата, переданная из `AddSlotWindow`

        if not isinstance(day_date, datetime.date):
            print("Ошибка: неверный формат даты", day_date)
            return

        # Преобразуем QTime в строковый формат HH:MM
        if isinstance(slot_data["start_time"], QTime):
            slot_data["start_time"] = slot_data["start_time"].toString("HH:mm")
        if isinstance(slot_data["end_time"], QTime):
            slot_data["end_time"] = slot_data["end_time"].toString("HH:mm")

        # **Находим существующий cache_key (по неделе)**
        cache_key = None
        for key in self.schedule_cache.keys():
            # Смотрим, что тренер и дата совпадают
            if key[0] == self.selected_trainer_id and day_date in self.schedule_cache[key]:
                cache_key = key
                break

        # Если нужного cache_key нет, создаём новый
        if cache_key is None:
            cache_key = (self.selected_trainer_id, day_date)
            self.schedule_cache[cache_key] = {}

        # **Добавляем слот в день (создаем если еще нет)**
        if day_date not in self.schedule_cache[cache_key]:
            self.schedule_cache[cache_key][day_date] = []

        # **Проверяем, что слот ещё не добавлен**
        existing_slot = next((s for s in self.schedule_cache[cache_key][day_date]
                              if s["start_time"] == slot_data["start_time"] and s["end_time"] == slot_data["end_time"]),
                             None)

        if existing_slot:
            print(f"Слот {slot_data['start_time']} - {slot_data['end_time']} уже существует!")
        else:
            self.schedule_cache[cache_key][day_date].append(slot_data)
            print(f"Слот добавлен в кэш: {slot_data}")

        print(f"Обновленный кэш: {self.schedule_cache}")

        # **Обновляем UI**
        if day_date in self.day_widgets:
            print(f"Обновляем виджет для {day_date}")
            self.update_day_widget(self.day_widgets[day_date], self.schedule_cache[cache_key][day_date],
                                   is_enabled=True, day=day_date)
        else:
            print(f"Ошибка: виджет для {day_date} не найден")

        print(f"После обновления UI: {self.schedule_cache.get(cache_key, {})}")

    def display_added_slot(self, slot_data):
        print(f"Добавленный слот: {slot_data}")

    def change_month(self, delta, button):
        """Изменяет текущий месяц и сохраняет выбранную неделю."""

        month_calendar = calendar.monthcalendar(self.current_date.year, self.current_date.month)
        self.previous_total_weeks = len(month_calendar)

        year = self.current_date.year
        month = self.current_date.month + delta
        if month > 12:
            month = 1
            year += 1
        elif month < 1:
            month = 12
            year -= 1

        self.current_date = datetime.date(year, month, 1)

        self.update_month_label()
        self.update_weeks_and_days(self.selected_trainer_id)

    def update_month_label(self):
        """Обновляет текст заголовка месяца на русском языке, добавляя год только при необходимости."""
        current_year = datetime.date.today().year
        month_name = format_date(self.current_date, "MMMM",
                                 locale="ru").capitalize()  # Название месяца с заглавной буквы
        if self.current_date.year != current_year:
            self.month_label.setText(f"{correct_to_nominative_case(month_name)} {self.current_date.year}")
        else:
            self.month_label.setText(f"{correct_to_nominative_case(month_name)}")

    # def update_existing_week_widgets(self):
    #     """
    #     Обновляет текущие виджеты недели, учитывая диапазон подписки.
    #     """
    #     today = datetime.date.today()
    #
    #
    #     subscription_start = None
    #     subscription_end = None
    #     if self.subscription_data:
    #         try:
    #             subscription_start = datetime.datetime.strptime(self.subscription_data.get("start_date", ""),
    #                                                             "%d.%m.%Y").date()
    #             subscription_end = datetime.datetime.strptime(self.subscription_data.get("end_date", ""),
    #                                                           "%d.%m.%Y").date()
    #         except ValueError:
    #             print("Ошибка формата дат в подписке. Подписка будет игнорироваться.")
    #             subscription_start, subscription_end = None, None
    #
    #     for day_date, day_widget in self.day_widgets.items():
    #         if subscription_start and subscription_end:
    #             is_enabled = subscription_start <= day_date <= subscription_end and day_date >= today
    #         else:
    #             is_enabled = day_date >= today  # Если подписки нет, только будущее
    #
    #
    #         if subscription_start and subscription_end and (
    #                 day_date < subscription_start or day_date > subscription_end):
    #             is_enabled = False
    #
    #         self.update_day_widget(day_widget, [], is_enabled)

    def update_days(self, week_number, trainer_id):
        """
        Обновляет отображение дней недели для текущей недели и выбранного тренера.
        :param week_number: Номер текущей недели.
        :param trainer_id: ID выбранного тренера.
        """
        self.week_frame.setVisible(True)

        buffer_layout = QGridLayout()
        buffer_layout.setSpacing(15)

        # Получение дней недели для текущей недели
        month_calendar = calendar.monthcalendar(self.current_date.year, self.current_date.month)
        if week_number - 1 >= len(month_calendar):
            print(f"Неделя {week_number} не существует для текущего месяца.")
            return

        days_in_week = month_calendar[week_number - 1]
        days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        today = datetime.date.today()

        start_date = None  # Начальная дата недели
        end_date = None  # Конечная дата недели

        subscription_start = None
        subscription_end = None

        if self.subscription_data:
            subscription_start = datetime.datetime.strptime(self.subscription_data.get("start_date", ""),
                                                            "%d.%m.%Y").date()
            subscription_end = datetime.datetime.strptime(self.subscription_data.get("end_date", ""), "%d.%m.%Y").date()

        for i, day in enumerate(days):
            if days_in_week[i] == 0:  # День не относится к текущему месяцу
                day_widget = self.create_day_widget(day, [], is_enabled=False)
                buffer_layout.addWidget(day_widget, 0, i)
            else:
                day_date = datetime.date(self.current_date.year, self.current_date.month, days_in_week[i])

                if start_date is None:  # Первая валидная дата недели
                    start_date = day_date

                end_date = day_date  # Последняя валидная дата недели

                is_enabled = (
                                     (
                                             subscription_start and subscription_end and subscription_start <= day_date <= subscription_end)
                                     or (subscription_start is None and subscription_end is None)
                             ) and day_date >= today

                # Создание виджета дня с учетом активности

                day_widget = self.create_day_widget(day, day_date, [], is_enabled=is_enabled)
                buffer_layout.addWidget(day_widget, 0, i)

                self.day_widgets[day_date] = day_widget

        if start_date and end_date:  # Если даты корректны
            # Загрузка данных для всей недели
            self.load_schedule_for_week(trainer_id, start_date, end_date)

        self.replace_week_layout(buffer_layout)

    def replace_week_layout(self, new_layout):
        """
        Заменяет текущий макет недели на новый буферный макет.
        :param new_layout: Новый макет для замены.
        """
        old_layout = self.week_frame.layout()
        if old_layout is not None:
            while old_layout.count():
                item = old_layout.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()

            QWidget().setLayout(old_layout)

        self.week_frame.setLayout(new_layout)

    def update_schedule_ui(self, schedule_data):
        """
        Обновляет UI с расписанием тренера за неделю.
        :param schedule_data: Расписание тренера, сгруппированное по дням.
        """
        if not schedule_data:
            print("Ошибка: пустое расписание для обновления UI.")
            return

        today = datetime.date.today()

        for day_date, slots in schedule_data.items():
            if day_date in self.day_widgets:
                print(f"Обновляем виджет для даты: {day_date}, слотов: {len(slots)}")
                day_widget = self.day_widgets[day_date]

                if self.subscription_data:
                    subscription_start = datetime.datetime.strptime(self.subscription_data.get("start_date", ""),
                                                                    "%d.%m.%Y").date()
                    subscription_end = datetime.datetime.strptime(self.subscription_data.get("end_date", ""),
                                                                  "%d.%m.%Y").date()

                    if subscription_start and subscription_end:
                        try:

                            is_enabled = subscription_start <= day_date <= subscription_end and today <= day_date
                        except ValueError as e:
                            print(f"Ошибка при преобразовании даты абонемента: {e}")
                            is_enabled = False
                    else:
                        print("Данные абонемента клиента отсутствуют.")
                        is_enabled = False  # Если данных абонемента нет, день считается неактивным
                else:
                    is_enabled = today <= day_date

                self.update_day_widget(day_widget, slots, is_enabled, day_date)  # Передаём is_enabled
            else:
                print(f"Ошибка: виджет для {day_date} не найден.")

    def terminate_all_threads(self):
        """
        Завершает все активные потоки.
        """

        for cache_key, worker in self.active_threads.items():
            logger.info(f"Завершение потока: {id(worker)} для {cache_key}")
            worker.terminate()
        self.active_threads.clear()

    def load_schedule_for_week(self, trainer_id, start_date, end_date):
        """
        Загружает расписание для тренера за неделю.
        """
        if hasattr(self, "is_loading_week") and self.is_loading_week:
            logger.info("Запрос расписания уже выполняется. Ожидание завершения.")
            return

        self.is_loading_week = True

        cache_key = (trainer_id, start_date, end_date)

        if cache_key in self.schedule_cache:
            self.update_schedule_ui(self.schedule_cache[cache_key])
            self.is_loading_week = False
            return

        # Обработчик результата
        def handle_result(schedule_data):
            try:
                if not schedule_data:
                    logger.warning(f"Пустое расписание для {cache_key}.")
                else:
                    self.schedule_cache[cache_key] = schedule_data
                    self.update_schedule_ui(schedule_data)
            except Exception as e:
                logger.error(f"Ошибка в обработчике результата: {e}")
            finally:
                self.is_loading_week = False
                logger.info(f"Флаг is_loading_week сброшен для {cache_key}")

        def handle_error(error_message):
            logger.error(f"Ошибка в потоке загрузки расписания: {error_message}")
            self.is_loading_week = False
            logger.info(f"Флаг is_loading_week сброшен после ошибки для {cache_key}")

        worker = WorkerThread(get_schedule_for_week, trainer_id, start_date, end_date)
        logger.info(f"Создан поток: {id(worker)} для {cache_key}")

        worker.result_signal.connect(handle_result)
        worker.error_signal.connect(handle_error)
        worker.finished_signal.connect(lambda: logger.info(f"Поток завершён: {id(worker)}"))
        worker.finished_signal.connect(lambda: self.active_threads.pop(cache_key, None))

        worker.finished_signal.connect(lambda: setattr(self, "is_loading_week", False))  # Сбрасываем флаг выполнения

        worker.start()

        self.active_threads[cache_key] = worker

    def get_schedule_hash_for_day(self, trainer_id, day_date):
        """
        Получает хэш расписания для тренера на определённый день.
        :param trainer_id: ID тренера.
        :param day_date: Дата дня.
        :return: Хэш данных (например, md5) или временная метка.
        """
        query = """
            SELECT MD5(STRING_AGG(CONCAT_WS(',', ts.start_time, ts.end_time, c.first_name, c.surname), ',')) AS hash
            FROM training_slots ts
            LEFT JOIN client c ON ts.client = c.client_id
            WHERE ts.trainer = %s AND DATE(ts.start_time) = %s;
        """
        result = execute_query(query, (trainer_id, day_date))
        return result[0][0] if result else None

    def update_day_widget(self, day_widget, schedule_data, is_enabled, day):
        """
        Обновляет содержимое существующего виджета дня.
        :param day_widget: Виджет дня, который нужно обновить.
        :param schedule_data: Данные расписания для обновления (список слотов).
        :param is_enabled: Включен ли день (активный или прошедший).
        """

        if day_widget is None or sip.isdeleted(day_widget):
            print(f"Ошибка: виджет дня {day_widget} не найден или был удален.")
            return

        print(f"Обновляем виджет дня: {day_widget.objectName()} с данными: {schedule_data}")

        # Очистка текущего содержимого контейнера
        container_widget = day_widget.findChild(QWidget, 'scroll_content')
        if not container_widget or sip.isdeleted(container_widget):
            print("Ошибка: контейнер для содержимого недоступен.")
            return

        container_layout = container_widget.layout()
        while container_layout.count():
            widget = container_layout.takeAt(0).widget()
            if widget:
                widget.deleteLater()
        spacer = QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Minimum)
        container_layout.addItem(spacer)
        if not schedule_data:
            print("Данные расписания пусты. Добавляем только кнопку '+'.")
        else:
            # Добавление новых записей из schedule_data
            for item in schedule_data:
                print(f"Добавляем запись: {item}")
                # Контейнер для одной записи
                entry_widget = QWidget()
                entry_layout = QHBoxLayout(entry_widget)
                entry_layout.setContentsMargins(0, 0, 0, 0)
                entry_layout.setSpacing(5)
                entry_widget.setFixedWidth(142)

                info_layout = QVBoxLayout()
                info_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                info_layout.setSpacing(2)
                fixed_width = 117 if self.admin_role == "Управляющий" else 142  # Меняем размер в зависимости от роли

                if isinstance(item['start_time'], QTime) and isinstance(item['end_time'], QTime):
                    time_label = QLabel(
                        f"{item['start_time'].toString('HH:mm')} - {item['end_time'].toString('HH:mm')}")
                elif isinstance(item['start_time'], datetime.datetime) and isinstance(item['end_time'],
                                                                                      datetime.datetime):
                    time_label = QLabel(
                        f"{item['start_time'].time().strftime('%H:%M')} - {item['end_time'].time().strftime('%H:%M')}")
                elif isinstance(item['start_time'], datetime.time) and isinstance(item['end_time'], datetime.time):
                    time_label = QLabel(
                        f"{item['start_time'].strftime('%H:%M')} - {item['end_time'].strftime('%H:%M')}")
                else:
                    time_label = QLabel(f"{item['start_time']} - {item['end_time']}")

                time_label.setAlignment(Qt.AlignCenter)
                time_label.setFixedWidth(fixed_width)
                if self.admin_role == "Управляющий":
                    time_label.setStyleSheet("""
                                        QLabel {
                                            font-family: 'Unbounded';
                                            font-size: 12px;
                                            font-weight: bold;
                                            color: black;
                                        }
                                    """)
                else:
                    time_label.setStyleSheet("""
                                                            QLabel {
                                                                font-family: 'Unbounded';
                                                                font-size: 14px;
                                                                font-weight: bold;
                                                                color: black;
                                                            }
                                                        """)
                info_layout.addWidget(time_label)

                client_label = ClickableLabelForSlots(item['client'],
                                                      item.get('client_id'),self.admin_role)  # Используем ClickableLabel
                client_label.setAlignment(Qt.AlignCenter)
                client_label.setWordWrap(True)
                if self.admin_role == "Управляющий":
                    client_label.setStyleSheet(f"""
                                QLabel {{
                                    font-family: 'Unbounded';
                                    font-size: 12px;
                                    font-weight:bold;
                                    color: {'black' if is_enabled else '#a0a0a0'};
                                 
                                }}
                            """)
                else:
                    client_label.setStyleSheet(f"""
                                                    QLabel {{
                                                        font-family: 'Unbounded';
                                                        font-size: 14px;
                                                        font-weight:bold;
                                                        color: {'black' if is_enabled else '#a0a0a0'};
                                                  
                                                    }}
                                                """)
                client_label.setFixedWidth(fixed_width)
                info_layout.addWidget(client_label)

                # --- Добавляем info_layout (время и клиент) в entry_layout (основной горизонтальный layout) ---
                entry_layout.addLayout(info_layout)

                # --- Добавляем кнопку удаления, если self.admin_role == "Управляющий" ---
                if self.admin_role == "Управляющий":
                    delete_button = HoverButton("Х", 25, 25, 30, '#8F2D31', True, '#8F2D31', 'red', 5, 'red')

                    delete_button.clicked.connect(
                        lambda _, slot_id=item.get('slot_id'), widget=entry_widget, day_date=day:
                        self.delete_slot(slot_id, widget, day_date)
                    )

                    entry_layout.addWidget(delete_button, alignment=Qt.AlignRight)  # Кнопка закрепляется справа

                container_layout.addWidget(entry_widget, alignment=Qt.AlignTop | Qt.AlignHCenter)

        print("Добавляем кнопку '+'")
        add_button = HoverButton("+", 30, 30, 40, '#75A9A7', True, '', '', 5, '#5DEBE6')
        add_button.clicked.connect(lambda: self.open_add_slot_window(container_layout, day))

        if not is_enabled:
            add_button.disable_button()

        container_layout.addWidget(add_button, alignment=Qt.AlignCenter)

        print("Обновление виджета завершено.")

    def delete_slot(self, slot_id, slot_widget, day_date):
        """
        Удаляет слот по его ID из базы данных, интерфейса и кэша.
        """
        reply = QMessageBox.question(
            self, "Удаление слота",
            "Вы уверены, что хотите удалить этот слот?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 1. Удаление из базы данных
            query = "DELETE FROM training_slots WHERE slot_id = %s"
            execute_query(query, (slot_id,), fetch=False)

            # 2. Удаление из интерфейса (из виджета)
            slot_widget.setParent(None)
            slot_widget.deleteLater()

            # 3. Удаление из `schedule_cache`
            cache_key = None
            for key in self.schedule_cache.keys():
                if key[0] == self.selected_trainer_id and day_date in self.schedule_cache[key]:
                    cache_key = key
                    break

            if cache_key:
                updated_slots = [slot for slot in self.schedule_cache[cache_key][day_date] if
                                 slot["slot_id"] != slot_id]

                if updated_slots:
                    self.schedule_cache[cache_key][day_date] = updated_slots
                else:
                    del self.schedule_cache[cache_key][day_date]  # Удаляем день, если слоты закончились

                    # Если после удаления `day_date` больше нет данных, удаляем `cache_key`
                    if not self.schedule_cache[cache_key]:
                        del self.schedule_cache[cache_key]

                print(f"Слот {slot_id} удалён из кэша для {day_date}")

            QMessageBox.information(self, "Удаление", "Слот успешно удалён.")

    def switch_to_page(self, page):
        if page == self.main_page:
            self.profile_button.attrib = "stroke"
            self.profile_button.svg_path = resources_path("src/group.svg")
            self.profile_button.load_svg_with_color()
            self.profile_button.update_buffer()
            self.profile_button.update()
            self.profile_button.clicked.disconnect()
            self.profile_button.clicked.connect(lambda: self.switch_to_page(self.schedule_page))
        elif page == self.schedule_page or page == self.administrator_page:
            self.profile_button.attrib = "fill"
            self.profile_button.svg_path = resources_path("src/home.svg")
            self.profile_button.load_svg_with_color()
            self.profile_button.update_buffer()
            self.profile_button.update()

            self.profile_button.clicked.disconnect()
            self.profile_button.clicked.connect(lambda: self.switch_to_page(self.main_page))
        if self.schedule_group.isVisible() and self.week_frame.isVisible() and self.from_add_client:
            self.from_add_client = False
        elif self.schedule_group.isVisible() and self.week_frame.isVisible() and not self.from_add_client:
            self.selected_client = None
            self.subscription_data = None
            self.from_add_client = False
            self.update_days(self.current_week, self.selected_trainer_id)
        elif self.from_add_client:
            self.from_add_client = False
        QApplication.processEvents()
        self.stack.setCurrentWidget(page)




    def closeEvent(self, event):
        self.terminate_all_threads()
        event.accept()
