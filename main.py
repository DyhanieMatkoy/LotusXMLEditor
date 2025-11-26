#!/usr/bin/env python3
"""
Lotus Xml Editor - Python Version
A modern XML editor with tree view, syntax highlighting, and validation
"""

import sys
import os
from version import __version__, __build_date__, __app_name__
from PyQt6.QtWidgets import (QApplication, QMainWindow, QSplitter, QTreeWidget, 
                             QTreeWidgetItem, QTextEdit, QStatusBar, QMenuBar, 
                             QToolBar, QVBoxLayout, QHBoxLayout, QWidget, 
                             QTabWidget, QListWidget, QListWidgetItem, QPushButton, QLabel, 
                             QFileDialog, QMessageBox, QLineEdit, QCheckBox, QComboBox, QToolButton,
                             QDialog, QDialogButtonBox, QSpinBox, QFrame,
                             QHeaderView, QTreeWidgetItemIterator, QMenu, QDockWidget, QProgressBar)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QDateTime, QSettings
from PyQt6.QtGui import QAction, QIcon, QFont, QSyntaxHighlighter, QTextCharFormat, QColor, QTextCursor, QPainter
import re

from xml_service import XmlService
from models import XmlFileModel, XmlTreeNode, XmlValidationResult
from highlighter import XmlHighlighter
from syntax import LanguageDefinition, LanguageRegistry, LanguageProfileCompiler, RuleHighlighter, load_udl_xml
from split_dialog import XmlSplitConfigDialog
from file_navigator import FileNavigatorWidget
from combine_dialog import CombineDialog
from multicolumn_tree import MultiColumnTreeWindow
from structure_diagram import StructureDiagramWindow
from auto_hide_manager import AutoHideManager
from exchange_manager import (
    parse_exchange_tags_from_path,
    parse_exchange_tags_from_content,
    identify_edited_file,
    save_pair_metadata,
    load_pair_metadata,
    package_zip,
    compute_exchange_dir,
)


class XmlTreeWidget(QTreeWidget):
    """Custom tree widget for displaying XML structure"""
    node_selected = pyqtSignal(object)
    
    def __init__(self, status_label=None):
        super().__init__()
        self.status_label = status_label
        self.hide_leaves_enabled = True  # default: hide leaf nodes
        self.use_friendly_labels = True  # default: show friendly labels
        self.setHeaderLabels(["Element", "Value"])
        self.setAlternatingRowColors(True)
        self.itemClicked.connect(self._on_item_clicked)
        
        # Quick Win #2: Enable uniform row heights for faster rendering (20-40% faster)
        self.setUniformRowHeights(True)
        
        # Level collapse buttons
        self.level_buttons = []
        self.max_depth = 0

        # Level header mount container reference (assigned by MainWindow)
        self.header_container = None
        self.current_header_widget = None
        
        # Enable column stretching
        self.setRootIsDecorated(True)
        self.setAllColumnsShowFocus(True)
        self.header().setStretchLastSection(False)
        self.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        # Default: hide value column when leaves are hidden
        try:
            self.setColumnHidden(1, self.hide_leaves_enabled)
            self._update_header_resize_modes()
        except Exception:
            pass

    def compute_display_name(self, xml_node):
        """Compute label for a node based on current mode."""
        if not xml_node:
            return ""
        if not self.use_friendly_labels:
            attr = getattr(xml_node, 'attributes', {}) or {}
            attr_string = " ".join([f'{k}="{v}"' for k, v in attr.items()])
            return f"{xml_node.tag} [{attr_string}]" if attr_string else f"{xml_node.tag}"

        display_name = xml_node.name
        preferred_name = None
        try:
            for child in getattr(xml_node, 'children', []) or []:
                if getattr(child, 'tag', '') in ("Наименование", "Имя", "Name") and getattr(child, 'value', None):
                    text = child.value.strip()
                    if text:
                        preferred_name = text
                        break
        except Exception:
            preferred_name = None

        if preferred_name:
            attr = getattr(xml_node, 'attributes', {}) or {}
            attr_string = " ".join([f'{k}="{v}"' for k, v in attr.items()])
            display_name = f"{preferred_name} ({xml_node.tag} [{attr_string}])" if attr_string else f"{preferred_name} ({xml_node.tag})"
        return display_name

    def refresh_labels(self):
        """Refresh all labels according to mode without rebuilding structure."""
        try:
            iterator = QTreeWidgetItemIterator(self)
            while iterator.value():
                item = iterator.value()
                if item and hasattr(item, 'xml_node') and item.xml_node:
                    item.setText(0, self.compute_display_name(item.xml_node))
                iterator += 1
            self.viewport().update()
        except Exception as e:
            print(f"Label refresh error: {e}")

    def set_hide_leaves(self, hide: bool):
        """Enable or disable leaf hiding and apply immediately."""
        self.hide_leaves_enabled = bool(hide)
        # Hide value column when leaves are hidden
        try:
            self.setColumnHidden(1, self.hide_leaves_enabled)
            self._update_header_resize_modes()
        except Exception:
            pass
        self.apply_hide_leaves_filter()

    def _update_header_resize_modes(self):
        """Adjust header resize behavior based on visibility of Value column."""
        try:
            if self.isColumnHidden(1):
                # Stretch Element column to take full width when Value hidden
                self.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            else:
                # Interactive first column, stretch second to fill remaining
                self.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
                self.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        except Exception:
            pass

    def apply_hide_leaves_filter(self):
        """Apply leaf hiding across the tree without altering structure."""
        try:
            root_count = self.topLevelItemCount()
            stack = [self.topLevelItem(i) for i in range(root_count)]
            while stack:
                item = stack.pop()
                if item is None:
                    continue
                is_leaf = item.childCount() == 0
                item.setHidden(self.hide_leaves_enabled and is_leaf)
                for i in range(item.childCount()):
                    stack.append(item.child(i))
            self.viewport().update()
        except Exception:
            pass
    
    def resizeEvent(self, event):
        """Handle resize events to maintain proportional column widths"""
        super().resizeEvent(event)
        total_width = self.viewport().width()
        if total_width > 0:
            if self.isColumnHidden(1):
                # Element column fills the entire width when Value is hidden
                self.setColumnWidth(0, total_width)
                # Ensure hidden column width doesn't consume space
                try:
                    self.setColumnWidth(1, 0)
                except Exception:
                    pass
            else:
                # Element column gets 40%, Value column gets 60%
                self.setColumnWidth(0, int(total_width * 0.4))
                self.setColumnWidth(1, int(total_width * 0.6))
    
    def _truncate_value(self, value: str, max_words: int = 2) -> str:
        """Truncate value to maximum number of words with ellipsis"""
        if not value:
            return ""
        
        # Split by whitespace and take first max_words
        words = value.strip().split()
        if len(words) <= max_words:
            return value
        
        # Join first max_words and add ellipsis
        return " ".join(words[:max_words]) + "..."
        
    def _on_item_clicked(self, item, column):
        """Handle tree item click"""
        if hasattr(item, 'xml_node'):
            self.node_selected.emit(item.xml_node)
    
    def create_level_buttons(self, max_depth):
        """Create level collapse buttons
        Safely clears previously created buttons to prevent errors when their underlying C++ objects were already deleted.
        """
        self.max_depth = max_depth
        
        # Clear existing buttons safely to avoid errors when their parent widget was destroyed
        # Accessing a Python wrapper after its underlying C++ object was deleted can raise:
        # "wrapped C/C++ object of type QPushButton has been deleted".
        for button in list(self.level_buttons):
            try:
                if button is not None:
                    # Try to detach from any parent if still valid
                    try:
                        button.setParent(None)
                    except Exception:
                        pass
                    # Schedule deletion if still valid
                    try:
                        button.deleteLater()
                    except Exception:
                        pass
            except Exception:
                # Ignore any errors due to already-deleted C++ objects
                pass
        self.level_buttons.clear()
        
        # Create header widget for buttons
        header_widget = QWidget()
        header_widget.setMaximumHeight(24)  # Constrain height
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(2, 1, 2, 1)  # Reduced margins
        header_layout.setSpacing(2)  # Reduced spacing
        
        # Add collapse all button
        collapse_all_btn = QPushButton("All")  # Shortened text
        collapse_all_btn.clicked.connect(self.collapse_all)
        collapse_all_btn.setFixedSize(35, 20)  # Smaller button
        collapse_all_btn.setStyleSheet("font-size: 9px; padding: 1px;")
        header_layout.addWidget(collapse_all_btn)
        
        # Add level buttons
        level_label = QLabel("Lvl:")  # Shortened label
        level_label.setStyleSheet("font-size: 9px;")
        header_layout.addWidget(level_label)
        for level in range(1, max_depth + 1):
            btn = QPushButton(str(level))
            btn.setFixedSize(22, 20)  # Smaller buttons
            btn.setStyleSheet("font-size: 9px; padding: 1px; background-color: #505050;")
            btn.clicked.connect(lambda checked, l=level: self.collapse_level(l))
            header_layout.addWidget(btn)
            self.level_buttons.append(btn)
        
        header_layout.addStretch()
        header_widget.setLayout(header_layout)
        
        # If a header_container has been provided, mount the header_widget there for visibility
        try:
            container = getattr(self, 'header_container', None)
            if container is not None:
                layout = container.layout()
                if layout is None:
                    layout = QHBoxLayout()
                    layout.setContentsMargins(0, 0, 0, 0)
                    container.setLayout(layout)
                # Clear existing
                for i in reversed(range(layout.count())):
                    item = layout.itemAt(i)
                    w = item.widget()
                    if w is not None:
                        layout.removeWidget(w)
                        try:
                            w.setParent(None)
                        except Exception:
                            pass
                        try:
                            w.deleteLater()
                        except Exception:
                            pass
                layout.addWidget(header_widget)
                self.current_header_widget = header_widget
        except Exception:
            pass
        
        return header_widget
    
    def collapse_level(self, level):
        """Collapse all items at specific level"""
        def collapse_items_at_level(item, current_level):
            if current_level == level:
                item.setExpanded(False)
            else:
                for i in range(item.childCount()):
                    child = item.child(i)
                    collapse_items_at_level(child, current_level + 1)
        
        # Start from root items
        for i in range(self.topLevelItemCount()):
            root_item = self.topLevelItem(i)
            collapse_items_at_level(root_item, 1)
    
    def collapse_all(self):
        """Collapse all items"""
        self.collapseAll()
    
    def expand_to_level(self, level):
        """Expand items to specific level"""
        def expand_items_to_level(item, current_level):
            if current_level < level:
                item.setExpanded(True)
                for i in range(item.childCount()):
                    child = item.child(i)
                    expand_items_to_level(child, current_level + 1)
            else:
                item.setExpanded(False)
        
        # Start from root items
        for i in range(self.topLevelItemCount()):
            root_item = self.topLevelItem(i)
            expand_items_to_level(root_item, 1)
    
    def populate_tree(self, xml_content: str, show_progress=True):
        """Populate tree with XML structure"""
        self.clear()
        service = XmlService()
        
        # Quick Win #1: Disable visual updates during tree building (30-50% faster)
        self.setUpdatesEnabled(False)
        
        # Progress tracking
        progress_dialog = None
        
        # For large files, use a more memory-efficient approach
        if len(xml_content) > 1024 * 1024:  # 1MB threshold
            if show_progress:
                # Create progress dialog
                progress_dialog = QProgressBar()
                progress_dialog.setRange(0, 0)  # Indeterminate progress
                progress_dialog.setTextVisible(True)
                progress_dialog.setFormat("Building tree for large file...")
                
                # Add to status bar temporarily
                main_window = self.window()
                if hasattr(main_window, 'status_bar'):
                    main_window.status_bar.addWidget(progress_dialog)
                    QApplication.processEvents()
            
            if self.status_label:
                self.status_label.setText("Building tree for large file...")
                QApplication.processEvents()
            
            # Parse XML incrementally
            try:
                import xml.etree.ElementTree as ET
                parser = ET.XMLParser(target=ET.TreeBuilder(), encoding='utf-8')
                parser.feed(xml_content.encode('utf-8'))
                root = parser.close()
                
                # Build tree incrementally
                root_node = service._element_to_tree_node(root)
                
                # Add items to tree with progress updates
                if root_node:
                    self._add_tree_items_large(None, root_node)
                    self.expandToDepth(2)  # Only expand first 2 levels for large files
                    # Apply leaf hiding after population
                    self.apply_hide_leaves_filter()
                    
                    if self.status_label:
                        self.status_label.setText("Large file loaded successfully")
                
            except Exception as e:
                QMessageBox.warning(self, "Large File Warning", 
                                  f"Large file loaded but tree building failed: {str(e)}\n"
                                  f"The file content is available in the editor.")
            finally:
                # Remove progress dialog
                if progress_dialog:
                    main_window = self.window()
                    if hasattr(main_window, 'status_bar'):
                        main_window.status_bar.removeWidget(progress_dialog)
                    progress_dialog.deleteLater()
                # Re-enable updates after large file processing
                self.setUpdatesEnabled(True)
        else:
            # Normal processing for smaller files
            root_node = service.build_xml_tree(xml_content)
            
            if root_node:
                self._add_tree_items(None, root_node)
                self.expandAll()
                
                # Calculate max depth and create level buttons
                max_depth = self._calculate_max_depth(root_node)
                if max_depth > 0:
                    self.create_level_buttons(max_depth)
                # Apply leaf hiding after population
                self.apply_hide_leaves_filter()
                # Re-enable updates after normal file processing
                self.setUpdatesEnabled(True)
    
    def _calculate_max_depth(self, xml_node, current_depth=1):
        """Calculate maximum depth of XML tree"""
        max_depth = current_depth
        for child in xml_node.children:
            child_depth = self._calculate_max_depth(child, current_depth + 1)
            max_depth = max(max_depth, child_depth)
        return max_depth
    
    def _add_tree_items(self, parent_item, xml_node, parent_node=None):
        """Add tree items using iterative approach for better performance"""
        # Quick Win #6: Use iteration instead of recursion to reduce function call overhead
        stack = [(parent_item, xml_node, parent_node)]
        
        while stack:
            current_parent_item, current_xml_node, current_parent_node = stack.pop()
            
            item = QTreeWidgetItem()
            # Compute display name based on toggle
            item.setText(0, self.compute_display_name(current_xml_node))
            item.setText(1, self._truncate_value(current_xml_node.value) if current_xml_node.value else "")
            item.xml_node = current_xml_node
            item.parent_node = current_parent_node
            
            if current_parent_item is None:
                self.addTopLevelItem(item)
            else:
                current_parent_item.addChild(item)
            
            # Add children to stack in reverse order for correct processing
            for child in reversed(current_xml_node.children):
                stack.append((item, child, current_xml_node))
    
    def _add_tree_items_large(self, parent_item, xml_node, parent_node=None, max_children=100):
        """Add tree items for large files with performance optimizations"""
        item = QTreeWidgetItem()
        # Compute display name based on toggle
        item.setText(0, self.compute_display_name(xml_node))
        item.setText(1, self._truncate_value(xml_node.value) if xml_node.value else "")
        item.xml_node = xml_node
        item.parent_node = parent_node
        
        if parent_item is None:
            self.addTopLevelItem(item)
        else:
            parent_item.addChild(item)
        
        # For large files, limit the number of children processed initially
        children_to_process = xml_node.children[:max_children]
        
        for child in children_to_process:
            self._add_tree_items_large(item, child, xml_node, max_children)
        
        # Add placeholder if there are more children
        if len(xml_node.children) > max_children:
            placeholder = QTreeWidgetItem()
            placeholder.setText(0, f"... ({len(xml_node.children) - max_children} more items)")
            placeholder.setForeground(0, QColor("gray"))
            item.addChild(placeholder)
    
    def keyPressEvent(self, event):
        """Handle key press events for tree view"""
        # Check for F3 (Find Next)
        if event.key() == Qt.Key.Key_F3 and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            self.window().find_next()
            event.accept()
            return
        # Delete: hide current node recursively (visual filter only)
        if event.key() == Qt.Key.Key_Delete and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            current = self.currentItem()
            if current:
                self.hide_item_recursively(current)
                if self.status_label:
                    self.status_label.setText("Hidden selected node (recursive)")
            event.accept()
            return
        
        # Let parent handle other keys
        super().keyPressEvent(event)

    def hide_item_recursively(self, item):
        """Hide item and all descendants; does not alter XML model."""
        try:
            stack = [item]
            while stack:
                it = stack.pop()
                if it is None:
                    continue
                it.setHidden(True)
                for i in range(it.childCount()):
                    stack.append(it.child(i))
            self.viewport().update()
        except Exception as e:
            print(f"hide_item_recursively error: {e}")


class XmlEditorWidget(QTextEdit):
    """Custom text editor for XML with syntax highlighting"""
    content_changed = pyqtSignal()
    cursor_position_changed = pyqtSignal(int, int)
    
    def __init__(self):
        super().__init__()
        self.setFont(QFont("Consolas", 11))
        self.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        # Accept drag-and-drop for opening files
        self.setAcceptDrops(True)
        
        # Set up syntax highlighter
        self.highlighter = XmlHighlighter(self.document())
        
        # Track folded ranges as (start_line, end_line) tuples, 1-based inclusive
        self._folded_ranges = []

        # Connect signals
        self.textChanged.connect(self.content_changed)
        self.cursorPositionChanged.connect(self._on_cursor_changed)
        # Ensure content edits do not leave stale folded state
        self.textChanged.connect(self._on_content_edited_unfold_all)
        
        # Set up tab behavior
        self.setTabStopDistance(40)  # 4 spaces
    
    def _on_cursor_changed(self):
        """Handle cursor position change"""
        cursor = self.textCursor()
        line = cursor.blockNumber() + 1
        column = cursor.columnNumber() + 1
        self.cursor_position_changed.emit(line, column)

    def _on_content_edited_unfold_all(self):
        """Unfold everything when content changes to avoid desync."""
        try:
            if self._folded_ranges:
                self.unfold_all()
        except Exception:
            pass
    
    def get_content(self) -> str:
        """Get editor content"""
        return self.toPlainText()
    
    def set_content(self, content: str):
        """Set editor content"""
        self.setPlainText(content)

    # --- Folding helpers ---
    def fold_lines(self, start_line_one_based: int, end_line_one_based: int):
        """Fold by hiding inner lines between start and end (inclusive lines, inner only)."""
        try:
            if start_line_one_based <= 0 or end_line_one_based <= 0:
                return
            if end_line_one_based <= start_line_one_based:
                return
            doc = self.document()
            start = max(0, start_line_one_based - 1)
            end = max(0, end_line_one_based - 1)
            # Hide inner blocks, keep boundary lines visible
            blk = doc.findBlockByNumber(start + 1)
            while blk.isValid() and blk.blockNumber() < end:
                try:
                    blk.setVisible(False)
                except Exception:
                    break
                blk = blk.next()
            try:
                doc.documentLayout().update()
                self.viewport().update()
            except Exception:
                pass
            rng = (start_line_one_based, end_line_one_based)
            if rng not in self._folded_ranges:
                self._folded_ranges.append(rng)
        except Exception as e:
            print(f"Fold error: {e}")

    def unfold_lines(self, start_line_one_based: int, end_line_one_based: int):
        """Unfold by showing previously hidden inner lines between start and end."""
        try:
            if start_line_one_based <= 0 or end_line_one_based <= 0:
                return
            doc = self.document()
            start = max(0, start_line_one_based - 1)
            end = max(0, end_line_one_based - 1)
            blk = doc.findBlockByNumber(start + 1)
            while blk.isValid() and blk.blockNumber() < end:
                try:
                    blk.setVisible(True)
                except Exception:
                    break
                blk = blk.next()
            try:
                doc.documentLayout().update()
                self.viewport().update()
            except Exception:
                pass
            rng = (start_line_one_based, end_line_one_based)
            try:
                self._folded_ranges = [r for r in self._folded_ranges if r != rng]
            except Exception:
                pass
        except Exception as e:
            print(f"Unfold error: {e}")

    def unfold_all(self):
        """Unfold all hidden blocks."""
        try:
            doc = self.document()
            blk = doc.firstBlock()
            while blk.isValid():
                try:
                    blk.setVisible(True)
                except Exception:
                    break
                blk = blk.next()
            try:
                doc.documentLayout().update()
                self.viewport().update()
            except Exception:
                pass
            self._folded_ranges = []
        except Exception as e:
            print(f"Unfold-all error: {e}")
    
    def keyPressEvent(self, event):
        """Handle key press events for navigation, bookmarks, and tree sync"""
        # User-defined editing shortcuts
        try:
            # Ctrl+Shift+Up/Down: move selected lines up/down
            if event.modifiers() == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier):
                if event.key() == Qt.Key.Key_Up:
                    self._move_selected_lines(-1)
                    event.accept()
                    return
                elif event.key() == Qt.Key.Key_Down:
                    self._move_selected_lines(1)
                    event.accept()
                    return
                elif event.key() == Qt.Key.Key_BracketLeft:
                    # Fold current element at cursor
                    try:
                        self.window().fold_current_element()
                    except Exception as e:
                        print(f"Fold current element error: {e}")
                    event.accept()
                    return
                elif event.key() == Qt.Key.Key_BracketRight:
                    # Unfold current element at cursor
                    try:
                        self.window().unfold_current_element()
                    except Exception as e:
                        print(f"Unfold current element error: {e}")
                    event.accept()
                    return
            # Ctrl+L: delete current line or selected lines
            if event.key() == Qt.Key.Key_L and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self._delete_selected_lines()
                event.accept()
                return
            # Ctrl+/ : toggle line comment "//" at beginning
            if event.key() == Qt.Key.Key_Slash and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                self._toggle_line_comments(prefix="//")
                event.accept()
                return
            # Ctrl+Shift+0: Unfold all
            if event.key() == Qt.Key.Key_0 and event.modifiers() == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier):
                try:
                    self.unfold_all()
                except Exception:
                    pass
                event.accept()
                return
        except Exception as e:
            print(f"Custom shortcut error: {e}")

        # Numbered bookmarks: set with Ctrl+Shift+1..9, focus with Ctrl+1..9
        try:
            mods = event.modifiers()
            has_ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
            has_shift = bool(mods & Qt.KeyboardModifier.ShiftModifier)
            has_alt = bool(mods & Qt.KeyboardModifier.AltModifier)
            has_keypad = bool(mods & Qt.KeyboardModifier.KeypadModifier)

            # Map both digit keys and their shifted symbols to 1..9
            key = event.key()
            digit_map = {
                Qt.Key.Key_1: 1, Qt.Key.Key_2: 2, Qt.Key.Key_3: 3, Qt.Key.Key_4: 4,
                Qt.Key.Key_5: 5, Qt.Key.Key_6: 6, Qt.Key.Key_7: 7, Qt.Key.Key_8: 8,
                Qt.Key.Key_9: 9,
                # Shifted symbols on US layout
                Qt.Key.Key_Exclam: 1,      # Shift+1
                Qt.Key.Key_At: 2,          # Shift+2
                Qt.Key.Key_NumberSign: 3,  # Shift+3
                Qt.Key.Key_Dollar: 4,      # Shift+4
                Qt.Key.Key_Percent: 5,     # Shift+5
                Qt.Key.Key_AsciiCircum: 6, # Shift+6
                Qt.Key.Key_Ampersand: 7,   # Shift+7
                Qt.Key.Key_Asterisk: 8,    # Shift+8
                Qt.Key.Key_ParenLeft: 9    # Shift+9
            }
            if key in digit_map:
                digit = digit_map[key]
                if has_ctrl and has_shift and not has_alt:
                    # Set numbered bookmark
                    try:
                        self.window().set_numbered_bookmark(digit)
                    except Exception:
                        pass
                    event.accept()
                    return
                elif has_ctrl and not has_shift and not has_alt:
                    # Go to numbered bookmark (supports keypad too)
                    try:
                        self.window().goto_numbered_bookmark(digit)
                    except Exception:
                        pass
                    event.accept()
                    return
        except Exception:
            pass

        # Ctrl+Shift+B: Clear all bookmarks; Ctrl+B: Toggle bookmark at cursor
        try:
            if event.key() == Qt.Key.Key_B:
                mods = event.modifiers()
                has_ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)
                has_shift = bool(mods & Qt.KeyboardModifier.ShiftModifier)
                if has_ctrl and has_shift:
                    try:
                        self.window().clear_bookmarks()
                    except Exception:
                        pass
                    event.accept()
                    return
                elif has_ctrl:
                    try:
                        self.window().toggle_bookmark()
                    except Exception:
                        pass
                    event.accept()
                    return
        except Exception:
            pass
        # Check for Ctrl+T (Find in Tree)
        if event.key() == Qt.Key.Key_T and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.window().find_in_tree()
            event.accept()
            return
        
        # Check for F3 (Find Next)
        if event.key() == Qt.Key.Key_F3 and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            self.window().find_next()
            event.accept()
            return

        # F4 - Select XML node near cursor; repeated press selects parent
        if event.key() == Qt.Key.Key_F4 and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            try:
                self.window().select_xml_node_or_parent()
            except Exception as e:
                print(f"F4 selection error: {e}")
            event.accept()
            return

        # Ctrl+F4 - Select root element
        if event.key() == Qt.Key.Key_F4 and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            try:
                self.window().select_root_element()
            except Exception as e:
                print(f"Ctrl+F4 root selection error: {e}")
            event.accept()
            return

        # Ctrl+Alt+F4 - Cycle top-level elements
        if event.key() == Qt.Key.Key_F4 and event.modifiers() == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier):
            try:
                self.window().cycle_top_level_elements()
            except Exception as e:
                print(f"Ctrl+Alt+F4 top-level cycle error: {e}")
            event.accept()
            return

        # F5 - Move selected text to new tab and leave link
        if event.key() == Qt.Key.Key_F5 and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            try:
                self.window().move_selection_to_new_tab_with_link()
            except Exception as e:
                print(f"F5 move to tab error: {e}")
            event.accept()
            return

        # Shift+F5 - Replace link with edited text from separate tab
        if event.key() == Qt.Key.Key_F5 and event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
            try:
                self.window().replace_link_with_tab_content()
            except Exception as e:
                print(f"Shift+F5 replace link error: {e}")
            event.accept()
            return
        
        # Bookmark shortcuts per requested mapping
        if event.key() == Qt.Key.Key_F2:
            if event.modifiers() == Qt.KeyboardModifier.NoModifier:
                # F2 - Next bookmark (cycle)
                self.window().next_bookmark()
                event.accept()
                return
            elif event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
                # Shift+F2 - Previous bookmark
                self.window().prev_bookmark()
                event.accept()
                return

            elif event.modifiers() == (Qt.KeyboardModifier.AltModifier):
                # Ctrl+Alt+F2 - Set/toggle bookmark at current line

                self.window().toggle_bookmark()
                event.accept()
                return

        # Alt+Arrow keys - Tree-backed navigation
        if event.modifiers() == Qt.KeyboardModifier.AltModifier:
            try:
                if event.key() == Qt.Key.Key_Left:
                    self.window().navigate_tree_left()
                    event.accept()
                    return
                elif event.key() == Qt.Key.Key_Right:
                    self.window().navigate_tree_right()
                    event.accept()
                    return
                elif event.key() == Qt.Key.Key_Up:
                    self.window().navigate_tree_up()
                    event.accept()
                    return
                elif event.key() == Qt.Key.Key_Down:
                    self.window().navigate_tree_down()
                    event.accept()
                    return
            except Exception as e:
                print(f"Alt+Arrow navigation error: {e}")

        # Let the parent handle other keys
        super().keyPressEvent(event)

    def _get_selection_line_range(self):
        cur = self.textCursor()
        anchor_cur = QTextCursor(self.document())
        anchor_cur.setPosition(cur.anchor())
        start_line = min(cur.blockNumber(), anchor_cur.blockNumber())
        end_line = max(cur.blockNumber(), anchor_cur.blockNumber())
        has_sel = cur.hasSelection()
        return start_line, end_line, has_sel

    def _move_selected_lines(self, direction: int):
        """Move selected lines up (-1) or down (+1)."""
        try:
            content = self.toPlainText()
            lines = content.split('\n')
            start_line, end_line, has_sel = self._get_selection_line_range()
            if not lines:
                return
            if direction < 0:
                if start_line == 0:
                    return
                segment = lines[start_line:end_line+1]
                above = lines[start_line-1]
                lines = lines[:start_line-1] + segment + [above] + lines[end_line+1:]
                new_start = start_line - 1
                new_end = end_line - 1
            else:
                if end_line >= len(lines) - 1:
                    return
                segment = lines[start_line:end_line+1]
                below = lines[end_line+1]
                lines = lines[:start_line] + [below] + segment + lines[end_line+2:]
                new_start = start_line + 1
                new_end = end_line + 1
            self.setPlainText('\n'.join(lines))
            # Restore selection at moved lines
            new_cur = QTextCursor(self.document())
            new_cur.movePosition(QTextCursor.MoveOperation.Start)
            new_cur.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.MoveAnchor, max(0, new_start))
            new_cur.movePosition(QTextCursor.MoveOperation.StartOfLine)
            if has_sel:
                # Select full lines of the moved segment
                new_cur.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.KeepAnchor, max(0, new_end - new_start))
                new_cur.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
            self.setTextCursor(new_cur)
        except Exception as e:
            print(f"Move lines error: {e}")

    def _delete_selected_lines(self):
        """Delete current line or selected lines."""
        try:
            content = self.toPlainText()
            lines = content.split('\n')
            if not lines:
                return
            start_line, end_line, _ = self._get_selection_line_range()
            # Clamp indices
            start_line = max(0, min(start_line, len(lines)-1))
            end_line = max(0, min(end_line, len(lines)-1))
            # Delete range
            del lines[start_line:end_line+1]
            self.setPlainText('\n'.join(lines))
            # Position cursor at start_line (or last line if at end)
            target_line = min(start_line, max(0, len(lines)-1))
            cur = QTextCursor(self.document())
            cur.movePosition(QTextCursor.MoveOperation.Start)
            cur.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.MoveAnchor, max(0, target_line))
            cur.movePosition(QTextCursor.MoveOperation.StartOfLine)
            self.setTextCursor(cur)
        except Exception as e:
            print(f"Delete lines error: {e}")

    def _toggle_line_comments(self, prefix: str = "//"):
        """Toggle comment prefix at beginning of selected lines or current line."""
        try:
            content = self.toPlainText()
            lines = content.split('\n')
            if not lines:
                return
            start_line, end_line, _ = self._get_selection_line_range()
            # Determine whether to uncomment (all targeted lines already commented)
            def is_commented(s: str) -> bool:
                i = 0
                while i < len(s) and s[i].isspace():
                    i += 1
                return s[i:i+len(prefix)] == prefix
            target_range = range(start_line, end_line+1)
            uncomment = all(is_commented(lines[i]) for i in target_range if 0 <= i < len(lines))
            for i in target_range:
                if i < 0 or i >= len(lines):
                    continue
                s = lines[i]
                j = 0
                while j < len(s) and s[j].isspace():
                    j += 1
                if uncomment and s[j:j+len(prefix)] == prefix:
                    lines[i] = s[:j] + s[j+len(prefix):]
                else:
                    lines[i] = s[:j] + prefix + s[j:]
            self.setPlainText('\n'.join(lines))
            # Restore cursor selection to modified block range
            cur = QTextCursor(self.document())
            cur.movePosition(QTextCursor.MoveOperation.Start)
            cur.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.MoveAnchor, max(0, start_line))
            cur.movePosition(QTextCursor.MoveOperation.StartOfLine)
            cur.movePosition(QTextCursor.MoveOperation.Down, QTextCursor.MoveMode.KeepAnchor, max(0, end_line - start_line))
            cur.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
            self.setTextCursor(cur)
        except Exception as e:
            print(f"Toggle comments error: {e}")
    
    def contextMenuEvent(self, event):
        """Create custom context menu for text editor"""
        # Create context menu
        context_menu = QMenu(self)
        
        # Add standard text editor actions
        undo_action = context_menu.addAction("Undo")
        undo_action.triggered.connect(self.undo)
        
        redo_action = context_menu.addAction("Redo")
        redo_action.triggered.connect(self.redo)
        
        context_menu.addSeparator()
        
        cut_action = context_menu.addAction("Cut")
        cut_action.triggered.connect(self.cut)
        
        copy_action = context_menu.addAction("Copy")
        copy_action.triggered.connect(self.copy)
        
        paste_action = context_menu.addAction("Paste")
        paste_action.triggered.connect(self.paste)
        
        context_menu.addSeparator()
        
        # Add tree sync actions
        find_in_tree_action = context_menu.addAction("Find in Tree (Ctrl+T)")
        find_in_tree_action.triggered.connect(self.window().find_in_tree)
        
        select_tree_node_action = context_menu.addAction("Select Tree Node at Cursor")
        select_tree_node_action.triggered.connect(self._select_tree_node_at_cursor)
        
        context_menu.addSeparator()
        
        # Bookmark actions moved to Bookmarks tab; keep editor menu focused on editing
        
        # Show context menu at cursor position
        context_menu.exec(event.globalPos())
    
    def _select_tree_node_at_cursor(self):
        """Manually select tree node at current cursor position"""
        self.window().find_in_tree()


