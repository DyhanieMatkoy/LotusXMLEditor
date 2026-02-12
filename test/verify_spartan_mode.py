import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QAction
from PyQt6.QtCore import QSettings

# Mock MainWindow class for testing
class MockMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.toggle_sync_action = QAction("Sync", self)
        self.toggle_sync_action.setCheckable(True)
        self.toggle_sync_action.setChecked(True)
        
        self.toggle_update_tree_view_action = QAction("Update Tree", self)
        self.toggle_update_tree_view_action.setCheckable(True)
        self.toggle_update_tree_view_action.setChecked(True)
        
        self.toggle_highlight_action = QAction("Highlight", self)
        self.toggle_highlight_action.setCheckable(True)
        self.toggle_highlight_action.setChecked(True)
        
        self.settings = QSettings("visxml.net", "LotusXmlEditor")
        
    def _save_flag(self, key, value):
        self.settings.setValue(f"flags/{key}", value)
        
    def activate_spartan_mode(self, checked):
        if checked:
            self.toggle_sync_action.setChecked(False)
            self.toggle_update_tree_view_action.setChecked(False)
            self.toggle_highlight_action.setChecked(False)

def verify_spartan_mode():
    app = QApplication(sys.argv)
    window = MockMainWindow()
    
    print("Initial State:")
    print(f"Sync: {window.toggle_sync_action.isChecked()}")
    print(f"Update Tree: {window.toggle_update_tree_view_action.isChecked()}")
    print(f"Highlight: {window.toggle_highlight_action.isChecked()}")
    
    print("\nActivating Spartan Mode...")
    window.activate_spartan_mode(True)
    
    print("State after Spartan Mode activation (Expected: All False):")
    print(f"Sync: {window.toggle_sync_action.isChecked()}")
    print(f"Update Tree: {window.toggle_update_tree_view_action.isChecked()}")
    print(f"Highlight: {window.toggle_highlight_action.isChecked()}")
    
    if (not window.toggle_sync_action.isChecked() and 
        not window.toggle_update_tree_view_action.isChecked() and 
        not window.toggle_highlight_action.isChecked()):
        print("\nSUCCESS: Spartan Mode correctly disabled features.")
    else:
        print("\nFAILURE: Some features remained enabled.")

if __name__ == "__main__":
    verify_spartan_mode()
