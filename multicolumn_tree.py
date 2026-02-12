#!/usr/bin/env python3
"""
Experimental Multicolumn Tree Window
Based on the existing XML tree but with multicolumn layout similar to newspaper layout
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QScrollArea, QLabel, QPushButton, QSpinBox, QFrame, QSplitter,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QTabWidget
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QFont, QColor

from xml_service import XmlService
from models import XmlTreeNode


class MultiColumnTreeItem(QWidget):
    """Individual tree item widget for multicolumn display"""
    item_clicked = pyqtSignal(object)  # Emits the xml_node
    
    def __init__(self, xml_node, level=0, parent=None):
        super().__init__(parent)
        self.xml_node = xml_node
        self.level = level
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the UI for this tree item"""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(1)
        
        # Create main item frame
        self.item_frame = QFrame()
        self.item_frame.setFrameStyle(QFrame.Shape.Box)
        self.item_frame.setLineWidth(1)
        self.item_frame.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                margin: 1px;
            }
            QFrame:hover {
                background-color: #e9ecef;
                border-color: #007acc;
            }
        """)
        
        item_layout = QVBoxLayout()
        item_layout.setContentsMargins(8, 4, 8, 4)
        
        # Element name with indentation based on level
        name_label = QLabel(self.xml_node.name)
        name_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        name_label.setStyleSheet(f"margin-left: {self.level * 15}px; color: #0066cc;")
        item_layout.addWidget(name_label)
        
        # Element value (if any)
        if self.xml_node.value and self.xml_node.value.strip():
            value_label = QLabel(self._truncate_value(self.xml_node.value))
            value_label.setFont(QFont("Segoe UI", 8))
            value_label.setStyleSheet("color: #666; margin-top: 2px;")
            value_label.setWordWrap(True)
            item_layout.addWidget(value_label)
        
        # Attributes (if any)
        if hasattr(self.xml_node, 'attributes') and self.xml_node.attributes:
            attr_text = ", ".join([f"{k}={v}" for k, v in self.xml_node.attributes.items()])
            attr_label = QLabel(f"[{attr_text}]")
            attr_label.setFont(QFont("Segoe UI", 7))
            attr_label.setStyleSheet("color: #888; font-style: italic;")
            item_layout.addWidget(attr_label)
        
        # Children count
        if self.xml_node.children:
            children_label = QLabel(f"({len(self.xml_node.children)} children)")
            children_label.setFont(QFont("Segoe UI", 7))
            children_label.setStyleSheet("color: #999;")
            item_layout.addWidget(children_label)
        
        self.item_frame.setLayout(item_layout)
        layout.addWidget(self.item_frame)
        
        self.setLayout(layout)
        
        # Make clickable
        self.item_frame.mousePressEvent = self._on_click
    
    def set_selected(self, selected: bool):
        """Programmatically select/highlight this item for sync visualization"""
        if not hasattr(self, 'item_frame') or self.item_frame is None:
            return
        if selected:
            self.item_frame.setStyleSheet("""
                QFrame {
                    background-color: #e6f2ff;
                    border: 2px solid #3399ff;
                    border-radius: 4px;
                    margin: 1px;
                }
                QFrame:hover {
                    background-color: #d9ecff;
                    border-color: #007acc;
                }
            """)
        else:
            self.item_frame.setStyleSheet("""
                QFrame {
                    background-color: #f8f9fa;
                    border: 1px solid #dee2e6;
                    border-radius: 4px;
                    margin: 1px;
                }
                QFrame:hover {
                    background-color: #e9ecef;
                    border-color: #007acc;
                }
            """)
        
    def _truncate_value(self, value, max_length=50):
        """Truncate value if too long"""
        if len(value) > max_length:
            return value[:max_length] + "..."
        return value
        
    def _on_click(self, event):
        """Handle item click"""
        self.item_clicked.emit(self.xml_node)
        
    def sizeHint(self):
        """Return size hint for layout calculations"""
        return super().sizeHint()


class MultiColumnTreeWidget(QScrollArea):
    """Multicolumn tree widget with newspaper-style layout"""
    node_selected = pyqtSignal(object)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.columns_count = 3
        self.tree_items = []
        self.last_selected_item = None
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the multicolumn layout"""
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Main container
        self.container = QWidget()
        self.main_layout = QHBoxLayout()
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)
        
        # Create initial columns
        self.columns = []
        self.create_columns()
        
        self.container.setLayout(self.main_layout)
        self.setWidget(self.container)
        
    def create_columns(self):
        """Create column layouts"""
        # Clear existing columns
        for column in self.columns:
            column.deleteLater()
        self.columns.clear()
        
        # Create new columns
        for i in range(self.columns_count):
            column_widget = QWidget()
            column_layout = QVBoxLayout()
            column_layout.setContentsMargins(5, 5, 5, 5)
            column_layout.setSpacing(5)
            column_layout.addStretch()  # Add stretch at the end
            
            column_widget.setLayout(column_layout)
            column_widget.setStyleSheet("""
                QWidget {
                    background-color: #ffffff;
                    border: 1px solid #e0e0e0;
                    border-radius: 6px;
                }
            """)
            
            self.columns.append(column_widget)
            self.main_layout.addWidget(column_widget)
            
    def populate_tree(self, xml_content: str):
        """Populate the multicolumn tree with XML structure"""
        self.clear_items()
        
        if not xml_content.strip():
            return
            
        try:
            # Parse XML using the service
            service = XmlService()
            root = service.parse_xml(xml_content)
            if root is None:
                print("Failed to parse XML in multicolumn tree")
                return
            root_node = service._element_to_tree_node(root)
            
            if root_node:
                # Flatten the tree structure for multicolumn display
                self._flatten_tree_recursive(root_node, 0)
                
                # Distribute items across columns
                self.distribute_items()
                
        except Exception as e:
            print(f"Error populating multicolumn tree: {e}")
            
    def _flatten_tree_recursive(self, node, level, max_level=4):
        """Recursively flatten tree structure with level limit"""
        if level > max_level:
            return
            
        # Create item for current node
        item_widget = MultiColumnTreeItem(node, level)
        item_widget.item_clicked.connect(self.node_selected.emit)
        self.tree_items.append(item_widget)
        
        # Process children
        for child in node.children:
            self._flatten_tree_recursive(child, level + 1, max_level)
            
    def distribute_items(self):
        """Distribute tree items across columns"""
        if not self.tree_items:
            return
            
        # Calculate items per column
        items_per_column = len(self.tree_items) // self.columns_count
        remainder = len(self.tree_items) % self.columns_count
        
        item_index = 0
        
        for col_index, column in enumerate(self.columns):
            # Calculate how many items this column should get
            column_items = items_per_column + (1 if col_index < remainder else 0)
            
            # Add items to this column
            column_layout = column.layout()
            
            for i in range(column_items):
                if item_index < len(self.tree_items):
                    # Insert before the stretch
                    column_layout.insertWidget(column_layout.count() - 1, self.tree_items[item_index])
                    item_index += 1
                    
    def clear_items(self):
        """Clear all tree items"""
        for item in self.tree_items:
            item.deleteLater()
        self.tree_items.clear()
        self.last_selected_item = None
        
        # Clear columns
        for column in self.columns:
            layout = column.layout()
            while layout.count() > 1:  # Keep the stretch item
                child = layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()
    
    def find_item_by_path(self, path: str):
        """Find a multicolumn item widget by its XmlTreeNode.path"""
        normalized = path if path.startswith('/') else '/' + path
        for item in self.tree_items:
            node = getattr(item, 'xml_node', None)
            node_path = getattr(node, 'path', '') if node else ''
            if node_path == normalized:
                return item
        return None
        
    def set_columns_count(self, count):
        """Set the number of columns"""
        if count != self.columns_count and 1 <= count <= 6:
            self.columns_count = count
            self.create_columns()
            if self.tree_items:
                self.distribute_items()


