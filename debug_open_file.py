import sys
import os
from PyQt6.QtWidgets import QApplication
# Add current directory to path so imports work
sys.path.append(os.getcwd())

# Import MainWindow from main.py
# We need to handle potential import errors if dependencies are missing, 
# but assuming environment is set up.
from main import MainWindow

def test_open():
    print("Initializing QApplication...")
    app = QApplication(sys.argv)
    
    print("Creating MainWindow...")
    window = MainWindow()
    
    test_file = os.path.abspath("large_test.xml")
    print(f"Testing open_file with {test_file}")
    
    window.open_file(test_file)
    
    # Check editor content immediately
    content = window.xml_editor.toPlainText()
    print(f"Immediate Editor content length: {len(content)}")
    if len(content) > 0:
        print(f"Immediate Editor content: {content[:50]}...")
    else:
        print("Immediate Editor content is EMPTY")
    
    # Process events loop for a few seconds to allow async tasks to complete
    print("Processing events for 3 seconds...")
    import time
    start = time.time()
    while time.time() - start < 3:
        app.processEvents()
        time.sleep(0.1)
    
    content_after = window.xml_editor.toPlainText()
    print(f"After events Editor content length: {len(content_after)}")
    if len(content_after) == 0:
        print("After events Editor content is EMPTY")

if __name__ == "__main__":
    try:
        test_open()
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
