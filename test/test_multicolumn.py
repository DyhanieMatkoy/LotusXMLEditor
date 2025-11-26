#!/usr/bin/env python3
"""
Test script for the experimental multicolumn tree
"""

import sys
from PyQt6.QtWidgets import QApplication
from multicolumn_tree import MultiColumnTreeWindow

def main():
    """Test the multicolumn tree with sample XML"""
    app = QApplication(sys.argv)
    
    # Sample XML content for testing
    sample_xml = """
    <?xml version="1.0" encoding="UTF-8"?>
    <ПравилаОбмена>
        <ВерсияФормата РежимСовместимости="РежимСовместимостиСБСП21">2.01</ВерсияФормата>
        <Группа>
            <Наименование>Основная группа</Наименование>
            <Правило>
                <Наименование>Правило 1</Наименование>
                <Описание>Описание первого правила</Описание>
                <Параметры>
                    <Параметр Имя="param1">Значение1</Параметр>
                    <Параметр Имя="param2">Значение2</Параметр>
                </Параметры>
            </Правило>
            <Правило>
                <Наименование>Правило 2</Наименование>
                <Описание>Описание второго правила</Описание>
                <Параметры>
                    <Параметр Имя="param3">Значение3</Параметр>
                    <Параметр Имя="param4">Значение4</Параметр>
                </Параметры>
            </Правило>
        </Группа>
        <Группа>
            <Наименование>Дополнительная группа</Наименование>
            <Правило>
                <Наименование>Правило 3</Наименование>
                <Описание>Описание третьего правила</Описание>
                <Условия>
                    <Условие Тип="Равно">Значение условия</Условие>
                </Условия>
            </Правило>
        </Группа>
        <Метаданные>
            <Автор>Тестовый автор</Автор>
            <Версия>1.0</Версия>
            <Дата>2024-01-15</Дата>
            <Описание>Тестовый XML файл для проверки многоколоночного дерева</Описание>
        </Метаданные>
    </ПравилаОбмена>
    """
    
    # Create and show the multicolumn tree window
    window = MultiColumnTreeWindow(sample_xml)
    window.show()
    
    print("Multicolumn tree test window opened successfully!")
    print("Features to test:")
    print("- Adjust column count using the spinbox")
    print("- Click on tree items to see selection")
    print("- Use refresh button to redistribute items")
    print("- Observe the multicolumn layout with XML structure")
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()