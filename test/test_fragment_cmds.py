import sys
import unittest
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QApplication

# Mock QsciScintilla before importing fragment_dialog if needed, 
# but it's better to let it import and just mock the instance in the dialog.

# Add path
import os
sys.path.append(os.getcwd())

from fragment_dialog import FragmentEditorDialog

class TestFragmentEditorCommands(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication(sys.argv)

    def test_escape_logic(self):
        # Mock dependencies
        mock_registry = MagicMock()
        mock_registry.list.return_value = []
        
        # Instantiate dialog
        dialog = FragmentEditorDialog("Initial text", mock_registry)
        
        # Mock editor methods
        dialog.editor.hasSelectedText = MagicMock(return_value=True)
        dialog.editor.selectedText = MagicMock(return_value='<foo> "bar" & baz')
        dialog.editor.replaceSelection = MagicMock()
        
        # Call escape
        dialog.escape_xml_entities()
        
        # Verify result
        dialog.editor.replaceSelection.assert_called_with('&lt;foo&gt; &quot;bar&quot; &amp; baz')
        
    def test_unescape_logic(self):
        # Mock dependencies
        mock_registry = MagicMock()
        mock_registry.list.return_value = []
        
        # Instantiate dialog
        dialog = FragmentEditorDialog("Initial text", mock_registry)
        
        # Mock editor methods
        dialog.editor.hasSelectedText = MagicMock(return_value=True)
        dialog.editor.selectedText = MagicMock(return_value='&lt;foo&gt; &quot;bar&quot; &amp; baz')
        dialog.editor.replaceSelection = MagicMock()
        
        # Call unescape
        dialog.unescape_xml_entities()
        
        # Verify result
        dialog.editor.replaceSelection.assert_called_with('<foo> "bar" & baz')

if __name__ == '__main__':
    unittest.main()
