import re

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QGridLayout, QDialog, QPushButton, QFrame, \
    QGraphicsDropShadowEffect, QMessageBox
from PyQt5.QtCore import Qt, QRectF, QPoint, pyqtSignal, QDate
from PyQt5.QtGui import QPainter, QColor, QPen
from hover_button import HoverButton
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QGridLayout, QLineEdit, QComboBox, QHBoxLayout, QPushButton
from PyQt5.QtCore import Qt

from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QFrame
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel, QLineEdit, QHBoxLayout, QFrame
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel, QLineEdit, QVBoxLayout
from PyQt5.QtCore import Qt

from utils import TariffCalculator, WorkerThread

current_active_widget = None
dict_widget = {}
qwidget_clicked = False
calculator = TariffCalculator()


class SelectionGroupWidget(QFrame):
    clicked = pyqtSignal()

    def __init__(self, idd: int, options: list, group_type: str, parent=None):
        super().__init__(parent)
        self.options = options
        self.setStyleSheet(f"""
            QFrame#bodyy_{idd}{{
            gap: 0px;
            border-radius: 18px;
            opacity: 0px;
            margin: 0px;
            font-size:15px;
            border: 2px solid #B0B0B0;
            }}
        """)
        self.setObjectName(f"bodyy_{idd}")
        self.group_type = group_type
        self.selected_option = None
        self.layout = self.create_selection_widget()
        self.setFixedHeight(50)
        self.setFixedWidth(300)
        self.setLayout(self.layout)

    def get_selected_option(self):
        """Возвращает текущую выбранную опцию."""
        return self.selected_option

    def set_selected_option(self, option):
        """Устанавливает указанную опцию как выбранную."""
        if option in self.options:
            self.selected_option = option
            self.update_selection_highlight()

    def update_selection_highlight(self):
        """Обновляет выделение для текущей выбранной опции."""
        for i in range(self.layout.count()):
            label = self.layout.itemAt(i).widget()
            if isinstance(label, SelectableLabel):
                if label.text() == self.selected_option:
                    label.set_selected(True)
                else:
                    label.set_selected(False)

    def select_closest_option(self):
        """Выбирает ближайшую доступную опцию, если текущая недоступна."""
        if self.selected_option not in self.options:
            if self.options:
                self.selected_option = self.options[-1]  # Последняя доступная неделя
                self.update_selection_highlight()

    def apply_styles_to_selected_option(self):
        """Применяет стили к выбранной кнопке."""
        for i in range(self.layout.count()):
            widget = self.layout.itemAt(i).widget()
            if isinstance(widget, SelectableLabel):
                if widget.text() == self.selected_option:
                    widget.set_selected(True)
                else:
                    widget.set_selected(False)

    def update_button_colors(self):
        """Обновляет цвет кнопок в зависимости от активности родительского виджета"""
        color = 'black' if self.is_parent_active else '#B0B0B0'

        for i in range(self.layout.count()):
            label = self.layout.itemAt(i).widget()
            if isinstance(label, SelectableLabel):
                label.font_color_value = color
                label.selected_color_value = color
                label.hover_color_value = color
                label.apply_styles()

    def set_parent_active(self, is_active: bool):
        """Метод для обновления состояния активности родителя"""
        self.is_parent_active = is_active
        self.update_button_colors()

    def create_selection_widget(self):
        """Создает горизонтальный виджет для выбора параметра"""
        layout = QHBoxLayout()
        for option in self.options:
            label = SelectableLabel(option, font_size=15)
            label.setObjectName(f"{self.group_type}_{option}")
            label.clicked.connect(
                lambda opt=option, grp_type=self.group_type: self.select_option(opt, grp_type))
            layout.addWidget(label)
        return layout

    def select_option(self, option, group_type):
        """Выбор параметра"""
        self.selected_option = option
        self.deselect_other_labels()
        self.update_parent_options()

    def deselect_other_labels(self):
        """Снимает выделение с других меток в группе"""
        for label in self.layout.findChildren(SelectableLabel):
            if label.is_selected:
                label.set_selected(False)

    def update_parent_options(self):
        """Информирует родительский виджет об изменении выбора для обновления."""
        parent_widget = self.parent()
        if hasattr(parent_widget, "update_selected_options"):
            parent_widget.update_selected_options()
        elif hasattr(parent_widget, "update_week_selection"):
            parent_widget.update_week_selection()

    def update_week_selection(self):
        """Обрабатывает выбор недели через SelectionGroupWidget."""
        selected_week = self.week_buttons_group.selected_option
        if selected_week:
            week_number = int(selected_week.split()[0])
            self.update_days(week_number)

    def mousePressEvent(self, event):
        """Обрабатывает событие нажатия мыши."""
        global qwidget_clicked
        qwidget_clicked = True
        self.clicked.emit()

    def update_options(self, options):
        """Обновляет параметры виджета."""
        self.options = options

        while self.layout.count():
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.create_selection_widget1()

    def create_selection_widget1(self):
        for option in self.options:
            label = SelectableLabel(option, font_size=15)
            label.setObjectName(f"{self.group_type}_{option}")
            label.clicked.connect(
                lambda opt=option, grp_type=self.group_type: self.select_option(opt, grp_type))
            self.layout.addWidget(label)

    def mouseReleaseEvent(self, event):
        """Обрабатывает событие нажатия мыши."""
        global qwidget_clicked
        qwidget_clicked = False


