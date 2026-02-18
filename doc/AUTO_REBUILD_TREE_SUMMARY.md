# AutoRebuildTree Feature - Summary

## Краткое описание

Добавлена опция **AutoRebuildTree** в настройки приложения, которая позволяет контролировать автоматическое обновление дерева XML при изменении текста в редакторе.

## Основные изменения

### 1. Новая опция в настройках
- **Название**: Auto Rebuild Tree
- **Раздел**: Tree Updates
- **Тип**: Boolean (checkbox)
- **По умолчанию**: Включено (True)
- **Описание**: "Automatically rebuild tree when text changes"

### 2. Визуальный индикатор
- **Символ**: ⚠ (оранжевый)
- **Расположение**: Слева от кнопки "Rebuild Tree" в toolbar
- **Условие показа**: Опция выключена И текст был изменен
- **Tooltip**: "Tree needs rebuild - click 'Rebuild Tree' to update"

### 3. Логика работы

#### Опция включена (по умолчанию):
```
Изменение текста → Debounce 5 сек → Автоматическое обновление дерева
```

#### Опция выключена:
```
Изменение текста → Показать индикатор ⚠ → Ожидание действия пользователя
                                        ↓
                                   Нажатие F11 или "Rebuild Tree"
                                        ↓
                                   Скрыть индикатор ⚠
                                        ↓
                                   Обновление дерева
```

## Измененные файлы

### main.py
```python
# Добавлено:
- self.auto_rebuild_tree = True  # Флаг опции
- self._tree_needs_rebuild = False  # Флаг необходимости обновления
- self.tree_rebuild_indicator = QLabel("⚠")  # Индикатор в toolbar

# Изменено:
- on_content_changed()  # Проверка флага auto_rebuild_tree
- rebuild_tree_with_autoclose()  # Скрытие индикатора
- _load_persisted_flags()  # Загрузка настройки
```

### settings_dialog.py
```python
# Добавлено в settings_structure:
"Tree Updates": {
    "auto_rebuild_tree": ("Auto Rebuild Tree", "bool", True, "..."),
    "tree_update_debounce": ("Debounce Interval (ms)", "int", 5000, "..."),
}

# Изменено:
- _load_current_values()  # Загрузка auto_rebuild_tree
- _save_and_close()  # Сохранение auto_rebuild_tree
- _apply_settings_to_parent()  # Применение к главному окну
```

## Созданные файлы документации

1. **doc/AUTO_REBUILD_TREE_FEATURE.md** - Полная документация (English)
2. **doc/AUTO_REBUILD_TREE_RU.md** - Краткая инструкция (Русский)
3. **doc/AUTO_REBUILD_TREE_VISUAL.txt** - Визуальное руководство
4. **CHANGELOG_AUTO_REBUILD_TREE.md** - Список изменений
5. **AUTO_REBUILD_TREE_README.md** - Краткая инструкция для пользователя
6. **test_auto_rebuild_tree.py** - Тестовый скрипт

## Использование

### Для пользователей
1. Откройте **Settings** → **Settings...**
2. Найдите **Tree Updates** → **Auto Rebuild Tree**
3. Установите/снимите флажок
4. Нажмите **OK**

### Для разработчиков
```python
# Чтение настройки
settings = QSettings("visxml.net", "LotusXmlEditor")
auto_rebuild = settings.value("flags/auto_rebuild_tree", True, type=bool)

# Сохранение настройки
settings.setValue("flags/auto_rebuild_tree", False)
```

## Тестирование

```bash
# Запуск теста
python test_auto_rebuild_tree.py

# Ожидаемый результат
✓ Test 1 passed: auto_rebuild_tree saved as True
✓ Test 2 passed: auto_rebuild_tree saved as False
✓ Test 3 passed: auto_rebuild_tree defaults to True
✓ All tests passed!
```

## Преимущества

1. **Производительность**: Отключение автообновления для больших файлов
2. **Контроль**: Пользователь решает, когда обновлять дерево
3. **Визуальная обратная связь**: Индикатор показывает необходимость обновления
4. **Гибкость**: Настройка сохраняется между сеансами
5. **Удобство**: Горячая клавиша F11 для быстрого обновления

## Совместимость

- ✓ Windows
- ✓ PyQt6
- ✓ Сохранение настроек в QSettings
- ✓ Обратная совместимость (по умолчанию включено)

## Горячие клавиши

- **F11** - Rebuild Tree (обновить дерево вручную)
