#!/usr/bin/env python3
"""
Demo script to visually test line numbers
"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout
from PyQt6.QtCore import QSettings

def main():
    app = QApplication(sys.argv)
    
    # Import after QApplication is created
    from main import XmlEditorWidget
    
    # Create main window
    window = QMainWindow()
    window.setWindowTitle("Line Numbers Demo")
    window.setGeometry(100, 100, 800, 600)
    
    # Create central widget
    central = QWidget()
    layout = QVBoxLayout()
    
    # Create editor
    editor = XmlEditorWidget()
    editor.setPlainText("""<?xml version="1.0" encoding="UTF-8"?>
<root>
    <element1>Value 1</element1>
    <element2>Value 2</element2>
    <element3>
        <nested>Nested Value</nested>
    </element3>
    <element4>Value 4</element4>
    <element5>Value 5</element5>
    <element6>Value 6</element6>
    <element7>Value 7</element7>
    <element8>Value 8</element8>
    <element9>Value 9</element9>
    <element10>Value 10</element10>
</root>""")
    
    # Create button layout
    button_layout = QHBoxLayout()
    
    # Toggle button
    toggle_btn = QPushButton("Toggle Line Numbers")
    toggle_btn.clicked.connect(lambda: editor.set_line_numbers_visible(
        not editor.line_number_widget.isVisible()
    ))
    button_layout.addWidget(toggle_btn)
    
    # Show button
    show_btn = QPushButton("Show Line Numbers")
    show_btn.clicked.connect(lambda: editor.set_line_numbers_visible(True))
    button_layout.addWidget(show_btn)
    
    # Hide button
    hide_btn = QPushButton("Hide Line Numbers")
    hide_btn.clicked.connect(lambda: editor.set_line_numbers_visible(False))
    button_layout.addWidget(hide_btn)
    
    layout.addLayout(button_layout)
    layout.addWidget(editor)
    
    central.setLayout(layout)
    window.setCentralWidget(central)
    
    # Show window
    window.show()
    
    print("Demo started!")
    print("- Click 'Toggle Line Numbers' to toggle visibility")
    print("- Click 'Show Line Numbers' to show them")
    print("- Click 'Hide Line Numbers' to hide them")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