class BottomPanel(QTabWidget):
    """Bottom panel with tabs for different panels"""
    def __init__(self):
        super().__init__()
        self.setMaximumHeight(300)
        # Move tab headers to right border
        self.setTabPosition(QTabWidget.TabPosition.East)
        
        # Create tabs
        self.output_tab = QWidget()
        self.validation_tab = QWidget()
        self.find_tab = QWidget()
        self.bookmarks_tab = QWidget()
        
        self.addTab(self.find_tab, "Find Results")
        self.addTab(self.bookmarks_tab, "Bookmarks")
        self.addTab(self.output_tab, "Output")
        self.addTab(self.validation_tab, "Validation")

        self._setup_output_tab()
        self._setup_validation_tab()
        self._setup_find_tab()
        self._setup_bookmarks_tab()
    
    def _setup_output_tab(self):
        """Setup output tab"""
        layout = QVBoxLayout()
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Consolas", 10))
        self.output_text.setMaximumHeight(250)
        layout.addWidget(self.output_text)
        self.output_tab.setLayout(layout)
    
    def _setup_validation_tab(self):
        """Setup validation tab"""
        layout = QVBoxLayout()
        self.validation_list = QListWidget()
        self.validation_list.setMaximumHeight(250)
        layout.addWidget(self.validation_list)
        self.validation_tab.setLayout(layout)
    
    def _setup_find_tab(self):
        """Setup find tab"""
        layout = QVBoxLayout()
        self.find_results = QListWidget()
        self.find_results.setMaximumHeight(250)
        layout.addWidget(self.find_results)
        self.find_tab.setLayout(layout)

    def _setup_bookmarks_tab(self):
        """Setup bookmarks tab"""
        layout = QVBoxLayout()
        # Controls for bookmark operations
        controls = QHBoxLayout()
        btn_toggle = QPushButton("Toggle at Cursor")
        btn_next = QPushButton("Next")
        btn_prev = QPushButton("Previous")
        btn_clear = QPushButton("Clear All")
        try:
            btn_toggle.clicked.connect(lambda: self.window().toggle_bookmark())
            btn_next.clicked.connect(lambda: self.window().next_bookmark())
            btn_prev.clicked.connect(lambda: self.window().prev_bookmark())
            btn_clear.clicked.connect(lambda: self.window().clear_bookmarks())
        except Exception:
            pass
        controls.addWidget(btn_toggle)
        controls.addWidget(btn_next)
        controls.addWidget(btn_prev)
        controls.addStretch()
        controls.addWidget(btn_clear)
        layout.addLayout(controls)
        self.bookmark_list = QListWidget()
        self.bookmark_list.setMaximumHeight(250)
        layout.addWidget(self.bookmark_list)
        self.bookmarks_tab.setLayout(layout)

    def dragEnterEvent(self, event):
        """Accept drags that look like supported local files."""
        try:
            md = event.mimeData()
            # File URLs
            if md.hasUrls():
                for url in md.urls():
                    try:
                        if url.isLocalFile():
                            p = url.toLocalFile()
                            if isinstance(p, str) and p.lower().endswith((".xml", ".xsd", ".xsl", ".xslt")):
                                event.acceptProposedAction()
                                return
                    except Exception:
                        continue
            # Plain text path
            if md.hasText():
                try:
                    t = md.text().strip()
                    if t and os.path.exists(t) and t.lower().endswith((".xml", ".xsd", ".xsl", ".xslt")):
                        event.acceptProposedAction()
                        return
                except Exception:
                    pass
        except Exception:
            pass
        event.ignore()

    def dropEvent(self, event):
        """Open the dropped file if supported."""
        try:
            md = event.mimeData()
            paths = []
            if md.hasUrls():
                for url in md.urls():
                    try:
                        if url.isLocalFile():
                            p = url.toLocalFile()
                            if isinstance(p, str):
                                paths.append(p)
                    except Exception:
                        continue
            elif md.hasText():
                try:
                    t = md.text().strip()
                    if t:
                        paths.append(t)
                except Exception:
                    pass
            # Open first supported file
            for p in paths:
                try:
                    if os.path.exists(p) and p.lower().endswith((".xml", ".xsd", ".xsl", ".xslt")):
                        try:
                            self.window().open_file(p)
                        except Exception:
                            try:
                                self.window()._load_file_from_path(p)
                            except Exception:
                                pass
                        event.acceptProposedAction()
                        return
                except Exception:
                    continue
        except Exception:
            pass
        event.ignore()
    
    def append_output(self, text: str):
        """Append text to output"""
        self.output_text.append(text)
    
    def clear_validation_errors(self):
        """Clear validation errors"""
        self.validation_list.clear()
    
    def add_validation_error(self, error: str):
        """Add validation error"""
        self.validation_list.addItem(error)
    
    def clear_find_results(self):
        """Clear find results"""
        self.find_results.clear()
    
    def add_find_result(self, result: str):
        """Add find result"""
        self.find_results.addItem(result)

    def clear_bookmarks(self):
        """Clear bookmarks list"""
        try:
            self.bookmark_list.clear()
        except Exception:
            pass

    def add_bookmark_item(self, line_number: int, display_text: str):
        """Add a bookmark item with text and a clear (X) button"""
        try:
            item = QListWidgetItem()
            # Store line number in item for navigation
            item.setData(Qt.ItemDataRole.UserRole, line_number)
            # Avoid painting default item text to prevent duplicate rendering with the widget
            item.setText("")
            # Create widget with label and X button
            container = QWidget()
            h = QHBoxLayout(container)
            h.setContentsMargins(6, 2, 6, 2)
            h.setSpacing(8)
            # Left number label with padding to prevent overlap
            num_label = QLabel(str(line_number))
            num_label.setMinimumWidth(44)  # leave more indent so text does not overlap
            num_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            # Text label for bookmark content
            text_label = QLabel(display_text)
            text_label.setToolTip("Double-click to jump to this bookmark")
            btn = QPushButton("X")
            btn.setFixedSize(20, 20)
            btn.setToolTip("Clear this bookmark")
            def _on_clear():
                try:
                    self.window().remove_bookmark(line_number)
                except Exception:
                    pass
            btn.clicked.connect(_on_clear)
            h.addWidget(num_label)
            h.addWidget(text_label, 1)
            h.addStretch()
            h.addWidget(btn)
            container.setLayout(h)
            self.bookmark_list.addItem(item)
            # Provide a reasonable size hint so the list row height matches the widget
            try:
                item.setSizeHint(container.sizeHint())
            except Exception:
                pass
            self.bookmark_list.setItemWidget(item, container)
        except Exception:
            pass