class MultiColumnTreeControlPanel(QWidget):
    """Control panel for the multicolumn tree"""
    columns_changed = pyqtSignal(int)
    refresh_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup control panel UI"""
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Columns control
        layout.addWidget(QLabel("Columns:"))
        
        self.columns_spinbox = QSpinBox()
        self.columns_spinbox.setRange(1, 6)
        self.columns_spinbox.setValue(3)
        self.columns_spinbox.valueChanged.connect(self.columns_changed.emit)
        layout.addWidget(self.columns_spinbox)
        
        layout.addWidget(QLabel("|"))
        
        # Refresh button
        refresh_btn = QPushButton("Refresh Layout")
        refresh_btn.clicked.connect(self.refresh_requested.emit)
        layout.addWidget(refresh_btn)
        
        layout.addStretch()
        
        # Info label
        info_label = QLabel("Experimental multicolumn tree view")
        info_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(info_label)
        
        self.setLayout(layout)


class MultiColumnTreeWindow(QMainWindow):
    """Main window for the experimental multicolumn tree"""
    
    def __init__(self, xml_content="", parent=None):
        super().__init__(parent)
        self.xml_content = xml_content
        self.sync_enabled = False
        self.setup_ui()
        self.setup_connections()
        
        if xml_content:
            self.populate_tree(xml_content)
            
    def setup_ui(self):
        """Setup the main window UI"""
        self.setWindowTitle("Experimental Multicolumn XML Tree")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout()
        
        # Control panel
        self.control_panel = MultiColumnTreeControlPanel()
        layout.addWidget(self.control_panel)
        
        # Multicolumn tree
        self.multicolumn_tree = MultiColumnTreeWidget()
        layout.addWidget(self.multicolumn_tree)
        
        central_widget.setLayout(layout)
        
        # Status bar
        self.statusBar().showMessage("Experimental multicolumn tree view ready")
        
    def setup_connections(self):
        """Setup signal connections"""
        self.control_panel.columns_changed.connect(self.multicolumn_tree.set_columns_count)
        self.control_panel.refresh_requested.connect(self.refresh_layout)
        self.multicolumn_tree.node_selected.connect(self.on_node_selected)
        
    def populate_tree(self, xml_content):
        """Populate the tree with XML content"""
        self.xml_content = xml_content
        self.multicolumn_tree.populate_tree(xml_content)
        self.statusBar().showMessage(f"Loaded {len(self.multicolumn_tree.tree_items)} tree items")
        
    def refresh_layout(self):
        """Refresh the layout"""
        if self.xml_content:
            self.populate_tree(self.xml_content)
            
    def on_node_selected(self, xml_node):
        """Handle node selection"""
        node_info = f"Selected: {xml_node.name}"
        if xml_node.value:
            node_info += f" = {xml_node.value[:50]}..."
        self.statusBar().showMessage(node_info)


if __name__ == '__main__':
    # Test the multicolumn tree with sample XML
    app = QApplication(sys.argv)
    
    sample_xml = """
    <?xml version="1.0" encoding="UTF-8"?>
    <root>
        <group name="Group1">
            <item id="1">Item 1 Value</item>
            <item id="2">Item 2 Value</item>
            <subgroup>
                <item id="3">Item 3 Value</item>
                <item id="4">Item 4 Value</item>
            </subgroup>
        </group>
        <group name="Group2">
            <item id="5">Item 5 Value</item>
            <item id="6">Item 6 Value</item>
        </group>
        <metadata>
            <author>Test Author</author>
            <version>1.0</version>
            <description>Sample XML for testing multicolumn tree</description>
        </metadata>
    </root>
    """
    
    window = MultiColumnTreeWindow(sample_xml)
    window.show()
    
    sys.exit(app.exec())