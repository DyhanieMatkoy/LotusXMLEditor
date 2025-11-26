"""
Settings Dialog - Grouped key/value table with filter
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QLineEdit, QLabel, QPushButton,
                             QHeaderView, QSpinBox, QCheckBox, QWidget, QDialogButtonBox)
from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QColor


class SettingsDialog(QDialog):
    """Settings dialog with grouped key/value table and filter"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(700, 500)
        self.parent_window = parent
        
        # Settings structure: {group: {key: (label, type, default, description)}}
        self.settings_structure = {
            "Tree Updates": {
                "tree_update_debounce": ("Debounce Interval (ms)", "int", 5000, "Delay before updating tree after typing stops"),
            },
            "Auto-Hide": {
                "toolbar_autohide": ("Toolbar Auto-hide", "bool", True, "Automatically hide toolbar when not in use"),
                "tree_header_autohide": ("Tree Header Auto-hide", "bool", True, "Automatically hide tree level buttons when not in use"),
                "tree_column_header_autohide": ("Tree Column Header Auto-hide", "bool", True, "Automatically hide tree column headers when not in use"),
                "tab_bar_autohide": ("Tab Bar Auto-hide", "bool", True, "Automatically hide tab bar when only one tab is open"),
            },
            "Debug": {
                "debug_mode": ("Debug Mode", "bool", False, "Enable console debug messages"),
            },
        }
        
        # Load current values
        self.current_values = {}
        self._load_current_values()
        
        # Build UI
        self._setup_ui()
        
        # Populate table
        self._populate_table()
    
    def _load_current_values(self):
        """Load current values from QSettings"""
        settings = QSettings("LotusXmlEditor", "Settings")
        
        for group, items in self.settings_structure.items():
            for key, (label, value_type, default, desc) in items.items():
                if value_type == "bool":
                    value = settings.value(key, default, type=bool)
                elif value_type == "int":
                    value = settings.value(key, default, type=int)
                else:
                    value = settings.value(key, default)
                self.current_values[key] = value
    
    def _setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout()
        
        # Filter box
        filter_layout = QHBoxLayout()
        filter_label = QLabel("Filter:")
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Type to filter settings...")
        self.filter_input.textChanged.connect(self._apply_filter)
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.filter_input)
        layout.addLayout(filter_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Group", "Setting", "Value", "Description"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self._save_and_close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def _populate_table(self):
        """Populate the table with settings"""
        self.table.setRowCount(0)
        row = 0
        
        for group, items in self.settings_structure.items():
            for key, (label, value_type, default, desc) in items.items():
                self.table.insertRow(row)
                
                # Group
                group_item = QTableWidgetItem(group)
                group_item.setFlags(group_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                group_item.setBackground(QColor(240, 240, 240))
                self.table.setItem(row, 0, group_item)
                
                # Setting name
                name_item = QTableWidgetItem(label)
                name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 1, name_item)
                
                # Value widget
                value = self.current_values.get(key, default)
                if value_type == "bool":
                    widget = QCheckBox()
                    widget.setChecked(value)
                    widget.setProperty("setting_key", key)
                    container = QWidget()
                    container_layout = QHBoxLayout()
                    container_layout.addWidget(widget)
                    container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    container_layout.setContentsMargins(0, 0, 0, 0)
                    container.setLayout(container_layout)
                    self.table.setCellWidget(row, 2, container)
                elif value_type == "int":
                    widget = QSpinBox()
                    widget.setMinimum(0)
                    widget.setMaximum(60000)
                    widget.setValue(value)
                    widget.setProperty("setting_key", key)
                    self.table.setCellWidget(row, 2, widget)
                else:
                    value_item = QTableWidgetItem(str(value))
                    value_item.setProperty("setting_key", key)
                    self.table.setItem(row, 2, value_item)
                
                # Description
                desc_item = QTableWidgetItem(desc)
                desc_item.setFlags(desc_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 3, desc_item)
                
                row += 1
        
        self.table.resizeRowsToContents()
    
    def _apply_filter(self):
        """Apply filter to table rows"""
        filter_text = self.filter_input.text().lower()
        
        for row in range(self.table.rowCount()):
            # Check if any column contains the filter text
            show_row = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and filter_text in item.text().lower():
                    show_row = True
                    break
            
            self.table.setRowHidden(row, not show_row)
    
    def _save_and_close(self):
        """Save settings and close dialog"""
        settings = QSettings("LotusXmlEditor", "Settings")
        
        # Collect values from table
        for row in range(self.table.rowCount()):
            # Get the setting key
            widget = self.table.cellWidget(row, 2)
            if widget:
                # It's a widget (checkbox or spinbox)
                if isinstance(widget, QWidget) and widget.layout():
                    # It's a container with a checkbox
                    checkbox = widget.layout().itemAt(0).widget()
                    if isinstance(checkbox, QCheckBox):
                        key = checkbox.property("setting_key")
                        value = checkbox.isChecked()
                        settings.setValue(key, value)
                        self.current_values[key] = value
                elif isinstance(widget, QSpinBox):
                    key = widget.property("setting_key")
                    value = widget.value()
                    settings.setValue(key, value)
                    self.current_values[key] = value
            else:
                # It's a table item
                item = self.table.item(row, 2)
                if item:
                    key = item.property("setting_key")
                    value = item.text()
                    settings.setValue(key, value)
                    self.current_values[key] = value
        
        # Apply settings to parent window
        if self.parent_window:
            self._apply_settings_to_parent()
        
        self.accept()
    
    def _apply_settings_to_parent(self):
        """Apply settings to parent window immediately"""
        parent = self.parent_window
        
        # Tree update debounce
        if hasattr(parent, 'tree_update_timer'):
            debounce = self.current_values.get('tree_update_debounce', 5000)
            # Timer interval will be applied on next trigger
            parent.tree_update_debounce_interval = debounce
        
        # Auto-hide settings
        if hasattr(parent, 'auto_hide_manager'):
            toolbar_autohide = self.current_values.get('toolbar_autohide', True)
            tree_header_autohide = self.current_values.get('tree_header_autohide', True)
            tree_column_header_autohide = self.current_values.get('tree_column_header_autohide', True)
            tab_bar_autohide = self.current_values.get('tab_bar_autohide', True)
            
            # Update auto-hide manager
            parent.auto_hide_manager.toolbar_enabled = toolbar_autohide
            parent.auto_hide_manager.tree_header_enabled = tree_header_autohide
            parent.auto_hide_manager.tree_column_header_enabled = tree_column_header_autohide
            parent.auto_hide_manager.tab_bar_enabled = tab_bar_autohide
            
            # Update menu actions if they exist
            if hasattr(parent, 'toggle_toolbar_autohide_action'):
                parent.toggle_toolbar_autohide_action.blockSignals(True)
                parent.toggle_toolbar_autohide_action.setChecked(toolbar_autohide)
                parent.toggle_toolbar_autohide_action.blockSignals(False)
            
            if hasattr(parent, 'toggle_tree_header_autohide_action'):
                parent.toggle_tree_header_autohide_action.blockSignals(True)
                parent.toggle_tree_header_autohide_action.setChecked(tree_header_autohide)
                parent.toggle_tree_header_autohide_action.blockSignals(False)
            
            if hasattr(parent, 'toggle_tree_column_header_autohide_action'):
                parent.toggle_tree_column_header_autohide_action.blockSignals(True)
                parent.toggle_tree_column_header_autohide_action.setChecked(tree_column_header_autohide)
                parent.toggle_tree_column_header_autohide_action.blockSignals(False)
            
            if hasattr(parent, 'toggle_tab_bar_autohide_action'):
                parent.toggle_tab_bar_autohide_action.blockSignals(True)
                parent.toggle_tab_bar_autohide_action.setChecked(tab_bar_autohide)
                parent.toggle_tab_bar_autohide_action.blockSignals(False)
        
        # Debug mode
        debug_mode = self.current_values.get('debug_mode', False)
        if hasattr(parent, 'debug_mode'):
            parent.debug_mode = debug_mode
        
        # Update status
        if hasattr(parent, 'status_label'):
            parent.status_label.setText("Settings applied")
