import sys
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QHBoxLayout, QPushButton, QDialog, QDesktopWidget, \
    QCheckBox
from PyQt5.QtCore import Qt, QRectF, QPoint, pyqtSignal, QSettings, QTimer
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush
from database import authenticate_user
from hover_button import HoverButton
from utils import WorkerThread

class LoginWidget(QDialog):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Авторизация")
        self.setGeometry(300, 300, 400, 300)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setObjectName("myParentWidget")
        self.login_button = None
        self.setStyleSheet("""
            QWidget#myParentWidget {
                background-color: transparent;
            }

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
                border-radius: 0px;
                background-color: transparent;
                border: 0px;
                font-family: 'Unbounded';
                font-size: 22.5px;
                font-weight: 500;
                text-align: center;
            }

            QLabel {
                font-family: 'Unbounded';
                font-size: 20px;
                font-weight: 500;
                text-align: center;
                margin-bottom: 5px;
            }
        """)

        self.initUI()

        self.oldPos = self.pos()
        self.radius = 18
        self.borderWidth = 5

        self.center_window()

    def center_window(self):
        screen = QDesktopWidget().screenGeometry()
        window = self.geometry()
        x = (screen.width() - window.width()) // 2
        y = (screen.height() - window.height()) // 2
        self.move(x, y)

    def initUI(self):
        layout = QVBoxLayout(self)

        # Title label
        title_label = QLabel("Авторизация", self)
        title_label.setObjectName("titleLabel")
        layout.addWidget(title_label, alignment=Qt.AlignCenter)

        # Username input field
        self.username_input = QLineEdit(self)
        self.username_input.setPlaceholderText("Логин")
        layout.addWidget(self.username_input)

        # Password input field
        self.password_input = QLineEdit(self)
        self.password_input.setPlaceholderText("Пароль")
        self.password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.password_input)

        # "Remember Me" checkbox
        # self.remember_me_checkbox = QCheckBox("Запомнить меня", self)
        # layout.addWidget(self.remember_me_checkbox)

        # Login button
        self.login_button = HoverButton("Войти", 190, 35, 15, '#5DEBE6', False, '#5DEBE6', '', 8)
        self.login_button.setFixedSize(180, 35)
        self.login_button.clicked.connect(self.authenticate_and_login)
        layout.addWidget(self.login_button, alignment=Qt.AlignCenter)

        self.setLayout(layout)
        # Load saved data
        # self.load_saved_data()

    def authenticate_and_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        if not username or not password:
            if not username:
                self.username_input.setStyleSheet("border-color:red;")
            if not password:
                self.password_input.setStyleSheet("border-color:red;")
            return

        # Create and start authentication thread
        self.username_input.setStyleSheet("border-color:#75A9A7;")
        self.password_input.setStyleSheet("border-color:#75A9A7;")
        self.login_button.set_border_color("Gold")
        self.login_button.set_hover_border_color("Yellow")
        self.login_button.set_font_color("Gold")

        self.auth_thread = WorkerThread(authenticate_user, username, password)

        self.auth_thread.result_signal.connect(self.handle_authentication_result)
        self.auth_thread.start()

    def handle_authentication_result(self, result):
        if result:
            # if self.remember_me_checkbox.isChecked():
            #     self.save_login_data()
            self.login_button.set_border_color("#00FF00")
            self.login_button.set_hover_border_color("#00FF00")
            self.login_button.set_font_color("#14B814")
            QTimer.singleShot(400, self.accept)
             # Close window on successful login
        else:
            self.username_input.setStyleSheet("border-color:red;")
            self.password_input.setStyleSheet("border-color:red;")
            self.login_button.set_border_color('#5DEBE6')
            self.login_button.set_hover_border_color('#5DEBE6')
            self.login_button.set_font_color('#5DEBE6')

    # def save_login_data(self):
    #     # Store the username and remember me status using QSettings
    #     settings = QSettings("MyOrganization", "MyApp")
    #     settings.setValue("username", self.username_input.text())
    #     settings.setValue("password", self.password_input.text())
    #     settings.setValue("remember_me", self.remember_me_checkbox.isChecked())

    # def load_saved_data(self):
    #     # Check if "Remember me" is enabled and load saved data
    #     settings = QSettings("MyOrganization", "MyApp")
    #     remember_me = settings.value("remember_me", False, type=bool)
    #
    #     if remember_me:
    #         # Pre-fill the username field
    #         self.username_input.setText(settings.value("username", ""))
    #         self.password_input.setText(settings.value("password", ""))
    #         self.remember_me_checkbox.setChecked(True)

    def paintEvent(self, event):
        # Custom paint event for rounded corners and border
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
        # Store initial position for dragging window
        self.oldPos = event.globalPos()

    def mouseMoveEvent(self, event):
        # Move window based on mouse drag
        delta = event.globalPos() - self.oldPos
        self.move(self.pos() + delta)
        self.oldPos = event.globalPos()

    def closeEvent(self, event):
        # Close event handling
        event.accept()
