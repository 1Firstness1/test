"""
Модуль диалога для расширенной работы с таблицами БД.
Содержит класс TaskDialog с возможностями управления данными и структурой таблиц.
ИСПРАВЛЕНЫ БАГИ: #1, #2, #3, #4, #5, #6, #7, #8, #9, #10, #11, #12, #13
ИСПРАВЛЕНЫ НОВЫЕ БАГИ: JOIN columns, string functions case handling, transaction rollback, empty column sorting,
table disappearing on sort, column selection
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                              QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
                              QComboBox, QLineEdit, QMenu, QInputDialog, QCheckBox,
                              QSpinBox, QFormLayout, QTextEdit, QDialogButtonBox, QWidget,
                              QScrollArea, QRadioButton, QButtonGroup, QGroupBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from controller import NumericTableItem
from logger import Logger
import psycopg2
import re


class TaskDialog(QDialog):
    """
    Диалог для расширенной работы с таблицами БД.
    """
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.logger = Logger()

        self.current_table = None
        self.current_columns = []
        self.all_columns_info = []
        self.current_sort_order = {}
        self.join_tables = []
        self.join_conditions = []
        self.current_where = None
        self.current_order_by = None
        self.current_group_by = None
        self.current_having = None
        # Добавляем флаг режима соединения для правильной обработки заголовков
        self.is_join_mode = False
        # Словарь для сохранения оригинальных имен столбцов
        self.original_column_names = {}

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

        # Статус таблицы (над таблицей)
        self.status_label = QLabel("<b>Статус:</b> Таблица не выбрана")
        self.status_label.setStyleSheet("background-color: #e3f2fd; padding: 10px; border-radius: 4px;")
        layout.addWidget(self.status_label)

        # Таблица данных
        self.data_table = QTableWidget()
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.data_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.data_table.setSelectionBehavior(QTableWidget.SelectItems)
        self.data_table.setSelectionMode(QTableWidget.SingleSelection)
        self.data_table.verticalHeader().setVisible(False)

        # Обработка клика по заголовку столбца для сортировки
        self.data_table.horizontalHeader().sectionClicked.connect(self.on_column_header_clicked)

        # Обработка двойного клика по ячейке для группировки
        self.data_table.cellDoubleClicked.connect(self.on_cell_double_clicked)

        layout.addWidget(self.data_table)

        # Панель кнопок
        buttons_layout = QHBoxLayout()

        # Кнопка поиска
        self.search_btn = QPushButton("Поиск")
        self.search_btn.clicked.connect(self.show_search_dialog)
        buttons_layout.addWidget(self.search_btn)

        # Кнопка редактирования
        self.edit_btn = QPushButton("Редактировать")
        self.edit_btn.clicked.connect(self.show_edit_menu)
        buttons_layout.addWidget(self.edit_btn)

        # Кнопка добавления
        self.add_btn = QPushButton("Добавить")
        self.add_btn.clicked.connect(self.show_add_menu)
        buttons_layout.addWidget(self.add_btn)

        # Кнопка удаления
        self.delete_btn = QPushButton("Удалить")
        self.delete_btn.clicked.connect(self.show_delete_menu)
        buttons_layout.addWidget(self.delete_btn)

        buttons_layout.addStretch()

        # ✅ БАГ #2: Кнопка сброса фильтров
        self.reset_filters_btn = QPushButton("Сбросить фильтры")
        self.reset_filters_btn.clicked.connect(self.reset_all_filters)
        buttons_layout.addWidget(self.reset_filters_btn)

        # Кнопка вывода данных
        self.display_btn = QPushButton("Вывод")
        self.display_btn.clicked.connect(self.show_display_options)
        buttons_layout.addWidget(self.display_btn)

        # Кнопка закрытия
        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(close_btn)

        layout.addLayout(buttons_layout)

    def update_status(self):
        """Обновление статуса таблицы."""
        if self.current_table:
            join_info = f", {len(self.join_tables)} соединений" if self.join_tables else ""
            self.status_label.setText(f"<b>Статус:</b> Таблица: {self.current_table}{join_info}")
        else:
            self.status_label.setText("<b>Статус:</b> Таблица не выбрана")

    # ✅ БАГ #2: Новый метод для сброса фильтров
    def reset_all_filters(self):
        """Сброс всех фильтров и перезагрузка таблицы."""
        if not self.current_table:
            QMessageBox.warning(self, "Ошибка", "Таблица не выбрана")
            return

        self.current_sort_order = {}
        self.current_where = None
        self.current_order_by = None
        self.current_group_by = None
        self.current_having = None
        self.join_tables = []
        self.join_conditions = []
        # Сбросить флаг режима соединения
        self.is_join_mode = False
        self.original_column_names = {}

        self.load_table_data_filtered()
        self.update_status()
        QMessageBox.information(self, "Успех", "Все фильтры и соединения сброшены")
        self.logger.info(f"Фильтры сброшены для таблицы {self.current_table}")

    # ✅ БАГ #5: Предзаполнение данных из выбранной ячейки
    def on_cell_double_clicked(self, row, column):
        """Обработка двойного клика по ячейке для открытия диалога группировки."""
        if not self.current_table or column >= len(self.current_columns):
            return

        column_name = self.current_columns[column]
        # Получаем значение из ячейки для предзаполнения
        cell_value = self.data_table.item(row, column).text() if self.data_table.item(row, column) else ""

        # Определяем оригинальное имя столбца для JOIN таблиц
        orig_column_name = column_name
        if self.is_join_mode and column_name in self.original_column_names:
            orig_column_name = self.original_column_names[column_name]

        dialog = GroupFilterDialog(self.controller, self.current_table,
                                   self.all_columns_info, orig_column_name,
                                   cell_value, self.is_join_mode, self)
        if dialog.exec_():
            self.current_where = dialog.where_clause if dialog.where_clause else None
            self.current_order_by = dialog.order_clause if dialog.order_clause else None
            self.current_group_by = dialog.group_clause if dialog.group_clause else None
            self.current_having = dialog.having_clause if dialog.having_clause else None

            self.load_table_data_filtered(
                where=self.current_where,
                order_by=self.current_order_by,
                group_by=self.current_group_by,
                having=self.current_having
            )

    # ✅ БАГ #6: Исправлена сортировка для JOIN таблиц и пустых столбцов
    def on_column_header_clicked(self, logical_index):
        """Обработка клика по заголовку столбца для сортировки."""
        if not self.current_table or logical_index >= len(self.current_columns):
            return

        column_name = self.current_columns[logical_index]

        # Проверка на пустую таблицу
        if self.data_table.rowCount() == 0:
            QMessageBox.warning(self, "Ошибка", "Таблица пуста, сортировка невозможна")
            return

        # Проверка на пустые столбцы
        empty_column = True
        for row in range(self.data_table.rowCount()):
            item = self.data_table.item(row, logical_index)
            if item and item.text().strip():
                empty_column = False
                break

        if empty_column:
            QMessageBox.warning(self, "Ошибка", "Столбец не содержит данных для сортировки")
            return

        if column_name in self.current_sort_order:
            order = "DESC" if self.current_sort_order[column_name] == "ASC" else "ASC"
        else:
            order = "ASC"

        self.current_sort_order = {column_name: order}

        # ✅ БАГ: Правильная сортировка для JOIN таблиц
        if self.is_join_mode:
            # Находим оригинальное имя столбца для соединенной таблицы
            if column_name in self.original_column_names:
                orig_column_name = self.original_column_names[column_name]
                order_clause = f"{orig_column_name} {order}"
                # Обновляем конфигурацию JOIN для сортировки
                self.join_config['order_by'] = order_clause
                # Заново выполняем JOIN с новым порядком сортировки
                self.execute_join_display(self.join_config)
            else:
                QMessageBox.warning(self, "Ошибка сортировки", "Не удалось найти информацию о столбце для сортировки")
        else:
            # Стандартная сортировка для обычной таблицы
            order_clause = f"{column_name} {order}"
            self.load_table_data_filtered(
                where=self.current_where,
                order_by=order_clause,
                group_by=self.current_group_by,
                having=self.current_having
            )

        self.logger.info(f"Сортировка по {column_name} {order}")

    def show_search_dialog(self):
        """Показ диалога поиска."""
        if not self.current_table:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите таблицу через 'Вывод данных'")
            return

        dialog = SearchDialog(self.controller, self.current_table, self.all_columns_info, self)
        if dialog.exec_():
            # ✅ БАГ #5: Использовать параметризованный запрос
            self.current_where = dialog.search_condition
            self.load_table_data_filtered(
                where=dialog.search_condition,
                params=getattr(dialog, 'search_params', None)
            )

    def show_edit_menu(self):
        """Показ меню редактирования как отдельный диалог."""
        if not self.current_table:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите таблицу через 'Вывод данных'")
            return

        dialog = EditMenuDialog(self.controller, self.current_table, self.all_columns_info,
                               self.data_table, self)
        if dialog.exec_():
            # ✅ БАГ #3: Очистить кэш перед перезагрузкой
            self.current_columns = []
            self.all_columns_info = self.controller.get_table_columns(self.current_table)
            self.load_table_data_filtered(
                where=self.current_where,
                order_by=self.current_order_by,
                group_by=self.current_group_by,
                having=self.current_having
            )

    def show_add_menu(self):
        """Показ меню добавления как отдельный диалог."""
        if not self.current_table:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите таблицу через 'Вывод данных'")
            return

        dialog = AddMenuDialog(self.controller, self.current_table, self.all_columns_info, self)
        if dialog.exec_():
            # ✅ БАГ #3: Очистить кэш перед перезагрузкой
            self.current_columns = []
            self.all_columns_info = self.controller.get_table_columns(self.current_table)
            self.load_table_data_filtered(
                where=self.current_where,
                order_by=self.current_order_by,
                group_by=self.current_group_by,
                having=self.current_having
            )

    # ✅ БАГ #4: Предустановка столбца для удаления
    def show_delete_menu(self):
        """Показ меню удаления как отдельный диалог."""
        if not self.current_table:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите таблицу через 'Вывод данных'")
            return

        # Получение выбранного столбца
        selected_column = None
        selected_items = self.data_table.selectedItems()
        if selected_items:
            selected_col_idx = self.data_table.column(selected_items[0])
            if 0 <= selected_col_idx < len(self.current_columns):
                selected_column = self.current_columns[selected_col_idx]

        dialog = DeleteMenuDialog(self.controller, self.current_table, self.all_columns_info,
                                 self.data_table, selected_column, self)
        if dialog.exec_():
            # ✅ БАГ #3: Очистить кэш перед перезагрузкой
            self.current_columns = []
            self.all_columns_info = self.controller.get_table_columns(self.current_table)
            self.load_table_data_filtered(
                where=self.current_where,
                order_by=self.current_order_by,
                group_by=self.current_group_by,
                having=self.current_having
            )

    # ✅ БАГ #9: Полная очистка таблицы перед заполнением
    def load_table_data_filtered(self, columns=None, where=None, order_by=None, group_by=None, having=None, params=None):
        """Загрузка данных таблицы с фильтрацией."""
        if not self.current_table:
            return

        if columns:
            self.current_columns = columns
        else:
            self.current_columns = [col['name'] for col in self.all_columns_info]

        try:
            if self.is_join_mode:
                # Для JOIN используем сохраненные параметры
                results = self.controller.execute_join(
                    self.join_config['tables_info'],
                    self.join_config['selected_columns'],
                    self.join_config['join_conditions'],
                    where or self.join_config.get('where'),
                    order_by or self.join_config.get('order_by')
                )
                data = results
            else:
                data = self.controller.get_table_data(
                    self.current_table,
                    self.current_columns if columns else None,
                    where,
                    order_by,
                    group_by,
                    having,
                    params
                )

            # ✅ БАГ #9: Очистить таблицу перед заполнением для избежания утечек памяти
            self.data_table.clearSpans()
            self.data_table.setRowCount(0)

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

        except Exception as e:
            self.logger.error(f"Ошибка при загрузке данных: {str(e)}")
            QMessageBox.critical(self, "Ошибка загрузки", f"Не удалось загрузить данные: {str(e)}")

    def show_display_options(self):
        """Показ опций вывода данных с выбором таблицы."""
        # ✅ БАГ #1: Всегда получать свежие данные
        dialog = DisplayOptionsDialog(self.controller, self.current_table, self)
        if dialog.exec_():
            self.current_table = dialog.selected_table
            self.join_tables = dialog.join_tables
            self.join_conditions = dialog.join_conditions
            self.is_join_mode = dialog.is_join_mode
            self.update_status()

            if not self.current_table:
                return

            self.all_columns_info = self.controller.get_table_columns(self.current_table)
            self.current_columns = []
            self.current_where = None
            self.current_order_by = None
            self.current_group_by = None
            self.current_having = None
            self.original_column_names = {}

            if dialog.is_join_mode:
                self.join_config = dialog.join_config
                self.execute_join_display(dialog.join_config)
            else:
                self.current_columns = dialog.selected_columns if dialog.selected_columns else [col['name'] for col in self.all_columns_info]
                self.load_table_data_filtered(columns=self.current_columns)

    # ✅ БАГ #7: Улучшенная обработка ошибок и сохранение оригинальных имен столбцов
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

            if results:
                # Сохраняем соответствие отображаемых имен столбцов и оригинальных имен
                if 'column_mapping' in join_config:
                    self.original_column_names = join_config['column_mapping']
                else:
                    # Для обратной совместимости
                    self.original_column_names = {}
                    for i, display_name in enumerate(join_config['column_labels']):
                        if i < len(join_config['selected_columns']):
                            self.original_column_names[display_name] = join_config['selected_columns'][i]

                self.current_columns = join_config['column_labels']
                self.data_table.clearSpans()
                self.data_table.setRowCount(0)

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

        except psycopg2.Error as e:
            self.logger.error(f"Ошибка JOIN: {str(e)}")
            error_msg = str(e)
            if "column" in error_msg.lower():
                hint = "Проверьте, что все указанные столбцы существуют в таблицах"
            elif "table" in error_msg.lower():
                hint = "Проверьте, что таблицы существуют"
            else:
                hint = "Проверьте условия соединения"

            QMessageBox.critical(self, "Ошибка выполнения JOIN",
                                 f"Не удалось выполнить соединение:\n\n{hint}\n\n"
                                 f"Техническая информация:\n{error_msg}")

        except Exception as e:
            self.logger.error(f"Неожиданная ошибка JOIN: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Неожиданная ошибка: {str(e)}")

    def execute_join_with_sort(self, join_config):
        """Выполнение JOIN запроса с учетом сортировки."""
        # Сохраняем текущую конфигурацию для последующих операций
        self.join_config = join_config
        self.execute_join_display(join_config)


class EditMenuDialog(QDialog):
    """Диалог меню редактирования."""
    def __init__(self, controller, table_name, columns_info, data_table, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info
        self.data_table = data_table
        self.action_taken = False

        self.setWindowTitle("Редактировать")
        self.setMinimumWidth(400)
        self.setMinimumHeight(250)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        """Центрирование диалога на экране."""
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        """Настройка UI."""
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<h3>Выберите действие</h3>"))

        edit_column_btn = QPushButton("Редактировать столбец")
        edit_column_btn.setMinimumHeight(50)
        edit_column_btn.clicked.connect(self.edit_column)
        layout.addWidget(edit_column_btn)

        edit_record_btn = QPushButton("Редактировать запись")
        edit_record_btn.setMinimumHeight(50)
        edit_record_btn.clicked.connect(self.edit_record)
        layout.addWidget(edit_record_btn)

        layout.addStretch()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def edit_column(self):
        """Редактирование столбца."""
        selected_column = None
        selected_items = self.data_table.selectedItems()
        if selected_items:
            selected_col_idx = self.data_table.column(selected_items[0])
            column_name = self.data_table.horizontalHeaderItem(selected_col_idx).text()
            if column_name:
                selected_column = column_name

        dialog = EditColumnDialog(self.controller, self.table_name, self.columns_info, selected_column, self)
        if dialog.exec_():
            self.action_taken = True
            self.accept()

    # ✅ БАГ #6: Проверка на пустую таблицу
    def edit_record(self):
        """Редактирование записи."""
        if not self.data_table.rowCount():
            QMessageBox.warning(self, "Ошибка", "Таблица пуста, нечего редактировать")
            return

        selected_items = self.data_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Ошибка", "Выберите ячейку в записи для редактирования")
            return

        item = selected_items[0]
        row = item.row()

        if row < 0 or row >= self.data_table.rowCount():
            QMessageBox.warning(self, "Ошибка", "Неверная строка")
            return

        row_data = {}
        for col_idx in range(self.data_table.columnCount()):
            cell_item = self.data_table.item(row, col_idx)
            if cell_item:
                col_name = self.data_table.horizontalHeaderItem(col_idx).text()
                row_data[col_name] = cell_item.text()

        dialog = EditRecordDialog(self.controller, self.table_name, self.columns_info, row_data, self)
        if dialog.exec_():
            self.action_taken = True
            self.accept()

    def accept_dialog(self):
        """Принятие диалога."""
        self.accept()


class AddMenuDialog(QDialog):
    """Диалог меню добавления."""
    def __init__(self, controller, table_name, columns_info, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info
        self.action_taken = False

        self.setWindowTitle("Добавить")
        self.setMinimumWidth(400)
        self.setMinimumHeight(250)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        """Центрирование диалога на экране."""
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        """Настройка UI."""
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<h3>Выберите действие</h3>"))

        add_column_btn = QPushButton("Создать столбец")
        add_column_btn.setMinimumHeight(50)
        add_column_btn.clicked.connect(self.add_column)
        layout.addWidget(add_column_btn)

        add_record_btn = QPushButton("Создать запись")
        add_record_btn.setMinimumHeight(50)
        add_record_btn.clicked.connect(self.add_record)
        layout.addWidget(add_record_btn)

        layout.addStretch()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def add_column(self):
        """Добавление столбца."""
        dialog = AddColumnDialog(self.controller, self.table_name, self)
        if dialog.exec_():
            self.action_taken = True
            self.accept()

    def add_record(self):
        """Добавление записи."""
        dialog = AddRecordDialog(self.controller, self.table_name, self.columns_info, self)
        if dialog.exec_():
            self.action_taken = True
            self.accept()

    def accept_dialog(self):
        """Принятие диалога."""
        self.accept()


# ✅ БАГ #4: Предустановка столбца для удаления
class DeleteMenuDialog(QDialog):
    """Диалог меню удаления."""
    def __init__(self, controller, table_name, columns_info, data_table, selected_column=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info
        self.data_table = data_table
        self.selected_column = selected_column
        self.action_taken = False

        self.setWindowTitle("Удалить")
        self.setMinimumWidth(400)
        self.setMinimumHeight(250)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        """Центрирование диалога на экране."""
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        """Настройка UI."""
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<h3>Выберите действие</h3>"))

        delete_column_btn = QPushButton("Удалить столбец")
        delete_column_btn.setMinimumHeight(50)
        delete_column_btn.clicked.connect(self.delete_column)
        layout.addWidget(delete_column_btn)

        delete_record_btn = QPushButton("Удалить запись")
        delete_record_btn.setMinimumHeight(50)
        delete_record_btn.clicked.connect(self.delete_record)
        layout.addWidget(delete_record_btn)

        layout.addStretch()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ✅ БАГ #4: Передаем выбранный столбец в диалог удаления столбца
    def delete_column(self):
        """Удаление столбца."""
        dialog = DeleteColumnDialog(self.controller, self.table_name, self.columns_info,
                                   self.selected_column, self)
        if dialog.exec_():
            self.action_taken = True
            self.accept()

    # ✅ БАГ #6: Проверка на пустую таблицу
    def delete_record(self):
        """Удаление записи."""
        if not self.data_table.rowCount():
            QMessageBox.warning(self, "Ошибка", "Таблица пуста, нечего удалять")
            return

        selected_items = self.data_table.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "Ошибка", "Выберите ячейку в записи для удаления")
            return

        item = selected_items[0]
        row = item.row()

        if row < 0 or row >= self.data_table.rowCount():
            QMessageBox.warning(self, "Ошибка", "Неверная строка")
            return

        confirm = QMessageBox.question(
            self,
            "Подтверждение",
            "Вы уверены, что хотите удалить эту запись?",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm != QMessageBox.Yes:
            return

        if not self.data_table.columnCount():
            QMessageBox.warning(self, "Ошибка", "Нет данных для удаления")
            return

        first_col_item = self.data_table.horizontalHeaderItem(0)
        if not first_col_item:
            return
        first_col = first_col_item.text()
        first_value = self.data_table.item(row, 0).text()

        where_clause = f"{first_col} = %s"
        success, error = self.controller.delete_row(self.table_name, where_clause, [first_value])

        if success:
            QMessageBox.information(self, "Успех", "Запись успешно удалена")
            self.action_taken = True
            self.accept()
        else:
            QMessageBox.critical(self, "Ошибка", f"Не удалось удалить запись:\n{error}")

    def accept_dialog(self):
        """Принятие диалога."""
        self.accept()


class AddColumnDialog(QDialog):
    """Диалог добавления нового столбца."""
    def __init__(self, controller, table_name, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name

        self.setWindowTitle("Добавить столбец")
        self.setMinimumWidth(400)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        """Центрирование диалога на экране."""
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

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


# ✅ БАГ #4: Использование предвыбранного столбца
class EditColumnDialog(QDialog):
    """Диалог редактирования столбца."""
    def __init__(self, controller, table_name, columns_info, selected_column=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info
        self.selected_column = selected_column

        self.setWindowTitle("Редактировать столбец")
        self.setMinimumWidth(450)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        """Центрирование диалога на экране."""
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        """Настройка UI."""
        layout = QVBoxLayout(self)

        column_layout = QHBoxLayout()
        column_layout.addWidget(QLabel("Столбец:"))
        self.column_combo = QComboBox()
        self.column_combo.addItems([col['name'] for col in self.columns_info])

        # Если передан выбранный столбец, устанавливаем его
        if self.selected_column:
            index = self.column_combo.findText(self.selected_column)
            if index >= 0:
                self.column_combo.setCurrentIndex(index)

        column_layout.addWidget(self.column_combo)
        layout.addLayout(column_layout)

        operations_label = QLabel("<b>Выберите операцию:</b>")
        layout.addWidget(operations_label)

        rename_btn = QPushButton("Переименовать столбец")
        rename_btn.clicked.connect(self.rename_column)
        layout.addWidget(rename_btn)

        change_type_btn = QPushButton("Изменить тип данных")
        change_type_btn.clicked.connect(self.change_column_type)
        layout.addWidget(change_type_btn)

        set_constraint_btn = QPushButton("Установить ограничение")
        set_constraint_btn.clicked.connect(self.set_constraint)
        layout.addWidget(set_constraint_btn)

        drop_constraint_btn = QPushButton("Снять ограничение")
        drop_constraint_btn.clicked.connect(self.drop_constraint)
        layout.addWidget(drop_constraint_btn)

        layout.addStretch()

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


# ✅ БАГ #4: Использование предвыбранного столбца
class DeleteColumnDialog(QDialog):
    """Диалог для удаления столбца."""
    def __init__(self, controller, table_name, columns_info, selected_column=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info
        self.selected_column = selected_column

        self.setWindowTitle("Удалить столбец")
        self.setMinimumWidth(300)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        """Центрирование диалога на экране."""
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        """Настройка UI."""
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Выберите столбец для удаления:"))

        self.column_combo = QComboBox()
        self.column_combo.addItems([col['name'] for col in self.columns_info])

        # Если есть предвыбранный столбец, устанавливаем его
        if self.selected_column:
            index = self.column_combo.findText(self.selected_column)
            if index >= 0:
                self.column_combo.setCurrentIndex(index)

        layout.addWidget(self.column_combo)

        layout.addStretch()

        buttons_layout = QHBoxLayout()

        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        delete_btn = QPushButton("Удалить")
        delete_btn.setStyleSheet("background-color: #d32f2f; color: white;")
        delete_btn.clicked.connect(self.delete_column)
        buttons_layout.addWidget(delete_btn)

        layout.addLayout(buttons_layout)

    def delete_column(self):
        """Удаление выбранного столбца."""
        column = self.column_combo.currentText()

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


# ✅ БАГ #10: Улучшенная валидация NOT NULL
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
        self.center_on_screen()

    def center_on_screen(self):
        """Центрирование диалога на экране."""
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        """Настройка UI."""
        layout = QFormLayout(self)

        for col in self.columns_info:
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

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def accept_dialog(self):
        """Принятие диалога с валидацией."""
        data = {}
        errors = []

        for col in self.columns_info:
            col_name = col['name']
            widget = self.field_widgets.get(col_name)

            if not widget:
                continue

            value = widget.text().strip()

            # ✅ БАГ #10: Проверка NOT NULL
            if not value and not col.get('nullable', True):
                errors.append(f"Поле '{col_name}' обязательно для заполнения")

            if value:
                data[col_name] = value

        if errors:
            QMessageBox.warning(self, "Ошибка валидации", "\n".join(errors))
            return

        if not data:
            QMessageBox.warning(self, "Ошибка", "Заполните хотя бы одно поле")
            return

        success, error = self.controller.insert_row(self.table_name, data)

        if success:
            QMessageBox.information(self, "Успех", "Запись успешно добавлена")
            self.accept()
        else:
            QMessageBox.critical(self, "Ошибка", f"Не удалось добавить запись:\n{error}")


# ✅ БАГ #10: Улучшенная валидация NOT NULL
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
        self.center_on_screen()

    def center_on_screen(self):
        """Центрирование диалога на экране."""
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        """Настройка UI."""
        layout = QFormLayout(self)

        for col in self.columns_info:
            col_name = col['name']
            widget = QLineEdit()

            if col_name in self.current_data:
                widget.setText(str(self.current_data[col_name]))

            self.field_widgets[col_name] = widget

            if col_name == self.columns_info[0]['name']:
                widget.setReadOnly(True)
                widget.setStyleSheet("background-color: #f0f0f0;")

            layout.addRow(f"{col_name}:", widget)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def accept_dialog(self):
        """Принятие диалога с валидацией."""
        first_col = self.columns_info[0]['name']
        where_value = self.field_widgets[first_col].text()

        data = {}
        errors = []

        for col in self.columns_info:
            if col['name'] == first_col:
                continue

            col_name = col['name']
            widget = self.field_widgets[col_name]
            value = widget.text().strip()

            # ✅ БАГ #10: Проверка NOT NULL
            if not value and not col.get('nullable', True):
                errors.append(f"Поле '{col_name}' обязательно для заполнения")

            if value:
                data[col_name] = value

        if errors:
            QMessageBox.warning(self, "Ошибка валидации", "\n".join(errors))
            return

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


# ✅ БАГ #5: Предзаполнение значений для группировки
class GroupFilterDialog(QDialog):
    """Диалог группировки и фильтрации данных."""
    def __init__(self, controller, table_name, columns_info, selected_column, cell_value="", is_join_mode=False, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info
        self.selected_column = selected_column
        self.cell_value = cell_value
        self.is_join_mode = is_join_mode

        self.where_clause = None
        self.order_clause = None
        self.group_clause = None
        self.having_clause = None

        self.setWindowTitle(f"Группировка и фильтрация: {selected_column}")
        self.setMinimumWidth(500)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        """Центрирование диалога на экране."""
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        """Настройка UI."""
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"<h3>Группировка и фильтрация по столбцу: {self.selected_column}</h3>"))

        form_layout = QFormLayout()

        # Группа для фильтрации
        filter_group = QGroupBox("Фильтрация (WHERE)")
        filter_layout = QVBoxLayout(filter_group)

        where_layout = QHBoxLayout()
        where_layout.addWidget(QLabel("Столбец:"))
        self.where_column_edit = QLineEdit(self.selected_column)
        where_layout.addWidget(self.where_column_edit)

        self.where_operator_combo = QComboBox()
        self.where_operator_combo.addItems(["=", "!=", "<", "<=", ">", ">=", "LIKE", "IN", "IS NULL", "IS NOT NULL"])
        where_layout.addWidget(self.where_operator_combo)

        self.where_value_edit = QLineEdit()
        # Предзаполняем значение, если оно есть
        if self.cell_value:
            self.where_value_edit.setText(self.cell_value)
        where_layout.addWidget(self.where_value_edit)
        filter_layout.addLayout(where_layout)

        # Скрываем поле значения для операторов IS NULL/IS NOT NULL
        self.where_operator_combo.currentTextChanged.connect(self.update_where_ui)

        layout.addWidget(filter_group)

        # Группа для группировки
        group_group = QGroupBox("Группировка (GROUP BY)")
        group_layout = QVBoxLayout(group_group)

        self.group_check = QCheckBox(f"Группировать по столбцу: {self.selected_column}")
        group_layout.addWidget(self.group_check)

        having_layout = QHBoxLayout()
        having_layout.addWidget(QLabel("HAVING:"))
        self.having_function_combo = QComboBox()
        self.having_function_combo.addItems(["COUNT", "SUM", "AVG", "MIN", "MAX"])
        having_layout.addWidget(self.having_function_combo)

        having_layout.addWidget(QLabel("(*)"))

        self.having_operator_combo = QComboBox()
        self.having_operator_combo.addItems(["=", "!=", "<", "<=", ">", ">="])
        having_layout.addWidget(self.having_operator_combo)

        self.having_value_edit = QLineEdit()
        having_layout.addWidget(self.having_value_edit)

        group_layout.addLayout(having_layout)
        layout.addWidget(group_group)

        # Группа для сортировки
        sort_group = QGroupBox("Сортировка (ORDER BY)")
        sort_layout = QVBoxLayout(sort_group)

        self.order_check = QCheckBox(f"Сортировать по столбцу: {self.selected_column}")
        self.order_check.setChecked(True)
        sort_layout.addWidget(self.order_check)

        order_direction_layout = QHBoxLayout()
        self.order_asc_radio = QRadioButton("По возрастанию (ASC)")
        self.order_asc_radio.setChecked(True)
        order_direction_layout.addWidget(self.order_asc_radio)

        self.order_desc_radio = QRadioButton("По убыванию (DESC)")
        order_direction_layout.addWidget(self.order_desc_radio)

        sort_layout.addLayout(order_direction_layout)
        layout.addWidget(sort_group)

        layout.addStretch()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Инициализируем UI фильтрации
        self.update_where_ui(self.where_operator_combo.currentText())

    def update_where_ui(self, operator_text):
        """Обновление UI фильтрации в зависимости от оператора."""
        if operator_text in ["IS NULL", "IS NOT NULL"]:
            self.where_value_edit.setVisible(False)
        else:
            self.where_value_edit.setVisible(True)

    def accept_dialog(self):
        """Принятие настроек."""
        # Сформировать WHERE
        if self.where_operator_combo.currentText() in ["IS NULL", "IS NOT NULL"]:
            self.where_clause = f"{self.where_column_edit.text()} {self.where_operator_combo.currentText()}"
        else:
            if self.where_value_edit.text().strip():
                op = self.where_operator_combo.currentText()
                if op == "LIKE":
                    value = f"'%{self.where_value_edit.text()}%'"
                elif op == "IN":
                    # Предполагаем, что значения разделены запятыми
                    values = [f"'{v.strip()}'" for v in self.where_value_edit.text().split(",")]
                    value = f"({', '.join(values)})"
                else:
                    # Для числовых значений не используем кавычки
                    try:
                        float(self.where_value_edit.text())
                        value = self.where_value_edit.text()
                    except ValueError:
                        value = f"'{self.where_value_edit.text()}'"
                self.where_clause = f"{self.where_column_edit.text()} {op} {value}"
            else:
                self.where_clause = None

        # Сформировать GROUP BY
        if self.group_check.isChecked():
            self.group_clause = self.selected_column

            # Сформировать HAVING
            if self.having_value_edit.text().strip():
                func = self.having_function_combo.currentText()
                op = self.having_operator_combo.currentText()
                value = self.having_value_edit.text()
                self.having_clause = f"{func}(*) {op} {value}"
            else:
                self.having_clause = None
        else:
            self.group_clause = None
            self.having_clause = None

        # Сформировать ORDER BY
        if self.order_check.isChecked():
            direction = "DESC" if self.order_desc_radio.isChecked() else "ASC"
            self.order_clause = f"{self.selected_column} {direction}"
        else:
            self.order_clause = None

        self.accept()


# ✅ БАГ #5: Параметризованный SearchDialog
class SearchDialog(QDialog):
    """Диалог поиска по таблице с защитой от SQL Injection."""

    def __init__(self, controller, table_name, columns_info, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info
        self.search_condition = None
        self.search_params = []

        self.setWindowTitle("Поиск")
        self.setMinimumWidth(500)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        """Центрирование диалога на экране."""
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        """Настройка UI."""
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<h3>Поиск по таблице</h3>"))

        form_layout = QFormLayout()

        self.column_combo = QComboBox()
        self.column_combo.addItems([col['name'] for col in self.columns_info])
        form_layout.addRow("Столбец:", self.column_combo)

        self.search_type_combo = QComboBox()
        self.search_type_combo.addItems([
            "LIKE (шаблонный поиск)",
            "~ (регулярка)",
            "~* (регулярка без учета регистра)",
            "!~ (не соответствует)",
            "!~* (не соответствует без учета регистра)",
            "= (точное совпадение)"
        ])
        form_layout.addRow("Тип поиска:", self.search_type_combo)

        self.search_text = QLineEdit()
        self.search_text.setPlaceholderText("Введите текст для поиска...")
        form_layout.addRow("Текст:", self.search_text)

        layout.addLayout(form_layout)

        hint_label = QLabel(
            "<i><b>Подсказка:</b><br>"
            "• LIKE: используйте % как подстановочный символ (пример: %текст%)<br>"
            "• ~: POSIX регулярное выражение<br>"
            "• ~*: POSIX регулярное выражение без учета регистра</i>"
        )
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept_dialog(self):
        """Формирование условия поиска с защитой от SQL Injection."""
        column = self.column_combo.currentText()
        search_text = self.search_text.text().strip()

        if not search_text:
            QMessageBox.warning(self, "Ошибка", "Введите текст для поиска")
            return

        search_type = self.search_type_combo.currentText()

        # ✅ БАГ #5: Использовать параметризованные запросы
        if "LIKE" in search_type:
            self.search_condition = f"{column} LIKE %s"
            self.search_params = [f"%{search_text}%"]
        elif "~*" in search_type and "!" in search_type:
            self.search_condition = f"{column} !~* %s"
            self.search_params = [search_text]
        elif "~*" in search_type:
            self.search_condition = f"{column} ~* %s"
            self.search_params = [search_text]
        elif "!~" in search_type:
            self.search_condition = f"{column} !~ %s"
            self.search_params = [search_text]
        elif "~" in search_type:
            self.search_condition = f"{column} ~ %s"
            self.search_params = [search_text]
        else:
            self.search_condition = f"{column} = %s"
            self.search_params = [search_text]

        self.accept()


class DisplayOptionsDialog(QDialog):
    """Диалог опций вывода данных."""

    def __init__(self, controller, current_table=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.current_table = current_table

        self.selected_table = current_table
        self.selected_columns = None
        self.is_join_mode = False
        self.join_config = None
        self.join_tables = []
        self.join_conditions = []

        self.setWindowTitle("Вывод данных")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        """Центрирование диалога на экране."""
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        """Настройка UI."""
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<h3>Вывод данных</h3>"))

        select_table_btn = QPushButton("Выбрать таблицу")
        select_table_btn.setMinimumHeight(50)
        select_table_btn.clicked.connect(self.select_table)
        layout.addWidget(select_table_btn)

        add_join_btn = QPushButton("Добавить соединения (JOIN)")
        add_join_btn.setMinimumHeight(50)
        add_join_btn.clicked.connect(self.add_join)
        layout.addWidget(add_join_btn)

        string_func_btn = QPushButton("Строковые функции")
        string_func_btn.setMinimumHeight(50)
        string_func_btn.clicked.connect(self.apply_string_functions)
        layout.addWidget(string_func_btn)

        layout.addStretch()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def select_table(self):
        """Выбор основной таблицы."""
        dialog = SelectTableDialog(self.controller, self.selected_table, self)
        if dialog.exec_():
            self.selected_table = dialog.selected_table
            self.selected_columns = dialog.selected_columns
            self.is_join_mode = False
            self.join_tables = []
            self.join_conditions = []

    def add_join(self):
        """Добавление соединений."""
        if not self.selected_table:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите основную таблицу")
            return

        dialog = JoinWizardDialog(self.controller, self.selected_table, self)
        if dialog.exec_():
            self.is_join_mode = True
            self.join_config = dialog.get_join_config()
            self.join_tables.append(self.join_config['join_conditions'][0]['table'])
            self.join_conditions.append(self.join_config['join_conditions'][0])

    def apply_string_functions(self):
        """Применение строковых функций."""
        if not self.selected_table:
            QMessageBox.warning(self, "Ошибка", "Сначала выберите таблицу")
            return

        columns_info = self.controller.get_table_columns(self.selected_table)
        dialog = StringFunctionsDialog(self.controller, self.selected_table, columns_info, self)
        dialog.exec_()

    def accept_dialog(self):
        """Принятие настроек."""
        if not self.selected_table:
            QMessageBox.warning(self, "Ошибка", "Выберите таблицу для вывода")
            return

        self.accept()


# ✅ БАГ #1: Всегда получать свежие данные при открытии
class SelectTableDialog(QDialog):
    """Диалог выбора таблицы с отображением и выбором столбцов."""

    def __init__(self, controller, current_table=None, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.selected_table = current_table
        self.selected_columns = None
        self.scroll_area = None

        self.setWindowTitle("Выбрать таблицу")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        """Центрирование диалога на экране."""
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        """Настройка UI."""
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<h3>Выберите таблицу</h3>"))

        table_layout = QHBoxLayout()
        table_layout.addWidget(QLabel("Таблица:"))

        self.table_combo = QComboBox()
        tables = self.controller.get_all_tables()
        self.table_combo.addItems(tables)

        if self.selected_table and self.selected_table in tables:
            self.table_combo.setCurrentText(self.selected_table)

        self.table_combo.currentTextChanged.connect(self.on_table_changed)
        table_layout.addWidget(self.table_combo)

        rename_btn = QPushButton("⚙ Переименовать")
        rename_btn.setMaximumWidth(120)
        rename_btn.clicked.connect(self.rename_table)
        table_layout.addWidget(rename_btn)

        layout.addLayout(table_layout)

        layout.addWidget(QLabel("<b>Выберите столбцы:</b>"))

        self.columns_checks = {}
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # ✅ БАГ #1: Всегда получать свежие данные
        current_columns = self.controller.get_table_columns(self.table_combo.currentText())

        for col in current_columns:
            check = QCheckBox(f"{col['name']} ({col['type']})")
            check.setChecked(True)
            self.columns_checks[col['name']] = check
            scroll_layout.addWidget(check)

        scroll_layout.addStretch()
        self.scroll_area.setWidget(scroll_widget)
        layout.addWidget(self.scroll_area)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept_dialog)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def on_table_changed(self, table_name):
        """Обработка изменения таблицы."""
        if table_name:
            columns = self.controller.get_table_columns(table_name)
            self.columns_checks.clear()

            # ✅ БАГ #4: Использовать сохранённую ссылку на scroll_area
            if self.scroll_area:
                scroll_widget = QWidget()
                scroll_layout = QVBoxLayout(scroll_widget)

                for col in columns:
                    check = QCheckBox(f"{col['name']} ({col['type']})")
                    check.setChecked(True)
                    self.columns_checks[col['name']] = check
                    scroll_layout.addWidget(check)

                scroll_layout.addStretch()
                self.scroll_area.setWidget(scroll_widget)

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
                current_index = self.table_combo.currentIndex()
                self.table_combo.setItemText(current_index, new_name)
            else:
                QMessageBox.critical(self, "Ошибка", f"Не удалось переименовать таблицу:\n{error}")

    def accept_dialog(self):
        """Принятие настроек."""
        self.selected_table = self.table_combo.currentText()
        selected = [name for name, check in self.columns_checks.items() if check.isChecked()]
        self.selected_columns = selected if selected else None

        self.accept()


# ✅ БАГ #1: Исправлен JoinWizardDialog для отображения столбцов из всех таблиц
class JoinWizardDialog(QDialog):
    """Мастер создания JOIN запросов."""

    def __init__(self, controller, base_table, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.base_table = base_table
        self.scroll_area = None
        self.join_columns_checks = {}
        self.base_columns_checks = {}

        self.setWindowTitle("Мастер соединений (JOIN)")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        """Центрирование диалога на экране."""
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        """Настройка UI."""
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(f"<h3>Создание JOIN запроса</h3>"))
        layout.addWidget(QLabel(f"<b>Базовая таблица:</b> {self.base_table}"))

        layout.addWidget(QLabel("<b>Выберите таблицу для соединения:</b>"))

        join_table_layout = QHBoxLayout()
        join_table_layout.addWidget(QLabel("Таблица:"))

        self.join_table_combo = QComboBox()
        all_tables = self.controller.get_all_tables()
        other_tables = [t for t in all_tables if t != self.base_table]
        self.join_table_combo.addItems(other_tables)
        self.join_table_combo.currentTextChanged.connect(self.update_join_columns)
        join_table_layout.addWidget(self.join_table_combo)

        layout.addLayout(join_table_layout)

        join_type_layout = QHBoxLayout()
        join_type_layout.addWidget(QLabel("Тип соединения:"))

        self.join_type_combo = QComboBox()
        self.join_type_combo.addItems(["INNER", "LEFT", "RIGHT", "FULL"])
        join_type_layout.addWidget(self.join_type_combo)

        layout.addLayout(join_type_layout)

        layout.addWidget(QLabel("<b>Условие соединения (ON):</b>"))

        on_layout = QHBoxLayout()

        self.base_column_combo = QComboBox()
        self.update_base_columns()
        on_layout.addWidget(QLabel(f"{self.base_table}."))
        on_layout.addWidget(self.base_column_combo)

        on_layout.addWidget(QLabel(" = "))

        self.join_column_combo = QComboBox()
        on_layout.addWidget(QLabel(""))
        self.join_table_label = QLabel()
        on_layout.addWidget(self.join_table_label)
        on_layout.addWidget(QLabel("."))
        on_layout.addWidget(self.join_column_combo)

        layout.addLayout(on_layout)

        # ✅ БАГ #1: Добавляем группы для выбора столбцов обеих таблиц
        layout.addWidget(QLabel("<b>Выберите столбцы для вывода:</b>"))

        columns_layout = QHBoxLayout()

        # Столбцы базовой таблицы
        base_group = QGroupBox(f"Столбцы таблицы {self.base_table}")
        base_layout = QVBoxLayout(base_group)
        base_scroll = QScrollArea()
        base_scroll.setWidgetResizable(True)
        base_scroll_widget = QWidget()
        base_scroll_layout = QVBoxLayout(base_scroll_widget)

        base_columns = self.controller.get_table_columns(self.base_table)
        for col in base_columns:
            check = QCheckBox(f"{col['name']}")
            check.setChecked(True)
            self.base_columns_checks[col['name']] = check
            base_scroll_layout.addWidget(check)

        base_scroll_layout.addStretch()
        base_scroll.setWidget(base_scroll_widget)
        base_layout.addWidget(base_scroll)
        columns_layout.addWidget(base_group)

        # Столбцы присоединяемой таблицы
        join_group = QGroupBox(f"Столбцы присоединяемой таблицы")
        join_layout = QVBoxLayout(join_group)
        self.join_scroll = QScrollArea()
        self.join_scroll.setWidgetResizable(True)
        self.update_join_columns(self.join_table_combo.currentText())
        join_layout.addWidget(self.join_scroll)
        columns_layout.addWidget(join_group)

        layout.addLayout(columns_layout)

        layout.addWidget(QLabel("<b>WHERE (опционально):</b>"))
        self.where_edit = QLineEdit()
        layout.addWidget(self.where_edit)

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

        # Обновляем список столбцов для выбора
        join_scroll_widget = QWidget()
        join_scroll_layout = QVBoxLayout(join_scroll_widget)
        self.join_columns_checks = {}

        for col in columns:
            check = QCheckBox(f"{col['name']}")
            check.setChecked(True)
            self.join_columns_checks[col['name']] = check
            join_scroll_layout.addWidget(check)

        join_scroll_layout.addStretch()
        self.join_scroll.setWidget(join_scroll_widget)

    def get_join_config(self):
        """Получение конфигурации JOIN."""
        join_table = self.join_table_combo.currentText()
        join_type = self.join_type_combo.currentText()

        base_col = self.base_column_combo.currentText()
        join_col = self.join_column_combo.currentText()

        on_condition = f"{self.base_table}.{base_col} = {join_table}.{join_col}"

        # Формируем выбранные столбцы из обеих таблиц
        selected_columns = []
        column_labels = []
        column_mapping = {}  # Для связи отображаемых имен и оригинальных имен столбцов

        # Столбцы из базовой таблицы
        for col_name, check in self.base_columns_checks.items():
            if check.isChecked():
                full_column_name = f"{self.base_table}.{col_name}"
                display_name = f"{self.base_table}_{col_name}"
                selected_columns.append(full_column_name)
                column_labels.append(display_name)
                column_mapping[display_name] = full_column_name

        # Столбцы из присоединяемой таблицы
        for col_name, check in self.join_columns_checks.items():
            if check.isChecked():
                full_column_name = f"{join_table}.{col_name}"
                display_name = f"{join_table}_{col_name}"
                selected_columns.append(full_column_name)
                column_labels.append(display_name)
                column_mapping[display_name] = full_column_name

        # Если ничего не выбрано, добавляем все столбцы
        if not selected_columns:
            selected_columns = [f"{self.base_table}.*", f"{join_table}.*"]
            base_columns = [col['name'] for col in self.controller.get_table_columns(self.base_table)]
            join_columns = [col['name'] for col in self.controller.get_table_columns(join_table)]

            column_labels = []
            for col in base_columns:
                display_name = f"{self.base_table}_{col}"
                column_labels.append(display_name)
                column_mapping[display_name] = f"{self.base_table}.{col}"

            for col in join_columns:
                display_name = f"{join_table}_{col}"
                column_labels.append(display_name)
                column_mapping[display_name] = f"{join_table}.{col}"

        return {
            'tables_info': [
                {'name': self.base_table, 'alias': None}
            ],
            'selected_columns': selected_columns,
            'column_labels': column_labels,
            'column_mapping': column_mapping,  # Сохраняем маппинг для использования при сортировке
            'join_conditions': [
                {
                    'type': join_type,
                    'table': join_table,
                    'alias': None,
                    'on': on_condition
                }
            ],
            'where': self.where_edit.text().strip() or None,
            'order_by': None
        }


# ✅ БАГ #3: Исправлена StringFunctionsDialog с возможностью применять функции к таблице
class StringFunctionsDialog(QDialog):
    """Диалог работы со строковыми функциями."""

    def __init__(self, controller, table_name, columns_info, parent=None, selected_column=None):
        super().__init__(parent)
        self.controller = controller
        self.table_name = table_name
        self.columns_info = columns_info
        self.selected_column = selected_column
        self.logger = Logger()

        self.setWindowTitle("Строковые функции")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self.setup_ui()
        self.center_on_screen()

    def center_on_screen(self):
        """Центрирование диалога на экране."""
        screen = self.screen().geometry()
        self.move(screen.center() - self.rect().center())

    def setup_ui(self):
        """Настройка UI."""
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("<h3>Применение строковых функций</h3>"))

        form_layout = QFormLayout()

        self.column_combo = QComboBox()
        string_columns = [col['name'] for col in self.columns_info
                          if 'char' in col.get('type', '').lower() or 'text' in col.get('type', '').lower()]
        if not string_columns:
            string_columns = [col['name'] for col in self.columns_info]
        self.column_combo.addItems(string_columns)

        if self.selected_column and self.selected_column in string_columns:
            self.column_combo.setCurrentText(self.selected_column)

        form_layout.addRow("Столбец:", self.column_combo)

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
            "LENGTH (длина строки)",
            "INITCAP (первый символ в верхнем регистре)"
        ])
        self.function_combo.currentTextChanged.connect(self.on_function_changed)
        form_layout.addRow("Функция:", self.function_combo)

        layout.addLayout(form_layout)

        self.params_widget = QWidget()
        self.params_layout = QFormLayout(self.params_widget)
        layout.addWidget(self.params_widget)

        layout.addWidget(QLabel("<b>Результат:</b>"))
        self.result_table = QTableWidget()
        self.result_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.result_table)

        buttons_layout = QHBoxLayout()

        apply_btn = QPushButton("Применить функцию")
        apply_btn.clicked.connect(self.apply_function)
        buttons_layout.addWidget(apply_btn)

        # ✅ БАГ #3: Добавляем кнопку для создания нового столбца с примененной функцией
        self.create_column_btn = QPushButton("Создать столбец с результатом")
        self.create_column_btn.clicked.connect(self.create_column_with_function)
        self.create_column_btn.setEnabled(False)  # Активируем после применения функции
        buttons_layout.addWidget(self.create_column_btn)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(close_btn)

        layout.addLayout(buttons_layout)

        self.on_function_changed(self.function_combo.currentText())

    def on_function_changed(self, function_text):
        """Обработка изменения выбранной функции."""
        while self.params_layout.rowCount() > 0:
            self.params_layout.removeRow(0)

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

        # Сохраняем текущую функцию и параметры для использования при создании столбца
        self.current_function = function_text

    def get_sql_expression(self):
        """Формирование SQL выражения для текущей функции с поддержкой кириллицы."""
        column = self.column_combo.currentText()
        function = self.function_combo.currentText()

        try:
            if "UPPER" in function:
                # Используем специальный вызов для корректной работы с кириллицей
                sql_expr = f"upper({column})"
            elif "LOWER" in function:
                # Используем простую функцию нижнего регистра
                sql_expr = f"lower({column})"
            elif "INITCAP" in function:
                # Используем простую инициализацию заглавных букв
                sql_expr = f"initcap({column})"
            elif "SUBSTRING" in function:
                start = self.start_pos.value()
                length = self.length.value()
                sql_expr = f"substring({column}, {start}, {length})"
            elif "LTRIM" in function:
                sql_expr = f"ltrim({column})"
            elif "RTRIM" in function:
                sql_expr = f"rtrim({column})"
            elif "TRIM" in function:
                sql_expr = f"trim({column})"
            elif "LPAD" in function:
                length = self.pad_length.value()
                char = self.pad_char.text() or ' '
                char_escaped = char.replace("'", "''")
                sql_expr = f"lpad({column}, {length}, '{char_escaped}')"
            elif "RPAD" in function:
                length = self.pad_length.value()
                char = self.pad_char.text() or ' '
                char_escaped = char.replace("'", "''")
                sql_expr = f"rpad({column}, {length}, '{char_escaped}')"
            elif "CONCAT" in function:
                text = self.concat_text.text()
                text_escaped = text.replace("'", "''")
                if self.concat_position.currentText() == "В начале":
                    # Использовать функцию concat вместо оператора || для лучшей совместимости
                    sql_expr = f"concat('{text_escaped}', {column})"
                else:
                    sql_expr = f"concat({column}, '{text_escaped}')"
            elif "LENGTH" in function:
                # Используем length для корректной работы с кириллицей
                sql_expr = f"length({column})"
            else:
                raise ValueError("Неизвестная функция")

            return sql_expr, column
        except Exception as e:
            self.logger.error(f"Ошибка формирования SQL выражения: {str(e)}")
            return None, None

    def apply_function(self):
        """Применение выбранной функции."""
        try:
            sql_expr, column = self.get_sql_expression()
            if not sql_expr:
                QMessageBox.warning(self, "Ошибка", "Не удалось сформировать SQL выражение")
                return

            query = f"SELECT {column} as original, {sql_expr} as result FROM {self.table_name} LIMIT 20"
            results = self.controller.execute_select(query)

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
                self.logger.info(f"Функция {self.function_combo.currentText()} применена успешно")

                # Разрешаем создание столбца после успешного применения функции
                self.create_column_btn.setEnabled(True)
            else:
                QMessageBox.information(self, "Результат", "Нет данных для отображения")

        except Exception as e:
            self.logger.error(f"Ошибка применения функции: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка при применении функции:\n{str(e)}")

    def create_column_with_function(self):
        """Создание нового столбца с результатом применения функции."""
        try:
            sql_expr, orig_column = self.get_sql_expression()
            if not sql_expr:
                QMessageBox.warning(self, "Ошибка", "Не удалось сформировать SQL выражение")
                return

            # Запрашиваем имя для нового столбца
            function_name = self.current_function.split(" ")[0].lower()
            suggested_name = f"{function_name}_{orig_column}"

            new_column_name, ok = QInputDialog.getText(
                self, "Имя нового столбца",
                "Введите имя для нового столбца:",
                text=suggested_name
            )

            if not ok or not new_column_name:
                return

            # Определяем тип данных для нового столбца
            data_type = "TEXT"  # По умолчанию используем TEXT
            if "LENGTH" in self.current_function:
                data_type = "INTEGER"

            # Сначала добавляем столбец
            success, error = self.controller.add_column(
                self.table_name, new_column_name, data_type
            )

            if not success:
                QMessageBox.critical(self, "Ошибка", f"Не удалось добавить столбец:\n{error}")
                return

            # Затем обновляем его значениями из функции
            update_query = f"UPDATE {self.table_name} SET {new_column_name} = {sql_expr}"
            try:
                # Установить правильную кодировку клиента перед выполнением запроса
                self.controller.execute_select("SET CLIENT_ENCODING TO 'UTF8'")
                # Выполнить запрос обновления
                self.controller.execute_select(update_query)
                QMessageBox.information(
                    self, "Успех",
                    f"Столбец '{new_column_name}' успешно создан и заполнен результатами функции."
                )
                self.logger.info(f"Создан столбец '{new_column_name}' с функцией {self.current_function}")
            except Exception as e:
                # В случае ошибки при обновлении пытаемся удалить столбец
                self.controller.drop_column(self.table_name, new_column_name)
                QMessageBox.critical(self, "Ошибка", f"Ошибка при заполнении столбца:\n{str(e)}")
                self.logger.error(f"Ошибка при заполнении столбца '{new_column_name}': {str(e)}")

        except Exception as e:
            self.logger.error(f"Ошибка создания столбца: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка при создании столбца:\n{str(e)}")

        except Exception as e:
            self.logger.error(f"Ошибка создания столбца: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Ошибка при создании столбца:\n{str(e)}")
