#!/usr/bin/env python3
"""
File Navigator Widget - Dockable file navigation window
Provides file tree view with quick selection and combine dialog integration
"""

import os
from PyQt6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, 
    QTreeWidgetItem, QPushButton, QLineEdit, QLabel, QFileDialog,
    QMessageBox, QMenu, QHeaderView, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal, QDir, QFileInfo
from PyQt6.QtGui import QAction, QIcon


class FileTreeWidget(QTreeWidget):
    """Custom tree widget for file navigation"""
    file_selected = pyqtSignal(str)  # Emits file path when file is selected
    file_double_clicked = pyqtSignal(str)  # Emits file path when file is double-clicked
    
    def __init__(self, status_label=None):
        super().__init__()
        self.status_label = status_label
        self.setHeaderLabels(["Name", "Size", "Modified"])
        self.setRootIsDecorated(True)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        
        # Configure column widths
        self.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        
        # Store current directory
        self.current_directory = None
        
        # Connect signals
        self.itemClicked.connect(self._on_item_clicked)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.itemExpanded.connect(self._on_item_expanded)
        
        # Setup context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        self.current_root_path = ""
    
    def _on_item_clicked(self, item, column):
        """Handle item click"""
        file_path = getattr(item, 'file_path', None)
        if file_path:
            if os.path.isfile(file_path):
                self.file_selected.emit(file_path)
            elif os.path.isdir(file_path) and item.text(0) == "📁 ..":
                # Parent directory navigation
                self.populate_directory(file_path)
    
    def _on_item_double_clicked(self, item, column):
        """Handle item double click"""
        file_path = getattr(item, 'file_path', None)
        if file_path:
            if os.path.isfile(file_path):
                self.file_double_clicked.emit(file_path)
            elif os.path.isdir(file_path):
                # Navigate to directory
                self.populate_directory(file_path)
    
    def _on_item_expanded(self, item):
        """Handle item expansion for lazy loading"""
        file_path = getattr(item, 'file_path', None)
        if file_path and os.path.isdir(file_path):
            # Check if this item has placeholder children
            if item.childCount() == 1 and item.child(0).text(0) == "Loading...":
                # Remove placeholder
                item.removeChild(item.child(0))
                # Populate with actual contents
                self._populate_directory_level(file_path, item)
    
    def _show_context_menu(self, position):
        """Show context menu"""
        item = self.itemAt(position)
        if not item or not hasattr(item, 'file_path'):
            return
        
        menu = QMenu(self)
        
        if os.path.isfile(item.file_path):
            open_action = QAction("Open", self)
            open_action.triggered.connect(lambda: self.file_double_clicked.emit(item.file_path))
            menu.addAction(open_action)
            
            menu.addSeparator()
            
            copy_path_action = QAction("Copy Path", self)
            copy_path_action.triggered.connect(lambda: self._copy_path_to_clipboard(item.file_path))
            menu.addAction(copy_path_action)
        
        elif os.path.isdir(item.file_path):
            expand_action = QAction("Expand All", self)
            expand_action.triggered.connect(lambda: self._expand_all_children(item))
            menu.addAction(expand_action)
            
            collapse_action = QAction("Collapse All", self)
            collapse_action.triggered.connect(lambda: self._collapse_all_children(item))
            menu.addAction(collapse_action)
        
        menu.exec(self.mapToGlobal(position))
    
    def _copy_path_to_clipboard(self, file_path):
        """Copy file path to clipboard"""
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(file_path)
    
    def _expand_all_children(self, item):
        """Expand all children of an item"""
        item.setExpanded(True)
        for i in range(item.childCount()):
            child = item.child(i)
            if hasattr(child, 'file_path') and os.path.isdir(child.file_path):
                self._expand_all_children(child)
    
    def _collapse_all_children(self, item):
        """Collapse all children of an item"""
        for i in range(item.childCount()):
            child = item.child(i)
            if hasattr(child, 'file_path') and os.path.isdir(child.file_path):
                self._collapse_all_children(child)
        item.setExpanded(False)
    
    def populate_directory(self, directory_path):
        """Populate the tree with files and directories from the given path"""
        self.clear()
        self.current_directory = directory_path
        self.current_root_path = directory_path
        
        if not os.path.exists(directory_path) or not os.path.isdir(directory_path):
            return
        
        try:
            # Add parent directory item if not at root
            parent_dir = os.path.dirname(directory_path)
            if parent_dir != directory_path:  # Not at root
                parent_item = QTreeWidgetItem(self)
                parent_item.setText(0, "📁 ..")
                parent_item.setText(1, "<UP>")
                parent_item.setText(2, "Parent Directory")
                parent_item.file_path = parent_dir
            
            # Populate current directory
            self._populate_directory_level(directory_path, self)
            
        except Exception as e:
            if self.status_label:
                self.status_label.setText(f"Error loading directory: {str(e)}")
    
    def _populate_directory_level(self, directory_path, parent_item):
        """Populate a single directory level with lazy loading for subdirectories"""
        try:
            entries = os.listdir(directory_path)
            # Sort: directories first, then files, both alphabetically
            entries.sort(key=lambda x: (not os.path.isdir(os.path.join(directory_path, x)), x.lower()))
            
            for entry in entries:
                if entry.startswith('.'):
                    continue  # Skip hidden files
                
                entry_path = os.path.join(directory_path, entry)
                
                if os.path.isdir(entry_path):
                    # Directory - add with placeholder for lazy loading
                    dir_item = QTreeWidgetItem(parent_item)
                    dir_item.setText(0, f"📁 {entry}")
                    dir_item.setText(1, "<DIR>")
                    dir_item.file_path = entry_path
                    
                    # Get modification time
                    try:
                        mtime = os.path.getmtime(entry_path)
                        from datetime import datetime
                        mod_time = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
                        dir_item.setText(2, mod_time)
                    except:
                        dir_item.setText(2, "Unknown")
                    
                    # Add placeholder child to make it expandable
                    placeholder = QTreeWidgetItem(dir_item)
                    placeholder.setText(0, "Loading...")
                
                elif entry.lower().endswith(('.xml', '.txt', '.json', '.csv', '.xsd', '.xsl', '.xslt')):
                    # Supported files
                    file_item = QTreeWidgetItem(parent_item)
                    file_item.setText(0, f"📄 {entry}")
                    file_item.file_path = entry_path
                    
                    # Get file size
                    try:
                        size = os.path.getsize(entry_path)
                        if size < 1024:
                            size_str = f"{size} B"
                        elif size < 1024 * 1024:
                            size_str = f"{size / 1024:.1f} KB"
                        else:
                            size_str = f"{size / (1024 * 1024):.1f} MB"
                        file_item.setText(1, size_str)
                    except:
                        file_item.setText(1, "Unknown")
                    
                    # Get modification time
                    try:
                        mtime = os.path.getmtime(entry_path)
                        from datetime import datetime
                        mod_time = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
                        file_item.setText(2, mod_time)
                    except:
                        file_item.setText(2, "Unknown")
        
        except PermissionError:
            if self.status_label:
                self.status_label.setText(f"Permission denied: {directory_path}")
        except Exception as e:
            if self.status_label:
                self.status_label.setText(f"Error reading directory: {str(e)}")
    
    def refresh_current_directory(self):
        """Refresh the current directory"""
        if self.current_root_path:
            self.populate_directory(self.current_root_path)


