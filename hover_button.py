from PyQt5.QtWidgets import QPushButton, QGraphicsDropShadowEffect, QLabel, QVBoxLayout, QWidget, QGridLayout
from PyQt5.QtGui import QColor, QPixmap
from PyQt5.QtCore import Qt, pyqtSignal


class HoverButton(QPushButton):
    def __init__(self, text='', width: float = 347, height: float = 72, font_size: float = 22,
                 font_color: str = 'black', non_padding: bool = False, default_border: str = '',
                 hover_border: str = '', border_radius: float = 18, hover_text_color: str = '',
                 margin: float = 0, parent=None):
        super().__init__(text, parent)
        self.setMouseTracking(True)  # Включаем отслеживание мыши
        self.width_value = width
        self.height_value = height
        self.margin_value = margin
        self.font_size_value = font_size
        self.font_color_value = font_color
        self.border_radius_value = border_radius
        self.font_padding_value = '-2px 15px 0px 15px'
        if non_padding:
            self.font_padding_value = '-11px 0px 0px 0px'
        self.default_border_value = default_border if default_border else '#75A9A7'
        self.hover_border_value = hover_border if hover_border else '#5DEBE6'
        self.hover_text_color_value = font_color if hover_text_color == '' else hover_text_color
        self.is_disabled = False  # Флаг отключённой кнопки

        self.initUI()

    def initUI(self):
        self.apply_styles()
        self.setFixedWidth(int(self.width_value))
        self.setFixedHeight(int(self.height_value))
        self.apply_default_shadow()

    def apply_styles(self):
        if self.is_disabled:
            # Стиль для отключённой кнопки
            self.setStyleSheet(f"""
            QPushButton {{
                color: #a0a0a0;
                background-color: #f0f0f0;
                border: 2.7px solid #d3d3d3;
                width: {self.width_value}px;
                height: {self.height_value}px;
                border-radius: {self.border_radius_value}px;
                padding: {self.font_padding_value};
                font-family: 'Unbounded';
                font-size: {self.font_size_value}px;
            }}
            """)
        else:
            # Стиль для активной кнопки
            self.setStyleSheet(f"""
            QPushButton {{
                color: {self.font_color_value};
                background-color: #ffffff;
                border: 2.7px solid {self.default_border_value};
                width: {self.width_value}px;
                height: {self.height_value}px;
                border-radius: {self.border_radius_value}px;
                padding: {self.font_padding_value};
                font-family: 'Unbounded';
                font-size: {self.font_size_value}px;
            }}
            """)

    def apply_default_shadow(self):
        if not self.is_disabled:
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(0)
            shadow.setXOffset(0)
            shadow.setYOffset(0)
            shadow.setColor(QColor(184, 182, 215, 178))
            self.setGraphicsEffect(shadow)

    def apply_hover_shadow(self):
        if not self.is_disabled:
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(10.9)
            shadow.setXOffset(0)
            shadow.setYOffset(0)
            shadow.setColor(QColor(0, 0, 0, int(255 * (178 / 255))))
            self.setGraphicsEffect(shadow)

    def enterEvent(self, event):
        if not self.is_disabled:  # Убираем эффект наведения, если кнопка отключена
            self.apply_hover_shadow()
            self.setStyleSheet(f"""
            QPushButton {{
                color: {self.hover_text_color_value};
                background-color: #ffffff;
                border: 2.7px solid {self.hover_border_value};
                width: {self.width_value}px;
                height: {self.height_value}px;
                border-radius: {self.border_radius_value}px;
                padding: {self.font_padding_value};
                font-family: 'Unbounded';
                font-size: {self.font_size_value}px;
            }}
            """)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.apply_styles()
        self.apply_default_shadow()
        super().leaveEvent(event)

    def disable_button(self):
        """Отключает кнопку, делает её серой и убирает интерактивность."""
        self.is_disabled = True
        self.setEnabled(False)
        self.apply_styles()

    def enable_button(self):
        """Включает кнопку, возвращает интерактивность."""
        self.is_disabled = False
        self.setEnabled(True)
        self.apply_styles()

    # Методы для изменения параметров
    def set_font_color(self, color: str):
        self.font_color_value = color
        self.apply_styles()

    def set_hover_text_color(self, color: str):
        self.hover_text_color_value = color

    def set_border_color(self, color: str):
        self.default_border_value = color
        self.apply_styles()

    def set_hover_border_color(self, color: str):
        self.hover_border_value = color

    def set_button_size(self, width: float, height: float):
        self.width_value = width
        self.height_value = height
        self.apply_styles()
        self.setFixedWidth(int(self.width_value))
        self.setFixedHeight(int(self.height_value))

    def set_font_size(self, size: float):
        self.font_size_value = size
        self.apply_styles()

    def set_border_radius(self, radius: float):
        self.border_radius_value = radius
        self.apply_styles()

    def set_padding(self, padding: str):
        self.font_padding_value = padding
        self.apply_styles()

    def set_shadow_blur_radius(self, blur_radius: float):
        shadow = self.graphicsEffect()
        if isinstance(shadow, QGraphicsDropShadowEffect):
            shadow.setBlurRadius(blur_radius)
