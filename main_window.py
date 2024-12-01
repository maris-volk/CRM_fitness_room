import datetime

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtChart import QChartView, QBarSeries, QBarSet, QChart, QBarCategoryAxis, QValueAxis
from PyQt5.QtCore import QTimer
from PyQt5.QtCore import Qt, QMargins, pyqtSignal, QThread
from PyQt5.QtGui import QColor, QPainter, QFont, QBrush, QIcon
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton

from add_visitor_window import AddVisitorWindow
from database import get_active_visitors, get_duty_trainers, get_visitors_in_gym, check_visitor_in_gym, end_attendance, \
    start_attendance
from hover_button import HoverButton
from utils import scan_card, WorkerThread



class MainWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fitness Gym Attendance Tracker")
        self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet("background-color: white;")
        self.initUI()

        # Create WorkerThreads for fetching data
        self.fetch_data_thread = WorkerThread(self.fetch_data)
        self.fetch_data_thread.result_signal.connect(self.update_data)
        self.fetch_data_thread.start()

        # Timer to refresh data periodically
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.fetch_and_update_data)
        self.timer.start(10000)  # update every 10 seconds

    def fetch_data(self):
        # This method will be executed in a separate thread
        try:
            total_visitors = get_active_visitors()
            visitors_in_gym = get_visitors_in_gym()
            duty_trainers = get_duty_trainers()

            # Return the fetched data
            return (total_visitors, visitors_in_gym, duty_trainers)
        except Exception as error:
            return None  # Return None in case of error

    def fetch_and_update_data(self):
        # Start the thread to fetch and update data
        self.fetch_data_thread = WorkerThread(self.fetch_data)
        self.fetch_data_thread.result_signal.connect(self.update_data)
        self.fetch_data_thread.start()

    def update_data(self, result):
        if result is None:
            return  # exit if no data is available

        total_visitors, visitors_in_gym, duty_trainers = result

        # Update labels with the latest visitor and trainer data
        self.visitors_label.setText(f"{len(total_visitors)} посетителей\n{len(visitors_in_gym)} в зале")
        self.trainers_label.setText(f"{len(duty_trainers)} тренеров\n{len(duty_trainers)} на смене")

    def show_add_visitor_window(self):
        if not hasattr(self, 'add_visitor_window') or not self.add_visitor_window.isVisible():
            self.add_visitor_window = AddVisitorWindow()
            self.add_visitor_window.show()
            self.add_visitor_window.raise_()

    def scan_card_for_attendance(self):
        card_number = scan_card()

        if card_number:
            # check if the visitor is already in the gym
            result = check_visitor_in_gym(card_number)
            visitor_id, check_in_time, check_out_time = result
            if result[1]:
                end_attendance(visitor_id)
            else:
                start_attendance(visitor_id)

    def initUI(self):
        main_layout = QVBoxLayout(self)

        # top panel with visitor and trainer data
        top_panel = QHBoxLayout()
        top_frame = QFrame()
        top_frame.setStyleSheet("""
            background-color: white;
            border-bottom: 3px solid #628F8D;
            width: 1920px;
            height: 131px;
        """)

        # visitor and trainer count labels
        self.visitors_label = QLabel()
        self.trainers_label = QLabel()

        total_visitors = get_active_visitors()
        visitors_in_gym = get_visitors_in_gym()
        duty_trainers = get_duty_trainers()
        self.visitors_label.setText(f"{len(total_visitors)} посетителей\n{len(visitors_in_gym)} в зале")
        self.trainers_label.setText(f"{len(duty_trainers)} тренеров\n{len(duty_trainers)} на смене")

        top_panel.addWidget(self.visitors_label)
        top_panel.addStretch()
        top_panel.addWidget(self.trainers_label)
        top_panel.addStretch()
        top_panel.addWidget(QLabel("Расписание тренеров"))

        # profile button
        profile_button = QPushButton()
        profile_button.setFixedSize(51, 51)
        profile_button.setIcon(QIcon("Group.png"))
        profile_button.setIconSize(QtCore.QSize(51, 51))
        profile_button.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
            }
            QPushButton:pressed {
                background-color: lightgray; 
            }
        """)

        top_panel.addStretch()
        top_panel.addWidget(profile_button)
        top_panel.setContentsMargins(130, 0, 130, 20)

        top_frame.setLayout(top_panel)

        # apply style to labels
        label_style = """
            font-family: 'Unbounded';
            font-size: 22px;
            border: none;
            weight:400;
        """

        for widget in top_frame.children():
            if isinstance(widget, QLabel):
                widget.setStyleSheet(label_style)

        main_layout.addWidget(top_frame)

        # main content area layout
        content_layout = QHBoxLayout()

        # left panel with buttons
        left_panel = QVBoxLayout()
        left_panel.setContentsMargins(130, 30, 130, 360)
        left_panel.setSpacing(0)

        new_visitor_button = HoverButton("Новый посетитель")
        new_visitor_button.clicked.connect(self.show_add_visitor_window)
        scan_card_button = HoverButton("Сканировать карту")
        scan_card_button.clicked.connect(self.scan_card_for_attendance)
        visitor_list_button = HoverButton("Список посетителей")
        left_panel.addWidget(new_visitor_button)
        left_panel.addWidget(scan_card_button)
        left_panel.addWidget(visitor_list_button)

        # central panel with duty trainers
        central_panel = QVBoxLayout()

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

        # frame for displaying trainers on duty
        center_frame = QFrame()
        center_frame_layout = QHBoxLayout(center_frame)
        center_frame_layout.setAlignment(Qt.AlignLeft)

        # display first 3 duty trainers
        for trainer in duty_trainers[:3]:
            image_placeholder = QLabel(f"{trainer[0]} {trainer[1]}")
            image_placeholder.setAlignment(Qt.AlignTop)
            image_placeholder.setFixedSize(93, 93)
            image_placeholder.setStyleSheet("""
                background-color: gray;
                border-radius: 18px;
                border: 2.7px solid #75A9A7;
                padding: 0px 2px 0px 3px;
                margin-top: 0px;
            """)
            center_frame_layout.addWidget(image_placeholder)

        central_panel.addWidget(duty_trainers_label)
        central_panel.addWidget(center_frame)

        # chart showing attendance
        chart_view = self.create_chart_view()
        central_panel.addWidget(chart_view)
        central_panel.setContentsMargins(80, 60, 100, 150)
        central_panel.setSpacing(15)

        right_panel = QVBoxLayout()
        right_panel.setContentsMargins(150, 80, 130, 200)

        # placeholder for profile picture
        photo_placeholder = QLabel()
        photo_placeholder.setFixedSize(325, 433)
        photo_placeholder.setStyleSheet("""
            background-color: lightgray;
            border-radius: 10px;
            border: 3px solid #75A9A7;
        """)
        right_panel.addWidget(photo_placeholder)

        # name and role labels
        name_label = QLabel("Имя Фамилия")
        role_label = QLabel("Администратор")
        name_label.setAlignment(Qt.AlignLeft)
        role_label.setAlignment(Qt.AlignLeft)
        name_label.setStyleSheet("""
            font-family: 'Unbounded';
            font-size: 36px;
        """)
        role_label.setStyleSheet("""
            font-family: 'Unbounded';
            font-size: 22px;
        """)

        right_panel.addWidget(name_label)
        right_panel.addWidget(role_label)
        right_panel.addStretch()

        content_layout.addLayout(left_panel)
        content_layout.addStretch()
        content_layout.addLayout(central_panel)
        content_layout.addStretch()
        content_layout.addLayout(right_panel)

        # set main layout
        main_layout.addLayout(content_layout)

    def create_chart_view(self):
        set0 = QBarSet("Посетители")
        set0.append([1, 2, 3, 4, 5, 3, 5])

        set0.setColor(QColor("#628F8D"))

        series = QBarSeries()
        series.append(set0)
        series.hovered.connect(self.show_tooltip)

        chart = QChart()
        chart.addSeries(series)
        heute = datetime.date.today()

        # Formatieren des Datums als 'TT.MM.JJ'
        formatiertes_datum = heute.strftime("%d.%m.%y")

        # Festlegen des Titels mit dem formatierten Datum
        chart.setTitle(f"{formatiertes_datum}")

        title_font = QFont("Unbounded", 15, QFont.Bold)

        chart.setTitleFont(title_font)
        title_brush = QBrush(QColor("black"))

        categories = ["08-10", "10-12", "12-14", "14-16", "16-18", "18-20", "20-22"]
        axisX = QBarCategoryAxis()
        axisX.append(categories)

        axisY = QValueAxis()
        axisY.setLabelsVisible(False)

        # Установка шрифта для осей
        axis_font = QFont("Unbounded", 5)
        axisX.setLabelsFont(axis_font)
        axisY.setLabelsFont(axis_font)
        chart.addAxis(axisX, Qt.AlignTop)
        chart.addAxis(axisY, Qt.AlignLeft)

        series.attachAxis(axisX)
        series.attachAxis(axisY)
        chart.setMargins(QMargins(-30, 0, 0, -18))

        chart_view = QChartView(chart)
        chart_view.setStyleSheet("""
                    border: 2.7px solid #628F8D; /* Цвет и толщина границы */
                    border-radius: 18px;      /* Радиус закругления углов */
                    background-color: white; /* Цвет фона для проверки */

        """)
        chart_view.setMinimumSize(441, 340)
        chart_view.setMaximumSize(441, 340)
        chart_view.setRenderHint(QPainter.Antialiasing)
        return chart_view

    def show_tooltip(self, status, index):
        if status:
            value = index + 1
            tooltip_text = f"Посетители: {value}"
            QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), tooltip_text)