class SubscriptionOptionWidget(QFrame):
    confirmed = pyqtSignal(dict)

    def __init__(self, period: str, classes: list, times: list, idd: int = 1):
        super().__init__()

        self.idd = idd
        global calculator
        self.calculator = calculator

        self.setFocusPolicy(Qt.StrongFocus)

        self.period = period  # Длительность периода
        self.classes = classes  # Варианты количества занятий
        self.times = times  # Варианты времени занятий

        self.selected_class_count = None  # Выбранное количество занятий
        self.selected_time = None  # Выбранное время занятия
        self.setStyleSheet(f"""
                      QFrame#parent_{idd}{{
                          border: 2.7px solid #B0B0B0;
                          gap: 0px;
                          border-radius: 18px;
                          opacity: 1;
                          font-weight: 500;
                          font-family: 'Unbounded';
                          font-size: 15px;
                          margin:0px;
                      }}
                      QLabel#head{{
                          font-size: 18px;
                      }}
                      QLineEdit#from_{idd}{{
                        font-family: 'Unbounded';
                        font-size: 14px;
                        padding: 10px 20.4px 10px 15px;
                        border-radius: 18px;
                        border: solid #B0B0B0;
                        border-width: 0px 0px 2.7px 2.7px;
                        background-color: transparent;
                     
                        margin-top: 10px;
                        margin-bottom: 10px;
                      }}
                      QLineEdit#until_{idd}{{
                        font-family: 'Unbounded';
                        font-size: 14px;
                        padding: 10px 20.4px 10px 15px;
                        border-radius: 18px;
                        border: solid #B0B0B0;
                        border-width: 0px 0px 2.7px 2.7px;
                        background-color: transparent;
                     
                        margin-top: 10px;
                        margin-bottom: 10px;
                      }}

                                        """)
        self.setObjectName(f'parent_{idd}')
        dict_widget[idd] = self
        self.initUI()

    def initUI(self):
        grid_layout = QGridLayout(self)

        # Первая строка - Заголовок
        label_title = QLabel(f"{self.period}", self)
        label_title.setObjectName('head')
        label_title.setAlignment(Qt.AlignCenter)
        grid_layout.addWidget(label_title, 0, 0, 1, 2)

        # Вторая строка - Дата начала и дата конца
        self.start_date_input = QLineEdit(self)
        self.start_date_input.setPlaceholderText("Дата начала")
        self.start_date_input.setObjectName(f"from_{self.idd}")

        self.end_date_input = QLineEdit(self)
        self.end_date_input.setPlaceholderText("Дата конца")
        self.end_date_input.setObjectName(f"until_{self.idd}")

        self.start_date_input.installEventFilter(self)
        self.end_date_input.installEventFilter(self)

        self.start_date_input.textChanged.connect(self.on_widget_interacted)
        self.end_date_input.textChanged.connect(self.on_widget_interacted)

        grid_layout.addWidget(self.start_date_input, 1, 0)
        grid_layout.addWidget(self.end_date_input, 1, 1)

        # Третья строка - Количество занятий
        label_class_count = QLabel("Количество занятий", self)
        grid_layout.addWidget(label_class_count, 2, 0, 1, 2, alignment=Qt.AlignCenter)

        # Четвертая строка - Виджет для выбора количества занятий
        self.class_count_widget = SelectionGroupWidget(self.idd, self.classes, "class", self)
        self.class_count_widget.clicked.connect(self.on_widget_interacted)

        grid_layout.addWidget(self.class_count_widget, 3, 0, 1, 2)

        # Пятая строка - Время занятий
        label_time = QLabel("Время занятий", self)
        grid_layout.addWidget(label_time, 4, 0, 1, 2, alignment=Qt.AlignCenter)

        self.time_widget = SelectionGroupWidget(self.idd, self.times, "time", self)
        self.time_widget.clicked.connect(self.on_widget_interacted)
        grid_layout.addWidget(self.time_widget, 5, 0, 1, 2)

        # Седьмая строка - Цена
        self.price_label = QLabel(f"", self)

        grid_layout.addWidget(self.price_label, 6, 0, 1, 2, alignment=Qt.AlignCenter)

        self.setLayout(grid_layout)
        if self.idd == 1:
            self.activate_first_widget()
        else:
            self.deactivate_widget()

    def get_result(self, result):
        if result is None:
            current_active_widget.price_label.setText(f"")
        else:
            current_active_widget.price_label.setText(f"{float(result) - 0.01}₽")

    def deactivate_widget(self):

        self.on_widget_interacted(True)

    def activate_first_widget(self):
        """Активировать первый виджет"""
        global current_active_widget
        current_active_widget = self
        self.on_widget_interacted()

    def update_selected_options(self):
        self.selected_class_count = self.class_count_widget.selected_option
        self.selected_time = self.time_widget.selected_option
        self.calculate_price()
        print(self.selected_class_count, self.selected_time)

    # def calculate_price(self):
    #     """Пример расчета цены"""
    #     # Можно реализовать более сложную логику расчета, учитывая выбранные параметры
    #     if self.selected_time and self.selected_class_count:
    #         print(self.selected_time,self.selected_class_count)
    #         key = f"{self.selected_class_count}-{self.selected_time}"
    #         print(key,self.prices)
    #         price = self.prices.get(key, 0)
    #     else:
    #         price = ''  # Если не выбраны все параметры
    #     return price

    def calculate_price(self):
        """Пример расчета цены"""
        if current_active_widget is not None:
            self.calculate_thread = WorkerThread(self.calculate_tariff_price, self.period, self.selected_class_count,
                                                 self.selected_time, 150)
            self.calculate_thread.result_signal.connect(current_active_widget.get_result)
            self.calculate_thread.start()
        else:
            return ''

    def calculate_tariff_price(self, period, k_class, k_time, base_price):
        """Вычисление тарифа в фоновом потоке."""
        try:

            price = self.calculator.calculate_price(period, k_class, k_time, base_price)
            return price
        except Exception as e:
            return None

    def eventFilter(self, object, event):
        if isinstance(object, QLineEdit) and event.type() == Qt.ClickFocus:
            if object == self.start_date_input:
                self.on_widget_interacted()
            elif object == self.end_date_input:
                self.on_widget_interacted()
            return False
        return super().eventFilter(object, event)

    def on_widget_interacted(self, deactivate: bool = False):
        """Обрабатывает взаимодействие с виджетом."""
        global current_active_widget
        if isinstance(deactivate, str):
            deactivate = False
            start_date_str = self.start_date_input.text()
            end_date_str = self.end_date_input.text()

            if self.start_date_input.hasFocus():
                print(self, 33434)
                self.update_end_date(start_date_str)
            elif self.end_date_input.hasFocus():
                self.update_start_date(end_date_str)

        # Если это не первый виджет с которым произошло взаимодействие
        if current_active_widget:
            cur_active_widget = current_active_widget

            if deactivate:
                iddd = self.idd
                cur_active_widget = self
            else:
                iddd = next((k for k, v in dict_widget.items() if v == cur_active_widget), None)
            cur_active_widget.class_count_widget.setStyleSheet(
                f"""
                QFrame#bodyy_{iddd}{{
                        gap: 0px;
                        border-radius: 18px;
                        opacity: 0px;
                        margin: 0px;
                        font-size:15px;
                        border: 2px solid #B0B0B0;
                        }}
                """
            )
            cur_active_widget.class_count_widget.set_parent_active(False)
            cur_active_widget.time_widget.setStyleSheet(
                f"""
                QFrame#bodyy_{iddd}{{
                        gap: 0px;
                        border-radius: 18px;
                        opacity: 0px;
                        margin: 0px;
                        font-size:15px;
                        border: 2px solid #B0B0B0;
                        }}
                """
            )
            cur_active_widget.time_widget.set_parent_active(False)
            cur_active_widget.setStyleSheet(f"""
            QFrame#parent_{iddd}{{
                          border: 2.7px solid #B0B0B0 ;
                          gap: 0px;
                          border-radius: 18px;
                          opacity: 1;
                          font-weight: 500;
                          font-family: 'Unbounded';
                          font-size: 15px;
                          margin:0px;
                      }}
                      QLabel#head{{
                          font-size: 18px;
                      }}

                      QLabel{{
                          color: #B0B0B0;
                      }}
                      QLineEdit#from_{iddd}{{
                        font-family: 'Unbounded';
                        font-size: 14px;
                        padding: 10px 20.4px 10px 15px;
                        border-radius: 18px;
                        border: solid #B0B0B0;
                        border-width: 0px 0px 2.7px 2.7px;
                        background-color: transparent;
                        color:  #B0B0B0;
                     
                        margin-top: 10px;
                        margin-bottom: 10px;
                      }}
                    QLineEdit#until_{iddd}{{
                        font-family: 'Unbounded';
                        font-size: 14px;
                        padding: 10px 20.4px 10px 15px;
                        border-radius: 18px;
                        border: solid #B0B0B0;
                        border-width: 0px 0px 2.7px 2.7px;
                        background-color: transparent;
                        color:  #B0B0B0;
                        margin-top: 10px;
                        margin-bottom: 10px;
                      }}
                      
                    
                      
                      
            """)
            if deactivate:
                return

        color = '#75A9A7' if self.idd == 1 else '#D3D700' if self.idd == 2 else '#5DEBE6'
        self.setStyleSheet(f"""
            QFrame#parent_{self.idd}{{
                          border: 2.7px solid {color};
                          gap: 0px;
                          border-radius: 18px;
                          opacity: 1;
                          font-weight: 500;
                          font-family: 'Unbounded';
                          font-size: 15px;
                          margin:0px;
                      }}
            QLabel#head{{
                          font-size: 18px;
                      }}
            QLineEdit#from_{self.idd}{{
                        font-family: 'Unbounded';
                        font-size: 14px;
                        padding: 10px 20.4px 10px 15px;
                        border-radius: 18px;
                        border: solid {color};
                        border-width: 0px 0px 2.7px 2.7px;
                        background-color: transparent;
                        color:  black;
                        margin-top: 10px;
                        margin-bottom: 10px;
                      }}
                    QLineEdit#until_{self.idd}{{
                        font-family: 'Unbounded';
                        font-size: 14px;
                        padding: 10px 20.4px 10px 15px;
                        border-radius: 18px;
                        border: solid {color};
                        border-width: 0px 0px 2.7px 2.7px;
                        background-color: transparent;
                        color:  black;
                        margin-top: 10px;
                        margin-bottom: 10px;
                      }}
                QFrame#body_{self.idd}{{
                        gap: 0px;
                        border-radius: 18px;
                        opacity: 0px;
                        margin: 0px;
                        font-size:15px;
                        border: 2px solid {color};
                        }}
            """)
        self.class_count_widget.setStyleSheet(
            f"""
                        QFrame#bodyy_{self.idd}{{
                                gap: 0px;
                                border-radius: 18px;
                                opacity: 0px;
                                margin: 0px;
                                font-size:15px;
                                border: 2px solid {color};
                                }}
                        """
        )
        self.class_count_widget.set_parent_active(True)
        self.time_widget.setStyleSheet(
            f"""
                        QFrame#bodyy_{self.idd}{{
                                gap: 0px;
                                border-radius: 18px;
                                opacity: 0px;
                                margin: 0px;
                                font-size:15px;
                                border: 2px solid {color};
                                }}
                        """
        )

        self.time_widget.set_parent_active(True)

        current_active_widget = self

    def update_end_date(self, start_date_str):
        today = QDate.currentDate()
        start_date = QDate.fromString(start_date_str, "dd.MM.yyyy")
        if start_date.isValid():
            pass
        else:
            self.end_date_input.setText('')
            return
        try:
            start_date = QDate.fromString(start_date_str, "dd.MM.yyyy")
            if self.period == "Месяц":
                if start_date < today:
                    self.start_date_input.setText(today.toString("dd.MM.yyyy"))
                    self.end_date_input.setText(today.addMonths(1).toString("dd.MM.yyyy"))
                else:
                    end_date = start_date.addMonths(1)
            elif self.period == "Полгода":
                if start_date < today:
                    self.start_date_input.setText(today.toString("dd.MM.yyyy"))
                    self.end_date_input.setText(today.addMonths(6).toString("dd.MM.yyyy"))
                else:
                    end_date = start_date.addMonths(6)
            elif self.period == "Год":
                if start_date < today:
                    self.start_date_input.setText(today.toString("dd.MM.yyyy"))
                    self.end_date_input.setText(today.addYears(1).toString("dd.MM.yyyy"))
                else:
                    end_date = start_date.addYears(1)

            self.end_date_input.setText(end_date.toString("dd.MM.yyyy"))
        except Exception as e:
            print(f"Ошибка при обновлении даты окончания: {e}")

    def update_start_date(self, end_date_str):

        today = QDate.currentDate()
        end_date = QDate.fromString(end_date_str, "dd.MM.yyyy")
        if end_date.isValid():
            pass
        else:
            self.start_date_input.setText('')
            return
        try:
            if self.period == "Месяц":
                if end_date.addMonths(-1) < today:
                    self.start_date_input.setText(today.toString("dd.MM.yyyy"))
                    self.end_date_input.setText(today.addMonths(1).toString("dd.MM.yyyy"))
                else:
                    start_date = end_date.addMonths(-1)
            elif self.period == "Полгода":
                if end_date.addMonths(-6) < today:
                    self.start_date_input.setText(today.toString("dd.MM.yyyy"))
                    self.end_date_input.setText(today.addMonths(6).toString("dd.MM.yyyy"))
                else:
                    start_date = end_date.addMonths(-6)
            elif self.period == "Год":
                if end_date.addMonths(-1) < today:
                    self.start_date_input.setText(today.toString("dd.MM.yyyy"))
                    self.end_date_input.setText(today.addYears(1).toString("dd.MM.yyyy"))
                else:
                    start_date = end_date.addYears(-1)

            self.start_date_input.setText(start_date.toString("dd.MM.yyyy"))
        except Exception as e:
            print(f"Ошибка при обновлении даты начала: {e}")