class TrainerButton(QWidget):
    clicked = pyqtSignal()  # Пользовательский сигнал для клика

    def __init__(self, name, image_path, avatar_width=100, avatar_height=100, font_size=14,
                 border_width_normal=2, border_color_normal="#75A9A7",
                 border_width_hover=3, border_color_hover="#5DEBE6",
                 border_width_selected=4, border_color_selected="#5DEBE6", parent=None):
        super().__init__(parent)
        self.name = name
        self.image_path = image_path
        self.avatar_width = avatar_width
        self.avatar_height = avatar_height
        self.font_size_value = font_size
        self.is_selected = False

        # Параметры рамки
        self.border_width_normal = border_width_normal
        self.border_color_normal = border_color_normal
        self.border_width_hover = border_width_hover
        self.border_color_hover = border_color_hover
        self.border_width_selected = border_width_selected
        self.border_color_selected = border_color_selected

        self.initUI()

    def initUI(self):
        # Создаем сеточный макет
        layout = QGridLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        # Аватарка
        self.avatar_label = QLabel(self)
        self.avatar_label.setPixmap(
            QPixmap(self.image_path).scaled(self.avatar_width, self.avatar_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )
        self.avatar_label.setAlignment(Qt.AlignCenter)
        self.avatar_label.setStyleSheet(f"""
            QLabel {{
                border: {self.border_width_normal}px solid {self.border_color_normal};
                border-radius: 10px;
                background-color: gray;
            }}
        """)
        self.apply_default_shadow(self.avatar_label)

        # Имя тренера
        self.name_label = QLabel(self.name, self)  # Создаем перед вызовом apply_styles
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setWordWrap(True)  # Включаем перенос текста
        self.name_label.setStyleSheet(f"""
            QLabel {{
                font-family: 'Unbounded';
                font-size: {self.font_size_value}px;
                font-weight: bold;
                color: black;
            }}
        """)

        # Добавляем виджеты в макет
        layout.addWidget(self.avatar_label, 0, 0, alignment=Qt.AlignCenter)  # Аватарка
        layout.addWidget(self.name_label, 1, 0, alignment=Qt.AlignCenter)    # Имя

        self.setLayout(layout)

        # Подключение событий
        self.avatar_label.installEventFilter(self)
        self.name_label.installEventFilter(self)

    def apply_styles(self, hovered=False):
        """Обновляет стили в зависимости от состояния выбора или наведения."""
        if hasattr(self, 'name_label') and self.name_label:  # Проверяем наличие name_label
            if self.is_selected:
                self.avatar_label.setStyleSheet(f"""
                    QLabel {{
                        border: {self.border_width_selected}px solid {self.border_color_selected};
                        border-radius: 10px;
                        background-color: gray;
                    }}
                """)
                self.name_label.setStyleSheet(f"""
                    QLabel {{
                        font-family: 'Unbounded';
                        font-size: {self.font_size_value}px;
                        font-weight: bold;
                        color: {self.border_color_selected};
                    }}
                """)
                self.apply_selected_shadow(self.avatar_label)
            elif hovered:
                self.avatar_label.setStyleSheet(f"""
                    QLabel {{
                        border: {self.border_width_hover}px solid {self.border_color_hover};
                        border-radius: 10px;
                        background-color: gray;
                    }}
                """)
                self.apply_hover_shadow(self.avatar_label)
            else:
                self.avatar_label.setStyleSheet(f"""
                    QLabel {{
                        border: {self.border_width_normal}px solid {self.border_color_normal};
                        border-radius: 10px;
                        background-color: gray;
                    }}
                """)
                self.name_label.setStyleSheet(f"""
                    QLabel {{
                        font-family: 'Unbounded';
                        font-size: {self.font_size_value}px;
                        font-weight: bold;
                        color: black;
                    }}
                """)
                self.apply_default_shadow(self.avatar_label)
    def update_styles(self, hovered=False):
        """Обновляет стили в зависимости от состояния выбора или наведения."""
        if self.is_selected:
            self.avatar_label.setStyleSheet(f"""
                QLabel {{
                    border: {self.border_width_selected}px solid {self.border_color_selected};
                    border-radius: 10px;
                    background-color: gray;
                }}
            """)
            self.name_label.setStyleSheet(f"""
                QLabel {{
                    font-family: 'Unbounded';
                    font-size: {self.font_size_value}px;
                    font-weight: bold;
                    color: {self.border_color_selected};
                }}
            """)
            self.apply_selected_shadow(self.avatar_label)
        elif hovered:
            self.avatar_label.setStyleSheet(f"""
                QLabel {{
                    border: {self.border_width_hover}px solid {self.border_color_hover};
                    border-radius: 10px;
                    background-color: gray;
                }}
            """)
            self.apply_hover_shadow(self.avatar_label)
        else:
            self.apply_styles()
            self.apply_default_shadow(self.avatar_label)

    def apply_default_shadow(self, widget):
        """Добавляет стандартную тень."""
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(0)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QColor(184, 182, 215, 178))
        widget.setGraphicsEffect(shadow)

    def apply_hover_shadow(self, widget):
        """Добавляет тень при наведении."""
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 50))
        widget.setGraphicsEffect(shadow)

    def apply_selected_shadow(self, widget):
        """Добавляет усиленную тень для выбранного тренера."""
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 100))
        widget.setGraphicsEffect(shadow)

    def eventFilter(self, source, event):
        """Фильтруем события для аватарки и имени."""
        if source == self.avatar_label or source == self.name_label:
            if event.type() == event.Enter:
                self.update_styles(hovered=True)
                return True
            elif event.type() == event.Leave:
                self.update_styles()
                return True
            elif event.type() == event.MouseButtonPress and event.button() == Qt.LeftButton:
                self.is_selected = not self.is_selected
                self.update_styles()
                self.clicked.emit()  # Испускаем сигнал при клике
                return True
        return super().eventFilter(source, event)