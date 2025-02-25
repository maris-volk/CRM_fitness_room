# chart.py

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QSizePolicy, QHBoxLayout, QToolTip
from PyQt5.QtChart import QChart, QChartView, QBarSet, QBarSeries, QBarCategoryAxis, QValueAxis
from PyQt5.QtGui import QPainter, QColor, QFont, QBrush, QCursor
from PyQt5.QtCore import Qt, QMargins, pyqtSignal, QObject
import datetime
import logging

from database import (
    get_max_visitors_per_hour,
    get_average_visitors_per_weekday,
    get_average_visitors_per_month, get_average_visitors_per_week_in_month,
)
from hover_button import SvgHoverButton
from utils import WorkerThread, resources_path

logger = logging.getLogger(__name__)

class ChartWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_period = datetime.date.today()
        self.granularity = 'day'  # 'day', 'week', 'month', 'year'
        self.is_fetching = False  # для управления потоками
        self.chart_view = self.create_chart_view()
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(10)

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(10)

        self.prev_button = SvgHoverButton(resources_path("src/prev.svg"), width=40, height=50,
                                                default_color='#75A9A7',
                                                hover_color="#88F9F5")


        self.prev_button.clicked.connect(self.go_prev)  # Подключение метода go_prev
        top_layout.addWidget(self.prev_button, alignment=Qt.AlignVCenter)

        # диаграмма
        self.chart_view = self.chart_view

        self.chart_view.setMinimumWidth(600)  # Устанавливаем минимальную ширину
        top_layout.addWidget(self.chart_view)

        self.next_button = SvgHoverButton(resources_path("src/next.svg"), width=40, height=50,
                                                default_color='#75A9A7',
                                                hover_color="#88F9F5")

        self.next_button.setStyleSheet("""
            QPushButton {
                background-color: #628F8D;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #75A9A7;
            }
        """)
        self.next_button.clicked.connect(self.go_next)  # Подключение метода go_next
        top_layout.addWidget(self.next_button, alignment=Qt.AlignVCenter)

        self.layout.addLayout(top_layout)

        # кнопки выбора периода
        bottom_layout = QHBoxLayout()
        bottom_layout.setAlignment(Qt.AlignHCenter)
        bottom_layout.setContentsMargins(30, 0, 30, 0)
        bottom_layout.setSpacing(15)

        # кнопки выбора периода
        self.day_button = QPushButton("День")
        self.day_button.setFixedSize(80, 30)
        self.day_button.setStyleSheet(self.get_period_button_style(selected=True))
        self.day_button.clicked.connect(lambda: self.set_granularity('day'))
        bottom_layout.addWidget(self.day_button,Qt.AlignCenter)


        self.week_button = QPushButton("Неделя")
        self.week_button.setFixedSize(80, 30)
        self.week_button.setStyleSheet(self.get_period_button_style(selected=False))
        self.week_button.clicked.connect(lambda: self.set_granularity('week'))
        bottom_layout.addWidget(self.week_button,Qt.AlignCenter)

        self.month_button = QPushButton("Месяц")
        self.month_button.setFixedSize(80, 30)
        self.month_button.setStyleSheet(self.get_period_button_style(selected=False))
        self.month_button.clicked.connect(lambda: self.set_granularity('month'))
        bottom_layout.addWidget(self.month_button,Qt.AlignCenter)

        self.year_button = QPushButton("Год")
        self.year_button.setFixedSize(80, 30)
        self.year_button.setStyleSheet(self.get_period_button_style(selected=False))
        self.year_button.clicked.connect(lambda: self.set_granularity('year'))
        bottom_layout.addWidget(self.year_button,Qt.AlignRight)

        # добавляем растяжку для выравнивания кнопок по центру


        self.layout.addLayout(bottom_layout)

        self.update_chart()

    def get_period_button_style(self, selected=False):
        """
        Возвращает стиль для кнопок выбора периода.
        """
        if selected:
            return """
                QPushButton {
                    background-color: #628F8D;
                    color: white;
                    border: 2px solid Gold;
                    border-radius: 5px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #75A9A7;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: #5DEBE6;
                    color: white;
                    border: 2px solid #628F8D;
                    border-radius: 5px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #628F8D;
                }
            """

    def get_week_number_within_month(self, date):
        """
        номер недели внутри месяца для данной даты.
        неделя с понедельника.
        """
        first_day = date.replace(day=1)
        first_weekday = first_day.weekday()  # 0 = Monday, 6 = Sunday
        # в какую неделю попадает текущая дата
        week_number = ((date.day + first_weekday - 1) // 7) + 1
        return week_number

    def create_chart_view(self):
        """
        графическое представление данных с сохранением оригинальных стилей.
        """
        logger.info("Создание диаграммы")

        set0 = QBarSet("Посетители")

        set0.setColor(QColor("#628F8D"))

        series = QBarSeries()
        series.append(set0)


        chart = QChart()
        chart.addSeries(series)
        heute = datetime.date.today()

        # форматирование даты в зависимости от гранулярности
        formatiertes_datum = heute.strftime("%d.%m.%Y")
        chart.setTitle(f"{formatiertes_datum}")

        title_font = QFont("Unbounded", 12, QFont.Bold)
        chart.setTitleFont(title_font)
        chart.setTitleBrush(QBrush(QColor("black")))

        categories = ["08-10", "10-12", "12-14", "14-16", "16-18", "18-20", "20-22"]
        axisX = QBarCategoryAxis()
        axisX.append(categories)

        axisY = QValueAxis()
        axisY.setLabelsVisible(False)  # скрываем подписи оси Y

        axis_font = QFont("Unbounded", 8)  # размер шрифта для подписей оси X
        axisX.setLabelsFont(axis_font)
        axisY.setLabelsFont(axis_font)
        axisX.setLabelsAngle(45)  # поворотна 45 градусов
        chart.addAxis(axisX, Qt.AlignBottom)  # ось X снизу
        chart.addAxis(axisY, Qt.AlignLeft)

        series.attachAxis(axisX)
        series.attachAxis(axisY)
        chart.setMargins(QMargins(10, 10, 10, 10))

        self.chart = chart  # Обязательно присваиваем self.chart
        logger.info("self.chart успешно создан")

        chart_view = QChartView(chart)
        chart_view.setStyleSheet("""
                    border: 2.7px solid #628F8D;
                    border-radius: 18px;     
                    background-color: white; 
        """)

        # chart_view.setMinimumSize(441, 340)
        # chart_view.setMaximumSize(441, 340)
        chart_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # расширение
        chart_view.setMinimumWidth(600)
        chart_view.setRenderHint(QPainter.Antialiasing)
        series.hovered.connect(self.show_tooltip)
        return chart_view

    def show_tooltip(self, status, barset, index):
        """
        Показывает всплывающую подсказку с количеством посетителей.
        """
        if not status:  # Если курсор ушел с элемента, ничего не делаем
            return

        try:
            if isinstance(barset, QBarSet) and isinstance(index, int):
                value = barset.at(index)
            elif isinstance(barset, int) and isinstance(index, QBarSet):
                value = index.at(barset)  # Поменялись местами
            else:
                logger.warning(f"Неверные данные в сигнале hovered: barset={barset}, index={index}")
                return

            # Убираем `.0`, если число целое
            tooltip_text = f"Посетители: {int(value) if value.is_integer() else round(value, 1)}"
            self.setFocus()
            QToolTip.showText(QCursor.pos(), tooltip_text)

        except Exception as e:
            logger.error(f"Ошибка в show_tooltip: {e}")

    def update_chart(self):
        """
        обновление диаграммы в зависимости от текущей гранулярности и периода.
        """
        if self.is_fetching:
            logger.info("Запрос уже выполняется. Ожидание завершения.")
            return

        self.is_fetching = True
        self.set_buttons_enabled(False)

        logger.info(f"Обновление диаграммы: Гранулярность={self.granularity}, Период={self.current_period}")

        if self.granularity == 'day':
            start_date = self.current_period
            end_date = self.current_period
            # запрос в отдельном потоке
            self.fetch_data_thread = WorkerThread(get_max_visitors_per_hour, start_date)
            self.fetch_data_thread.result_signal.connect(
                lambda data: self.process_chart_data(
                    data,
                    ["08-10", "10-12", "12-14", "14-16", "16-18", "18-20", "20-22"],
                    f"{start_date.strftime('%d.%m.%Y')}"
                )
            )
            self.fetch_data_thread.finished_signal.connect(self.on_fetch_finished)
            self.fetch_data_thread.start()
        elif self.granularity == 'week':
            start_date = self.current_period - datetime.timedelta(days=self.current_period.weekday())
            end_date = start_date + datetime.timedelta(days=6)
            week_number = self.get_week_number_within_month(start_date)
            self.fetch_data_thread = WorkerThread(get_average_visitors_per_weekday, start_date, end_date)
            self.fetch_data_thread.result_signal.connect(
                lambda data: self.process_chart_data(
                    data,
                    ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'],
                    f"Неделя {week_number} {start_date.strftime('%m.%Y')}"
                )
            )
            self.fetch_data_thread.finished_signal.connect(self.on_fetch_finished)
            self.fetch_data_thread.start()
        elif self.granularity == 'month':
            start_date = self.current_period.replace(day=1)
            next_month = start_date.replace(day=28) + datetime.timedelta(days=4)  # на следующий месяц
            end_date = next_month - datetime.timedelta(days=next_month.day)
            month = start_date.month
            year = start_date.year
            # Запуск запроса в отдельном потоке
            self.fetch_data_thread = WorkerThread(get_average_visitors_per_week_in_month, month, year)
            self.fetch_data_thread.result_signal.connect(
                lambda data: self.process_chart_data(
                    data,
                    ["Нед 1", "Нед 2", "Нед 3", "Нед 4", "Нед 5"],
                    f"{start_date.strftime('%m.%Y')}"
                )
            )
            self.fetch_data_thread.finished_signal.connect(self.on_fetch_finished)
            self.fetch_data_thread.start()
        elif self.granularity == 'year':
            year = self.current_period.year
            self.fetch_data_thread = WorkerThread(get_average_visitors_per_month, year)
            self.fetch_data_thread.result_signal.connect(
                lambda data: self.process_chart_data(
                    data,
                    [f"{i:02}" for i in range(1, 13)],  # числовые значения месяцев
                    f"{year}"
                )
            )
            self.fetch_data_thread.finished_signal.connect(self.on_fetch_finished)
            self.fetch_data_thread.start()
        else:
            logger.error(f"Неизвестная гранулярность: {self.granularity}")
            self.is_fetching = False
            self.set_buttons_enabled(True)
            return

    def on_fetch_finished(self):
        """
        по завершении потока загрузки данных.
        """
        self.is_fetching = False
        self.set_buttons_enabled(True)

    def process_chart_data(self, data, categories, title):
        """
        полученные данные и диаграмма.
        """
        if data is None:
            logger.error("Нет данных для обновления диаграммы")
            self.on_fetch_finished()
            return

        self.chart.removeAllSeries()
        series = QBarSeries()
        self.chart.addSeries(series)

        set_visitors = QBarSet("Посетители")
        set_visitors.setColor(QColor("#628F8D"))

        for category in categories:
            set_visitors.append(data.get(category, 0))

        series.append(set_visitors)
        series.hovered.connect(self.show_tooltip)

        axis_x = QBarCategoryAxis()
        axis_x.append(categories)

        axis_y = QValueAxis()
        max_value = max(set_visitors) if set_visitors else 10
        axis_y.setRange(0, max_value + 5)
        axis_y.setLabelsVisible(False)  # Скрываем подписи оси Y

        self.chart.removeAxis(self.chart.axisX())
        self.chart.removeAxis(self.chart.axisY())

        self.chart.addAxis(axis_x, Qt.AlignBottom)
        self.chart.addAxis(axis_y, Qt.AlignLeft)

        series.attachAxis(axis_x)
        series.attachAxis(axis_y)

        self.chart.setTitle(title)  # title только период

        # легенда
        self.chart.legend().setVisible(True)
        self.chart.legend().setAlignment(Qt.AlignBottom)

        self.on_fetch_finished()

    def set_granularity(self, granularity):
        """
        устанавливка гранулярности и обновление диаграммы.
        """
        if self.is_fetching:
            logger.info("Обновление гранулярности уже выполняется. Ожидание завершения.")
            return  # игнорирование изменение гранулярности

        self.granularity = granularity
        logger.info(f"Установка гранулярности: {self.granularity}")

        self.day_button.setStyleSheet(self.get_period_button_style(selected=(granularity == 'day')))
        self.week_button.setStyleSheet(self.get_period_button_style(selected=(granularity == 'week')))
        self.month_button.setStyleSheet(self.get_period_button_style(selected=(granularity == 'month')))
        self.year_button.setStyleSheet(self.get_period_button_style(selected=(granularity == 'year')))

        self.update_chart()

    def set_buttons_enabled(self, enabled):

        self.prev_button.setEnabled(enabled)
        self.next_button.setEnabled(enabled)
        self.day_button.setEnabled(enabled)
        self.week_button.setEnabled(enabled)
        self.month_button.setEnabled(enabled)
        self.year_button.setEnabled(enabled)

    def go_prev(self):
        """
        к предыдущему периоду в зависимости от гранулярности.
        """
        if self.is_fetching:
            logger.info("Переход к предыдущему периоду уже выполняется. Ожидание завершения.")
            return

        if self.granularity == 'day':
            self.current_period -= datetime.timedelta(days=1)
        elif self.granularity == 'week':
            self.current_period -= datetime.timedelta(weeks=1)
        elif self.granularity == 'month':
            month = self.current_period.month - 1 or 12
            year = self.current_period.year - 1 if self.current_period.month == 1 else self.current_period.year
            self.current_period = self.current_period.replace(year=year, month=month, day=1)
        elif self.granularity == 'year':
            self.current_period = self.current_period.replace(year=self.current_period.year - 1)
        self.update_chart()

    def go_next(self):
        """
        к следующему периоду в зависимости от гранулярности.
        """
        if self.is_fetching:
            logger.info("Переход к следующему периоду уже выполняется. Ожидание завершения.")
            return

        if self.granularity == 'day':
            self.current_period += datetime.timedelta(days=1)
        elif self.granularity == 'week':
            self.current_period += datetime.timedelta(weeks=1)
        elif self.granularity == 'month':
            month = self.current_period.month + 1 if self.current_period.month < 12 else 1
            year = self.current_period.year + 1 if self.current_period.month == 12 else self.current_period.year
            self.current_period = self.current_period.replace(year=year, month=month, day=1)
        elif self.granularity == 'year':
            self.current_period = self.current_period.replace(year=self.current_period.year + 1)
        self.update_chart()