class SelectableLabel(QLabel):
    clicked = pyqtSignal()

    def __init__(self, text='', font_size: int = 10, font_color: str = 'black', hover_color: str = '#5DEBE6',
                 selected_color: str = '#8DF2F2', border_radius: float = 18, padding: str = '0px'):
        super().__init__(text)
        self.setMouseTracking(True)
        self.font_size_value = font_size
        self.font_color_value = font_color
        self.hover_color_value = hover_color
        self.selected_color_value = selected_color
        self.border_radius_value = border_radius
        self.font_padding_value = padding
        self.is_selected = False

        self.initUI()

    def initUI(self):
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)

        # self.adjustSize()
        self.setAlignment(Qt.AlignCenter)
        self.apply_styles()
        self.apply_default_shadow()

    def apply_styles(self):
        selected_border = self.selected_color_value if self.is_selected else self.hover_color_value
        selected_text_color = self.selected_color_value if self.is_selected else self.font_color_value
        self.setStyleSheet(f"""
        QLabel {{
            color: {selected_text_color};
            font-family: 'Unbounded';

            font-size: {self.font_size_value}px;
            cursor: pointer;

        }}
        """)

    def apply_default_shadow(self):
        """стандартная тень"""
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(0)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QColor(184, 182, 215, 178))
        self.setGraphicsEffect(shadow)

    def apply_hover_shadow(self):
        """тень для наведения"""
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10.9)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, int(255 * (178 / 255))))
        self.setGraphicsEffect(shadow)

    def enterEvent(self, event):
        if not self.is_selected:
            self.setCursor(Qt.PointingHandCursor)
            self.apply_hover_shadow()

            self.setStyleSheet(f"""
                QLabel {{
                    font-family: 'Unbounded';
                    cursor: pointer;
                    color: {self.font_color_value};
                    font-size: {self.font_size_value}px;
                    
                }}
                
            """)
        super().enterEvent(event)

    def leaveEvent(self, event):

        if not self.is_selected:
            self.unsetCursor()
            self.setCursor(Qt.ArrowCursor)
            self.apply_default_shadow()
            self.apply_styles()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()


        self.is_selected = not self.is_selected if self.is_selected == False else self.is_selected
        self.apply_styles()

        self.deselect_other_labels()
        self.apply_shadow()

        super().mousePressEvent(event)

    def deselect_other_labels(self):
        """Убирает выделение с других меток в контейнере (если они есть)"""
        parent_widget = self.parent()
        if parent_widget:
            for label in parent_widget.findChildren(SelectableLabel):
                if label != self:
                    label.is_selected = False
                    label.apply_styles()
                    label.apply_shadow()

    def set_selected(self, selected: bool):

        self.is_selected = selected
        self.apply_styles()

        self.apply_shadow()

    def apply_shadow(self):
        """Обновление тени в зависимости от состояния кнопки"""
        if self.is_selected:
            self.apply_hover_shadow()
        else:
            self.apply_default_shadow()


