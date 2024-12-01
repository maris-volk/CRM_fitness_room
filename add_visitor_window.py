import re
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QLineEdit, QGridLayout, QDialog
from PyQt5.QtCore import Qt, QRectF, QPoint
from PyQt5.QtGui import QPainter, QColor, QPen
from hover_button import HoverButton

class AddVisitorWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Добавление нового посетителя")
        self.setGeometry(300, 300, 426, 426)
        self.setWindowFlags(Qt.FramelessWindowHint)  # Remove window controls
        self.setAttribute(Qt.WA_TranslucentBackground)  # Transparent background
        self.setStyleSheet("""
            QDialog {}
            QLineEdit {
                font-family: 'Unbounded';
                font-size: 22.5px;
                padding: 15px 20.4px 15px 15px;
                border-radius: 18px;
                border: solid #75A9A7;
                border-width: 0px 0px 2.7px 2.7px;
                background-color: transparent;
                margin-left: 65px;
                margin-right: 65px;
                margin-top: 10px;
                margin-bottom: 10px;
            }
            QLabel {
                font-family: 'Unbounded';
                font-size: 22.5px;
                font-weight: 500;
                text-align: center;
                background-color: transparent;
                border: 0px;
            }
        """)
        self.initUI()
        self.oldPos = self.pos()
        self.radius = 18  # Corner radius
        self.borderWidth = 5  # Border thickness
        self.setWindowModality(Qt.ApplicationModal)  # Modal window blocking other windows

    def initUI(self):
        layout = QVBoxLayout(self)
        grid_layout = QGridLayout()

        # Title (centered)
        title_label = QLabel("Новый посетитель", self)
        title_label.setObjectName("titleLabel")
        grid_layout.addWidget(title_label, 0, 1)  # Center title

        # Close button (top-right)
        close_button = HoverButton("X", 30, 30, 35, '#8F2D31', True, '#8F2D31', 'red', 5, 'red')
        close_button.setObjectName("closeButton")
        close_button.clicked.connect(self.close)
        grid_layout.addWidget(close_button, 0, 2)  # Right-aligned close button

        # Set column stretch
        grid_layout.setColumnStretch(0, 1)  # Empty left column
        grid_layout.setColumnStretch(1, 3)  # Center column with title
        grid_layout.setColumnStretch(2, 1)  # Empty right column
        layout.addLayout(grid_layout)

        # Input fields
        phone_input = QLineEdit(self)
        phone_input.setPlaceholderText("Номер телефона")
        layout.addWidget(phone_input)

        last_name_input = QLineEdit(self)
        last_name_input.setPlaceholderText("Фамилия")
        layout.addWidget(last_name_input)

        first_name_input = QLineEdit(self)
        first_name_input.setPlaceholderText("Имя")
        layout.addWidget(first_name_input)

        patronymic_input = QLineEdit(self)
        patronymic_input.setPlaceholderText("Отчество")
        layout.addWidget(patronymic_input)

        # Button grid for trainer and subscription
        button_grid_layout = QGridLayout()

        # Labels
        trainer_label = QLabel("Тренер", self)
        trainer_label.setAlignment(Qt.AlignCenter)
        button_grid_layout.addWidget(trainer_label, 0, 0, alignment=Qt.AlignCenter)

        subscription_label = QLabel("Абонемент", self)
        subscription_label.setAlignment(Qt.AlignCenter)
        button_grid_layout.addWidget(subscription_label, 0, 1, alignment=Qt.AlignCenter)

        # Buttons
        trainer_button = HoverButton("+", 30, 30, 40, '#75A9A7', True, '', '', 5, '#5DEBE6')
        button_grid_layout.addWidget(trainer_button, 1, 0, alignment=Qt.AlignCenter)

        subscription_button = HoverButton("+", 30, 30, 40, '#75A9A7', True, '', '', 5, '#5DEBE6')
        button_grid_layout.addWidget(subscription_button, 1, 1, alignment=Qt.AlignCenter)

        layout.addLayout(button_grid_layout)

        # Add space before confirm button
        layout.addStretch(1)

        # Confirm button (centered)
        confirm_button = HoverButton("Подтвердить", 190, 35, 15, '#5DEBE6', False, '#5DEBE6', '', 8)
        confirm_button.setContentsMargins(10, 30, 10, 30)
        confirm_button.setFixedSize(180, 35)  # Fixed size for alignment
        confirm_button.clicked.connect(lambda: self.validate_and_add_user(
            first_name_input, last_name_input, patronymic_input, phone_input))
        layout.addWidget(confirm_button, alignment=Qt.AlignCenter)

        # Add space after confirm button
        layout.addStretch(1)

        self.setLayout(layout)

    def showEvent(self, event):
        super().showEvent(event)

        # Position the close button
        title_label = self.findChild(QLabel)  # Find title label
        title_width = title_label.width()  # Get title width
        title_pos = title_label.pos()  # Get title position

        # Position the close button (custom placement)

    def validate_and_add_user(self, first_name_input, last_name_input, patronymic_input, phone_input):
        first_name = first_name_input.text().strip()
        last_name = last_name_input.text().strip()
        patronymic = patronymic_input.text().strip()
        phone_number = phone_input.text().strip()

        valid = True

        if not first_name:
            first_name_input.setStyleSheet("border-color:red;")
            valid = False
        else:
            first_name_input.setStyleSheet("border-color:#75A9A7;")

        if not last_name:
            last_name_input.setStyleSheet("border-color:red;")
            valid = False
        else:
            last_name_input.setStyleSheet("border-color:#75A9A7;")

        # Check phone number format (e.g., +1234567890)
        if not re.match(r"^\+\d{10,15}$", phone_number):
            phone_input.setStyleSheet("border-color:red;")
            valid = False
        else:
            phone_input.setStyleSheet("border-color:#75A9A7;")

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
        delta = QPoint(event.globalPos() - self.oldPos)
        self.move(self.pos() + delta)
        self.oldPos = event.globalPos()
