"""
About Dialog for Lotus XML Editor
Shows application information with copyable paths
"""

import sys
import os
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QLineEdit, QGroupBox, QApplication)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from version import __version__, __build_date__, __app_name__


class AboutDialog(QDialog):
    """About dialog showing application and file information"""
    
    def __init__(self, parent=None, current_file_path=None):
        super().__init__(parent)
        self.current_file_path = current_file_path
        self.setWindowTitle(f"About {__app_name__}")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Application name and version
        title_label = QLabel(f"{__app_name__}")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        version_label = QLabel(f"Version: {__version__}")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)
        
        build_label = QLabel(f"Build Date: {__build_date__}")
        build_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(build_label)
        
        layout.addSpacing(10)
        
        # Executable path group
        exe_group = QGroupBox("Application Path")
        exe_layout = QVBoxLayout()
        
        exe_path = sys.executable
        exe_text = QLineEdit(exe_path)
        exe_text.setReadOnly(True)
        exe_layout.addWidget(exe_text)
        
        exe_copy_btn = QPushButton("Copy to Clipboard")
        exe_copy_btn.clicked.connect(lambda: self._copy_to_clipboard(exe_path))
        exe_layout.addWidget(exe_copy_btn)
        
        exe_group.setLayout(exe_layout)
        layout.addWidget(exe_group)
        
        # Current file path group
        file_group = QGroupBox("Current File")
        file_layout = QVBoxLayout()
        
        if self.current_file_path:
            file_path = os.path.abspath(self.current_file_path)
        else:
            file_path = "No file opened"
            
        file_text = QLineEdit(file_path)
        file_text.setReadOnly(True)
        file_layout.addWidget(file_text)
        
        file_copy_btn = QPushButton("Copy to Clipboard")
        file_copy_btn.setEnabled(bool(self.current_file_path))
        file_copy_btn.clicked.connect(lambda: self._copy_to_clipboard(file_path))
        file_layout.addWidget(file_copy_btn)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        layout.addStretch()
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setDefault(True)
        layout.addWidget(close_btn)
        
        self.setLayout(layout)
        
    def _copy_to_clipboard(self, text):
        """Copy text to clipboard"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        
        # Show brief feedback
        sender = self.sender()
        if sender:
            original_text = sender.text()
            sender.setText("Copied!")
            sender.setEnabled(False)
            
            # Reset after 1 second
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(1000, lambda: self._reset_button(sender, original_text))
    
    def _reset_button(self, button, original_text):
        """Reset button text and state"""
        if button:
            button.setText(original_text)
            button.setEnabled(True)
