#!/usr/bin/env python3
"""
Combine Dialog - Dialog for combining multiple XML files
Integrates with file navigation for quick file selection
"""

import os
import xml.etree.ElementTree as ET
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QLabel, QLineEdit, QGroupBox, QCheckBox,
    QFileDialog, QMessageBox, QProgressBar, QComboBox, QSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from PyQt6.Qsci import QsciScintilla, QsciLexerXML


class CombineWorkerThread(QThread):
    """Worker thread for combining XML files"""
    progress_updated = pyqtSignal(int)
    status_updated = pyqtSignal(str)
    finished_successfully = pyqtSignal(str)  # Combined XML content
    error_occurred = pyqtSignal(str)
    
    def __init__(self, file_paths, combine_method, root_element_name):
        super().__init__()
        self.file_paths = file_paths
        self.combine_method = combine_method
        self.root_element_name = root_element_name
    
    def run(self):
        """Run the combine operation"""
        try:
            if self.combine_method == "merge_roots":
                result = self._merge_root_elements()
            elif self.combine_method == "wrap_in_root":
                result = self._wrap_in_new_root()
            elif self.combine_method == "concatenate":
                result = self._concatenate_files()
            else:
                result = self._merge_root_elements()  # Default
            
            self.finished_successfully.emit(result)
            
        except Exception as e:
            self.error_occurred.emit(str(e))
    
    def _merge_root_elements(self):
        """Merge all root elements into a single root"""
        self.status_updated.emit("Merging root elements...")
        
        # Create new root element
        root = ET.Element(self.root_element_name or "combined")
        
        total_files = len(self.file_paths)
        for i, file_path in enumerate(self.file_paths):
            self.status_updated.emit(f"Processing {os.path.basename(file_path)}...")
            
            try:
                tree = ET.parse(file_path)
                file_root = tree.getroot()
                
                # Add all children of the file's root to our combined root
                for child in file_root:
                    root.append(child)
                
                # Update progress
                progress = int((i + 1) / total_files * 100)
                self.progress_updated.emit(progress)
                
            except ET.ParseError as e:
                self.status_updated.emit(f"Warning: Could not parse {file_path}: {e}")
                continue
        
        # Convert to string with proper formatting
        ET.indent(root, space="  ", level=0)
        return ET.tostring(root, encoding='unicode', xml_declaration=True)
    
    def _wrap_in_new_root(self):
        """Wrap each file's content in a new root element"""
        self.status_updated.emit("Wrapping files in new root...")
        
        # Create new root element
        root = ET.Element(self.root_element_name or "combined")
        
        total_files = len(self.file_paths)
        for i, file_path in enumerate(self.file_paths):
            self.status_updated.emit(f"Processing {os.path.basename(file_path)}...")
            
            try:
                tree = ET.parse(file_path)
                file_root = tree.getroot()
                
                # Create a wrapper element for this file
                file_wrapper = ET.SubElement(root, "file")
                file_wrapper.set("source", os.path.basename(file_path))
                file_wrapper.append(file_root)
                
                # Update progress
                progress = int((i + 1) / total_files * 100)
                self.progress_updated.emit(progress)
                
            except ET.ParseError as e:
                self.status_updated.emit(f"Warning: Could not parse {file_path}: {e}")
                continue
        
        # Convert to string with proper formatting
        ET.indent(root, space="  ", level=0)
        return ET.tostring(root, encoding='unicode', xml_declaration=True)
    
    def _concatenate_files(self):
        """Simple concatenation of file contents"""
        self.status_updated.emit("Concatenating files...")
        
        combined_content = []
        combined_content.append('<?xml version="1.0" encoding="UTF-8"?>')
        combined_content.append(f'<{self.root_element_name or "combined"}>')
        
        total_files = len(self.file_paths)
        for i, file_path in enumerate(self.file_paths):
            self.status_updated.emit(f"Reading {os.path.basename(file_path)}...")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Remove XML declaration if present
                    lines = content.split('\n')
                    filtered_lines = [line for line in lines if not line.strip().startswith('<?xml')]
                    
                    combined_content.append(f'<!-- Content from {os.path.basename(file_path)} -->')
                    combined_content.extend(filtered_lines)
                
                # Update progress
                progress = int((i + 1) / total_files * 100)
                self.progress_updated.emit(progress)
                
            except Exception as e:
                self.status_updated.emit(f"Warning: Could not read {file_path}: {e}")
                continue
        
        combined_content.append(f'</{self.root_element_name or "combined"}>')
        return '\n'.join(combined_content)


