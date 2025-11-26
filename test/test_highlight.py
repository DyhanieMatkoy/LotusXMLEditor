#!/usr/bin/env python3
"""
Test script to verify the orange border highlighting feature
"""

import sys
from PyQt6.QtWidgets import QApplication
from main import MainWindow

def test_highlight():
    """Test the highlight feature with a sample XML file"""
    app = QApplication(sys.argv)
    
    # Create main window
    window = MainWindow()
    
    # Load a test XML file (you can change this to any XML file)
    test_xml = """<?xml version="1.0" encoding="UTF-8"?>
<root>
    <parent>
        <child id="1">
            <name>Test Element</name>
            <value>Some value here</value>
        </child>
        <child id="2">
            <name>Another Element</name>
            <value>Another value</value>
        </child>
    </parent>
</root>"""
    
    window.xml_editor.set_content(test_xml)
    window.xml_tree.populate_tree(test_xml, show_progress=False)
    
    window.show()
    
    print("Test window opened. Click on tree nodes to see the orange border highlighting.")
    print("The status bar should show the line count.")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    test_highlight()
