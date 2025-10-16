"""
Модуль диалога для расширенной работы с таблицами БД.
Содержит класс TaskDialog с возможностями управления данными и структурой таблиц.
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                              QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
                              QComboBox, QLineEdit, QMenu, QInputDialog, QCheckBox,
                              QSpinBox, QFormLayout, QTextEdit, QDialogButtonBox, QWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from controller import NumericTableItem
from logger import Logger


class TaskDialog(QDialog):
    """
    Диалог для расширенной работы с таблицами БД.
    Предоставляет возможности ALTER TABLE, расширенные SELECT, поиск, JOIN и строковые функции.
    """
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.logger = Logger()

        self.current_table = None
        self.current_columns = []
        self.all_columns_info = []

        self.setWindowTitle("Техническое задание - Управление БД")
        self.setMinimumSize(1200, 700)

        self.setup_ui()
        self.load_tables()

    def setup_ui(self):
        """Настройка пользовательского интерфейса."""
        layout = QVBoxLayout(self)

        # Заголовок
        title_layout = QHBoxLayout()
        title_label = QLabel("<h2>Управление структурой и данными БД</h2>")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # Панель выбора таблицы
        table_selection_layout = QHBoxLayout()

        table_selection_layout.addWidget(QLabel("Выбор таблицы:"))

        self.table_combo = QComboBox()
        self.table_combo.setMinimumWidth(200)
        self.table_combo.currentTextChanged.connect(self.on_table_changed)
        table_selection_layout.addWidget(self.table_combo)

        # Кнопка переименования таблицы
        self.rename_table_btn = QPushButton("⚙ Переименовать")
        self.rename_table_btn.setMaximumWidth(150)
        self.rename_table_btn.clicked.connect(self.rename_current_table)
        table_selection_layout.addWidget(self.rename_table_btn)

        # Кнопка вывода данных
        self.display_btn = QPushButton("📊 Вывод данных")
        self.display_btn.setMaximumWidth(150)
        self.display_btn.clicked.connect(self.show_display_options)
        table_selection_layout.addWidget(self.display_btn)

        table_selection_layout.addStretch()
        layout.addLayout(table_selection_layout)

        # Таблица данных
        self.data_table = QTableWidget()
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.data_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.data_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.data_table.verticalHeader().setVisible(False)

        # Обработка клика по заголовку столбца
        self.data_table.horizontalHeader().sectionClicked.connect(self.on_column_header_clicked)

        layout.addWidget(self.data_table)

        # Панель кнопок
        buttons_layout = QHBoxLayout()

        # Кнопка поиска (самая левая)
        self.search_btn = QPushButton("🔍 Поиск")
        self.search_btn.clicked.connect(self.open_search_dialog)
        buttons_layout.addWidget(self.search_btn)

        # Кнопка редактирования
        self.edit_btn = QPushButton("✏ Редактировать")
        self.edit_btn.clicked.connect(self.show_edit_menu)
        buttons_layout.addWidget(self.edit_btn)

        # Кнопка добавления
        self.add_btn = QPushButton("➕ Добавить")
        self.add_btn.clicked.connect(self.show_add_menu)
        buttons_layout.addWidget(self.add_btn)

        # Кнопка удаления записи
        self.delete_btn = QPushButton("🗑 Удалить запись")
        self.delete_btn.clicked.connect(self.delete_record)
        buttons_layout.addWidget(self.delete_btn)

        # Кнопка строковых функций
        self.string_func_btn = QPushButton("📝 Строковые функции")
        self.string_func_btn.clicked.connect(self.show_string_functions)
        buttons_layout.addWidget(self.string_func_btn)

        buttons_layout.addStretch()

        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(close_btn)

        layout.addLayout(buttons_layout)

    def load_tables(self):
        """Загрузка списка таблиц из БД."""
        tables = self.controller.get_all_tables()
        self.table_combo.clear()
        self.table_combo.addItems(tables)

    def on_table_changed(self, table_name):
        """Обработка изменения выбранной таблицы."""
        if not table_name:
            return

        self.current_table = table_name
        self.load_table_data()

    def load_table_data(self, columns=None, where=None, order_by=None, group_by=None, having=None):
        """Загрузка данных таблицы."""
        if not self.current_table:
            return

        # Получаем информацию о столбцах
        self.all_columns_info = self.controller.get_table_columns(self.current_table)

        # Определяем столбцы для отображения
        if columns:
            self.current_columns = columns
        else:
            self.current_columns = [col['name'] for col in self.all_columns_info]

        # Получаем данные
        data = self.controller.get_table_data(
            self.current_table,
            self.current_columns if columns else None,
            where,
            order_by,
            group_by,
            having
        )

        # Заполняем таблицу
        self.data_table.setColumnCount(len(self.current_columns))
        self.data_table.setHorizontalHeaderLabels(self.current_columns)
        self.data_table.setRowCount(len(data))

        for row_idx, row_data in enumerate(data):
            for col_idx, value in enumerate(row_data):
                # Преобразуем значение в строку
                str_value = str(value) if value is not None else ""

                # Проверяем, является ли значение числовым для правильной сортировки
                if isinstance(value, (int, float)):
                    item = NumericTableItem(str_value, value)
                else:
                    item = QTableWidgetItem(str_value)

                self.data_table.setItem(row_idx, col_idx, item)

        self.logger.info(f"Загружены данные таблицы {self.current_table}: {len(data)} строк")

    def on_column_header_clicked(self, logical_index):
        """Обработка клика по заголовку столбца - открытие меню."""
        if not self.current_table or logical_index >= len(self.current_columns):
            return

        column_name = self.current_columns[logical_index]

        # Создаем контекстное меню
        menu = QMenu(self)

        # Сортировка по возрастанию
        sort_asc_action = QAction("⬆ Сортировать по возрастанию", self)
        sort_asc_action.triggered.connect(lambda: self.sort_by_column(column_name, "ASC"))
        menu.addAction(sort_asc_action)

        # Сортировка по убыванию
        sort_desc_action = QAction("⬇ Сортировать по убыванию", self)
        sort_desc_action.triggered.connect(lambda: self.sort_by_column(column_name, "DESC"))
        menu.addAction(sort_desc_action)

        menu.addSeparator()

        # Группировка
        group_action = QAction("📊 Группировка с COUNT", self)
        group_action.triggered.connect(lambda: self.group_by_column(column_name))
        menu.addAction(group_action)

        # Отображаем меню в позиции курсора
        menu.exec_(self.data_table.horizontalHeader().mapToGlobal(
            self.data_table.horizontalHeader().pos()))

    def sort_by_column(self, column_name, order):
        """Сортировка данных по столбцу."""
        order_clause = f"{column_name} {order}"
        self.load_table_data(order_by=order_clause)
        self.logger.info(f"Сортировка по {column_name} {order}")

    def group_by_column(self, column_name):
        """Группировка данных по столбцу с COUNT."""
        # Создаем запрос с группировкой
        columns = [column_name, f"COUNT(*) as count"]
        self.load_table_data(
            columns=columns,
            group_by=column_name,
            order_by=f"COUNT(*) DESC"
        )
        self.logger.info(f"Группировка по {column_name}")

    def show_add_menu(self):
        """Показ меню добавления."""
        menu = QMenu(self)

        add_column_action = QAction("➕ Создать столбец", self)
        add_column_action.triggered.connect(self.add_column)
        menu.addAction(add_column_action)

        add_record_action = QAction("➕ Создать запись", self)
        add_record_action.triggered.connect(self.add_record)
        menu.addAction(add_record_action)

        menu.exec_(self.add_btn.mapToGlobal(self.add_btn.rect().bottomLeft()))

    def show_edit_menu(self):
        """Показ меню редактирования."""
        menu = QMenu(self)

        edit_column_action = QAction("✏ Редактировать столбец", self)
        edit_column_action.triggered.connect(self.show_edit_column_menu)
        menu.addAction(edit_column_action)

        edit_record_action = QAction("✏ Редактировать запись", self)
        edit_record_action.triggered.connect(self.edit_record)
        menu.addAction(edit_record_action)

        menu.exec_(self.edit_btn.mapToGlobal(self.edit_btn.rect().bottomLeft()))

    def show_edit_column_menu(self):
        """Показ меню редактирования столбца."""
        dialog = EditColumnDialog(self.controller, self.current_table, self.all_columns_info, self)
        if dialog.exec_():
            self.load_table_data()

    def add_column(self):
        """Добавление нового столбца."""
        dialog = AddColumnDialog(self.controller, self.current_table, self)
        if dialog.exec_():
            self.load_table_data()

    def add_record(self):
        """Добавление новой записи."""
        dialog = AddRecordDialog(self.controller, self.current_table, self.all_columns_info, self)
        if dialog.exec_():
            self.load_table_data()

    def edit_record(self):
        """Редактирование выбранной записи."""
        selected_rows = self.data_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Ошибка", "Выберите запись для редактирования")
            return

        row = selected_rows[0].row()
        row_data = {}
        for col_idx, col_name in enumerate(self.current_columns):
            item = self.data_table.item(row, col_idx)
            row_data[col_name] = item.text() if item else ""

        dialog = EditRecordDialog(self.controller, self.current_table, self.all_columns_info, row_data, self)
        if dialog.exec_():
            self.load_table_data()

    def delete_record(self):
        """Удаление выбранной записи."""
        selected_rows = self.data_table.selectedItems()
        if not selected_rows:
            QMessageBox.warning(self, "Ошибка", "Выберите запись для удаления")
            return

        confirm = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите удалить эту запись?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm != QMessageBox.Yes:
            return

        row = selected_rows[0].row()

        # Формируем WHERE условие на основе первого столбца (обычно это ID)
        if not self.current_columns:
            QMessageBox.warning(self, "Ошибка", "Нет данных для удаления")
            return

        first_col = self.current_columns[0]
        first_value = self.data_table.item(row, 0).text()

        where_clause = f"{first_col} = %s"
        success, error = self.controller.delete_row(self.current_table, where_clause, [first_value])

        if success:
            QMessageBox.information(self, "Успех", "Запись успешно удалена")
            self.load_table_data()
        else:
            QMessageBox.critical(self, "Ошибка", f"Не удалось удалить запись:\n{error}")

    def rename_current_table(self):
        """Переименование текущей таблицы."""
        if not self.current_table:
            QMessageBox.warning(self, "Ошибка", "Выберите таблицу")
            return

        new_name, ok = QInputDialog.getText(
            self,
            "Переименование таблицы",
            f"Новое имя для таблицы '{self.current_table}':",
            text=self.current_table
        )

        if ok and new_name and new_name != self.current_table:
            success, error = self.controller.rename_table(self.current_table, new_name)
            if success:
                QMessageBox.information(self, "Успех", f"Таблица переименована: {self.current_table} → {new_name}")
                self.load_tables()
                # Устанавливаем новое имя как текущее
                index = self.table_combo.findText(new_name)
                if index >= 0:
                    self.table_combo.setCurrentIndex(index)
            else:
                QMessageBox.critical(self, "Ошибка", f"Не удалось переименовать таблицу:\n{error}")

    def show_display_options(self):
        """Показ опций вывода данных."""
        dialog = DisplayOptionsDialog(self.controller, self.current_table, self.all_columns_info, self)
        if dialog.exec_():
            # Применяем настройки отображения
            if dialog.is_join_mode:
                # Режим JOIN
                self.execute_join_display(dialog.join_config)
            else:
                # Обычный режим с выбором столбцов
                self.load_table_data(
                    columns=dialog.selected_columns if dialog.selected_columns else None,
                    where=dialog.where_clause if dialog.where_clause else None,
                    order_by=dialog.order_clause if dialog.order_clause else None,
                    group_by=dialog.group_clause if dialog.group_clause else None,
                    having=dialog.having_clause if dialog.having_clause else None
                )

    def execute_join_display(self, join_config):
        """Выполнение и отображение результатов JOIN."""
        try:
            results = self.controller.execute_join(
                join_config['tables_info'],
                join_config['selected_columns'],
                join_config['join_conditions'],
                join_config.get('where'),
                join_config.get('order_by')
            )

            # Отображаем результаты
            if results:
                self.current_columns = join_config['column_labels']
                self.data_table.setColumnCount(len(self.current_columns))
                self.data_table.setHorizontalHeaderLabels(self.current_columns)
                self.data_table.setRowCount(len(results))

                for row_idx, row_data in enumerate(results):
                    for col_idx, value in enumerate(row_data):
                        str_value = str(value) if value is not None else ""
                        item = QTableWidgetItem(str_value)
                        self.data_table.setItem(row_idx, col_idx, item)

                self.logger.info(f"Выполнен JOIN запрос: {len(results)} строк")
            else:
                QMessageBox.information(self, "Результат", "Запрос не вернул результатов")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка выполнения JOIN:\n{str(e)}")

    def open_search_dialog(self):
        """Открытие диалога поиска."""
        dialog = SearchDialog(self.controller, self.current_table, self.all_columns_info, self)
        if dialog.exec_():
            # Применяем результаты поиска
            self.load_table_data(where=dialog.search_condition)

    def show_string_functions(self):
        """Показ диалога строковых функций."""
        dialog = StringFunctionsDialog(self.controller, self.current_table, self.all_columns_info, self)
        dialog.exec_()


class AddColumnDialog(QDialog):
    """Диалог добавления нового столбца."""
    def __init__(self, controller, table_name, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name

        self.setWindowTitle("Добавить столбец")
        self.setMinimumWidth(400)
        self.setup_ui()

    def setup_ui(self):
        """Настройка UI."""
        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        layout.addRow("Имя столбца:", self.name_edit)

        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "INTEGER", "BIGINT", "VARCHAR(100)", "VARCHAR(200)",
            "TEXT", "BOOLEAN", "DATE", "TIMESTAMP", "NUMERIC"
        ])
        layout.addRow("Тип данных:", self.type_combo)

        self.nullable_check = QCheckBox("Может быть NULL")
        self.nullable_check.setChecked(True)
        layout.addRow("", self.nullable_check)

        self.default_edit = QLineEdit()
        layout.addRow("Значение по умолчанию:", self.default_edit)

        # Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def accept_dialog(self):
        """Принятие диалога с валидацией."""
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите имя столбца")
            return

        data_type = self.type_combo.currentText()
        nullable = self.nullable_check.isChecked()
        default = self.default_edit.text().strip() if self.default_edit.text().strip() else None

        success, error = self.controller.add_column(
            self.table_name, name, data_type, nullable, default
        )

        if success:
            QMessageBox.information(self, "Успех", f"Столбец '{name}' успешно добавлен")
            self.accept()
        else:
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить столбец:\n{error}")


class EditColumnDialog(QDialog):
    """Диалог редактирования столбца."""
    def __init__(self, controller, table_name, columns_info, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info

        self.setWindowTitle("Редактировать столбец")
        self.setMinimumWidth(450)
        self.setup_ui()

    def setup_ui(self):
        """Настройка UI."""
        layout = QVBoxLayout(self)

        # Выбор столбца
        column_layout = QHBoxLayout()
        column_layout.addWidget(QLabel("Столбец:"))
        self.column_combo = QComboBox()
        self.column_combo.addItems([col['name'] for col in self.columns_info])
        column_layout.addWidget(self.column_combo)
        layout.addLayout(column_layout)

        # Операции
        operations_label = QLabel("<b>Выберите операцию:</b>")
        layout.addWidget(operations_label)

        # Переименование
        rename_btn = QPushButton("Переименовать столбец")
        rename_btn.clicked.connect(self.rename_column)
        layout.addWidget(rename_btn)

        # Изменение типа
        change_type_btn = QPushButton("Изменить тип данных")
        change_type_btn.clicked.connect(self.change_column_type)
        layout.addWidget(change_type_btn)

        # Установка ограничения
        set_constraint_btn = QPushButton("Установить ограничение")
        set_constraint_btn.clicked.connect(self.set_constraint)
        layout.addWidget(set_constraint_btn)

        # Снятие ограничения
        drop_constraint_btn = QPushButton("Снять ограничение")
        drop_constraint_btn.clicked.connect(self.drop_constraint)
        layout.addWidget(drop_constraint_btn)

        # Удаление столбца
        delete_btn = QPushButton("Удалить столбец")
        delete_btn.clicked.connect(self.delete_column)
        delete_btn.setStyleSheet("background-color: #d32f2f; color: white;")
        layout.addWidget(delete_btn)

        layout.addStretch()

        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def get_current_column(self):
        """Получение текущего выбранного столбца."""
        return self.column_combo.currentText()

    def rename_column(self):
        """Переименование столбца."""
        old_name = self.get_current_column()
        new_name, ok = QInputDialog.getText(
            self, "Переименование столбца",
            f"Новое имя для столбца '{old_name}':",
            text=old_name
        )

        if ok and new_name and new_name != old_name:
            success, error = self.controller.rename_column(self.table_name, old_name, new_name)
            if success:
                QMessageBox.information(self, "Успех", f"Столбец переименован: {old_name} → {new_name}")
                # Обновляем список столбцов
                current_index = self.column_combo.currentIndex()
                self.columns_info[current_index]['name'] = new_name
                self.column_combo.setItemText(current_index, new_name)
            else:
                QMessageBox.critical(self, "Ошибка", f"Не удалось переименовать столбец:\n{error}")

    def change_column_type(self):
        """Изменение типа данных столбца."""
        column = self.get_current_column()

        types = ["INTEGER", "BIGINT", "VARCHAR(100)", "VARCHAR(200)", "TEXT", "BOOLEAN", "DATE", "TIMESTAMP", "NUMERIC"]
        new_type, ok = QInputDialog.getItem(
            self, "Изменение типа",
            f"Новый тип для столбца '{column}':",
            types, 0, False
        )

        if ok and new_type:
            success, error = self.controller.alter_column_type(self.table_name, column, new_type)
            if success:
                QMessageBox.information(self, "Успех", f"Тип столбца '{column}' изменен на {new_type}")
            else:
                QMessageBox.critical(self, "Ошибка", f"Не удалось изменить тип столбца:\n{error}")

    def set_constraint(self):
        """Установка ограничения на столбец."""
        column = self.get_current_column()

        constraints = ["NOT NULL", "UNIQUE", "CHECK"]
        constraint, ok = QInputDialog.getItem(
            self, "Установка ограничения",
            f"Выберите тип ограничения для '{column}':",
            constraints, 0, False
        )

        if not ok:
            return

        constraint_value = None
        if constraint == "CHECK":
            constraint_value, ok = QInputDialog.getText(
                self, "Условие CHECK",
                f"Введите условие CHECK для '{column}':\n(например: {column} > 0)"
            )
            if not ok or not constraint_value:
                return

        success, error = self.controller.set_constraint(
            self.table_name, column, constraint, constraint_value
        )

        if success:
            QMessageBox.information(self, "Успех", f"Ограничение {constraint} установлено на столбец '{column}'")
        else:
            QMessageBox.critical(self, "Ошибка", f"Не удалось установить ограничение:\n{error}")

    def drop_constraint(self):
        """Снятие ограничения со столбца."""
        column = self.get_current_column()

        constraints = ["NOT NULL", "UNIQUE", "CHECK"]
        constraint, ok = QInputDialog.getItem(
            self, "Снятие ограничения",
            f"Выберите тип ограничения для снятия с '{column}':",
            constraints, 0, False
        )

        if ok:
            success, error = self.controller.drop_constraint(self.table_name, column, constraint)
            if success:
                QMessageBox.information(self, "Успех", f"Ограничение {constraint} снято со столбца '{column}'")
            else:
                QMessageBox.critical(self, "Ошибка", f"Не удалось снять ограничение:\n{error}")

    def delete_column(self):
        """Удаление столбца."""
        column = self.get_current_column()

        confirm = QMessageBox.question(
            self, "Подтверждение",
            f"Вы уверены, что хотите удалить столбец '{column}'?\nЭто действие необратимо!",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            success, error = self.controller.drop_column(self.table_name, column)
            if success:
                QMessageBox.information(self, "Успех", f"Столбец '{column}' удален")
                self.accept()
            else:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить столбец:\n{error}")


class AddRecordDialog(QDialog):
    """Диалог добавления новой записи."""
    def __init__(self, controller, table_name, columns_info, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info
        self.field_widgets = {}

        self.setWindowTitle("Добавить запись")
        self.setMinimumWidth(500)
        self.setup_ui()

    def setup_ui(self):
        """Настройка UI."""
        layout = QFormLayout(self)

        # Создаем поля ввода для каждого столбца
        for col in self.columns_info:
            # Пропускаем SERIAL столбцы (они автоинкрементные)
            if 'serial' in col.get('type', '').lower() or 'nextval' in str(col.get('default', '')).lower():
                continue

            widget = QLineEdit()
            if col.get('default'):
                widget.setPlaceholderText(f"По умолчанию: {col['default']}")

            self.field_widgets[col['name']] = widget
            label_text = col['name']
            if not col.get('nullable', True):
                label_text += " *"
            layout.addRow(f"{label_text}:", widget)

        # Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def accept_dialog(self):
        """Принятие диалога с валидацией."""
        data = {}
        for col_name, widget in self.field_widgets.items():
            value = widget.text().strip()
            if value:
                data[col_name] = value

        if not data:
            QMessageBox.warning(self, "Ошибка", "Заполните хотя бы одно поле")
            return

        success, error = self.controller.insert_row(self.table_name, data)

        if success:
            QMessageBox.information(self, "Успех", "Запись успешно добавлена")
            self.accept()
        else:
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить запись:\n{error}")


class EditRecordDialog(QDialog):
    """Диалог редактирования записи."""
    def __init__(self, controller, table_name, columns_info, current_data, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info
        self.current_data = current_data
        self.field_widgets = {}

        self.setWindowTitle("Редактировать запись")
        self.setMinimumWidth(500)
        self.setup_ui()

    def setup_ui(self):
        """Настройка UI."""
        layout = QFormLayout(self)

        # Создаем поля ввода для каждого столбца
        for col in self.columns_info:
            col_name = col['name']
            widget = QLineEdit()

            # Устанавливаем текущее значение
            if col_name in self.current_data:
                widget.setText(str(self.current_data[col_name]))

            self.field_widgets[col_name] = widget

            # Первый столбец (обычно ID) делаем readonly
            if col_name == self.columns_info[0]['name']:
                widget.setReadOnly(True)
                widget.setStyleSheet("background-color: #f0f0f0;")

            layout.addRow(f"{col_name}:", widget)

        # Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def accept_dialog(self):
        """Принятие диалога с валидацией."""
        # Первый столбец используем для WHERE
        first_col = self.columns_info[0]['name']
        where_value = self.field_widgets[first_col].text()

        # Собираем данные для обновления (кроме первого столбца)
        data = {}
        for col_name, widget in self.field_widgets.items():
            if col_name != first_col:
                value = widget.text().strip()
                if value:
                    data[col_name] = value

        if not data:
            QMessageBox.warning(self, "Ошибка", "Нет данных для обновления")
            return

        where_clause = f"{first_col} = %s"
        success, error = self.controller.update_row(
            self.table_name, data, where_clause, [where_value]
        )

        if success:
            QMessageBox.information(self, "Успех", "Запись успешно обновлена")
            self.accept()
        else:
            QMessageBox.critical(self, "Ошибка", f"Не удалось обновить запись:\n{error}")


class SearchDialog(QDialog):
    """Диалог поиска по таблице."""
    def __init__(self, controller, table_name, columns_info, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info
        self.search_condition = None

        self.setWindowTitle("Поиск")
        self.setMinimumWidth(500)
        self.setup_ui()

    def setup_ui(self):
        """Настройка UI."""
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<h3>Поиск по таблице</h3>"))

        form_layout = QFormLayout()

        # Выбор столбца
        self.column_combo = QComboBox()
        self.column_combo.addItems([col['name'] for col in self.columns_info])
        form_layout.addRow("Столбец:", self.column_combo)

        # Выбор типа поиска
        self.search_type_combo = QComboBox()
        self.search_type_combo.addItems([
            "LIKE (шаблон)",
            "POSIX ~ (регулярка)",
            "POSIX ~* (регулярка без учета регистра)",
            "POSIX !~ (не соответствует)",
            "POSIX !~* (не соответствует без учета регистра)",
            "= (точное совпадение)"
        ])
        form_layout.addRow("Тип поиска:", self.search_type_combo)

        # Текст поиска
        self.search_text = QLineEdit()
        self.search_text.setPlaceholderText("Введите текст для поиска...")
        form_layout.addRow("Текст:", self.search_text)

        layout.addLayout(form_layout)

        # Подсказка
        hint_label = QLabel(
            "<i>Подсказка: для LIKE используйте % как подстановочный символ<br>"
            "Пример: %текст% найдет все записи содержащие 'текст'</i>"
        )
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)

        # Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept_dialog(self):
        """Формирование условия поиска."""
        column = self.column_combo.currentText()
        search_text = self.search_text.text().strip()

        if not search_text:
            QMessageBox.warning(self, "Ошибка", "Введите текст для поиска")
            return

        search_type = self.search_type_combo.currentText()

        # Формируем условие в зависимости от типа поиска
        if "LIKE" in search_type:
            self.search_condition = f"{column} LIKE '{search_text}'"
        elif "~*" in search_type and "!" in search_type:
            self.search_condition = f"{column} !~* '{search_text}'"
        elif "~*" in search_type:
            self.search_condition = f"{column} ~* '{search_text}'"
        elif "!~" in search_type:
            self.search_condition = f"{column} !~ '{search_text}'"
        elif "~" in search_type:
            self.search_condition = f"{column} ~ '{search_text}'"
        else:  # точное совпадение
            self.search_condition = f"{column} = '{search_text}'"

        self.accept()


class StringFunctionsDialog(QDialog):
    """Диалог работы со строковыми функциями."""
    def __init__(self, controller, table_name, columns_info, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info

        self.setWindowTitle("Строковые функции")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self.setup_ui()

    def setup_ui(self):
        """Настройка UI."""
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<h3>Применение строковых функций</h3>"))

        form_layout = QFormLayout()

        # Выбор столбца
        self.column_combo = QComboBox()
        string_columns = [col['name'] for col in self.columns_info
                         if 'char' in col.get('type', '').lower() or 'text' in col.get('type', '').lower()]
        if not string_columns:
            string_columns = [col['name'] for col in self.columns_info]
        self.column_combo.addItems(string_columns)
        form_layout.addRow("Столбец:", self.column_combo)

        # Выбор функции
        self.function_combo = QComboBox()
        self.function_combo.addItems([
            "UPPER (верхний регистр)",
            "LOWER (нижний регистр)",
            "SUBSTRING (подстрока)",
            "TRIM (удаление пробелов)",
            "LTRIM (удаление пробелов слева)",
            "RTRIM (удаление пробелов справа)",
            "LPAD (дополнение слева)",
            "RPAD (дополнение справа)",
            "CONCAT (объединение)",
            "LENGTH (длина строки)"
        ])
        self.function_combo.currentTextChanged.connect(self.on_function_changed)
        form_layout.addRow("Функция:", self.function_combo)

        layout.addLayout(form_layout)

        # Дополнительные параметры
        self.params_widget = QWidget()
        self.params_layout = QFormLayout(self.params_widget)
        layout.addWidget(self.params_widget)

        # Таблица результатов
        layout.addWidget(QLabel("<b>Результат:</b>"))
        self.result_table = QTableWidget()
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.result_table)

        # Кнопки
        buttons_layout = QHBoxLayout()

        apply_btn = QPushButton("Применить функцию")
        apply_btn.clicked.connect(self.apply_function)
        buttons_layout.addWidget(apply_btn)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(close_btn)

        layout.addLayout(buttons_layout)

        self.on_function_changed(self.function_combo.currentText())

    def on_function_changed(self, function_text):
        """Обработка изменения выбранной функции."""
        # Очищаем предыдущие параметры
        while self.params_layout.rowCount() > 0:
            self.params_layout.removeRow(0)

        # Добавляем специфические параметры для функции
        if "SUBSTRING" in function_text:
            self.start_pos = QSpinBox()
            self.start_pos.setRange(1, 1000)
            self.start_pos.setValue(1)
            self.params_layout.addRow("Начальная позиция:", self.start_pos)

            self.length = QSpinBox()
            self.length.setRange(1, 1000)
            self.length.setValue(10)
            self.params_layout.addRow("Длина:", self.length)

        elif "LPAD" in function_text or "RPAD" in function_text:
            self.pad_length = QSpinBox()
            self.pad_length.setRange(1, 1000)
            self.pad_length.setValue(20)
            self.params_layout.addRow("Длина:", self.pad_length)

            self.pad_char = QLineEdit()
            self.pad_char.setText(" ")
            self.pad_char.setMaxLength(1)
            self.params_layout.addRow("Символ:", self.pad_char)

        elif "CONCAT" in function_text:
            self.concat_text = QLineEdit()
            self.concat_text.setPlaceholderText("Текст для объединения")
            self.params_layout.addRow("Текст:", self.concat_text)

            self.concat_position = QComboBox()
            self.concat_position.addItems(["В начале", "В конце"])
            self.params_layout.addRow("Позиция:", self.concat_position)

    def apply_function(self):
        """Применение выбранной функции."""
        column = self.column_combo.currentText()
        function = self.function_combo.currentText()

        # Формируем SQL выражение
        if "UPPER" in function:
            sql_expr = f"UPPER({column})"
        elif "LOWER" in function:
            sql_expr = f"LOWER({column})"
        elif "SUBSTRING" in function:
            start = self.start_pos.value()
            length = self.length.value()
            sql_expr = f"SUBSTRING({column}, {start}, {length})"
        elif "LTRIM" in function:
            sql_expr = f"LTRIM({column})"
        elif "RTRIM" in function:
            sql_expr = f"RTRIM({column})"
        elif "TRIM" in function:
            sql_expr = f"TRIM({column})"
        elif "LPAD" in function:
            length = self.pad_length.value()
            char = self.pad_char.text() or ' '
            sql_expr = f"LPAD({column}, {length}, '{char}')"
        elif "RPAD" in function:
            length = self.pad_length.value()
            char = self.pad_char.text() or ' '
            sql_expr = f"RPAD({column}, {length}, '{char}')"
        elif "CONCAT" in function:
            text = self.concat_text.text()
            if self.concat_position.currentText() == "В начале":
                sql_expr = f"'{text}' || {column}"
            else:
                sql_expr = f"{column} || '{text}'"
        elif "LENGTH" in function:
            sql_expr = f"LENGTH({column})"
        else:
            QMessageBox.warning(self, "Ошибка", "Неизвестная функция")
            return

        # Выполняем запрос
        query = f"SELECT {column} as original, {sql_expr} as result FROM {self.table_name} LIMIT 20"
        results = self.controller.execute_select(query)

        # Отображаем результаты
        if results:
            self.result_table.setColumnCount(2)
            self.result_table.setHorizontalHeaderLabels(["Оригинал", "Результат"])
            self.result_table.setRowCount(len(results))

            for row_idx, row_data in enumerate(results):
                for col_idx, value in enumerate(row_data):
                    str_value = str(value) if value is not None else ""
                    item = QTableWidgetItem(str_value)
                    self.result_table.setItem(row_idx, col_idx, item)

            self.result_table.resizeColumnsToContents()
        else:
            QMessageBox.information(self, "Результат", "Нет данных для отображения")


class DisplayOptionsDialog(QDialog):
    """Диалог опций вывода данных."""
    def __init__(self, controller, table_name, columns_info, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info

        self.selected_columns = None
        self.where_clause = None
        self.order_clause = None
        self.group_clause = None
        self.having_clause = None
        self.is_join_mode = False
        self.join_config = None

        self.setWindowTitle("Настройки вывода")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)
        self.setup_ui()

    def setup_ui(self):
        """Настройка UI."""
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<h3>Настройки вывода данных</h3>"))

        # Кнопка мастера соединений
        join_btn = QPushButton("🔗 Мастер соединений (JOIN)")
        join_btn.clicked.connect(self.open_join_wizard)
        layout.addWidget(join_btn)

        layout.addWidget(QLabel("<hr>"))
        layout.addWidget(QLabel("<b>Или настройте обычную выборку:</b>"))

        # Выбор столбцов
        columns_group = QLabel("<b>Выбор столбцов:</b>")
        layout.addWidget(columns_group)

        self.columns_checks = {}
        columns_layout = QVBoxLayout()

        # Добавляем чекбоксы для каждого столбца
        for col in self.columns_info:
            check = QCheckBox(f"{col['name']} ({col['type']})")
            check.setChecked(True)
            self.columns_checks[col['name']] = check
            columns_layout.addWidget(check)

        layout.addLayout(columns_layout)

        # WHERE условие
        where_layout = QHBoxLayout()
        where_layout.addWidget(QLabel("WHERE:"))
        self.where_edit = QLineEdit()
        self.where_edit.setPlaceholderText("Например: id > 5 AND name LIKE '%test%'")
        where_layout.addWidget(self.where_edit)
        layout.addLayout(where_layout)

        # ORDER BY
        order_layout = QHBoxLayout()
        order_layout.addWidget(QLabel("ORDER BY:"))
        self.order_edit = QLineEdit()
        self.order_edit.setPlaceholderText("Например: id DESC, name ASC")
        order_layout.addWidget(self.order_edit)
        layout.addLayout(order_layout)

        # GROUP BY
        group_layout = QHBoxLayout()
        group_layout.addWidget(QLabel("GROUP BY:"))
        self.group_edit = QLineEdit()
        self.group_edit.setPlaceholderText("Например: name")
        group_layout.addWidget(self.group_edit)
        layout.addLayout(group_layout)

        # HAVING
        having_layout = QHBoxLayout()
        having_layout.addWidget(QLabel("HAVING:"))
        self.having_edit = QLineEdit()
        self.having_edit.setPlaceholderText("Например: COUNT(*) > 5")
        having_layout.addWidget(self.having_edit)
        layout.addLayout(having_layout)

        # Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def open_join_wizard(self):
        """Открытие мастера соединений."""
        wizard = JoinWizardDialog(self.controller, self.table_name, self)
        if wizard.exec_():
            self.is_join_mode = True
            self.join_config = wizard.get_join_config()
            self.accept()

    def accept_dialog(self):
        """Принятие настроек."""
        # Собираем выбранные столбцы
        selected = [name for name, check in self.columns_checks.items() if check.isChecked()]
        self.selected_columns = selected if selected else None

        # Собираем условия
        self.where_clause = self.where_edit.text().strip() or None
        self.order_clause = self.order_edit.text().strip() or None
        self.group_clause = self.group_edit.text().strip() or None
        self.having_clause = self.having_edit.text().strip() or None

        self.accept()


class JoinWizardDialog(QDialog):
    """Мастер создания JOIN запросов."""
    def __init__(self, controller, base_table, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.base_table = base_table

        self.setWindowTitle("Мастер соединений (JOIN)")
        self.setMinimumWidth(800)
        self.setMinimumHeight(600)
        self.setup_ui()

    def setup_ui(self):
        """Настройка UI."""
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"<h3>Создание JOIN запроса</h3>"))
        layout.addWidget(QLabel(f"<b>Базовая таблица:</b> {self.base_table}"))

        # Таблица для присоединения
        join_table_layout = QHBoxLayout()
        join_table_layout.addWidget(QLabel("Присоединить таблицу:"))

        self.join_table_combo = QComboBox()
        all_tables = self.controller.get_all_tables()
        # Убираем текущую таблицу из списка
        other_tables = [t for t in all_tables if t != self.base_table]
        self.join_table_combo.addItems(other_tables)
        join_table_layout.addWidget(self.join_table_combo)

        layout.addLayout(join_table_layout)

        # Тип соединения
        join_type_layout = QHBoxLayout()
        join_type_layout.addWidget(QLabel("Тип соединения:"))

        self.join_type_combo = QComboBox()
        self.join_type_combo.addItems(["INNER", "LEFT", "RIGHT", "FULL"])
        join_type_layout.addWidget(self.join_type_combo)

        layout.addLayout(join_type_layout)

        # Условие соединения
        layout.addWidget(QLabel("<b>Условие соединения (ON):</b>"))

        on_layout = QHBoxLayout()

        # Столбец из базовой таблицы
        self.base_column_combo = QComboBox()
        self.update_base_columns()
        on_layout.addWidget(QLabel(f"{self.base_table}."))
        on_layout.addWidget(self.base_column_combo)

        on_layout.addWidget(QLabel(" = "))

        # Столбец из присоединяемой таблицы
        self.join_column_combo = QComboBox()
        on_layout.addWidget(QLabel(""))
        self.join_table_label = QLabel()
        on_layout.addWidget(self.join_table_label)
        on_layout.addWidget(QLabel("."))
        on_layout.addWidget(self.join_column_combo)

        layout.addLayout(on_layout)

        # Выбор столбцов для вывода - СОЗДАЕМ ДО подключения сигнала
        layout.addWidget(QLabel("<b>Столбцы для вывода:</b>"))

        self.columns_text = QTextEdit()
        self.columns_text.setPlaceholderText(
            "Введите столбцы через запятую\n"
            f"Например: {self.base_table}.id, {self.base_table}.name, "
            f"{self.join_table_combo.currentText() if self.join_table_combo.count() > 0 else 'table2'}.field"
        )
        self.columns_text.setMaximumHeight(100)
        layout.addWidget(self.columns_text)

        # ТЕПЕРЬ подключаем сигнал и вызываем обновление
        self.join_table_combo.currentTextChanged.connect(self.update_join_columns)
        self.update_join_columns(self.join_table_combo.currentText())

        # Дополнительные условия
        layout.addWidget(QLabel("<b>WHERE (опционально):</b>"))
        self.where_edit = QLineEdit()
        layout.addWidget(self.where_edit)

        layout.addWidget(QLabel("<b>ORDER BY (опционально):</b>"))
        self.order_edit = QLineEdit()
        layout.addWidget(self.order_edit)

        # Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def update_base_columns(self):
        """Обновление списка столбцов базовой таблицы."""
        columns = self.controller.get_table_columns(self.base_table)
        self.base_column_combo.clear()
        self.base_column_combo.addItems([col['name'] for col in columns])

    def update_join_columns(self, table_name):
        """Обновление списка столбцов присоединяемой таблицы."""
        if not table_name:
            return

        self.join_table_label.setText(table_name)
        columns = self.controller.get_table_columns(table_name)
        self.join_column_combo.clear()
        self.join_column_combo.addItems([col['name'] for col in columns])

        # Обновляем плейсхолдер
        self.columns_text.setPlaceholderText(
            "Введите столбцы через запятую\n"
            f"Например: {self.base_table}.id, {self.base_table}.name, {table_name}.field"
        )

    def get_join_config(self):
        """Получение конфигурации JOIN."""
        join_table = self.join_table_combo.currentText()
        join_type = self.join_type_combo.currentText()

        base_col = self.base_column_combo.currentText()
        join_col = self.join_column_combo.currentText()

        on_condition = f"{self.base_table}.{base_col} = {join_table}.{join_col}"

        # Парсим выбранные столбцы
        columns_text = self.columns_text.toPlainText().strip()
        if columns_text:
            selected_columns = [col.strip() for col in columns_text.split(',')]
        else:
            # По умолчанию все столбцы
            selected_columns = [f"{self.base_table}.*", f"{join_table}.*"]

        return {
            'tables_info': [
                {'name': self.base_table, 'alias': None}
            ],
            'selected_columns': selected_columns,
            'column_labels': [col.replace('.', '_') for col in selected_columns],
            'join_conditions': [
                {
                    'type': join_type,
                    'table': join_table,
                    'alias': None,
                    'on': on_condition
                }
            ],
            'where': self.where_edit.text().strip() or None,
            'order_by': self.order_edit.text().strip() or None
        }
