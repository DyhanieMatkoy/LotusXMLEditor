
import sys
import os
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from fragment_dialog import FragmentEditorDialog
from PyQt6.Qsci import QsciScintilla

class MockRegistry:
    def list(self):
        return ["Python", "JavaScript"]
    def get(self, name):
        return {}

def test_fragment_dialog():
    print("Initializing Application...")
    app = QApplication(sys.argv)
    
    registry = MockRegistry()
    print("Creating FragmentEditorDialog...")
    dialog = FragmentEditorDialog("<root>test</root>", registry)
    dialog.show()
    
    print("Verifying editor type...")
    # Check if editor is QsciScintilla
    if isinstance(dialog.editor, QsciScintilla):
        print("Verified: dialog.editor is QsciScintilla")
    else:
        print(f"Failed: dialog.editor is {type(dialog.editor)}")
        sys.exit(1)
        
    print("Test passed. Closing in 1 second...")
    
    # Close after a moment
    QTimer.singleShot(1000, dialog.close)
    
    app.exec()
    print("Application finished.")

if __name__ == "__main__":
    test_fragment_dialog()
