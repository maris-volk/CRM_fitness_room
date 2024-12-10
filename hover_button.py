from PyQt5.QtWidgets import QPushButton, QGraphicsDropShadowEffect
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt


class HoverButton(QPushButton):
    def __init__(self, text='', width: float = 347, height: float = 72, font_size: float = 22,
                 font_color: str = 'black', non_padding: bool = False, default_border: str = '',
                 hover_border: str = '', border_radius: float = 18, hover_text_color: str = '',margin: float = 0):
        super().__init__(text)
        self.setMouseTracking(True)  # Включаем отслеживание мыши
        self.width_value = width  # Сохраняем переданные значения ширины и высоты
        self.height_value = height
        self.margin_value = margin
        self.font_size_value = font_size
        self.font_color_value = font_color
        self.border_radius_value = border_radius
        self.font_padding_value = '-2px 15px 0px 15px'
        if non_padding:
            self.font_padding_value = '-11px 0px 0px 0px'
        if default_border == '':
            self.default_border_value = '#75A9A7'
        else:
            self.default_border_value = default_border
        if hover_border == '':
            self.hover_border_value = '#5DEBE6'
        else:
            self.hover_border_value = hover_border
        self.hover_text_color_value = font_color if hover_text_color == '' else hover_text_color

        self.initUI()

    def initUI(self):
        self.apply_styles()

        self.setFixedWidth(int(self.width_value))
        self.setFixedHeight(int(self.height_value))
        self.apply_default_shadow()

    def apply_styles(self):
        # Применяем стили с переданными значениями ширины и высоты
        self.setStyleSheet(f"""
        QPushButton {{
            color: {self.font_color_value};
            background-color: #ffffff;
            border: 2.7px solid {self.default_border_value};
            width: {self.width_value}px;
            height: {self.height_value}px;
            gap: 0px;
            border-radius: {self.border_radius_value}px;
            opacity: 1;
            padding: {self.font_padding_value};
            font-weight: 500;
            font-family: 'Unbounded';
            font-size: {self.font_size_value}px;
            margin: {self.margin_value}px;
        }}
        """)

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
        self.setStyleSheet(f"""
               QPushButton {{
                   color: {self.hover_text_color_value};
                   background-color: #ffffff;
                   border: 2.7px solid {self.hover_border_value};
                   width: {self.width_value}px;
                   height: {self.height_value}px;
                   padding: {self.font_padding_value};
                   gap: 0px;
                   border-radius: {self.border_radius_value}px;
                   opacity: 0.9;
                   font-weight: 500;
                   font-family: 'Unbounded';
                   font-size: {self.font_size_value}px;
                   margin: {self.margin_value}px;
               }}
           """)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.apply_styles()
        self.apply_default_shadow()
        super().leaveEvent(event)

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
