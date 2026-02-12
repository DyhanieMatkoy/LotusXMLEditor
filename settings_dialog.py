"""
Settings Dialog - Grouped key/value table with filter
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QLineEdit, QLabel, QPushButton,
                             QHeaderView, QSpinBox, QCheckBox, QWidget, QDialogButtonBox, QMessageBox,
                             QToolTip, QFontComboBox)
from PyQt6.QtCore import Qt, QSettings, QFile, QTextStream
from PyQt6.QtGui import QColor, QCursor, QFont
import os
import re
import win_integration


class SettingsDialog(QDialog):
    """Settings dialog with grouped key/value table and filter"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(700, 500)
        self.parent_window = parent
        
        # Settings structure: {group: {key: (label, type, default, description)}}
        self.settings_structure = {
            "Editor": {
                "show_line_numbers": ("Show Line Numbers", "bool", False, "Display line numbers in the editor"),
                "save_cursor_position": ("Save Cursor Position", "bool", True, "Remember cursor position and selection for recent files"),
                "save_tree_state": ("Save Tree State", "bool", False, "Remember selected node and expansion in XML Tree"),
                "store_settings_in_file_dir": ("Store Settings in File Directory", "bool", False, "Save .visxml_state sidecar file in the same directory as the opened file"),
                "editor_font_family": ("Editor Font Family", "font", "Consolas", "Font family for the editor"),
                "editor_font_size": ("Editor Font Size", "int", 11, "Font size for the editor (pt)"),
            },
            "Tree Updates": {
                "auto_rebuild_tree": ("Auto Rebuild Tree", "bool", True, "Automatically rebuild tree when text changes"),
                "tree_update_debounce": ("Debounce Interval (ms)", "int", 5000, "Delay before updating tree after typing stops"),
            },
            "Auto-Hide": {
                "toolbar_autohide": ("Toolbar Auto-hide", "bool", True, "Automatically hide toolbar when not in use"),
                "tree_header_autohide": ("Tree Header Auto-hide", "bool", True, "Automatically hide tree level buttons when not in use"),
                "tree_column_header_autohide": ("Tree Column Header Auto-hide", "bool", True, "Automatically hide tree column headers when not in use"),
                "tab_bar_autohide": ("Tab Bar Auto-hide", "bool", True, "Automatically hide tab bar when only one tab is open"),
            },
            "Zip Archive": {
                "zip_default_file_pattern": ("Default File Pattern", "str", "ExchangeRules.xml", "Filename pattern to select by default in Zip archives"),
            },
            "Debug": {
                "debug_mode": ("Debug Mode", "bool", False, "Enable console debug messages"),
            },
        }
        
        # Load current values
        self.current_values = {}
        self._load_current_values()
        
        # Help state
        self.help_mode = False
        self.help_content = {}
        self._load_help_content()
        
        # Build UI
        self._setup_ui()
        
        # Populate table
        self._populate_table()
    
    def _load_help_content(self):
        """Load help content from markdown file"""
        self.help_content = {}
        try:
            # Assume doc/ is in the same directory as this file or one level up?
            # Based on LS, doc is at root, settings_dialog.py is at root.
            help_path = os.path.join(os.path.dirname(__file__), "doc", "SETTINGS_HELP.md")
            if not os.path.exists(help_path):
                # Try relative path if running from root
                help_path = "doc/SETTINGS_HELP.md"
            
            if os.path.exists(help_path):
                with open(help_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # Parse markdown line by line
                current_title = None
                current_desc = []
                
                for line in lines:
                    stripped = line.strip()
                    if not stripped:
                        # Append blank line to description if we are in a section
                        if current_title:
                            current_desc.append("")
                        continue
                        
                    if stripped.startswith('##'):
                        # Section header, save previous and reset
                        if current_title:
                            self.help_content[current_title] = "\n".join(current_desc).strip()
                            current_title = None
                            current_desc = []
                        continue
                        
                    # Check for **Title** on a single line
                    # We assume setting names are wrapped in ** and are on their own line
                    if stripped.startswith('**') and stripped.endswith('**') and len(stripped) > 4:
                        # Save previous
                        if current_title:
                            self.help_content[current_title] = "\n".join(current_desc).strip()
                        
                        current_title = stripped[2:-2].strip()
                        current_desc = []
                    else:
                        if current_title:
                            current_desc.append(stripped)
                
                # Save last entry
                if current_title:
                    self.help_content[current_title] = "\n".join(current_desc).strip()
                    
        except Exception as e:
            print(f"Error loading settings help: {e}")

    def _load_current_values(self):
        """Load current values from QSettings"""
        # Match main.py: QSettings("visxml.net", "LotusXmlEditor")
        settings = QSettings("visxml.net", "LotusXmlEditor")
        
        for group, items in self.settings_structure.items():
            for key, (label, value_type, default, desc) in items.items():
                # Prepend flags/ if it matches known flags from main.py
                # Based on analysis: settings_structure keys need adaptation or mapping
                # However, for simplicity, we'll map them here or just change the keys in settings_structure.
                # Changing keys in settings_structure is cleaner.
                
                # But wait, the keys in settings_structure are used as identifiers.
                # If I change them there, I need to check if they are used elsewhere.
                # In this file, they are used to set 'setting_key' property on widgets.
                # And in _save_and_close, that property is used to save.
                # And in _apply_settings_to_parent, keys are used to look up values.
                
                # So if I change keys in settings_structure, I must update _apply_settings_to_parent too.
                
                # Let's adjust settings_structure keys directly to match main.py expectations where possible,
                # OR handle the mapping in load/save.
                # Given main.py uses "flags/toolbar_autohide" etc., it's better to use those keys directly.
                
                # Actually, main.py uses "flags/..." for these.
                read_key = key
                if key in ["toolbar_autohide", "tree_header_autohide", 
                           "tree_column_header_autohide", "tab_bar_autohide", "debug_mode"]:
                    read_key = f"flags/{key}"
                elif key in ["show_line_numbers", "auto_rebuild_tree", 
                             "save_cursor_position", "save_tree_state", "store_settings_in_file_dir"]:
                    read_key = f"flags/{key}"
                
                if value_type == "bool":
                    value = settings.value(read_key, default, type=bool)
                elif value_type == "int":
                    value = settings.value(read_key, default, type=int)
                else:
                    value = settings.value(read_key, default)
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
        
        # Help button
        self.help_btn = QPushButton("[?]")
        self.help_btn.setFixedWidth(40)
        self.help_btn.setCheckable(True)
        self.help_btn.setToolTip("Toggle Help Mode")
        self.help_btn.clicked.connect(self._toggle_help_mode)
        filter_layout.addWidget(self.help_btn)
        
        layout.addLayout(filter_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setMouseTracking(True)
        self.table.cellEntered.connect(self._on_cell_entered)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Group", "Setting", "Value", "Description"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)
        
        # System Integration
        sys_layout = QHBoxLayout()
        sys_label = QLabel("System Integration:")
        self.reg_btn = QPushButton("Register Context Menu")
        self.unreg_btn = QPushButton("Unregister Context Menu")
        
        self.reg_btn.clicked.connect(self._register_context_menu)
        self.unreg_btn.clicked.connect(self._unregister_context_menu)
        
        sys_layout.addWidget(sys_label)
        sys_layout.addWidget(self.reg_btn)
        sys_layout.addWidget(self.unreg_btn)
        sys_layout.addStretch()
        layout.addLayout(sys_layout)

        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self._save_and_close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def _toggle_help_mode(self, checked):
        """Toggle help mode"""
        self.help_mode = checked
        if checked:
            self.setCursor(Qt.CursorShape.WhatsThisCursor)
        else:
            self.unsetCursor()
            
    def _on_cell_entered(self, row, column):
        """Handle mouse hover over cells"""
        if not self.help_mode:
            return
            
        # Get the setting name from column 1 (Setting Name)
        name_item = self.table.item(row, 1)
        if not name_item:
            return
            
        setting_name = name_item.text()
        
        # Look up help
        if setting_name in self.help_content:
            help_text = self.help_content[setting_name]
            # Convert simple markdown to HTML for tooltip
            html = self._markdown_to_html(help_text, setting_name)
            QToolTip.showText(QCursor.pos(), html, self.table)
            
    def _markdown_to_html(self, text, title):
        """Convert simple markdown to HTML for tooltip"""
        html = f"<h3>{title}</h3>"
        
        lines = text.split('\n')
        in_list = False
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('- '):
                if not in_list:
                    html += "<ul>"
                    in_list = True
                html += f"<li>{line[2:]}</li>"
            else:
                if in_list:
                    html += "</ul>"
                    in_list = False
                
                # Bold
                line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
                # Code
                line = re.sub(r'`(.*?)`', r'<code style="background-color: #eee;">\1</code>', line)
                
                html += f"<p>{line}</p>"
        
        if in_list:
            html += "</ul>"
            
        # Style
        style = """
        <style>
            h3 { color: #2c3e50; margin-bottom: 5px; }
            p { margin: 5px 0; }
            ul { margin: 5px 0; padding-left: 20px; }
            li { margin: 2px 0; }
        </style>
        """
        return style + html

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
                elif value_type == "font":
                    widget = QFontComboBox()
                    widget.setCurrentFont(QFont(value))
                    widget.setProperty("setting_key", key)
                    # We need a container to center/adjust if needed, but default is usually okay.
                    # QFontComboBox is wide, let's just add it directly.
                    self.table.setCellWidget(row, 2, widget)
                else:
                    value_item = QTableWidgetItem(str(value))
                    value_item.setData(Qt.ItemDataRole.UserRole, key)  # Store key in UserRole data
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
        # Match main.py: QSettings("visxml.net", "LotusXmlEditor")
        settings = QSettings("visxml.net", "LotusXmlEditor")
        
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
                        
                        save_key = key
                        if key in ["toolbar_autohide", "tree_header_autohide", 
                                   "tree_column_header_autohide", "tab_bar_autohide", 
                                   "debug_mode", "show_line_numbers", "auto_rebuild_tree",
                                   "save_cursor_position", "save_tree_state", "store_settings_in_file_dir"]:
                             save_key = f"flags/{key}"
                             
                        settings.setValue(save_key, value)
                        self.current_values[key] = value
                elif isinstance(widget, QSpinBox):
                    key = widget.property("setting_key")
                    value = widget.value()
                    # Spinbox usually int settings, check if it needs prefix
                    # Currently only tree_update_debounce, which main.py reads as raw key (not flags/)
                    settings.setValue(key, value)
                    self.current_values[key] = value
                elif isinstance(widget, QFontComboBox):
                    key = widget.property("setting_key")
                    value = widget.currentFont().family()
                    settings.setValue(key, value)
                    self.current_values[key] = value
            else:
                # It's a table item
                item = self.table.item(row, 2)
                if item:
                    key = item.data(Qt.ItemDataRole.UserRole)
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
        
        # Line numbers
        show_line_numbers = self.current_values.get('show_line_numbers', False)
        if hasattr(parent, 'apply_line_numbers_to_all_editors'):
            parent.apply_line_numbers_to_all_editors(show_line_numbers)
        
        # Auto rebuild tree
        auto_rebuild_tree = self.current_values.get('auto_rebuild_tree', True)
        if hasattr(parent, 'auto_rebuild_tree'):
            parent.auto_rebuild_tree = auto_rebuild_tree
        
        # Tree update debounce
        if hasattr(parent, 'tree_update_timer'):
            debounce = self.current_values.get('tree_update_debounce', 5000)
            # Timer interval will be applied on next trigger
            parent.tree_update_debounce_interval = debounce
        
        # Font settings
        if hasattr(parent, 'apply_font_settings'):
            font_family = self.current_values.get('editor_font_family', 'Consolas')
            font_size = self.current_values.get('editor_font_size', 11)
            parent.apply_font_settings(font_family, font_size)

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

    def _register_context_menu(self):
        """Register context menu handler"""
        success, msg = win_integration.register_context_menu()
        if success:
            QMessageBox.information(self, "Context Menu", msg)
        else:
            QMessageBox.warning(self, "Context Menu", f"Failed to register:\n{msg}")

    def _unregister_context_menu(self):
        """Unregister context menu handler"""
        success, msg = win_integration.unregister_context_menu()
        if success:
            QMessageBox.information(self, "Context Menu", msg)
        else:
            QMessageBox.warning(self, "Context Menu", f"Failed to unregister:\n{msg}")
