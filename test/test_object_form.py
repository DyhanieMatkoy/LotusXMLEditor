
import sys
import unittest
from PyQt6.QtWidgets import QApplication, QLineEdit, QTableWidget, QGroupBox, QPushButton, QLabel
from models import XmlTreeNode
from object_form import ObjectNodeForm

# Create application instance if not exists
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

class TestObjectForm(unittest.TestCase):
    def setUp(self):
        # Create a complex XML node structure
        self.root = XmlTreeNode(name="root", tag="RootObject")
        
        # 1. Simple Attributes
        self.root.attributes = {"id": "123", "type": "demo"}
        
        # 2. Simple Field Child
        child1 = XmlTreeNode(name="name", tag="Name", value="Test Object")
        self.root.children.append(child1)
        
        # 3. Table Data (List of Items)
        item1 = XmlTreeNode(name="item", tag="Item")
        item1.attributes = {"code": "A1"}
        item1_val = XmlTreeNode(name="value", tag="Value", value="100")
        item1.children.append(item1_val)
        
        item2 = XmlTreeNode(name="item", tag="Item")
        item2.attributes = {"code": "B2"}
        item2_val = XmlTreeNode(name="value", tag="Value", value="200")
        item2.children.append(item2_val)
        
        self.root.children.append(item1)
        self.root.children.append(item2)
        
        # 4. Complex Child (Nested Object)
        self.nested = XmlTreeNode(name="config", tag="Configuration")
        setting = XmlTreeNode(name="setting", tag="Setting", value="Enabled")
        self.nested.children.append(setting)
        self.root.children.append(self.nested)

    def test_form_creation(self):
        form = ObjectNodeForm(self.root)
        
        # Verify window title
        self.assertEqual(form.windowTitle(), "Object Viewer - RootObject")
        
        # Traverse layout to find widgets
        widgets = self._get_all_widgets(form)
        
        # Check for Attribute fields
        line_edits = [w for w in widgets if isinstance(w, QLineEdit)]
        values = [le.text() for le in line_edits]
        self.assertIn("123", values)
        self.assertIn("demo", values)
        self.assertIn("Test Object", values)
        
        # Check for Table
        tables = [w for w in widgets if isinstance(w, QTableWidget)]
        self.assertTrue(len(tables) >= 1)
        
        # Check for Nested Object (Group/Collapse)
        buttons = [w for w in widgets if isinstance(w, QPushButton)]
        toggle_btns = [b for b in buttons if "Configuration" in b.text()]
        self.assertTrue(len(toggle_btns) > 0)
        
        # Check Navigation Button
        open_btns = [b for b in buttons if b.text() == "Open"]
        self.assertTrue(len(open_btns) > 0)

    def test_navigation(self):
        form = ObjectNodeForm(self.root)
        
        # Initially at root
        self.assertEqual(form.current_node, self.root)
        self.assertEqual(len(form.history), 0)
        self.assertFalse(form.back_btn.isEnabled())
        
        # Navigate to nested
        form.navigate_to(self.nested)
        
        # Check state
        self.assertEqual(form.current_node, self.nested)
        self.assertEqual(len(form.history), 1)
        self.assertTrue(form.back_btn.isEnabled())
        self.assertEqual(form.windowTitle(), "Object Viewer - Configuration")
        
        # Verify Breadcrumbs
        breadcrumbs = form.breadcrumbs_layout
        # Expected: RootObject > Configuration (stretch at end)
        # We can count widgets in layout
        # But easier to check functionality
        
        # Go Back
        form.go_back()
        self.assertEqual(form.current_node, self.root)
        self.assertEqual(len(form.history), 0)
        self.assertFalse(form.back_btn.isEnabled())

    def _get_all_widgets(self, widget):
        widgets = []
        children = widget.findChildren(object)
        for child in children:
            widgets.append(child)
        return widgets

if __name__ == '__main__':
    unittest.main()
