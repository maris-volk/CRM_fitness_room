import sys

from PyQt5 import QtWidgets, QtGui
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton, \
    QGraphicsDropShadowEffect
from PyQt5.QtChart import QChartView, QBarSeries, QBarSet, QChart, QBarCategoryAxis, QValueAxis
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPainter, QFont


class HoverButton(QPushButton):
    def __init__(self, text=''):
        super().__init__(text)
        self.setMouseTracking(True)  # Включаем отслеживание мыши
        self.initUI()

    def initUI(self):
        self.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                border: 2.7px solid #75A9A7;
                width: 250.4px; 
                height: 40.9px;
                padding: 20.5px 39.1px 20.4px 40.3px;
                border-radius: 18px;
                font-weight: 500;
                font-family: 'Unbounded';
                font-size: 30.5px;
            }
        """)
        self.apply_default_shadow()

    def apply_default_shadow(self):
        shadow = QGraphicsDropShadowEffect()

        shadow.setBlurRadius(0)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QColor(184, 182, 215, 178))

        self.setGraphicsEffect(shadow)

    def apply_hover_shadow(self):
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10.9)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, int(255 * (178 / 255))))

        self.setGraphicsEffect(shadow)

    def enterEvent(self, event):
        self.apply_hover_shadow()
        self.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                border: 2.7px solid #5DEBE6;
                width: 250.4px; 
                height: 40.9px;
                padding: 20.5px 39.1px 20.4px 40.3px;
                border-radius: 18px;
                font-family: 'Unbounded';
                font-weight: 500;
                font-size: 22.5px;
            }
        """)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setStyleSheet("""
                    QPushButton {
                        background-color: #ffffff;
                        border: 2.7px solid #75A9A7;
                        width: 250.4px; 
                        height: 40.9px;
                        padding: 20.5px 39.1px 20.4px 40.3px;
                        border-radius: 18px;
                        font-weight: 500;
                        font-family: 'Unbounded';
                        font-size: 22.5px;
                    }
                """)

        self.apply_default_shadow()
        super().leaveEvent(event)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Учёт посещемости клиентов фитнес-зала")
        self.setGeometry(100, 100, 1200, 800)  # Изменение размеров окна
        self.setStyleSheet("background-color: white;")

        self.initUI()

    def initUI(self):
        main_layout = QHBoxLayout(self)

        left_panel = QVBoxLayout()

        new_visitor_button = HoverButton("Новый посетитель")
        scan_card_button = HoverButton("Сканировать карту")
        visitor_list_button = HoverButton("Список посетителей")
        trainers_button = HoverButton("Тренера")

        left_panel.addWidget(new_visitor_button)
        left_panel.addWidget(scan_card_button)
        left_panel.addWidget(visitor_list_button)
        left_panel.addWidget(trainers_button)

        central_panel = QVBoxLayout()
        duty_trainers_label = QLabel("Тренера на дежурстве:")
        center_frame = QFrame()
        center_frame_layout = QHBoxLayout(center_frame)
        center_frame_layout.setAlignment(Qt.AlignLeft)

        for _ in range(3):
            image_placeholder = QLabel()
            image_placeholder.setFixedSize(93, 93)  # Изменение размеров
            image_placeholder.setStyleSheet("""
                background-color: gray;
                margin-left: 2px;
                border-radius: 18px 18px 18px 18px;
                border: 2.7px solid #75A9A7;
                padding: 0px 2.4px 0px 3.2px;

            """)
            center_frame_layout.addWidget(image_placeholder)

        central_panel.addWidget(duty_trainers_label)
        central_panel.addWidget(center_frame)

        chart_view = self.create_chart_view()
        central_panel.addWidget(chart_view)

        right_panel = QVBoxLayout()

        profile_picture_label = QLabel("фото профиля")
        name_role_label = QLabel("Имя Фамилия\nАдминистратор")

        right_panel.addWidget(profile_picture_label)
        right_panel.addStretch()
        right_panel.addWidget(name_role_label)

        main_layout.addLayout(left_panel)
        main_layout.addStretch()
        main_layout.addLayout(central_panel)
        main_layout.addStretch()
        main_layout.addLayout(right_panel)

        self.setLayout(main_layout)

    def create_chart_view(self):
        set0 = QBarSet("Посетители")
        set0.append([1, 2, 3, 4, 5])

        set0.setColor(QColor("#628F8D"))

        series = QBarSeries()
        series.append(set0)
        series.hovered.connect(self.show_tooltip)

        chart = QChart()
        chart.addSeries(series)
        chart.setTitle("Активность по времени")

        title_font = QFont("Unbounded", 11, QFont.Bold)
        chart.setTitleFont(title_font)

        categories = ["00-03", "03-06", "06-09", "09-12", "12-15"]
        axisX = QBarCategoryAxis()
        axisX.append(categories)

        axisY = QValueAxis()
        axisY.setLabelsVisible(False)

        # Установка шрифта для осей
        axis_font = QFont("Unbounded", 3)
        axisX.setLabelsFont(axis_font)
        axisY.setLabelsFont(axis_font)
        chart.addAxis(axisX, Qt.AlignTop)
        chart.addAxis(axisY, Qt.AlignLeft)

        series.attachAxis(axisX)
        series.attachAxis(axisY)

        chart_view = QChartView(chart)
        chart_view.setMinimumSize(541, 440)
        chart_view.setMaximumSize(541, 440)
        chart_view.setRenderHint(QPainter.Antialiasing)
        return chart_view

    def show_tooltip(self, status, index):
        if status:
            value = index + 1
            tooltip_text = f"Посетители: {value}"
            QtWidgets.QToolTip.showText(QtGui.QCursor.pos(), tooltip_text)


app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec_())