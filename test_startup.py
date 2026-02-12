
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.Qsci import QsciScintilla
try:
    from main import MainWindow, XmlEditorWidget
except ImportError as e:
    print(f"Import Error: {e}")
    sys.exit(1)

def test_startup():
    print("Initializing QApplication...")
    app = QApplication(sys.argv)
    
    print("Creating MainWindow...")
    try:
        window = MainWindow()
        print("MainWindow created successfully.")
        
        # Check if xml_editor is QScintilla
        if isinstance(window.xml_editor, QsciScintilla):
            print("Verified: xml_editor is instance of QsciScintilla")
        else:
            print(f"Error: xml_editor is {type(window.xml_editor)}")
            
        # Check QScintilla functionality
        print("Checking QScintilla methods...")
        # Check if we can get text
        text = window.xml_editor.text()
        print(f"text() returned length: {len(text)}")
        
        # Check if we can get line count
        lines = window.xml_editor.lines()
        print(f"lines() returned: {lines}")
        
        # Check available methods
        # print(dir(window.xml_editor))
        
        # Check specific fold methods
        print(f"has isFoldLine: {hasattr(window.xml_editor, 'isFoldLine')}")
        print(f"has foldLine: {hasattr(window.xml_editor, 'foldLine')}")
        print(f"has foldExpanded: {hasattr(window.xml_editor, 'foldExpanded')}")
        print(f"has foldAll: {hasattr(window.xml_editor, 'foldAll')}")
        
        print("Closing window...")
        window.close()
        print("Test passed.")
        
    except Exception as e:
        print(f"Runtime Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_startup()