class CombineDialog(QDialog):
    """Dialog for combining multiple XML files"""
    
    def __init__(self, file_paths=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Combine XML Files")
        self.setModal(True)
        self.resize(600, 500)
        
        self.file_paths = file_paths or []
        self.combined_content = ""
        
        self._setup_ui()
        self._populate_file_list()
    
    def _setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout()
        
        # File selection group
        file_group = QGroupBox("Files to Combine")
        file_layout = QVBoxLayout()
        
        # File list
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        file_layout.addWidget(self.file_list)
        
        # File management buttons
        file_btn_layout = QHBoxLayout()
        
        add_files_btn = QPushButton("Add Files...")
        add_files_btn.clicked.connect(self._add_files)
        file_btn_layout.addWidget(add_files_btn)
        
        remove_files_btn = QPushButton("Remove Selected")
        remove_files_btn.clicked.connect(self._remove_selected_files)
        file_btn_layout.addWidget(remove_files_btn)
        
        clear_files_btn = QPushButton("Clear All")
        clear_files_btn.clicked.connect(self._clear_all_files)
        file_btn_layout.addWidget(clear_files_btn)
        
        file_btn_layout.addStretch()
        file_layout.addLayout(file_btn_layout)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Combine options group
        options_group = QGroupBox("Combine Options")
        options_layout = QVBoxLayout()
        
        # Combine method
        method_layout = QHBoxLayout()
        method_layout.addWidget(QLabel("Combine Method:"))
        
        self.method_combo = QComboBox()
        self.method_combo.addItems([
            "Merge Root Elements",
            "Wrap in New Root",
            "Simple Concatenation"
        ])
        self.method_combo.setCurrentIndex(0)
        method_layout.addWidget(self.method_combo)
        method_layout.addStretch()
        
        options_layout.addLayout(method_layout)
        
        # Root element name
        root_layout = QHBoxLayout()
        root_layout.addWidget(QLabel("Root Element Name:"))
        
        self.root_name_edit = QLineEdit("combined")
        root_layout.addWidget(self.root_name_edit)
        root_layout.addStretch()
        
        options_layout.addLayout(root_layout)
        
        # Validation option
        self.validate_checkbox = QCheckBox("Validate XML after combining")
        self.validate_checkbox.setChecked(True)
        options_layout.addWidget(self.validate_checkbox)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Progress group
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Ready to combine files")
        self.status_label.setFont(QFont("Consolas", 9))
        progress_layout.addWidget(self.status_label)
        
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.combine_btn = QPushButton("Combine Files")
        self.combine_btn.clicked.connect(self._combine_files)
        button_layout.addWidget(self.combine_btn)
        
        self.preview_btn = QPushButton("Preview Result")
        self.preview_btn.clicked.connect(self._preview_result)
        self.preview_btn.setEnabled(False)
        button_layout.addWidget(self.preview_btn)
        
        save_btn = QPushButton("Save Combined")
        save_btn.clicked.connect(self._save_combined)
        save_btn.setEnabled(False)
        self.save_btn = save_btn
        button_layout.addWidget(save_btn)
        
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _populate_file_list(self):
        """Populate the file list with initial files"""
        for file_path in self.file_paths:
            self._add_file_to_list(file_path)
    
    def _add_file_to_list(self, file_path):
        """Add a file to the list widget"""
        item = QListWidgetItem()
        item.setText(f"{os.path.basename(file_path)} ({file_path})")
        item.setData(Qt.ItemDataRole.UserRole, file_path)
        self.file_list.addItem(item)
    
    def _add_files(self):
        """Add files using file dialog"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select XML Files", "", "XML Files (*.xml);;All Files (*.*)"
        )
        
        for file_path in files:
            if file_path not in self.file_paths:
                self.file_paths.append(file_path)
                self._add_file_to_list(file_path)
    
    def _remove_selected_files(self):
        """Remove selected files from the list"""
        selected_items = self.file_list.selectedItems()
        for item in selected_items:
            file_path = item.data(Qt.ItemDataRole.UserRole)
            if file_path in self.file_paths:
                self.file_paths.remove(file_path)
            self.file_list.takeItem(self.file_list.row(item))
    
    def _clear_all_files(self):
        """Clear all files from the list"""
        self.file_list.clear()
        self.file_paths.clear()
    
    def _combine_files(self):
        """Start the combine operation"""
        if len(self.file_paths) < 2:
            QMessageBox.warning(self, "Insufficient Files", "Please select at least 2 files to combine.")
            return
        
        # Get combine method
        method_map = {
            0: "merge_roots",
            1: "wrap_in_root", 
            2: "concatenate"
        }
        combine_method = method_map[self.method_combo.currentIndex()]
        root_element_name = self.root_name_edit.text().strip() or "combined"
        
        # Setup progress
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.combine_btn.setEnabled(False)
        
        # Start worker thread
        self.worker = CombineWorkerThread(self.file_paths, combine_method, root_element_name)
        self.worker.progress_updated.connect(self.progress_bar.setValue)
        self.worker.status_updated.connect(self.status_label.setText)
        self.worker.finished_successfully.connect(self._on_combine_finished)
        self.worker.error_occurred.connect(self._on_combine_error)
        self.worker.start()
    
    def _on_combine_finished(self, combined_content):
        """Handle successful combine completion"""
        self.combined_content = combined_content
        self.progress_bar.setVisible(False)
        self.combine_btn.setEnabled(True)
        self.preview_btn.setEnabled(True)
        self.save_btn.setEnabled(True)
        self.status_label.setText(f"Successfully combined {len(self.file_paths)} files")
        
        # Validate if requested
        if self.validate_checkbox.isChecked():
            self._validate_combined_xml()
    
    def _on_combine_error(self, error_message):
        """Handle combine error"""
        self.progress_bar.setVisible(False)
        self.combine_btn.setEnabled(True)
        self.status_label.setText(f"Error: {error_message}")
        QMessageBox.critical(self, "Combine Error", f"Failed to combine files:\n{error_message}")
    
    def _validate_combined_xml(self):
        """Validate the combined XML"""
        try:
            ET.fromstring(self.combined_content)
            self.status_label.setText(self.status_label.text() + " (Valid XML)")
        except ET.ParseError as e:
            self.status_label.setText(self.status_label.text() + f" (Invalid XML: {e})")
            QMessageBox.warning(self, "Validation Warning", f"The combined XML is not valid:\n{e}")
    
    def _preview_result(self):
        """Preview the combined result"""
        if not self.combined_content:
            QMessageBox.information(self, "No Content", "Please combine files first.")
            return
        
        preview_dialog = QDialog(self)
        preview_dialog.setWindowTitle("Combined XML Preview")
        preview_dialog.resize(700, 500)
        
        layout = QVBoxLayout()
        
        preview_text = QsciScintilla()
        preview_text.setUtf8(True)
        preview_text.setText(self.combined_content)
        preview_text.setReadOnly(True)
        
        # Configure lexer for XML highlighting
        lexer = QsciLexerXML()
        lexer.setDefaultFont(QFont("Consolas", 10))
        preview_text.setLexer(lexer)
        
        # Simple dark theme adjustments if needed (assuming standard theme for now)
        # But let's stick to defaults or match the dialog style if it's dark
        # The dialog has no specific dark theme applied in the init, 
        # so we assume default or system theme. 
        # However, split_dialog had dark theme. 
        # Let's check if main window applies theme globally.
        # For now, basic highlighting is a win.
        
        layout.addWidget(preview_text)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(preview_dialog.accept)
        layout.addWidget(close_btn)
        
        preview_dialog.setLayout(layout)
        preview_dialog.exec()
    
    def _save_combined(self):
        """Save the combined XML to a file"""
        if not self.combined_content:
            QMessageBox.information(self, "No Content", "Please combine files first.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Combined XML", "combined.xml", "XML Files (*.xml);;All Files (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.combined_content)
                
                QMessageBox.information(self, "Success", f"Combined XML saved to:\n{file_path}")
                self.accept()  # Close dialog
                
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to save file:\n{e}")
    
    def get_combined_content(self):
        """Get the combined XML content"""
        return self.combined_content
    
    def set_file_paths(self, file_paths):
        """Set the file paths to combine"""
        self.file_paths = file_paths[:]
        self.file_list.clear()
        self._populate_file_list()