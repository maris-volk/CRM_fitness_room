import logging
import os
import sys

from PyQt5.QtCore import QLocale, QTranslator, QLibraryInfo
from PyQt5.QtGui import QFontDatabase, QFont
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox

from database import close_pool
from login import LoginWidget
from main_window import MainWindow
from utils import resources_path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)





def load_fonts():
    """Загружает все .ttf шрифты из папки 'fonts'."""
    font_dir = resources_path("fonts")
    if not os.path.exists(font_dir):
        logger.warning("Папка fonts не найдена!")
        return QFont("Arial", 12)

    font_files = [f for f in os.listdir(font_dir) if f.endswith(".ttf")]

    if not font_files:
        logger.warning("Нет файлов шрифтов в папке fonts!")
        return QFont("Arial", 12)

    loaded_fonts = []

    for font_file in font_files:
        font_path = os.path.join(font_dir, font_file)
        font_id = QFontDatabase.addApplicationFont(font_path)

        if font_id == -1:
            logger.error(f"Ошибка загрузки шрифта: {font_file}")
        else:
            families = QFontDatabase.applicationFontFamilies(font_id)
            loaded_fonts.extend(families)
            logger.info(f"Загружен шрифт: {font_file} | Доступные начертания: {families}")

    # Проверяем, загружен ли `Unbounded`
    available_fonts = QFontDatabase().families()

    if "Unbounded" in available_fonts:
        font = QFont("Unbounded", 8)
    else:
        font = QFont("Arial", 12)

    return font


def set_locale():
    """Устанавливает локаль для корректного отображения русского и английского."""
    import locale

    try:
        locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
    except locale.Error:
        print("Локаль 'ru_RU.UTF-8' не доступна, используем альтернативу.")
        try:
            locale.setlocale(locale.LC_TIME, 'Russian_Russia.1251')  # Для Windows
        except locale.Error:
            print("Не удалось установить русскую локаль.")

    system_locale = QLocale.system().name()

    if system_locale.startswith("ru"):
        locale = QLocale(QLocale.Russian, QLocale.Russia)
    else:
        locale = QLocale(QLocale.English, QLocale.UnitedStates)

    QLocale.setDefault(locale)
    logger.info(f"Установлена локаль: {locale.name()}")

    # Загружаем переводы Qt
    translator = QTranslator()
    if translator.load(locale, "qt", "_", QLibraryInfo.location(QLibraryInfo.TranslationsPath)):
        app.installTranslator(translator)
        logger.info("Загружены системные переводы Qt")

def main():
    global app  # Нужно для установки трансляторов
    app = QApplication(sys.argv)

    # **Загружаем локаль и шрифты**
    set_locale()
    font = load_fonts()
    app.setFont(font)

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
