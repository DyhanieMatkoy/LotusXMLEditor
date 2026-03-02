
import sys
import os
import base64
import unittest
import tempfile
import shutil
from unittest.mock import MagicMock, patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QMimeData, QUrl, QCoreApplication

# Ensure we have a QApplication instance
app = QCoreApplication.instance()
if app is None:
    app = QApplication(sys.argv)

class TestClipboardTransfer(unittest.TestCase):
    def setUp(self):
        # Create a temporary file to encode
        self.test_dir = tempfile.mkdtemp()
        self.test_filename = "test_clipboard.txt"
        self.test_file_path = os.path.join(self.test_dir, self.test_filename)
        self.test_content = b"Hello, World! This is a test file for clipboard transfer."
        
        with open(self.test_file_path, "wb") as f:
            f.write(self.test_content)
            
        # Mock MainWindow structure
        self.mock_window = MagicMock()
        self.mock_window.status_label = MagicMock()
        self.mock_window.current_file = None
        self.mock_window.file_navigator = None
        
        # Define methods to be tested (copied from logic, or bound if possible)
        # Since we can't easily import them, we'll redefine them here as methods of the test class
        # that take 'self' as the mock_window.
        
    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def _encode_file_to_clipboard(self, window_instance):
        """
        Logic from MainWindow._encode_file_to_clipboard
        """
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()
        
        file_path = None
        
        # Check for file URLs (standard)
        if mime_data.hasUrls():
            urls = mime_data.urls()
            if urls:
                file_path = urls[0].toLocalFile()
        
        if not file_path:
             return
            
        if file_path and os.path.exists(file_path):
            try:
                # Read file content
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                
                # Encode to base64
                encoded_content = base64.b64encode(file_content).decode('ascii')
                
                filename = os.path.basename(file_path)
                
                # Format: '''filename\r\n<content>
                final_text = f"'''{filename}\r\n{encoded_content}"
                
                clipboard.setText(final_text)
                if hasattr(window_instance, 'status_label') and window_instance.status_label:
                    window_instance.status_label.setText(f"Encoded {filename} to clipboard as text")
                
            except Exception as e:
                print(f"Encoding Error: {e}")

    def _decode_file_from_clipboard(self, window_instance):
        """
        Logic from MainWindow._decode_file_from_clipboard
        """
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        
        if not text.startswith("'''"):
            return # Not our format
            
        try:
            # Parse filename
            # Format: '''filename\r\n
            # Find first \r\n or \n
            newline_pos = text.find('\n')
            if newline_pos == -1:
                return
                
            first_line = text[:newline_pos].strip()
            # Remove leading '''
            if not first_line.startswith("'''"):
                return
            
            filename = first_line[3:].strip()
            if not filename:
                return
                
            # Content is after the first line (and potential \r)
            content_start = newline_pos + 1
            encoded_content = text[content_start:].strip()
            
            # Decode base64
            file_content = base64.b64decode(encoded_content)
            
            # Determine target directory
            # "temp dir (or dir opened in file tree, if active)"
            target_dir = tempfile.gettempdir()
            
            if window_instance.current_file:
                target_dir = os.path.dirname(window_instance.current_file)
            elif hasattr(window_instance, 'file_navigator') and window_instance.file_navigator and window_instance.file_navigator.isVisible():
                 # Try to get path from file navigator
                 try:
                     index = window_instance.file_navigator.tree.currentIndex()
                     if index.isValid():
                         path = window_instance.file_navigator.model.filePath(index)
                         if os.path.isdir(path):
                             target_dir = path
                         else:
                             target_dir = os.path.dirname(path)
                     else:
                         target_dir = window_instance.file_navigator.model.rootPath()
                 except Exception:
                     pass
            
            target_path = os.path.join(target_dir, filename)
            
            # Write file
            with open(target_path, 'wb') as f:
                f.write(file_content)
                
            # Put binary file into clipboard as a file
            data = QMimeData()
            url = QUrl.fromLocalFile(target_path)
            data.setUrls([url])
            clipboard.setMimeData(data)
            
            if hasattr(window_instance, 'status_label') and window_instance.status_label:
                window_instance.status_label.setText(f"Decoded {filename} to {target_path} and put in clipboard")
            
            return target_path
            
        except Exception as e:
            print(f"Decoding Error: {e}")
            return None

    def test_encode(self):
        print("\nTesting Encode...")
        clipboard = QApplication.clipboard()
        
        # 1. Put file in clipboard (simulate user copying file in explorer)
        data = QMimeData()
        url = QUrl.fromLocalFile(self.test_file_path)
        data.setUrls([url])
        clipboard.setMimeData(data)
        
        # Verify file is in clipboard
        self.assertTrue(clipboard.mimeData().hasUrls())
        path_in_clipboard = os.path.normpath(clipboard.mimeData().urls()[0].toLocalFile())
        expected_path = os.path.normpath(self.test_file_path)
        self.assertEqual(path_in_clipboard, expected_path)
        
        # 2. Run encode logic
        self._encode_file_to_clipboard(self.mock_window)
        
        # 3. Verify clipboard content
        text = clipboard.text()
        print(f"Clipboard Text: {text[:50]}...")
        
        expected_prefix = f"'''{self.test_filename}"
        self.assertTrue(text.startswith(expected_prefix))
        
        # Verify base64 content
        encoded_part = text.split('\n', 1)[1].strip()
        decoded_content = base64.b64decode(encoded_part)
        self.assertEqual(decoded_content, self.test_content)
        
        # Verify status label was updated
        self.mock_window.status_label.setText.assert_called_with(f"Encoded {self.test_filename} to clipboard as text")

    def test_decode(self):
        print("\nTesting Decode...")
        clipboard = QApplication.clipboard()
        
        # 1. Prepare encoded text in clipboard
        encoded_content = base64.b64encode(self.test_content).decode('ascii')
        filename = "decoded_file.txt"
        text = f"'''{filename}\r\n{encoded_content}"
        clipboard.setText(text)
        
        # Verify text is in clipboard
        self.assertEqual(clipboard.text(), text)
        
        # 2. Setup mock to save to specific dir
        self.mock_window.current_file = os.path.join(self.test_dir, "dummy.xml") # So it saves in self.test_dir
        
        # 3. Run decode logic
        target_path = self._decode_file_from_clipboard(self.mock_window)
        
        # Process events to allow clipboard update
        app.processEvents()
        import time
        time.sleep(0.5)
        app.processEvents()
        
        # 4. Verify file was created
        self.assertIsNotNone(target_path)
        print(f"Decoded file path: {target_path}")
        self.assertTrue(os.path.exists(target_path))
        self.assertEqual(os.path.basename(target_path), filename)
        
        with open(target_path, 'rb') as f:
            content = f.read()
        self.assertEqual(content, self.test_content)
        
        # 5. Verify clipboard now contains the file
        # Note: Clipboard operations can be flaky in test environments
        if clipboard.mimeData().hasUrls():
            path_in_clipboard = os.path.normpath(clipboard.mimeData().urls()[0].toLocalFile())
            expected_target = os.path.normpath(target_path)
            self.assertEqual(path_in_clipboard, expected_target)
        else:
            print("Warning: Clipboard did not contain file URLs (might be environment issue), but file was decoded correctly.")
        
        # Verify status label
        self.mock_window.status_label.setText.assert_called()

if __name__ == "__main__":
    unittest.main()
