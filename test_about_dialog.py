"""
Test script for About Dialog
"""

import sys
from PyQt6.QtWidgets import QApplication
from about_dialog import AboutDialog


def test_about_dialog():
    """Test the About dialog"""
    app = QApplication(sys.argv)
    
    # Test with a file path
    dialog = AboutDialog(None, "C:/test/example.xml")
    dialog.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    test_about_dialog()
