
import sys
import os
from PyQt6.QtCore import QSettings, QCoreApplication

# Mocking the logic
def simulate_zip_open(xml_files, user_selection=None):
    app = QCoreApplication(sys.argv)
    app.setOrganizationName("visxml.net")
    app.setApplicationName("LotusXmlEditor")
    
    settings = QSettings("visxml.net", "LotusXmlEditor")
    
    # Read current setting
    default_pattern = settings.value("zip_default_file_pattern", "ExchangeRules.xml")
    print(f"Current setting: {default_pattern}")
    
    default_index = 0
    found = False
    
    # 1. Try saved preference
    if default_pattern:
        for i, fname in enumerate(xml_files):
            if fname == default_pattern:
                default_index = i
                found = True
                print(f"Found preference match '{fname}' at index {i}")
                break
    
    # 2. Fallback to ExchangeRules.xml if preference not found
    if not found and default_pattern != "ExchangeRules.xml":
            for i, fname in enumerate(xml_files):
                if fname == "ExchangeRules.xml":
                    default_index = i
                    print(f"Fallback match '{fname}' at index {i}")
                    break
    
    print(f"Proposed selection: {xml_files[default_index]}")
    
    # Simulate user selection
    if user_selection:
        print(f"User selected: {user_selection}")
        settings.setValue("zip_default_file_pattern", user_selection)
        print(f"Saved setting: {user_selection}")

def reset_settings():
    app = QCoreApplication(sys.argv)
    app.setOrganizationName("visxml.net")
    app.setApplicationName("LotusXmlEditor")
    settings = QSettings("visxml.net", "LotusXmlEditor")
    settings.remove("zip_default_file_pattern")
    print("Settings reset")

if __name__ == "__main__":
    print("--- Test 1: Default behavior ---")
    reset_settings()
    files = ["FileA.xml", "ExchangeRules.xml", "FileB.xml"]
    simulate_zip_open(files) # Should propose ExchangeRules.xml
    
    print("\n--- Test 2: Persistence ---")
    files = ["FileA.xml", "FileB.xml"]
    simulate_zip_open(files, "FileB.xml") # User selects FileB.xml
    
    print("\n--- Test 3: New Default ---")
    files = ["FileA.xml", "FileB.xml", "ExchangeRules.xml"]
    simulate_zip_open(files) # Should propose FileB.xml
    
    print("\n--- Test 4: Fallback ---")
    # Setting is still FileB.xml from Test 2/3
    files = ["FileA.xml", "ExchangeRules.xml"]
    # FileB.xml is missing. Should fallback to ExchangeRules.xml
    simulate_zip_open(files) 
    
    print("\n--- Cleanup ---")
    reset_settings()
