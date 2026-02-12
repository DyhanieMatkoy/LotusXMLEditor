import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel
from PyQt6.QtGui import QAction

# Mock MainWindow class for testing toggle logic
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
        
        self.status_label = QLabel("Ready")
        
        # Connect signals to update mocked state
        self.toggle_sync_action.toggled.connect(lambda c: print(f"Sync toggled: {c}"))
        self.toggle_update_tree_view_action.toggled.connect(lambda c: print(f"Tree toggled: {c}"))
        self.toggle_highlight_action.toggled.connect(lambda c: print(f"Highlight toggled: {c}"))

    def _save_flag(self, key, value):
        print(f"Saving flag {key}: {value}")

    def _update_flags_indicator(self):
        pass

    def _on_spartan_mode_toggled(self, checked: bool):
        # Implementation copied from main.py for verification
        self.spartan_mode = checked
        try:
            self._save_flag('spartan_mode', checked)
        except Exception:
            pass
        
        if checked:
            self.spartan_pre_state = {}
            
            if hasattr(self, 'toggle_sync_action'):
                self.spartan_pre_state['sync'] = self.toggle_sync_action.isChecked()
                self.toggle_sync_action.setChecked(False)
                
            if hasattr(self, 'toggle_update_tree_view_action'):
                self.spartan_pre_state['update_tree'] = self.toggle_update_tree_view_action.isChecked()
                self.toggle_update_tree_view_action.setChecked(False)
                
            if hasattr(self, 'toggle_highlight_action'):
                self.spartan_pre_state['highlight'] = self.toggle_highlight_action.isChecked()
                self.toggle_highlight_action.setChecked(False)
            
            if hasattr(self, 'status_label') and self.status_label:
                self.status_label.setText("Spartan Mode enabled")
        else:
            restore_sync = False
            restore_tree = True
            restore_highlight = True
            
            if hasattr(self, 'spartan_pre_state'):
                restore_sync = self.spartan_pre_state.get('sync', False)
                restore_tree = self.spartan_pre_state.get('update_tree', True)
                restore_highlight = self.spartan_pre_state.get('highlight', True)
            
            if hasattr(self, 'toggle_sync_action'):
                self.toggle_sync_action.setChecked(restore_sync)
            
            if hasattr(self, 'toggle_update_tree_view_action'):
                self.toggle_update_tree_view_action.setChecked(restore_tree)
            
            if hasattr(self, 'toggle_highlight_action'):
                self.toggle_highlight_action.setChecked(restore_highlight)
            
            if hasattr(self, 'status_label') and self.status_label:
                self.status_label.setText("Spartan Mode disabled")

def verify_toggle_logic():
    app = QApplication(sys.argv)
    window = MockMainWindow()
    
    print("--- Initial State ---")
    print(f"Sync: {window.toggle_sync_action.isChecked()}")
    print(f"Tree: {window.toggle_update_tree_view_action.isChecked()}")
    print(f"High: {window.toggle_highlight_action.isChecked()}")
    
    print("\n--- Enabling Spartan Mode ---")
    window._on_spartan_mode_toggled(True)
    
    print(f"Sync: {window.toggle_sync_action.isChecked()} (Expected: False)")
    print(f"Tree: {window.toggle_update_tree_view_action.isChecked()} (Expected: False)")
    print(f"High: {window.toggle_highlight_action.isChecked()} (Expected: False)")
    
    if (not window.toggle_sync_action.isChecked() and 
        not window.toggle_update_tree_view_action.isChecked() and 
        not window.toggle_highlight_action.isChecked()):
        print("SUCCESS: Spartan Mode disabled features.")
    else:
        print("FAILURE: Some features remained enabled.")
        
    print("\n--- Disabling Spartan Mode (Restoring) ---")
    window._on_spartan_mode_toggled(False)
    
    print(f"Sync: {window.toggle_sync_action.isChecked()} (Expected: True)")
    print(f"Tree: {window.toggle_update_tree_view_action.isChecked()} (Expected: True)")
    print(f"High: {window.toggle_highlight_action.isChecked()} (Expected: True)")
    
    if (window.toggle_sync_action.isChecked() and 
        window.toggle_update_tree_view_action.isChecked() and 
        window.toggle_highlight_action.isChecked()):
        print("SUCCESS: Features restored correctly.")
    else:
        print("FAILURE: Features not restored.")

    # Test "Fresh Start" scenario (simulate restart in Spartan Mode)
    print("\n--- Simulating Restart in Spartan Mode ---")
    window.spartan_mode = True
    # Simulate loaded state (Spartan On, Features Off)
    if hasattr(window, 'spartan_pre_state'):
        del window.spartan_pre_state
    window.toggle_sync_action.setChecked(False)
    window.toggle_update_tree_view_action.setChecked(False)
    window.toggle_highlight_action.setChecked(False)
    
    print("Disabling Spartan Mode (Expect defaults: Sync=False, Tree=True, High=True)")
    window._on_spartan_mode_toggled(False)
    
    print(f"Sync: {window.toggle_sync_action.isChecked()} (Expected: False)")
    print(f"Tree: {window.toggle_update_tree_view_action.isChecked()} (Expected: True)")
    print(f"High: {window.toggle_highlight_action.isChecked()} (Expected: True)")
    
    if (not window.toggle_sync_action.isChecked() and 
        window.toggle_update_tree_view_action.isChecked() and 
        window.toggle_highlight_action.isChecked()):
        print("SUCCESS: Defaults applied correctly.")
    else:
        print("FAILURE: Defaults logic failed.")

if __name__ == "__main__":
    verify_toggle_logic()
