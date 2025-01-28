from datetime import datetime, timedelta

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt5.QtCore import Qt
from database import execute_query

class RevokeSubscriptionWindow(QDialog):
    def __init__(self, client_id, parent_window, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self.parent_window = parent_window

        self.setWindowTitle("Лишение абонемента")
        self.setWindowModality(Qt.ApplicationModal)
        self.setFixedSize(400, 200)

        # Создаём интерфейс
        layout = QVBoxLayout(self)

        # Заголовок
        title_label = QLabel("Лишение абонемента")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)

        self.reason_input = QLineEdit()
        self.reason_input.setPlaceholderText("Введите причину лишения абонемента")
        self.reason_input.setMaxLength(255)  # Ограничение длины
        layout.addWidget(self.reason_input)

        # Кнопка подтверждения
        confirm_button = QPushButton("Подтвердить")
        confirm_button.clicked.connect(self.revoke_subscription)
        layout.addWidget(confirm_button)

        # Кнопка отмены
        cancel_button = QPushButton("Отмена")
        cancel_button.clicked.connect(self.close)
        layout.addWidget(cancel_button)

    def revoke_subscription(self):
        """
        Обрабатывает лишение абонемента: обновляет БД и интерфейс.
        """
        reason = self.reason_input.text().strip()
        if not reason:
            QMessageBox.warning(self, "Ошибка", "Причина лишения абонемента не может быть пустой.")
            return

        try:

            query_check_subscription = """
                SELECT subscription FROM client WHERE client_id = %s
            """
            subscription_result = execute_query(query_check_subscription, (self.client_id,), fetch=True)
            if not subscription_result or not subscription_result[0][0]:
                QMessageBox.warning(self, "Ошибка", "У клиента нет активного абонемента.")
                return


            query_update_subscription = """
                UPDATE subscription
                SET revoke_reason = %s, is_valid = FALSE
                WHERE subscription_id = (
                    SELECT subscription FROM client WHERE client_id = %s
                )
            """
            query_update_client = """
                UPDATE client
                SET subscription = NULL
                WHERE client_id = %s
            """
            execute_query(query_update_subscription, (reason, self.client_id))
            execute_query(query_update_client, (self.client_id,))


            query_log_action = """
                INSERT INTO logs (action, details, client_id, timestamp)
                VALUES (%s, %s, %s, NOW())
            """
            log_details = f"Клиенту {self.client_id} был лишён абонемент. Причина: {reason}"
            execute_query(query_log_action, ("Лишение абонемента", log_details, self.client_id))

            self.parent_window.update_client_in_list(self.client_id, None)
            QMessageBox.information(self, "Успех", "Абонемент успешно лишён!")
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось лишить абонемент: {e}")


class FreezeSubscriptionWindow(QDialog):
    def __init__(self, client_id, parent_window, parent=None):
        super().__init__(parent)
        self.client_id = client_id
        self.parent_window = parent_window

        self.setWindowTitle("Заморозка абонемента")
        self.setWindowModality(Qt.ApplicationModal)
        self.setFixedSize(400, 250)

        layout = QVBoxLayout(self)

        # Заголовок
        title_label = QLabel("Заморозка абонемента")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)

        # Поле для ввода даты начала заморозки
        self.start_date_input = QLineEdit()
        self.start_date_input.setPlaceholderText("Введите дату начала (дд.мм.гггг)")
        layout.addWidget(self.start_date_input)

        # Поле для ввода даты окончания заморозки
        self.end_date_input = QLineEdit()
        self.end_date_input.setPlaceholderText("Введите дату окончания (дд.мм.гггг)")
        layout.addWidget(self.end_date_input)

        # Кнопка подтверждения
        confirm_button = QPushButton("Подтвердить")
        confirm_button.clicked.connect(self.freeze_subscription)
        layout.addWidget(confirm_button)

    def freeze_subscription(self):
        """
        Обрабатывает заморозку абонемента: обновляет БД и интерфейс.
        """
        start_date_str = self.start_date_input.text().strip()
        end_date_str = self.end_date_input.text().strip()

        # формат даты
        try:
            start_date = datetime.strptime(start_date_str, "%d.%m.%Y").date()
            end_date = datetime.strptime(end_date_str, "%d.%m.%Y").date()
        except ValueError:
            QMessageBox.warning(self, "Ошибка", "Некорректный формат даты. Используйте ДД.ММ.ГГГГ")
            return

        # дата окончания была позже даты начала
        if start_date >= end_date:
            QMessageBox.warning(self, "Ошибка", "Дата окончания должна быть позже даты начала.")
            return

        # начала и окончания действия абонемента
        query_subscription_dates = """
            SELECT valid_since, valid_until FROM subscription WHERE subscription_id = (
                SELECT subscription FROM client WHERE client_id = %s
            )
        """
        result = execute_query(query_subscription_dates, (self.client_id,), fetch=True)
        if not result:
            QMessageBox.critical(self, "Ошибка", "Не удалось получить данные абонемента.")
            return

        valid_since, valid_until = result[0]

        # **Дата начала не может быть раньше начала действия абонемента**
        if start_date < valid_since:
            QMessageBox.warning(self, "Ошибка", "Дата начала заморозки не может быть раньше начала действия абонемента.")
            return

        # **Дата окончания не может быть позже окончания абонемента**
        if end_date > valid_until:
            QMessageBox.warning(self, "Ошибка", "Дата окончания выходит за границы действия абонемента.")
            return

        freeze_period = (end_date - start_date).days
        new_valid_until = valid_until + timedelta(days=freeze_period)


        query_update_subscription = """
            UPDATE subscription
            SET frozen_from = %s, frozen_until = %s, valid_until = %s
            WHERE subscription_id = (
                SELECT subscription FROM client WHERE client_id = %s
            )
            RETURNING tariff, TO_CHAR(valid_since, 'DD.MM.YY'), TO_CHAR(valid_until, 'DD.MM.YY'), is_valid, price;
        """
        updated_data = execute_query(query_update_subscription, (start_date, end_date, new_valid_until, self.client_id), fetch=True)

        if not updated_data:
            QMessageBox.critical(self, "Ошибка", "Не удалось обновить абонемент.")
            return


        subscription_data = {
            "tariff": updated_data[0][0],
            "start_date": updated_data[0][1],
            "end_date": updated_data[0][2],
            "is_valid": updated_data[0][3],
            "price": updated_data[0][4],
        }


        self.parent_window.update_client_in_list(self.client_id, subscription_data)

        QMessageBox.information(self, "Успех", "Абонемент успешно заморожен!")
        self.close()