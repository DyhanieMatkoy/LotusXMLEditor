import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings

def verify_settings():
    # Setup QSettings to match what we expect
    settings = QSettings("visxml.net", "LotusXmlEditor")
    
    # 1. Verify highlight_enabled persistence
    # Simulate saving a value
    settings.setValue("flags/highlight_enabled", True)
    
    # Verify we can read it back with the correct key
    val = settings.value("flags/highlight_enabled")
    print(f"Read highlight_enabled: {val} (Expected: True/true)")
    
    # Simulate false
    settings.setValue("flags/highlight_enabled", False)
    val = settings.value("flags/highlight_enabled")
    print(f"Read highlight_enabled: {val} (Expected: False/false)")

    # 2. Verify settings dialog keys
    # toolbar_autohide should be under flags/
    settings.setValue("flags/toolbar_autohide", False)
    val = settings.value("flags/toolbar_autohide")
    print(f"Read toolbar_autohide: {val} (Expected: False/false)")
    
    print("Verification complete.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    verify_settings()
