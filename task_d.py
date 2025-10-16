"""
Модуль диалога для расширенной работы с таблицами БД.
Содержит класс TaskDialog с возможностями управления данными и структурой таблиц.
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                              QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
                              QComboBox, QLineEdit, QMenu, QInputDialog, QCheckBox,
                              QSpinBox, QFormLayout, QTextEdit, QDialogButtonBox, QWidget,
                              QButtonGroup, QRadioButton, QScrollArea, QGroupBox)
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
        self.is_join_mode = False
        self.selected_tables_for_join = []

        self.setWindowTitle("Техническое задание - Управление БД")
        self.setMinimumSize(1200, 700)

        self.setup_ui()

    def setup_ui(self):
        """Настройка пользовательского интерфейса."""
        layout = QVBoxLayout(self)

        # Заголовок
        title_layout = QHBoxLayout()
        title_label = QLabel("<h2>Управление структурой и данными БД</h2>")
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        layout.addLayout(title_layout)

        # Переключатель режима: обычная таблица / JOIN
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("<b>Режим работы:</b>"))

        self.mode_group = QButtonGroup(self)
        self.table_mode_radio = QRadioButton("Обычная таблица")
        self.join_mode_radio = QRadioButton("Метод JOIN")
        self.table_mode_radio.setChecked(True)

        self.mode_group.addButton(self.table_mode_radio)
        self.mode_group.addButton(self.join_mode_radio)

        self.table_mode_radio.toggled.connect(self.on_mode_changed)

        mode_layout.addWidget(self.table_mode_radio)
        mode_layout.addWidget(self.join_mode_radio)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        # Панель выбора таблиц/столбцов
        self.selection_widget = QWidget()
        self.selection_layout = QVBoxLayout(self.selection_widget)
        layout.addWidget(self.selection_widget)

        # Таблица данных
        self.data_table = QTableWidget()
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.data_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.data_table.setSelectionBehavior(QTableWidget.SelectItems)  # Выбор ячеек
        self.data_table.setSelectionMode(QTableWidget.SingleSelection)  # Одна ячейка
        self.data_table.verticalHeader().setVisible(False)

        # Убираем обработку клика по заголовку
        layout.addWidget(self.data_table)

        # Панель кнопок
        buttons_layout = QHBoxLayout()

        # Кнопка поиска
        self.search_btn = QPushButton("🔍 Поиск")
        self.search_btn.clicked.connect(self.open_search_dialog)
        buttons_layout.addWidget(self.search_btn)

        # Кнопка редактирования
        self.edit_btn = QPushButton("✏ Редактировать")
        self.edit_btn.clicked.connect(self.open_edit_dialog)
        buttons_layout.addWidget(self.edit_btn)

        # Кнопка добавления
        self.add_btn = QPushButton("➕ Добавить")
        self.add_btn.clicked.connect(self.open_add_dialog)
        buttons_layout.addWidget(self.add_btn)

        # Кнопка удаления
        self.delete_btn = QPushButton("🗑 Удалить")
        self.delete_btn.clicked.connect(self.open_delete_dialog)
        buttons_layout.addWidget(self.delete_btn)

        # Кнопка сортировки/группировки/фильтрации
        self.sort_btn = QPushButton("📊 Сортировка/Фильтрация")
        self.sort_btn.clicked.connect(self.open_sort_filter_dialog)
        buttons_layout.addWidget(self.sort_btn)

        # Кнопка вывода данных
        self.display_btn = QPushButton("📋 Вывод данных")
        self.display_btn.clicked.connect(self.open_display_dialog)
        buttons_layout.addWidget(self.display_btn)

        buttons_layout.addStretch()

        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(close_btn)

        layout.addLayout(buttons_layout)

        # Инициализируем панель выбора
        self.update_selection_panel()

    def on_mode_changed(self):
        """Обработка изменения режима работы."""
        self.is_join_mode = self.join_mode_radio.isChecked()
        self.update_selection_panel()

    def update_selection_panel(self):
        """Обновление панели выбора таблиц/столбцов в зависимости от режима."""
        # Очищаем текущую панель
        while self.selection_layout.count():
            child = self.selection_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if self.is_join_mode:
            # Режим JOIN
            self.setup_join_selection()
        else:
            # Режим обычной таблицы
            self.setup_table_selection()

    def setup_table_selection(self):
        """Настройка панели для обычной таблицы."""
        # Выбор таблицы
        table_layout = QHBoxLayout()
        table_layout.addWidget(QLabel("Таблица:"))

        self.table_combo = QComboBox()
        self.table_combo.setMinimumWidth(200)
        tables = self.controller.get_all_tables()
        self.table_combo.addItems(tables)
        self.table_combo.currentTextChanged.connect(self.on_table_selected)
        table_layout.addWidget(self.table_combo)
        table_layout.addStretch()

        self.selection_layout.addLayout(table_layout)

        # Выбор столбцов через галочки
        columns_group = QGroupBox("Выбор столбцов для отображения:")
        columns_scroll = QScrollArea()
        columns_scroll.setWidgetResizable(True)
        columns_scroll.setMaximumHeight(150)

        self.columns_widget = QWidget()
        self.columns_checks_layout = QVBoxLayout(self.columns_widget)
        self.columns_checks = {}

        columns_scroll.setWidget(self.columns_widget)
        columns_group_layout = QVBoxLayout(columns_group)
        columns_group_layout.addWidget(columns_scroll)

        self.selection_layout.addWidget(columns_group)

        # Загружаем первую таблицу
        if self.table_combo.count() > 0:
            self.on_table_selected(self.table_combo.currentText())

    def setup_join_selection(self):
        """Настройка панели для JOIN."""
        # Выбор таблиц для JOIN
        tables_group = QGroupBox("Выбор таблиц для объединения:")
        tables_scroll = QScrollArea()
        tables_scroll.setWidgetResizable(True)
        tables_scroll.setMaximumHeight(100)

        tables_widget = QWidget()
        self.tables_checks_layout = QVBoxLayout(tables_widget)
        self.tables_checks = {}

        all_tables = self.controller.get_all_tables()
        for table in all_tables:
            check = QCheckBox(table)
            check.stateChanged.connect(self.on_join_tables_changed)
            self.tables_checks[table] = check
            self.tables_checks_layout.addWidget(check)

        tables_scroll.setWidget(tables_widget)
        tables_group_layout = QVBoxLayout(tables_group)
        tables_group_layout.addWidget(tables_scroll)

        self.selection_layout.addWidget(tables_group)

        # Выбор столбцов (появится после выбора таблиц)
        self.join_columns_group = QGroupBox("Выбор столбцов для отображения:")
        self.join_columns_scroll = QScrollArea()
        self.join_columns_scroll.setWidgetResizable(True)
        self.join_columns_scroll.setMaximumHeight(150)

        self.join_columns_widget = QWidget()
        self.join_columns_layout = QVBoxLayout(self.join_columns_widget)
        self.join_column_checks = {}

        self.join_columns_scroll.setWidget(self.join_columns_widget)
        join_columns_group_layout = QVBoxLayout(self.join_columns_group)
        join_columns_group_layout.addWidget(self.join_columns_scroll)

        self.selection_layout.addWidget(self.join_columns_group)
        self.join_columns_group.setVisible(False)

    def on_table_selected(self, table_name):
        """Обработка выбора таблицы в режиме обычной таблицы."""
        if not table_name:
            return

        self.current_table = table_name

        # Обновляем список столбцов
        self.all_columns_info = self.controller.get_table_columns(table_name)

        # Очищаем старые чекбоксы
        while self.columns_checks_layout.count():
            child = self.columns_checks_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.columns_checks.clear()

        # Создаем новые чекбоксы
        for col in self.all_columns_info:
            check = QCheckBox(f"{col['name']} ({col['type']})")
            check.setChecked(True)
            check.stateChanged.connect(self.on_columns_changed)
            self.columns_checks[col['name']] = check
            self.columns_checks_layout.addWidget(check)

        # Загружаем данные
        self.load_table_data()

    def on_join_tables_changed(self):
        """Обработка изменения выбранных таблиц для JOIN."""
        selected_tables = [name for name, check in self.tables_checks.items() if check.isChecked()]

        if len(selected_tables) < 1:
            self.join_columns_group.setVisible(False)
            return

        # Показываем панель выбора столбцов
        self.join_columns_group.setVisible(True)

        # Очищаем старые чекбоксы
        while self.join_columns_layout.count():
            child = self.join_columns_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        self.join_column_checks.clear()

        # Создаем чекбоксы для каждого столбца каждой таблицы
        for table in selected_tables:
            # Добавляем заголовок таблицы
            table_label = QLabel(f"<b>{table}:</b>")
            self.join_columns_layout.addWidget(table_label)

            # Получаем столбцы
            columns = self.controller.get_table_columns(table)
            for col in columns:
                check = QCheckBox(f"  {col['name']} ({col['type']})")
                check.setChecked(True)
                self.join_column_checks[f"{table}.{col['name']}"] = check
                self.join_columns_layout.addWidget(check)

    def on_columns_changed(self):
        """Обработка изменения выбранных столбцов."""
        self.load_table_data()

    def load_table_data(self, where=None, order_by=None, group_by=None, having=None):
        """Загрузка данных таблицы."""
        if not self.current_table:
            return

        # Определяем выбранные столбцы
        selected_columns = [name for name, check in self.columns_checks.items() if check.isChecked()]

        if not selected_columns:
            self.data_table.setRowCount(0)
            self.data_table.setColumnCount(0)
            return

        self.current_columns = selected_columns

        # Получаем данные
        data = self.controller.get_table_data(
            self.current_table,
            selected_columns,
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
                str_value = str(value) if value is not None else ""

                if isinstance(value, (int, float)):
                    item = NumericTableItem(str_value, value)
                else:
                    item = QTableWidgetItem(str_value)

                self.data_table.setItem(row_idx, col_idx, item)

        self.logger.info(f"Загружены данные таблицы {self.current_table}: {len(data)} строк")

    def open_search_dialog(self):
        """Открытие диалога поиска."""
        if not self.current_table:
            QMessageBox.warning(self, "Ошибка", "Выберите таблицу")
            return

        dialog = SearchDialog(self.controller, self.current_table, self.all_columns_info, self)
        if dialog.exec_():
            self.load_table_data(where=dialog.search_condition)

    def open_edit_dialog(self):
        """Открытие диалога редактирования."""
        if not self.current_table:
            QMessageBox.warning(self, "Ошибка", "Выберите таблицу")
            return

        dialog = EditDialog(self.controller, self.current_table, self.all_columns_info, self.data_table, self)
        if dialog.exec_():
            self.load_table_data()

    def open_add_dialog(self):
        """Открытие диалога добавления."""
        if not self.current_table:
            QMessageBox.warning(self, "Ошибка", "Выберите таблицу")
            return

        dialog = AddDialog(self.controller, self.current_table, self.all_columns_info, self)
        if dialog.exec_():
            self.load_table_data()

    def open_delete_dialog(self):
        """Открытие диалога удаления."""
        if not self.current_table:
            QMessageBox.warning(self, "Ошибка", "Выберите таблицу")
            return

        dialog = DeleteDialog(self.controller, self.current_table, self.all_columns_info, self.data_table, self)
        if dialog.exec_():
            self.load_table_data()

    def open_sort_filter_dialog(self):
        """Открытие диалога сортировки/фильтрации."""
        if not self.current_table:
            QMessageBox.warning(self, "Ошибка", "Выберите таблицу")
            return

        dialog = SortFilterDialog(self.controller, self.current_table, self.all_columns_info, self)
        if dialog.exec_():
            self.load_table_data(
                where=dialog.where_clause,
                order_by=dialog.order_clause,
                group_by=dialog.group_clause,
                having=dialog.having_clause
            )

    def open_display_dialog(self):
        """Открытие диалога вывода данных (выбор таблицы и переименование)."""
        dialog = DisplayDialog(self.controller, self.current_table, self)
        if dialog.exec_():
            # Обновляем интерфейс если таблица была переименована
            self.update_selection_panel()


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
}


# Новые диалоги для отдельных окон

class EditDialog(QDialog):
    """Диалог редактирования (столбца или записи)."""
    def __init__(self, controller, table_name, columns_info, data_table, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info
        self.data_table = data_table

        self.setWindowTitle("Редактирование")
        self.setMinimumWidth(500)
        self.setup_ui()

    def setup_ui(self):
        """Настройка UI."""
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<h3>Выберите действие:</h3>"))

        # Кнопка редактирования столбца
        edit_column_btn = QPushButton("✏ Редактировать столбец")
        edit_column_btn.clicked.connect(self.edit_column)
        layout.addWidget(edit_column_btn)

        # Кнопка редактирования записи
        edit_record_btn = QPushButton("✏ Редактировать запись")
        edit_record_btn.clicked.connect(self.edit_record)
        layout.addWidget(edit_record_btn)

        layout.addStretch()

        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn)

    def edit_column(self):
        """Редактирование столбца."""
        dialog = EditColumnWithFunctionsDialog(self.controller, self.table_name, self.columns_info, self)
        if dialog.exec_():
            self.accept()

    def edit_record(self):
        """Редактирование записи."""
        selected_items = self.data_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Ошибка", "Выберите ячейку в записи для редактирования")
            return

        row = selected_items[0].row()
        row_data = {}

        # Получаем все столбцы из таблицы
        for col_idx in range(self.data_table.columnCount()):
            col_name = self.data_table.horizontalHeaderItem(col_idx).text()
            item = self.data_table.item(row, col_idx)
            row_data[col_name] = item.text() if item else ""

        dialog = EditRecordDialog(self.controller, self.table_name, self.columns_info, row_data, self)
        if dialog.exec_():
            self.accept()


class EditColumnWithFunctionsDialog(QDialog):
    """Диалог редактирования столбца со строковыми функциями."""
    def __init__(self, controller, table_name, columns_info, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info

        self.setWindowTitle("Редактировать столбец")
        self.setMinimumWidth(500)
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

        # Строковые функции
        string_funcs_btn = QPushButton("📝 Строковые функции")
        string_funcs_btn.clicked.connect(self.apply_string_functions)
        layout.addWidget(string_funcs_btn)

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

    def apply_string_functions(self):
        """Применение строковых функций к столбцу."""
        dialog = StringFunctionsDialog(self.controller, self.table_name, self.columns_info, self)
        dialog.exec_()


class AddDialog(QDialog):
    """Диалог добавления (столбца или записи)."""
    def __init__(self, controller, table_name, columns_info, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info

        self.setWindowTitle("Добавление")
        self.setMinimumWidth(400)
        self.setup_ui()

    def setup_ui(self):
        """Настройка UI."""
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<h3>Выберите действие:</h3>"))

        # Кнопка добавления столбца
        add_column_btn = QPushButton("➕ Создать столбец")
        add_column_btn.clicked.connect(self.add_column)
        layout.addWidget(add_column_btn)

        # Кнопка добавления записи
        add_record_btn = QPushButton("➕ Создать запись")
        add_record_btn.clicked.connect(self.add_record)
        layout.addWidget(add_record_btn)

        layout.addStretch()

        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn)

    def add_column(self):
        """Добавление столбца."""
        dialog = AddColumnDialog(self.controller, self.table_name, self)
        if dialog.exec_():
            self.accept()

    def add_record(self):
        """Добавление записи."""
        dialog = AddRecordDialog(self.controller, self.table_name, self.columns_info, self)
        if dialog.exec_():
            self.accept()


class DeleteDialog(QDialog):
    """Диалог удаления (столбца или записи)."""
    def __init__(self, controller, table_name, columns_info, data_table, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info
        self.data_table = data_table

        self.setWindowTitle("Удаление")
        self.setMinimumWidth(400)
        self.setup_ui()

    def setup_ui(self):
        """Настройка UI."""
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<h3>Выберите действие:</h3>"))

        # Кнопка удаления столбца
        delete_column_btn = QPushButton("🗑 Удалить столбец")
        delete_column_btn.clicked.connect(self.delete_column)
        layout.addWidget(delete_column_btn)

        # Кнопка удаления записи
        delete_record_btn = QPushButton("🗑 Удалить запись")
        delete_record_btn.clicked.connect(self.delete_record)
        layout.addWidget(delete_record_btn)

        layout.addStretch()

        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.reject)
        layout.addWidget(close_btn)

    def delete_column(self):
        """Удаление столбца."""
        column, ok = QInputDialog.getItem(
            self, "Удаление столбца",
            "Выберите столбец для удаления:",
            [col['name'] for col in self.columns_info], 0, False
        )

        if not ok:
            return

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

    def delete_record(self):
        """Удаление записи."""
        selected_items = self.data_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Ошибка", "Выберите ячейку в записи для удаления")
            return

        confirm = QMessageBox.question(
            self, "Подтверждение",
            "Вы уверены, что хотите удалить эту запись?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm != QMessageBox.Yes:
            return

        row = selected_items[0].row()

        # Формируем WHERE условие на основе первого столбца
        first_col_name = self.data_table.horizontalHeaderItem(0).text()
        first_value = self.data_table.item(row, 0).text()

        where_clause = f"{first_col_name} = %s"
        success, error = self.controller.delete_row(self.table_name, where_clause, [first_value])

        if success:
            QMessageBox.information(self, "Успех", "Запись успешно удалена")
            self.accept()
        else:
            QMessageBox.critical(self, "Ошибка", f"Не удалось удалить запись:\n{error}")


class SortFilterDialog(QDialog):
    """Диалог сортировки, группировки и фильтрации."""
    def __init__(self, controller, table_name, columns_info, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info

        self.where_clause = None
        self.order_clause = None
        self.group_clause = None
        self.having_clause = None

        self.setWindowTitle("Сортировка, группировка и фильтрация")
        self.setMinimumWidth(600)
        self.setup_ui()

    def setup_ui(self):
        """Настройка UI."""
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<h3>Сортировка, группировка и фильтрация</h3>"))

        # WHERE условие (фильтрация)
        filter_group = QGroupBox("Фильтрация (WHERE)")
        filter_layout = QVBoxLayout(filter_group)

        self.where_edit = QLineEdit()
        self.where_edit.setPlaceholderText("Например: id > 5 AND name LIKE '%test%'")
        filter_layout.addWidget(QLabel("Условие WHERE:"))
        filter_layout.addWidget(self.where_edit)

        layout.addWidget(filter_group)

        # ORDER BY (сортировка)
        sort_group = QGroupBox("Сортировка (ORDER BY)")
        sort_layout = QVBoxLayout(sort_group)

        self.order_edit = QLineEdit()
        self.order_edit.setPlaceholderText("Например: id DESC, name ASC")
        sort_layout.addWidget(QLabel("Условие ORDER BY:"))
        sort_layout.addWidget(self.order_edit)

        # Быстрая сортировка
        quick_sort_layout = QHBoxLayout()
        quick_sort_layout.addWidget(QLabel("Быстрая сортировка:"))

        self.quick_sort_column = QComboBox()
        self.quick_sort_column.addItems([col['name'] for col in self.columns_info])
        quick_sort_layout.addWidget(self.quick_sort_column)

        asc_btn = QPushButton("⬆ ASC")
        asc_btn.clicked.connect(lambda: self.quick_sort('ASC'))
        quick_sort_layout.addWidget(asc_btn)

        desc_btn = QPushButton("⬇ DESC")
        desc_btn.clicked.connect(lambda: self.quick_sort('DESC'))
        quick_sort_layout.addWidget(desc_btn)

        sort_layout.addLayout(quick_sort_layout)
        layout.addWidget(sort_group)

        # GROUP BY (группировка)
        group_group = QGroupBox("Группировка (GROUP BY)")
        group_layout = QVBoxLayout(group_group)

        self.group_edit = QLineEdit()
        self.group_edit.setPlaceholderText("Например: name")
        group_layout.addWidget(QLabel("Условие GROUP BY:"))
        group_layout.addWidget(self.group_edit)

        # Быстрая группировка с COUNT
        quick_group_layout = QHBoxLayout()
        quick_group_layout.addWidget(QLabel("Быстрая группировка с COUNT:"))

        self.quick_group_column = QComboBox()
        self.quick_group_column.addItems([col['name'] for col in self.columns_info])
        quick_group_layout.addWidget(self.quick_group_column)

        group_btn = QPushButton("📊 Группировать")
        group_btn.clicked.connect(self.quick_group)
        quick_group_layout.addWidget(group_btn)

        group_layout.addLayout(quick_group_layout)
        layout.addWidget(group_group)

        # HAVING (фильтрация групп)
        having_group = QGroupBox("Фильтрация групп (HAVING)")
        having_layout = QVBoxLayout(having_group)

        self.having_edit = QLineEdit()
        self.having_edit.setPlaceholderText("Например: COUNT(*) > 5")
        having_layout.addWidget(QLabel("Условие HAVING:"))
        having_layout.addWidget(self.having_edit)

        layout.addWidget(having_group)

        # Кнопки
        buttons_layout = QHBoxLayout()

        clear_btn = QPushButton("Очистить все")
        clear_btn.clicked.connect(self.clear_all)
        buttons_layout.addWidget(clear_btn)

        buttons_layout.addStretch()

        apply_btn = QPushButton("Применить")
        apply_btn.clicked.connect(self.apply_filters)
        buttons_layout.addWidget(apply_btn)

        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        layout.addLayout(buttons_layout)

    def quick_sort(self, direction):
        """Быстрая сортировка по выбранному столбцу."""
        column = self.quick_sort_column.currentText()
        self.order_edit.setText(f"{column} {direction}")

    def quick_group(self):
        """Быстрая группировка с COUNT."""
        column = self.quick_group_column.currentText()
        self.group_edit.setText(column)

    def clear_all(self):
        """Очистка всех полей."""
        self.where_edit.clear()
        self.order_edit.clear()
        self.group_edit.clear()
        self.having_edit.clear()

    def apply_filters(self):
        """Применение фильтров."""
        self.where_clause = self.where_edit.text().strip() or None
        self.order_clause = self.order_edit.text().strip() or None
        self.group_clause = self.group_edit.text().strip() or None
        self.having_clause = self.having_edit.text().strip() or None

        self.accept()


class DisplayDialog(QDialog):
    """Диалог вывода данных (выбор таблицы и переименование)."""
    def __init__(self, controller, current_table, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.current_table = current_table

        self.setWindowTitle("Вывод данных")
        self.setMinimumWidth(500)
        self.setup_ui()

    def setup_ui(self):
        """Настройка UI."""
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<h3>Управление таблицами</h3>"))

        # Выбор таблицы
        table_group = QGroupBox("Выбор таблицы")
        table_layout = QVBoxLayout(table_group)

        select_layout = QHBoxLayout()
        select_layout.addWidget(QLabel("Таблица:"))

        self.table_combo = QComboBox()
        tables = self.controller.get_all_tables()
        self.table_combo.addItems(tables)

        if self.current_table and self.current_table in tables:
            self.table_combo.setCurrentText(self.current_table)

        select_layout.addWidget(self.table_combo)
        table_layout.addLayout(select_layout)

        layout.addWidget(table_group)

        # Операции с таблицей
        operations_group = QGroupBox("Операции с таблицей")
        operations_layout = QVBoxLayout(operations_group)

        # Переименование таблицы
        rename_btn = QPushButton("⚙ Переименовать таблицу")
        rename_btn.clicked.connect(self.rename_table)
        operations_layout.addWidget(rename_btn)

        layout.addWidget(operations_group)

        layout.addStretch()

        # Кнопки
        buttons_layout = QHBoxLayout()

        select_btn = QPushButton("Выбрать таблицу")
        select_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(select_btn)

        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        layout.addLayout(buttons_layout)

    def rename_table(self):
        """Переименование таблицы."""
        old_name = self.table_combo.currentText()
        if not old_name:
            QMessageBox.warning(self, "Ошибка", "Выберите таблицу")
            return

        new_name, ok = QInputDialog.getText(
            self,
            "Переименование таблицы",
            f"Новое имя для таблицы '{old_name}':",
            text=old_name
        )

        if ok and new_name and new_name != old_name:
            success, error = self.controller.rename_table(old_name, new_name)
            if success:
                QMessageBox.information(self, "Успех", f"Таблица переименована: {old_name} → {new_name}")
                # Обновляем список таблиц
                tables = self.controller.get_all_tables()
                self.table_combo.clear()
                self.table_combo.addItems(tables)
                self.table_combo.setCurrentText(new_name)
                self.current_table = new_name
            else:
                QMessageBox.critical(self, "Ошибка", f"Не удалось переименовать таблицу:\n{error}")