class FindDialog(QDialog):
    """Find dialog for searching in XML"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Find")
        self.setModal(False)
        self.setFixedSize(400, 200)
        
        layout = QVBoxLayout()
        
        # Find input
        find_layout = QHBoxLayout()
        find_layout.addWidget(QLabel("Find:"))
        self.find_input = QLineEdit()
        find_layout.addWidget(self.find_input)
        layout.addLayout(find_layout)
        
        # Options
        options_layout = QVBoxLayout()
        self.case_sensitive = QCheckBox("Case sensitive")
        self.whole_word = QCheckBox("Whole word")
        self.use_regex = QCheckBox("Use regular expressions")
        options_layout.addWidget(self.case_sensitive)
        options_layout.addWidget(self.whole_word)
        options_layout.addWidget(self.use_regex)
        layout.addLayout(options_layout)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Close
        )
        button_box.accepted.connect(self.find_text)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def get_search_params(self):
        """Get search parameters"""
        return {
            'text': self.find_input.text(),
            'case_sensitive': self.case_sensitive.isChecked(),
            'whole_word': self.whole_word.isChecked(),
            'use_regex': self.use_regex.isChecked()
        }
    
    def find_text(self):
        """Handle find button click"""
        # Just accept the dialog - the main window will handle the search
        self.accept()


class ReplaceDialog(QDialog):
    """Replace dialog for searching and replacing in XML"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Replace")
        self.setModal(False)
        self.setFixedSize(420, 240)

        layout = QVBoxLayout()

        # Find input
        find_layout = QHBoxLayout()
        find_layout.addWidget(QLabel("Find:"))
        self.find_input = QLineEdit()
        find_layout.addWidget(self.find_input)
        layout.addLayout(find_layout)

        # Replace input
        repl_layout = QHBoxLayout()
        repl_layout.addWidget(QLabel("Replace:"))
        self.replace_input = QLineEdit()
        repl_layout.addWidget(self.replace_input)
        layout.addLayout(repl_layout)

        # Options
        options_layout = QVBoxLayout()
        self.case_sensitive = QCheckBox("Case sensitive")
        self.whole_word = QCheckBox("Whole word")
        self.use_regex = QCheckBox("Use regular expressions")
        options_layout.addWidget(self.case_sensitive)
        options_layout.addWidget(self.whole_word)
        options_layout.addWidget(self.use_regex)
        layout.addLayout(options_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        replace_btn = QPushButton("Replace")
        replace_all_btn = QPushButton("Replace All")
        close_btn = QPushButton("Close")
        btn_layout.addWidget(replace_btn)
        btn_layout.addWidget(replace_all_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        # Wire actions to parent
        if parent is not None:
            replace_btn.clicked.connect(lambda: parent.replace_text(self.get_params()))
            replace_all_btn.clicked.connect(lambda: parent.replace_all(self.get_params()))
        close_btn.clicked.connect(self.close)

        self.setLayout(layout)

    def get_params(self):
        return {
            'text': self.find_input.text(),
            'replace': self.replace_input.text(),
            'case_sensitive': self.case_sensitive.isChecked(),
            'whole_word': self.whole_word.isChecked(),
            'use_regex': self.use_regex.isChecked()
        }


class GoToLineDialog(QDialog):
    """Go to line dialog"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Go to Line")
        self.setModal(True)
        self.setFixedSize(300, 120)
        
        layout = QVBoxLayout()
        
        # Line input
        line_layout = QHBoxLayout()
        line_layout.addWidget(QLabel("Line number:"))
        self.line_spinbox = QSpinBox()
        self.line_spinbox.setMinimum(1)
        self.line_spinbox.setMaximum(999999)
        line_layout.addWidget(self.line_spinbox)
        layout.addLayout(line_layout)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def get_line_number(self):
        """Get line number"""
        return self.line_spinbox.value()


class TreeExportDialog(QDialog):
    """Dialog for exporting tree content to table format"""
    def __init__(self, tree_widget, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export Tree Content")
        self.setModal(False)
        self.resize(800, 600)
        
        layout = QVBoxLayout()
        
        # Info label
        info_label = QLabel("Tree content exported to table format. Select all (Ctrl+A) and copy (Ctrl+C) to clipboard.")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Table widget
        self.table_widget = QTableWidget()
        self.table_widget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        self.table_widget.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        layout.addWidget(self.table_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all_cells)
        button_layout.addWidget(select_all_btn)
        
        copy_btn = QPushButton("Copy to Clipboard")
        copy_btn.clicked.connect(self.copy_to_clipboard)
        button_layout.addWidget(copy_btn)
        
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Populate the table with tree content
        self.populate_table(tree_widget)
    
    def populate_table(self, tree_widget):
        """Populate table with tree content"""
        # Get all items from tree
        all_items = []
        self.get_all_tree_items(tree_widget.invisibleRootItem(), all_items, 0)
        
        if not all_items:
            self.table_widget.setRowCount(1)
            self.table_widget.setColumnCount(1)
            self.table_widget.setItem(0, 0, QTableWidgetItem("No tree content available"))
            return
        
        # Set up table
        self.table_widget.setRowCount(len(all_items))
        self.table_widget.setColumnCount(4)  # Level, Name, Value, Attributes
        self.table_widget.setHorizontalHeaderLabels(["Level", "Name", "Value", "Attributes"])
        
        # Populate table
        for row, (level, name, value, attributes) in enumerate(all_items):
            self.table_widget.setItem(row, 0, QTableWidgetItem(str(level)))
            self.table_widget.setItem(row, 1, QTableWidgetItem(name))
            self.table_widget.setItem(row, 2, QTableWidgetItem(value if value else ""))
            self.table_widget.setItem(row, 3, QTableWidgetItem(attributes if attributes else ""))
        
        # Resize columns to content
        self.table_widget.resizeColumnsToContents()
    
    def get_all_tree_items(self, parent_item, items_list, level):
        """Recursively get all tree items"""
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            
            # Get item data
            name = child.text(0) if child.text(0) else ""
            value = child.text(1) if child.text(1) else ""
            attributes = child.text(2) if child.text(2) else ""
            
            items_list.append((level, name, value, attributes))
            
            # Recursively process children
            self.get_all_tree_items(child, items_list, level + 1)
    
    def select_all_cells(self):
        """Select all cells in the table"""
        self.table_widget.selectAll()
    
    def copy_to_clipboard(self):
        """Copy selected cells to clipboard"""
        selection = self.table_widget.selectedRanges()
        if not selection:
            QMessageBox.information(self, "Info", "No cells selected. Please select cells first.")
            return
        
        # Get all selected cells
        selected_items = self.table_widget.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "Info", "No cells selected. Please select cells first.")
            return
        
        # Create text representation
        text_data = []
        for item in selected_items:
            row = item.row()
            col = item.column()
            text = item.text()
            text_data.append(f"Row {row}, Col {col}: {text}")
        
        # Copy to clipboard
        clipboard = QApplication.clipboard()
        clipboard.setText("\n".join(text_data))
        
        QMessageBox.information(self, "Success", f"Copied {len(selected_items)} cells to clipboard!")


class MainWindow(QMainWindow):
    """Main application window"""
    def __init__(self, file_path=None):
        super().__init__()
        self.current_file = None
        self.xml_service = XmlService()
        
        # Debug logging flag (set to True to enable treedebug.txt logging)
        self.tree_debug_enabled = False
        
        # Bookmarks functionality
        self.bookmarks = {}  # line_number -> description
        self.current_bookmark_index = -1
        self.numbered_bookmarks = {}  # digit (1..9) -> line_number
        
        # Search functionality
        self.last_search_params = None
        self.last_search_results = []  # List of (line_number, column_start, column_end) tuples
        self.current_search_index = -1
        
        # Recent files functionality
        self.recent_files = []
        self.max_recent_files = 5  # Show 5 recent files in menu
        self.recent_files_menu = None  # Will be set in _create_menu_bar

        # Optional synchronization feature flag and multicolumn windows registry
        self.sync_enabled = False
        self.multicolumn_windows = []
        
        # Highlight feature flag (orange border on tree node selection)
        self.highlight_enabled = True  # Enabled by default
        
        self.setWindowTitle("Lotus Xml Editor - Python Version")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize language registry and default profiles
        self.language_registry = LanguageRegistry()
        try:
            self._install_default_languages()
        except Exception as e:
            print(f"Language registry initialization error: {e}")
        
        self._create_menu_bar()
        self._create_tool_bar()
        self._create_central_widget()
        self._create_file_navigator()
        self._create_status_bar()
        self._setup_auto_hide()
        self._connect_signals()

        # Load persisted toggle flags (after UI and actions are created)
        try:
            self._load_persisted_flags()
        except Exception as e:
            print(f"Error loading persisted flags: {e}")

        # Path→line indexing and cache configuration
        self.path_line_index = {}
        self.path_line_cache = {}
        self.sync_index_enabled = False
        self.sync_cache_enabled = False
        self._sync_index_available = False  # lxml availability flag
        # Loading guard to suppress content-changed side effects during programmatic loads
        self._loading_file = False
        
        # Set up timer for auto-save
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self._auto_save)
        self.auto_save_timer.start(300000)  # 5 minutes
        
        # Theme is applied via persisted settings in _load_persisted_flags
        
        # Load recent files and open file if provided, otherwise open most recent
        self._load_recent_files()
        if file_path and os.path.exists(file_path):
            self._load_file_from_path(file_path)
            self.status_label.setText(f"Opened file: {os.path.basename(file_path)}")
            # Hide file navigator when starting with a file provided
            self._set_file_navigator_visible(False)
        else:
            self._open_most_recent_file()
            # Hide file navigator if a recent file was auto-opened
            if self.current_file:
                self._set_file_navigator_visible(False)

    def _build_path_line_index(self, content: str):
        """Build path→line index using lxml.etree.sourceline if available."""
        self.path_line_index = {}
        try:
            from lxml import etree
            import io
            f = io.BytesIO(content.encode('utf-8'))
            tag_counters_stack = []  # sibling counters per level (depth-indexed)
            path_stack = []  # active path stack of (tag_name, index)
            # Use both start and end events to maintain accurate ancestry
            for event, elem in etree.iterparse(f, events=("start", "end")):
                if event == "start":
                    tag = elem.tag
                    # Strip namespace if present
                    if isinstance(tag, str) and tag.startswith("{"):
                        tag = tag.split('}', 1)[1]
                    depth = len(path_stack)
                    # Ensure counters exist for this depth
                    if len(tag_counters_stack) <= depth:
                        tag_counters_stack.append({})
                    level_counters = tag_counters_stack[depth]
                    level_counters[tag] = level_counters.get(tag, 0) + 1
                    idx = level_counters[tag]
                    # Push to path stack
                    path_stack.append((tag, idx))
                    # Record full path for this start element
                    path = ''.join([f"/{t}[{i}]" for (t, i) in path_stack])
                    line = getattr(elem, 'sourceline', None) or 0
                    if line:
                        self.path_line_index[path] = line
                else:  # end event
                    # Pop the last element from the path stack
                    if path_stack:
                        path_stack.pop()
                    # Trim counters stack to current depth
                    if len(tag_counters_stack) > len(path_stack) + 1:
                        tag_counters_stack = tag_counters_stack[:len(path_stack) + 1]
            self._sync_index_available = True
        except Exception as e:
            print(f"DEBUG: lxml indexing not available or failed: {e}")
            self.path_line_index = {}
            self._sync_index_available = False
    
    def _create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_action = QAction("New", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        
        open_action = QAction("Open...", self)
        open_action.setShortcut("Ctrl+O")
        # Use lambda to avoid passing QAction's bool to open_file
        open_action.triggered.connect(lambda: self.open_file())
        file_menu.addAction(open_action)
        
        # Recent Files submenu
        self.recent_files_menu = file_menu.addMenu("Recent Files")
        self._update_recent_files_menu()
        
        file_menu.addSeparator()
        
        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("Save As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("Edit")
        
        undo_action = QAction("Undo", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self.undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("Redo", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(self.redo)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        find_action = QAction("Find...", self)
        find_action.setShortcut("Ctrl+F")
        find_action.triggered.connect(self.show_find_dialog)
        edit_menu.addAction(find_action)
        
        find_next_action = QAction("Find Next", self)
        find_next_action.setShortcut("F3")
        find_next_action.triggered.connect(self.find_next)
        edit_menu.addAction(find_next_action)

        # Replace actions
        replace_action = QAction("Replace...", self)
        replace_action.setShortcut("Ctrl+H")
        replace_action.triggered.connect(self.show_replace_dialog)
        edit_menu.addAction(replace_action)

        replace_all_action = QAction("Replace All", self)
        replace_all_action.setShortcut("Ctrl+Shift+H")
        replace_all_action.triggered.connect(self.replace_all_from_last_or_dialog)
        edit_menu.addAction(replace_all_action)
        
        goto_action = QAction("Go to Line...", self)
        goto_action.setShortcut("Ctrl+G")
        goto_action.triggered.connect(self.show_goto_dialog)
        edit_menu.addAction(goto_action)
        
        edit_menu.addSeparator()
        
        # Bookmark actions
        toggle_bookmark_action = QAction("Set/Toggle Bookmark", self)
        toggle_bookmark_action.setShortcut("Alt+F2")
        toggle_bookmark_action.triggered.connect(self.toggle_bookmark)
        edit_menu.addAction(toggle_bookmark_action)
        
        next_bookmark_action = QAction("Next Bookmark", self)
        next_bookmark_action.setShortcut("F2")
        next_bookmark_action.triggered.connect(self.next_bookmark)
        edit_menu.addAction(next_bookmark_action)
        
        prev_bookmark_action = QAction("Previous Bookmark", self)
        prev_bookmark_action.setShortcut("Shift+F2")
        prev_bookmark_action.triggered.connect(self.prev_bookmark)
        edit_menu.addAction(prev_bookmark_action)
        
        clear_bookmarks_action = QAction("Clear All Bookmarks", self)
        clear_bookmarks_action.triggered.connect(self.clear_bookmarks)
        edit_menu.addAction(clear_bookmarks_action)
        
        # XML menu
        xml_menu = menubar.addMenu("XML")
        
        format_action = QAction("Format XML", self)
        format_action.setShortcut("Ctrl+Shift+F")
        format_action.triggered.connect(self.format_xml)
        xml_menu.addAction(format_action)
        
        validate_action = QAction("Validate XML", self)
        validate_action.setShortcut("Ctrl+Shift+V")
        validate_action.triggered.connect(self.validate_xml)
        xml_menu.addAction(validate_action)
        
        stats_action = QAction("XML Statistics", self)
        stats_action.triggered.connect(self.show_xml_stats)
        xml_menu.addAction(stats_action)
        
        xml_menu.addSeparator()
        
        find_in_tree_action = QAction("Find in Tree", self)
        find_in_tree_action.setShortcut("Ctrl+Shift+T")
        find_in_tree_action.triggered.connect(self.find_in_tree)
        xml_menu.addAction(find_in_tree_action)
        
        xml_menu.addSeparator()
        
        # Node operations
        copy_node_action = QAction("Copy Current Node with Subnodes", self)
        copy_node_action.setShortcut("Ctrl+Shift+C")
        copy_node_action.triggered.connect(self.copy_current_node_with_subnodes)
        xml_menu.addAction(copy_node_action)
        
        open_node_window_action = QAction("Open Node in New Window", self)
        open_node_window_action.setShortcut("Ctrl+Shift+N")
        open_node_window_action.triggered.connect(self.open_node_in_new_window)
        xml_menu.addAction(open_node_window_action)
        
        xml_menu.addSeparator()
        
        export_tree_action = QAction("Export Tree", self)
        export_tree_action.setShortcut("Ctrl+E")
        export_tree_action.triggered.connect(self.export_tree)
        xml_menu.addAction(export_tree_action)
        
        xml_menu.addSeparator()
        
        # XML Split functionality
        split_xml_action = QAction("Split XML...", self)
        split_xml_action.setShortcut("Ctrl+Shift+S")
        split_xml_action.triggered.connect(self.show_split_dialog)
        xml_menu.addAction(split_xml_action)
        
        open_split_project_action = QAction("Open Split Project...", self)
        open_split_project_action.triggered.connect(self.open_split_project)
        xml_menu.addAction(open_split_project_action)
        
        reconstruct_xml_action = QAction("Reconstruct from Parts...", self)
        reconstruct_xml_action.triggered.connect(self.reconstruct_from_parts)
        xml_menu.addAction(reconstruct_xml_action)
        
        # Quick Split and Structure Diagram
        xml_menu.addSeparator()
        quick_split_action = QAction("Quick Split (3 parts)", self)
        quick_split_action.setToolTip("Split current XML into three files by distributing top-level elements")
        quick_split_action.triggered.connect(self.quick_split_three_parts)
        xml_menu.addAction(quick_split_action)

        structure_diagram_action = QAction("Structure Diagram", self)
        structure_diagram_action.setToolTip("Open a layered diagram view of the XML structure")
        structure_diagram_action.triggered.connect(self.open_structure_diagram)
        xml_menu.addAction(structure_diagram_action)
        
        # 1C Exchange menu (Обмен с 1С)
        exchange_menu = menubar.addMenu("Обмен с 1С")

        # Mode toggle: Semi-automatic (checked) vs Manual (unchecked)
        self.exchange_mode_action = QAction("Полуавтоматический режим", self)
        self.exchange_mode_action.setCheckable(True)
        self.exchange_mode_action.setChecked(True)
        self.exchange_mode_action.setToolTip(
            "Переключение режима: Полуавтоматический (по умолчанию) или ручной"
        )
        def _toggle_exchange_mode(checked: bool):
            self.exchange_mode = "semi" if checked else "manual"
            try:
                # Persist as flag
                self._save_flag('exchange_semi_mode', checked)
            except Exception:
                pass
        self.exchange_mode_action.toggled.connect(_toggle_exchange_mode)
        exchange_menu.addAction(self.exchange_mode_action)

        exchange_menu.addSeparator()

        # Import from 1C: choose two XML files (unzipped) and open edited one
        exchange_import_action = QAction("Импорт из 1С (2 XML)", self)
        exchange_import_action.setToolTip(
            "Выбрать два XML из 1С и открыть редактируемый файл"
        )
        exchange_import_action.triggered.connect(self.exchange_import)
        exchange_menu.addAction(exchange_import_action)

        # Export to 1C: package two XML into one ZIP
        exchange_export_zip_action = QAction("Экспорт в 1С (ZIP из 2 XML)", self)
        exchange_export_zip_action.setToolTip(
            "Упаковать редактируемый и парный XML в один ZIP"
        )
        exchange_export_zip_action.triggered.connect(self.exchange_export_zip)
        exchange_menu.addAction(exchange_export_zip_action)

        # View menu
        view_menu = menubar.addMenu("View")
        
        toggle_theme_action = QAction("Toggle Dark Theme", self)
        toggle_theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(toggle_theme_action)
        
        view_menu.addSeparator()
        
        # Breadcrumb visibility toggle
        self.toggle_breadcrumb_action = QAction("Show Breadcrumbs", self)
        self.toggle_breadcrumb_action.setCheckable(True)
        self.toggle_breadcrumb_action.setChecked(False)  # Hidden by default
        self.toggle_breadcrumb_action.triggered.connect(self.toggle_breadcrumbs)
        view_menu.addAction(self.toggle_breadcrumb_action)
        
        # Bottom panel visibility toggle
        self.toggle_bottom_panel_action = QAction("Show Bottom Panel", self)
        self.toggle_bottom_panel_action.setCheckable(True)
        self.toggle_bottom_panel_action.setChecked(False)  # Hidden by default
        self.toggle_bottom_panel_action.triggered.connect(self.toggle_bottom_panel)
        view_menu.addAction(self.toggle_bottom_panel_action)
        
        # File navigator visibility toggle
        self.toggle_file_navigator_action = QAction("Show File Navigator", self)
        self.toggle_file_navigator_action.setCheckable(True)
        self.toggle_file_navigator_action.setChecked(True)  # Visible by default
        self.toggle_file_navigator_action.triggered.connect(self.toggle_file_navigator)
        view_menu.addAction(self.toggle_file_navigator_action)
        
        view_menu.addSeparator()
        # Friendly labels toggle in tree
        self.toggle_friendly_labels_action = QAction("Use Friendly Labels", self)
        self.toggle_friendly_labels_action.setCheckable(True)
        self.toggle_friendly_labels_action.setChecked(True)
        
        def _on_friendly_labels_toggled(checked: bool):
            try:
                if hasattr(self, 'xml_tree') and self.xml_tree:
                    self.xml_tree.use_friendly_labels = checked
                    self.xml_tree.refresh_labels()
                    if hasattr(self, 'status_label') and self.status_label:
                        self.status_label.setText(f"Labels: {'friendly' if checked else 'raw tags'}")
                        self._update_flags_indicator()
                    # Persist
                    try:
                        self._save_flag('friendly_labels', checked)
                    except Exception:
                        pass
            except Exception as e:
                print(f"Friendly labels toggle error: {e}")
        
        self.toggle_friendly_labels_action.toggled.connect(_on_friendly_labels_toggled)
        view_menu.addAction(self.toggle_friendly_labels_action)

        # Update Tree on Tab Switch toggle in View menu (mirrors toolbar toggle)
        self.toggle_update_tree_view_action = QAction("Update Tree on Tab Switch", self)
        self.toggle_update_tree_view_action.setCheckable(True)
        self.toggle_update_tree_view_action.setChecked(True)

        def _on_update_tree_view_toggled(checked: bool):
            # Set the underlying flag
            self.update_tree_on_tab_switch = checked
            # Sync toolbar toggle if present
            if hasattr(self, 'update_tree_toggle'):
                try:
                    self.update_tree_toggle.blockSignals(True)
                    self.update_tree_toggle.setChecked(checked)
                    self.update_tree_toggle.blockSignals(False)
                except Exception:
                    pass
            # Status and flags indicator
            if hasattr(self, 'status_label') and self.status_label:
                self.status_label.setText(f"Tree update on tab switch {'enabled' if checked else 'disabled'}")
            try:
                self._update_flags_indicator()
            except Exception:
                pass
            # Persist
            try:
                self._save_flag('update_tree_on_tab_switch', checked)
            except Exception:
                pass

        self.toggle_update_tree_view_action.toggled.connect(_on_update_tree_view_toggled)
        view_menu.addAction(self.toggle_update_tree_view_action)
        
        view_menu.addSeparator()
        
        # Auto-hide toggles
        self.toggle_toolbar_autohide_action = QAction("Auto-hide Toolbar", self)
        self.toggle_toolbar_autohide_action.setCheckable(True)
        self.toggle_toolbar_autohide_action.setChecked(True)  # Enabled by default
        self.toggle_toolbar_autohide_action.setShortcut("Ctrl+Shift+T")
        
        def _on_toolbar_autohide_toggled(checked: bool):
            try:
                if hasattr(self, 'toolbar_auto_hide'):
                    self.toolbar_auto_hide.set_auto_hide_enabled(checked)
                if hasattr(self, 'status_label') and self.status_label:
                    self.status_label.setText(f"Toolbar auto-hide {'enabled' if checked else 'disabled'}")
                try:
                    self._save_flag('toolbar_autohide', checked)
                except Exception:
                    pass
            except Exception as e:
                print(f"Toolbar auto-hide toggle error: {e}")
        
        self.toggle_toolbar_autohide_action.toggled.connect(_on_toolbar_autohide_toggled)
        view_menu.addAction(self.toggle_toolbar_autohide_action)
        
        self.toggle_tree_header_autohide_action = QAction("Auto-hide Tree Header", self)
        self.toggle_tree_header_autohide_action.setCheckable(True)
        self.toggle_tree_header_autohide_action.setChecked(True)  # Enabled by default
        self.toggle_tree_header_autohide_action.setShortcut("Ctrl+Shift+H")
        
        def _on_tree_header_autohide_toggled(checked: bool):
            try:
                if hasattr(self, 'tree_header_auto_hide'):
                    self.tree_header_auto_hide.set_auto_hide_enabled(checked)
                if hasattr(self, 'status_label') and self.status_label:
                    self.status_label.setText(f"Tree header auto-hide {'enabled' if checked else 'disabled'}")
                try:
                    self._save_flag('tree_header_autohide', checked)
                except Exception:
                    pass
            except Exception as e:
                print(f"Tree header auto-hide toggle error: {e}")
        
        self.toggle_tree_header_autohide_action.toggled.connect(_on_tree_header_autohide_toggled)
        view_menu.addAction(self.toggle_tree_header_autohide_action)
        
        self.toggle_tree_column_header_autohide_action = QAction("Auto-hide Tree Column Header", self)
        self.toggle_tree_column_header_autohide_action.setCheckable(True)
        self.toggle_tree_column_header_autohide_action.setChecked(True)  # Enabled by default
        self.toggle_tree_column_header_autohide_action.setShortcut("Ctrl+Shift+E")
        
        def _on_tree_column_header_autohide_toggled(checked: bool):
            try:
                if hasattr(self, 'tree_column_header_auto_hide'):
                    self.tree_column_header_auto_hide.set_auto_hide_enabled(checked)
                if hasattr(self, 'status_label') and self.status_label:
                    self.status_label.setText(f"Tree column header auto-hide {'enabled' if checked else 'disabled'}")
                try:
                    self._save_flag('tree_column_header_autohide', checked)
                except Exception:
                    pass
            except Exception as e:
                print(f"Tree column header auto-hide toggle error: {e}")
        
        self.toggle_tree_column_header_autohide_action.toggled.connect(_on_tree_column_header_autohide_toggled)
        view_menu.addAction(self.toggle_tree_column_header_autohide_action)
        
        self.toggle_tab_bar_autohide_action = QAction("Auto-hide Tab Bar", self)
        self.toggle_tab_bar_autohide_action.setCheckable(True)
        self.toggle_tab_bar_autohide_action.setChecked(True)  # Enabled by default
        self.toggle_tab_bar_autohide_action.setShortcut("Ctrl+Shift+B")
        
        def _on_tab_bar_autohide_toggled(checked: bool):
            try:
                if hasattr(self, 'tab_bar_auto_hide'):
                    self.tab_bar_auto_hide.set_auto_hide_enabled(checked)
                if hasattr(self, 'status_label') and self.status_label:
                    self.status_label.setText(f"Tab bar auto-hide {'enabled' if checked else 'disabled'}")
                try:
                    self._save_flag('tab_bar_autohide', checked)
                except Exception:
                    pass
            except Exception as e:
                print(f"Tab bar auto-hide toggle error: {e}")
        
        self.toggle_tab_bar_autohide_action.toggled.connect(_on_tab_bar_autohide_toggled)
        view_menu.addAction(self.toggle_tab_bar_autohide_action)
        
        view_menu.addSeparator()
        
        # Experimental multicolumn tree
        multicolumn_tree_action = QAction("Open Multicolumn Tree (Experimental)", self)
        multicolumn_tree_action.setShortcut("Ctrl+Shift+M")
        multicolumn_tree_action.triggered.connect(self.open_multicolumn_tree)
        view_menu.addAction(multicolumn_tree_action)

        # Help menu
        help_menu = menubar.addMenu("Help")
        hotkeys_action = QAction("Keyboard Shortcuts...", self)
        hotkeys_action.setShortcut("F1")
        hotkeys_action.triggered.connect(self.show_hotkey_help)
        help_menu.addAction(hotkeys_action)
    
    def _create_tool_bar(self):
        """Create tool bar"""
        toolbar = self.addToolBar("Main")
        
        new_btn = QAction("New", self)
        new_btn.triggered.connect(self.new_file)
        toolbar.addAction(new_btn)
        
        open_btn = QAction("Open", self)
        # Use lambda to avoid passing QAction's bool to open_file
        open_btn.triggered.connect(lambda: self.open_file())
        toolbar.addAction(open_btn)
        
        save_btn = QAction("Save", self)
        save_btn.triggered.connect(self.save_file)
        toolbar.addAction(save_btn)
        
        toolbar.addSeparator()
        
        format_btn = QAction("Format", self)
        format_btn.triggered.connect(self.format_xml)
        toolbar.addAction(format_btn)
        
        validate_btn = QAction("Validate", self)
        validate_btn.triggered.connect(self.validate_xml)
        toolbar.addAction(validate_btn)
        
        toolbar.addSeparator()

        # Toggle File Tree (File Navigator) visibility in toolbar
        self.toggle_file_tree_toolbar_action = QAction("File Tree", self)
        self.toggle_file_tree_toolbar_action.setCheckable(True)
        self.toggle_file_tree_toolbar_action.setChecked(True)

        def _on_toolbar_file_tree_toggled(checked: bool):
            try:
                self._set_file_navigator_visible(checked)
            except Exception:
                pass
            # Persist toggle state
            try:
                self._save_flag('show_file_navigator', checked)
            except Exception:
                pass

        self.toggle_file_tree_toolbar_action.toggled.connect(_on_toolbar_file_tree_toggled)
        toolbar.addAction(self.toggle_file_tree_toolbar_action)
        
        # Language selector (XML by default + loaded UDL profiles)
        # Language selector moved to status bar
        
        split_btn = QAction("Split XML", self)
        split_btn.triggered.connect(self.show_split_dialog)
        toolbar.addAction(split_btn)
        
        # One-button quick split into 3 parts for later root-merge combine
        quick_split_btn = QAction("Quick Split (3 parts)", self)
        quick_split_btn.setToolTip("Split current XML into three files by distributing top-level elements")
        quick_split_btn.triggered.connect(self.quick_split_three_parts)
        toolbar.addAction(quick_split_btn)
        
        # Structure Diagram view (levels left-to-right)
        diagram_btn = QAction("Structure Diagram", self)
        diagram_btn.setToolTip("Open a layered diagram view of the XML structure")
        diagram_btn.triggered.connect(self.open_structure_diagram)
        toolbar.addAction(diagram_btn)
        
        # Rebuild Tree button with auto-close tags
        rebuild_tree_btn = QAction("Rebuild Tree", self)
        rebuild_tree_btn.setToolTip("Rebuild tree from editor content with auto-close unclosed tags")
        rebuild_tree_btn.triggered.connect(self.rebuild_tree_with_autoclose)
        toolbar.addAction(rebuild_tree_btn)
        
        # Sync toggle in command bar to optionally enable text-to-tree sync
        toolbar.addSeparator()
        self.toggle_sync_action = QAction("Enable Sync", self)
        self.toggle_sync_action.setCheckable(True)
        self.toggle_sync_action.setChecked(False)
        
        def _on_sync_toggled(checked: bool):
            """Handle sync toggled from command bar: set flag, update status, and update tree selection immediately when enabled"""
            # Update button state
            self._update_button_state('sync', checked)
            
            self.sync_enabled = checked
            if hasattr(self, 'status_label') and self.status_label:
                self.status_label.setText(f"Sync {'enabled' if checked else 'disabled'}")
            # Refresh compact flags indicator
            try:
                self._update_flags_indicator()
            except Exception:
                pass
            # Persist
            try:
                self._save_flag('sync_enabled', checked)
            except Exception:
                pass
            if checked:
                try:
                    cursor = self.xml_editor.textCursor()
                    current_line = cursor.blockNumber() + 1
                    # Update main tree
                    self._sync_tree_to_cursor(current_line)
                    # Compute path for multicolumn windows and propagate
                    content = self.xml_editor.get_content()
                    path = self._get_element_path_at_line(content, current_line)
                    if path:
                        for win in getattr(self, 'multicolumn_windows', []):
                            try:
                                win.set_sync_enabled(True)
                                win.select_node_by_path(path)
                            except Exception as e:
                                print(f"Error syncing multicolumn window: {e}")
                except Exception as e:
                    print(f"Error syncing on enable: {e}")
        
        self.toggle_sync_action.toggled.connect(_on_sync_toggled)
        
        # Visibility toggles for syntax categories (moved to status bar)
        
        # 1) Hide angle bracket symbols '<' and '>'
        self.toggle_symbols_action = QAction("Hide <> Symbols", self)
        self.toggle_symbols_action.setCheckable(True)
        self.toggle_symbols_action.setChecked(False)
        self.toggle_symbols_action.setToolTip("Toggle visibility of angle bracket symbols by coloring them with the editor background")
        
        def _on_symbols_toggled(checked: bool):
            """When toggled, set XmlHighlighter to hide/show angle bracket symbols by using background color"""
            # Update button state
            self._update_button_state('symbols', checked)
            
            if hasattr(self, 'xml_editor') and hasattr(self.xml_editor, 'highlighter'):
                # Update highlighter visibility option for symbols
                self.xml_editor.highlighter.set_visibility_options(hide_symbols=checked)
                # Reflect state in status bar for clarity
                if hasattr(self, 'status_label') and self.status_label:
                    self.status_label.setText(f"<> symbols {'hidden' if checked else 'visible'}")
                # Refresh compact flags indicator
                try:
                    self._update_flags_indicator()
                except Exception:
                    pass
                # Persist
                try:
                    self._save_flag('hide_symbols', checked)
                except Exception:
                    pass
        
        self.toggle_symbols_action.toggled.connect(_on_symbols_toggled)
        
        # 2) Hide element tag names
        self.toggle_tags_action = QAction("Hide Tags", self)
        self.toggle_tags_action.setCheckable(True)
        self.toggle_tags_action.setChecked(False)
        self.toggle_tags_action.setToolTip("Toggle visibility of element tag names by coloring them with the editor background")
        
        def _on_tags_toggled(checked: bool):
            """When toggled, set XmlHighlighter to hide/show element tag names by using background color"""
            # Update button state
            self._update_button_state('tags', checked)
            
            if hasattr(self, 'xml_editor') and hasattr(self.xml_editor, 'highlighter'):
                # Update highlighter visibility option for tags
                self.xml_editor.highlighter.set_visibility_options(hide_tags=checked)
                # Reflect state in status bar for clarity
                if hasattr(self, 'status_label') and self.status_label:
                    self.status_label.setText(f"Tags {'hidden' if checked else 'visible'}")
                # Refresh compact flags indicator
                try:
                    self._update_flags_indicator()
                except Exception:
                    pass
                # Persist
                try:
                    self._save_flag('hide_tags', checked)
                except Exception:
                    pass
        
        self.toggle_tags_action.toggled.connect(_on_tags_toggled)
        
        # 3) Hide attribute values (quoted values, numbers, booleans)
        self.toggle_values_action = QAction("Hide Values", self)
        self.toggle_values_action.setCheckable(True)
        self.toggle_values_action.setChecked(False)
        self.toggle_values_action.setToolTip("Toggle visibility of attribute values by coloring them with the editor background")
        
        def _on_values_toggled(checked: bool):
            """When toggled, set XmlHighlighter to hide/show attribute values, numbers, and booleans by using background color"""
            # Update button state
            self._update_button_state('values', checked)
            
            if hasattr(self, 'xml_editor') and hasattr(self.xml_editor, 'highlighter'):
                # Update highlighter visibility option for values
                self.xml_editor.highlighter.set_visibility_options(hide_values=checked)
                # Reflect state in status bar for clarity
                if hasattr(self, 'status_label') and self.status_label:
                    self.status_label.setText(f"Values {'hidden' if checked else 'visible'}")
                # Refresh compact flags indicator
                try:
                    self._update_flags_indicator()
                except Exception:
                    pass
                # Persist
                try:
                    self._save_flag('hide_values', checked)
                except Exception:
                    pass
        
        self.toggle_values_action.toggled.connect(_on_values_toggled)

        # 4) Highlight selected element with orange border
        self.toggle_highlight_action = QAction("Highlight Selection", self)
        self.toggle_highlight_action.setCheckable(True)
        self.toggle_highlight_action.setChecked(True)  # Enabled by default
        self.toggle_highlight_action.setToolTip("Toggle orange border highlighting when clicking tree nodes")
        
        def _on_highlight_toggled(checked: bool):
            """When toggled, enable/disable orange border highlighting for selected elements"""
            # Update button state
            self._update_button_state('highlight', checked)
            
            self.highlight_enabled = checked
            
            # Clear existing highlights if disabled
            if not checked and hasattr(self, 'xml_editor'):
                self.xml_editor.setExtraSelections([])
            
            # Reflect state in status bar for clarity
            if hasattr(self, 'status_label') and self.status_label:
                self.status_label.setText(f"Highlight {'enabled' if checked else 'disabled'}")
            
            # Refresh compact flags indicator
            try:
                self._update_flags_indicator()
            except Exception:
                pass
            
            # Persist
            try:
                self._save_flag('highlight_enabled', checked)
            except Exception:
                pass
        
        self.toggle_highlight_action.toggled.connect(_on_highlight_toggled)

        # Tree update on tab switch toggle (moved to status bar)
        self.update_tree_toggle = QAction("Update Tree on Tab Switch", self)
        self.update_tree_toggle.setCheckable(True)
        self.update_tree_toggle.setChecked(True)

        def _on_update_tree_toggled(checked: bool):
            # Update button state
            self._update_button_state('updtree', checked)
            
            self.update_tree_on_tab_switch = checked
            if hasattr(self, 'status_label') and self.status_label:
                self.status_label.setText(f"Tree update on tab switch {'enabled' if checked else 'disabled'}")
            # Keep View menu toggle in sync
            if hasattr(self, 'toggle_update_tree_view_action'):
                try:
                    self.toggle_update_tree_view_action.blockSignals(True)
                    self.toggle_update_tree_view_action.setChecked(checked)
                    self.toggle_update_tree_view_action.blockSignals(False)
                except Exception:
                    pass
            # Refresh compact flags indicator
            try:
                self._update_flags_indicator()
            except Exception:
                pass
            # Persist
            try:
                self._save_flag('update_tree_on_tab_switch', checked)
            except Exception:
                pass
        
        self.update_tree_toggle.toggled.connect(_on_update_tree_toggled)

        # Hide Leaves toggle for XML tree
        toolbar.addSeparator()
        self.toggle_hide_leaves_action = QAction("Hide Leaves", self)
        self.toggle_hide_leaves_action.setCheckable(True)
        self.toggle_hide_leaves_action.setChecked(True)

        def _on_hide_leaves_toggled(checked: bool):
            try:
                if hasattr(self, 'xml_tree') and self.xml_tree:
                    self.xml_tree.set_hide_leaves(checked)
                if hasattr(self, 'status_label') and self.status_label:
                    self.status_label.setText(f"Leaf nodes {'hidden' if checked else 'visible'}")
                # Refresh compact flags indicator
                try:
                    self._update_flags_indicator()
                except Exception:
                    pass
                # Persist
                try:
                    self._save_flag('hide_leaves', checked)
                except Exception:
                    pass
            except Exception as e:
                print(f"Hide leaves toggle error: {e}")

        self.toggle_hide_leaves_action.toggled.connect(_on_hide_leaves_toggled)
        toolbar.addAction(self.toggle_hide_leaves_action)
    
    def _on_language_combo_changed(self, index: int):
        """Handle language selection changes from the toolbar combo box."""
        try:
            if not hasattr(self, 'language_combo'):
                return
            name = self.language_combo.itemText(index) if index >= 0 else 'XML'
            # Persist selection
            try:
                s = self._get_settings()
                s.setValue("language/name", name)
            except Exception:
                pass
            # Apply to current editor
            try:
                if hasattr(self, 'xml_editor') and isinstance(self.xml_editor, XmlEditorWidget):
                    self._apply_selected_language_to_editor(self.xml_editor)
            except Exception:
                pass
            # Status feedback
            try:
                if hasattr(self, 'status_label') and self.status_label:
                    self.status_label.setText(f"Language set to {name}")
            except Exception:
                pass
        except Exception as e:
            print(f"Language change handler error: {e}")

    def _install_default_languages(self):
        """Install built-in and bundled UDL language profiles into the registry."""
        try:
            # Bundled Notepad++ UDL example, if present
            base_dir = os.path.dirname(__file__)
            udl_path = os.path.join(base_dir, "1C Ent_TRANS.xml")
            if os.path.exists(udl_path):
                ld = load_udl_xml(udl_path)
                if ld:
                    self.language_registry.install(ld)
        except Exception as e:
            print(f"Default language install error: {e}")

    def _apply_selected_language_to_editor(self, editor: 'XmlEditorWidget'):
        """Apply the currently selected language profile to the given editor."""
        try:
            # Determine selection (fall back to XML)
            selected = 'XML'
            try:
                if hasattr(self, 'language_combo') and self.language_combo:
                    idx = self.language_combo.currentIndex()
                    if idx >= 0:
                        selected = self.language_combo.itemText(idx) or 'XML'
            except Exception:
                pass

            if selected == 'XML':
                # Use built-in XML highlighter
                try:
                    editor.highlighter = XmlHighlighter(editor.document())
                except Exception as e:
                    print(f"XML highlighter init error: {e}")
            else:
                # Use rule-based highlighter compiled from the language registry
                try:
                    ld = self.language_registry.get(selected)
                    if ld is None:
                        # Fallback to XML if language not found
                        editor.highlighter = XmlHighlighter(editor.document())
                    else:
                        rules = LanguageProfileCompiler(ld).compile()
                        editor.highlighter = RuleHighlighter(editor.document(), rules)
                except Exception as e:
                    print(f"Rule highlighter init error: {e}")
                    try:
                        editor.highlighter = XmlHighlighter(editor.document())
                    except Exception:
                        pass

            # Align theme on the new highlighter
            try:
                # Detect current theme from persisted flag
                s = self._get_settings()
                is_dark = s.value("flags/dark_theme")
                if isinstance(is_dark, str):
                    is_dark = is_dark.lower() in ("1", "true", "yes", "on")
                elif not isinstance(is_dark, bool):
                    is_dark = True
                editor.highlighter.set_dark_theme(bool(is_dark))
            except Exception:
                pass
        except Exception as e:
            print(f"Apply language error: {e}")
    
    def _apply_highlighter_settings(self):
        """Apply saved highlighter visibility settings after opening a file."""
        try:
            if hasattr(self, 'xml_editor') and hasattr(self.xml_editor, 'highlighter'):
                hide_syms = read_bool('hide_symbols', False)
                hide_tgs = read_bool('hide_tags', False)
                hide_vals = read_bool('hide_values', False)
                self.xml_editor.highlighter.set_visibility_options(
                    hide_symbols=hide_syms,
                    hide_tags=hide_tgs,
                    hide_values=hide_vals
                )
        except Exception as e:
            print(f"Error applying highlighter settings: {e}")
    
    def _create_central_widget(self):
        """Create central widget with splitter layout and tabbed MDI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        try:
            main_layout.setContentsMargins(4, 4, 4, 4)
            main_layout.setSpacing(2)  # Reduced from 4 to 2
        except Exception:
            pass
        
        # Breadcrumb widget (hidden by default)
        self.breadcrumb_label = QLabel("/")
        self.breadcrumb_label.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                padding: 2px;
                border: 1px solid #ccc;
                font-family: monospace;
                font-size: 10px;
            }
        """)
        self.breadcrumb_label.setMaximumHeight(20)  # Reduced from 25 to 20
        self.breadcrumb_label.setVisible(False)  # Hidden by default
        main_layout.addWidget(self.breadcrumb_label)
        
        # Main splitter
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel - XML tree
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        try:
            left_layout.setContentsMargins(2, 2, 2, 2)
            left_layout.setSpacing(2)  # Reduced from 4 to 2
        except Exception:
            pass
        
        tree_label = QLabel("XML Structure")
        tree_label.setStyleSheet("font-weight: bold; padding: 1px; font-size: 10px;")  # Reduced padding and font size
        tree_label.setMaximumHeight(18)  # Add max height constraint
        left_layout.addWidget(tree_label)
        
        # Persistent container to show level header buttons above the tree
        self.level_header_container = QWidget()
        self.level_header_container.setMaximumHeight(24)  # Reduced from implicit to 24
        _lvl_header_layout = QHBoxLayout()
        _lvl_header_layout.setContentsMargins(0, 0, 0, 0)
        _lvl_header_layout.setSpacing(2)  # Add spacing control
        self.level_header_container.setLayout(_lvl_header_layout)
        left_layout.addWidget(self.level_header_container)
        
        self.xml_tree = XmlTreeWidget()
        # Provide the container to the tree so it can mount header buttons
        self.xml_tree.header_container = self.level_header_container
        
        # Store reference to update status_label later
        self.xml_tree.status_label = None
        # Sync editor folding with tree expand/collapse
        try:
            self.xml_tree.itemCollapsed.connect(self._on_tree_item_collapsed)
            self.xml_tree.itemExpanded.connect(self._on_tree_item_expanded)
        except Exception:
            pass
        left_layout.addWidget(self.xml_tree)
        
        left_panel.setLayout(left_layout)
        
        # Right panel - tabbed editors and bottom panel
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        try:
            right_layout.setContentsMargins(2, 2, 2, 2)
            right_layout.setSpacing(2)  # Reduced from 4 to 2
        except Exception:
            pass
        
        # Tabbed MDI for editors
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self._close_tab)
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        self.update_tree_on_tab_switch = True
        # Reduce tab bar height
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #ccc; }
            QTabBar::tab { 
                height: 22px; 
                padding: 2px 8px; 
                margin: 0px;
            }
        """)
        
        # Create initial editor tab
        initial_editor = XmlEditorWidget()
        self.tab_widget.addTab(initial_editor, "Document 1")
        self.xml_editor = initial_editor  # Maintain existing reference for compatibility
        # Apply default/persisted language to the initial editor
        try:
            self._apply_selected_language_to_editor(initial_editor)
        except Exception:
            pass
        
        right_layout.addWidget(self.tab_widget)
        
        right_panel.setLayout(right_layout)
        
        # Add to splitter
        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(right_panel)
        main_splitter.setSizes([300, 900])
        
        # Add splitter to main layout
        main_layout.addWidget(main_splitter)
        central_widget.setLayout(main_layout)

        # Dockable bottom panel (hidden by default)
        self.bottom_panel = BottomPanel()
        self.bottom_dock = QDockWidget("", self)  # Empty title to save vertical space
        self.bottom_dock.setObjectName("BottomPanelDock")
        self.bottom_dock.setWidget(self.bottom_panel)
        self.bottom_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.bottom_dock)
        self.bottom_dock.setVisible(False)
    
    def _create_status_bar(self):
        """Create status bar"""
        self.status_bar = self.statusBar()
        # Set dark grey background for less contrast and reduce height by 1/3
        self.status_bar.setStyleSheet("QStatusBar { background-color: #3C3C3C; color: #CCCCCC; max-height: 24px; padding: 0px; margin: 0px; }")
        self.status_bar.setMaximumHeight(24)
        self.status_bar.setContentsMargins(0, 0, 0, 0)
        
        # Add status widgets with reduced font size (1/3 smaller)
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("font-size: 9px; padding: 0px; margin: 0px;")
        self.status_label.setContentsMargins(0, 0, 0, 0)
        self.status_bar.addWidget(self.status_label)
        
        sep1 = QLabel("|")
        sep1.setStyleSheet("font-size: 9px; padding: 0px; margin: 0px;")
        sep1.setContentsMargins(0, 0, 0, 0)
        self.status_bar.addPermanentWidget(sep1)
        
        self.line_label = QLabel("Ln: 1, Col: 1")
        self.line_label.setStyleSheet("font-size: 9px; padding: 0px; margin: 0px;")
        self.line_label.setContentsMargins(0, 0, 0, 0)
        self.status_bar.addPermanentWidget(self.line_label)
        
        sep2 = QLabel("|")
        sep2.setStyleSheet("font-size: 9px; padding: 0px; margin: 0px;")
        sep2.setContentsMargins(0, 0, 0, 0)
        self.status_bar.addPermanentWidget(sep2)
        
        self.encoding_label = QLabel("UTF-8")
        self.encoding_label.setStyleSheet("font-size: 9px; padding: 0px; margin: 0px;")
        self.encoding_label.setContentsMargins(0, 0, 0, 0)
        self.status_bar.addPermanentWidget(self.encoding_label)

        # Language selector (moved from toolbar)
        try:
            sep3 = QLabel("|")
            sep3.setStyleSheet("font-size: 9px; padding: 0px; margin: 0px;")
            sep3.setContentsMargins(0, 0, 0, 0)
            self.status_bar.addPermanentWidget(sep3)
            lang_label = QLabel("Lang:")
            lang_label.setStyleSheet("font-size: 9px; padding: 0px; margin: 0px;")
            lang_label.setContentsMargins(0, 0, 0, 0)
            self.status_bar.addPermanentWidget(lang_label)
            self.language_combo = QComboBox()
            self.language_combo.setStyleSheet("font-size: 9px; max-height: 22px; padding: 0px; margin: 0px;")
            self.language_combo.setMaximumHeight(22)
            self.language_combo.setContentsMargins(0, 0, 0, 0)
            self.language_combo.setToolTip("Select syntax language for editor")
            # Always include XML as the default option
            self.language_combo.addItem("XML")
            # Append installed language profiles
            try:
                for name in self.language_registry.list():
                    if name and name != "XML":
                        self.language_combo.addItem(name)
            except Exception:
                pass
            self.language_combo.currentIndexChanged.connect(self._on_language_combo_changed)
            self.status_bar.addPermanentWidget(self.language_combo)
        except Exception as e:
            print(f"Language selector init error: {e}")

        # Compact interactive flag bar (moved from toolbar)
        try:
            sep4 = QLabel("|")
            sep4.setStyleSheet("font-size: 9px; padding: 0px; margin: 0px;")
            sep4.setContentsMargins(0, 0, 0, 0)
            self.status_bar.addPermanentWidget(sep4)
            flags_bar = QWidget()
            flags_bar.setMaximumHeight(22)
            flags_bar.setContentsMargins(0, 0, 0, 0)
            flags_layout = QHBoxLayout()
            flags_layout.setContentsMargins(0, 0, 0, 0)
            flags_layout.setSpacing(2)
            flags_bar.setLayout(flags_layout)

            # Store button references for activity indication
            self.status_buttons = {}

            # Create compact toolbuttons bound to existing actions
            def _add_flag_button(action, text=None, button_key=None):
                btn = QToolButton()
                btn.setAutoRaise(True)
                btn.setStyleSheet("font-size: 9px; max-height: 22px; padding: 1px 3px; margin: 0px;")
                btn.setMaximumHeight(22)
                btn.setContentsMargins(0, 0, 0, 0)
                if text:
                    # Override displayed text while keeping the action behavior
                    action.setText(text)
                btn.setDefaultAction(action)
                flags_layout.addWidget(btn)
                # Store button reference if key provided
                if button_key:
                    self.status_buttons[button_key] = btn
                return btn

            # Sync, Symbols, Tags, Values, Highlight, Update Tree
            if hasattr(self, 'toggle_highlight_action'):
                _add_flag_button(self.toggle_highlight_action, text="NodeHilit", button_key='highlight')
            if hasattr(self, 'toggle_sync_action'):
                _add_flag_button(self.toggle_sync_action, text="Sync", button_key='sync')
            if hasattr(self, 'toggle_symbols_action'):
                _add_flag_button(self.toggle_symbols_action, text="<>", button_key='symbols')
            if hasattr(self, 'toggle_tags_action'):
                _add_flag_button(self.toggle_tags_action, text="Tags", button_key='tags')
            if hasattr(self, 'toggle_values_action'):
                _add_flag_button(self.toggle_values_action, text="Vals", button_key='values')
            if hasattr(self, 'update_tree_toggle'):
                _add_flag_button(self.update_tree_toggle, text="UpdTree", button_key='updtree')

            self.status_bar.addPermanentWidget(flags_bar)
        except Exception as e:
            print(f"Flags bar init error: {e}")

        # Removed duplicate rightmost text indicator to avoid redundancy

    def _update_flags_indicator(self):
        """Update compact flags indicator in the status bar."""
        try:
            parts = []
            # Sync
            if hasattr(self, 'toggle_sync_action'):
                parts.append(f"Sync:{'on' if self.toggle_sync_action.isChecked() else 'off'}")
            # Symbols visibility
            if hasattr(self, 'toggle_symbols_action'):
                parts.append(f"<>:{'hide' if self.toggle_symbols_action.isChecked() else 'show'}")
            # Tags visibility
            if hasattr(self, 'toggle_tags_action'):
                parts.append(f"Tags:{'hide' if self.toggle_tags_action.isChecked() else 'show'}")
            # Values visibility
            if hasattr(self, 'toggle_values_action'):
                parts.append(f"Vals:{'hide' if self.toggle_values_action.isChecked() else 'show'}")
            # Friendly labels in tree
            if hasattr(self, 'toggle_friendly_labels_action'):
                parts.append(f"Lbls:{'friendly' if self.toggle_friendly_labels_action.isChecked() else 'raw'}")
            # Update tree on tab switch
            if hasattr(self, 'update_tree_toggle'):
                parts.append(f"Upd:{'on' if self.update_tree_toggle.isChecked() else 'off'}")
            # Hide leaf nodes in tree
            if hasattr(self, 'toggle_hide_leaves_action'):
                parts.append(f"Leaves:{'hide' if self.toggle_hide_leaves_action.isChecked() else 'show'}")
            # Set compact string
            if hasattr(self, 'flags_label') and self.flags_label:
                self.flags_label.setText(" ".join(parts))
        except Exception as e:
            print(f"Flags indicator update error: {e}")
        
        # Set status_label reference on xml_tree after it's created
        if hasattr(self, 'xml_tree'):
            self.xml_tree.status_label = self.status_label

    def _update_button_state(self, button_key: str, is_active: bool):
        """Update button appearance to reflect its ON/OFF state."""
        if not hasattr(self, 'status_buttons') or button_key not in self.status_buttons:
            return
        
        btn = self.status_buttons[button_key]
        if is_active:
            # Active state: eye-safe teal/cyan background instead of bright green
            btn.setStyleSheet("QToolButton { background-color: #5B9AA0; color: white; border: 1px solid #4A8A90; font-size: 9px; max-height: 22px; padding: 1px 3px; margin: 0px; }")
        else:
            # Inactive state: default appearance with proper sizing
            btn.setStyleSheet("font-size: 9px; max-height: 22px; padding: 1px 3px; margin: 0px;")

    def _get_settings(self) -> QSettings:
        return QSettings("visxml.net", "VisualXmlEditor")

    def _save_flag(self, key: str, value: bool):
        try:
            s = self._get_settings()
            s.setValue(f"flags/{key}", value)
        except Exception as e:
            print(f"Error saving flag '{key}': {e}")

    def _load_persisted_flags(self):
        """Load persisted flags and apply them to actions and UI state."""
        s = self._get_settings()
        # Helper to read boolean with default
        def read_bool(name: str, default: bool) -> bool:
            try:
                v = s.value(f"flags/{name}")
                if v is None:
                    return default
                # QSettings may store as string "true"/"false" or QVariant
                if isinstance(v, bool):
                    return v
                if isinstance(v, str):
                    return v.lower() in ("1", "true", "yes", "on")
                return bool(v)
            except Exception:
                return default

        # Apply to actions without emitting toggled signals
        # Sync
        if hasattr(self, 'toggle_sync_action'):
            val = read_bool('sync_enabled', False)
            try:
                self.toggle_sync_action.blockSignals(True)
                self.toggle_sync_action.setChecked(val)
                self.toggle_sync_action.blockSignals(False)
            except Exception:
                pass
            self.sync_enabled = val
            # Update button state
            self._update_button_state('sync', val)
        # Symbols
        if hasattr(self, 'toggle_symbols_action'):
            val = read_bool('hide_symbols', False)
            try:
                self.toggle_symbols_action.blockSignals(True)
                self.toggle_symbols_action.setChecked(val)
                self.toggle_symbols_action.blockSignals(False)
            except Exception:
                pass
            if hasattr(self, 'xml_editor') and hasattr(self.xml_editor, 'highlighter'):
                self.xml_editor.highlighter.set_visibility_options(hide_symbols=val)
            # Update button state
            self._update_button_state('symbols', val)
        # Tags
        if hasattr(self, 'toggle_tags_action'):
            val = read_bool('hide_tags', False)
            try:
                self.toggle_tags_action.blockSignals(True)
                self.toggle_tags_action.setChecked(val)
                self.toggle_tags_action.blockSignals(False)
            except Exception:
                pass
            if hasattr(self, 'xml_editor') and hasattr(self.xml_editor, 'highlighter'):
                self.xml_editor.highlighter.set_visibility_options(hide_tags=val)
            # Update button state
            self._update_button_state('tags', val)
        # Values
        if hasattr(self, 'toggle_values_action'):
            val = read_bool('hide_values', False)
            try:
                self.toggle_values_action.blockSignals(True)
                self.toggle_values_action.setChecked(val)
                self.toggle_values_action.blockSignals(False)
            except Exception:
                pass
            if hasattr(self, 'xml_editor') and hasattr(self.xml_editor, 'highlighter'):
                self.xml_editor.highlighter.set_visibility_options(hide_values=val)
            # Update button state
            self._update_button_state('values', val)
        # Friendly labels
        if hasattr(self, 'toggle_friendly_labels_action'):
            val = read_bool('friendly_labels', True)
            try:
                self.toggle_friendly_labels_action.blockSignals(True)
                self.toggle_friendly_labels_action.setChecked(val)
                self.toggle_friendly_labels_action.blockSignals(False)
            except Exception:
                pass
            if hasattr(self, 'xml_tree') and self.xml_tree:
                self.xml_tree.use_friendly_labels = val
                self.xml_tree.refresh_labels()
        # Update tree on tab switch (both actions reflect)
        val_upd = read_bool('update_tree_on_tab_switch', True)
        if hasattr(self, 'update_tree_toggle'):
            try:
                self.update_tree_toggle.blockSignals(True)
                self.update_tree_toggle.setChecked(val_upd)
                self.update_tree_toggle.blockSignals(False)
            except Exception:
                pass
            # Update button state
            self._update_button_state('updtree', val_upd)
        if hasattr(self, 'toggle_update_tree_view_action'):
            try:
                self.toggle_update_tree_view_action.blockSignals(True)
                self.toggle_update_tree_view_action.setChecked(val_upd)
                self.toggle_update_tree_view_action.blockSignals(False)
            except Exception:
                pass
        self.update_tree_on_tab_switch = val_upd
        # Hide leaves
        if hasattr(self, 'toggle_hide_leaves_action'):
            val = read_bool('hide_leaves', True)
            try:
                self.toggle_hide_leaves_action.blockSignals(True)
                self.toggle_hide_leaves_action.setChecked(val)
                self.toggle_hide_leaves_action.blockSignals(False)
            except Exception:
                pass
            if hasattr(self, 'xml_tree') and self.xml_tree:
                self.xml_tree.set_hide_leaves(val)
        # Breadcrumbs
        if hasattr(self, 'toggle_breadcrumb_action'):
            val = read_bool('show_breadcrumbs', False)
            try:
                self.toggle_breadcrumb_action.blockSignals(True)
                self.toggle_breadcrumb_action.setChecked(val)
                self.toggle_breadcrumb_action.blockSignals(False)
            except Exception:
                pass
            try:
                self.breadcrumb_label.setVisible(val)
            except Exception:
                pass
        # Bottom panel
        if hasattr(self, 'toggle_bottom_panel_action'):
            val = read_bool('show_bottom_panel', False)
            try:
                self.toggle_bottom_panel_action.blockSignals(True)
                self.toggle_bottom_panel_action.setChecked(val)
                self.toggle_bottom_panel_action.blockSignals(False)
            except Exception:
                pass
            try:
                self.bottom_dock.setVisible(val)
            except Exception:
                pass
        # File navigator
        if hasattr(self, 'toggle_file_navigator_action'):
            val = read_bool('show_file_navigator', True)
            try:
                self.toggle_file_navigator_action.blockSignals(True)
                self.toggle_file_navigator_action.setChecked(val)
                self.toggle_file_navigator_action.blockSignals(False)
            except Exception:
                pass
            try:
                self.file_navigator.setVisible(val)
            except Exception:
                pass
            # Sync toolbar toggle if present
            try:
                if hasattr(self, 'toggle_file_tree_toolbar_action'):
                    self.toggle_file_tree_toolbar_action.blockSignals(True)
                    self.toggle_file_tree_toolbar_action.setChecked(val)
                    self.toggle_file_tree_toolbar_action.blockSignals(False)
            except Exception:
                pass

        # Exchange mode (semi-auto toggle)
        if hasattr(self, 'exchange_mode_action'):
            val = read_bool('exchange_semi_mode', True)
            try:
                self.exchange_mode_action.blockSignals(True)
                self.exchange_mode_action.setChecked(val)
                self.exchange_mode_action.blockSignals(False)
            except Exception:
                pass
            self.exchange_mode = 'semi' if val else 'manual'

        # Auto-hide preferences
        toolbar_autohide_val = read_bool('toolbar_autohide', True)
        tree_header_autohide_val = read_bool('tree_header_autohide', True)
        tree_column_header_autohide_val = read_bool('tree_column_header_autohide', True)
        tab_bar_autohide_val = read_bool('tab_bar_autohide', True)
        
        if hasattr(self, 'toggle_toolbar_autohide_action'):
            try:
                self.toggle_toolbar_autohide_action.blockSignals(True)
                self.toggle_toolbar_autohide_action.setChecked(toolbar_autohide_val)
                self.toggle_toolbar_autohide_action.blockSignals(False)
            except Exception:
                pass
        
        if hasattr(self, 'toggle_tree_header_autohide_action'):
            try:
                self.toggle_tree_header_autohide_action.blockSignals(True)
                self.toggle_tree_header_autohide_action.setChecked(tree_header_autohide_val)
                self.toggle_tree_header_autohide_action.blockSignals(False)
            except Exception:
                pass
        
        if hasattr(self, 'toggle_tree_column_header_autohide_action'):
            try:
                self.toggle_tree_column_header_autohide_action.blockSignals(True)
                self.toggle_tree_column_header_autohide_action.setChecked(tree_column_header_autohide_val)
                self.toggle_tree_column_header_autohide_action.blockSignals(False)
            except Exception:
                pass
        
        if hasattr(self, 'toggle_tab_bar_autohide_action'):
            try:
                self.toggle_tab_bar_autohide_action.blockSignals(True)
                self.toggle_tab_bar_autohide_action.setChecked(tab_bar_autohide_val)
                self.toggle_tab_bar_autohide_action.blockSignals(False)
            except Exception:
                pass
        
        # Apply auto-hide after UI is fully rendered (use QTimer to delay)
        def apply_autohide():
            try:
                print(f"DEBUG: Applying auto-hide - toolbar:{toolbar_autohide_val}, tree_header:{tree_header_autohide_val}, tree_column:{tree_column_header_autohide_val}, tab_bar:{tab_bar_autohide_val}")
                if hasattr(self, 'toolbar_auto_hide'):
                    self.toolbar_auto_hide.set_auto_hide_enabled(toolbar_autohide_val)
                    print(f"DEBUG: Toolbar auto-hide applied, enabled={self.toolbar_auto_hide.auto_hide_enabled}")
                if hasattr(self, 'tree_header_auto_hide'):
                    self.tree_header_auto_hide.set_auto_hide_enabled(tree_header_autohide_val)
                    print(f"DEBUG: Tree header auto-hide applied, enabled={self.tree_header_auto_hide.auto_hide_enabled}")
                if hasattr(self, 'tree_column_header_auto_hide'):
                    self.tree_column_header_auto_hide.set_auto_hide_enabled(tree_column_header_autohide_val)
                    print(f"DEBUG: Tree column header auto-hide applied, enabled={self.tree_column_header_auto_hide.auto_hide_enabled}")
                if hasattr(self, 'tab_bar_auto_hide'):
                    self.tab_bar_auto_hide.set_auto_hide_enabled(tab_bar_autohide_val)
                    print(f"DEBUG: Tab bar auto-hide applied, enabled={self.tab_bar_auto_hide.auto_hide_enabled}")
            except Exception as e:
                print(f"DEBUG: Error applying auto-hide: {e}")
                import traceback
                traceback.print_exc()
        
        # Delay application to ensure UI is rendered
        QTimer.singleShot(100, apply_autohide)
        
        # Finally, refresh flags indicator
        try:
            self._update_flags_indicator()
        except Exception:
            pass
        
        # Set status_label reference on xml_tree after it's created
        if hasattr(self, 'xml_tree'):
            self.xml_tree.status_label = self.status_label

        # Apply persisted theme AFTER visibility options so they are preserved
        try:
            is_dark = read_bool('dark_theme', True)
            if is_dark:
                self.set_dark_theme()
            else:
                self.set_light_theme()
        except Exception:
            pass

        # Reapply visibility options after theme to ensure they take effect
        try:
            if hasattr(self, 'xml_editor') and hasattr(self.xml_editor, 'highlighter'):
                hide_syms = read_bool('hide_symbols', False)
                hide_tgs = read_bool('hide_tags', False)
                hide_vals = read_bool('hide_values', False)
                print(f"DEBUG: Reapplying visibility - symbols:{hide_syms}, tags:{hide_tgs}, values:{hide_vals}")
                self.xml_editor.highlighter.set_visibility_options(
                    hide_symbols=hide_syms,
                    hide_tags=hide_tgs,
                    hide_values=hide_vals
                )
                print(f"DEBUG: Highlighter state after reapply - symbols:{self.xml_editor.highlighter.hide_symbols}, tags:{self.xml_editor.highlighter.hide_tags}, values:{self.xml_editor.highlighter.hide_values}")
        except Exception as e:
            print(f"Error reapplying visibility options: {e}")

        # Apply persisted language selection and update current editor
        try:
            s = self._get_settings()
            name = s.value("language/name")
            if isinstance(name, str) and name:
                if hasattr(self, 'language_combo') and self.language_combo:
                    try:
                        self.language_combo.blockSignals(True)
                        for i in range(self.language_combo.count()):
                            if self.language_combo.itemText(i) == name:
                                self.language_combo.setCurrentIndex(i)
                                break
                        self.language_combo.blockSignals(False)
                    except Exception:
                        pass
            if hasattr(self, 'xml_editor') and isinstance(self.xml_editor, XmlEditorWidget):
                try:
                    self._apply_selected_language_to_editor(self.xml_editor)
                except Exception:
                    pass
        except Exception:
            pass
    
    def _create_file_navigator(self):
        """Create dockable file navigator widget"""
        self.file_navigator = FileNavigatorWidget(self)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.file_navigator)
        
        # Connect file navigator signals
        self.file_navigator.file_opened.connect(self._open_file_from_navigator)
        self.file_navigator.combine_requested.connect(self._show_combine_dialog)

    def _set_file_navigator_visible(self, visible: bool):
        """Set file navigator dock visibility and sync toggle action state."""
        try:
            self.file_navigator.setVisible(visible)
            if hasattr(self, 'show_file_navigator_action'):
                self.show_file_navigator_action.setChecked(visible)
            if hasattr(self, 'status_label') and self.status_label:
                self.status_label.setText(f"File navigator {'shown' if visible else 'hidden'}")
        except Exception:
            pass
    
    def _setup_auto_hide(self):
        """Setup auto-hide functionality for toolbar and tree header"""
        try:
            # Get toolbar reference
            self.toolbar = self.findChild(QToolBar, "Main")
            if not self.toolbar:
                # Fallback: get first toolbar
                toolbars = self.findChildren(QToolBar)
                if toolbars:
                    self.toolbar = toolbars[0]
            
            # Create auto-hide manager for toolbar
            if self.toolbar:
                self.toolbar_auto_hide = AutoHideManager(
                    self.toolbar,
                    hover_zone_height=3,
                    animation_duration=200,
                    hide_delay=500
                )
                
                # Create toolbar hover zone at top of central widget
                main_layout = self.centralWidget().layout()
                if main_layout:
                    self.toolbar_hover_zone = self.toolbar_auto_hide.create_hover_zone(self.centralWidget())
                    main_layout.insertWidget(0, self.toolbar_hover_zone)
                    self.toolbar_hover_zone.hide()  # Hidden initially
            
            # Find the tree label and level header container
            tree_label = None
            left_panel = self.xml_tree.parent()
            
            if left_panel:
                for child in left_panel.findChildren(QLabel):
                    if child.text() == "XML Structure":
                        tree_label = child
                        break
                
                # Create container for tree header elements (label + level buttons)
                self.tree_header_widget = QWidget()
                tree_header_layout = QVBoxLayout()
                tree_header_layout.setContentsMargins(0, 0, 0, 0)
                tree_header_layout.setSpacing(0)
                self.tree_header_widget.setLayout(tree_header_layout)
                
                # Move tree label into the tree header widget
                if tree_label:
                    parent_layout = tree_label.parent().layout()
                    if parent_layout:
                        parent_layout.removeWidget(tree_label)
                        tree_header_layout.addWidget(tree_label)
                
                # Move level header container into the tree header widget
                if hasattr(self, 'level_header_container'):
                    parent_layout = self.level_header_container.parent().layout()
                    if parent_layout:
                        parent_layout.removeWidget(self.level_header_container)
                        tree_header_layout.addWidget(self.level_header_container)
                
                # Insert tree header widget back into the left panel at the top
                left_layout = left_panel.layout()
                if left_layout:
                    left_layout.insertWidget(0, self.tree_header_widget)
                
                # Force layout update to get proper size
                self.tree_header_widget.updateGeometry()
                QApplication.processEvents()
                
                # Create auto-hide manager for tree header
                self.tree_header_auto_hide = AutoHideManager(
                    self.tree_header_widget,
                    hover_zone_height=3,
                    animation_duration=200,
                    hide_delay=500
                )
                
                # Set a reasonable max height for tree header (label + level buttons)
                # This prevents it from capturing the entire panel height
                self.tree_header_auto_hide.original_height = 50  # Reasonable height for header elements
                
                # Create tree header hover zone at top of tree panel
                self.tree_header_hover_zone = self.tree_header_auto_hide.create_hover_zone(left_panel)
                left_layout.insertWidget(0, self.tree_header_hover_zone)
                self.tree_header_hover_zone.hide()  # Hidden initially
            
            # Setup auto-hide for tree column header ("Element", "Value")
            if hasattr(self, 'xml_tree') and self.xml_tree:
                tree_column_header = self.xml_tree.header()
                if tree_column_header:
                    self.tree_column_header_auto_hide = AutoHideManager(
                        tree_column_header,
                        hover_zone_height=3,
                        animation_duration=200,
                        hide_delay=500
                    )
                    
                    # Create hover zone for tree column header
                    if left_panel and left_layout:
                        self.tree_column_header_hover_zone = self.tree_column_header_auto_hide.create_hover_zone(left_panel)
                        # Insert after tree header hover zone and tree header widget
                        insert_index = 2 if hasattr(self, 'tree_header_widget') else 0
                        left_layout.insertWidget(insert_index, self.tree_column_header_hover_zone)
                        self.tree_column_header_hover_zone.hide()
            
            # Setup auto-hide for tab bar (Document 1, etc.)
            if hasattr(self, 'tab_widget') and self.tab_widget:
                tab_bar = self.tab_widget.tabBar()
                if tab_bar:
                    self.tab_bar_auto_hide = AutoHideManager(
                        tab_bar,
                        hover_zone_height=3,
                        animation_duration=200,
                        hide_delay=500
                    )
                    
                    # Create hover zone for tab bar
                    right_panel = self.tab_widget.parent()
                    if right_panel:
                        right_layout = right_panel.layout()
                        if right_layout:
                            self.tab_bar_hover_zone = self.tab_bar_auto_hide.create_hover_zone(right_panel)
                            # Insert before tab widget
                            tab_widget_index = right_layout.indexOf(self.tab_widget)
                            if tab_widget_index >= 0:
                                right_layout.insertWidget(tab_widget_index, self.tab_bar_hover_zone)
                            else:
                                right_layout.insertWidget(0, self.tab_bar_hover_zone)
                            self.tab_bar_hover_zone.hide()
        
        except Exception as e:
            print(f"Auto-hide setup error: {e}")
            import traceback
            traceback.print_exc()
    
    def _connect_signals(self):
        """Connect signals"""
        self.xml_editor.content_changed.connect(self.on_content_changed)
        self.xml_editor.cursor_position_changed.connect(self.on_cursor_changed)
        self.xml_tree.node_selected.connect(self.on_tree_node_selected)
        # Find results double-click → navigate to match
        try:
            self.bottom_panel.find_results.itemDoubleClicked.connect(self._on_find_result_double_clicked)
        except Exception:
            pass
        # Bookmarks list double-click → navigate to line
        try:
            self.bottom_panel.bookmark_list.itemDoubleClicked.connect(self._on_bookmark_item_double_clicked)
        except Exception:
            pass

    def _on_find_result_double_clicked(self, item):
        """Navigate to the match when a find result is double-clicked"""
        try:
            row = self.bottom_panel.find_results.row(item)
            if 0 <= row < len(self.last_search_results):
                self.current_search_index = row
                self._navigate_to_search_result(row)
        except Exception as e:
            print(f"Find result double-click error: {e}")

    def _on_bookmark_item_double_clicked(self, item):
        """Navigate to the line when a bookmark item is double-clicked"""
        try:
            # Prefer stored line number in item data
            line = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(line, int) and line > 0:
                self.goto_line(line)
            else:
                # Fallback: parse from text "N: ..."
                text = item.text()
                try:
                    num_str = text.split(":", 1)[0].strip()
                    line = int(num_str)
                    self.goto_line(line)
                except Exception:
                    pass
        except Exception as e:
            print(f"Bookmark item double-click error: {e}")

    def _on_tab_changed(self, index: int):
        """Handle tab change: swap current editor reference and optionally update tree"""
        try:
            new_widget = self.tab_widget.widget(index)
            if not isinstance(new_widget, XmlEditorWidget):
                return
            # Disconnect old editor signals
            try:
                self.xml_editor.content_changed.disconnect(self.on_content_changed)
            except Exception:
                pass
            try:
                self.xml_editor.cursor_position_changed.disconnect(self.on_cursor_changed)
            except Exception:
                pass
            # Update reference and connect signals
            self.xml_editor = new_widget
            self.xml_editor.content_changed.connect(self.on_content_changed)
            self.xml_editor.cursor_position_changed.connect(self.on_cursor_changed)
            # Apply selected language to the new active editor
            try:
                self._apply_selected_language_to_editor(self.xml_editor)
            except Exception:
                pass
            # Update tree if toggle enabled
            if getattr(self, 'update_tree_on_tab_switch', True):
                content = self.xml_editor.get_content()
                self.xml_tree.populate_tree(content)
        except Exception as e:
            print(f"Error on tab change: {e}")

    def _close_tab(self, index: int):
        """Close tab and clean up references"""
        widget = self.tab_widget.widget(index)
        self.tab_widget.removeTab(index)
        # If closing active tab, _on_tab_changed will update reference; ensure we have at least one tab
        if self.tab_widget.count() == 0:
            new_editor = XmlEditorWidget()
            self.tab_widget.addTab(new_editor, "Document")
            self.xml_editor = new_editor
            self._connect_signals()

    def _create_editor_tab(self, title: str, content: str):
        """Create a new editor tab with given title and content, return editor and index"""
        editor = XmlEditorWidget()
        editor.set_content(content)
        index = self.tab_widget.addTab(editor, title)
        # Switch to the new tab
        self.tab_widget.setCurrentIndex(index)
        # Apply selected language to the new editor
        try:
            self._apply_selected_language_to_editor(editor)
        except Exception:
            pass
        return editor, index

    # --- Folding helpers and tree-sync ---
    def _compute_range_lines_at_cursor(self):
        """Find the smallest enclosing XML element range at the cursor and return (start_line, end_line)."""
        try:
            editor = self.xml_editor
            text = editor.get_content()
            cur = editor.textCursor()
            pos = cur.position()
            ranges = self._compute_enclosing_xml_ranges(text)
            if not ranges:
                return None
            containing = [r for r in ranges if r[1] <= pos <= r[2]]
            if not containing:
                return None
            target = sorted(containing, key=lambda r: (r[2] - r[1]))[0]
            start_pos, end_pos = target[1], target[2]
            # Map positions to 1-based line numbers
            lines = text.split('\n')
            def _pos_to_line(p):
                # Count '\n' up to position
                cnt = text[:p].count('\n') + 1
                return cnt
            start_line = _pos_to_line(start_pos)
            end_line = _pos_to_line(end_pos)
            return (start_line, end_line)
        except Exception as e:
            print(f"Range-at-cursor error: {e}")
            return None

    def fold_current_element(self):
        """Fold the current XML element under the cursor."""
        rng = self._compute_range_lines_at_cursor()
        if rng:
            try:
                self.xml_editor.fold_lines(rng[0], rng[1])
                if hasattr(self, 'status_label') and self.status_label:
                    self.status_label.setText(f"Folded element to lines {rng[0]}..{rng[1]}")
            except Exception as e:
                print(f"Fold current element error: {e}")

    def unfold_current_element(self):
        """Unfold the current XML element under the cursor."""
        rng = self._compute_range_lines_at_cursor()
        if rng:
            try:
                self.xml_editor.unfold_lines(rng[0], rng[1])
                if hasattr(self, 'status_label') and self.status_label:
                    self.status_label.setText(f"Unfolded element at lines {rng[0]}..{rng[1]}")
            except Exception as e:
                print(f"Unfold current element error: {e}")

    def _find_range_for_tree_item(self, item):
        """Compute (start_line, end_line) for a given tree item by using its opening tag line and range scan."""
        try:
            if not item or not hasattr(item, 'xml_node') or not item.xml_node:
                return None
            node = item.xml_node
            content = self.xml_editor.get_content()
            if not content:
                return None
            target_line = getattr(node, 'line_number', 0)
            if target_line <= 0:
                return None
            # Convert line to an approximate position
            lines = content.split('\n')
            if target_line > len(lines):
                return None
            start_pos_guess = sum(len(l) + 1 for l in lines[: max(0, target_line - 1)])
            ranges = self._compute_enclosing_xml_ranges(content)
            # Find smallest range that contains the line
            def _pos_to_line(p):
                return content[:p].count('\n') + 1
            candidates = []
            for r in ranges:
                s_line = _pos_to_line(r[1])
                e_line = _pos_to_line(r[2])
                if s_line <= target_line <= e_line:
                    candidates.append((s_line, e_line))
            if not candidates:
                return None
            # Pick smallest span
            candidates.sort(key=lambda x: (x[1] - x[0]))
            return candidates[0]
        except Exception as e:
            print(f"Tree item range error: {e}")
            return None

    def _on_tree_item_collapsed(self, item):
        """Fold corresponding element in editor when a tree item collapses."""
        try:
            rng = self._find_range_for_tree_item(item)
            if rng:
                self.xml_editor.fold_lines(rng[0], rng[1])
        except Exception as e:
            print(f"Tree collapse sync error: {e}")

    def _on_tree_item_expanded(self, item):
        """Unfold corresponding element in editor when a tree item expands."""
        try:
            rng = self._find_range_for_tree_item(item)
            if rng:
                self.xml_editor.unfold_lines(rng[0], rng[1])
        except Exception as e:
            print(f"Tree expand sync error: {e}")

    # --- F4/F5 helpers ---
    def _compute_enclosing_xml_ranges(self, text: str):
        """Compute element ranges using a simple stack-based parser. Returns list of (tag, start, end)."""
        ranges = []
        stack = []  # list of (tag, start_index)
        # Handle comments and CDATA and PIs by temporarily removing them to avoid mis-parsing
        # Record their spans as atomic ranges too
        comment_pattern = re.compile(r"<!--.*?-->", re.DOTALL)
        cdata_pattern = re.compile(r"<!\[CDATA\[.*?\]\]>", re.DOTALL)
        pi_pattern = re.compile(r"<\?.*?\?>", re.DOTALL)
        doctype_pattern = re.compile(r"<!DOCTYPE.*?>", re.DOTALL)
        special_spans = []
        for pat in (comment_pattern, cdata_pattern, pi_pattern, doctype_pattern):
            for m in pat.finditer(text):
                special_spans.append(("special", m.start(), m.end()))
        # Support Unicode tag names (including Cyrillic), namespaces, and punctuation
        # Tag name: one or more non-space, non-'>' and non'/' characters
        tag_pattern = re.compile(r"<(/?)([^\s>/]+)([^>]*)>", re.UNICODE)
        i = 0
        for m in tag_pattern.finditer(text):
            # Skip special spans region
            skip = False
            for _, s, e in special_spans:
                if m.start() >= s and m.start() < e:
                    skip = True
                    break
            if skip:
                continue
            is_close = m.group(1) == '/'
            tag = m.group(2)
            rest = m.group(3) or ''
            full_end = m.end()
            # Detect self-closing tags like <tag .../>
            self_closing = rest.rstrip().endswith('/')
            if not is_close and not self_closing:
                stack.append((tag, m.start()))
            elif is_close:
                # pop matching tag
                for si in range(len(stack) - 1, -1, -1):
                    if stack[si][0] == tag:
                        open_tag, start_idx = stack.pop(si)
                        ranges.append((tag, start_idx, full_end))
                        break
            else:
                # self-closing element
                ranges.append((tag, m.start(), full_end))
        # Add special spans as ranges
        ranges.extend(special_spans)
        # Sort by span size (smallest first) for deepest-first selection
        ranges.sort(key=lambda r: (r[2] - r[1]))
        return ranges

    def select_xml_node_or_parent(self):
        """Select XML node at cursor; repeated presses select parent element."""
        editor = self.xml_editor
        text = editor.get_content()
        cursor = editor.textCursor()
        pos = cursor.position()
        # Compute containing ranges at cursor and sort deepest->root
        ranges = self._compute_enclosing_xml_ranges(text)
        containing_sorted = sorted([r for r in ranges if r[1] <= pos <= r[2]], key=lambda r: (r[2] - r[1]))
        if not containing_sorted:
            # Fallback: select the nearest XML element range to the cursor
            if ranges:
                def _distance_to_range(p, r):
                    if r[1] <= p <= r[2]:
                        return 0
                    return min(abs(p - r[1]), abs(p - r[2]))
                nearest = min(ranges, key=lambda r: _distance_to_range(pos, r))
                start, end = nearest[1], nearest[2]
                new_cursor = editor.textCursor()
                new_cursor.setPosition(start)
                new_cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
                editor.setTextCursor(new_cursor)
                # Sync tree to the newly selected element
                try:
                    line = editor.textCursor().blockNumber() + 1
                    self._sync_tree_to_cursor(line)
                except Exception:
                    pass
                return
            # If no ranges at all (empty/invalid XML), fall back to line selection
            cursor.select(QTextCursor.SelectionType.LineUnderCursor)
            editor.setTextCursor(cursor)
            return
        if not cursor.hasSelection():
            # First press: select deepest element
            target = containing_sorted[0]
        else:
            sel_start = min(cursor.anchor(), cursor.position())
            sel_end = max(cursor.anchor(), cursor.position())
            # Find current selection in the chain
            idx = next((i for i, r in enumerate(containing_sorted) if r[1] == sel_start and r[2] == sel_end), None)
            if idx is None:
                # If current selection isn't one of the known ranges, select deepest first
                target = containing_sorted[0]
            else:
                # Next press: move to immediate parent if available, else keep current
                parent_idx = min(idx + 1, len(containing_sorted) - 1)
                target = containing_sorted[parent_idx]
        start, end = target[1], target[2]
        new_cursor = editor.textCursor()
        new_cursor.setPosition(start)
        new_cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        editor.setTextCursor(new_cursor)
        # Sync tree to the newly selected element
        try:
            line = editor.textCursor().blockNumber() + 1
            self._sync_tree_to_cursor(line)
        except Exception:
            pass

    def move_selection_to_new_tab_with_link(self):
        """Move selected text to a new tab and leave a link comment in place."""
        editor = self.xml_editor
        cursor = editor.textCursor()
        if not cursor.hasSelection():
            # If nothing selected, select element under cursor
            self.select_xml_node_or_parent()
            cursor = editor.textCursor()
            if not cursor.hasSelection():
                return
        start = min(cursor.anchor(), cursor.position())
        end = max(cursor.anchor(), cursor.position())
        text = editor.get_content()
        selected_text = text[start:end]
        # Create new tab
        if not hasattr(self, 'tab_link_counter'):
            self.tab_link_counter = 1
        link_id = f"tab-{self.tab_link_counter}"
        self.tab_link_counter += 1
        tab_title = f"Subdoc {self.tab_link_counter - 1}"
        sub_editor, idx = self._create_editor_tab(tab_title, selected_text)
        # Map link id to editor
        if not hasattr(self, 'tab_link_map'):
            self.tab_link_map = {}
        self.tab_link_map[link_id] = sub_editor
        # Replace selection with link comment
        link_comment = f"<!-- TABREF: {link_id} -->"
        new_cursor = editor.textCursor()
        new_cursor.setPosition(start)
        new_cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
        new_cursor.insertText(link_comment)
        editor.setTextCursor(new_cursor)
        # Optionally update tree if toggle enabled
        if getattr(self, 'update_tree_on_tab_switch', True):
            self.xml_tree.populate_tree(editor.get_content())
        # Status update
        if hasattr(self, 'status_label') and self.status_label:
            self.status_label.setText(f"Moved selection to '{tab_title}', inserted link {link_id}")

    def replace_link_with_tab_content(self):
        """Replace a TABREF comment under cursor with the content from its tab."""
        editor = self.xml_editor
        text = editor.get_content()
        cursor = editor.textCursor()
        pos = cursor.position()
        # Find TABREF comment around cursor
        pattern = re.compile(r"<!--\s*TABREF:\s*([A-Za-z0-9_\-]+)\s*-->")
        # Search a window around the cursor to find the comment boundaries
        start_search = max(0, pos - 200)
        end_search = min(len(text), pos + 200)
        segment = text[start_search:end_search]
        m = pattern.search(segment)
        if not m:
            # Try global search
            m2 = pattern.search(text)
            if not m2:
                return
            # Use global match
            link_id = m2.group(1)
            abs_start = m2.start()
            abs_end = m2.end()
        else:
            link_id = m.group(1)
            abs_start = start_search + m.start()
            abs_end = start_search + m.end()
        # Lookup tab content
        if not hasattr(self, 'tab_link_map') or link_id not in self.tab_link_map:
            return
        sub_editor = self.tab_link_map[link_id]
        sub_content = sub_editor.get_content()
        # Replace the comment with content
        new_cursor = editor.textCursor()
        new_cursor.setPosition(abs_start)
        new_cursor.setPosition(abs_end, QTextCursor.MoveMode.KeepAnchor)
        new_cursor.insertText(sub_content)
        editor.setTextCursor(new_cursor)
        # Optionally update tree
        if getattr(self, 'update_tree_on_tab_switch', True):
            self.xml_tree.populate_tree(editor.get_content())
        if hasattr(self, 'status_label') and self.status_label:
            self.status_label.setText(f"Replaced link {link_id} with tab content")
    
    def new_file(self):
        """Create new file"""
        self.current_file = None
        self.xml_editor.set_content("")
        self.xml_tree.clear()
        self.setWindowTitle("Lotus Xml Editor - New File")
        self.status_label.setText("New file created")
        
        # Clear recent files list when creating a new file
        # This ensures that closing the app after "New File" doesn't reopen the previous file
        self.recent_files = []
        self._save_recent_files()
    
    def open_file(self, file_path=None):
        """Open XML file"""
        if file_path is None:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Open XML File", "", "XML Files (*.xml);;All Files (*.*)"
            )
        
        if file_path:
            try:
                # Check file size first
                file_size = os.path.getsize(file_path)
                
                # For large files (>1MB), show progress and use chunked reading
                if file_size > 1024 * 1024:
                    self.status_label.setText(f"Loading large file ({file_size / 1024 / 1024:.1f} MB)...")
                    QApplication.processEvents()  # Update UI
                    
                    # Read large files in chunks to avoid memory issues
                    content = self._read_large_file(file_path)
                else:
                    # Read small files normally
                    with open(file_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                
                self.xml_editor.set_content(content)
                self.xml_tree.populate_tree(content)
                
                # Apply saved highlighter visibility settings
                self._apply_highlighter_settings()
                
                self.current_file = file_path
                self.setWindowTitle(f"Lotus Xml Editor - {os.path.basename(file_path)}")
                self.status_label.setText(f"Opened: {file_path}")
                
                # Update encoding label
                self.encoding_label.setText("UTF-8")
                
                # Add to recent files
                self._add_to_recent_files(file_path)
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open file: {str(e)}")
                self.status_label.setText("Ready")
    
    def _read_large_file(self, file_path: str) -> str:
        """Read large files efficiently using chunked reading"""
        content_parts = []
        chunk_size = 64 * 1024  # 64KB chunks
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                while True:
                    chunk = file.read(chunk_size)
                    if not chunk:
                        break
                    content_parts.append(chunk)
            
            return ''.join(content_parts)
        except UnicodeDecodeError:
            # Try with different encoding if UTF-8 fails
            try:
                with open(file_path, 'r', encoding='cp1251') as file:
                    while True:
                        chunk = file.read(chunk_size)
                        if not chunk:
                            break
                        content_parts.append(chunk)
                return ''.join(content_parts)
            except Exception as e:
                raise Exception(f"Failed to read file with any encoding: {str(e)}")
    
    def save_file(self):
        """Save current file"""
        if not self.current_file:
            self.save_file_as()
            return
        
        try:
            content = self.xml_editor.get_content()
            with open(self.current_file, 'w', encoding='utf-8') as file:
                file.write(content)
            
            self.status_label.setText(f"Saved: {self.current_file}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file: {str(e)}")
    
    def save_file_as(self):
        """Save file as"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save XML File", "", "XML Files (*.xml);;All Files (*.*)"
        )
        
        if file_path:
            self.current_file = file_path
            self.save_file()
            self.setWindowTitle(f"Lotus Xml Editor - {os.path.basename(file_path)}")
    
    def undo(self):
        """Undo last action"""
        self.xml_editor.undo()
    
    def redo(self):
        """Redo last action"""
        self.xml_editor.redo()
    
    def show_find_dialog(self):
        """Show find dialog"""
        dialog = FindDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            params = dialog.get_search_params()
            self.find_text(params)

    def show_replace_dialog(self):
        """Show replace dialog (modeless)"""
        try:
            if not hasattr(self, '_replace_dialog') or self._replace_dialog is None:
                self._replace_dialog = ReplaceDialog(self)
            # Pre-fill find with last search text if available
            if self.last_search_params and 'text' in self.last_search_params:
                try:
                    self._replace_dialog.find_input.setText(self.last_search_params['text'])
                    self._replace_dialog.case_sensitive.setChecked(self.last_search_params.get('case_sensitive', False))
                    self._replace_dialog.whole_word.setChecked(self.last_search_params.get('whole_word', False))
                    self._replace_dialog.use_regex.setChecked(self.last_search_params.get('use_regex', False))
                except Exception:
                    pass
            self._replace_dialog.show()
            self._replace_dialog.raise_()
            self._replace_dialog.activateWindow()
        except Exception as e:
            print(f"Error showing replace dialog: {e}")

    def replace_all_from_last_or_dialog(self):
        """Replace all using last search params if present; otherwise open dialog."""
        if self.last_search_params:
            params = dict(self.last_search_params)
            # Expect a replace value from the replace dialog if open
            repl = None
            try:
                if hasattr(self, '_replace_dialog') and self._replace_dialog:
                    repl = self._replace_dialog.replace_input.text()
            except Exception:
                pass
            if repl is None:
                repl = ""
            params['replace'] = repl
            self.replace_all(params)
        else:
            self.show_replace_dialog()

    def replace_text(self, params: dict):
        """Replace current match and navigate to next."""
        try:
            find_text = params.get('text', '')
            replace_text = params.get('replace', '')
            if not find_text:
                return
            # If no prior search or different params, perform a fresh search
            if (self.last_search_params is None or
                any(self.last_search_params.get(k) != params.get(k) for k in ['text','case_sensitive','whole_word','use_regex'])):
                self.find_text({
                    'text': find_text,
                    'case_sensitive': params.get('case_sensitive', False),
                    'whole_word': params.get('whole_word', False),
                    'use_regex': params.get('use_regex', False)
                })
                # After find_text, current_search_index is 0 if results exist
            if not self.last_search_results:
                return
            # Replace current selection
            cursor = self.xml_editor.textCursor()
            if not cursor.hasSelection():
                # Ensure selection for the current search index
                self._navigate_to_search_result(self.current_search_index if self.current_search_index >= 0 else 0)
                cursor = self.xml_editor.textCursor()
            # Insert replacement
            cursor.insertText(replace_text)
            self.xml_editor.setTextCursor(cursor)
            self.xml_editor.setFocus()
            # Update status
            try:
                self.status_label.setText("Replaced one occurrence")
            except Exception:
                pass
            # Recompute search results and navigate to next
            self.find_text({
                'text': find_text,
                'case_sensitive': params.get('case_sensitive', False),
                'whole_word': params.get('whole_word', False),
                'use_regex': params.get('use_regex', False)
            })
            if self.last_search_results:
                self.find_next()
        except Exception as e:
            print(f"Error replacing text: {e}")

    def replace_all(self, params: dict):
        """Replace all occurrences according to options."""
        try:
            find_text = params.get('text', '')
            replace_text = params.get('replace', '')
            if not find_text:
                return
            content = self.xml_editor.get_content()
            # Determine replacement strategy
            use_regex = params.get('use_regex', False)
            case_sensitive = params.get('case_sensitive', False)
            whole_word = params.get('whole_word', False)

            replaced_count = 0
            new_content = content

            if use_regex:
                flags = re.MULTILINE
                if not case_sensitive:
                    flags |= re.IGNORECASE
                pattern_text = find_text
                if whole_word:
                    pattern_text = fr"\b{pattern_text}\b"
                try:
                    pattern = re.compile(pattern_text, flags)
                    new_content, replaced_count = pattern.subn(replace_text, content)
                except re.error as e:
                    QMessageBox.critical(self, "Regex Error", f"Invalid regex: {e}")
                    return
            else:
                # Non-regex path
                if whole_word:
                    flags = 0 if case_sensitive else re.IGNORECASE
                    pattern = re.compile(fr"\b{re.escape(find_text)}\b", flags)
                    new_content, replaced_count = pattern.subn(replace_text, content)
                else:
                    if case_sensitive:
                        replaced_count = content.count(find_text)
                        new_content = content.replace(find_text, replace_text)
                    else:
                        # Case-insensitive replace using regex
                        pattern = re.compile(re.escape(find_text), re.IGNORECASE)
                        new_content, replaced_count = pattern.subn(replace_text, content)

            if replaced_count > 0:
                self.xml_editor.set_content(new_content)
                try:
                    self.status_label.setText(f"Replaced {replaced_count} occurrence(s)")
                except Exception:
                    pass
                # Clear previous search result selection
                self.last_search_results = []
                # Optionally repopulate tree from new content
                if getattr(self, 'update_tree_on_tab_switch', True):
                    try:
                        self.xml_tree.populate_tree(new_content)
                    except Exception:
                        pass
            else:
                try:
                    self.status_label.setText("No occurrences found to replace")
                except Exception:
                    pass
        except Exception as e:
            print(f"Error replacing all: {e}")
    
    def show_goto_dialog(self):
        """Show go to line dialog"""
        dialog = GoToLineDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            line_number = dialog.get_line_number()
            self.goto_line(line_number)

    def show_hotkey_help(self):
        """Show a dialog with a complete hotkey reference."""
        try:
            shortcuts = [
                "File:",
                "  Ctrl+N  New",
                "  Ctrl+O  Open",
                "  Ctrl+S  Save",
                "  Ctrl+Shift+S  Save As / Split XML (context)",
                "  Ctrl+Q  Exit",
                "",
                "Edit:",
                "  Ctrl+Z  Undo",
                "  Ctrl+Y  Redo",
                "  Ctrl+F  Find...",
                "  F3      Find Next",
                "  Ctrl+G  Go to Line...",
                "  Ctrl+L  Delete current line or selected lines",
                "  Ctrl+/  Toggle line comment (//) for selected lines",
                "  Ctrl+Shift+Up    Move current/selected lines up",
                "  Ctrl+Shift+Down  Move current/selected lines down",
                "",
                "Bookmarks:",
                "  Ctrl+B        Toggle Bookmark at cursor",
                "  Ctrl+Shift+B  Clear all bookmarks",
                "  F2            Next Bookmark",
                "  Alt+F2        Toggle Bookmark (menu)",
                "  Ctrl+Alt+F2   Previous Bookmark",
                "",
                "Numbered Bookmarks:",
                "  Ctrl+Shift+1..9  Set numbered bookmark (1-9)",
                "  Ctrl+1..9        Go to numbered bookmark (1-9)",
                "",
                "XML:",
                "  Ctrl+Shift+F  Format XML",
                "  Ctrl+Shift+V  Validate XML",
                "  Ctrl+Shift+T  Find in Tree",
                "  Ctrl+Shift+C  Copy Current Node with Subnodes",
                "  Ctrl+Shift+N  Open Node in New Window",
                "  Ctrl+E        Export Tree",
                "  Ctrl+Shift+S  Split XML...",
                "",
                "Code Folding:",
                "  Ctrl+Shift+[  Fold current element",
                "  Ctrl+Shift+]  Unfold current element",
                "  Ctrl+Shift+0  Unfold all",
                "",
                "View:",
                "  Ctrl+Shift+M  Open Multicolumn Tree (Experimental)",
                "",
                "Editor/Navigation:",
                "  Ctrl+T        Find in Tree (editor)",
                "  F4            Select XML node near cursor",
                "  Ctrl+F4       Select root element",
                "  Ctrl+Alt+F4   Cycle top-level elements",
                "  F5            Move selection to new tab with link",
                "  Shift+F5      Replace link with edited text from separate tab",
                "  Alt+←/→/↑/↓   Tree-backed navigation",
                "",
                "Tree:",
                "  Delete        Hide current node recursively (visual filter)",
            ]

            text = "\n".join(shortcuts)
            dlg = QDialog(self)
            dlg.setWindowTitle("Keyboard Shortcuts")
            dlg.setModal(True)
            dlg.resize(520, 500)
            v = QVBoxLayout()
            label = QLabel("These shortcuts are available across menus and the editor:")
            label.setWordWrap(True)
            v.addWidget(label)
            from PyQt6.QtWidgets import QTextEdit
            te = QTextEdit()
            te.setReadOnly(True)
            te.setPlainText(text)
            font = te.font()
            font.setFamily("Consolas")
            te.setFont(font)
            v.addWidget(te)
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            buttons.rejected.connect(dlg.reject)
            v.addWidget(buttons)
            dlg.setLayout(v)
            dlg.exec()
        except Exception as e:
            try:
                QMessageBox.information(self, "Shortcuts", f"Hotkey list:\n\n{text}")
            except Exception:
                print(f"Error showing hotkey help: {e}")
    
    def find_text(self, params: dict):
        """Find text in editor"""
        content = self.xml_editor.get_content()
        search_text = params['text']
        
        if not search_text:
            return
        
        # Store search parameters
        self.last_search_params = params
        self.last_search_results = []
        self.current_search_index = -1
        
        self.bottom_panel.clear_find_results()
        self.bottom_panel.setCurrentWidget(self.bottom_panel.find_tab)
        
        use_regex = params.get('use_regex', False)
        case_sensitive = params.get('case_sensitive', False)
        whole_word = params.get('whole_word', False)

        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            matches = []
            if use_regex:
                flags = 0
                if not case_sensitive:
                    flags |= re.IGNORECASE
                pattern_text = search_text
                if whole_word:
                    pattern_text = fr"\b{pattern_text}\b"
                try:
                    pattern = re.compile(pattern_text, flags)
                    for m in pattern.finditer(line):
                        matches.append((m.start(), m.end()))
                except re.error as e:
                    QMessageBox.critical(self, "Regex Error", f"Invalid regex: {e}")
                    return
            else:
                # Non-regex path
                if whole_word:
                    flags = 0 if case_sensitive else re.IGNORECASE
                    pattern = re.compile(fr"\b{re.escape(search_text)}\b", flags)
                    for m in pattern.finditer(line):
                        matches.append((m.start(), m.end()))
                else:
                    src = line if case_sensitive else line.lower()
                    needle = search_text if case_sensitive else search_text.lower()
                    start = 0
                    while True:
                        pos = src.find(needle, start)
                        if pos == -1:
                            break
                        matches.append((pos, pos + len(search_text)))
                        start = pos + 1

            if matches:
                for (s, e) in matches:
                    self.last_search_results.append((i, s, e))
                self.bottom_panel.add_find_result(f"Line {i}: {line.strip()}")
        
        # Show bottom panel to display results
        self._show_bottom_panel_auto("find")

        # Navigate to first result if any found
        if self.last_search_results:
            self.current_search_index = 0
            self._navigate_to_search_result(0)
    
    def find_next(self):
        """Find next occurrence (F3)"""
        if not self.last_search_results or self.current_search_index == -1:
            # No previous search, show find dialog
            self.show_find_dialog()
            return
        
        # Move to next result
        self.current_search_index = (self.current_search_index + 1) % len(self.last_search_results)
        self._navigate_to_search_result(self.current_search_index)
    
    def _navigate_to_search_result(self, result_index: int):
        """Navigate to a specific search result"""
        if not self.last_search_results or result_index < 0 or result_index >= len(self.last_search_results):
            return
        
        line_num, col_start, col_end = self.last_search_results[result_index]
        
        # Navigate to the line
        cursor = self.xml_editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.MoveAnchor, line_num - 1)
        
        # Move to the column position
        cursor.movePosition(cursor.MoveOperation.Right, cursor.MoveMode.MoveAnchor, col_start)
        
        # Select the found text
        cursor.movePosition(cursor.MoveOperation.Right, cursor.MoveMode.KeepAnchor, col_end - col_start)
        
        self.xml_editor.setTextCursor(cursor)
        self.xml_editor.setFocus()
        
        # Update status
        self.status_label.setText(f"Found match {result_index + 1} of {len(self.last_search_results)} at line {line_num}")
    
    def goto_line(self, line_number: int):
        """Go to specific line"""
        cursor = self.xml_editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.MoveAnchor, line_number - 1)
        self.xml_editor.setTextCursor(cursor)
        self.xml_editor.setFocus()

    def goto_line_and_column(self, line_number: int, column: int):
        """Go to specific line and column within the editor."""
        cursor = self.xml_editor.textCursor()
        cursor.movePosition(cursor.MoveOperation.Start)
        cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.MoveAnchor, max(0, line_number - 1))
        if column and column > 0:
            cursor.movePosition(cursor.MoveOperation.Right, cursor.MoveMode.MoveAnchor, column)
        self.xml_editor.setTextCursor(cursor)
        self.xml_editor.setFocus()
    
    def find_in_tree(self):
        """Find current line in tree view (Ctrl+T functionality)"""
        try:
            # Get current cursor position
            cursor = self.xml_editor.textCursor()
            current_line = cursor.blockNumber() + 1
            
            # Check if tree is populated
            if self.xml_tree.topLevelItemCount() == 0:
                self.status_label.setText("Tree is empty - please load an XML file first")
                return
            
            # Get the editor content
            content = self.xml_editor.get_content()
            if not content.strip():
                self.status_label.setText("Editor is empty")
                return
            
            # Find and select the tree item for current line using path-based approach
            element_path = self._get_element_path_at_line(content, current_line)
            if element_path and element_path != "/":
                tree_item = self._find_tree_item_by_path(element_path)
            else:
                tree_item = None
            if tree_item:
                # Select the item in the tree
                self.xml_tree.setCurrentItem(tree_item)
                # Expand parents if needed
                parent = tree_item.parent()
                while parent:
                    parent.setExpanded(True)
                    parent = parent.parent()
                # Scroll to make the item visible
                self.xml_tree.scrollToItem(tree_item)
                self.status_label.setText(f"Found element at line {current_line} in tree")
            else:
                self.status_label.setText(f"No element found at line {current_line}")
        except Exception as e:
            self.status_label.setText(f"Error finding in tree: {str(e)}")
            print(f"Find in tree error: {e}")  # Debug output
    
    def format_xml(self):
        """Format XML content"""
        content = self.xml_editor.get_content()
        if not content.strip():
            return
        
        try:
            formatted = self.xml_service.format_xml(content)
            self.xml_editor.set_content(formatted)
            self.status_label.setText("XML formatted")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to format XML: {str(e)}")
    
    def rebuild_tree_with_autoclose(self):
        """Rebuild tree from editor content with auto-close unclosed tags"""
        content = self.xml_editor.get_content()
        if not content.strip():
            self.status_label.setText("No content to rebuild")
            return
        
        try:
            # Auto-close any unclosed tags
            fixed_content = self.xml_service.auto_close_tags(content)
            
            # Check if content was modified
            if fixed_content != content:
                # Update editor with fixed content
                self.xml_editor.set_content(fixed_content)
                self.status_label.setText("Auto-closed unclosed tags and rebuilt tree")
            else:
                self.status_label.setText("Rebuilt tree (no unclosed tags found)")
            
            # Rebuild the tree
            self.xml_tree.populate_tree(fixed_content)
            
            # Reset caches and optionally rebuild index
            try:
                self.path_line_cache = {}
                lines_count = len(fixed_content.split('\n')) if fixed_content else 0
                if self.sync_index_enabled and lines_count < 50000:
                    self._build_path_line_index(fixed_content)
            except Exception:
                pass
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to rebuild tree: {str(e)}")
            self.status_label.setText(f"Error rebuilding tree: {str(e)}")
    
    def validate_xml(self):
        """Validate XML content"""
        content = self.xml_editor.get_content()
        if not content.strip():
            return
        
        try:
            result = self.xml_service.validate_xml(content)
            
            self.bottom_panel.clear_validation_errors()
            self.bottom_panel.setCurrentWidget(self.bottom_panel.validation_tab)
            
            if result.is_valid:
                self.bottom_panel.add_validation_error("XML is valid!")
                self.status_label.setText("XML validation passed")
            else:
                for error in result.errors:
                    self.bottom_panel.add_validation_error(error)
                self.status_label.setText(f"XML validation failed: {len(result.errors)} errors")
                # Show bottom panel when there are validation errors
                self._show_bottom_panel_auto("validation")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to validate XML: {str(e)}")
    
    def show_xml_stats(self):
        """Show XML statistics"""
        content = self.xml_editor.get_content()
        if not content.strip():
            return
        
        try:
            stats = self.xml_service.get_xml_statistics(content)
            
            stats_text = f"""XML Statistics:
Elements: {stats.element_count}
Attributes: {stats.attribute_count}
Text nodes: {stats.text_node_count}
Comments: {stats.comment_count}
Total size: {stats.total_size} bytes"""
            
            self.bottom_panel.append_output(stats_text)
            self.bottom_panel.setCurrentWidget(self.bottom_panel.output_tab)
            # Show bottom panel when stats are displayed
            self._show_bottom_panel_auto()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to get XML statistics: {str(e)}")
    
    def export_tree(self):
        """Export tree content to table format"""
        try:
            # Check if tree has content
            if self.xml_tree.topLevelItemCount() == 0:
                QMessageBox.information(self, "Info", "Tree is empty. Please load an XML file first.")
                return
            
            # Create and show export dialog
            dialog = TreeExportDialog(self.xml_tree, self)
            dialog.show()  # Use show() instead of exec() for non-modal
            self.status_label.setText("Tree export dialog opened")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export tree: {str(e)}")
            self.status_label.setText(f"Error exporting tree: {str(e)}")

    # --- 1C Exchange handlers ---
    def exchange_import(self):
        """Import two XML files from 1C and open the edited one (semi-auto)."""
        try:
            files, _ = QFileDialog.getOpenFileNames(
                self,
                "Выберите два XML файла из 1С",
                "",
                "XML Files (*.xml)"
            )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Диалог выбора файлов недоступен: {e}")
            return

        if not files or len(files) != 2:
            QMessageBox.information(self, "Импорт", "Нужно выбрать ровно два XML файла.")
            return

        a_path, b_path = files[0], files[1]

        # Try to identify edited file by matching current editor's tags
        edited_path = None
        try:
            current_content = self.xml_editor.get_content() if hasattr(self, 'xml_editor') else ""
            if current_content and current_content.strip():
                edited_path = identify_edited_file([a_path, b_path], current_content)
        except Exception:
            edited_path = None

        # If not identified, ask the user which file to open
        if not edited_path:
            base_a = os.path.basename(a_path)
            base_b = os.path.basename(b_path)
            resp = QMessageBox.question(
                self,
                "Импорт",
                f"Не удалось определить автоматически. Открыть файл '{base_a}'?\n(Нет — откроется '{base_b}')",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            edited_path = a_path if resp == QMessageBox.StandardButton.Yes else b_path

        # Parse exchange tags from edited and companion
        try:
            edited_source, edited_receiver = parse_exchange_tags_from_path(edited_path)
            companion_path = b_path if edited_path == a_path else a_path
        except Exception as e:
            QMessageBox.critical(self, "Ошибка XML", f"Не удалось разобрать теги: {e}")
            return

        # Persist pair metadata to facilitate export later
        try:
            # Compute exchange dir under current working directory
            root_work_dir = os.getcwd()
            pair_dir = compute_exchange_dir(root_work_dir, edited_source or "unknown_source", edited_receiver or "unknown_receiver")
            save_pair_metadata(pair_dir, edited_source or "", edited_receiver or "", edited_path, companion_path)
        except Exception:
            pass

        # Open the chosen edited file
        try:
            self.open_file(edited_path)
            QMessageBox.information(self, "Импорт", f"Открыт файл: {os.path.basename(edited_path)}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка открытия", f"Не удалось открыть файл: {e}")

    def exchange_export_zip(self):
        """Export current edited XML and its paired XML into a single ZIP for 1C."""
        current_path = getattr(self, 'current_file', None)
        if not current_path:
            QMessageBox.information(self, "Экспорт", "Сначала откройте XML для редактирования.")
            return

        # Parse current file tags to compute pair dir
        try:
            cur_source, cur_receiver = parse_exchange_tags_from_path(current_path)
        except Exception as e:
            QMessageBox.critical(self, "Ошибка XML", f"Не удалось разобрать теги текущего файла: {e}")
            return

        root_work_dir = os.getcwd()
        pair_dir = compute_exchange_dir(root_work_dir, cur_source or "unknown_source", cur_receiver or "unknown_receiver")

        companion_abs_path = None
        # Try to load metadata
        try:
            meta = load_pair_metadata(pair_dir)
            if meta:
                # Resolve companion by filename: prefer same dir as current
                comp_name = meta.get('companion_file_name')
                if comp_name:
                    cand_same_dir = os.path.join(os.path.dirname(current_path), comp_name)
                    if os.path.exists(cand_same_dir):
                        companion_abs_path = cand_same_dir
        except Exception:
            meta = None

        # If metadata not helpful, ask user to choose companion
        if not companion_abs_path:
            try:
                companion_abs_path, _ = QFileDialog.getOpenFileName(
                    self,
                    "Выберите второй XML (парный)",
                    os.path.dirname(current_path) if current_path else "",
                    "XML Files (*.xml)"
                )
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Диалог выбора файла недоступен: {e}")
                return
            if not companion_abs_path:
                return

            # Update metadata to remember companion name
            try:
                save_pair_metadata(pair_dir, cur_source or "", cur_receiver or "", current_path, companion_abs_path)
            except Exception:
                pass

        # Ask where to save ZIP
        try:
            default_zip = os.path.join(os.path.dirname(current_path), f"{os.path.splitext(os.path.basename(current_path))[0]}_1C.zip")
            zip_path, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить ZIP для 1С",
                default_zip,
                "ZIP Archive (*.zip)"
            )
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Диалог сохранения недоступен: {e}")
            return
        if not zip_path:
            return

        # Prepare arc names (use base names)
        edited_arc = os.path.basename(current_path)
        companion_arc = os.path.basename(companion_abs_path)

        ok = package_zip(zip_path, current_path, edited_arc, companion_abs_path, companion_arc)
        if ok:
            QMessageBox.information(self, "Экспорт", f"Создан ZIP: {os.path.basename(zip_path)}")
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось создать ZIP")
    
    def on_content_changed(self):
        """Handle content change"""
        # Suppress handling during programmatic file loads to avoid repeated rebuilds
        if getattr(self, '_loading_file', False):
            return
        content = self.xml_editor.get_content()
        self.xml_tree.populate_tree(content)
        # Reset caches and optionally rebuild index based on new content size
        try:
            lines_count = len(content.split('\n')) if content else 0
            self.sync_index_enabled = lines_count > 8000
            self.sync_cache_enabled = lines_count > 8000
            self.path_line_cache = {}
            self.path_line_index = {}
            if self.sync_index_enabled:
                self._build_path_line_index(content)
                print(f"DEBUG: Rebuilt index after content change, entries={len(self.path_line_index)}")
            else:
                print("DEBUG: Index/cache disabled after content change (small file)")
        except Exception as e:
            print(f"DEBUG: Error handling index/cache on content change: {e}")
        
        # Dump tree data to file for debugging (disabled by default)
        if self.tree_debug_enabled:
            try:
                with open('treedebug.txt', 'a', encoding='utf-8') as f:
                    f.write(f"\n{'='*60}\n")
                    f.write(f"XML CONTENT LOADED - Time: {QDateTime.currentDateTime().toString()}\n")
                    f.write(f"Content length: {len(content) if content else 0} characters\n")
                    f.write(f"Tree items: {self.xml_tree.topLevelItemCount()}\n")
                    
                    # Dump tree structure
                    def dump_item(item, level=0):
                        indent = "  " * level
                        if hasattr(item, 'xml_node') and item.xml_node:
                            node_name = getattr(item.xml_node, 'name', 'Unknown')
                            node_path = getattr(item.xml_node, 'path', 'No path')
                            f.write(f"{indent}- {node_name} (path: {node_path})\n")
                        else:
                            f.write(f"{indent}- Item (no xml_node)\n")
                        
                        # Dump children
                        for i in range(item.childCount()):
                            child = item.child(i)
                            dump_item(child, level + 1)
                    
                    # Dump all top level items
                    for i in range(self.xml_tree.topLevelItemCount()):
                        top_item = self.xml_tree.topLevelItem(i)
                        dump_item(top_item)
                    
                    f.write(f"{'='*60}\n")
                    
            except Exception as e:
                print(f"Error dumping tree debug info on load: {e}")
    
    def on_cursor_changed(self, line: int, column: int):
        """Handle cursor position change"""
        self.line_label.setText(f"Ln: {line}, Col: {column}")
        
        # Update breadcrumb based on current cursor position
        self._update_breadcrumb_from_cursor(line)
        
        # Sync tree selection to current cursor position (backward sync) when enabled
        if getattr(self, 'sync_enabled', False):
            self._sync_tree_to_cursor(line)
            # Also propagate selection to multicolumn tree windows, if any
            try:
                content = self.xml_editor.get_content()
                path = self._get_element_path_at_line(content, line)
                if path:
                    for win in getattr(self, 'multicolumn_windows', []):
                        try:
                            win.select_node_by_path(path)
                        except Exception as e:
                            print(f"Error propagating sync to multicolumn window: {e}")
            except Exception as e:
                print(f"Error computing path for multicolumn sync: {e}")
    
    def _update_breadcrumb_from_cursor(self, line_number: int):
        """Update breadcrumb based on cursor position"""
        content = self.xml_editor.get_content()
        if not content:
            return
        
        # Find the XML element at the current line
        lines = content.split('\n')
        if line_number <= 0 or line_number > len(lines):
            return
        
        # Search backwards from current line to find the containing element
        current_line = line_number - 1  # Convert to 0-based index
        element_stack = []
        
        for i in range(current_line, -1, -1):
            line = lines[i].strip()
            
            # Check for closing tags (pop from stack)
            if line.startswith('</'):
                tag_name = line[2:line.find('>')]
                element_stack.append(tag_name)
            
            # Check for opening tags
            elif line.startswith('<') and not line.startswith('<!--'):
                # Find the tag name
                tag_end = line.find('>')
                if tag_end == -1:
                    continue
                
                tag_content = line[1:tag_end]
                space_pos = tag_content.find(' ')
                if space_pos != -1:
                    tag_name = tag_content[:space_pos]
                else:
                    tag_name = tag_content
                
                # Skip self-closing tags
                if line.endswith('/>'):
                    continue
                
                # If this matches the top of our stack, pop it
                if element_stack and element_stack[-1] == tag_name:
                    element_stack.pop()
                else:
                    # This is our containing element
                    # Create a simple XML node for breadcrumb generation
                    class SimpleXmlNode:
                        def __init__(self, tag, parent=None):
                            self.tag = tag
                            self.name = tag
                            self.parent_node = parent
                            self.children = []
                            self.attributes = {}
                            self.path = ""
                    
                    # Build the path from root to this element
                    current_node = None
                    parent_node = None
                    
                    # Create nodes for each element in our simplified stack
                    for tag in reversed(element_stack):
                        parent_node = SimpleXmlNode(tag, parent_node)
                    
                    # Add the current element
                    current_node = SimpleXmlNode(tag_name, parent_node)
                    
                    # Generate breadcrumb
                    breadcrumb = self._generate_breadcrumb(current_node)
                    self.breadcrumb_label.setText(breadcrumb)
                    return
        
        # If no element found, show root
        self.breadcrumb_label.setText("/")
    
    def _sync_tree_to_cursor(self, line_number: int):
        """Synchronize tree selection to current cursor position using index-aware paths.
        This re-enables cursor-to-tree syncing and respects sibling indices in paths (e.g., Tag[2])."""
        try:
            content = self.xml_editor.get_content()
            if not content:
                self.status_label.setText("No content to sync")
                return
            
            # Resolve the element path at the given cursor line (index-aware, e.g., Tag[2])
            element_path = self._get_element_path_at_line(content, line_number)
            print(f"SYNC: Cursor at line {line_number}, resolved path: '{element_path}'")
            
            if element_path:
                # Prefer index-aware path lookup in the tree
                tree_item = self._find_tree_item_by_path_index_aware(element_path)
                if not tree_item:
                    # Fallback to legacy path lookup
                    tree_item = self._find_tree_item_by_path(element_path)
                
                if tree_item:
                    # Reveal hidden nodes for visibility, then select and expand
                    try:
                        self._reveal_item_and_ancestors(tree_item)
                    except Exception:
                        pass
                    # Temporarily block signals to avoid triggering editor jumps
                    prev_block = False
                    try:
                        prev_block = self.xml_tree.blockSignals(True)
                    except Exception:
                        pass
                    try:
                        self.xml_tree.setCurrentItem(tree_item)
                        try:
                            self.xml_tree.scrollToItem(tree_item)
                        except Exception:
                            pass
                    finally:
                        try:
                            self.xml_tree.blockSignals(prev_block)
                        except Exception:
                            pass
                    parent = tree_item.parent()
                    while parent:
                        parent.setExpanded(True)
                        parent = parent.parent()
                    self.status_label.setText(f"Synced to {element_path}")
                    return
                else:
                    print(f"SYNC: No matching tree item found for path '{element_path}', attempting line-based fallback")
            else:
                print("SYNC: No path resolved for current cursor line, attempting line-based fallback")
            
            # Fallback: try to find nearest element by line number when path matching fails
            if self._sync_tree_to_cursor_fallback(line_number):
                self.status_label.setText(f"Fallback synced near line {line_number}")
            else:
                self.status_label.setText(f"Could not sync to cursor at line {line_number}")
        except Exception as e:
            print(f"SYNC ERROR: {e}")
            self.status_label.setText("Sync error - see logs")
        return
    
    def _dump_tree_debug_info(self, line_number: int, element_path: str):
        """Dump tree debug information to file for manual analysis (disabled by default)"""
        if not self.tree_debug_enabled:
            return
            
        try:
            with open('treedebug.txt', 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"SYNC ATTEMPT - Line: {line_number}, Time: {QDateTime.currentDateTime().toString()}\n")
                f.write(f"Generated Path: '{element_path}'\n")
                
                # Dump tree structure
                f.write(f"Tree Structure:\n")
                f.write(f"Top level items: {self.xml_tree.topLevelItemCount()}\n")
                
                def dump_item(item, level=0):
                    indent = "  " * level
                    if hasattr(item, 'xml_node') and item.xml_node:
                        node_name = getattr(item.xml_node, 'name', 'Unknown')
                        node_path = getattr(item.xml_node, 'path', 'No path')
                        f.write(f"{indent}- {node_name} (path: {node_path})\n")
                    else:
                        f.write(f"{indent}- Item (no xml_node)\n")
                    
                    # Dump children
                    for i in range(item.childCount()):
                        child = item.child(i)
                        dump_item(child, level + 1)
                
                # Dump all top level items
                for i in range(self.xml_tree.topLevelItemCount()):
                    top_item = self.xml_tree.topLevelItem(i)
                    dump_item(top_item)
                
                f.write(f"{'='*60}\n")
                
        except Exception as e:
            print(f"Error dumping tree debug info: {e}")
    
    def _find_tree_item_by_path(self, element_path: str):
        """Find tree item by element path using XPath with fallback to partial matching"""
        try:
            # Check if tree widget is valid and has items
            if not self.xml_tree or self.xml_tree.topLevelItemCount() == 0:
                return None
            
            # First try exact path matching
            iterator = QTreeWidgetItemIterator(self.xml_tree)
            exact_matches = []
            partial_matches = []
            
            while iterator.value():
                item = iterator.value()
                if item and hasattr(item, 'xml_node') and item.xml_node:
                    try:
                        # Check if this item's path matches the target path
                        if (hasattr(item.xml_node, 'path') and 
                            item.xml_node.path == element_path):
                            exact_matches.append(item)
                        elif (hasattr(item.xml_node, 'path') and 
                              element_path.endswith(item.xml_node.path)):
                            # Partial match - path ends with this item's path
                            partial_matches.append(item)
                    except (AttributeError, TypeError):
                        # Skip items with missing or invalid attributes
                        pass
                iterator += 1
            
            # Return exact match if found, otherwise best partial match
            if exact_matches:
                return exact_matches[0]
            elif partial_matches:
                # Return the partial match with the longest path (most specific)
                best_match = max(partial_matches, key=lambda item: len(getattr(item.xml_node, 'path', '')))
                return best_match
            
            # If no good match found, try index-aware matching
            return self._find_tree_item_by_path_index_aware(element_path)
            
        except Exception as e:
            # Log error but don't crash
            print(f"Error in _find_tree_item_by_path: {e}")
            return None
    
    def _find_tree_item_by_path_index_aware(self, element_path: str):
        """Find tree item by path with index-aware matching"""
        try:
            if not element_path:
                return None
            
            # Parse the target path parts
            target_parts = element_path.split('/')[1:]  # Remove leading empty string
            
            # Iterate through all tree items to find best index-aware match
            iterator = QTreeWidgetItemIterator(self.xml_tree)
            best_match = None
            best_match_score = 0
            
            while iterator.value():
                item = iterator.value()
                if item and hasattr(item, 'xml_node') and item.xml_node:
                    try:
                        # Get the item's path and parse it
                        item_path = getattr(item.xml_node, 'path', '')
                        if item_path:
                            item_parts = item_path.split('/')[1:]
                            
                            # Calculate match score based on path parts
                            match_score = 0
                            min_parts = min(len(target_parts), len(item_parts))
                            
                            for i in range(min_parts):
                                target_part = target_parts[i]
                                item_part = item_parts[i]
                                
                                # Parse target part (handle index notation)
                                target_tag = target_part
                                target_index = 1
                                
                                if '[' in target_part and ']' in target_part:
                                    base_part = target_part.split('[')[0]
                                    attr_part = target_part[target_part.find('[')+1:target_part.find(']')]
                                    
                                    if attr_part.isdigit():
                                        target_index = int(attr_part)
                                        target_tag = base_part
                                    else:
                                        # Attribute-based notation, use full part for comparison
                                        target_tag = target_part
                                
                                # Parse item part (handle index notation)
                                item_tag = item_part
                                item_index = 1
                                
                                if '[' in item_part and ']' in item_part:
                                    base_part = item_part.split('[')[0]
                                    attr_part = item_part[item_part.find('[')+1:item_part.find(']')]
                                    
                                    if attr_part.isdigit():
                                        item_index = int(attr_part)
                                        item_tag = base_part
                                    else:
                                        # Attribute-based notation, use full part for comparison
                                        item_tag = item_part
                                
                                # Check if tag names match
                                if target_tag == item_tag:
                                    # Check if indices match (for index-aware paths)
                                    if '[' in target_part and target_part.split('[')[1].split(']')[0].isdigit():
                                        if target_index == item_index:
                                            match_score += 2  # Bonus for exact index match
                                    else:
                                        match_score += 1  # Basic match for tag name
                                else:
                                    break  # No match at this level
                            
                            # Update best match if this is better
                            if match_score > best_match_score:
                                best_match_score = match_score
                                best_match = item
                                
                    except (AttributeError, TypeError, ValueError, IndexError):
                        # Skip items with missing or invalid attributes
                        pass
                iterator += 1
            
            return best_match
            
        except Exception as e:
            print(f"Error in _find_tree_item_by_path_index_aware: {e}")
        return None
    
    def _get_element_path_at_line(self, xml_content: str, line_number: int) -> str:
        """Get the proper XPath of the element at the given line number using XML parsing"""
        print(f"DEBUG: _get_element_path_at_line called with line_number={line_number}")
        try:
            import xml.etree.ElementTree as ET
            
            # Parse the XML content
            root = ET.fromstring(xml_content)
            
            # Find the element at the given line by parsing line by line
            lines = xml_content.split('\n')
            print(f"DEBUG: Total lines in content: {len(lines)}")
            
            if line_number <= 0 or line_number > len(lines):
                print(f"DEBUG: Line number {line_number} out of range")
                return ""
            
            target_line = lines[line_number - 1].strip()
            print(f"DEBUG: Processing line {line_number}: '{target_line}'")
            
            # Extract tag name from the target line
            if not target_line.startswith('<') or target_line.startswith('<!--'):
                print(f"DEBUG: Line is not an opening tag")
                return ""
            
            # Find tag name
            tag_end = target_line.find('>')
            if tag_end == -1:
                return ""
            
            tag_content = target_line[1:tag_end]
            # Handle attributes - find first space or other delimiter
            space_pos = tag_content.find(' ')
            slash_pos = tag_content.find('/')
            
            # Find the earliest delimiter
            delimiters = [pos for pos in [space_pos, slash_pos] if pos != -1]
            if delimiters:
                tag_name = tag_content[:min(delimiters)].strip()
            else:
                tag_name = tag_content.strip()
            
            print(f"DEBUG: Looking for tag: {tag_name}")
            
            # Build element path map with parent relationships
            element_paths = {}
            self._build_element_paths(root, [], element_paths, None)
            
            # Find the element that corresponds to this line
            target_element_path = self._find_element_path_at_line(root, tag_name, line_number, xml_content, element_paths)
            
            if target_element_path:
                print(f"DEBUG: Generated path: {target_element_path}")
                return target_element_path
            else:
                print(f"DEBUG: Could not find element at line {line_number}")
                return ""
                
        except Exception as e:
            print(f"Error getting element path at line {line_number}: {e}")
            import traceback
            traceback.print_exc()
            return ""
    
    def _build_element_paths(self, element, current_path, element_paths, parent=None):
        """Build a map of elements to their XPath with proper indexing"""
        # Count siblings with the same tag name
        if parent is not None:
            siblings_before = 0
            for sibling in parent:
                if sibling == element:
                    break
                if sibling.tag == element.tag:
                    siblings_before += 1
            index = siblings_before + 1
        else:
            # Root element
            index = 1
        
        # Build current element path
        element_path_part = f"{element.tag}[{index}]"
        full_path = current_path + [element_path_part]
        
        # Store the path for this element
        element_paths[element] = "/" + "/".join(full_path)
        
        # Recursively process children
        for child in element:
            self._build_element_paths(child, full_path, element_paths, element)
    
    def _find_element_path_at_line(self, root, tag_name, target_line, xml_content, element_paths):
        """Find the XPath of the element at the specified line number"""
        lines = xml_content.split('\n')
        
        # Find all elements with the target tag name
        matching_elements = []
        
        def find_matching_elements(element):
            if element.tag == tag_name:
                matching_elements.append(element)
            for child in element:
                find_matching_elements(child)
        
        find_matching_elements(root)
        
        # For each matching element, try to find which one corresponds to our line
        for element in matching_elements:
            element_line = self._find_element_line_in_content(element, lines, xml_content)
            if element_line == target_line:
                return element_paths.get(element, "")
        
        return ""
    
    def _find_element_line_in_content(self, element, lines, xml_content):
        """Find the line number where an element appears in the original content"""
        tag_name = element.tag
        
        # Get element attributes and text content to help identify the exact element
        element_attrs = element.attrib
        element_text = element.text.strip() if element.text else ""
        
        # Search through lines to find this specific element
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if line_stripped.startswith(f'<{tag_name}') and not line_stripped.startswith(f'</{tag_name}'):
                # Check if this line matches our element by comparing attributes and text
                if self._line_matches_element(line_stripped, tag_name, element_attrs, element_text, i, lines):
                    return i + 1
        
        return 0
    
    def _line_matches_element(self, line, tag_name, element_attrs, element_text, line_index, lines):
        """Check if a line matches an element based on tag name, attributes, and text content.
        Enhanced to handle XML entity-encoded text (e.g., &lt;, &gt;, &amp;, &quot;, &apos;)."""
        # Check attributes first
        if element_attrs:
            for attr_name, attr_value in element_attrs.items():
                attr_pattern = f'{attr_name}="{attr_value}"'
                if attr_pattern not in line:
                    return False
        
        # If element has text content, check if it matches (consider entity encoding)
        if element_text:
            # Check if this is a self-closing tag with text content
            if line.endswith('/>'):
                return False
            
            def escape_xml_text(text: str) -> str:
                # Minimal XML escaping to compare with encoded source lines
                return (
                    text.replace('&', '&amp;')
                        .replace('<', '&lt;')
                        .replace('>', '&gt;')
                        .replace('"', '&quot;')
                        .replace("'", '&apos;')
                )
            
            escaped_text = escape_xml_text(element_text)
            
            # Check if the text content appears on the same line (raw or escaped)
            if f'>{element_text}<' in line or f'>{escaped_text}<' in line:
                return True
            
            # Check if text content is on the next line (raw or escaped)
            if line_index + 1 < len(lines):
                next_line = lines[line_index + 1].strip()
                if next_line == element_text or next_line == escaped_text or f'>{element_text}<' in next_line or f'>{escaped_text}<' in next_line:
                    return True
            
            # If we have text content but it doesn't match, this isn't our element
            return False
        
        # If no specific attributes or text to match, this is a valid match
        return True
    
    def _sync_tree_to_cursor_fallback(self, line_number: int):
        """Fallback sync method using line numbers when path-based sync fails"""
        try:
            # Use the old line-based approach as fallback
            tree_item = self._find_tree_item_by_line_fallback(line_number)
            if tree_item:
                self.xml_tree.setCurrentItem(tree_item)
                parent = tree_item.parent()
                while parent:
                    parent.setExpanded(True)
                    parent = parent.parent()
                return True
        except Exception as e:
            print(f"Fallback sync failed: {e}")
        return False
    
    def _find_tree_item_by_line_fallback(self, line_number: int):
        """Fallback method to find tree item by line number"""
        try:
            if not self.xml_tree or self.xml_tree.topLevelItemCount() == 0:
                return None
            
            # Iterate through all tree items to find closest match
            iterator = QTreeWidgetItemIterator(self.xml_tree)
            best_match = None
            best_distance = float('inf')
            
            while iterator.value():
                item = iterator.value()
                if item and hasattr(item, 'xml_node') and item.xml_node:
                    try:
                        if hasattr(item.xml_node, 'line_number') and item.xml_node.line_number > 0:
                            distance = abs(item.xml_node.line_number - line_number)
                            if distance < best_distance:
                                best_distance = distance
                                best_match = item
                    except (AttributeError, TypeError):
                        pass
                iterator += 1
            
            return best_match
        except Exception as e:
            print(f"Error in fallback line search: {e}")
        return None
    
    def _is_line_in_element(self, line_number: int, xml_node):
        """Check if a line number falls within an element's range (deprecated - use path-based sync instead)"""
        # This method is deprecated in favor of path-based sync
        return False
    
    def on_tree_node_selected(self, xml_node):
        """Handle tree node selection - jump to element in editor using XPath"""
        # Log tree selection for debugging
        print(f"TREE SELECTION: Node selected - name: {xml_node.name if xml_node else 'None'}")
        if xml_node and hasattr(xml_node, 'path'):
            print(f"TREE SELECTION: Node path: {xml_node.path}")
        if xml_node and hasattr(xml_node, 'line_number'):
            print(f"TREE SELECTION: Stored line number: {xml_node.line_number}")
        
        line_number = 0
        
        # First try to use stored line number
        if xml_node and hasattr(xml_node, 'line_number') and xml_node.line_number > 0:
            line_number = xml_node.line_number
            print(f"TREE SELECTION: Using stored line number: {line_number}")
        else:
            # Try to find the element using multiple methods
            content = self.xml_editor.get_content()
            if content and xml_node:
                # Try path-based search first
                if hasattr(xml_node, 'path') and xml_node.path:
                    print(f"TREE SELECTION: Attempting path-based search for: {xml_node.path}")
                    line_number = self._find_element_line_by_path(content, xml_node.path)
                    print(f"TREE SELECTION: Path-based search result: line {line_number}")
                
                # If path-based search fails, try name and attributes
                if line_number <= 0:
                    print(f"TREE SELECTION: Fallback to name/attributes search for: {xml_node.name}")
                    line_number = self._find_element_line(content, xml_node.name, xml_node.attributes)
                    print(f"TREE SELECTION: Name/attributes search result: line {line_number}")
        
        # Jump to the found line (and column if multiple siblings are on the same line)
        if line_number > 0:
            # Determine tag and index from path (for column targeting on same line)
            col_pos = None
            try:
                content = self.xml_editor.get_content()
                line_text = content.split('\n')[line_number - 1]
                last_part = None
                if hasattr(xml_node, 'path') and xml_node.path:
                    parts = xml_node.path.split('/')
                    if parts:
                        last_part = parts[-1]
                if last_part:
                    tag_name = last_part.split('[')[0]
                    idx = 1
                    if '[' in last_part and ']' in last_part:
                        inside = last_part[last_part.find('[')+1:last_part.find(']')]
                        if inside.isdigit():
                            idx = int(inside)
                    # Find nth occurrence of the opening tag on this line
                    matches = list(re.finditer(r'<\s*' + re.escape(tag_name) + r'\b', line_text))
                    if matches:
                        if idx <= len(matches):
                            col_pos = matches[idx - 1].start()
                        else:
                            col_pos = matches[0].start()
            except Exception:
                col_pos = None

            if col_pos is not None and col_pos >= 0:
                # Use column-aware navigation when available
                try:
                    self.goto_line_and_column(line_number, col_pos)
                    self.status_label.setText(f"Jumped to {xml_node.name} at line {line_number}, col {col_pos}")
                except Exception:
                    self.goto_line(line_number)
                    self.status_label.setText(f"Jumped to {xml_node.name} at line {line_number}")
            else:
                self.goto_line(line_number)
                self.status_label.setText(f"Jumped to {xml_node.name} at line {line_number}")
            
            # Highlight the element block with orange border
            self._highlight_element_block(xml_node, line_number)
            
            # Debug output
            if hasattr(xml_node, 'path'):
                print(f"Tree-to-text sync: Found element at line {line_number}, path: {xml_node.path}")
            else:
                print(f"Tree-to-text sync: Found element at line {line_number}, name: {xml_node.name}")
        else:
            print(f"Tree-to-text sync: Could not find element line for {xml_node.name}")
            self.status_label.setText(f"Could not find element {xml_node.name} in text")
        
        # Update breadcrumb
        if xml_node:
            breadcrumb = self._generate_breadcrumb(xml_node)
            self.breadcrumb_label.setText(breadcrumb)

    def _reveal_item_and_ancestors(self, item):
        """Ensure the item and its ancestors are visible and expanded."""
        try:
            current = item
            while current:
                current.setHidden(False)
                parent = current.parent()
                if parent:
                    parent.setExpanded(True)
                current = parent
            # Reflect in viewport
            self.xml_tree.viewport().update()
        except Exception as e:
            print(f"Reveal error: {e}")

    def select_node_by_path(self, element_path: str):
        """Select a node by its path, revealing hidden leaves on demand."""
        try:
            item = self._find_tree_item_by_path(element_path)
            if item:
                self._reveal_item_and_ancestors(item)
                self.xml_tree.setCurrentItem(item)
                self.xml_tree.scrollToItem(item)
                # Jump editor to this element
                if hasattr(item, 'xml_node') and item.xml_node:
                    self.on_tree_node_selected(item.xml_node)
                if hasattr(self, 'status_label') and self.status_label:
                    self.status_label.setText(f"Selected {element_path}")
        except Exception as e:
            print(f"select_node_by_path error: {e}")

    def _ensure_current_tree_item(self):
        """Ensure there is a current tree item; if none, sync from cursor or pick first."""
        item = self.xml_tree.currentItem()
        if item:
            return item
        # Try to sync from cursor
        try:
            cursor = self.xml_editor.textCursor()
            line = cursor.blockNumber() + 1
            content = self.xml_editor.get_content()
            path = self._get_element_path_at_line(content, line)
            if path:
                item = self._find_tree_item_by_path(path)
                if item:
                    self._reveal_item_and_ancestors(item)
                    self.xml_tree.setCurrentItem(item)
                    return item
        except Exception:
            pass
        # Fallback to first top-level item
        if self.xml_tree.topLevelItemCount() > 0:
            first = self.xml_tree.topLevelItem(0)
            self._reveal_item_and_ancestors(first)
            self.xml_tree.setCurrentItem(first)
            return first
        return None

    def navigate_tree_left(self):
        """Select parent node."""
        current = self._ensure_current_tree_item()
        if not current:
            return
        parent = current.parent()
        if parent:
            self._reveal_item_and_ancestors(parent)
            self.xml_tree.setCurrentItem(parent)
            if hasattr(parent, 'xml_node'):
                self.on_tree_node_selected(parent.xml_node)

    def navigate_tree_right(self):
        """Select first child node."""
        current = self._ensure_current_tree_item()
        if not current:
            return
        if current.childCount() > 0:
            # pick first visible child
            child = None
            for i in range(current.childCount()):
                c = current.child(i)
                if not c.isHidden():
                    child = c
                    break
            if not child:
                return
            self._reveal_item_and_ancestors(child)
            self.xml_tree.setCurrentItem(child)
            if hasattr(child, 'xml_node'):
                self.on_tree_node_selected(child.xml_node)

    def navigate_tree_up(self):
        """Select previous sibling (or parent if first)."""
        current = self._ensure_current_tree_item()
        if not current:
            return
        parent = current.parent()
        if not parent:
            # Top-level: move to previous top-level item
            idx = -1
            for i in range(self.xml_tree.topLevelItemCount()):
                if self.xml_tree.topLevelItem(i) is current:
                    idx = i
                    break
            # find previous visible top-level
            while idx > 0:
                prev_item = self.xml_tree.topLevelItem(idx - 1)
                if not prev_item.isHidden():
                    break
                idx -= 1
            if idx > 0:
                self._reveal_item_and_ancestors(prev_item)
                self.xml_tree.setCurrentItem(prev_item)
                if hasattr(prev_item, 'xml_node'):
                    self.on_tree_node_selected(prev_item.xml_node)
            return
        # Find index in parent
        index = None
        for i in range(parent.childCount()):
            if parent.child(i) is current:
                index = i
                break
        if index is not None and index > 0:
            # find previous visible sibling
            prev_sibling = None
            j = index - 1
            while j >= 0:
                candidate = parent.child(j)
                if not candidate.isHidden():
                    prev_sibling = candidate
                    break
                j -= 1
            if not prev_sibling:
                # if none visible, fall back to parent
                self._reveal_item_and_ancestors(parent)
                self.xml_tree.setCurrentItem(parent)
                if hasattr(parent, 'xml_node'):
                    self.on_tree_node_selected(parent.xml_node)
                return
            self._reveal_item_and_ancestors(prev_sibling)
            self.xml_tree.setCurrentItem(prev_sibling)
            if hasattr(prev_sibling, 'xml_node'):
                self.on_tree_node_selected(prev_sibling.xml_node)
        elif parent:
            # If first child, select parent
            self._reveal_item_and_ancestors(parent)
            self.xml_tree.setCurrentItem(parent)
            if hasattr(parent, 'xml_node'):
                self.on_tree_node_selected(parent.xml_node)

    def navigate_tree_down(self):
        """Select next sibling (or parent if last)."""
        current = self._ensure_current_tree_item()
        if not current:
            return
        parent = current.parent()
        if not parent:
            # Top-level: move to next top-level item
            idx = -1
            count = self.xml_tree.topLevelItemCount()
            for i in range(count):
                if self.xml_tree.topLevelItem(i) is current:
                    idx = i
                    break
            # find next visible top-level
            if idx != -1:
                j = idx + 1
                next_item = None
                while j < count:
                    candidate = self.xml_tree.topLevelItem(j)
                    if not candidate.isHidden():
                        next_item = candidate
                        break
                    j += 1
                if next_item:
                    self._reveal_item_and_ancestors(next_item)
                    self.xml_tree.setCurrentItem(next_item)
                    if hasattr(next_item, 'xml_node'):
                        self.on_tree_node_selected(next_item.xml_node)
            return
        # Find index in parent
        index = None
        for i in range(parent.childCount()):
            if parent.child(i) is current:
                index = i
                break
        if index is not None and index < parent.childCount() - 1:
            # find next visible sibling
            next_sibling = None
            j = index + 1
            while j < parent.childCount():
                candidate = parent.child(j)
                if not candidate.isHidden():
                    next_sibling = candidate
                    break
                j += 1
            if not next_sibling:
                # if none visible, fall back to parent
                self._reveal_item_and_ancestors(parent)
                self.xml_tree.setCurrentItem(parent)
                if hasattr(parent, 'xml_node'):
                    self.on_tree_node_selected(parent.xml_node)
                return
            self._reveal_item_and_ancestors(next_sibling)
            self.xml_tree.setCurrentItem(next_sibling)
            if hasattr(next_sibling, 'xml_node'):
                self.on_tree_node_selected(next_sibling.xml_node)
        elif parent:
            # If last child, select parent
            self._reveal_item_and_ancestors(parent)
            self.xml_tree.setCurrentItem(parent)
            if hasattr(parent, 'xml_node'):
                self.on_tree_node_selected(parent.xml_node)

    def select_root_element(self):
        """Select the root/top-level element and jump to it."""
        if self.xml_tree.topLevelItemCount() > 0:
            root_item = self.xml_tree.topLevelItem(0)
            self._reveal_item_and_ancestors(root_item)
            self.xml_tree.setCurrentItem(root_item)
            if hasattr(root_item, 'xml_node'):
                self.on_tree_node_selected(root_item.xml_node)

    def cycle_top_level_elements(self):
        """Cycle selection across top-level elements."""
        count = self.xml_tree.topLevelItemCount()
        if count == 0:
            return
        idx = getattr(self, 'top_level_cycle_index', -1)
        idx = (idx + 1) % count
        self.top_level_cycle_index = idx
        item = self.xml_tree.topLevelItem(idx)
        self._reveal_item_and_ancestors(item)
        self.xml_tree.setCurrentItem(item)
        if hasattr(item, 'xml_node'):
            self.on_tree_node_selected(item.xml_node)
    
    def _generate_breadcrumb(self, xml_node):
        """Generate breadcrumb path with special handling for Группа and Правило nodes"""
        if not xml_node:
            return "/"
        
        # Build path from root to current node
        path_parts = []
        current = xml_node
        
        # Get current content to find child elements
        content = self.xml_editor.get_content()
        
        while current:
            tag_name = current.tag
            
            # Special handling for Группа and Правило nodes
            if tag_name in ["Группа", "Правило"]:
                # Look for Наименование child element
                наименование = self._find_child_value(content, current.path, "Наименование")
                if наименование:
                    path_parts.insert(0, f'{tag_name}[Наименование="{наименование}"]')
                else:
                    # Fallback to index-based notation
                    path_parts.insert(0, tag_name)
            else:
                path_parts.insert(0, tag_name)
            
            # Move to parent using stored parent reference
            current = current.parent_node if hasattr(current, 'parent_node') else None
        
        return "/" + "/".join(path_parts)
    
    def _find_child_value(self, content, parent_path, child_tag):
        """Find the value of a child element by tag name, supporting index-aware parent paths (e.g., Tag[2])."""
        if not content or not parent_path or not child_tag:
            return None
        
        try:
            # Use XML parsing to find the child element value
            import xml.etree.ElementTree as ET
            root = ET.fromstring(content)
            
            # Parse the parent path into parts, handling indices like Tag[2]
            parts = [p for p in parent_path.split('/') if p]
            current = root
            
            # Walk down the path using indices
            for part in parts[1:]:  # skip root part at index 0
                # Extract tag and optional index
                if '[' in part and ']' in part:
                    tag_name = part.split('[')[0]
                    index_str = part[part.find('[')+1:part.find(']')]
                    index = int(index_str) if index_str.isdigit() else 1
                else:
                    tag_name = part
                    index = 1
                
                # Find the nth child with this tag (1-based)
                count = 0
                next_current = None
                for child in list(current):
                    if child.tag == tag_name:
                        count += 1
                        if count == index:
                            next_current = child
                            break
                if next_current is None:
                    return None
                current = next_current
            
            # Find the child element with the specified tag and return its text
            for child in list(current):
                if child.tag == child_tag and child.text:
                    return child.text.strip()
            return None
            
        except Exception:
            # Fallback to simple text parsing
            lines = content.split('\n')
            # Use the last part of parent tag without index for text search
            parent_last = [p for p in parent_path.split('/') if p][-1] if parent_path else ''
            parent_tag = parent_last.split('[')[0]
            in_parent = False
            
            for line in lines:
                line_stripped = line.strip()
                
                # Check if we're entering the parent element
                if not in_parent and f'<{parent_tag}' in line_stripped and not line_stripped.startswith(f'</{parent_tag}>'):
                    in_parent = True
                    continue
                
                if in_parent:
                    # Check for the child element
                    if f'<{child_tag}>' in line_stripped:
                        # Extract value between opening and closing tags
                        start_idx = line_stripped.find(f'<{child_tag}>') + len(f'<{child_tag}>')
                        end_idx = line_stripped.find(f'</{child_tag}>')
                        if start_idx > len(f'<{child_tag}>') and end_idx > start_idx:
                            return line_stripped[start_idx:end_idx]
                    
                    # Check if we're leaving the parent element
                    if line_stripped.startswith(f'</{parent_tag}>'):
                        break
            
            return None
    
    def _find_parent_node(self, xml_node):
        """Find parent node from tree structure"""
        # This is a simplified implementation
        # In a real implementation, you'd need to traverse the tree widget to find the parent
        return None
    
    def _find_element_line(self, content: str, element_name: str, attributes: dict = None) -> int:
        """Find the line number of an XML element in the content"""
        lines = content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Look for opening tag
            tag_pattern = f'<{element_name}'
            if tag_pattern in line:
                # If we have attributes, check for them too
                if attributes:
                    attr_found = True
                    for attr_name, attr_value in attributes.items():
                        if f'{attr_name}="{attr_value}"' not in line:
                            attr_found = False
                            break
                    if attr_found:
                        return i
                else:
                    return i
        
        return 0
    
    def _find_element_line_by_path(self, content: str, element_path: str) -> int:
        """Find the line number of an XML element by its XPath-like path with index support.
        Strategy:
        1) Cache lookup
        2) lxml index lookup (if built)
        3) Parent-anchored subtree search
        4) Chunked full-file scan (no 10k cap)
        """
        print(f"DEBUG: _find_element_line_by_path called with path: {element_path}")

        if not element_path or element_path == "/":
            print(f"DEBUG: Returning line 1 for root element")
            return 1  # Root element

        # Cache fast path
        if self.sync_cache_enabled and element_path in self.path_line_cache:
            line_cached = self.path_line_cache[element_path]
            print(f"DEBUG: Cache hit for {element_path} -> line {line_cached}")
            return line_cached

        lines = content.split('\n')
        path_parts = element_path.split('/')[1:]  # Remove leading empty string

        if not path_parts:
            print(f"DEBUG: No path parts, returning 0")
            return 0

        print(f"DEBUG: Processing {len(lines)} lines for path parts: {path_parts}")

        # lxml index lookup
        if self.sync_index_enabled and self._sync_index_available:
            if element_path in self.path_line_index:
                line = self.path_line_index[element_path]
                print(f"DEBUG: Index hit for {element_path} -> line {line}")
                if self.sync_cache_enabled:
                    self.path_line_cache[element_path] = line
                return line

        # Try parent-anchored subtree search
        parent_line = 0
        parent_path = None
        if len(path_parts) > 1:
            parent_path = '/' + '/'.join(path_parts[:-1])
            if self.sync_index_enabled and self._sync_index_available:
                parent_line = self.path_line_index.get(parent_path, 0)
            if parent_line == 0 and self.sync_cache_enabled:
                parent_line = self.path_line_cache.get(parent_path, 0)

        def _parse_part(part: str):
            expected_tag_name = part
            expected_index = 1
            expected_attr_value = None
            if '[' in part and ']' in part:
                base = part.split('[')[0]
                inside = part[part.find('[')+1:part.find(']')]
                if 'Наименование=' in inside:
                    try:
                        expected_attr_value = inside.split('Наименование="')[1].split('"')[0]
                    except Exception:
                        expected_attr_value = None
                    expected_tag_name = base
                elif inside.isdigit():
                    expected_index = int(inside)
                    expected_tag_name = base
            return expected_tag_name, expected_index, expected_attr_value

        if parent_line > 0:
            print(f"DEBUG: Anchored search from parent path {parent_path} at line {parent_line}")
            parent_tag, parent_idx, _ = _parse_part(path_parts[-2])
            depth = 0
            start_index = max(parent_line - 1, 0)
            end_index = len(lines)
            for j in range(start_index, len(lines)):
                s = lines[j].strip()
                if s.startswith(f"<{parent_tag}") and not s.startswith("<!") and not s.endswith("/>"):
                    depth += 1
                elif s.startswith(f"</{parent_tag}"):
                    depth -= 1
                    if depth <= 0 and j > start_index:
                        end_index = j + 1
                        break
            relative_parts = path_parts[-1:]
            element_stack = []
            tag_counters = {}
            for i in range(start_index + 1, end_index + 1):
                line_stripped = lines[i-1].strip()
                if not line_stripped:
                    continue
                # Build ordered list of tag events (open/close) on this line
                events = []
                try:
                    for m in re.finditer(r'</\s*([^\s>]+)\s*>', line_stripped):
                        events.append((m.start(), 'close', m.group(1), False))
                    for m in re.finditer(r'<\s*([^\s>/!?]+)([^>]*)>', line_stripped):
                        full = m.group(0)
                        tn = m.group(1)
                        self_closing = full.strip().endswith('/>')
                        events.append((m.start(), 'open', tn, self_closing))
                    events.sort(key=lambda x: x[0])
                except Exception:
                    events = []
                for _, etype, tn, self_closing in events:
                    if etype == 'close':
                        if element_stack and element_stack[-1][0] == tn:
                            element_stack.pop()
                            level_key = f"level_{len(element_stack)}"
                            if level_key in tag_counters:
                                del tag_counters[level_key]
                        continue
                    # opening tag
                    level_key = f"level_{len(element_stack)}"
                    if level_key not in tag_counters:
                        tag_counters[level_key] = {}
                    tag_counters[level_key][tn] = tag_counters[level_key].get(tn, 0) + 1
                    tag_index = tag_counters[level_key][tn]
                    current_depth = len(element_stack) + 1
                    if current_depth <= len(relative_parts):
                        exp_tag, exp_idx, exp_attr = _parse_part(relative_parts[current_depth - 1])
                        if tn == exp_tag:
                            if exp_attr and f'Наименование="{exp_attr}"' in line_stripped:
                                if current_depth == len(relative_parts):
                                    print(f"DEBUG: Anchored match (attr) at line {i}")
                                    if self.sync_cache_enabled:
                                        self.path_line_cache[element_path] = i
                                    return i
                            elif exp_idx == tag_index:
                                if current_depth == len(relative_parts):
                                    print(f"DEBUG: Anchored match at line {i}")
                                    if self.sync_cache_enabled:
                                        self.path_line_cache[element_path] = i
                                    return i
                            elif exp_idx == 1 and not exp_attr and tag_index == 1:
                                if current_depth == len(relative_parts):
                                    print(f"DEBUG: Anchored simple match at line {i}")
                                    if self.sync_cache_enabled:
                                        self.path_line_cache[element_path] = i
                                    return i
                    # push if not self-closing
                    if not self_closing:
                        element_stack.append((tn, tag_index))

        # Chunked full-file scan with preserved state (no 10k limit)
        element_stack = []
        tag_counters = {}
        batch_size = 10000
        for start in range(0, len(lines), batch_size):
            end = min(start + batch_size, len(lines))
            for i, line in enumerate(lines[start:end], start + 1):
                line_stripped = line.strip()
                if not line_stripped:
                    continue
                # Build ordered list of tag events (open/close) on this line
                events = []
                try:
                    for m in re.finditer(r'</\s*([^\s>]+)\s*>', line_stripped):
                        events.append((m.start(), 'close', m.group(1), False))
                    for m in re.finditer(r'<\s*([^\s>/!?]+)([^>]*)>', line_stripped):
                        full = m.group(0)
                        tn = m.group(1)
                        self_closing = full.strip().endswith('/>')
                        events.append((m.start(), 'open', tn, self_closing))
                    events.sort(key=lambda x: x[0])
                except Exception:
                    events = []
                for _, etype, tn, self_closing in events:
                    if etype == 'close':
                        if element_stack and element_stack[-1][0] == tn:
                            element_stack.pop()
                            level_key = f"level_{len(element_stack)}"
                            if level_key in tag_counters:
                                del tag_counters[level_key]
                        continue
                    # opening tag
                    level_key = f"level_{len(element_stack)}"
                    if level_key not in tag_counters:
                        tag_counters[level_key] = {}
                    tag_counters[level_key][tn] = tag_counters[level_key].get(tn, 0) + 1
                    tag_index = tag_counters[level_key][tn]
                    current_depth = len(element_stack) + 1
                    if current_depth <= len(path_parts):
                        exp_tag, exp_idx, exp_attr = _parse_part(path_parts[current_depth - 1])
                        if tn == exp_tag:
                            if exp_attr and f'Наименование="{exp_attr}"' in line_stripped:
                                if current_depth == len(path_parts):
                                    print(f"DEBUG: Found target element by attribute at line {i}")
                                    if self.sync_cache_enabled:
                                        self.path_line_cache[element_path] = i
                                    return i
                            elif exp_idx == tag_index:
                                if current_depth == len(path_parts):
                                    print(f"DEBUG: Found target element at line {i}")
                                    if self.sync_cache_enabled:
                                        self.path_line_cache[element_path] = i
                                    return i
                            elif exp_idx == 1 and not exp_attr and tag_index == 1:
                                if current_depth == len(path_parts):
                                    print(f"DEBUG: Found target element by simple match at line {i}")
                                    if self.sync_cache_enabled:
                                        self.path_line_cache[element_path] = i
                                    return i
                    # push if not self-closing
                    if not self_closing:
                        element_stack.append((tn, tag_index))

        print(f"DEBUG: Element not found, returning 0")
        return 0
    
    def _find_element_end_line(self, content: str, tag_name: str, start_line: int) -> int:
        """Find the closing tag line for an XML element starting at start_line.
        Returns the line number of the closing tag, or start_line if it's a self-closing tag.
        """
        lines = content.split('\n')
        if start_line < 1 or start_line > len(lines):
            return start_line
        
        start_line_text = lines[start_line - 1]
        
        # Check if it's a self-closing tag
        if re.search(r'<\s*' + re.escape(tag_name) + r'[^>]*/>', start_line_text):
            return start_line
        
        # Check if opening and closing tags are on the same line
        if re.search(r'<\s*' + re.escape(tag_name) + r'\b[^>]*>.*?</' + re.escape(tag_name) + r'>', start_line_text):
            return start_line
        
        # Track nesting depth
        depth = 0
        
        # Count opening tags on the start line
        opening_tags = len(re.findall(r'<\s*' + re.escape(tag_name) + r'\b[^/>]*(?<!/)>', start_line_text))
        closing_tags = len(re.findall(r'</' + re.escape(tag_name) + r'>', start_line_text))
        depth = opening_tags - closing_tags
        
        # Search for closing tag in subsequent lines
        for i in range(start_line, len(lines)):
            line = lines[i]
            
            # Count opening and closing tags
            opening_tags = len(re.findall(r'<\s*' + re.escape(tag_name) + r'\b[^/>]*(?<!/)>', line))
            closing_tags = len(re.findall(r'</' + re.escape(tag_name) + r'>', line))
            
            depth += opening_tags - closing_tags
            
            if depth <= 0:
                return i + 1
        
        # If no closing tag found, return start line
        return start_line
    
    def _highlight_element_block(self, xml_node, start_line: int):
        """Highlight the XML element block with an orange border and show line count."""
        # Check if highlighting is enabled
        if not self.highlight_enabled:
            return
        
        try:
            content = self.xml_editor.get_content()
            tag_name = xml_node.tag if hasattr(xml_node, 'tag') else xml_node.name
            
            # Find the end line of the element
            end_line = self._find_element_end_line(content, tag_name, start_line)
            
            # Calculate line count
            line_count = end_line - start_line + 1
            
            # Create multiple selections to simulate a border effect
            selections = []
            
            # Main block selection with orange background
            cursor = self.xml_editor.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.MoveAnchor, start_line - 1)
            cursor.movePosition(cursor.MoveOperation.StartOfLine)
            cursor.movePosition(cursor.MoveOperation.Down, cursor.MoveMode.KeepAnchor, line_count - 1)
            cursor.movePosition(cursor.MoveOperation.EndOfLine, cursor.MoveMode.KeepAnchor)
            
            selection = QTextEdit.ExtraSelection()
            selection.cursor = cursor
            fmt = QTextCharFormat()
            fmt.setBackground(QColor(255, 140, 0, 60))  # Orange background
            selection.format = fmt
            selections.append(selection)
            
            # Top border line (first line with darker orange)
            cursor_top = self.xml_editor.textCursor()
            cursor_top.movePosition(cursor_top.MoveOperation.Start)
            cursor_top.movePosition(cursor_top.MoveOperation.Down, cursor_top.MoveMode.MoveAnchor, start_line - 1)
            cursor_top.movePosition(cursor_top.MoveOperation.StartOfLine)
            cursor_top.movePosition(cursor_top.MoveOperation.EndOfLine, cursor_top.MoveMode.KeepAnchor)
            
            selection_top = QTextEdit.ExtraSelection()
            selection_top.cursor = cursor_top
            fmt_top = QTextCharFormat()
            fmt_top.setBackground(QColor(255, 100, 0, 120))  # Darker orange for border
            selection_top.format = fmt_top
            selections.append(selection_top)
            
            # Bottom border line (last line with darker orange)
            if line_count > 1:
                cursor_bottom = self.xml_editor.textCursor()
                cursor_bottom.movePosition(cursor_bottom.MoveOperation.Start)
                cursor_bottom.movePosition(cursor_bottom.MoveOperation.Down, cursor_bottom.MoveMode.MoveAnchor, end_line - 1)
                cursor_bottom.movePosition(cursor_bottom.MoveOperation.StartOfLine)
                cursor_bottom.movePosition(cursor_bottom.MoveOperation.EndOfLine, cursor_bottom.MoveMode.KeepAnchor)
                
                selection_bottom = QTextEdit.ExtraSelection()
                selection_bottom.cursor = cursor_bottom
                fmt_bottom = QTextCharFormat()
                fmt_bottom.setBackground(QColor(255, 100, 0, 120))  # Darker orange for border
                selection_bottom.format = fmt_bottom
                selections.append(selection_bottom)
            
            # Apply all selections
            self.xml_editor.setExtraSelections(selections)
            
            # Update status bar with line count
            self.status_label.setText(f"Selected {xml_node.name} at line {start_line} ({line_count} line{'s' if line_count != 1 else ''})")
            
            print(f"HIGHLIGHT: Element {tag_name} from line {start_line} to {end_line} ({line_count} lines)")
            
        except Exception as e:
            print(f"Error highlighting element block: {e}")
    
    def _auto_save(self):
        """Auto-save functionality"""
        if self.current_file and self.xml_editor.get_content().strip():
            try:
                content = self.xml_editor.get_content()
                auto_save_path = self.current_file + '.autosave'
                with open(auto_save_path, 'w', encoding='utf-8') as file:
                    file.write(content)
            except Exception:
                pass  # Silently fail for auto-save
    
    def closeEvent(self, event):
        """Handle close event"""
        # Clean up auto-save file
        if self.current_file:
            auto_save_path = self.current_file + '.autosave'
            if os.path.exists(auto_save_path):
                try:
                    os.remove(auto_save_path)
                except Exception:
                    pass
        
        event.accept()
    
    def toggle_theme(self):
        """Toggle between light and dark themes"""
        # Use QTimer to defer theme application and prevent UI hang
        current_style = self.styleSheet()
        if "dark" in current_style.lower():
            QTimer.singleShot(0, self.set_light_theme)
        else:
            QTimer.singleShot(0, self.set_dark_theme)
    
    def set_dark_theme(self):
        """Apply dark theme"""
        dark_style = """
        QMainWindow {
            background-color: #1e1e1e;
            color: #d4d4d4;
        }
        QMenuBar {
            background-color: #2d2d30;
            color: #d4d4d4;
            border-bottom: 1px solid #464647;
        }
        QMenuBar::item:selected {
            background-color: #094771;
        }
        QMenu {
            background-color: #2d2d30;
            color: #d4d4d4;
            border: 1px solid #464647;
        }
        QMenu::item:selected {
            background-color: #094771;
        }
        QToolBar {
            background-color: #2d2d30;
            border: none;
            padding: 2px;
        }
        QToolButton {
            background-color: #2d2d30;
            color: #d4d4d4;
            border: none;
            padding: 4px;
        }
        QToolButton:hover {
            background-color: #3e3e40;
        }
        QToolButton:pressed {
            background-color: #094771;
        }
        QTextEdit {
            background-color: #1e1e1e;
            color: #d4d4d4;
            border: 1px solid #464647;
            selection-background-color: #264f78;
        }
        QTreeWidget {
            background-color: #252526;
            color: #d4d4d4;
            border: 1px solid #464647;
            alternate-background-color: #1e1e1e;
        }
        QTreeWidget::item:selected {
            background-color: #094771;
        }
        QTreeWidget::header {
            background-color: #2d2d30;
            color: #d4d4d4;
            border: 1px solid #464647;
        }
        QTreeWidget::header::section {
            background-color: #2d2d30;
            color: #d4d4d4;
            border: 1px solid #464647;
            padding: 4px;
        }
        QTabWidget::pane {
            border: 1px solid #464647;
            background-color: #1e1e1e;
        }
        QTabBar::tab {
            background-color: #2d2d30;
            color: #d4d4d4;
            border: 1px solid #464647;
            padding: 8px 16px;
        }
        QTabBar::tab:selected {
            background-color: #1e1e1e;
            border-bottom: 1px solid #1e1e1e;
        }
        QStatusBar {
            background-color: #007acc;
            color: white;
        }
        QPushButton {
            background-color: #0e639c;
            color: white;
            border: none;
            padding: 6px 16px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #1177bb;
        }
        QPushButton:pressed {
            background-color: #094771;
        }
        QLineEdit {
            background-color: #3c3c3c;
            color: #d4d4d4;
            border: 1px solid #464647;
            padding: 4px;
        }
        QSpinBox {
            background-color: #3c3c3c;
            color: #d4d4d4;
            border: 1px solid #464647;
        }
        QListWidget {
            background-color: #1e1e1e;
            color: #d4d4d4;
            border: 1px solid #464647;
        }
        QLabel {
            background-color: #2d2d30;
            color: #d4d4d4;
            border: 1px solid #464647;
        }
        QScrollBar:vertical {
            background-color: #252526;
            border: none;
            width: 14px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background-color: #686868;
            border-radius: 7px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #9e9e9e;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            border: none;
            background: none;
            height: 0px;
        }
        QScrollBar:horizontal {
            background-color: #252526;
            border: none;
            height: 14px;
            margin: 0px;
        }
        QScrollBar::handle:horizontal {
            background-color: #686868;
            border-radius: 7px;
            min-width: 20px;
        }
        QScrollBar::handle:horizontal:hover {
            background-color: #9e9e9e;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            border: none;
            background: none;
            width: 0px;
        }
        """
        self.setStyleSheet(dark_style)
        
        # Update highlighter for dark theme
        if hasattr(self, 'xml_editor') and hasattr(self.xml_editor, 'highlighter'):
            self.xml_editor.highlighter.set_dark_theme(True)
        
        # Update breadcrumb label styling
        if hasattr(self, 'breadcrumb_label'):
            self.breadcrumb_label.setStyleSheet("""
                QLabel {
                    background-color: #2d2d30;
                    color: #d4d4d4;
                    padding: 4px 8px;
                    border: 1px solid #464647;
                    border-radius: 3px;
                }
            """)
        
        self.status_label.setText("Dark theme enabled")
        # Persist theme selection
        try:
            self._save_flag('dark_theme', True)
        except Exception:
            pass
    
    def set_light_theme(self):
        """Apply light theme"""
        self.setStyleSheet("")
        
        # Update highlighter for light theme
        if hasattr(self, 'xml_editor') and hasattr(self.xml_editor, 'highlighter'):
            self.xml_editor.highlighter.set_dark_theme(False)
        
        self.status_label.setText("Light theme enabled")
        # Persist theme selection
        try:
            self._save_flag('dark_theme', False)
        except Exception:
            pass
    
    def toggle_breadcrumbs(self):
        """Toggle breadcrumb visibility"""
        is_visible = self.toggle_breadcrumb_action.isChecked()
        self.breadcrumb_label.setVisible(is_visible)
        self.status_label.setText(f"Breadcrumbs {'shown' if is_visible else 'hidden'}")
        # Persist
        try:
            self._save_flag('show_breadcrumbs', is_visible)
        except Exception:
            pass
    
    def toggle_bottom_panel(self):
        """Toggle bottom panel visibility"""
        is_visible = self.toggle_bottom_panel_action.isChecked()
        try:
            self.bottom_dock.setVisible(is_visible)
        except Exception:
            try:
                self.bottom_panel.setVisible(is_visible)
            except Exception:
                pass
        self.status_label.setText(f"Bottom panel {'shown' if is_visible else 'hidden'}")
        # Persist
        try:
            self._save_flag('show_bottom_panel', is_visible)
        except Exception:
            pass
    
    def _show_bottom_panel_auto(self, tab_name=None):
        """Automatically show bottom panel when needed (search, bookmarks, etc.)"""
        try:
            self.bottom_dock.setVisible(True)
            # Sync the menu action without emitting signals
            if hasattr(self, 'toggle_bottom_panel_action'):
                self.toggle_bottom_panel_action.blockSignals(True)
                self.toggle_bottom_panel_action.setChecked(True)
                self.toggle_bottom_panel_action.blockSignals(False)
            # Switch to specific tab if requested
            if tab_name and hasattr(self, 'bottom_panel'):
                if tab_name == "bookmarks":
                    self.bottom_panel.setCurrentWidget(self.bottom_panel.bookmarks_tab)
                elif tab_name == "find":
                    self.bottom_panel.setCurrentWidget(self.bottom_panel.find_tab)
                elif tab_name == "validation":
                    self.bottom_panel.setCurrentWidget(self.bottom_panel.validation_tab)
        except Exception as e:
            print(f"Error showing bottom panel: {e}")
    
    def copy_current_node_with_subnodes(self):
        """Copy current tree node with all subnodes to clipboard as XML"""
        try:
            # Get currently selected tree item
            current_item = self.xml_tree.currentItem()
            if not current_item or not hasattr(current_item, 'xml_node'):
                self.status_label.setText("No tree node selected")
                return
            
            xml_node = current_item.xml_node
            if not xml_node:
                self.status_label.setText("Invalid tree node")
                return
            
            # Get the XML content for this node and its subnodes
            xml_content = self._extract_node_xml(xml_node, current_item)
            
            if xml_content:
                # Copy to clipboard
                clipboard = QApplication.clipboard()
                clipboard.setText(xml_content)
                self.status_label.setText(f"Copied node '{xml_node.name}' with subnodes to clipboard")
            else:
                self.status_label.setText("Failed to extract node XML content")
                
        except Exception as e:
            print(f"Error copying node: {e}")
            self.status_label.setText(f"Error copying node: {str(e)}")
    
    def open_node_in_new_window(self):
        """Open a new application window with current node and its subnodes"""
        try:
            # Get currently selected tree item
            current_item = self.xml_tree.currentItem()
            if not current_item or not hasattr(current_item, 'xml_node'):
                self.status_label.setText("No tree node selected")
                return
            
            xml_node = current_item.xml_node
            if not xml_node:
                self.status_label.setText("Invalid tree node")
                return
            
            # Get the XML content for this node and its subnodes
            xml_content = self._extract_node_xml(xml_node, current_item)
            
            if xml_content:
                # Create a new window instance
                new_window = MainWindow()
                new_window.setWindowTitle(f"Lotus Xml Editor - {xml_node.name}")
                
                # Set the extracted XML content
                new_window.xml_editor.set_content(xml_content)
                
                # Parse and populate the tree
                new_window.tree_widget.populate_tree(xml_content)
                
                # Show the new window
                new_window.show()
                
                self.status_label.setText(f"Opened node '{xml_node.name}' in new window")
            else:
                self.status_label.setText("Failed to extract node XML content")
                
        except Exception as e:
            print(f"Error opening node in new window: {e}")
            self.status_label.setText(f"Error opening node in new window: {str(e)}")
    
    def open_multicolumn_tree(self):
        """Open experimental multicolumn tree window"""
        try:
            # Get current XML content
            xml_content = self.xml_editor.get_content()
            
            if not xml_content.strip():
                self.status_label.setText("No XML content to display in multicolumn tree")
                return
            
            # Create and show multicolumn tree window
            multicolumn_window = MultiColumnTreeWindow(xml_content, self)
            # Track window for sync propagation
            try:
                self.multicolumn_windows.append(multicolumn_window)
                multicolumn_window.set_sync_enabled(getattr(self, 'sync_enabled', False))
                multicolumn_window.destroyed.connect(lambda _: self.multicolumn_windows.remove(multicolumn_window) if multicolumn_window in self.multicolumn_windows else None)
            except Exception as e:
                print(f"Error tracking multicolumn window: {e}")
            multicolumn_window.show()
            
            self.status_label.setText("Opened experimental multicolumn tree window")
            
        except Exception as e:
            print(f"Error opening multicolumn tree: {e}")
            self.status_label.setText(f"Error opening multicolumn tree: {str(e)}")
    
    def _extract_node_xml(self, xml_node, tree_item):
        """Extract XML content for a node and all its subnodes"""
        try:
            # Get the full XML content
            full_content = self.xml_editor.get_content()
            if not full_content.strip():
                return None
            
            # Parse the XML to find the node
            import xml.etree.ElementTree as ET
            root = ET.fromstring(full_content)
            
            # Find the target element using the node's path
            if hasattr(xml_node, 'path') and xml_node.path:
                # Ensure path starts with '/' for consistency
                node_path = xml_node.path
                if not node_path.startswith('/'):
                    node_path = '/' + node_path
                target_element = self._find_element_by_path(root, node_path)
                if target_element is not None:
                    # Convert the element and its subnodes back to XML string
                    xml_string = ET.tostring(target_element, encoding='unicode', xml_declaration=False)
                    
                    # Format the XML for better readability
                    try:
                        # Try to format with minidom
                        from xml.dom import minidom
                        dom = minidom.parseString(f'<?xml version="1.0" encoding="UTF-8"?>{xml_string}')
                        formatted_xml = dom.toprettyxml(indent="  ", encoding=None)
                        # Remove the first line (XML declaration) and empty lines
                        lines = [line for line in formatted_xml.split('\n') if line.strip()]
                        if lines and lines[0].startswith('<?xml'):
                            lines = lines[1:]
                        return '\n'.join(lines)
                    except:
                        # Fallback to unformatted XML
                        return xml_string
            
            return None
            
        except Exception as e:
            print(f"Error extracting node XML: {e}")
            return None
    
    def _find_element_by_path(self, root, path):
        """Find an XML element by its path"""
        try:
            if not path or path == "/":
                return root
            
            # Remove leading slash and split path
            path_parts = path.split('/')[1:] if path.startswith('/') else path.split('/')
            
            # If the path is just the root element name, return root
            if len(path_parts) == 1 and path_parts[0] == root.tag:
                return root
            
            current = root
            # Skip the first part if it matches the root tag
            start_index = 1 if len(path_parts) > 0 and path_parts[0] == root.tag else 0
            
            for part in path_parts[start_index:]:
                # Handle indexed elements like "Группа[2]"
                if '[' in part and ']' in part:
                    tag_name = part.split('[')[0]
                    index_part = part[part.find('[')+1:part.find(']')]
                    
                    if index_part.isdigit():
                        # Numeric index
                        index = int(index_part) - 1  # Convert to 0-based
                        matching_children = [child for child in current if child.tag == tag_name]
                        if 0 <= index < len(matching_children):
                            current = matching_children[index]
                        else:
                            return None
                    elif 'Наименование=' in index_part:
                        # Attribute-based selection
                        attr_value = index_part.split('Наименование="')[1].split('"')[0]
                        found = False
                        for child in current:
                            if child.tag == tag_name:
                                # Look for Наименование child element
                                name_elem = child.find('Наименование')
                                if name_elem is not None and name_elem.text == attr_value:
                                    current = child
                                    found = True
                                    break
                        if not found:
                            return None
                else:
                    # Simple tag name
                    found = False
                    for child in current:
                        if child.tag == part:
                            current = child
                            found = True
                            break
                    if not found:
                        return None
            
            return current
            
        except Exception as e:
            print(f"Error finding element by path: {e}")
            return None
    
    def clear_bookmarks(self):
        """Clear all bookmarks"""
        self.bookmarks.clear()
        self.current_bookmark_index = -1
        try:
            self.numbered_bookmarks.clear()
        except Exception:
            pass
        self.status_label.setText("All bookmarks cleared")
        try:
            self.bottom_panel.clear_bookmarks()
        except Exception:
            pass
        try:
            self._update_bookmark_highlights()
        except Exception:
            pass
    
    def toggle_bookmark(self):
        """Toggle bookmark at current line"""
        cursor = self.xml_editor.textCursor()
        line_number = cursor.blockNumber() + 1
        
        if line_number in self.bookmarks:
            # Remove bookmark
            del self.bookmarks[line_number]
            self.status_label.setText(f"Bookmark removed from line {line_number}")
        else:
            # Add bookmark
            self.bookmarks[line_number] = f"Line {line_number}"
            self.status_label.setText(f"Bookmark added to line {line_number}")
            # Show bottom panel when bookmark is added
            self._show_bottom_panel_auto("bookmarks")
        # Refresh bottom panel list and highlights
        try:
            self._refresh_bookmarks_panel()
        except Exception:
            pass
        try:
            self._update_bookmark_highlights()
        except Exception:
            pass

    def remove_bookmark(self, line_number: int):
        """Remove a specific bookmark by line number"""
        try:
            if line_number in self.bookmarks:
                del self.bookmarks[line_number]
            # Remove from numbered bookmarks if it points to this line
            try:
                to_delete = [d for d, ln in self.numbered_bookmarks.items() if ln == line_number]
                for d in to_delete:
                    del self.numbered_bookmarks[d]
            except Exception:
                pass
            self.status_label.setText(f"Bookmark cleared at line {line_number}")
            self._refresh_bookmarks_panel()
            self._update_bookmark_highlights()
        except Exception:
            pass
    
    def next_bookmark(self):
        """Navigate to next bookmark"""
        if not self.bookmarks:
            self.status_label.setText("No bookmarks set")
            return
        
        cursor = self.xml_editor.textCursor()
        current_line = cursor.blockNumber() + 1
        
        # Get sorted list of bookmark lines
        bookmark_lines = sorted(self.bookmarks.keys())
        
        # Find next bookmark
        next_line = None
        for line in bookmark_lines:
            if line > current_line:
                next_line = line
                break
        
        # If no next bookmark, go to first one
        if next_line is None:
            next_line = bookmark_lines[0]
        
        self.goto_line(next_line)
        self.status_label.setText(f"Jumped to bookmark at line {next_line}")
    
    def prev_bookmark(self):
        """Navigate to previous bookmark"""
        if not self.bookmarks:
            self.status_label.setText("No bookmarks set")
            return
        
        cursor = self.xml_editor.textCursor()
        current_line = cursor.blockNumber() + 1
        
        # Get sorted list of bookmark lines
        bookmark_lines = sorted(self.bookmarks.keys())
        
        # Find previous bookmark
        prev_line = None
        for line in reversed(bookmark_lines):
            if line < current_line:
                prev_line = line
                break
        
        # If no previous bookmark, go to last one
        if prev_line is None:
            prev_line = bookmark_lines[-1]
        
        self.goto_line(prev_line)
        self.status_label.setText(f"Jumped to bookmark at line {prev_line}")

    def _refresh_bookmarks_panel(self):
        """Populate the bookmarks tab list from current bookmarks"""
        try:
            self.bottom_panel.clear_bookmarks()
            content_lines = []
            try:
                content_lines = self.xml_editor.get_content().splitlines()
            except Exception:
                pass
            for line in sorted(self.bookmarks.keys()):
                line_text = ""
                try:
                    if 0 <= (line - 1) < len(content_lines):
                        line_text = content_lines[line - 1].strip()
                except Exception:
                    pass
                # Use plain line number to the left and text without digit tags
                self.bottom_panel.add_bookmark_item(line, line_text)
            # Show bottom panel when bookmarks exist
            if self.bookmarks:
                self._show_bottom_panel_auto("bookmarks")
        except Exception:
            pass

    def _update_bookmark_highlights(self):
        """Highlight bookmarked lines in the editor using extra selections"""
        try:
            selections = []
            doc = self.xml_editor.document()
            for line in self.bookmarks.keys():
                block = doc.findBlockByNumber(line - 1)
                if not block.isValid():
                    continue
                cursor = QTextCursor(block)
                fmt = QTextCharFormat()
                fmt.setBackground(QColor(255, 240, 200))  # soft highlight color
                sel = QTextEdit.ExtraSelection()
                sel.cursor = cursor
                sel.format = fmt
                selections.append(sel)
            self.xml_editor.setExtraSelections(selections)
        except Exception:
            pass

    def set_numbered_bookmark(self, digit: int):
        """Set a numbered bookmark (1..9) to current line"""
        try:
            cursor = self.xml_editor.textCursor()
            line_number = cursor.blockNumber() + 1
            self.numbered_bookmarks[digit] = line_number
            self.status_label.setText(f"Set bookmark {digit} at line {line_number}")
            # Ensure it's also present in normal bookmarks for list/highlight
            if line_number not in self.bookmarks:
                self.bookmarks[line_number] = f"Line {line_number}"
            self._refresh_bookmarks_panel()
            self._update_bookmark_highlights()
        except Exception:
            pass

    def goto_numbered_bookmark(self, digit: int):
        """Go to a numbered bookmark line if set"""
        try:
            if digit in self.numbered_bookmarks:
                self.goto_line(self.numbered_bookmarks[digit])
                self.status_label.setText(f"Jumped to bookmark {digit} at line {self.numbered_bookmarks[digit]}")
            else:
                self.status_label.setText(f"Bookmark {digit} not set")
        except Exception:
            pass
    
    def _load_recent_files(self):
        """Load recent files from configuration"""
        try:
            config_path = os.path.join(os.path.expanduser("~"), ".visxml_recent")
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.recent_files = [line.strip() for line in f.readlines() if line.strip()]
                    # Remove non-existent files
                    self.recent_files = [f for f in self.recent_files if os.path.exists(f)]
        except Exception:
            self.recent_files = []
        
        # Update menu after loading
        self._update_recent_files_menu()
    
    def _save_recent_files(self):
        """Save recent files to configuration"""
        try:
            config_path = os.path.join(os.path.expanduser("~"), ".visxml_recent")
            with open(config_path, 'w', encoding='utf-8') as f:
                for file_path in self.recent_files[:self.max_recent_files]:
                    f.write(file_path + '\n')
        except Exception:
            pass
    
    def _add_to_recent_files(self, file_path):
        """Add file to recent files list"""
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        self.recent_files.insert(0, file_path)
        self.recent_files = self.recent_files[:self.max_recent_files]
        self._save_recent_files()
        self._update_recent_files_menu()
    
    def _update_recent_files_menu(self):
        """Update the recent files menu with current list"""
        if not self.recent_files_menu:
            return
        
        # Clear existing actions
        self.recent_files_menu.clear()
        
        # Add recent files
        if self.recent_files:
            for i, file_path in enumerate(self.recent_files[:self.max_recent_files]):
                if os.path.exists(file_path):
                    # Show just the filename, with full path as tooltip
                    display_name = f"{i+1}. {os.path.basename(file_path)}"
                    action = QAction(display_name, self)
                    action.setToolTip(file_path)
                    action.triggered.connect(lambda checked, path=file_path: self._open_recent_file(path))
                    self.recent_files_menu.addAction(action)
            
            # Add separator and clear action
            self.recent_files_menu.addSeparator()
            clear_action = QAction("Clear Recent Files", self)
            clear_action.triggered.connect(self._clear_recent_files)
            self.recent_files_menu.addAction(clear_action)
        else:
            # Show "No recent files" when list is empty
            no_files_action = QAction("No recent files", self)
            no_files_action.setEnabled(False)
            self.recent_files_menu.addAction(no_files_action)
    
    def _open_recent_file(self, file_path):
        """Open a file from the recent files list"""
        if os.path.exists(file_path):
            self._load_file_from_path(file_path)
            self.status_label.setText(f"Opened recent file: {os.path.basename(file_path)}")
        else:
            QMessageBox.warning(self, "File Not Found", 
                              f"The file no longer exists:\n{file_path}")
            # Remove from recent files
            if file_path in self.recent_files:
                self.recent_files.remove(file_path)
                self._save_recent_files()
                self._update_recent_files_menu()
    
    def _clear_recent_files(self):
        """Clear the recent files list"""
        reply = QMessageBox.question(self, "Clear Recent Files",
                                    "Are you sure you want to clear the recent files list?",
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.recent_files = []
            self._save_recent_files()
            self._update_recent_files_menu()
            self.status_label.setText("Recent files cleared")
    
    def _open_most_recent_file(self):
        """Open the most recent file on startup"""
        if self.recent_files and os.path.exists(self.recent_files[0]):
            self._load_file_from_path(self.recent_files[0])
            self.status_label.setText(f"Opened recent file: {os.path.basename(self.recent_files[0])}")
            # Hide file navigator since we opened a file from history
            self._set_file_navigator_visible(False)
        else:
            self.status_label.setText("Ready - No recent files to open")
    
    def _load_file_from_path(self, file_path: str, use_cache: bool = True):
        """Load file from specific path (used for recent files)
        
        Args:
            file_path: Path to the file to load
            use_cache: If True, try to load from cache for faster startup
        """
        try:
            # Enter loading mode to prevent redundant content-change handling
            self._loading_file = True
            print(f"DEBUG: Loading file from path: {file_path}")
            print(f"DEBUG: File exists: {os.path.exists(file_path)}")
            
            # Check file size first
            file_size = os.path.getsize(file_path)
            print(f"DEBUG: File size: {file_size} bytes")
            
            # Try to load from cache for faster startup
            cache_loaded = False
            if use_cache:
                cache_loaded = self._try_load_from_cache(file_path, file_size)
            
            if not cache_loaded:
                # For large files (>1MB), show progress and use chunked reading
                if file_size > 1024 * 1024:
                    self.status_label.setText(f"Loading large file ({file_size / 1024 / 1024:.1f} MB)...")
                    QApplication.processEvents()  # Update UI
                    
                    # Read large files in chunks to avoid memory issues
                    content = self._read_large_file(file_path)
                else:
                    # Read small files normally
                    with open(file_path, 'r', encoding='utf-8') as file:
                        content = file.read()
                
                print(f"DEBUG: Content length: {len(content) if content else 0} characters")
                print(f"DEBUG: First 100 chars: {content[:100] if content else 'None'}")
                
                self.xml_editor.set_content(content)
                
                # Defer tree building for large files to speed up initial load
                lines_count = len(content.split('\n')) if content else 0
                file_size_mb = (file_size / (1024 * 1024)) if file_size else 0
                
                if file_size_mb > 2.0:  # For files > 2MB, defer tree building
                    self.status_label.setText(f"File loaded. Building tree in background...")
                    QApplication.processEvents()
                    # Use QTimer to defer tree building, allowing UI to be responsive
                    QTimer.singleShot(100, lambda: self._deferred_tree_build(content, file_path, file_size))
                else:
                    self.xml_tree.populate_tree(content)
                    self._finalize_file_load(file_path, file_size, content)
                
                # Save to cache for next startup
                if use_cache:
                    self._save_to_cache(file_path, content, file_size)
            
            # Exit loading mode
            self._loading_file = False
            
        except Exception as e:
            print(f"DEBUG: Error loading file: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to open file: {str(e)}")
            self.status_label.setText("Ready")
            # Ensure we exit loading mode even on failure
            self._loading_file = False
    
    def _deferred_tree_build(self, content: str, file_path: str, file_size: int):
        """Build tree in a deferred manner for large files"""
        try:
            self.xml_tree.populate_tree(content)
            self._finalize_file_load(file_path, file_size, content)
        except Exception as e:
            print(f"DEBUG: Error in deferred tree build: {str(e)}")
            self.status_label.setText(f"Opened: {file_path} (tree build failed)")
    
    def _finalize_file_load(self, file_path: str, file_size: int, content: str):
        """Finalize file loading after tree is built"""
        # Decide index/cache enablement based on size/lines
        lines_count = len(content.split('\n')) if content else 0
        file_size_mb = (file_size / (1024 * 1024)) if file_size else 0
        self.sync_index_enabled = (lines_count > 8000 or file_size_mb > 1.0)
        self.sync_cache_enabled = (lines_count > 8000 or file_size_mb > 1.0)
        # Reset caches
        self.path_line_cache = {}
        self.path_line_index = {}
        if self.sync_index_enabled:
            self._build_path_line_index(content)
            print(f"DEBUG: Index enabled={self.sync_index_enabled}, available={self._sync_index_available}, entries={len(self.path_line_index)}")
        else:
            print(f"DEBUG: Index/cache disabled for small file (lines={lines_count}, size={file_size_mb:.2f}MB)")
        
        self.current_file = file_path
        self.setWindowTitle(f"Lotus Xml Editor - {os.path.basename(file_path)}")
        self.status_label.setText(f"Opened: {file_path}")
        
        # Update encoding label
        self.encoding_label.setText("UTF-8")
    
    def _try_load_from_cache(self, file_path: str, file_size: int) -> bool:
        """Try to load file from cache for faster startup
        
        Returns:
            True if loaded from cache, False otherwise
        """
        try:
            import pickle
            import hashlib
            
            # Create cache directory
            cache_dir = os.path.join(os.path.expanduser("~"), ".visxml_cache")
            os.makedirs(cache_dir, exist_ok=True)
            
            # Generate cache key from file path and modification time
            file_mtime = os.path.getmtime(file_path)
            cache_key = hashlib.md5(f"{file_path}_{file_mtime}_{file_size}".encode()).hexdigest()
            cache_file = os.path.join(cache_dir, f"{cache_key}.cache")
            
            if os.path.exists(cache_file):
                # Check if cache is recent (within 24 hours)
                cache_age = os.path.getmtime(cache_file)
                if (os.path.getmtime(file_path) <= cache_age):
                    print(f"DEBUG: Loading from cache: {cache_file}")
                    with open(cache_file, 'rb') as f:
                        cached_data = pickle.load(f)
                    
                    # Load cached content
                    content = cached_data.get('content', '')
                    self.xml_editor.set_content(content)
                    
                    # Note: We still need to rebuild the tree as it contains Qt objects
                    # that can't be pickled, but having the content cached speeds things up
                    self.xml_tree.populate_tree(content)
                    self._finalize_file_load(file_path, file_size, content)
                    
                    self.status_label.setText(f"Loaded from cache: {os.path.basename(file_path)}")
                    print(f"DEBUG: Successfully loaded from cache")
                    return True
            
            return False
        except Exception as e:
            print(f"DEBUG: Cache load failed: {str(e)}")
            return False
    
    def _save_to_cache(self, file_path: str, content: str, file_size: int):
        """Save file content to cache for faster next startup"""
        try:
            import pickle
            import hashlib
            
            # Don't cache very large files (> 10MB)
            if file_size > 10 * 1024 * 1024:
                return
            
            # Create cache directory
            cache_dir = os.path.join(os.path.expanduser("~"), ".visxml_cache")
            os.makedirs(cache_dir, exist_ok=True)
            
            # Generate cache key
            file_mtime = os.path.getmtime(file_path)
            cache_key = hashlib.md5(f"{file_path}_{file_mtime}_{file_size}".encode()).hexdigest()
            cache_file = os.path.join(cache_dir, f"{cache_key}.cache")
            
            # Save to cache
            cached_data = {
                'content': content,
                'file_path': file_path,
                'file_size': file_size,
                'mtime': file_mtime
            }
            
            with open(cache_file, 'wb') as f:
                pickle.dump(cached_data, f)
            
            print(f"DEBUG: Saved to cache: {cache_file}")
            
            # Clean up old cache files (keep only last 10)
            self._cleanup_old_cache(cache_dir)
            
        except Exception as e:
            print(f"DEBUG: Cache save failed: {str(e)}")
    
    def _cleanup_old_cache(self, cache_dir: str):
        """Clean up old cache files, keeping only the most recent ones"""
        try:
            cache_files = []
            for filename in os.listdir(cache_dir):
                if filename.endswith('.cache'):
                    filepath = os.path.join(cache_dir, filename)
                    cache_files.append((os.path.getmtime(filepath), filepath))
            
            # Sort by modification time (newest first)
            cache_files.sort(reverse=True)
            
            # Keep only the 10 most recent cache files
            for _, filepath in cache_files[10:]:
                try:
                    os.remove(filepath)
                    print(f"DEBUG: Removed old cache file: {filepath}")
                except Exception:
                    pass
        except Exception as e:
            print(f"DEBUG: Cache cleanup failed: {str(e)}")
    
    def show_split_dialog(self):
        """Show XML split configuration dialog"""
        if not self.xml_editor.get_content().strip():
            QMessageBox.warning(self, "Warning", "No XML content to split. Please open or create an XML file first.")
            return
        
        try:
            dialog = XmlSplitConfigDialog(self, self.xml_editor.get_content())
            if dialog.exec() == QDialog.DialogCode.Accepted:
                config = dialog.get_split_config()
                output_dir = dialog.get_output_directory()
                create_backup = dialog.should_create_backup()
                
                if not output_dir:
                    QMessageBox.warning(self, "Warning", "Please select an output directory.")
                    return
                
                # Create output directory if it doesn't exist
                os.makedirs(output_dir, exist_ok=True)
                
                # Create backup if requested
                if create_backup and self.current_file:
                    backup_path = self.current_file + ".backup"
                    try:
                        import shutil
                        shutil.copy2(self.current_file, backup_path)
                        self.bottom_panel.append_output(f"Backup created: {backup_path}")
                    except Exception as e:
                        QMessageBox.warning(self, "Backup Warning", f"Failed to create backup: {str(e)}")
                
                # Perform the split
                self.status_label.setText("Splitting XML...")
                QApplication.processEvents()
                
                success = self.xml_service.split_xml_content(
                    self.xml_editor.get_content(),
                    output_dir,
                    config
                )
                
                if success:
                    self.status_label.setText("XML split completed successfully")
                    self.bottom_panel.append_output(f"XML split completed. Output directory: {output_dir}")
                    
                    # Ask if user wants to open the split project
                    reply = QMessageBox.question(
                        self, "Split Complete", 
                        "XML has been split successfully. Would you like to open the split project?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    
                    if reply == QMessageBox.StandardButton.Yes:
                        self._open_split_project_directory(output_dir)
                else:
                    self.status_label.setText("XML split failed")
                    QMessageBox.critical(self, "Error", "Failed to split XML. Check the output panel for details.")
                    
        except Exception as e:
            self.status_label.setText("Ready")
            QMessageBox.critical(self, "Error", f"Failed to show split dialog: {str(e)}")
    
    def open_split_project(self):
        """Open an existing split XML project"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Split Project Directory", 
            os.getcwd(), QFileDialog.Option.ShowDirsOnly
        )
        
        if directory:
            self._open_split_project_directory(directory)
    
    def _open_split_project_directory(self, directory: str):
        """Open a split project directory"""
        try:
            # Check if it's a valid split project
            project_info = self.xml_service.get_split_project_info(directory)
            
            if not project_info.get('is_valid', False):
                QMessageBox.warning(self, "Invalid Project", "The selected directory is not a valid split XML project.")
                return
            
            # Show project information
            stats = project_info.get('statistics', {})
            parts = project_info.get('parts', [])
            
            info_text = f"Split Project Information:\n\n"
            info_text += f"Directory: {directory}\n"
            info_text += f"Number of parts: {len(parts)}\n"
            info_text += f"Total elements: {stats.get('total_elements', 'Unknown')}\n"
            info_text += f"Total size: {stats.get('total_size', 'Unknown')} bytes\n\n"
            info_text += "Parts:\n"
            
            for i, part in enumerate(parts[:10]):  # Show first 10 parts
                info_text += f"  {i+1}. {part}\n"
            
            if len(parts) > 10:
                info_text += f"  ... and {len(parts) - 10} more parts\n"
            
            self.bottom_panel.append_output(info_text)
            self.status_label.setText(f"Opened split project: {os.path.basename(directory)}")
            
            # Ask if user wants to reconstruct the XML
            reply = QMessageBox.question(
                self, "Split Project Opened", 
                "Split project opened successfully. Would you like to reconstruct and view the complete XML?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self._reconstruct_and_load(directory)
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open split project: {str(e)}")
    
    def reconstruct_from_parts(self):
        """Reconstruct XML from split parts"""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Split Project Directory", 
            os.getcwd(), QFileDialog.Option.ShowDirsOnly
        )
        
        if directory:
            self._reconstruct_and_load(directory)
    
    def quick_split_three_parts(self):
        """
        One-click split of the current XML into 3 parts using a size-balanced strategy.
        - We measure the byte size of each root-level child element.
        - We distribute the heaviest elements across different parts first, then place remaining
          elements using a greedy approach to minimize size disparity, followed by local balancing
          moves to further equalize part sizes.
        - Each part keeps the original root tag and attributes, making it compatible with the
          File Navigator's Combine button (root merge method) to recombine after editing.
        """
        try:
            # Ensure we have content to split
            if not hasattr(self, 'xml_editor') or not self.xml_editor.get_content().strip():
                QMessageBox.warning(self, "No Content", "There is no XML content to split.")
                return
            # Ensure file is saved so we can place parts next to it
            if not getattr(self, 'current_file', None):
                QMessageBox.warning(self, "Unsaved File", "Please save the file first so parts can be created alongside it.")
                return
            
            content = self.xml_editor.get_content()
            root = self.xml_service.parse_xml(content)
            if root is None:
                QMessageBox.critical(self, "Parse Error", "Failed to parse the XML. Please fix errors and try again.")
                return
            
            children = list(root)
            chunk_count = 3
            
            import xml.etree.ElementTree as ET
            import copy
            
            # Compute weight (byte length) for each child by serializing to bytes.
            # If serialization fails, fall back to weight=1 to ensure inclusion.
            weights = []
            for child in children:
                try:
                    weights.append(len(ET.tostring(child, encoding='utf-8')))
                except Exception:
                    weights.append(1)
            
            # Heavy-first distribution with balancing:
            # 1) Identify the top heavy root children and seed bins with them.
            # 2) Assign remaining children by LPT (greedy to smallest bin total).
            # 3) Perform a few local balancing moves to reduce max-min disparity.
            n = len(children)
            items = list(zip(children, weights))
            # Sort descending by weight to identify heavy ones
            items.sort(key=lambda x: x[1], reverse=True)
            bins = [[] for _ in range(chunk_count)]
            totals = [0] * chunk_count
            
            # Seed bins with up to top-3 heavy items
            heavy_seed_count = min(chunk_count, len(items))
            for i in range(heavy_seed_count):
                child, w = items[i]
                bins[i].append(child)
                totals[i] += w
            
            # Assign the rest using LPT to the bin with smallest total
            for child, w in items[heavy_seed_count:]:
                idx = min(range(chunk_count), key=lambda i: totals[i])
                bins[idx].append(child)
                totals[idx] += w
            
            # Local balancing: try moving a smallest item from the largest bin to the smallest bin
            # if it reduces disparity. Limit iterations to avoid long runtime.
            def _bin_weight(children_list):
                try:
                    return sum(len(ET.tostring(c, encoding='utf-8')) for c in children_list)
                except Exception:
                    return len(children_list)
            
            for _ in range(10):
                max_idx = max(range(chunk_count), key=lambda i: totals[i])
                min_idx = min(range(chunk_count), key=lambda i: totals[i])
                if max_idx == min_idx:
                    break
                if not bins[max_idx]:
                    break
                # Pick the smallest-weight item in the largest bin
                smallest_item = min(bins[max_idx], key=lambda c: len(ET.tostring(c, encoding='utf-8')) if c is not None else 1)
                smallest_weight = len(ET.tostring(smallest_item, encoding='utf-8')) if smallest_item is not None else 1
                # Check improvement if we move it
                new_max = max(totals[max_idx] - smallest_weight, totals[min_idx] + smallest_weight, *[totals[i] for i in range(chunk_count) if i not in (max_idx, min_idx)])
                current_max = max(totals)
                if new_max < current_max:
                    # Move item
                    bins[max_idx].remove(smallest_item)
                    bins[min_idx].append(smallest_item)
                    totals[max_idx] -= smallest_weight
                    totals[min_idx] += smallest_weight
                else:
                    break
            
            base_dir = os.path.dirname(self.current_file)
            base_name = os.path.splitext(os.path.basename(self.current_file))[0]
            part_paths = []
            
            for i in range(1, chunk_count + 1):
                # Create new root with same tag and attributes
                part_root = ET.Element(root.tag, attrib=dict(root.attrib))
                
                # Append deep-copied children assigned to this bin
                for child in bins[i - 1]:
                    part_root.append(copy.deepcopy(child))
                
                # Serialize and format
                xml_str = ET.tostring(part_root, encoding='unicode')
                formatted = self.xml_service.format_xml(xml_str)
                
                part_filename = f"{base_name}_part{i}.xml"
                part_path = os.path.join(base_dir, part_filename)
                with open(part_path, 'w', encoding='utf-8') as f:
                    f.write(formatted)
                part_paths.append(part_path)
            
            # Refresh file navigator to show newly created parts
            try:
                if hasattr(self, 'file_navigator') and self.file_navigator:
                    self.file_navigator._refresh_directory()
            except Exception:
                pass
            
            # Update status and inform user
            if hasattr(self, 'status_label') and self.status_label:
                self.status_label.setText(f"Split into 3 parts: {', '.join([os.path.basename(p) for p in part_paths])}")
            if hasattr(self, 'bottom_panel') and self.bottom_panel:
                self.bottom_panel.append_output("Quick Split completed:\n" + "\n".join(part_paths))
            QMessageBox.information(self, "Quick Split", "XML was split into 3 parts next to the original file.\nUse the File Navigator's Combine button to merge after editing.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Quick Split failed: {e}")
    
    def _reconstruct_and_load(self, directory: str):
        """Reconstruct XML from parts and load into editor"""
        try:
            self.status_label.setText("Reconstructing XML...")
            QApplication.processEvents()
            
            # Reconstruct the XML
            reconstructed_xml = self.xml_service.reconstruct_xml_from_parts(directory)
            
            if reconstructed_xml:
                # Load the reconstructed XML into the editor
                self.xml_editor.set_content(reconstructed_xml)
                self.xml_tree.populate_tree(reconstructed_xml)
                
                # Update window title and status
                self.current_file = None  # Mark as unsaved
                self.setWindowTitle(f"Lotus Xml Editor - Reconstructed from {os.path.basename(directory)}")
                self.status_label.setText("XML reconstructed successfully")
                
                self.bottom_panel.append_output(f"XML reconstructed from split project: {directory}")
                
                # Ask if user wants to save the reconstructed XML
                reply = QMessageBox.question(
                    self, "Save Reconstructed XML", 
                    "XML has been reconstructed successfully. Would you like to save it to a file?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    self.save_file_as()
            else:
                self.status_label.setText("Reconstruction failed")
                QMessageBox.critical(self, "Error", "Failed to reconstruct XML from parts.")
                
        except Exception as e:
            self.status_label.setText("Ready")
            QMessageBox.critical(self, "Error", f"Failed to reconstruct XML: {str(e)}")

    def _on_diagram_xpath_clicked(self, xpath: str):
        try:
            if hasattr(self, 'bottom_panel') and self.bottom_panel:
                self.bottom_panel.append_output(f"Diagram XPath clicked: {xpath}")
            if hasattr(self, 'status_label') and self.status_label:
                self.status_label.setText(f"XPath: {xpath}")
            print(xpath)
        except Exception:
            pass

    def open_structure_diagram(self):
        try:
            content = self.xml_editor.get_content() if hasattr(self, 'xml_editor') else ''
            if not content.strip():
                QMessageBox.warning(self, "No Content", "There is no XML content to visualize.")
                return
            # Open diagram in a separate top-level window (no parent) and pass debug logger
            self.diagram_window = StructureDiagramWindow(content, on_xpath_clicked=self._on_diagram_xpath_clicked, on_debug_log=self._on_diagram_debug_log, parent=None)
            self.diagram_window.show()
            if hasattr(self, 'status_label') and self.status_label:
                self.status_label.setText("Structure Diagram opened")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open Structure Diagram: {e}")

    def _on_diagram_debug_log(self, message: str):
        try:
            print(f"[Diagram] {message}")
        except Exception:
            pass
        try:
            if hasattr(self, 'bottom_panel') and self.bottom_panel:
                self.bottom_panel.append_output(message)
            if hasattr(self, 'status_label') and self.status_label:
                self.status_label.setText(message)
        except Exception:
            pass
    
    def toggle_file_navigator(self):
        """Toggle file navigator visibility"""
        is_visible = self.file_navigator.isVisible()
        self.file_navigator.setVisible(not is_visible)
        if hasattr(self, 'show_file_navigator_action'):
            self.show_file_navigator_action.setChecked(not is_visible)
        # if hasattr(self, 'status_label') and self.status_label:
        #     self.status_label.setText(f"File navigator {'hidden' if is_visible else 'shown'}")
        # Persist
        try:
            self._save_flag('show_file_navigator', not is_visible)
        except Exception:
            pass
    
    def _open_file_from_navigator(self, file_path):
        """Open file selected from file navigator"""
        try:
            if os.path.exists(file_path) and file_path.lower().endswith(('.xml', '.xsd', '.xsl', '.xslt')):
                self.open_file(file_path)
            else:
                self.status_label.setText("Selected file is not a valid XML file")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open file: {str(e)}")
    
    def _show_combine_dialog(self, initial_files=None):
        """Combine selected XML files by merging their root children into a new file, then open it.
        
        Behavior:
        - If all selected files have the same root tag, the combined document uses that tag and merges the children.
        - If root tags differ, a generic <Combined> root is created and all roots' children are appended under it.
        - Attributes from the first root are preserved when roots share the same tag.
        """
        try:
            files = initial_files or []
            # Filter to valid XML files
            xml_files = [f for f in files if os.path.isfile(f) and f.lower().endswith('.xml')]
            if len(xml_files) < 2:
                QMessageBox.information(self, "Selection", "Select at least two XML files to combine.")
                return
            
            import xml.etree.ElementTree as ET
            from copy import deepcopy
            
            # Parse roots from each selected file
            roots = []
            for path in xml_files:
                with open(path, 'r', encoding='utf-8', errors='ignore') as fp:
                    content = fp.read()
                root = ET.fromstring(content)  # Parse content into an Element
                roots.append(root)
            
            # Decide the combined root strategy
            tags = {r.tag for r in roots}
            if len(tags) == 1:
                # Same root tag across all files: preserve tag and attributes from the first root
                combined_root = ET.Element(next(iter(tags)))
                try:
                    combined_root.attrib.update(roots[0].attrib)
                except Exception:
                    pass
            else:
                # Different root tags: use a generic container
                combined_root = ET.Element('Combined')
            
            # Merge children from each root element
            for r in roots:
                for child in list(r):  # Iterate direct children
                    # Use deepcopy to preserve original child trees and avoid reparenting issues
                    combined_root.append(deepcopy(child))
            
            # Build output path next to the first selected file
            base_dir = os.path.dirname(xml_files[0])
            from datetime import datetime
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            out_path = os.path.join(base_dir, f'combined_{ts}.xml')
            
            # Serialize and format the combined XML
            try:
                service = XmlService()
                raw_str = ET.tostring(combined_root, encoding='utf-8')
                formatted = service.format_xml(raw_str.decode('utf-8'))
                with open(out_path, 'w', encoding='utf-8') as out:
                    out.write(formatted)
            except Exception:
                # Fallback: write without pretty formatting
                ET.ElementTree(combined_root).write(out_path, encoding='utf-8', xml_declaration=True)
            
            # Open the newly created file in the editor
            self.open_file(out_path)
            if hasattr(self, 'status_label') and self.status_label:
                self.status_label.setText(f"Combined {len(xml_files)} files into {os.path.basename(out_path)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to combine files: {str(e)}")


def main():
    """Main function"""
    app = QApplication(sys.argv)
    app.setApplicationName("Visual XML Editor")
    app.setApplicationVersion("1.0.0")
    
    # Set application style
    app.setStyle("Fusion")
    
    # Handle command line arguments
    file_path = None
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        # Convert relative path to absolute path
        if not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)
    
    window = MainWindow(file_path)
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
    def paintEvent(self, event):
        # Default paint
        super().paintEvent(event)
        # Overlay painting for bookmark markers at the right border
        try:
            mw = self.window()
            if not hasattr(mw, 'bookmarks') or not mw.bookmarks:
                return
            vp = self.viewport()
            w = vp.width()
            x = w - 8  # marker x position from right edge
            painter = QPainter(vp)
            color = QColor(255, 200, 120, 180)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(color)
            for line in mw.bookmarks.keys():
                try:
                    block = self.document().findBlockByNumber(line - 1)
                    if not block.isValid():
                        continue
                    cursor = QTextCursor(block)
                    rect = self.cursorRect(cursor)
                    y = rect.y()
                    # Draw a small rounded marker
                    painter.drawRoundedRect(x, y + 1, 6, 3, 1.5, 1.5)
                except Exception:
                    continue
            painter.end()
        except Exception:
            pass