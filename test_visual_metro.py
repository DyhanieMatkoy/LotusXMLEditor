"""
Visual test for Metro Navigator graphical elements

This script creates a simple test window to verify:
1. Station nodes render correctly
2. Connection lines render correctly
3. Zoom functionality works
4. Pan functionality works
"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt

from models import XmlTreeNode
from metro_navigator import MetroNavigatorWindow


def create_test_xml_tree():
    """Create a simple test XML tree for visualization"""
    # Root node
    root = XmlTreeNode(
        name="root[1]",
        tag="root",
        value="",
        attributes={"version": "1.0", "encoding": "UTF-8"},
        path="/root[1]",
        line_number=1
    )
    
    # Level 1 nodes
    for i in range(3):
        level1 = XmlTreeNode(
            name=f"section[{i+1}]",
            tag="section",
            value="",
            attributes={"id": f"sec{i+1}", "type": "content"},
            path=f"/root[1]/section[{i+1}]",
            line_number=i+2
        )
        root.children.append(level1)
        
        # Level 2 nodes
        for j in range(2 + i):  # Variable number of children
            level2 = XmlTreeNode(
                name=f"item[{j+1}]",
                tag="item",
                value=f"Content {j+1}",
                attributes={"name": f"item{j+1}"},
                path=f"/root[1]/section[{i+1}]/item[{j+1}]",
                line_number=(i+2)*10 + j
            )
            level1.children.append(level2)
    
    return root


class TestControlPanel(QWidget):
    """Control panel for testing metro navigator features"""
    
    def __init__(self, navigator: MetroNavigatorWindow, parent=None):
        super().__init__(parent)
        self.navigator = navigator
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup control panel UI"""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("<h2>Metro Navigator Visual Test</h2>")
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(
            "<b>Test Instructions:</b><br>"
            "1. Verify station nodes are visible and styled correctly<br>"
            "2. Verify connection lines connect parent-child nodes<br>"
            "3. Test zoom with Ctrl+Mouse Wheel<br>"
            "4. Test pan by dragging the canvas<br>"
            "5. Click nodes to select and highlight paths<br>"
            "6. Use buttons below to test zoom controls"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Zoom controls
        zoom_layout = QHBoxLayout()
        
        zoom_in_btn = QPushButton("Zoom In (150%)")
        zoom_in_btn.clicked.connect(lambda: self.navigator.view.set_zoom(1.5))
        zoom_layout.addWidget(zoom_in_btn)
        
        zoom_out_btn = QPushButton("Zoom Out (50%)")
        zoom_out_btn.clicked.connect(lambda: self.navigator.view.set_zoom(0.5))
        zoom_layout.addWidget(zoom_out_btn)
        
        zoom_normal_btn = QPushButton("Zoom Normal (100%)")
        zoom_normal_btn.clicked.connect(lambda: self.navigator.view.set_zoom(1.0))
        zoom_layout.addWidget(zoom_normal_btn)
        
        layout.addLayout(zoom_layout)
        
        # Fit to view button
        fit_btn = QPushButton("Fit to View")
        fit_btn.clicked.connect(self.navigator.view.fit_to_view)
        layout.addWidget(fit_btn)
        
        # Test extreme zoom
        extreme_zoom_layout = QHBoxLayout()
        
        min_zoom_btn = QPushButton("Min Zoom (25%)")
        min_zoom_btn.clicked.connect(lambda: self.navigator.view.set_zoom(0.25))
        extreme_zoom_layout.addWidget(min_zoom_btn)
        
        max_zoom_btn = QPushButton("Max Zoom (400%)")
        max_zoom_btn.clicked.connect(lambda: self.navigator.view.set_zoom(4.0))
        extreme_zoom_layout.addWidget(max_zoom_btn)
        
        layout.addLayout(extreme_zoom_layout)
        
        # Status
        self.status_label = QLabel("<b>Status:</b> Ready for testing")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Current zoom display
        self.zoom_display = QLabel(f"Current Zoom: 100%")
        layout.addWidget(self.zoom_display)
        
        # Connect to zoom changes
        self.navigator.view.zoom_changed.connect(self._on_zoom_changed)
        
        layout.addStretch()
    
    def _on_zoom_changed(self, zoom: float):
        """Update zoom display"""
        self.zoom_display.setText(f"Current Zoom: {int(zoom * 100)}%")
        
        # Update status based on zoom level
        if zoom < 0.5:
            mode = "Simplified (name only)"
        elif zoom > 1.5:
            mode = "Detailed (name + attributes + children)"
        else:
            mode = "Normal (name + child badge)"
        
        self.status_label.setText(f"<b>Status:</b> Zoom at {int(zoom * 100)}% - Display mode: {mode}")


class VisualTestWindow(QMainWindow):
    """Main window for visual testing"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Metro Navigator Visual Test")
        self.resize(1400, 900)
        
        # Create test data
        test_tree = create_test_xml_tree()
        
        # Create navigator
        self.navigator = MetroNavigatorWindow(test_tree)
        
        # Create control panel
        self.control_panel = TestControlPanel(self.navigator)
        
        # Setup layout
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        
        # Add navigator (main area)
        layout.addWidget(self.navigator, stretch=3)
        
        # Add control panel (side)
        layout.addWidget(self.control_panel, stretch=1)
        
        # Show success message
        self.statusBar().showMessage("Visual test loaded successfully - Test all features!", 5000)


def main():
    """Run visual test"""
    app = QApplication(sys.argv)
    
    print("=" * 60)
    print("Metro Navigator Visual Test")
    print("=" * 60)
    print("\nThis test verifies:")
    print("  ✓ Station nodes render correctly")
    print("  ✓ Connection lines render correctly")
    print("  ✓ Zoom functionality (Ctrl+Mouse Wheel)")
    print("  ✓ Pan functionality (drag canvas)")
    print("  ✓ Node selection and path highlighting")
    print("  ✓ Adaptive detail display at different zoom levels")
    print("\nUse the control panel on the right to test zoom controls.")
    print("Close the window when testing is complete.")
    print("=" * 60)
    
    window = VisualTestWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
