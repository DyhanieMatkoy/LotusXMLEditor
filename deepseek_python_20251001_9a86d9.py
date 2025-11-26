import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

class NewspaperItemWidget(QWidget):
    def __init__(self, title, items, parent=None):
        super().__init__(parent)
        self.title = title
        self.items = items
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        # Заголовок категории
        title_label = QLabel(self.title)
        title_label.setStyleSheet("""
            QLabel {
                font-weight: bold;
                font-size: 14px;
                color: #2c3e50;
                padding: 5px;
                border-bottom: 2px solid #3498db;
                background: #f8f9fa;
                border-radius: 4px;
            }
        """)
        layout.addWidget(title_label)
        
        # Элементы категории
        for item in self.items:
            item_widget = QPushButton(item)
            item_widget.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 8px;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    background: white;
                }
                QPushButton:hover {
                    background: #e3f2fd;
                    border-color: #2196f3;
                }
            """)
            item_widget.setCursor(Qt.PointingHandCursor)
            item_widget.clicked.connect(lambda checked, i=item: self.on_item_clicked(i))
            layout.addWidget(item_widget)
        
        # Растягивающий элемент для выравнивания
        layout.addStretch()

    def on_item_clicked(self, item):
        print(f"Clicked: {self.title} -> {item}")

class NewspaperTreeWidget(QScrollArea):
    def __init__(self):
        super().__init__()
        self.setup_ui()
        self.load_sample_data()
        
    def setup_ui(self):
        self.setWidgetResizable(True)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Главный контейнер
        self.main_widget = QWidget()
        self.setWidget(self.main_widget)
        
        # Layout для колонок
        self.columns_layout = QHBoxLayout(self.main_widget)
        self.columns_layout.setSpacing(20)
        self.columns_layout.setContentsMargins(15, 15, 15, 15)
        
        # Создаем колонки
        self.columns = []
        self.create_columns(3)  # Начальное количество колонок
        
    def create_columns(self, num_columns):
        # Очищаем старые колонки
        for column in self.columns:
            column.setParent(None)
        self.columns.clear()
        
        # Создаем новые колонки
        for i in range(num_columns):
            column_widget = QWidget()
            column_layout = QVBoxLayout(column_widget)
            column_layout.setSpacing(15)
            column_layout.setContentsMargins(0, 0, 0, 0)
            column_layout.addStretch()  # Добавляем растягивающий элемент внизу
            
            self.columns.append(column_layout)
            self.columns_layout.addWidget(column_widget)
    
    def load_sample_data(self):
        # Создаем тестовые данные
        categories = {
            "Разработка проектов": [
                "Веб-сайт компании", "Мобильное приложение", 
                "Внутренний портал", "API сервис", "Админ панель",
                "База данных", "Микросервисы", "Кэширование"
            ],
            "Задачи и этапы": [
                "Дизайн интерфейса", "Разработка API", "Тестирование", 
                "Документация", "Ревью кода", "Деплой", "Мониторинг",
                "Оптимизация", "Резервное копирование"
            ],
            "Команда разработки": [
                "Фронтенд разработчики", "Бэкенд разработчики", 
                "Дизайнеры", "Менеджеры", "Тестировщики", "DevOps",
                "Архитекторы", "Техлиды"
            ],
            "Технологии и инструменты": [
                "Python", "JavaScript", "React", "Django", "PostgreSQL",
                "Docker", "Git", "CI/CD", "Kubernetes", "AWS"
            ],
            "Управление проектами": [
                "Agile методология", "Scrum доски", "Спринт планирование",
                "KPI метрики", "Бюджетирование", "Риск менеджмент"
            ],
            "Документация": [
                "Технические требования", "API документация", 
                "Пользовательские руководства", "Архитектурные схемы",
                "Регламенты работы"
            ],
            "Календарь и сроки": [
                "Спринт 1: Исследование", "Спринт 2: Прототип", 
                "Спринт 3: Разработка", "Спринт 4: Тестирование",
                "Релизная кандидатура", "Продакшен релиз"
            ],
            "Ресурсы и инфраструктура": [
                "Серверы и хостинг", "Базы данных", "CDN сети",
                "Системы мониторинга", "Логирование", "Безопасность"
            ]
        }
        
        self.distribute_items(categories)
    
    def distribute_items(self, categories):
        """Распределяет элементы по колонкам с балансировкой высоты"""
        
        # Создаем виджеты для всех категорий
        category_widgets = []
        for title, items in categories.items():
            widget = NewspaperItemWidget(title, items)
            category_widgets.append(widget)
        
        # Сортируем по убыванию высоты (приблизительно по количеству элементов)
        category_widgets.sort(key=lambda w: len(w.items), reverse=True)
        
        # Распределяем по колонкам (алгоритм балансировки)
        column_heights = [0] * len(self.columns)
        
        for widget in category_widgets:
            # Находим колонку с минимальной текущей высотой
            min_height_index = column_heights.index(min(column_heights))
            
            # Вставляем виджет перед растягивающим элементом
            self.columns[min_height_index].insertWidget(
                self.columns[min_height_index].count() - 1, 
                widget
            )
            
            # Обновляем высоту колонки (приблизительно)
            column_heights[min_height_index] += len(widget.items) + 1
    
    def update_columns_count(self, count):
        """Обновляет количество колонок"""
        self.create_columns(count)
        self.load_sample_data()  # Перераспределяем элементы

class ControlPanel(QWidget):
    def __init__(self, newspaper_widget):
        super().__init__()
        self.newspaper_widget = newspaper_widget
        self.setup_ui()
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        
        # Выбор количества колонок
        layout.addWidget(QLabel("Количество колонок:"))
        self.columns_spin = QSpinBox()
        self.columns_spin.setRange(1, 6)
        self.columns_spin.setValue(3)
        self.columns_spin.valueChanged.connect(self.newspaper_widget.update_columns_count)
        layout.addWidget(self.columns_spin)
        
        layout.addStretch()
        
        # Кнопка обновления
        refresh_btn = QPushButton("Обновить распределение")
        refresh_btn.clicked.connect(self.newspaper_widget.load_sample_data)
        layout.addWidget(refresh_btn)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Настоящая газетная верстка с многоколоночным QGridLayout")
        self.setGeometry(100, 100, 1400, 800)
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Основной layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Панель управления
        self.newspaper_widget = NewspaperTreeWidget()
        self.control_panel = ControlPanel(self.newspaper_widget)
        
        layout.addWidget(self.control_panel)
        layout.addWidget(self.newspaper_widget)

# Альтернативная версия с динамической подстройкой под размер окна
class AdaptiveNewspaperWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.categories = {}
        self.setup_ui()
        self.load_sample_data()
        
    def setup_ui(self):
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        
        self.main_widget = QWidget()
        self.scroll_area.setWidget(self.main_widget)
        
        self.flow_layout = QHBoxLayout(self.main_widget)
        self.flow_layout.setSpacing(20)
        self.flow_layout.setContentsMargins(20, 20, 20, 20)
        
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.scroll_area)
        
    def load_sample_data(self):
        self.categories = {
            "Проекты": ["Веб-сайт", "Мобильное приложение", "API", "База данных"],
            "Задачи": ["Дизайн", "Разработка", "Тестирование", "Документация"],
            "Команда": ["Разработчики", "Дизайнеры", "Менеджеры"],
            "Ресурсы": ["Серверы", "Инструменты", "Библиотеки"]
        }
        self.distribute_items()
    
    def distribute_items(self):
        # Очищаем layout
        for i in reversed(range(self.flow_layout.count())): 
            self.flow_layout.itemAt(i).widget().setParent(None)
        
        # Создаем колонки на основе ширины окна
        available_width = self.width() - 40  # Учитываем отступы
        column_width = 300  # Фиксированная ширина колонки
        num_columns = max(1, available_width // column_width)
        
        # Создаем контейнеры для колонок
        columns = []
        for i in range(num_columns):
            column_widget = QWidget()
            column_layout = QVBoxLayout(column_widget)
            column_layout.setSpacing(10)
            column_layout.addStretch()
            columns.append(column_layout)
            self.flow_layout.addWidget(column_widget)
        
        # Распределяем категории по колонкам
        current_column = 0
        for title, items in self.categories.items():
            widget = NewspaperItemWidget(title, items)
            columns[current_column].insertWidget(columns[current_column].count() - 1, widget)
            current_column = (current_column + 1) % num_columns
    
    def resizeEvent(self, event):
        """Перераспределяем элементы при изменении размера окна"""
        super().resizeEvent(event)
        self.distribute_items()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Создаем вкладки с разными реализациями
    tab_widget = QTabWidget()
    
    # Основная версия с контролем колонок
    main_window_content = QWidget()
    main_layout = QVBoxLayout(main_window_content)
    main_layout.setContentsMargins(0, 0, 0, 0)
    
    newspaper = NewspaperTreeWidget()
    control = ControlPanel(newspaper)
    
    main_layout.addWidget(control)
    main_layout.addWidget(newspaper)
    
    tab_widget.addTab(main_window_content, "Управляемая версия")
    
    # Адаптивная версия
    adaptive_widget = AdaptiveNewspaperWidget()
    tab_widget.addTab(adaptive_widget, "Адаптивная версия")
    
    window = QMainWindow()
    window.setWindowTitle("Многоколоночная газетная верстка")
    window.setGeometry(100, 100, 1200, 700)
    window.setCentralWidget(tab_widget)
    window.show()
    
    sys.exit(app.exec_())