class SubscriptionWidget(QWidget):
    confirmed = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Добавление нового посетителя")
        self.setGeometry(300, 300, 426, 426)
        self.confirmedd = False
        self.setWindowFlags(Qt.FramelessWindowHint)  # Remove window controls
        self.setAttribute(Qt.WA_TranslucentBackground)  # Transparent background
        self.setStyleSheet("""
 
            
            QLabel {
                font-family: 'Unbounded';
                font-size: 15px;
                font-weight: 500;
                text-align: center;
                background-color: transparent;
                border: 0px;
            }
            QLabel#titleLabel {
                font-family: 'Unbounded';
                font-size: 25px;
                font-weight: 500;
                text-align: center;
                background-color: transparent;
                border: 0px;
                margin-bottom:15px;
            }
        """)
        self.initUI()
        self.oldPos = self.pos()
        self.radius = 18  # Corner radius
        self.borderWidth = 5  # Border thickness
        self.setWindowModality(Qt.ApplicationModal)

    def initUI(self):
        # Основной макет
        layout = QVBoxLayout(self)

        # Заголовок с кнопкой закрытия
        grid_layout = QGridLayout()

        # Title (centered)
        title_label = QLabel("Добавление абонемента", self)
        title_label.setObjectName("titleLabel")
        grid_layout.addWidget(title_label, 0, 1, alignment=Qt.AlignCenter)  # Center title

        # Close button (top-right)
        close_button = HoverButton("X", 30, 30, 35, '#8F2D31', True, '#8F2D31', 'red', 5, 'red')
        close_button.setObjectName("closeButton")
        close_button.clicked.connect(self.close)
        grid_layout.addWidget(close_button, 0, 2)

        layout.addLayout(grid_layout)

        # Сетка для вариантов подписки
        grid_layout = QGridLayout()

        period = ["Месяц", "Полгода", "Год"]

        classes = ["8", "12", "безлимит"]
        times = ["<16ч", ">16ч", "безлимит"]
        half_year_widget0 = SubscriptionOptionWidget(period[0], classes, times, 1)
        half_year_widget1 = SubscriptionOptionWidget(period[1], [classes[2]], times, 2)
        half_year_widget2 = SubscriptionOptionWidget(period[2], [classes[2]], times, 3)
        grid_layout.addWidget(half_year_widget0, 0, 0)
        grid_layout.addWidget(half_year_widget1, 0, 1)
        grid_layout.addWidget(half_year_widget2, 0, 2)

        layout.addLayout(grid_layout)

        confirm_button = HoverButton("Подтвердить", 220, 60, 18, '#5DEBE6', False, '#5DEBE6', '', 18, '', 10)
        confirm_button.clicked.connect(self.on_confirm_button_click)
        layout.addWidget(confirm_button, alignment=Qt.AlignCenter)

    def on_confirm_button_click(self):
        """Проверка перед подтверждением"""

        global current_active_widget
        # Проверка, что дата начала и дата конца введены и корректны
        start_date = current_active_widget.start_date_input.text()
        end_date = current_active_widget.end_date_input.text()
        if not start_date or not end_date:
            color = '#75A9A7' if current_active_widget.idd == 1 else '#D3D700' if current_active_widget.idd == 2 else '#5DEBE6'
            current_active_widget.setStyleSheet(f"""
                                QLineEdit#from_{current_active_widget.idd}{{
                                            font-family: 'Unbounded';
                                            font-size: 14px;
                                            padding: 10px 20.4px 10px 15px;
                                            border-radius: 18px;
                                            border: solid red;
                                            border-width: 0px 0px 2.7px 2.7px;
                                            background-color: transparent;
                                            color:  black;
                                            margin-top: 10px;
                                            margin-bottom: 10px;
                                          }}
                                        QLineEdit#until_{current_active_widget.idd}{{
                                            font-family: 'Unbounded';
                                            font-size: 14px;
                                            padding: 10px 20.4px 10px 15px;
                                            border-radius: 18px;
                                            border: solid red;
                                            border-width: 0px 0px 2.7px 2.7px;
                                            background-color: transparent;
                                            color:  black;
                                            margin-top: 10px;
                                            margin-bottom: 10px;
                                          }}
                                QFrame#parent_{current_active_widget.idd}{{
                                  border: 2.7px solid {color};
                                  gap: 0px;
                                  border-radius: 18px;
                                  opacity: 1;
                                  font-weight: 500;
                                  font-family: 'Unbounded';
                                  font-size: 15px;
                                  margin:0px;
                                }}
                                QLabel#head{{
                                font-size: 18px;
                                }}""")

        start_date_obj = QDate.fromString(start_date, "dd.MM.yyyy")
        end_date_obj = QDate.fromString(end_date, "dd.MM.yyyy")

        if not start_date_obj.isValid() or not end_date_obj.isValid():
            color = '#75A9A7' if current_active_widget.idd == 1 else '#D3D700' if current_active_widget.idd == 2 else '#5DEBE6'
            current_active_widget.setStyleSheet(f"""
                                            QLineEdit#from_{current_active_widget.idd}{{
                                                        font-family: 'Unbounded';
                                                        font-size: 14px;
                                                        padding: 10px 20.4px 10px 15px;
                                                        border-radius: 18px;
                                                        border: solid red;
                                                        border-width: 0px 0px 2.7px 2.7px;
                                                        background-color: transparent;
                                                        color:  black;
                                                        margin-top: 10px;
                                                        margin-bottom: 10px;
                                                      }}
                                                    QLineEdit#until_{current_active_widget.idd}{{
                                                        font-family: 'Unbounded';
                                                        font-size: 14px;
                                                        padding: 10px 20.4px 10px 15px;
                                                        border-radius: 18px;
                                                        border: solid red;
                                                        border-width: 0px 0px 2.7px 2.7px;
                                                        background-color: transparent;
                                                        color:  black;
                                                        margin-top: 10px;
                                                        margin-bottom: 10px;
                                                      }}
                                            QFrame#parent_{current_active_widget.idd}{{
                                              border: 2.7px solid {color};
                                              gap: 0px;
                                              border-radius: 18px;
                                              opacity: 1;
                                              font-weight: 500;
                                              font-family: 'Unbounded';
                                              font-size: 15px;
                                              margin:0px;
                                            }}
                                            QLabel#head{{
                                            font-size: 18px;
                                            }}""")

        # Проверка, что дата начала не позже даты конца
        if start_date_obj > end_date_obj:
            color = '#75A9A7' if current_active_widget.idd == 1 else '#D3D700' if current_active_widget.idd == 2 else '#5DEBE6'
            current_active_widget.setStyleSheet(f"""
                                            QLineEdit#from_{current_active_widget.idd}{{
                                                        font-family: 'Unbounded';
                                                        font-size: 14px;
                                                        padding: 10px 20.4px 10px 15px;
                                                        border-radius: 18px;
                                                        border: solid red;
                                                        border-width: 0px 0px 2.7px 2.7px;
                                                        background-color: transparent;
                                                        color:  black;
                                                        margin-top: 10px;
                                                        margin-bottom: 10px;
                                                      }}
                                                    QLineEdit#until_{current_active_widget.idd}{{
                                                        font-family: 'Unbounded';
                                                        font-size: 14px;
                                                        padding: 10px 20.4px 10px 15px;
                                                        border-radius: 18px;
                                                        border: solid red;
                                                        border-width: 0px 0px 2.7px 2.7px;
                                                        background-color: transparent;
                                                        color:  black;
                                                        margin-top: 10px;
                                                        margin-bottom: 10px;
                                                      }}
                                            QFrame#parent_{current_active_widget.idd}{{
                                              border: 2.7px solid {color};
                                              gap: 0px;
                                              border-radius: 18px;
                                              opacity: 1;
                                              font-weight: 500;
                                              font-family: 'Unbounded';
                                              font-size: 15px;
                                              margin:0px;
                                            }}
                                            QLabel#head{{
                                            font-size: 18px;
                                            }}""")

        if current_active_widget is None or (
                current_active_widget.selected_class_count == None or current_active_widget.selected_time == None):
            if current_active_widget.selected_time == None:
                current_active_widget.time_widget.setStyleSheet(f"""
                QFrame#bodyy_{current_active_widget.idd}{{
                gap: 0px;
                border-radius: 18px;
                opacity: 0px;
                margin: 0px;
                font-size:15px;
                border: 2px solid red;
                }}
            """)
            if current_active_widget.selected_class_count == None:
                current_active_widget.class_count_widget.setStyleSheet(f"""
                QFrame#bodyy_{current_active_widget.idd}{{
                gap: 0px;
                border-radius: 18px;
                opacity: 0px;
                margin: 0px;
                font-size:15px;
                border: 2px solid red;
                }}
            """)
            else:
                return

        try:
            # Проверка, является ли абонемент действительным
            is_valid = self.check_validity(start_date, end_date)
            subscription_data = {
                "tariff": calculator.generate_k_type(
                    current_active_widget.period,
                    current_active_widget.selected_class_count,
                    current_active_widget.selected_time
                ),
                "start_date": start_date,
                "end_date": end_date,
                "price": current_active_widget.price_label.text(),
                "visit_ids": [],
                "is_valid": is_valid
            }

            self.confirmed.emit(subscription_data)
            self.confirmedd = True
            self.close()

        except ValueError as e:
            QMessageBox.critical(self, "Ошибка", str(e))

        print("Все проверки пройдены, можно подтверждать.")

    def check_validity(self, start_date, end_date):
        """Проверяет, действителен ли абонемент."""
        today = QDate.currentDate()
        start_date_obj = QDate.fromString(start_date, "dd.MM.yyyy")
        end_date_obj = QDate.fromString(end_date, "dd.MM.yyyy")

        if not (start_date_obj.isValid() and end_date_obj.isValid()):
            raise ValueError("Некорректный формат дат.")

        return start_date_obj <= today <= end_date_obj

    def create_subscription_option(self, title: str, classes: list, times: list):
        widget = QWidget()
        vbox = QVBoxLayout(widget)

        label_title = QLabel(title)

        for cls in classes:
            label_class = QLabel(cls)
            vbox.addWidget(label_class)

        for time in times:
            label_time = QLabel(time)
            vbox.addWidget(label_time)

        return widget

    def paintEvent(self, event):
        # Custom paint event for rounded corners and border
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Define the rectangle for the window
        rect = QRectF(0, 0, self.width(), self.height())

        # Set border color and width
        borderPen = QPen(QColor(117, 169, 167))  # Border color
        borderPen.setWidth(self.borderWidth)  # Border thickness
        painter.setPen(borderPen)

        # Set background color
        backgroundBrush = QColor(255, 255, 255)  # White background
        painter.setBrush(backgroundBrush)

        # Draw rounded rectangle if radius > 0
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
        global qwidget_clicked
        if qwidget_clicked:
            pass
        else:

            delta = QPoint(event.globalPos() - self.oldPos)
            self.move(self.pos() + delta)
            self.oldPos = event.globalPos()

    def closeEvent(self, event):
        """Обработчик закрытия окна."""
        global current_active_widget


        if not self.confirmedd:
            self.confirmed.emit(None)
        current_active_widget = None
        super().closeEvent(event)
