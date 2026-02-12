from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QTableWidget, QTableWidgetItem, QGroupBox, QScrollArea, 
    QWidget, QPushButton, QHeaderView, QFrame, QToolButton
)
from PyQt6.QtCore import Qt, pyqtSignal
from models import XmlTreeNode

class ObjectNodeForm(QDialog):
    """
    A Windows form to display an XML object node with edit fields, 
    tables, and expand/collapse controls.
    """
    jump_to_source_requested = pyqtSignal(object) # XmlTreeNode

    def __init__(self, xml_node: XmlTreeNode, parent=None):
        super().__init__(parent)
        self.root_node = xml_node
        self.current_node = xml_node
        self.history = [] # Stack of nodes
        
        self.setWindowTitle(f"Object Viewer - {xml_node.tag}")
        self.resize(800, 600)
        
        # Main layout
        self.main_layout = QVBoxLayout(self)
        
        # --- Toolbar (Back, Breadcrumbs, Jump) ---
        toolbar_layout = QHBoxLayout()
        
        # Back Button
        self.back_btn = QPushButton("Back")
        self.back_btn.clicked.connect(self.go_back)
        self.back_btn.setEnabled(False)
        self.back_btn.setFixedWidth(60)
        toolbar_layout.addWidget(self.back_btn)
        
        # Breadcrumbs Container
        self.breadcrumbs_layout = QHBoxLayout()
        self.breadcrumbs_layout.setContentsMargins(0, 0, 0, 0)
        self.breadcrumbs_layout.setSpacing(2)
        
        # Scroll area for breadcrumbs (in case deep nesting)
        bread_scroll = QScrollArea()
        bread_scroll.setWidgetResizable(True)
        bread_scroll.setFixedHeight(40)
        bread_scroll.setFrameShape(QFrame.Shape.NoFrame)
        bread_container = QWidget()
        bread_container.setLayout(self.breadcrumbs_layout)
        bread_scroll.setWidget(bread_container)
        toolbar_layout.addWidget(bread_scroll, stretch=1)
        
        # Jump to Source Button
        self.jump_btn = QPushButton("Jump to Source")
        self.jump_btn.clicked.connect(self._on_jump_clicked)
        toolbar_layout.addWidget(self.jump_btn)
        
        self.main_layout.addLayout(toolbar_layout)
        
        # --- Content Area ---
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        
        self.main_layout.addWidget(self.scroll_area)
        
        # Close button
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.close_btn)
        self.main_layout.addLayout(btn_layout)
        
        # Initial Render
        self._refresh_ui()

    def navigate_to(self, node: XmlTreeNode):
        """Navigate deeper into a node"""
        self.history.append(self.current_node)
        self.current_node = node
        self._refresh_ui()

    def go_back(self):
        """Go back to previous node"""
        if self.history:
            self.current_node = self.history.pop()
            self._refresh_ui()

    def _on_jump_clicked(self):
        """Emit signal to jump to source"""
        self.jump_to_source_requested.emit(self.current_node)

    def _refresh_ui(self):
        """Update UI to reflect current_node state"""
        # 1. Update Toolbar
        self.back_btn.setEnabled(bool(self.history))
        self._update_breadcrumbs()
        
        # 2. Clear Content
        # Safely delete widgets
        while self.scroll_layout.count():
            item = self.scroll_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
                
        # 3. Build Content
        self._build_ui(self.current_node, self.scroll_layout)
        self.setWindowTitle(f"Object Viewer - {self.current_node.tag}")

    def _update_breadcrumbs(self):
        """Rebuild breadcrumbs layout"""
        # Clear existing
        while self.breadcrumbs_layout.count():
            item = self.breadcrumbs_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        
        # Build path: history + current
        path = self.history + [self.current_node]
        
        for i, node in enumerate(path):
            # Separator
            if i > 0:
                self.breadcrumbs_layout.addWidget(QLabel(">"))
            
            # Button
            btn = QPushButton(node.tag)
            btn.setFlat(True)
            # We need to capture the target state for this breadcrumb
            # If clicked, we should pop history until we reach this node
            # Or easier: navigate to it (but requires careful history management)
            
            # Correct approach: Clicking a breadcrumb means "Go back to this point"
            # So we set current to this node, and history becomes path[:i]
            
            btn.clicked.connect(lambda checked, idx=i: self._on_breadcrumb_clicked(idx))
            
            # Highlight current
            if i == len(path) - 1:
                btn.setStyleSheet("font-weight: bold; color: blue;")
                
            self.breadcrumbs_layout.addWidget(btn)
            
        self.breadcrumbs_layout.addStretch()

    def _on_breadcrumb_clicked(self, index):
        """Handle breadcrumb click"""
        # The path is history + current
        full_path = self.history + [self.current_node]
        
        # Target node is full_path[index]
        target_node = full_path[index]
        
        if target_node == self.current_node:
            return
            
        # New history is everything before index
        self.history = full_path[:index]
        self.current_node = target_node
        self._refresh_ui()

    def _build_ui(self, node: XmlTreeNode, parent_layout):
        """Recursively build UI based on node structure"""
        
        # 1. Display Attributes
        if node.attributes:
            attr_group = QGroupBox("Attributes")
            attr_layout = QVBoxLayout()
            for key, value in node.attributes.items():
                row = QHBoxLayout()
                row.addWidget(QLabel(f"{key}:"))
                edit = QLineEdit(value)
                edit.setReadOnly(True) # Read-only for now
                row.addWidget(edit)
                attr_layout.addLayout(row)
            attr_group.setLayout(attr_layout)
            parent_layout.addWidget(attr_group)

        # 2. Analyze Children
        children_by_tag = {}
        for child in node.children:
            if child.tag not in children_by_tag:
                children_by_tag[child.tag] = []
            children_by_tag[child.tag].append(child)
            
        # 3. Process Children
        for tag, children in children_by_tag.items():
            if len(children) > 1:
                # Render as Table if multiple items
                self._render_table(tag, children, parent_layout)
            else:
                # Render as Single Field or Complex Object
                child = children[0]
                if not child.children:
                    # Simple Field
                    row = QHBoxLayout()
                    row.addWidget(QLabel(f"{child.tag}:"))
                    edit = QLineEdit(child.value or "")
                    edit.setReadOnly(True)
                    row.addWidget(edit)
                    parent_layout.addLayout(row)
                else:
                    # Complex Object
                    self._render_complex_object(child, parent_layout)

    def _render_table(self, tag, nodes, parent_layout):
        """Render a list of nodes as a table"""
        group = QGroupBox(f"{tag} List ({len(nodes)} items)")
        layout = QVBoxLayout()
        
        # Add help label
        layout.addWidget(QLabel("Double-click a row to view details"))
        
        # Determine columns (union of all child tags/attributes)
        columns = set()
        for node in nodes:
            # Add attributes as columns
            for attr in node.attributes:
                columns.add(f"@{attr}")
            # Add simple children as columns
            for child in node.children:
                if not child.children:
                    columns.add(child.tag)
        
        sorted_columns = sorted(list(columns))
        
        table = QTableWidget()
        table.setRowCount(len(nodes))
        table.setColumnCount(len(sorted_columns))
        table.setHorizontalHeaderLabels(sorted_columns)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        
        for r, node in enumerate(nodes):
            # Store node reference in the first item
            
            for c, col in enumerate(sorted_columns):
                val = ""
                if col.startswith("@"):
                    val = node.attributes.get(col[1:], "")
                else:
                    # Find child with this tag
                    for child in node.children:
                        if child.tag == col:
                            val = child.value or ""
                            break
                
                item = QTableWidgetItem(val)
                item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable) # Read-only
                
                if c == 0:
                    item.setData(Qt.ItemDataRole.UserRole, node)
                    
                table.setItem(r, c, item)
        
        # Double click to navigate
        table.itemDoubleClicked.connect(self._on_table_row_double_clicked)
                
        layout.addWidget(table)
        group.setLayout(layout)
        parent_layout.addWidget(group)

    def _on_table_row_double_clicked(self, item):
        """Handle table row double click"""
        # Get row
        row = item.row()
        # Get first item in row to retrieve node
        first_item = item.tableWidget().item(row, 0)
        node = first_item.data(Qt.ItemDataRole.UserRole)
        
        if node:
            self.navigate_to(node)

    def _render_complex_object(self, node, parent_layout):
        """Render a complex object with option to drill down"""
        # Custom collapsible implementation using a button and a widget
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        header_layout = QHBoxLayout()
        
        toggle_btn = QPushButton(f"▼ {node.tag}")
        toggle_btn.setCheckable(True)
        toggle_btn.setChecked(True)
        toggle_btn.setStyleSheet("text-align: left; font-weight: bold;")
        header_layout.addWidget(toggle_btn, stretch=1)
        
        # Add Navigate/Open Button
        nav_btn = QPushButton("Open")
        nav_btn.setFixedWidth(60)
        nav_btn.setToolTip("Open in full view")
        nav_btn.clicked.connect(lambda: self.navigate_to(node))
        header_layout.addWidget(nav_btn)
        
        layout.addLayout(header_layout)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_widget.setVisible(True)
        
        # Recursively build UI for this node
        # Note: If it's too deep, maybe we shouldn't recurse infinitely here?
        # But user can collapse it.
        self._build_ui(node, content_layout)
        
        toggle_btn.toggled.connect(lambda checked: self._toggle_collapse(toggle_btn, content_widget, node.tag, checked))
        
        layout.addWidget(content_widget)
        parent_layout.addWidget(container)

    def _toggle_collapse(self, btn, widget, tag, checked):
        """Handle collapse/expand"""
        widget.setVisible(checked)
        arrow = "▼" if checked else "▶"
        btn.setText(f"{arrow} {tag}")