class FileNavigatorWidget(QDockWidget):
    """Dockable file navigation widget"""
    file_opened = pyqtSignal(str)  # Emits when a file should be opened
    combine_requested = pyqtSignal(list)  # Emits list of files for combine dialog
    
    def __init__(self, parent=None):
        super().__init__("File Navigator", parent)
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)
        
        # Main widget
        main_widget = QWidget()
        layout = QVBoxLayout()
        
        # Toolbar
        toolbar_layout = QHBoxLayout()
        
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Enter directory path...")
        self.path_edit.returnPressed.connect(self._navigate_to_path)
        toolbar_layout.addWidget(self.path_edit)
        
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_directory)
        toolbar_layout.addWidget(browse_btn)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh_directory)
        toolbar_layout.addWidget(refresh_btn)
        
        layout.addLayout(toolbar_layout)
        
        # Create file tree with status label reference
        self.file_tree = FileTreeWidget()
        self.file_tree.file_selected.connect(self._on_file_selected)
        self.file_tree.file_double_clicked.connect(self._on_file_double_clicked)
        layout.addWidget(self.file_tree)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        open_btn = QPushButton("Open Selected")
        open_btn.clicked.connect(self._open_selected_file)
        action_layout.addWidget(open_btn)
        
        combine_btn = QPushButton("Combine Files")
        combine_btn.clicked.connect(self._show_combine_dialog)
        action_layout.addWidget(combine_btn)
        
        layout.addLayout(action_layout)
        
        main_widget.setLayout(layout)
        self.setWidget(main_widget)
        
        # Initialize with current working directory to show XML files by default
        current_dir = os.getcwd()
        self.set_current_directory(current_dir)
        
        self.selected_files = []  # Track selected files for combine
    
    def _navigate_to_path(self):
        """Navigate to the path in the text field"""
        path = self.path_edit.text().strip()
        if os.path.exists(path) and os.path.isdir(path):
            self.file_tree.populate_directory(path)
        else:
            QMessageBox.warning(self, "Invalid Path", f"The path '{path}' does not exist or is not a directory.")
    
    def _browse_directory(self):
        """Browse for directory"""
        directory = QFileDialog.getExistingDirectory(self, "Select Directory", self.path_edit.text())
        if directory:
            self.path_edit.setText(directory)
            self.file_tree.populate_directory(directory)
    
    def _refresh_directory(self):
        """Refresh current directory"""
        self.file_tree.refresh_current_directory()
    
    def _on_file_selected(self, file_path):
        """Handle file selection"""
        # Update selected files list for combine functionality
        if file_path not in self.selected_files:
            self.selected_files.append(file_path)
    
    def _on_file_double_clicked(self, file_path):
        """Handle file double click - open the file"""
        if file_path.lower().endswith(('.xml', '.txt', '.json', '.csv')):
            self.file_opened.emit(file_path)
        else:
            QMessageBox.information(self, "File Type", "Only XML, TXT, JSON, and CSV files can be opened in the editor.")
    
    def _open_selected_file(self):
        """Open the currently selected file"""
        current_item = self.file_tree.currentItem()
        if current_item and hasattr(current_item, 'file_path'):
            if os.path.isfile(current_item.file_path):
                self._on_file_double_clicked(current_item.file_path)
            else:
                QMessageBox.information(self, "Selection", "Please select a file to open.")
        else:
            QMessageBox.information(self, "Selection", "Please select a file to open.")
    
    def _show_combine_dialog(self):
        """Emit selected XML files for combining"""
        # Prefer currently selected items in the tree
        selected_items = self.file_tree.selectedItems()
        xml_files = []
        if selected_items:
            for item in selected_items:
                file_path = getattr(item, 'file_path', None)
                if file_path and os.path.isfile(file_path) and file_path.lower().endswith('.xml'):
                    xml_files.append(file_path)
        else:
            # Fallback to previously clicked files list
            for file_path in self.selected_files:
                if os.path.isfile(file_path) and file_path.lower().endswith('.xml'):
                    xml_files.append(file_path)
        
        # Deduplicate while preserving order
        seen = set()
        xml_files = [fp for fp in xml_files if not (fp in seen or seen.add(fp))]
        
        if len(xml_files) >= 2:
            self.combine_requested.emit(xml_files)
        elif len(xml_files) == 1:
            QMessageBox.information(self, "Selection", "Select at least two XML files to combine.")
        else:
            QMessageBox.information(self, "No Files", "No XML files selected for combining.")
    
    def set_current_directory(self, directory_path):
        """Set the current directory programmatically"""
        if os.path.exists(directory_path) and os.path.isdir(directory_path):
            self.path_edit.setText(directory_path)
            self.file_tree.populate_directory(directory_path)