import sys
from PyQt5.QtWidgets import QApplication, QDialog
from login import LoginWidget
from main_window import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)

    login_widget = LoginWidget()

    # if login_widget.exec_() == QDialog.Accepted:
    #     window = MainWindow()
    #     window.show()
    # elif login_widget.exec_() == QDialog.Rejected:
    #     sys.exit(0)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
