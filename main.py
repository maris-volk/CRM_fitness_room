# main.py

import sys
import locale
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox

from database import close_pool
from login import LoginWidget
from main_window import MainWindow

import logging

logging.basicConfig(
    level=logging.INFO,  # Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    # Установка локали с обработкой исключений
    try:
        locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
    except locale.Error:
        logger.warning("Локаль 'ru_RU.UTF-8' не доступна. Используется стандартная локаль.")
        locale.setlocale(locale.LC_TIME, '')

    app = QApplication(sys.argv)

    login_widget = LoginWidget()
    result = login_widget.exec_()

    if result == QDialog.Accepted:
        current_user_id = login_widget.current_user_id
        if current_user_id is not None:
            window = MainWindow(current_user_id)
            window.show()
            logger.info(f"Пользователь с ID {current_user_id} вошёл в систему.")
        else:
            QMessageBox.critical(None, "Ошибка", "Не удалось получить идентификатор пользователя.")
            sys.exit(1)
    else:
        sys.exit(0)

    # Подключение сигнала для закрытия пула при выходе из приложения
    app.aboutToQuit.connect(close_pool)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
