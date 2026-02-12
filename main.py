#!/usr/bin/env python3
"""
Lotus Xml Editor - Python Version
A modern XML editor with tree view, syntax highlighting, and validation
"""

import sys
import os
import random
import subprocess
from version import __version__, __build_date__, __app_name__
from PyQt6.QtWidgets import (QApplication, QMainWindow, QSplitter, QTreeWidget, 
                             QTreeWidgetItem, QStatusBar, QMenuBar, 
                             QToolBar, QVBoxLayout, QHBoxLayout, QWidget, 
                             QTabWidget, QListWidget, QListWidgetItem, QPushButton, QLabel, 
                             QFileDialog, QMessageBox, QLineEdit, QCheckBox, QComboBox, QToolButton,
                             QDialog, QDialogButtonBox, QSpinBox, QFrame,
                             QHeaderView, QTreeWidgetItemIterator, QMenu, QDockWidget, QProgressBar, QInputDialog, QStyle)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QDateTime, QSettings, QThread, QByteArray, QMimeData, QUrl
from PyQt6.QtGui import QAction, QIcon, QFont, QColor, QPainter, QShortcut, QKeySequence
from PyQt6.Qsci import QsciScintilla, QsciLexerXML
import re
import zipfile
import json
import base64
import tempfile
import shutil

from xml_service import XmlService
from models import XmlFileModel, XmlTreeNode, XmlValidationResult
from syntax import LanguageDefinition, LanguageRegistry, LanguageProfileCompiler, load_udl_xml
from split_dialog import XmlSplitConfigDialog
from file_navigator import FileNavigatorWidget
from combine_dialog import CombineDialog
from settings_dialog import SettingsDialog
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
from splash_screen import LoadingSplashScreen
from fragment_dialog import FragmentEditorDialog
from metro_navigator import MetroNavigatorWindow
from about_dialog import AboutDialog
from favorites_widget import FavoritesWidget
from object_form import ObjectNodeForm


class XmlTreeWidget(QTreeWidget):
    """Custom tree widget for displaying XML structure"""
    node_selected = pyqtSignal(object)
    delete_node_requested = pyqtSignal(object)
    hide_node_requested = pyqtSignal(object)
    tree_built = pyqtSignal()
    
    def __init__(self, status_label=None):
        super().__init__()
        self.status_label = status_label
        self.hide_leaves_enabled = True  # default: hide leaf nodes
        self.use_friendly_labels = True  # default: show friendly labels
        self.setHeaderLabels(["Element", "Value"])
        self.setAlternatingRowColors(True)
        self.setDragEnabled(True)
        self.itemClicked.connect(self._on_item_clicked)
        
        # Context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        # Quick Win #2: Enable uniform row heights for faster rendering (20-40% faster)
        self.setUniformRowHeights(True)
        
        # Level collapse buttons
        self.level_buttons = []
        self.max_depth = 0
        self.max_load_depth = 2  # Default load depth
        self.max_level_buttons = 5  # Default: show max 5 level buttons

        # Level header mount container reference (assigned by MainWindow)
        self.header_container = None
        self.current_header_widget = None
        
        # Search filter
        self.search_filter_text = ""
        self.search_matches = []  # Store matching items
        
        # Enable column stretching
        self.setRootIsDecorated(True)
        self.setAllColumnsShowFocus(True)
        self.header().setStretchLastSection(False)
        self.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        # Shortcuts
        self.expand_2_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Right"), self)
        self.expand_2_shortcut.activated.connect(self._expand_selected_2_levels)
        
        # Default: hide value column when leaves are hidden
        try:
            self.setColumnHidden(1, self.hide_leaves_enabled)
            self._update_header_resize_modes()
        except Exception:
            pass
            
        # Connect expansion signal for lazy loading
        try:
            self.itemExpanded.connect(self._on_item_expanded)
        except Exception:
            pass

    def mimeData(self, items):
        """Create mime data for dragged items"""
        mime_data = QMimeData()
        
        # We only support dragging one item at a time for now
        if not items:
            return mime_data
            
        item = items[0]
        if not hasattr(item, 'xml_node'):
            return mime_data
            
        node = item.xml_node
        
        # Create a serializable dictionary
        data = {
            'tag': getattr(node, 'tag', ''),
            'name': getattr(node, 'name', ''),
            'value': getattr(node, 'value', ''),
            'attributes': getattr(node, 'attributes', {}),
            'path': getattr(node, 'path', ''),
            'line_number': getattr(node, 'line_number', 0)
        }
        
        mime_data.setData('application/x-lotus-xml-node', json.dumps(data).encode('utf-8'))
        return mime_data

    def _open_object_view(self, item):
        """Open object viewer for the selected item"""
        if not hasattr(item, 'xml_node'):
            return
        
        try:
            form = ObjectNodeForm(item.xml_node, self)
            form.jump_to_source_requested.connect(lambda node: self._on_jump_to_source(node, form))
            form.show()
            # Keep reference to prevent garbage collection
            if not hasattr(self, '_object_forms'):
                self._object_forms = []
            self._object_forms.append(form)
            # Cleanup when closed
            form.finished.connect(lambda: self._object_forms.remove(form) if form in self._object_forms else None)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to open object view: {str(e)}")

    def select_node(self, target_node):
        """Select a specific node in the tree, expanding path as needed"""
        if not target_node or not getattr(target_node, 'path', None):
            return

        # Path format: /Root[1]/Child[1]/GrandChild[2]
        # Remove leading slash and split
        path_parts = target_node.path.strip('/').split('/')
        if not path_parts:
            return

        # Start search from top level items
        current_item = None
        
        # 1. Find Root
        root_part = path_parts[0]
        root_tag, root_idx = self._parse_path_part(root_part)
        
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            if self._match_node(item, root_tag, root_idx, f"/{root_part}"):
                current_item = item
                break
        
        if not current_item:
            return

        # 2. Traverse down
        current_path = f"/{root_part}"
        
        for part in path_parts[1:]:
            # Ensure current item is expanded to load children
            if not current_item.isExpanded():
                current_item.setExpanded(True)
                QApplication.processEvents()
            
            tag, idx = self._parse_path_part(part)
            current_path += f"/{part}"
            
            found_child = False
            
            # Loop to handle dynamic loading (loaders)
            max_loader_loops = 100 # Safety break
            loop_count = 0
            
            while loop_count < max_loader_loops:
                loop_count += 1
                
                # Scan current children
                for i in range(current_item.childCount()):
                    child = current_item.child(i)
                    
                    # Skip placeholders/loaders for matching
                    if getattr(child, 'is_loader', False) or getattr(child, 'is_loader_node', False):
                        continue
                        
                    if self._match_node(child, tag, idx, current_path):
                        current_item = child
                        found_child = True
                        break
                
                if found_child:
                    break
                    
                # If not found, check for loader
                loader = None
                for i in range(current_item.childCount()):
                    child = current_item.child(i)
                    if getattr(child, 'is_loader', False) or getattr(child, 'is_loader_node', False):
                        loader = child
                        break
                
                if loader:
                    loader.setExpanded(True)
                    QApplication.processEvents()
                else:
                    # No loader and not found -> path doesn't exist
                    return

        # 3. Select final item
        if current_item:
            self.setCurrentItem(current_item)
            self.scrollToItem(current_item)
            self._on_item_clicked(current_item, 0)

    def _parse_path_part(self, part):
        """Parse 'Tag[Index]' into (Tag, Index)"""
        if '[' in part and part.endswith(']'):
            tag = part[:part.rfind('[')]
            idx_str = part[part.rfind('[')+1:-1]
            try:
                return tag, int(idx_str)
            except:
                return tag, 1
        return part, 1

    def _match_node(self, item, tag, idx, path):
        """Check if item matches tag, index and path"""
        node = getattr(item, 'xml_node', None)
        if not node:
            return False
        
        # Check path exact match (most reliable)
        if hasattr(node, 'path') and node.path == path:
            return True
            
        return False

    def _on_jump_to_source(self, node, form):
        """Handle jump to source request from object form"""
        try:
            # 1. Select in Tree
            # We need to find the item in the tree that corresponds to this node
            # This is tricky because the tree might be lazy loaded.
            # But we can try to find by matching node object if it exists
            
            # Simple approach: Emit signal to MainWindow to handle selection/scrolling
            # But XmlTreeWidget is a widget, not the MainWindow.
            # We can access MainWindow via window()
            
            main_window = self.window()
            if hasattr(main_window, 'select_node_and_scroll'):
                main_window.select_node_and_scroll(node)
            elif hasattr(main_window, 'xml_editor') and node.line_number > 0:
                # Scroll editor directly
                main_window.xml_editor.highlight_line(node.line_number)
                # Ideally also select in tree
                
            # Focus the main window
            main_window.activateWindow()
            
        except Exception as e:
            print(f"Jump to source failed: {e}")

    def _show_context_menu(self, position):
        """Show context menu for tree items"""
        item = self.itemAt(position)
        if not item:
            return
            
        menu = QMenu(self)
        
        # Object View Action
        view_object_action = QAction("Open Object View", self)
        view_object_action.triggered.connect(lambda: self._open_object_view(item))
        menu.addAction(view_object_action)
        menu.addSeparator()
        
        # Expand actions
        expand_action = QAction("Expand All Children", self)
        expand_action.triggered.connect(lambda: self._expand_recursive(item))
        menu.addAction(expand_action)
        
        expand_2_action = QAction("Expand Next 2 Levels", self)
        expand_2_action.triggered.connect(lambda: self._expand_levels(item, 2))
        menu.addAction(expand_2_action)
        
        collapse_action = QAction("Collapse All Children", self)
        collapse_action.triggered.connect(lambda: self._collapse_recursive(item))
        menu.addAction(collapse_action)
        
        menu.addSeparator()
        
        # Copy actions
        copy_tag_action = QAction("Copy Tag Name", self)
        copy_tag_action.triggered.connect(lambda: QApplication.clipboard().setText(item.text(0)))
        menu.addAction(copy_tag_action)
        
        if item.text(1):
            copy_val_action = QAction("Copy Value", self)
            copy_val_action.triggered.connect(lambda: QApplication.clipboard().setText(item.text(1)))
            menu.addAction(copy_val_action)
        
        menu.addSeparator()
        
        # Delete/Hide actions
        delete_action = QAction("Delete XML Block", self)
        delete_action.triggered.connect(lambda: self.delete_node_requested.emit(item.xml_node))
        menu.addAction(delete_action)
        
        hide_action = QAction("Hide XML Block", self)
        hide_action.triggered.connect(lambda: self.hide_node_requested.emit(item.xml_node))
        menu.addAction(hide_action)
            
        menu.exec(self.mapToGlobal(position))
        
    def _expand_recursive(self, item):
        """Recursively expand an item and all its children"""
        self.expandItem(item)
        for i in range(item.childCount()):
            self._expand_recursive(item.child(i))
            
    def _expand_selected_2_levels(self):
        """Expand selected items by 2 levels"""
        for item in self.selectedItems():
            self._expand_levels(item, 2)

    def mouseDoubleClickEvent(self, event):
        """Handle double click to force deep expansion if collapsed"""
        item = self.itemAt(event.pos())
        if item and not item.isExpanded():
            # Custom expansion (2 levels)
            self._expand_levels(item, 2)
            # Prevent default behavior which might conflict or be redundant
            return
            
        # Otherwise default behavior (e.g. collapse if expanded)
        super().mouseDoubleClickEvent(event)

    def _expand_levels(self, item, levels):
        """Expand item to specific depth"""
        if levels <= 0:
            return
        self.expandItem(item)
        for i in range(item.childCount()):
            self._expand_levels(item.child(i), levels - 1)
            
    def _collapse_recursive(self, item):
        """Recursively collapse an item and all its children"""
        for i in range(item.childCount()):
            self._collapse_recursive(item.child(i))
        self.collapseItem(item)

    def _finish_lazy_load(self, root, xml_content, progress_dialog):
        if root is None:
            error_item = QTreeWidgetItem()
            error_item.setText(0, "Tree building failed")
            error_item.setText(1, "File content is available in the editor")
            error_item.setForeground(0, QColor("red"))
            self.addTopLevelItem(error_item)
            if self.status_label:
                self.status_label.setText("Tree building failed - content available in editor")
            if progress_dialog:
                main_window = self.window()
                if hasattr(main_window, 'status_bar'):
                    main_window.status_bar.removeWidget(progress_dialog)
                progress_dialog.deleteLater()
            self.setUpdatesEnabled(True)
            return
        lines = xml_content.split('\n')
        line_index = None
        self._xml_root = root
        self._xml_lines = lines
        self._xml_line_index = line_index
        root_node = self._xml_service._element_to_shallow_node_with_lines(root, lines, "", 0, 1, line_index)
        item = QTreeWidgetItem()
        item.setText(0, self.compute_display_name(root_node, root))
        item.setText(1, self._truncate_value(root_node.value) if root_node.value else "")
        item.xml_node = root_node
        item.xml_element = root
        item.lazy_loaded = False
        self.addTopLevelItem(item)
        if len(root):
            placeholder = QTreeWidgetItem()
            placeholder.setText(0, "...")
            placeholder.is_placeholder = True
            item.addChild(placeholder)
        
        # Signal is already connected in __init__
        # Expand to selected depth
        self.expand_to_level(self.max_load_depth)
                    
        self.apply_hide_leaves_filter()
        if self.status_label:
            self.status_label.setText("Lazy tree ready")
        if progress_dialog:
            main_window = self.window()
            if hasattr(main_window, 'status_bar'):
                main_window.status_bar.removeWidget(progress_dialog)
            progress_dialog.deleteLater()
        self.setUpdatesEnabled(True)
        
        # Signal that tree is ready
        self.tree_built.emit()

        self._xml_root = None
        self._xml_lines = []
        self._xml_line_index = None
        try:
            self._xml_service = XmlService()
        except Exception:
            self._xml_service = None

    def compute_display_name(self, xml_node, xml_element=None):
        """Compute label for a node based on current mode."""
        if not xml_node:
            return ""
            
        # 1. Calculate attributes string (common)
        attr = getattr(xml_node, 'attributes', {}) or {}
        attr_string = " ".join([f'{k}="{v}"' for k, v in attr.items()])
        
        # 2. Extract friendly name
        # Optimization: Skip extraction entirely if friendly labels are disabled
        # This restores fast loading for large files when the setting is OFF
        if not self.use_friendly_labels:
             return f"{xml_node.tag} [{attr_string}]" if attr_string else f"{xml_node.tag}"
        
        preferred_name = None
        fallback_name = None
        found = False
        
        # Try XmlTreeNode children first (populated nodes)
        try:
            children = getattr(xml_node, 'children', []) or []
            if children:
                # Limit scan to first 6 children to prevent freeze on massive nodes
                for child in children[:6]:
                    tag = getattr(child, 'tag', '')
                    if not tag:
                        continue
                    tag_lower = tag.lower()

                    if tag_lower in ("наименование", "имя", "name") and getattr(child, 'value', None):
                        text = child.value.strip()
                        if text:
                            preferred_name = text
                            found = True
                            break
                    elif tag_lower == "код" and getattr(child, 'value', None):
                        text = child.value.strip()
                        if text:
                            fallback_name = text
        except Exception:
            pass

        # If not found and xml_element provided, try raw element children (shallow nodes)
        if not found and xml_element is not None:
            try:
                # Limit iteration count for raw element children as well
                count = 0
                for child in xml_element:
                    count += 1
                    if count > 50: # Optimization: Stop after checking 50 children
                        break
                        
                    tag = getattr(child, 'tag', '')
                    # Handle namespaces if present in tag (e.g. {ns}tag)
                    if isinstance(tag, str) and '}' in tag:
                        tag = tag.split('}', 1)[1]
                        
                    if tag:
                        tag_lower = tag.lower()
                        if tag_lower in ("наименование", "имя", "name"):
                            text = getattr(child, 'text', '')
                            if text and text.strip():
                                preferred_name = text.strip()
                                found = True
                                break
                        elif tag_lower == "код" and not fallback_name:
                            text = getattr(child, 'text', '')
                            if text and text.strip():
                                fallback_name = text.strip()
            except Exception:
                pass
        
        if not found and fallback_name:
            preferred_name = fallback_name

        # 3. Format based on mode
        # Friendly mode: "Friendly (Tag [attrs])"
        if preferred_name:
            return f"{preferred_name} ({xml_node.tag} [{attr_string}])" if attr_string else f"{preferred_name} ({xml_node.tag})"
            
        # Fallback for Friendly mode (no friendly name found)
        return f"{xml_node.tag} [{attr_string}]" if attr_string else f"{xml_node.tag}"

    def refresh_labels(self):
        """Refresh all labels according to mode without rebuilding structure."""
        try:
            iterator = QTreeWidgetItemIterator(self)
            while iterator.value():
                item = iterator.value()
                if item and hasattr(item, 'xml_node') and item.xml_node:
                    item.setText(0, self.compute_display_name(item.xml_node, getattr(item, 'xml_element', None)))
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
        
        # Add Load Depth SpinBox
        depth_label = QLabel("Depth:")
        depth_label.setStyleSheet("font-size: 9px;")
        header_layout.addWidget(depth_label)
        
        depth_spin = QSpinBox()
        depth_spin.setRange(1, 10)
        depth_spin.setValue(self.max_load_depth)
        depth_spin.setFixedSize(35, 20)
        depth_spin.setStyleSheet("font-size: 9px; padding: 0px;")
        depth_spin.setToolTip("Select how many levels to load into tree")
        depth_spin.valueChanged.connect(self.apply_load_depth)
        header_layout.addWidget(depth_spin)
        self.depth_spin = depth_spin
        
        # Add level buttons (limited by max_level_buttons setting)
        level_label = QLabel("Lvl:")  # Shortened label
        level_label.setStyleSheet("font-size: 9px;")
        header_layout.addWidget(level_label)
        num_buttons = min(max_depth, self.max_level_buttons)
        for level in range(1, num_buttons + 1):
            btn = QPushButton(str(level))
            btn.setFixedSize(22, 20)  # Smaller buttons
            btn.setStyleSheet("font-size: 9px; padding: 1px; background-color: #505050;")
            btn.clicked.connect(lambda checked, l=level: self._handle_level_button(l))
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
    
    def apply_load_depth(self, depth):
        """Apply the selected load depth (expand/collapse)"""
        self.max_load_depth = depth
        self.setUpdatesEnabled(False)
        self.expand_to_level(depth)
        self.setUpdatesEnabled(True)

    def _handle_level_button(self, level):
        """Handle level button click"""
        # If requested level is deeper than current load depth, update load depth first.
        # This ensures nodes are expanded/loaded to the requested level.
        if hasattr(self, 'depth_spin') and self.depth_spin:
            current_depth = self.depth_spin.value()
            if level > current_depth:
                # Update spinner without triggering its signal to avoid double work/flicker
                self.depth_spin.blockSignals(True)
                self.depth_spin.setValue(level)
                self.depth_spin.blockSignals(False)
                
                # Manually update internal state
                self.max_load_depth = level
                
                # Force tree rebuild from current editor content
                # This ensures that even if lazy nodes are present, they are properly re-evaluated
                # and expanded to the new depth.
                try:
                    main_window = self.window()
                    if hasattr(main_window, 'xml_editor'):
                        content = main_window.xml_editor.get_content()
                        # Use populate_tree to rebuild. 
                        # Passing show_progress=True to show user something is happening.
                        self.populate_tree(content, show_progress=True)
                except Exception as e:
                    print(f"Error forcing rebuild: {e}")
                
                return

        # Otherwise standard collapse behavior
        self.collapse_level(level)

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
    
    def populate_tree(self, xml_content: str, show_progress=True, file_path: str = None, force_async=False):
        """Populate tree with XML structure"""
        self.clear()
        service = getattr(self, '_xml_service', None) or XmlService()
        self._xml_service = service  # Ensure service is available for async callback
        
        # Quick Win #1: Disable visual updates during tree building (30-50% faster)
        self.setUpdatesEnabled(False)
        
        # Try to load from cache first if file path is available
        if file_path and not force_async:
            try:
                cached_root = service.load_tree_cache(file_path)
                if cached_root:
                    self._add_tree_items_lazy_from_node(cached_root)
                    
                    # Create header with level buttons
                    max_depth = self._calculate_max_depth(cached_root)
                    if max_depth > 0:
                        self.create_level_buttons(max_depth)
                    
                    # Expand to selected depth
                    self.expand_to_level(self.max_load_depth)
                    
                    # Apply leaf hiding
                    self.apply_hide_leaves_filter()
                    self.setUpdatesEnabled(True)
                    if self.status_label:
                        self.status_label.setText("Loaded from cache")
                    # Signal tree built
                    self.tree_built.emit()
                    return
            except Exception as e:
                print(f"Cache load failed: {e}")

        # Progress tracking
        progress_dialog = None
        
        # Optimization: If file_path is provided and lxml is available, use direct loading (fast)
        # Bypassing the thread worker which might not handle file paths/encodings as well
        use_fast_path = False
        if file_path and not force_async:
             try:
                 from xml_service import LXML_AVAILABLE
                 if LXML_AVAILABLE:
                     use_fast_path = True
             except ImportError:
                 pass

        if (len(xml_content) > 1024 * 1024 and not use_fast_path) or force_async:
            progress_dialog = None
            if show_progress:
                progress_dialog = QProgressBar()
                progress_dialog.setRange(0, 0)
                progress_dialog.setTextVisible(True)
                progress_dialog.setFormat("Parsing XML in background...")
                main_window = self.window()
                if hasattr(main_window, 'status_bar'):
                    main_window.status_bar.addWidget(progress_dialog)
                    QApplication.processEvents()
            if self.status_label:
                self.status_label.setText("Parsing lazy tree in background...")
                QApplication.processEvents()
            worker = XmlParseWorker(xml_content, service)
            worker.parsed.connect(lambda root: self._finish_lazy_load(root, xml_content, progress_dialog))
            worker.start()
            # Keep reference to worker to prevent garbage collection
            self._parse_worker = worker
        else:
            # Normal processing for smaller files (or fast path for large files)
            root_node = service.build_xml_tree(xml_content, file_path=file_path)
            
            if root_node:
                # Save to cache if file path is available
                if file_path:
                    service.save_tree_cache(file_path, root_node)

                # Always use lazy population for better performance and consistency
                self._add_tree_items_lazy_from_node(root_node)
                
                # Calculate max depth and create level buttons
                max_depth = self._calculate_max_depth(root_node)
                if max_depth > 0:
                    self.create_level_buttons(max_depth)
                
                # Expand to selected depth instead of ExpandAll
                self.expand_to_level(self.max_load_depth)

                # Apply leaf hiding after population
                self.apply_hide_leaves_filter()
                # Re-enable updates after normal file processing
                self.setUpdatesEnabled(True)
                # Signal tree built
                self.tree_built.emit()

    def _on_item_expanded(self, item):
        try:
            # Handle "Load more" loader expansion for node-based lazy loading
            if getattr(item, 'is_loader_node', False):
                parent_item = item.parent()
                if parent_item is None:
                    return
                
                children_list = getattr(item, 'children_list', [])
                offset = getattr(item, 'loader_offset', 0)
                
                try:
                    parent_item.removeChild(item)
                except Exception:
                    pass
                
                self._expand_children_chunk_from_node(parent_item, children_list, offset)
                return

            # Handle lazy expansion for pre-built XmlTreeNode structure (fast path)
            if getattr(item, 'lazy_loaded_from_node', None) is False:
                node = getattr(item, 'xml_node', None)
                if node:
                    # Remove placeholder
                    if item.childCount() > 0 and getattr(item.child(0), 'is_placeholder', False):
                        item.removeChild(item.child(0))
                    
                    self._expand_children_chunk_from_node(item, node.children, 0)
                    item.lazy_loaded_from_node = True
                return

            # Handle "Load more" loader expansion for element-based lazy loading
            if getattr(item, 'is_loader', False):
                parent_item = item.parent()
                if parent_item is None:
                    return
                elem = getattr(parent_item, 'xml_element', None)
                node = getattr(parent_item, 'xml_node', None)
                if elem is None or node is None:
                    return
                offset = getattr(item, 'loader_offset', 0)
                try:
                    parent_item.removeChild(item)
                except Exception:
                    pass
                self._expand_children_chunk(parent_item, elem, node, offset)
                return

            if getattr(item, 'lazy_loaded', False):
                return
            elem = getattr(item, 'xml_element', None)
            node = getattr(item, 'xml_node', None)
            if elem is None or node is None:
                return
            # Remove simple placeholder if present
            while item.childCount() > 0:
                c = item.child(0)
                try:
                    if getattr(c, 'is_placeholder', False):
                        item.removeChild(c)
                    else:
                        break
                except Exception:
                    break
            # Expand first chunk
            self._expand_children_chunk(item, elem, node, getattr(item, 'load_offset', 0))
        except Exception:
            pass

    def _expand_children_chunk(self, parent_item, elem, node, offset=0, max_children=500):
        try:
            tag_counts = {}
            children = list(elem)
            end = min(offset + max_children, len(children))
            processed = 0
            for i in range(offset, end):
                child = children[i]
                cnt = tag_counts.get(child.tag, 0) + 1
                tag_counts[child.tag] = cnt
                child_node = self._xml_service._element_to_shallow_node_with_lines(child, self._xml_lines, node.path, node.line_number, cnt, self._xml_line_index)
                it = QTreeWidgetItem()
                it.setText(0, self.compute_display_name(child_node, child))
                it.setText(1, self._truncate_value(child_node.value) if child_node.value else "")
                it.xml_node = child_node
                it.xml_element = child
                it.lazy_loaded = False
                parent_item.addChild(it)
                if len(child):
                    ph = QTreeWidgetItem()
                    ph.setText(0, "...")
                    ph.is_placeholder = True
                    it.addChild(ph)
                processed += 1
                if processed %6 == 0:
                    QApplication.processEvents()
            # Add loader if more children remain
            if end < len(children):
                loader = QTreeWidgetItem()
                loader.setText(0, f"Load more... ({len(children) - end} remaining)")
                loader.is_loader = True
                loader.loader_offset = end
                parent_item.addChild(loader)
            else:
                parent_item.lazy_loaded = True
            parent_item.load_offset = end
        except Exception:
            pass
    
    def _add_tree_items_lazy_from_node(self, root_node):
        """Add top level item and setup lazy loading from existing XmlTreeNode structure"""
        item = QTreeWidgetItem()
        item.setText(0, self.compute_display_name(root_node))
        item.setText(1, self._truncate_value(root_node.value) if root_node.value else "")
        item.xml_node = root_node
        item.lazy_loaded_from_node = False 
        
        self.addTopLevelItem(item)
        
        if root_node.children:
            placeholder = QTreeWidgetItem()
            placeholder.setText(0, "...")
            placeholder.is_placeholder = True
            item.addChild(placeholder)
        
        item.setExpanded(True) # Expand root
        self.setUpdatesEnabled(True)

    def _expand_children_chunk_from_node(self, parent_item, children_list, offset=0, max_children=100):
        """Expand children from XmlTreeNode list in chunks"""
        try:
            end = min(offset + max_children, len(children_list))
            
            for i in range(offset, end):
                child_node = children_list[i]
                child_item = QTreeWidgetItem()
                child_item.setText(0, self.compute_display_name(child_node))
                child_item.setText(1, self._truncate_value(child_node.value) if child_node.value else "")
                child_item.xml_node = child_node
                child_item.lazy_loaded_from_node = False
                
                parent_item.addChild(child_item)
                
                if child_node.children:
                    ph = QTreeWidgetItem()
                    ph.setText(0, "...")
                    ph.is_placeholder = True
                    child_item.addChild(ph)
            
            if end < len(children_list):
                loader = QTreeWidgetItem()
                loader.setText(0, f"Load more... ({len(children_list) - end} remaining)")
                loader.is_loader_node = True # Distinguish from other loader
                loader.loader_offset = end
                loader.children_list = children_list # Store reference to list
                parent_item.addChild(loader)
        except Exception as e:
            print(f"Error expanding children chunk: {e}")

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
    
    def _add_tree_items_large(self, parent_item, xml_node, parent_node=None, max_children=50):
        """Add tree items for large files with performance optimizations"""
        # Use iterative approach with batching to avoid deep recursion and allow UI updates
        stack = [(parent_item, xml_node, parent_node, 0)]  # (parent, node, parent_node, depth)
        items_processed = 0
        batch_size = 25  # Process 25 items before allowing UI update (reduced for better responsiveness)
        max_depth = 2  # Only expand first 2 levels for large files (reduced from 3)
        max_items = 1000  # Maximum total items to process (safety limit)
        
        while stack and items_processed < max_items:
            current_parent_item, current_xml_node, current_parent_node, depth = stack.pop()
            
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
            
            # For large files, limit the number of children processed initially
            # Also limit depth to avoid excessive tree size
            if depth < max_depth:
                children_to_process = current_xml_node.children[:max_children]
                
                # Add children to stack in reverse order for correct processing
                for child in reversed(children_to_process):
                    stack.append((item, child, current_xml_node, depth + 1))
                
                # Add placeholder if there are more children
                if len(current_xml_node.children) > max_children:
                    placeholder = QTreeWidgetItem()
                    placeholder.setText(0, f"... ({len(current_xml_node.children) - max_children} more items)")
                    placeholder.setForeground(0, QColor("gray"))
                    item.addChild(placeholder)
            
            # Periodically allow UI updates
            items_processed += 1
            if items_processed % batch_size == 0:
                QApplication.processEvents()
        
        # If we hit the max items limit, add a warning
        if items_processed >= max_items and stack:
            warning_item = QTreeWidgetItem()
            warning_item.setText(0, f"Tree truncated at {max_items} items for performance")
            warning_item.setText(1, "Use editor to view full content")
            warning_item.setForeground(0, QColor("orange"))
            self.addTopLevelItem(warning_item)
    
    def keyPressEvent(self, event):
        """Handle key press events for tree view"""
        # Check for F3 (Find Next)
        if event.key() == Qt.Key.Key_F3 and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            self.window().find_next()
            event.accept()
            return
        # Check for Shift+F3 (Find Previous)
        if event.key() == Qt.Key.Key_F3 and event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
            self.window().find_previous()
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

        # Ctrl+Delete: Delete XML Block (Model change)
        if event.key() == Qt.Key.Key_Delete and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            current = self.currentItem()
            if current:
                 self.delete_node_requested.emit(current.xml_node)
            event.accept()
            return
            
        # Ctrl+/: Hide XML Block (Comment out - Model change)
        if event.key() == Qt.Key.Key_Slash and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            current = self.currentItem()
            if current:
                 self.hide_node_requested.emit(current.xml_node)
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
    
    def set_search_filter(self, search_text: str):
        """Filter tree items by search text"""
        self.search_filter_text = search_text.lower().strip()
        self.search_matches.clear()
        
        if not self.search_filter_text:
            # Clear filter - show all items
            self._show_all_items()
            if self.status_label:
                self.status_label.setText("Search cleared")
            return
        
        # Find all matching items
        iterator = QTreeWidgetItemIterator(self)
        while iterator.value():
            item = iterator.value()
            if item and self._item_matches_search(item):
                self.search_matches.append(item)
            iterator += 1
        
        # Apply filter visibility
        self._apply_search_filter()
        
        # Update status
        if self.status_label:
            self.status_label.setText(f"Found {len(self.search_matches)} matches")
    
    def _item_matches_search(self, item) -> bool:
        """Check if item matches search text"""
        if not self.search_filter_text:
            return False
        
        # Check element name
        element_text = item.text(0).lower()
        if self.search_filter_text in element_text:
            return True
        
        # Check value
        value_text = item.text(1).lower()
        if self.search_filter_text in value_text:
            return True
        
        # Check xml_node attributes if available
        if hasattr(item, 'xml_node') and item.xml_node:
            node = item.xml_node
            # Check tag
            if hasattr(node, 'tag') and self.search_filter_text in node.tag.lower():
                return True
            # Check attributes
            if hasattr(node, 'attributes') and node.attributes:
                for key, value in node.attributes.items():
                    if self.search_filter_text in key.lower() or self.search_filter_text in str(value).lower():
                        return True
        
        return False
    
    def _apply_search_filter(self):
        """Apply search filter visibility to all items"""
        if not self.search_filter_text:
            return
        
        # First hide all items
        iterator = QTreeWidgetItemIterator(self)
        while iterator.value():
            item = iterator.value()
            if item:
                item.setHidden(True)
            iterator += 1
        
        # Show matching items and their ancestors
        for match_item in self.search_matches:
            # Show the matching item
            match_item.setHidden(False)
            
            # Show all ancestors
            parent = match_item.parent()
            while parent:
                parent.setHidden(False)
                parent.setExpanded(True)  # Expand to show the match
                parent = parent.parent()
        
        self.viewport().update()
    
    def _show_all_items(self):
        """Show all items (clear search filter)"""
        iterator = QTreeWidgetItemIterator(self)
        while iterator.value():
            item = iterator.value()
            if item:
                # Respect hide_leaves filter
                is_leaf = item.childCount() == 0
                item.setHidden(self.hide_leaves_enabled and is_leaf)
            iterator += 1
        self.viewport().update()

    def navigate_node_down(self):
        """Navigate to the next node in the tree."""
        current = self.currentItem()
        if not current:
            # If no selection, select first item
            if self.topLevelItemCount() > 0:
                top = self.topLevelItem(0)
                if top:
                    self.setCurrentItem(top)
                    self.scrollToItem(top)
                    self._on_item_clicked(top, 0)
            return

        next_item = self.itemBelow(current)
        if next_item:
            self.setCurrentItem(next_item)
            self.scrollToItem(next_item)
            self._on_item_clicked(next_item, 0)

    def navigate_node_up(self):
        """Navigate to the previous node in the tree."""
        current = self.currentItem()
        if not current:
            return

        prev_item = self.itemAbove(current)
        if prev_item:
            self.setCurrentItem(prev_item)
            self.scrollToItem(prev_item)
            self._on_item_clicked(prev_item, 0)
    
class XmlParseWorker(QThread):
    parsed = pyqtSignal(object)

    def __init__(self, xml_content, service):
        super().__init__()
        self.xml_content = xml_content
        self.service = service

    def run(self):
        try:
            # Strip BOM if present
            if self.xml_content and self.xml_content.startswith('\ufeff'):
                self.xml_content = self.xml_content[1:]
                
            # Use build_xml_tree for lxml support instead of raw parse_xml
            # This ensures we get line numbers and robust parsing
            root_node = self.service.build_xml_tree(self.xml_content)
            
            # Extract the raw element from the node if successful
            root = None
            if root_node:
                # Re-parse to get raw element if needed, or modify build_xml_tree to return both
                # For now, we trust build_xml_tree to handle the parsing
                # But _finish_lazy_load expects a raw element or compatible object
                # Let's check if we can get the raw element
                
                # Actually, for lazy loading, we often need the raw element for further traversal
                # If build_xml_tree used lxml, we don't have the raw element easily available unless we re-parse
                # So let's try direct parsing first as the original code did, but with BOM handling
                
                # Revert to direct parse to match original logic, but keep BOM fix
                root = self.service.parse_xml(self.xml_content)
                
            self.parsed.emit(root)
        except Exception as e:
            print(f"Worker parse error: {e}")
            self.parsed.emit(None)


class AutoCloseWorker(QThread):
    """Worker thread for auto-closing tags"""
    finished = pyqtSignal(str, bool)

    def __init__(self, xml_content, service):
        super().__init__()
        self.xml_content = xml_content
        self.service = service

    def run(self):
        try:
            fixed_content = self.service.auto_close_tags(self.xml_content)
            modified = (fixed_content != self.xml_content)
            self.finished.emit(fixed_content, modified)
        except Exception:
            self.finished.emit(self.xml_content, False)


class ProgressPopup(QWidget):
    """Floating progress popup"""
    def __init__(self, text, parent=None):
        super().__init__(parent, Qt.WindowType.ToolTip)
        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        self.label = QLabel(text)
        self.label.setStyleSheet("color: white; font-weight: bold;")
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.setStyleSheet("background-color: #333; border: 1px solid #555; border-radius: 4px;")
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)


class XmlEditorWidget(QsciScintilla):
    """Custom text editor for XML with QScintilla"""
    content_changed = pyqtSignal()
    cursor_position_changed = pyqtSignal(int, int)
    fragment_editor_requested = pyqtSignal()
    definition_lookup_requested = pyqtSignal(str)
    modification_changed = pyqtSignal(bool)
    
    class LineNumberWidgetAdapter:
        def __init__(self, editor):
            self.editor = editor
            self.folding_enabled = True

        def isVisible(self):
            return self.editor.marginWidth(0) > 0

        def show(self):
            self.editor.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
            self.editor.setMarginWidth(0, "00000")

        def hide(self):
            self.editor.setMarginWidth(0, 0)
            
        def set_folding_enabled(self, enabled):
            self.folding_enabled = enabled
            
        def update(self, *args):
            pass 
            
        def calculate_width(self):
            return 0 
            
        def setGeometry(self, *args):
            pass


    def __init__(self):
        super().__init__()
        
        # Visibility options (Must be before lexer config)
        self.visibility_options = {
            'hide_symbols': False,
            'hide_tags': False,
            'hide_values': False
        }
        self.is_dark_theme = False
        
        
        # Font setup
        font_family = "Consolas"
        font_size = 11
        try:
            settings = QSettings("visxml.net", "LotusXmlEditor")
            font_family = settings.value("editor_font_family", "Consolas")
            font_size = int(settings.value("editor_font_size", 11))
        except Exception:
            pass
            
        font = QFont(font_family, font_size)
        self.setFont(font)
        self.setMarginsFont(font)
        
        # Lexer setup
        self._configure_lexer()
        
        # Encoding
        self.setUtf8(True)
        
        # Indicators
        self._init_indicators()
        
        # Drag and drop
        self.setAcceptDrops(True)
        
        # Flags
        self.enable_occurrence_highlighting = True
        
        # Bookmarks & File info
        self.bookmarks = {}
        self.numbered_bookmarks = {}
        self.file_path = None
        self.zip_source = None
        self._folded_ranges = []

        # Line Number Adapter
        self.line_number_widget = self.LineNumberWidgetAdapter(self)
        
        # Signals
        self.textChanged.connect(self.content_changed)
        self.modificationChanged.connect(self.modification_changed.emit)
        self.cursorPositionChanged.connect(self._on_cursor_changed)
        self.selectionChanged.connect(self.highlight_all_occurrences)
        
        # Initial Setup
        self.set_line_numbers_visible(False)
        self.set_code_folding_enabled(True)
        self.highlighter = None
        
        # Tab settings
        self.setIndentationsUseTabs(False)
        self.setTabWidth(4)
        self.setIndentationGuides(True)
        self.setAutoIndent(True)
        self.setWrapMode(QsciScintilla.WrapMode.WrapNone)

        # Occurrence highlighting
        self._occurrence_indicators = []
        
        # Visibility options
        self.visibility_options = {
            'hide_symbols': False,
            'hide_tags': False,
            'hide_values': False
        }
        self.is_dark_theme = False

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            # Handle Ctrl+Click for definition lookup
            pos = event.pos()
            # Convert visual position to scintilla position
            scint_pos = self.SendScintilla(QsciScintilla.SCI_POSITIONFROMPOINT, pos.x(), pos.y())
            
            if scint_pos != -1:
                line, index = self.lineIndexFromPosition(scint_pos)
                # Get line text
                text = self.text(line)
                if index < len(text):
                    # Check if inside quotes
                    self._check_definition_lookup(text, index)
        
        super().mousePressEvent(event)

    def _check_definition_lookup(self, text, index):
        """Check if cursor is inside a quoted string and if it matches a definition pattern"""
        try:
            # Find quotes around the index
            # Simple logic: search backwards for " and forwards for "
            # This is naive but often sufficient for simple XML attributes
            
            # Find opening quote before index
            start_quote = -1
            for i in range(index, -1, -1):
                if text[i] == '"':
                    start_quote = i
                    break
            
            if start_quote == -1:
                return

            # Find closing quote after index
            end_quote = -1
            for i in range(index, len(text)):
                if text[i] == '"':
                    end_quote = i
                    break
            
            if end_quote == -1:
                return
            
            # Ensure we are inside the quotes (not on them)
            if start_quote < index < end_quote:
                content = text[start_quote+1 : end_quote]
                # Check pattern
                if content.startswith("Запросы.") or content.startswith("Алгоритмы."):
                    self.definition_lookup_requested.emit(content)

        except Exception as e:
            print(f"Definition lookup check error: {e}")

    def get_cursor_char_position(self):
        """Get the character index of the cursor relative to the start of the document."""
        line, index = self.getCursorPosition()
        pos = 0
        # Sum lengths of previous lines
        # Note: text(i) returns the line content including newline
        for i in range(line):
            pos += len(self.text(i))
        pos += index
        return pos

    def navigate_to(self, line_one_based: int, column: int = 0, select_length: int = 0):
        """Navigate to a specific line and column, optionally selecting text."""
        if line_one_based <= 0:
            return
            
        line_idx = line_one_based - 1
        
        # Ensure line exists
        if line_idx >= self.lines():
            line_idx = self.lines() - 1
            
        # Move cursor
        self.setCursorPosition(line_idx, column)
        self.ensureLineVisible(line_idx)
        self.ensureCursorVisible()
        
        # Select if requested
        if select_length > 0:
            # We need to calculate end position
            # QScintilla selection is (line_from, index_from, line_to, index_to)
            # This is complicated if the selection spans lines.
            # Assuming single line selection for now as mostly used for search results
            self.setSelection(line_idx, column, line_idx, column + select_length)
            
        self.setFocus()

    def get_selected_text(self):
        """Get currently selected text."""
        return self.selectedText()

    def set_line_numbers_visible(self, visible: bool):
        if visible:
            self.line_number_widget.show()
        else:
            self.line_number_widget.hide()

    def set_code_folding_enabled(self, enabled: bool):
        self.line_number_widget.set_folding_enabled(enabled)
        if enabled:
            self.setMarginType(1, QsciScintilla.MarginType.SymbolMargin)
            self.setMarginWidth(1, 20)
            self.setFolding(QsciScintilla.FoldStyle.BoxedTreeFoldStyle)
        else:
            self.setMarginWidth(1, 0)
            self.setFolding(QsciScintilla.FoldStyle.NoFoldStyle)
            self.unfold_all()

    def _on_cursor_changed(self, line, index):
        self.cursor_position_changed.emit(line + 1, index + 1)

    def get_content(self) -> str:
        return self.text()
    
    def set_content(self, content: str):
        self.setText(content)


    def highlight_line(self, line_number: int):
        if line_number <= 0:
            return
        line_idx = line_number - 1
        self.setCursorPosition(line_idx, 0)
        self.ensureLineVisible(line_idx)
        self.setSelection(line_idx, 0, line_idx + 1, 0)

    def _configure_lexer(self):
        lexer = QsciLexerXML(self)
        lexer.setDefaultFont(self.font())
        self.setLexer(lexer)
        # Apply default light theme initially
        self.set_dark_theme(False)

    def set_dark_theme(self, dark_theme=True):
        """Apply dark or light theme colors to the lexer."""
        self.is_dark_theme = dark_theme
        self.update_colors()

    def set_visibility_options(self, hide_symbols=False, hide_tags=False, hide_values=False):
        """Set visibility options for syntax highlighting."""
        self.visibility_options = {
            'hide_symbols': hide_symbols,
            'hide_tags': hide_tags,
            'hide_values': hide_values
        }
        self.update_colors()

    def update_colors(self):
        """Update lexer colors based on theme and visibility options."""
        lexer = self.lexer()
        if not lexer:
            return

        dark_theme = self.is_dark_theme
        
        if dark_theme:
            # Dark Theme Colors
            default_color = QColor("#D4D4D4") # Light Grey
            background_color = QColor("#1e1e1e")
            
            tag_color = QColor("#569CD6") # Blue
            attr_color = QColor("#D4D4D4") # Light Grey
            value_color = QColor("#B5CEA8") # Light Green
            comment_color = QColor("#6A9955") # Green
            cdata_color = QColor("#D7BA7D") # Light yellow
            entity_color = QColor("#C586C0") # Pink
            
            # Set background
            self.setColor(default_color)
            self.setPaper(background_color)
            self.setMarginsBackgroundColor(QColor("#252526"))
            self.setMarginsForegroundColor(QColor("#858585"))
            self.setCaretForegroundColor(QColor("#ffffff"))
            
        else:
            # Light Theme Colors (Modern/VS Code style)
            default_color = QColor("#000000") # Black
            background_color = QColor("#ffffff") # White
            
            tag_color = QColor("#0000FF") # Blue (Keywords)
            attr_color = QColor("#A31515") # Dark Red (Attributes)
            value_color = QColor("#008000") # Green (Strings)
            comment_color = QColor("#008000") # Green
            cdata_color = QColor("#8B4513") # Brown
            entity_color = QColor("#FF00FF") # Magenta
            
            # Set background
            self.setColor(default_color)
            self.setPaper(background_color)
            self.setMarginsBackgroundColor(QColor("#f0f0f0"))
            self.setMarginsForegroundColor(QColor("#333333"))
            self.setCaretForegroundColor(QColor("#000000"))

        # Apply visibility overrides (hide by setting to background color)
        if self.visibility_options['hide_tags'] or self.visibility_options['hide_symbols']:
            tag_color = background_color
            
        if self.visibility_options['hide_values']:
            value_color = background_color

        # Lexer colors
        lexer.setColor(default_color, QsciLexerXML.Default)
        lexer.setColor(tag_color, QsciLexerXML.Tag)
        lexer.setColor(attr_color, QsciLexerXML.Attribute)
        lexer.setColor(value_color, QsciLexerXML.HTMLDoubleQuotedString)
        lexer.setColor(value_color, QsciLexerXML.HTMLSingleQuotedString)
        lexer.setColor(comment_color, QsciLexerXML.HTMLComment)
        lexer.setColor(cdata_color, QsciLexerXML.CDATA)
        lexer.setColor(entity_color, QsciLexerXML.Entity)
        
        if dark_theme:
            lexer.setColor(QColor("#569CD6"), QsciLexerXML.XMLStart) # Processing instruction
        else:
            lexer.setColor(QColor("#0000FF"), QsciLexerXML.XMLStart)

    def highlight_all_occurrences(self):
        """Highlights all occurrences of the currently selected text."""
        # Clear existing indicators
        self.clearIndicatorRange(0, 0, self.lines(), self.lineLength(self.lines()-1), 8)
        
        # Get selected text
        text = self.selectedText()
        print(f"DEBUG: highlight_all_occurrences selected text: '{text}'")
        if not text:
            return
            
        # Don't highlight if text is too short or too long
        if len(text) < 2 or len(text) > 100:
            return
            
        # Search and highlight
        search_bytes = text.encode('utf-8')
        
        for line_idx in range(self.lines()):
            line_text = self.text(line_idx)
            # Ensure we have bytes for searching to match QScintilla's internal byte offsets
            line_bytes = line_text.encode('utf-8')
            
            start_idx = 0
            while True:
                idx = line_bytes.find(search_bytes, start_idx)
                if idx == -1:
                    break
                
                # fillIndicatorRange uses byte offsets in UTF-8 mode
                print(f"DEBUG: Filling indicator at line {line_idx}, start {idx}, len {len(search_bytes)}")
                self.fillIndicatorRange(line_idx, idx, line_idx, idx + len(search_bytes), 8)
                
                start_idx = idx + len(search_bytes)

    def _init_indicators(self):
        # Indicator 8 for highlighting occurrences
        self.indicatorDefine(QsciScintilla.IndicatorStyle.StraightBoxIndicator, 8)
        self.setIndicatorForegroundColor(QColor("purple"), 8)
        self.setIndicatorDrawUnder(True, 8) # Draw under text


    def _is_fold_line(self, line):
        # SC_FOLDLEVELHEADERFLAG = 0x2000
        level = self.SendScintilla(QsciScintilla.SCI_GETFOLDLEVEL, line)
        return bool(level & 0x2000)

    def _is_fold_expanded(self, line):
        return bool(self.SendScintilla(QsciScintilla.SCI_GETFOLDEXPANDED, line))

    def fold_lines(self, start_line_one_based: int, end_line_one_based: int):
        line = start_line_one_based - 1
        if self._is_fold_line(line) and self._is_fold_expanded(line):
            self.foldLine(line)

    def unfold_lines(self, start_line_one_based: int, end_line_one_based: int):
        line = start_line_one_based - 1
        if self._is_fold_line(line) and not self._is_fold_expanded(line):
            self.foldLine(line)

    def fold_multiple_lines(self, ranges: list):
        for start, end in ranges:
            line = start - 1
            if self._is_fold_line(line) and self._is_fold_expanded(line):
                self.foldLine(line)

    def unfold_all(self):
        self.foldAll(False)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction("Undo", self.undo, QKeySequence("Ctrl+Z"))
        menu.addAction("Redo", self.redo, QKeySequence("Ctrl+Y"))
        menu.addSeparator()
        menu.addAction("Cut", self.cut, QKeySequence("Ctrl+X"))
        menu.addAction("Copy", self.copy, QKeySequence("Ctrl+C"))
        menu.addAction("Paste", self.paste, QKeySequence("Ctrl+V"))
        menu.addSeparator()
        menu.addAction("Select All", self.selectAll, QKeySequence("Ctrl+A"))
        menu.addSeparator()
        
        main_window = self.window()
        if hasattr(main_window, 'toggle_comment'):
            toggle_comment_action = menu.addAction("Toggle Comment")
            toggle_comment_action.setShortcut("Ctrl+/")
            toggle_comment_action.triggered.connect(main_window.toggle_comment)
            
        if hasattr(main_window, 'remove_empty_lines'):
            remove_empty_lines_action = menu.addAction("Remove Empty Lines")
            remove_empty_lines_action.triggered.connect(main_window.remove_empty_lines)
            
        menu.addSeparator()
        fragment_action = menu.addAction("Open Selected Fragment in New Window")
        fragment_action.setShortcut("F8")
        fragment_action.triggered.connect(self.fragment_editor_requested.emit)
        
        menu.exec(event.globalPos())

    def resizeEvent(self, event):
        super().resizeEvent(event)

    def _update_line_number_width(self):
        pass
        
    def _on_content_edited_unfold_all(self):
        pass
        
    def setPlainText(self, text):
        self.setText(text)
        
    def toPlainText(self):
        return self.text()

    def ensureCursorVisible(self):
        pass
        
    def centerCursor(self):
        pass


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
        self.links_tab = QWidget()
        self.favorites_tab = QWidget()
        
        self.addTab(self.find_tab, "Find Results")
        self.addTab(self.favorites_tab, "Favorites")
        self.addTab(self.bookmarks_tab, "Bookmarks")
        self.addTab(self.links_tab, "Links")
        self.addTab(self.output_tab, "Output")
        self.addTab(self.validation_tab, "Validation")

        self._setup_output_tab()
        self._setup_validation_tab()
        self._setup_find_tab()
        self._setup_bookmarks_tab()
        self._setup_links_tab()
        self._setup_favorites_tab()
    
    def _setup_favorites_tab(self):
        """Setup favorites tab"""
        layout = QVBoxLayout()
        self.favorites_widget = FavoritesWidget()
        layout.addWidget(self.favorites_widget)
        self.favorites_tab.setLayout(layout)
    
    def _setup_output_tab(self):
        """Setup output tab"""
        layout = QVBoxLayout()
        self.output_text = QsciScintilla()
        self.output_text.setUtf8(True)
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Consolas", 10))
        # Configure minimal look for output
        self.output_text.setMargins(0)
        self.output_text.setMarginWidth(0, 0)
        self.output_text.setMarginWidth(1, 0)
        self.output_text.setPaper(QColor("#ffffff"))
        self.output_text.setColor(QColor("#000000"))
        
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
        # Controls for bookmark operations - moved to right side
        controls = QHBoxLayout()
        controls.addStretch()  # Push buttons to the right
        btn_toggle = QPushButton("Toggle at Cursor")
        btn_next = QPushButton("Next")
        btn_prev = QPushButton("Previous")
        btn_clear = QPushButton("Clear All")
        # Make buttons more compact
        btn_style = "padding: 2px 6px; font-size: 9px;"
        btn_toggle.setStyleSheet(btn_style)
        btn_next.setStyleSheet(btn_style)
        btn_prev.setStyleSheet(btn_style)
        btn_clear.setStyleSheet(btn_style)
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
        controls.addWidget(btn_clear)
        layout.addLayout(controls)
        self.bookmark_list = QListWidget()
        self.bookmark_list.setMaximumHeight(250)
        self.bookmark_list.setStyleSheet("font-size: 9px;")  # Make list more compact
        layout.addWidget(self.bookmark_list)
        self.bookmarks_tab.setLayout(layout)

    def _setup_links_tab(self):
        """Setup links tab for XPath navigation"""
        layout = QVBoxLayout()
        
        # Info label
        info_label = QLabel("XPath Links (Ctrl+F11 to copy, F12 to navigate)")
        info_label.setStyleSheet("font-size: 9px; color: #888;")
        layout.addWidget(info_label)
        
        # Links text edit - one XPath per line
        self.links_text = QsciScintilla()
        self.links_text.setUtf8(True)
        self.links_text.setFont(QFont("Consolas", 9))
        self.links_text.setMargins(0)
        self.links_text.setMarginWidth(0, 0) # No line numbers needed for simple list
        self.links_text.setMarginWidth(1, 0)
        # QScintilla doesn't have placeholder text, simplified
        self.links_text.setText("<!-- XPath links will appear here... One link per line -->")
        self.links_text.setColor(QColor("#808080")) # Gray text initially
        
        # Clear placeholder on first focus (simple hack) or just leave it as comment
        
        layout.addWidget(self.links_text)
        
        self.links_tab.setLayout(layout)

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
        self.setFixedSize(450, 80)
        
        layout = QVBoxLayout()
        
        # Find input with history (no label)
        input_layout = QHBoxLayout()
        # Use QComboBox for history
        self.find_input = QComboBox()
        self.find_input.setEditable(True)
        self.find_input.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.find_input.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.find_input.setPlaceholderText("Find...")
        # Make line edit clearable and handle return press
        self.find_input.lineEdit().setClearButtonEnabled(True)
        self.find_input.lineEdit().returnPressed.connect(self.find_text)
        input_layout.addWidget(self.find_input)
        
        layout.addLayout(input_layout)
        
        # Options
        options_layout = QHBoxLayout()
        self.case_sensitive = QCheckBox("Case")
        self.case_sensitive.setToolTip("Case sensitive")
        self.whole_word = QCheckBox("Whole")
        self.whole_word.setToolTip("Whole word")
        self.use_regex = QCheckBox("Regex")
        self.use_regex.setToolTip("Use regular expressions")
        options_layout.addWidget(self.case_sensitive)
        options_layout.addWidget(self.whole_word)
        options_layout.addWidget(self.use_regex)
        options_layout.addStretch()

        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Close
        )
        button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Find")
        button_box.accepted.connect(self.find_text)
        button_box.rejected.connect(self.reject)
        options_layout.addWidget(button_box)
        layout.addLayout(options_layout)
        
        self.setLayout(layout)
        
        # Load search history
        self.search_history = self._load_search_history()
        self.find_input.addItems(self.search_history)
        self.find_input.setCurrentIndex(-1)

    def showEvent(self, event):
        """Auto-select text on show"""
        super().showEvent(event)
        # Use timer to ensure selection happens after focus events
        QTimer.singleShot(0, self._select_all)

    def _select_all(self):
        """Select all text in input"""
        self.find_input.setFocus()
        if self.find_input.lineEdit():
            self.find_input.lineEdit().selectAll()
        
    def _load_search_history(self):
        """Load search history from settings"""
        try:
            parent = self.parent()
            if hasattr(parent, '_get_settings'):
                settings = parent._get_settings()
                history = settings.value('search_history', '')
                if history:
                    return history.split('\n')[:20]  # Keep last 20 items
            return []
        except Exception:
            return []
    
    def _save_search_history(self, text):
        """Save search text to history"""
        if not text or not text.strip():
            return
            
        try:
            # Update local history list
            if text in self.search_history:
                self.search_history.remove(text)
            self.search_history.insert(0, text)
            # Keep only last 20
            self.search_history = self.search_history[:20]
            
            # Update combo box
            self.find_input.blockSignals(True)
            self.find_input.clear()
            self.find_input.addItems(self.search_history)
            self.find_input.setCurrentText(text)
            self.find_input.blockSignals(False)

            parent = self.parent()
            if hasattr(parent, '_get_settings'):
                # Save as newline-separated string
                settings = parent._get_settings()
                history_str = '\n'.join(self.search_history)
                settings.setValue('search_history', history_str)
        except Exception as e:
            print(f"Error saving search history: {e}")
    
    def get_search_params(self):
        """Get search parameters"""
        return {
            'text': self.find_input.currentText(),
            'case_sensitive': self.case_sensitive.isChecked(),
            'whole_word': self.whole_word.isChecked(),
            'use_regex': self.use_regex.isChecked()
        }
    
    def find_text(self):
        """Handle find button click"""
        text = self.find_input.currentText().strip()
        if text:
            self._save_search_history(text)
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
        self.current_zip_source = None  # { 'zip_path': str, 'arc_name': str, 'temp_dir': str }
        self.xml_service = XmlService()
        
        # Debug logging flag (set to True to enable treedebug.txt logging)
        self.tree_debug_enabled = False
        
        # Bookmarks functionality
        self._temp_bookmarks = {}  # Temporary storage until editor is active
        self._temp_numbered_bookmarks = {} # Temporary storage until editor is active
        self.current_bookmark_index = -1
        
        # Fragment editors tracking
        self.fragment_editors = []
        
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
        
        # Set up debounce timer for tree updates
        self.tree_update_debounce_interval = 5000  # Default 5 seconds, configurable in settings
        self.tree_update_timer = QTimer()
        self.tree_update_timer.setSingleShot(True)
        self.tree_update_timer.timeout.connect(self._debounced_tree_update)
        self._pending_tree_content = None
        
        # Auto rebuild tree flag (configurable in settings)
        self.auto_rebuild_tree = True
        self._tree_needs_rebuild = False  # Flag to track if tree needs manual rebuild
        self._pending_tree_path = None  # Pending path for deferred restoration
        
        # Debug mode flag
        self.debug_mode = False
        
        # Theme is applied via persisted settings in _load_persisted_flags
        
        # Load recent files and open file if provided, otherwise open most recent
        self._load_recent_files()
        self._load_file_states()  # Load cursor/selection states
        if file_path and os.path.exists(file_path):
            if file_path.lower().endswith('.zip'):
                # Defer zip opening slightly to ensure UI is fully ready
                QTimer.singleShot(100, lambda: self._open_zip_workflow(file_path))
            else:
                self._load_file_from_path(file_path)
                self.status_label.setText(f"Opened file: {os.path.basename(file_path)}")
                # Hide file navigator when starting with a file provided
                self._set_file_navigator_visible(False)
        else:
            session_path = os.path.join(os.path.expanduser("~"), ".lotus_xml_editor_session.json")
            if os.path.exists(session_path):
                QTimer.singleShot(0, self._restore_session)
            else:
                self._open_most_recent_file()
                # Hide file navigator if a recent file was auto-opened
                if self.current_file:
                    self._set_file_navigator_visible(False)

        # Zip support state
        # Zip support state initialized earlier

    def _get_version_string(self) -> str:
        """Calculate version string based on max modification time of core files."""
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            files_to_check = ['main.py', 'xml_service.py']
            max_ts = 0
            for fname in files_to_check:
                fpath = os.path.join(base_dir, fname)
                if os.path.exists(fpath):
                    ts = os.path.getmtime(fpath)
                    if ts > max_ts:
                        max_ts = ts
            
            if max_ts > 0:
                dt = QDateTime.fromSecsSinceEpoch(int(max_ts))
                return f"ver.{dt.toString('yyMMdd')}"
        except Exception:
            pass
        return "ver.dev"

    def _update_window_title(self):
        """Update window title with current file name and version"""
        ver_str = self._get_version_string()
        base_title = f"Lotus Xml Editor - {ver_str}"
        
        # Update FavoritesWidget file path
        if hasattr(self, 'bottom_panel') and hasattr(self.bottom_panel, 'favorites_widget'):
            self.bottom_panel.favorites_widget.current_file_path = self.current_file
        
        if self.current_file:
            filename = os.path.basename(self.current_file)
            if self.current_zip_source:
                 zip_name = os.path.basename(self.current_zip_source['zip_path'])
                 self.setWindowTitle(f"{filename} [{zip_name}] - {self.current_file} - {base_title}")
            else:
                 self.setWindowTitle(f"{filename} - {self.current_file} - {base_title}")
        else:
            self.setWindowTitle(base_title)

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
            self._debug_print(f"DEBUG: lxml indexing not available or failed: {e}")
            self.path_line_index = {}
            self._sync_index_available = False
    
    @property
    def numbered_bookmarks(self):
        """Get numbered bookmarks for the current editor"""
        if hasattr(self, 'xml_editor') and self.xml_editor:
            return self.xml_editor.numbered_bookmarks
        return self._temp_numbered_bookmarks

    @numbered_bookmarks.setter
    def numbered_bookmarks(self, value):
        """Set numbered bookmarks for the current editor"""
        if hasattr(self, 'xml_editor') and self.xml_editor:
            self.xml_editor.numbered_bookmarks = value
        else:
            self._temp_numbered_bookmarks = value

    @property
    def bookmarks(self):
        """Get bookmarks for the current editor"""
        if hasattr(self, 'xml_editor') and self.xml_editor:
            return self.xml_editor.bookmarks
        return self._temp_bookmarks

    @bookmarks.setter
    def bookmarks(self, value):
        """Set bookmarks for the current editor"""
        if hasattr(self, 'xml_editor') and self.xml_editor:
            self.xml_editor.bookmarks = value
        else:
            self._temp_bookmarks = value

    def _create_menu_bar(self):
        """Create menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        new_action = QAction("New", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        
        new_window_action = QAction("New Window", self)
        new_window_action.setShortcut("Ctrl+Shift+N")
        new_window_action.triggered.connect(self.file_new_window)
        file_menu.addAction(new_window_action)
        
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
        
        reread_action = QAction("Reread from Disk", self)
        reread_action.setShortcut("Ctrl+R")
        reread_action.setToolTip("Reload file from disk, discarding changes")
        reread_action.triggered.connect(self.reread_file)
        file_menu.addAction(reread_action)

        rename_action = QAction("Rename...", self)
        rename_action.setShortcut("Ctrl+F2")
        rename_action.setToolTip("Rename current file on disk")
        rename_action.triggered.connect(self.rename_file)
        file_menu.addAction(rename_action)
        
        open_folder_action = QAction("Open Containing Folder", self)
        open_folder_action.setShortcut("Alt+Shift+O")
        open_folder_action.setToolTip("Open folder in system file explorer")
        open_folder_action.triggered.connect(self.open_containing_folder)
        file_menu.addAction(open_folder_action)
        
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
        
        find_previous_action = QAction("Find Previous", self)
        find_previous_action.setShortcut("Shift+F3")
        find_previous_action.triggered.connect(self.find_previous)
        edit_menu.addAction(find_previous_action)

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
        
        remove_empty_lines_action = QAction("Remove Empty Lines", self)
        remove_empty_lines_action.setToolTip("Remove empty lines from selected text")
        remove_empty_lines_action.triggered.connect(self.remove_empty_lines)
        edit_menu.addAction(remove_empty_lines_action)

        toggle_comment_action = QAction("Toggle Comment", self)
        toggle_comment_action.setShortcut("Ctrl+/")
        toggle_comment_action.triggered.connect(self.toggle_comment)
        edit_menu.addAction(toggle_comment_action)
        
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
        
        edit_menu.addSeparator()
        
        # XPath Links actions
        copy_xpath_link_action = QAction("Copy XPath Link", self)
        copy_xpath_link_action.setShortcut("Ctrl+F11")
        copy_xpath_link_action.triggered.connect(self.copy_xpath_link)
        edit_menu.addAction(copy_xpath_link_action)
        
        navigate_xpath_link_action = QAction("Navigate to XPath Link", self)
        navigate_xpath_link_action.setShortcut("F12")
        navigate_xpath_link_action.triggered.connect(self.navigate_xpath_link)
        edit_menu.addAction(navigate_xpath_link_action)
        
        edit_menu.addSeparator()
        
        fragment_editor_action = QAction("Open Fragment Editor", self)
        fragment_editor_action.setShortcut("F8")
        fragment_editor_action.triggered.connect(self.open_fragment_editor)
        edit_menu.addAction(fragment_editor_action)
        
        edit_menu.addSeparator()

        # Select Node actions
        select_node_action = QAction("Select XML Node", self)
        select_node_action.setShortcut("Shift+F4")
        select_node_action.setToolTip("Select entire XML node near cursor (tags + content)")
        select_node_action.triggered.connect(lambda: self.select_xml_node_or_parent(exclude_border_tags=False))
        edit_menu.addAction(select_node_action)

        select_content_action = QAction("Select XML Content", self)
        select_content_action.setShortcut("F4")
        select_content_action.setToolTip("Select content inside XML tags near cursor")
        select_content_action.triggered.connect(lambda: self.select_xml_node_or_parent(exclude_border_tags=True))
        edit_menu.addAction(select_content_action)

        move_selection_action = QAction("Move Selection to New Tab with Link", self)
        move_selection_action.setShortcut("F6")
        move_selection_action.setToolTip("Move selected text to a new tab and replace with a link")
        move_selection_action.triggered.connect(self.move_selection_to_new_tab_with_link)
        edit_menu.addAction(move_selection_action)
        
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


        #  Structure Diagram
        xml_menu.addSeparator()
        structure_diagram_action = QAction("Structure Diagram", self)
        structure_diagram_action.setToolTip("Open a layered diagram view of the XML structure")
        structure_diagram_action.triggered.connect(self.open_structure_diagram)
        xml_menu.addAction(structure_diagram_action)

        # Commands menu
        commands_menu = menubar.addMenu("Commands")
        
        encode_file_action = QAction("Encode File to Clipboard", self)
        encode_file_action.setShortcut("Meta+Ctrl+Ins")
        encode_file_action.setToolTip("Encode file from system clipboard to base64 text with prefix")
        encode_file_action.triggered.connect(self._encode_file_to_clipboard)
        commands_menu.addAction(encode_file_action)
        
        decode_file_action = QAction("Decode File from Clipboard", self)
        decode_file_action.setShortcut("Meta+Shift+Ins")
        decode_file_action.setToolTip("Decode base64 text from clipboard to file")
        decode_file_action.triggered.connect(self._decode_file_from_clipboard)
        commands_menu.addAction(decode_file_action)

        commands_menu.addSeparator()

        escape_entities_action = QAction("Escape XML Entities in Selection", self)
        escape_entities_action.setShortcut("Ctrl+Shift+K")
        escape_entities_action.setToolTip("Convert special characters to XML entities (safe)")
        escape_entities_action.triggered.connect(self.escape_selection_entities)
        commands_menu.addAction(escape_entities_action)

        unescape_entities_action = QAction("Unescape XML Entities in Selection", self)
        unescape_entities_action.setShortcut("Ctrl+Alt+U")
        unescape_entities_action.setToolTip("Convert XML entities back to characters")
        unescape_entities_action.triggered.connect(self.unescape_selection_entities)
        commands_menu.addAction(unescape_entities_action)

        # Help menu (Обмен с 1С)
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

        # Spartan Mode toggle (No Sync/updates)
        self.spartan_mode_action = QAction("Spartan Mode (No Sync/updates)", self)
        self.spartan_mode_action.setCheckable(True)
        self.spartan_mode_action.setToolTip("Enable for large/broken files: disables sync, tree updates, highlights")
        
        def _on_spartan_mode_toggled(checked: bool):
            self.spartan_mode = checked
            # Persist flag
            try:
                self._save_flag('spartan_mode', checked)
            except Exception:
                pass
            
            # Apply Spartan Mode effects
            if checked:
                # Save current state before disabling
                self.spartan_pre_state = {}
                
                if hasattr(self, 'toggle_sync_action'):
                    self.spartan_pre_state['sync'] = self.toggle_sync_action.isChecked()
                    self.toggle_sync_action.setChecked(False)
                    
                if hasattr(self, 'toggle_update_tree_view_action'):
                    self.spartan_pre_state['update_tree'] = self.toggle_update_tree_view_action.isChecked()
                    self.toggle_update_tree_view_action.setChecked(False)
                    
                if hasattr(self, 'toggle_highlight_action'):
                    self.spartan_pre_state['highlight'] = self.toggle_highlight_action.isChecked()
                    self.toggle_highlight_action.setChecked(False)
                
                # Update status
                if hasattr(self, 'status_label') and self.status_label:
                    self.status_label.setText("Spartan Mode enabled: Sync, Auto-updates, Highlight disabled")
            else:
                # Restore previous state
                # If no pre-state (e.g. started in Spartan Mode), default to enabling standard features (Highlight, Tree)
                restore_sync = False
                restore_tree = True
                restore_highlight = True
                
                if hasattr(self, 'spartan_pre_state'):
                    restore_sync = self.spartan_pre_state.get('sync', False)
                    restore_tree = self.spartan_pre_state.get('update_tree', True)
                    restore_highlight = self.spartan_pre_state.get('highlight', True)
                
                if hasattr(self, 'toggle_sync_action'):
                    self.toggle_sync_action.setChecked(restore_sync)
                
                if hasattr(self, 'toggle_update_tree_view_action'):
                    self.toggle_update_tree_view_action.setChecked(restore_tree)
                
                if hasattr(self, 'toggle_highlight_action'):
                    self.toggle_highlight_action.setChecked(restore_highlight)
                
                if hasattr(self, 'status_label') and self.status_label:
                    self.status_label.setText("Spartan Mode disabled")
            
            # Update indicator
            try:
                self._update_flags_indicator()
            except Exception:
                pass

        self.spartan_mode_action.toggled.connect(_on_spartan_mode_toggled)
        view_menu.addAction(self.spartan_mode_action)
        view_menu.addSeparator()

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
        self.toggle_bottom_panel_action.setShortcut("F9")
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
        # view_menu.addAction(self.toggle_friendly_labels_action)

        # Update Tree on Tab Switch toggle in View menu (mirrors toolbar toggle)
        self.toggle_update_tree_view_action = QAction("Update Tree on Tab Switch", self)
        self.toggle_update_tree_view_action.setCheckable(True)
        self.toggle_update_tree_view_action.setChecked(False)  # Default: off
        #self.toggle_update_tree_view_action.setShortcut("F11")  # Hotkey: F9

        def _on_update_tree_view_toggled(checked: bool):
            # Set the underlying flag
            self.update_tree_on_tab_switch = checked
            
            # Disconnect or reconnect content_changed signal based on toggle state
            try:
                if checked:
                    # Reconnect signal to enable live tree updates
                    self.xml_editor.content_changed.connect(self.on_content_changed)
                else:
                    # Disconnect signal to prevent tree updates on every keystroke
                    self.xml_editor.content_changed.disconnect(self.on_content_changed)
            except Exception as e:
                # Signal might already be connected/disconnected, ignore
                pass
            
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
                self.status_label.setText(f"Tree update {'enabled' if checked else 'disabled'}")
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

        # XML Metro Navigator
        metro_navigator_action = QAction("XML Metro Navigator", self)
        metro_navigator_action.setShortcut("Ctrl+M")
        metro_navigator_action.triggered.connect(self.open_metro_navigator)
        view_menu.addAction(metro_navigator_action)

        view_menu.addSeparator()
        
        # Toggle Line Numbers
        self.toggle_line_numbers_action = QAction("Show Line Numbers", self)
        self.toggle_line_numbers_action.setCheckable(True)
        self.toggle_line_numbers_action.setChecked(False)  # Default: off
        self.toggle_line_numbers_action.setShortcut("Ctrl+L")
        
        def _on_line_numbers_toggled(checked: bool):
            try:
                self.apply_line_numbers_to_all_editors(checked)
                if hasattr(self, 'status_label') and self.status_label:
                    self.status_label.setText(f"Line numbers {'shown' if checked else 'hidden'}")
                try:
                    self._save_flag('show_line_numbers', checked)
                except Exception:
                    pass
            except Exception as e:
                print(f"Line numbers toggle error: {e}")
        
        self.toggle_line_numbers_action.toggled.connect(_on_line_numbers_toggled)
        view_menu.addAction(self.toggle_line_numbers_action)
        
        # Toggle Code Folding
        self.toggle_code_folding_action = QAction("Enable Code Folding", self)
        self.toggle_code_folding_action.setCheckable(True)
        self.toggle_code_folding_action.setChecked(True)  # Default: on
        
        def _on_code_folding_toggled(checked: bool):
            try:
                # Apply to current editor
                if hasattr(self, 'xml_editor') and self.xml_editor:
                    self.xml_editor.set_code_folding_enabled(checked)
                
                # Update status
                if hasattr(self, 'status_label') and self.status_label:
                    self.status_label.setText(f"Code folding {'enabled' if checked else 'disabled'}")
                
                # Persist flag
                try:
                    self._save_flag('code_folding', checked)
                except Exception:
                    pass
            except Exception as e:
                print(f"Code folding toggle error: {e}")
        
        self.toggle_code_folding_action.toggled.connect(_on_code_folding_toggled)
        view_menu.addAction(self.toggle_code_folding_action)
        
        view_menu.addSeparator()
        
        # Code Folding actions
        fold_current_action = QAction("Fold Current Element", self)
        fold_current_action.setShortcut("Ctrl+Shift+[")
        fold_current_action.triggered.connect(self.fold_current_element)
        view_menu.addAction(fold_current_action)
        
        unfold_current_action = QAction("Unfold Current Element", self)
        unfold_current_action.setShortcut("Ctrl+Shift+]")
        unfold_current_action.triggered.connect(self.unfold_current_element)
        view_menu.addAction(unfold_current_action)
        
        unfold_all_action = QAction("Unfold All", self)
        unfold_all_action.setShortcut("Ctrl+Shift+U")
        unfold_all_action.triggered.connect(self.unfold_all_elements)
        view_menu.addAction(unfold_all_action)
        
        view_menu.addSeparator()
        
        nav_up_action = QAction("Navigate Tree Up", self)
        nav_up_action.setShortcut("Ctrl+Up")
        nav_up_action.triggered.connect(lambda: self.xml_tree.navigate_node_up() if hasattr(self, 'xml_tree') else None)
        view_menu.addAction(nav_up_action)
        
        nav_down_action = QAction("Navigate Tree Down", self)
        nav_down_action.setShortcut("Ctrl+Down")
        nav_down_action.triggered.connect(lambda: self.xml_tree.navigate_node_down() if hasattr(self, 'xml_tree') else None)
        view_menu.addAction(nav_down_action)

        # Settings menu
        settings_menu = menubar.addMenu("Settings")
        settings_action = QAction("Preferences...", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self.show_settings_dialog)
        settings_menu.addAction(settings_action)

        # Help menu
        help_menu = menubar.addMenu("Help")
        hotkeys_action = QAction("Keyboard Shortcuts...", self)
        hotkeys_action.setShortcut("F1")
        hotkeys_action.triggered.connect(self.show_hotkey_help)
        help_menu.addAction(hotkeys_action)
        
        about_action = QAction("About...", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
    
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
        save_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))
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
        
        #split_btn = QAction("Split XML", self)
        #split_btn.triggered.connect(self.show_split_dialog)
        #toolbar.addAction(split_btn)
        
        # Tree rebuild indicator (shown when auto-rebuild is disabled and tree needs update)
        self.tree_rebuild_indicator = QLabel("⚠")
        self.tree_rebuild_indicator.setStyleSheet("color: orange; font-size: 16px; font-weight: bold; padding: 0 5px;")
        self.tree_rebuild_indicator.setToolTip("Tree needs rebuild - click 'Rebuild Tree' to update")
        self.tree_rebuild_indicator.setVisible(False)
        toolbar.addWidget(self.tree_rebuild_indicator)
        
        # Rebuild Tree button with auto-close tags
        rebuild_tree_btn = QAction("Rebuild Tree", self)
        rebuild_tree_btn.setShortcut("F5")
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
                    current_line = 0
                    line, _ = self.xml_editor.getCursorPosition()
                    current_line = line + 1

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
            
            if hasattr(self, 'xml_editor'):
                if hasattr(self.xml_editor, 'set_visibility_options'):
                    # Update visibility via QScintilla method
                    # We need to get current states of other flags
                    hide_tgs = self._read_flag('hide_tags', False)
                    hide_vals = self._read_flag('hide_values', False)
                    self.xml_editor.set_visibility_options(
                        hide_symbols=checked,
                        hide_tags=hide_tgs,
                        hide_values=hide_vals
                    )
                elif hasattr(self.xml_editor, 'highlighter') and self.xml_editor.highlighter:
                    # Legacy update highlighter visibility option for symbols
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
            
            if hasattr(self, 'xml_editor'):
                if hasattr(self.xml_editor, 'set_visibility_options'):
                    # Update visibility via QScintilla method
                    hide_syms = self._read_flag('hide_symbols', False)
                    hide_vals = self._read_flag('hide_values', False)
                    self.xml_editor.set_visibility_options(
                        hide_symbols=hide_syms,
                        hide_tags=checked,
                        hide_values=hide_vals
                    )
                elif hasattr(self.xml_editor, 'highlighter') and self.xml_editor.highlighter:
                    # Legacy update highlighter visibility option for tags
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
            
            if hasattr(self, 'xml_editor'):
                if hasattr(self.xml_editor, 'set_visibility_options'):
                    # Update visibility via QScintilla method
                    hide_syms = self._read_flag('hide_symbols', False)
                    hide_tgs = self._read_flag('hide_tags', False)
                    self.xml_editor.set_visibility_options(
                        hide_symbols=hide_syms,
                        hide_tags=hide_tgs,
                        hide_values=checked
                    )
                elif hasattr(self.xml_editor, 'highlighter') and self.xml_editor.highlighter:
                    # Legacy update highlighter visibility option for values
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
        self.update_tree_toggle.setChecked(False)  # Default: off
        self.update_tree_toggle.setShortcut("Shift+F11")  # Hotkey: Shift+F11

        def _on_update_tree_toggled(checked: bool):
            # Update button state
            self._update_button_state('updtree', checked)
            
            self.update_tree_on_tab_switch = checked
            
            # Disconnect or reconnect content_changed signal based on toggle state
            try:
                if checked:
                    # Reconnect signal to enable live tree updates
                    self.xml_editor.content_changed.connect(self.on_content_changed)
                else:
                    # Disconnect signal to prevent tree updates on every keystroke
                    self.xml_editor.content_changed.disconnect(self.on_content_changed)
            except Exception as e:
                # Signal might already be connected/disconnected, ignore
                pass
            
            if hasattr(self, 'status_label') and self.status_label:
                self.status_label.setText(f"Tree update {'enabled' if checked else 'disabled'}")
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
        # toolbar.addSeparator()
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
        # Moved to status bar
        # toolbar.addAction(self.toggle_hide_leaves_action)
    
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
            # Check multiple locations for bundled file
            locations = [
                os.path.dirname(os.path.abspath(__file__)), # Dev mode
            ]
            if getattr(sys, 'frozen', False):
                 # PyInstaller onedir/onefile
                 locations.append(os.path.dirname(sys.executable))
                 if hasattr(sys, '_MEIPASS'):
                     locations.append(sys._MEIPASS)

            found = False
            for base_dir in locations:
                udl_path = os.path.join(base_dir, "1C Ent_TRANS.xml")
                if os.path.exists(udl_path):
                    ld = load_udl_xml(udl_path)
                    if ld:
                        self.language_registry.install(ld)
                        found = True
                        break
            
            if not found:
                 # Try current working directory as fallback
                 udl_path = os.path.join(os.getcwd(), "1C Ent_TRANS.xml")
                 if os.path.exists(udl_path):
                     ld = load_udl_xml(udl_path)
                     if ld:
                         self.language_registry.install(ld)
        except Exception as e:
            print(f"Default language install error: {e}")

    def handle_definition_lookup(self, content):
        """Handle definition lookup request from editor (Ctrl+Click on quoted text)"""
        try:
            target_type = None
            target_name = None
            
            if content.startswith("Запросы."):
                target_type = "Запрос"
                target_name = content.split(".", 1)[1]
            elif content.startswith("Алгоритмы."):
                target_type = "Алгоритм"
                target_name = content.split(".", 1)[1]
            
            if not target_type or not target_name:
                return

            editor_content = self.xml_editor.get_content()
            
            # Find the tag with the given name attribute
            # We look for <Type ... Имя="Name" ...>
            # Use regex for robustness against attribute order and whitespace
            pattern = f'<{target_type}[^>]*Имя="{re.escape(target_name)}"[^>]*>'
            match = re.search(pattern, editor_content)
            
            if not match:
                self.status_bar.showMessage(f"Definition not found: {content}", 3000)
                return
            
            start_pos = match.end()
            
            # Find the closing tag
            # We need to handle nested tags of same type if any (unlikely for top-level definitions but possible)
            # A simple search for </Type> after start_pos might be enough if we assume well-formedness
            # But better to use a balanced finder if possible.
            # For now, let's try simple search for closing tag.
            closing_tag = f"</{target_type}>"
            end_pos = editor_content.find(closing_tag, start_pos)
            
            if end_pos == -1:
                self.status_bar.showMessage(f"Closing tag for {content} not found", 3000)
                return
            
            # Extract content (excluding the tag itself)
            fragment_text = editor_content[start_pos:end_pos]
            
            # Remove leading newline if present (optional, but cleaner)
            if fragment_text.startswith('\n'):
                fragment_text = fragment_text[1:]
            
            # Open in fragment editor
            # We pass 'XML' as language (or maybe 1C Internal if supported)
            dlg = FragmentEditorDialog(fragment_text, self.language_registry, initial_language='XML', parent=self)
            
            # If user saves, we need to update the original document
            # This is tricky because we need to replace the exact range.
            # We can use a callback.
            
            def on_save(new_text):
                # Replace the range in the editor
                # We need to convert byte offsets (start_pos, end_pos) to line/index if using QScintilla API
                # Or just use setText but that replaces everything.
                # Better: use byte offsets if we are sure content hasn't changed.
                # If content changed, we are in trouble.
                # But dialog is modal? No, it's non-modal usually?
                # FragmentEditorDialog inherits QDialog, so exec() makes it modal.
                
                # Check if content changed in background
                current_content = self.xml_editor.get_content()
                current_match = re.search(pattern, current_content)
                if not current_match:
                    QMessageBox.warning(self, "Error", "Original definition not found (file changed?)")
                    return
                
                current_start = current_match.end()
                current_end = current_content.find(closing_tag, current_start)
                
                if current_end == -1:
                    QMessageBox.warning(self, "Error", "Closing tag not found (file changed?)")
                    return
                
                # Construct new content
                new_full_content = current_content[:current_start] + ("\n" if not new_text.startswith('\n') else "") + new_text + current_content[current_end:]
                
                # Set text and preserve cursor if possible
                line, index = self.xml_editor.getCursorPosition()
                self.xml_editor.set_content(new_full_content)
                self.xml_editor.setCursorPosition(line, index)
                
                self.status_bar.showMessage(f"Updated definition for {content}", 3000)

            dlg.save_requested.connect(on_save)
            dlg.exec()

        except Exception as e:
            print(f"Definition lookup error: {e}")
            self.status_bar.showMessage(f"Error opening definition: {str(e)}", 3000)

    def open_fragment_editor(self):
        """Open selected text in fragment editor."""
        try:
            editor = self.xml_editor
            if not editor:
                return
            
            update_target = None
            text = ""
            
            if not editor.hasSelectedText():
                QMessageBox.information(self, "Fragment Editor", "Please select XML fragment to edit.")
                return
            text = editor.selectedText()
            update_target = editor
            
            dialog = FragmentEditorDialog(text, self.language_registry, parent=self)
            
            # Connect save signal to update the main editor
            dialog.save_requested.connect(lambda new_text: self._update_fragment_in_editor(update_target, new_text))
            
            dialog.setWindowFlags(Qt.WindowType.Window)  # Make it a non-modal window
            dialog.show()  # Show non-modal dialog
            
            # Track dialog for persistence
            if not hasattr(self, 'fragment_editors'):
                self.fragment_editors = []
            self.fragment_editors.append(dialog)
            # Remove from list when closed
            dialog.finished.connect(lambda result: self.fragment_editors.remove(dialog) if dialog in self.fragment_editors else None)
            
        except Exception as e:
            print(f"Fragment editor error: {e}")

    def _update_fragment_in_editor(self, target, new_text: str):
        """Update the fragment in the main editor with new text."""
        try:
            target.replaceSelectedText(new_text)
            if hasattr(self, 'status_bar') and self.status_bar:
                self.status_bar.showMessage("Fragment updated in main document", 3000)
                
        except Exception as e:
            print(f"Error updating fragment: {e}")
            QMessageBox.warning(self, "Update Error", f"Failed to update fragment: {e}")

    def _apply_selected_language_to_editor(self, editor: 'XmlEditorWidget'):
        """Apply the currently selected language profile to the given editor."""
        # TODO: Implement language switching for QScintilla (currently only XML is supported)
        pass                

    def cycle_syntax_language(self):
        """Cycle to the next available syntax language."""
        try:
            if hasattr(self, 'language_combo') and self.language_combo:
                count = self.language_combo.count()
                if count > 1:
                    current = self.language_combo.currentIndex()
                    next_index = (current + 1) % count
                    self.language_combo.setCurrentIndex(next_index)
        except Exception as e:
            print(f"Cycle syntax language error: {e}")

    def toggle_comment(self):
        """Toggle comment based on current syntax language."""
        try:
            current_lang = 'XML'
            if hasattr(self, 'language_combo') and self.language_combo:
                current_lang = self.language_combo.currentText()
            
            # Check for 1c-Ent syntax (case-insensitive check)
            # User specifically mentioned "1c-Ent syntax"
            is_1c = '1c' in current_lang.lower() or 'ent' in current_lang.lower()
            
            if is_1c:
                # Line comment with //
                if hasattr(self, 'xml_editor') and self.xml_editor:
                    self.xml_editor._toggle_line_comments(prefix="//")
            else:
                # Default to XML block comment <!-- -->
                if hasattr(self, 'xml_editor') and self.xml_editor:
                    self.xml_editor.toggle_block_comment()
        except Exception as e:
            print(f"Toggle comment error: {e}")

    
    def _apply_highlighter_settings(self):
        """Apply saved highlighter visibility settings after opening a file."""
        try:
            if hasattr(self, 'xml_editor') and self.xml_editor:
                hide_syms = self._read_flag('hide_symbols', False)
                hide_tgs = self._read_flag('hide_tags', False)
                hide_vals = self._read_flag('hide_values', False)
                
                # Use QScintilla method if available
                if hasattr(self.xml_editor, 'set_visibility_options'):
                    self.xml_editor.set_visibility_options(
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
        
        # Unified tree container with close button
        self.tree_container = QWidget()
        self.tree_container_layout = QVBoxLayout()
        self.tree_container_layout.setContentsMargins(0, 0, 0, 0)
        self.tree_container_layout.setSpacing(0)
        
        # Header row with title and close button
        header_row = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(2)
        
        """ tree_label = QLabel("XML Structure")
        tree_label.setStyleSheet("font-weight: bold; padding: 1px; font-size: 10px;")
        header_layout.addWidget(tree_label)
        header_layout.addStretch()
        
        # Close button - positioned at top right
        close_btn = QPushButton("✕")
        close_btn.setStyleSheet(" ""
            QPushButton {
                border: none;
                background: transparent;
                color: #888;
                font-size: 12px;
                padding: 0px;
                margin: 0px;
                width: 16px;
                height: 16px;
                border-radius: 2px;
            }
            QPushButton:hover {
                background: #e0e0e0;
                color: #333;
            }
        " "")
        close_btn.setToolTip("Hide XML Structure panel")
        close_btn.clicked.connect(self._hide_tree_panel)
        header_layout.addWidget(close_btn) """
        
        header_row.setLayout(header_layout)
        self.tree_container_layout.addWidget(header_row)
        
        # Search filter input
        search_container = QWidget()
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(0, 2, 0, 2)
        search_layout.setSpacing(4)
        
        search_label = QLabel("Filter:")
        search_label.setStyleSheet("font-size: 9px;")
        search_layout.addWidget(search_label)
        
        self.tree_search_input = QLineEdit()
        self.tree_search_input.setPlaceholderText("Type to filter tree nodes...")
        self.tree_search_input.setMaximumHeight(22)
        self.tree_search_input.setStyleSheet("font-size: 9px; padding: 2px;")
        self.tree_search_input.textChanged.connect(self._on_tree_search_changed)
        self.tree_search_input.setClearButtonEnabled(True)
        search_layout.addWidget(self.tree_search_input)
        
        search_container.setLayout(search_layout)
        search_container.setMaximumHeight(26)
        self.tree_container_layout.addWidget(search_container)
        
        # Persistent container for level header buttons
        self.level_header_container = QWidget()
        self.level_header_container.setMaximumHeight(24)
        _lvl_header_layout = QHBoxLayout()
        _lvl_header_layout.setContentsMargins(0, 0, 0, 0)
        _lvl_header_layout.setSpacing(2)
        self.level_header_container.setLayout(_lvl_header_layout)
        self.tree_container_layout.addWidget(self.level_header_container)
        
        self.tree_container.setLayout(self.tree_container_layout)
        
        # Create xml_tree widget
        self.xml_tree = XmlTreeWidget()
        # Provide the container to the tree so it can mount header buttons
        self.xml_tree.header_container = self.level_header_container
        
        # Store reference to update status_label later
        self.xml_tree.status_label = None
        # Sync editor folding with tree expand/collapse
        try:
            self.xml_tree.itemCollapsed.connect(self._on_tree_item_collapsed)
            self.xml_tree.itemExpanded.connect(self._on_tree_item_expanded)
            # Connect delete/hide signals
            self.xml_tree.delete_node_requested.connect(self.delete_xml_node)
            self.xml_tree.hide_node_requested.connect(self.hide_xml_node)
            self.xml_tree.tree_built.connect(self._on_tree_built)
        except Exception:
            pass
        
        # Add xml_tree BEFORE tree_container to left_layout
        left_layout.addWidget(self.xml_tree, 1)  # stretch factor 1 - takes available space
        left_layout.addWidget(self.tree_container, 0)  # stretch factor 0 - minimal space
        
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
        
        # Tab context menu
        self.tab_widget.tabBar().setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tab_widget.tabBar().customContextMenuRequested.connect(self._on_tab_context_menu)
        
        self.update_tree_on_tab_switch = False  # Default: off to avoid tree updates on every keystroke
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
        initial_editor.fragment_editor_requested.connect(self.open_fragment_editor)
        initial_editor.modification_changed.connect(self._on_editor_modification_changed)
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
        
        # Connect Favorites navigation signal
        if hasattr(self.bottom_panel, 'favorites_widget'):
            self.bottom_panel.favorites_widget.navigate_requested.connect(self.goto_line)
            
        self.bottom_dock = QDockWidget("", self)  # Empty title to save vertical space
        self.bottom_dock.setObjectName("BottomPanelDock")
        self.bottom_dock.setWidget(self.bottom_panel)
        self.bottom_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.bottom_dock)
        self.bottom_dock.setVisible(False)
    
    def _create_status_bar(self):
        """Create status bar"""
        self.status_bar = self.statusBar()
        
        # Random background color for status bar to distinguish multiple windows
        # Pink, Blue, Green, Brown, Teal, Purple (dark muted shades)
        colors = ["#5e3846", "#38495e", "#385e40", "#5e4838", "#385e5e", "#4b385e"]
        bg_color = random.choice(colors)
        
        # Set background for less contrast and reduce height by 1/3
        self.status_bar.setStyleSheet(f"QStatusBar {{ background-color: {bg_color}; color: #CCCCCC; max-height: 24px; padding: 0px; margin: 0px; }}")
        self.status_bar.setMaximumHeight(24)
        self.status_bar.setContentsMargins(0, 0, 0, 0)
        
        # Store button references for activity indication
        self.status_buttons = {}

        # Helper to create compact toolbuttons bound to actions
        def _add_flag_button(layout, action, text=None, button_key=None):
            btn = QToolButton()
            btn.setAutoRaise(True)
            btn.setStyleSheet("font-size: 9px; max-height: 22px; padding: 1px 3px; margin: 0px;")
            btn.setMaximumHeight(22)
            btn.setContentsMargins(0, 0, 0, 0)
            if text:
                # Override displayed text while keeping the action behavior
                action.setText(text)
            btn.setDefaultAction(action)
            layout.addWidget(btn)
            # Store button reference if key provided
            if button_key:
                self.status_buttons[button_key] = btn
                # Connect toggle to style update
                # Use lambda with default arg to capture key correctly
                action.toggled.connect(lambda checked, k=button_key: self._update_button_state(k, checked))
            return btn
        
        # Add status widgets with reduced font size (1/3 smaller)
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("font-size: 9px; padding: 0px; margin: 0px;")
        self.status_label.setContentsMargins(0, 0, 0, 0)
        self.status_bar.addWidget(self.status_label)
        
        # New "Left Flags" container (placed before line counter)
        try:
            left_flags_bar = QWidget()
            left_flags_bar.setMaximumHeight(22)
            left_flags_bar.setContentsMargins(0, 0, 0, 0)
            left_flags_layout = QHBoxLayout()
            left_flags_layout.setContentsMargins(0, 0, 0, 0)
            left_flags_layout.setSpacing(2)
            left_flags_bar.setLayout(left_flags_layout)
            
            # Friendly Labels
            if hasattr(self, 'toggle_friendly_labels_action'):
                _add_flag_button(left_flags_layout, self.toggle_friendly_labels_action, text="Friendly", button_key='friendly')
                
            # Hide Leaves
            if hasattr(self, 'toggle_hide_leaves_action'):
                _add_flag_button(left_flags_layout, self.toggle_hide_leaves_action, text="HideLeaf", button_key='leaves')
                
            self.status_bar.addPermanentWidget(left_flags_bar)
        except Exception as e:
            print(f"Left flags bar init error: {e}")

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

            # Sync, Symbols, Tags, Values, Highlight, Update Tree
            if hasattr(self, 'toggle_highlight_action'):
                _add_flag_button(flags_layout, self.toggle_highlight_action, text="NodeHilit", button_key='highlight')
            if hasattr(self, 'toggle_sync_action'):
                _add_flag_button(flags_layout, self.toggle_sync_action, text="Sync", button_key='sync')
            if hasattr(self, 'toggle_symbols_action'):
                _add_flag_button(flags_layout, self.toggle_symbols_action, text="<>", button_key='symbols')
            if hasattr(self, 'toggle_tags_action'):
                _add_flag_button(flags_layout, self.toggle_tags_action, text="Tags", button_key='tags')
            if hasattr(self, 'toggle_values_action'):
                _add_flag_button(flags_layout, self.toggle_values_action, text="Vals", button_key='values')
            if hasattr(self, 'update_tree_toggle'):
                _add_flag_button(flags_layout, self.update_tree_toggle, text="UpdTree", button_key='updtree')

            self.status_bar.addPermanentWidget(flags_bar)
        except Exception as e:
            print(f"Flags bar init error: {e}")

        # Removed duplicate rightmost text indicator to avoid redundancy

    def _update_flags_indicator(self):
        try:
            #"""Update compact flags string in status bar"""
            parts = []
            # Spartan Mode
            if hasattr(self, 'spartan_mode_action') and self.spartan_mode_action.isChecked():
                parts.append("SPARTAN")

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
        return QSettings("visxml.net", "LotusXmlEditor")

    def _debug_print(self, message: str):
        """Print debug message if debug mode is enabled"""
        if getattr(self, 'debug_mode', False):
            print(message)
    
    def apply_line_numbers_to_all_editors(self, visible: bool):
        """Apply line number visibility to all editor tabs"""
        try:
            if hasattr(self, 'tab_widget'):
                for i in range(self.tab_widget.count()):
                    editor = self.tab_widget.widget(i)
                    if isinstance(editor, XmlEditorWidget):
                        editor.set_line_numbers_visible(visible)
        except Exception as e:
            print(f"Error applying line numbers: {e}")
            
    def apply_font_settings(self, family: str, size: int):
        """Apply font settings to all open editors and output panel"""
        try:
            font = QFont(family, size)
            
            # Apply to all open editors
            if hasattr(self, 'tab_widget'):
                for i in range(self.tab_widget.count()):
                    editor = self.tab_widget.widget(i)
                    if isinstance(editor, XmlEditorWidget):
                        editor.setFont(font)
                        editor.setMarginsFont(font)
                        # Re-configure lexer to apply font
                        if editor.lexer():
                            editor.lexer().setDefaultFont(font)
                            editor.lexer().setFont(font)
            
            # Apply to output tab
            if hasattr(self, 'bottom_panel') and hasattr(self.bottom_panel, 'output_text'):
                self.bottom_panel.output_text.setFont(font)
                self.bottom_panel.output_text.setMarginsFont(font)
        except Exception as e:
            print(f"Error applying font settings: {e}")
    
    def _save_flag(self, key: str, value: bool):
        try:
            s = self._get_settings()
            s.setValue(f"flags/{key}", value)
        except Exception as e:
            print(f"Error saving flag '{key}': {e}")

    def _read_flag(self, name: str, default: bool) -> bool:
        """Helper to read boolean flag from settings"""
        try:
            s = self._get_settings()
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

    def _load_persisted_flags(self):
        """Load persisted flags and apply them to actions and UI state."""
        # Apply to actions without emitting toggled signals
        # Spartan Mode
        if hasattr(self, 'spartan_mode_action'):
            val = self._read_flag('spartan_mode', False)
            try:
                self.spartan_mode_action.blockSignals(True)
                self.spartan_mode_action.setChecked(val)
                self.spartan_mode_action.blockSignals(False)
            except Exception:
                pass
            self.spartan_mode = val
            # If enabled, enforce disabled states on other flags
            if val:
                # We need to ensure these are OFF regardless of what was just loaded
                # However, _load_persisted_flags logic is sequential.
                # If we load spartan mode late, we can override previous loaded values.
                # Or we can just rely on the toggle handler if we trigger it, but we blocked signals.
                # So we must manually apply effects here.
                if hasattr(self, 'toggle_sync_action'):
                    self.toggle_sync_action.setChecked(False)
                if hasattr(self, 'toggle_update_tree_view_action'):
                    self.toggle_update_tree_view_action.setChecked(False)
                if hasattr(self, 'toggle_highlight_action'):
                    self.toggle_highlight_action.setChecked(False)

        # Sync
        if hasattr(self, 'toggle_sync_action'):
            val = self._read_flag('sync_enabled', False)
            if getattr(self, 'spartan_mode', False):
                val = False
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
            val = self._read_flag('hide_symbols', False)
            try:
                self.toggle_symbols_action.blockSignals(True)
                self.toggle_symbols_action.setChecked(val)
                self.toggle_symbols_action.blockSignals(False)
            except Exception:
                pass
            if hasattr(self, 'xml_editor') and hasattr(self.xml_editor, 'highlighter') and self.xml_editor.highlighter:
                self.xml_editor.highlighter.set_visibility_options(hide_symbols=val)
            # Update button state
            self._update_button_state('symbols', val)
        # Tags
        if hasattr(self, 'toggle_tags_action'):
            val = self._read_flag('hide_tags', False)
            try:
                self.toggle_tags_action.blockSignals(True)
                self.toggle_tags_action.setChecked(val)
                self.toggle_tags_action.blockSignals(False)
            except Exception:
                pass
            if hasattr(self, 'xml_editor') and hasattr(self.xml_editor, 'highlighter') and self.xml_editor.highlighter:
                self.xml_editor.highlighter.set_visibility_options(hide_tags=val)
            # Update button state
            self._update_button_state('tags', val)
        # Values
        if hasattr(self, 'toggle_values_action'):
            val = self._read_flag('hide_values', False)
            try:
                self.toggle_values_action.blockSignals(True)
                self.toggle_values_action.setChecked(val)
                self.toggle_values_action.blockSignals(False)
            except Exception:
                pass
            if hasattr(self, 'xml_editor') and hasattr(self.xml_editor, 'highlighter') and self.xml_editor.highlighter:
                self.xml_editor.highlighter.set_visibility_options(hide_values=val)
            # Update button state
            self._update_button_state('values', val)
        # Highlight (Node Hilit)
        if hasattr(self, 'toggle_highlight_action'):
            val = self._read_flag('highlight_enabled', True)
            if getattr(self, 'spartan_mode', False):
                val = False
            try:
                self.toggle_highlight_action.blockSignals(True)
                self.toggle_highlight_action.setChecked(val)
                self.toggle_highlight_action.blockSignals(False)
            except Exception:
                pass
            self.highlight_enabled = val
            # Update button state
            self._update_button_state('highlight', val)
        # Friendly labels
        if hasattr(self, 'toggle_friendly_labels_action'):
            val = self._read_flag('friendly_labels', True)
            try:
                self.toggle_friendly_labels_action.blockSignals(True)
                self.toggle_friendly_labels_action.setChecked(val)
                self.toggle_friendly_labels_action.blockSignals(False)
            except Exception:
                pass
            if hasattr(self, 'xml_tree') and self.xml_tree:
                self.xml_tree.use_friendly_labels = val
                self.xml_tree.refresh_labels()
            # Update button state
            self._update_button_state('friendly', val)
            
        # Code Folding
        if hasattr(self, 'toggle_code_folding_action'):
            val = self._read_flag('code_folding', True)
            try:
                self.toggle_code_folding_action.blockSignals(True)
                self.toggle_code_folding_action.setChecked(val)
                self.toggle_code_folding_action.blockSignals(False)
            except Exception:
                pass
            if hasattr(self, 'xml_editor') and self.xml_editor:
                self.xml_editor.set_code_folding_enabled(val)
        # Show tree header preference
        show_tree_header = self._read_flag('show_tree_header', True)  # Default: show
        if not show_tree_header:
            # Hide unified tree container if it exists
            if hasattr(self, 'tree_container') and self.tree_container:
                self.tree_container.hide()
            # Hide left panel if it exists
            if hasattr(self, 'left_panel') and self.left_panel:
                self.left_panel.hide()
        
        # Update tree on tab switch (both actions reflect)
        val_upd = self._read_flag('update_tree_on_tab_switch', False)  # Default: off
        
        # Line numbers
        show_line_numbers = self._read_flag('show_line_numbers', False)  # Default: off
        self.apply_line_numbers_to_all_editors(show_line_numbers)
        # Sync toggle action state
        if hasattr(self, 'toggle_line_numbers_action'):
            try:
                self.toggle_line_numbers_action.blockSignals(True)
                self.toggle_line_numbers_action.setChecked(show_line_numbers)
                self.toggle_line_numbers_action.blockSignals(False)
            except Exception:
                pass
        
        # Auto rebuild tree
        self.auto_rebuild_tree = self._read_flag('auto_rebuild_tree', True)  # Default: on
        
        if getattr(self, 'spartan_mode', False):
            val_upd = False
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
        # Apply the signal connection state based on loaded setting
        try:
            if val_upd:
                # Ensure signal is connected
                try:
                    self.xml_editor.content_changed.connect(self.on_content_changed)
                except Exception:
                    pass  # Already connected
            else:
                # Ensure signal is disconnected
                try:
                    self.xml_editor.content_changed.disconnect(self.on_content_changed)
                except Exception:
                    pass  # Already disconnected
        except Exception:
            pass
        # Hide leaves
        if hasattr(self, 'auto_hide_enabled'):
            self.auto_hide_enabled = self._read_flag('auto_hide', True)
        if hasattr(self, 'toggle_hide_leaves_action'):
            val = self._read_flag('hide_leaves', True)
            try:
                self.toggle_hide_leaves_action.blockSignals(True)
                self.toggle_hide_leaves_action.setChecked(val)
                self.toggle_hide_leaves_action.blockSignals(False)
            except Exception:
                pass
            if hasattr(self, 'xml_tree') and self.xml_tree:
                self.xml_tree.set_hide_leaves(val)
            # Update button state
            self._update_button_state('leaves', val)
        # Breadcrumbs
        if hasattr(self, 'toggle_breadcrumb_action'):
            val = self._read_flag('show_breadcrumbs', False)
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
            val = self._read_flag('show_bottom_panel', False)
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
            val = self._read_flag('show_file_navigator', True)
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
            val = self._read_flag('exchange_semi_mode', True)
            try:
                self.exchange_mode_action.blockSignals(True)
                self.exchange_mode_action.setChecked(val)
                self.exchange_mode_action.blockSignals(False)
            except Exception:
                pass
            self.exchange_mode = 'semi' if val else 'manual'

        # Load debounce interval from settings
        try:
            debounce_val = s.value('tree_update_debounce', 5000, type=int)
            self.tree_update_debounce_interval = debounce_val
        except Exception:
            self.tree_update_debounce_interval = 5000
        
        # Load debug mode from settings
        debug_mode_val = self._read_flag('debug_mode', False)
        self.debug_mode = debug_mode_val
        
        # Auto-hide preferences
        toolbar_autohide_val = self._read_flag('toolbar_autohide', True)
        tree_header_autohide_val = self._read_flag('tree_header_autohide', True)
        tree_column_header_autohide_val = self._read_flag('tree_column_header_autohide', True)
        tab_bar_autohide_val = self._read_flag('tab_bar_autohide', True)
        
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
                self._debug_print(f"DEBUG: Applying auto-hide - toolbar:{toolbar_autohide_val}, tree_header:{tree_header_autohide_val}, tree_column:{tree_column_header_autohide_val}, tab_bar:{tab_bar_autohide_val}")
                if hasattr(self, 'toolbar_auto_hide'):
                    self.toolbar_auto_hide.set_auto_hide_enabled(toolbar_autohide_val)
                    self._debug_print(f"DEBUG: Toolbar auto-hide applied, enabled={self.toolbar_auto_hide.auto_hide_enabled}")
                if hasattr(self, 'tree_header_auto_hide'):
                    self.tree_header_auto_hide.set_auto_hide_enabled(tree_header_autohide_val)
                    self._debug_print(f"DEBUG: Tree header auto-hide applied, enabled={self.tree_header_auto_hide.auto_hide_enabled}")
                if hasattr(self, 'tree_column_header_auto_hide'):
                    self.tree_column_header_auto_hide.set_auto_hide_enabled(tree_column_header_autohide_val)
                    self._debug_print(f"DEBUG: Tree column header auto-hide applied, enabled={self.tree_column_header_auto_hide.auto_hide_enabled}")
                if hasattr(self, 'tab_bar_auto_hide'):
                    self.tab_bar_auto_hide.set_auto_hide_enabled(tab_bar_autohide_val)
                    self._debug_print(f"DEBUG: Tab bar auto-hide applied, enabled={self.tab_bar_auto_hide.auto_hide_enabled}")
            except Exception as e:
                self._debug_print(f"DEBUG: Error applying auto-hide: {e}")
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
            is_dark = self._read_flag('dark_theme', True)
            if is_dark:
                # Use QTimer to ensure UI is ready before applying theme
                QTimer.singleShot(0, self.set_dark_theme)
            else:
                QTimer.singleShot(0, self.set_light_theme)
        except Exception:
            pass

        # Reapply visibility options after theme to ensure they take effect
        try:
            if hasattr(self, 'xml_editor') and hasattr(self.xml_editor, 'highlighter') and self.xml_editor.highlighter:
                hide_syms = self._read_flag('hide_symbols', False)
                hide_tgs = self._read_flag('hide_tags', False)
                hide_vals = self._read_flag('hide_values', False)
                self._debug_print(f"DEBUG: Reapplying visibility - symbols:{hide_syms}, tags:{hide_tgs}, values:{hide_vals}")
                self.xml_editor.highlighter.set_visibility_options(
                    hide_symbols=hide_syms,
                    hide_tags=hide_tgs,
                    hide_values=hide_vals
                )
                self._debug_print(f"DEBUG: Highlighter state after reapply - symbols:{self.xml_editor.highlighter.hide_symbols}, tags:{self.xml_editor.highlighter.hide_tags}, values:{self.xml_editor.highlighter.hide_values}")
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
        # Only connect content_changed if update_tree_on_tab_switch is enabled
        if getattr(self, 'update_tree_on_tab_switch', False):
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
            # Get the row index of the double-clicked item
            row = self.bottom_panel.find_results.row(item)
            print(f"DEBUG: Double-clicked item at row {row}, total results: {len(self.last_search_results)}")
            
            if 0 <= row < len(self.last_search_results):
                # Update current search index to match the clicked item
                self.current_search_index = row
                # Navigate to the specific result
                self._navigate_to_search_result(row)
            else:
                print(f"DEBUG: Row {row} is out of bounds for search results")
        except Exception as e:
            print(f"Find result double-click error: {e}")
            import traceback
            traceback.print_exc()

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

    def _on_editor_modification_changed(self, modified: bool):
        """Update tab title with unsaved indicator (*)"""
        try:
            editor = self.sender()
            if not isinstance(editor, XmlEditorWidget):
                return
            
            index = self.tab_widget.indexOf(editor)
            if index == -1:
                return
            
            title = self.tab_widget.tabText(index)
            has_star = title.startswith("*")
            clean_title = title[1:] if has_star else title
            
            if modified:
                if not has_star:
                    self.tab_widget.setTabText(index, f"*{clean_title}")
            else:
                if has_star:
                    self.tab_widget.setTabText(index, clean_title)
        except Exception as e:
            print(f"Error updating tab title: {e}")

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
            self.current_file = getattr(self.xml_editor, 'file_path', None)
            self._update_window_title()
            
            self.xml_editor.content_changed.connect(self.on_content_changed)
            self.xml_editor.cursor_position_changed.connect(self.on_cursor_changed)
            # Apply selected language to the new active editor
            try:
                self._apply_selected_language_to_editor(self.xml_editor)
            except Exception:
                pass
            
            # Sync code folding action state
            if hasattr(self, 'toggle_code_folding_action'):
                was_blocked = self.toggle_code_folding_action.blockSignals(True)
                self.toggle_code_folding_action.setChecked(self.xml_editor.line_number_widget.folding_enabled)
                self.toggle_code_folding_action.blockSignals(was_blocked)

            # Update tree if toggle enabled
            if getattr(self, 'update_tree_on_tab_switch', True):
                content = self.xml_editor.get_content()
                self.xml_tree.populate_tree(content)
        except Exception as e:
            print(f"Error on tab change: {e}")

    def _on_tab_context_menu(self, point):
        """Show context menu for tab bar."""
        try:
            tab_bar = self.tab_widget.tabBar()
            index = tab_bar.tabAt(point)
            
            menu = QMenu(self)
            
            # Action: Replace link with edited text
            replace_action = menu.addAction("Replace link with edited text from separate tab")
            replace_action.setShortcut("Shift+F5")
            replace_action.triggered.connect(self.replace_link_with_tab_content)
            
            menu.addSeparator()
            
            # Action: Close
            close_action = menu.addAction("Close Tab")
            close_action.triggered.connect(lambda: self._close_tab(index) if index >= 0 else None)
            if index < 0:
                close_action.setEnabled(False)
            
            menu.exec(tab_bar.mapToGlobal(point))
        except Exception as e:
            print(f"Tab context menu error: {e}")

    def _close_tab(self, index: int):
        """Close tab and clean up references"""
        widget = self.tab_widget.widget(index)
        
        # Capture state before closing
        if isinstance(widget, XmlEditorWidget):
            self._capture_editor_state(widget)
            # Save to disk to ensure state is persisted even if app crashes later
            # We defer saving slightly to avoid lag on close, or just save now.
            # Saving now is safer.
            QTimer.singleShot(0, self._save_file_states)

        self.tab_widget.removeTab(index)
        # If closing active tab, _on_tab_changed will update reference; ensure we have at least one tab
        if self.tab_widget.count() == 0:
            new_editor = XmlEditorWidget()
            new_editor.fragment_editor_requested.connect(self.open_fragment_editor)
            new_editor.modification_changed.connect(self._on_editor_modification_changed)
            
            # Apply line numbers setting
            show_line_numbers = self._read_flag('show_line_numbers', False)
            new_editor.set_line_numbers_visible(show_line_numbers)
            
            # Apply code folding setting
            code_folding = self._read_flag('code_folding', True)
            new_editor.set_code_folding_enabled(code_folding)
            
            self.tab_widget.addTab(new_editor, "Document")
            self.xml_editor = new_editor
            self._connect_signals()

    def _create_editor_tab(self, title: str, content: str):
        """Create a new editor tab with given title and content, return editor and index"""
        editor = XmlEditorWidget()
        editor.fragment_editor_requested.connect(self.open_fragment_editor)
        editor.definition_lookup_requested.connect(self.handle_definition_lookup)
        editor.modification_changed.connect(self._on_editor_modification_changed)
        editor.set_content(content)
        
        # Apply line numbers setting
        show_line_numbers = self._read_flag('show_line_numbers', False)
        editor.set_line_numbers_visible(show_line_numbers)
        
        # Apply code folding setting
        code_folding = self._read_flag('code_folding', True)
        editor.set_code_folding_enabled(code_folding)
        
        if code_folding:
            self.auto_fold_special_tags(editor)
        
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
            text = editor.text()
            pos = editor.get_cursor_char_position()

            ranges = self._compute_enclosing_xml_ranges(text)
            if not ranges:
                return None
            containing = [r for r in ranges if r[1] <= pos <= r[2]]
            if not containing:
                return None
            target = sorted(containing, key=lambda r: (r[2] - r[1]))[0]
            start_pos, end_pos = target[1], target[2]
            
            # Map positions to 1-based line numbers
            start_line = text.count('\n', 0, start_pos) + 1
            end_line = text.count('\n', 0, end_pos) + 1
            
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

    def unfold_all_elements(self):
        """Unfold all folded elements in the editor."""
        try:
            self.xml_editor.unfold_all()
            if hasattr(self, 'status_label') and self.status_label:
                self.status_label.setText("All elements unfolded")
        except Exception as e:
            print(f"Unfold all error: {e}")

    def jump_to_matching_tag(self, direction: str):
        """
        Jump to matching tag based on direction.
        direction: 'next_close' (Ctrl+]) or 'prev_open' (Ctrl+[)
        """
        try:
            editor = self.xml_editor
            text = editor.text()
            pos = editor.get_cursor_char_position()
            
            # Get all enclosing ranges
            ranges = self._compute_enclosing_xml_ranges(text)
            
            # Filter for ranges containing the cursor
            containing = [r for r in ranges if r[1] <= pos <= r[2]]
            if not containing:
                return

            # Sort by size (smallest first -> innermost)
            containing.sort(key=lambda r: (r[2] - r[1]))
            
            target_pos = None
            
            if direction == 'next_close':
                # Find innermost range where end > pos
                for r in containing:
                    if r[2] > pos:
                        target_pos = r[2]
                        break
            elif direction == 'prev_open':
                # Find innermost range where start < pos
                for r in containing:
                    if r[1] < pos:
                        target_pos = r[1]
                        break
            
            if target_pos is not None:
                # Convert char offset to byte offset for QScintilla
                # Reuse 'text' which is already fetched
                byte_offset = len(text[:target_pos].encode('utf-8'))
                editor.SendScintilla(QsciScintilla.SCI_GOTOPOS, byte_offset)
                editor.ensureCursorVisible()
                    
                if hasattr(self, 'status_label') and self.status_label:
                    self.status_label.setText(f"Jumped to position {target_pos}")
                
        except Exception as e:
            print(f"Jump error: {e}")

    def fold_by_level(self, level: int):
        """Fold all XML elements at the specified nesting level."""
        try:
            content = self.xml_editor.get_content()
            if not content:
                return

            # Regex patterns (same as _compute_enclosing_xml_ranges)
            comment_pattern = re.compile(r"<!--.*?-->", re.DOTALL)
            cdata_pattern = re.compile(r"<!\[CDATA\[.*?\]\]>", re.DOTALL)
            pi_pattern = re.compile(r"<\?.*?\?>", re.DOTALL)
            doctype_pattern = re.compile(r"<!DOCTYPE.*?>", re.DOTALL)
            
            special_spans = []
            for pat in (comment_pattern, cdata_pattern, pi_pattern, doctype_pattern):
                for m in pat.finditer(content):
                    special_spans.append((m.start(), m.end()))
            
            tag_pattern = re.compile(r"<(/?)([^\s>/]+)([^>]*)>", re.UNICODE)
            
            stack = []  # (tag, start_index, depth)
            ranges_to_fold = []
            
            # Helper to check if pos is in special span
            def is_special(pos):
                for s, e in special_spans:
                    if s <= pos < e:
                        return True
                return False

            for m in tag_pattern.finditer(content):
                if is_special(m.start()):
                    continue
                    
                is_close = m.group(1) == '/'
                tag = m.group(2)
                rest = m.group(3) or ''
                self_closing = rest.rstrip().endswith('/')
                
                if not is_close and not self_closing:
                    # Open tag
                    depth = len(stack) + 1
                    stack.append((tag, m.start(), depth))
                elif is_close:
                    # Close tag
                    # Try to match with stack
                    for si in range(len(stack) - 1, -1, -1):
                        if stack[si][0] == tag:
                            # Found match
                            opentag, start_idx, depth = stack.pop(si)
                            # If this element is at the target level, mark for folding
                            if depth == level:
                                end_idx = m.end()
                                ranges_to_fold.append((start_idx, end_idx))
                            break
            
            if not ranges_to_fold:
                self.status_label.setText(f"No elements found at level {level}")
                return

            lines_ranges = []
            count = 0
            
            content = self.xml_editor.text()
            for start_idx, end_idx in ranges_to_fold:
                start_line = content.count('\n', 0, start_idx) + 1
                end_line = content.count('\n', 0, end_idx) + 1
                
                if start_line < end_line:
                    lines_ranges.append((start_line, end_line))
                    count += 1
            
            if lines_ranges:
                self.xml_editor.fold_multiple_lines(lines_ranges)
                self.status_label.setText(f"Folded {count} elements at level {level}")
            
        except Exception as e:
            print(f"Fold by level error: {e}")

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
    
    def _on_tree_search_changed(self, text: str):
        """Handle tree search filter text change"""
        try:
            if hasattr(self, 'xml_tree') and self.xml_tree:
                self.xml_tree.set_search_filter(text)
        except Exception as e:
            print(f"Tree search error: {e}")

    def _hide_tree_panel(self):
        """Hide the XML Structure panel and save the preference"""
        try:
            # Hide the unified tree container
            if hasattr(self, 'tree_container') and self.tree_container:
                self.tree_container.hide()
            # Also hide the left panel if it exists
            if hasattr(self, 'left_panel') and self.left_panel:
                self.left_panel.hide()
            self._save_flag('show_tree_header', False)
        except Exception as e:
            print(f"Error hiding tree panel: {e}")

    # --- F4/F5 helpers ---
    def auto_fold_special_tags(self, editor=None):
        """Automatically fold specific tags like <ПослеЗагрузки...>"""
        try:
            if not editor:
                editor = self.xml_editor
            
            # Check if folding is enabled
            if not editor.line_number_widget.folding_enabled:
                return

            content = editor.get_content()
            ranges = self._compute_enclosing_xml_ranges(content)
            
            ranges_to_fold = []
            for tag, start, end in ranges:
                if tag.startswith("ПослеЗагрузки") or tag.startswith("АлгоритмПослеЗагрузки"):
                    # Convert to lines
                    start_line = content[:start].count('\n') + 1
                    end_line = content[:end].count('\n') + 1
                    # Only fold if it spans multiple lines
                    if start_line < end_line:
                        ranges_to_fold.append((start_line, end_line))
            
            if ranges_to_fold:
                editor.fold_multiple_lines(ranges_to_fold)
                if hasattr(self, 'status_label') and self.status_label:
                    self.status_label.setText(f"Auto-folded {len(ranges_to_fold)} special blocks")
        except Exception as e:
            print(f"Auto-fold error: {e}")

    def _compute_enclosing_xml_ranges(self, text: str):
        """Compute element ranges using a simple stack-based parser. Returns list of (tag, start, end)."""
        ranges = []
        stack = []  # list of (tag, start_index)
        # Handle comments and CDATA and PIs by temporarily removing them to avoid mis-parsing
        # Record their spans as atomic ranges too
        comment_pattern = re.compile(r"<!--.*?-->", re.DOTALL)
        # Regex for C++ style line comments (//) - match contiguous blocks
        # Match start of line, optional whitespace, //, rest of line, and the newline
        line_comment_pattern = re.compile(r"(?:^\s*//.*(?:\r?\n|$))+", re.MULTILINE)
        cdata_pattern = re.compile(r"<!\[CDATA\[.*?\]\]>", re.DOTALL)
        pi_pattern = re.compile(r"<\?.*?\?>", re.DOTALL)
        doctype_pattern = re.compile(r"<!DOCTYPE.*?>", re.DOTALL)
        special_spans = []
        for pat in (comment_pattern, line_comment_pattern, cdata_pattern, pi_pattern, doctype_pattern):
            for m in pat.finditer(text):
                # For line comments, we only want to fold if it's more than one line or manually requested
                # But for now, let's treat any block as a range.
                # Use "comment" tag so it might be styled or treated as comment
                special_spans.append(("comment", m.start(), m.end()))
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

    def _get_node_range(self, node):
        """Get (start, end) text positions for an XmlTreeNode"""
        if not node or node.line_number <= 0:
            return None
            
        editor = self.xml_editor
        text = editor.text()

        ranges = self._compute_enclosing_xml_ranges(text)
        
        # Find range that starts at the node's line
        # node.line_number is 1-based
        target_line_idx = node.line_number - 1
        
        candidates = []
        
        for r in ranges:
            tag, start, end = r
            # Map char start position to line index
            # Optimization: use count which is fast in C-implemented python strings
            line_idx = text.count('\n', 0, start)
            if line_idx == target_line_idx:
                candidates.append(r)
        
        if not candidates:
            return None
            
        # Match tag if possible
        for r in candidates:
            if r[0] == node.tag:
                return (r[1], r[2])
        
        return (candidates[0][1], candidates[0][2])

    def _set_selection_range(self, start, end):
        """Helper to set selection range for both QScintilla and QTextEdit"""
        text = self.xml_editor.text()
         
        # Start
        start_line = text.count('\n', 0, start)
        last_nl_start = text.rfind('\n', 0, start)
        start_index = start if last_nl_start == -1 else start - last_nl_start - 1
         
        # End
        end_line = text.count('\n', 0, end)
        last_nl_end = text.rfind('\n', 0, end)
        end_index = end if last_nl_end == -1 else end - last_nl_end - 1
         
        self.xml_editor.setSelection(start_line, start_index, end_line, end_index)

    def delete_xml_node(self, node):
        """Delete the XML block corresponding to the node"""
        try:
            r = self._get_node_range(node)
            if not r:
                QMessageBox.warning(self, "Delete Error", "Could not locate the XML block in the editor.\nTry rebuilding the tree first.")
                return
                
            start, end = r
            self._set_selection_range(start, end)
            
            self.xml_editor.replaceSelectedText("")
            
            # Rebuild tree
            self.rebuild_tree_with_autoclose()
            if hasattr(self, 'status_label'):
                self.status_label.setText(f"Deleted {node.tag}")
        except Exception as e:
            QMessageBox.warning(self, "Delete Error", f"An error occurred: {e}")

    def hide_xml_node(self, node):
        """Hide (comment out) the XML block corresponding to the node"""
        try:
            r = self._get_node_range(node)
            if not r:
                QMessageBox.warning(self, "Hide Error", "Could not locate the XML block in the editor.\nTry rebuilding the tree first.")
                return
                
            start, end = r
            
            # Check content
            text = self.xml_editor.text()
                 
            selected_text = text[start:end]
            
            if "-->" in selected_text:
                 QMessageBox.warning(self, "Hide Error", "Cannot comment out block containing '-->'.")
                 return
    
            self._set_selection_range(start, end)
            
            new_text = f"<!-- {selected_text} -->"
            
            self.xml_editor.replaceSelectedText(new_text)
            
            # Rebuild tree
            self.rebuild_tree_with_autoclose()
            if hasattr(self, 'status_label'):
                self.status_label.setText(f"Hidden {node.tag}")
        except Exception as e:
            QMessageBox.warning(self, "Hide Error", f"An error occurred: {e}")

    def _get_inner_xml_range(self, text, start, end):
        """Helper to get inner content range excluding border tags."""
        # Find end of opening tag
        open_tag_end_idx = text.find('>', start, end)
        if open_tag_end_idx != -1:
             content_start = open_tag_end_idx + 1
        else:
             content_start = start

        # Find start of closing tag
        close_tag_start_idx = text.rfind('<', start, end)
        if close_tag_start_idx != -1:
             content_end = close_tag_start_idx
        else:
             content_end = end
             
        # Handle self-closing
        if content_start >= content_end:
             return content_end, content_end
        return content_start, content_end

    def _get_selection_char_offsets(self, editor):
        """Helper to get selection character offsets for both QScintilla and QTextEdit"""
        if not editor.hasSelectedText():
             return None, None
        
        # getSelection() -> (lineFrom, indexFrom, lineTo, indexTo)
        lf, if_, lt, it = editor.getSelection()
        
        # Helper to convert line/index to char offset
        def pos_from_line_index(line, index):
            pos = 0
            for i in range(line):
                 pos += len(editor.text(i))
            pos += index
            return pos
        
        start = pos_from_line_index(lf, if_)
        end = pos_from_line_index(lt, it)
        
        if start > end:
            start, end = end, start
        return start, end

    def select_xml_node_or_parent(self, exclude_border_tags=False):
        """Select XML node at cursor; repeated presses select parent element.
           If exclude_border_tags is True, selects only the content inside tags.
        """
        editor = self.xml_editor
        text = editor.text()
        pos = editor.get_cursor_char_position()


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
                
                if exclude_border_tags:
                    start, end = self._get_inner_xml_range(text, start, end)

                self._set_selection_range(start, end)
                
                # Sync tree to the newly selected element
                try:
                    line, _ = editor.getCursorPosition()
                    line += 1
                    self._sync_tree_to_cursor(line)
                except Exception:
                    pass
                return
            
            # If no ranges at all (empty/invalid XML), fall back to line selection
            line, _ = editor.getCursorPosition()
            # Select line
            # QScintilla doesn't have SelectLine? 
            # We can calculate line start/end or use setSelection with line + 1
            # Using setSelection(line, 0, line + 1, 0)
            editor.setSelection(line, 0, line + 1, 0)
            return
        
        target = None
        sel_start, sel_end = self._get_selection_char_offsets(editor)
        
        if sel_start is None:
            # First press: select deepest element
            target = containing_sorted[0]
        else:
            # Find current selection in the chain
            idx = next((i for i, r in enumerate(containing_sorted) if r[1] == sel_start and r[2] == sel_end), None)
            
            if idx is not None:
                # Found exact full match. Move to parent.
                parent_idx = min(idx + 1, len(containing_sorted) - 1)
                target = containing_sorted[parent_idx]
            else:
                # No full match. 
                # If exclude_border_tags is True, check if we match the CONTENT of any range.
                matched_content_idx = None
                if exclude_border_tags:
                    for i, r in enumerate(containing_sorted):
                        c_start, c_end = self._get_inner_xml_range(text, r[1], r[2])
                        if c_start == sel_start and c_end == sel_end:
                            matched_content_idx = i
                            break
                
                if matched_content_idx is not None:
                     # Found content match. Move to parent.
                     parent_idx = min(matched_content_idx + 1, len(containing_sorted) - 1)
                     target = containing_sorted[parent_idx]
                else:
                    # If current selection isn't one of the known ranges, select deepest first
                    target = containing_sorted[0]

        start, end = target[1], target[2]
        
        if exclude_border_tags:
            start, end = self._get_inner_xml_range(text, start, end)

        self._set_selection_range(start, end)
        
        # Sync tree to the newly selected element
        try:
            line, _ = editor.getCursorPosition()
            line += 1
            self._sync_tree_to_cursor(line)
        except Exception:
            pass

    def move_selection_to_new_tab_with_link(self):
        """Move selected text to a new tab and leave a link comment in place."""
        editor = self.xml_editor
        sel_start, sel_end = self._get_selection_char_offsets(editor)
        
        if sel_start is None:
            # If nothing selected, select element under cursor
            self.select_xml_node_or_parent()
            sel_start, sel_end = self._get_selection_char_offsets(editor)
            if sel_start is None:
                return
                
        text = editor.text()
             
        selected_text = text[sel_start:sel_end]
        
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
        
        self._set_selection_range(sel_start, sel_end)
        
        editor.replaceSelectedText(link_comment)
             
        # Optionally update tree if toggle enabled
        if getattr(self, 'update_tree_on_tab_switch', True):
            self.xml_tree.populate_tree(editor.text())
                 
        # Status update
        if hasattr(self, 'status_label') and self.status_label:
            self.status_label.setText(f"Moved selection to '{tab_title}', inserted link {link_id}")

    def replace_link_with_tab_content(self):
        """Replace a TABREF comment under cursor with the content from its tab."""
        editor = self.xml_editor
        text = editor.text()
        pos = editor.get_cursor_char_position()
             
        # Find TABREF comment around cursor
        pattern = re.compile(r"<!--\s*TABREF:\s*([A-Za-z0-9_\-]+)\s*-->")
        # Search a window around the cursor to find the comment boundaries
        start_search = max(0, pos - 200)
        end_search = min(len(text), pos + 200)
        segment = text[start_search:end_search]
        m = pattern.search(segment)
        
        link_id = None
        abs_start = 0
        abs_end = 0
        
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
            
        # Check if cursor is actually inside or near the match?
        # The logic above prefers local match, but if not found uses global.
        # This seems intended.
        
        # Lookup tab content
        if not hasattr(self, 'tab_link_map') or link_id not in self.tab_link_map:
            return
        sub_editor = self.tab_link_map[link_id]
        sub_content = sub_editor.text()
             
        # Replace the comment with content
        self._set_selection_range(abs_start, abs_end)
        
        editor.replaceSelectedText(sub_content)
             
        # Optionally update tree
        if getattr(self, 'update_tree_on_tab_switch', True):
            self.xml_tree.populate_tree(editor.text())
                 
        if hasattr(self, 'status_label') and self.status_label:
            self.status_label.setText(f"Replaced link {link_id} with tab content")
    
    def file_new_window(self):
        """Open a new editor window"""
        # Launch a new instance of the application
        if getattr(sys, 'frozen', False):
            # If running as compiled executable
            subprocess.Popen([sys.executable])
        else:
            # If running as script
            subprocess.Popen([sys.executable, sys.argv[0]])

    def new_file(self):
        """Create new file"""
        self.current_file = None
        self.current_zip_source = None
        self.xml_editor.set_content("")
        self.xml_tree.clear()
        self.current_file = None
        self._update_window_title()
        self.status_label.setText("New file created")
        
        # Clear recent files list when creating a new file
        # This ensures that closing the app after "New File" doesn't reopen the previous file
        self.recent_files = []
        self._save_recent_files()
    
    def open_file(self, file_path=None):
        """Open XML file"""
        print(f"DEBUG: open_file called with {file_path}")
        if file_path is None:
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Open XML or Zip File", "", "XML Files (*.xml);;Zip Archives (*.zip);;All Files (*.*)"
            )
        
        if file_path:
            print(f"DEBUG: Opening file: {file_path}")
            # Check for Zip file
            if file_path.lower().endswith('.zip'):
                self._open_zip_workflow(file_path)
                return

            splash = None
            try:
                # Check file size first
                file_size = os.path.getsize(file_path)
                print(f"DEBUG: File size: {file_size}")
                
                # For large files (>1MB), show progress and use chunked reading
                if file_size > 1024 * 1024:
                    # Show splash screen for large files
                    splash = LoadingSplashScreen()
                    splash.show()
                    splash.show_message(f"Loading large file ({file_size / 1024 / 1024:.1f} MB)...")
                    QApplication.processEvents()  # Update UI
                    
                    # Read large files in chunks to avoid memory issues
                    content = self._read_file_robust(file_path)
                    
                    # Update splash for tree building phase
                    splash.show_message(f"Building tree structure...")
                    QApplication.processEvents()
                else:
                    # Read small files using robust reader too (to handle encodings)
                    content = self._read_file_robust(file_path)
                
                print(f"DEBUG: Content read, length: {len(content)}")
                
                # Set content first (this is fast)
                self.xml_editor.set_content(content)
                print("DEBUG: Content set to editor")

                
                # For large files (>1MB), defer tree building
                file_size_mb = file_size / (1024 * 1024)
                if file_size_mb > 1.0:
                    # Close splash before deferring
                    if splash:
                        splash.close()
                        splash = None
                    
                    self.status_label.setText(f"File loaded. Building tree in background...")
                    QApplication.processEvents()
                    
                    # Defer tree building to allow UI to be responsive
                    # Optimization: Call populate_tree directly with file_path to use lxml fast path
                    if self.toggle_update_tree_view_action.isChecked():
                        QTimer.singleShot(100, lambda: self.xml_tree.populate_tree(content, show_progress=True, file_path=file_path))
                    else:
                        self.status_label.setText(f"File loaded. Tree building skipped (Spartan Mode).")
                else:
                    # Build tree immediately for smaller files
                    if self.toggle_update_tree_view_action.isChecked():
                        self.xml_tree.populate_tree(content, show_progress=True, file_path=file_path)
                    else:
                        self.xml_tree.clear()
                        self.status_label.setText(f"File loaded. Tree building skipped (Spartan Mode).")
                    
                    # Close splash after tree is built
                    if splash:
                        splash.close()
                        splash = None
                    
                    self._finalize_open_file(file_path)
                
                # Apply saved highlighter visibility settings
                self._apply_highlighter_settings()
                
            except Exception as e:
                if splash:
                    splash.close()
                QMessageBox.critical(self, "Error", f"Failed to open file: {str(e)}")
                self.status_label.setText("Ready")
    
    def reread_file(self):
        """Reload the current file from disk, discarding unsaved changes."""
        if not self.current_file:
            QMessageBox.information(self, "Reread File", "No file is currently open.")
            return

        if self.xml_editor.document().isModified():
            reply = QMessageBox.question(
                self, "Reread File",
                "File has unsaved changes. Rereading will discard them.\nAre you sure?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # Reload using open_file logic
        self.open_file(self.current_file)
        self.status_label.setText(f"File reloaded: {self.current_file}")

    def rename_file(self):
        """Rename the current file on disk."""
        if not self.current_file or not os.path.exists(self.current_file):
            QMessageBox.warning(self, "Rename Error", "No file is currently active or file does not exist on disk.")
            return
            
        old_path = self.current_file
        
        # Prompt for new name
        new_path, _ = QFileDialog.getSaveFileName(
            self, "Rename File", old_path, "XML Files (*.xml);;All Files (*.*)"
        )
        
        if not new_path or os.path.abspath(new_path) == os.path.abspath(old_path):
            return
            
        try:
            # Rename on disk
            os.rename(old_path, new_path)
            
            # Update internal state
            self.current_file = new_path
            self.xml_editor.file_path = new_path
            
            # Update UI
            self._update_window_title()
            if hasattr(self, 'tab_widget') and self.tab_widget:
                idx = self.tab_widget.indexOf(self.xml_editor)
                if idx >= 0:
                    self.tab_widget.setTabText(idx, os.path.basename(new_path))
                    self.tab_widget.setTabToolTip(idx, new_path)
            
            # Update recent files
            if old_path in self.recent_files:
                self.recent_files.remove(old_path)
            self._add_to_recent_files(new_path) # This saves and updates menu
            
            self.status_label.setText(f"File renamed to: {new_path}")
            
        except OSError as e:
            QMessageBox.critical(self, "Rename Error", f"Failed to rename file:\n{e}")

    def open_containing_folder(self):
        """Open the folder containing the current file."""
        if not self.current_file:
             QMessageBox.information(self, "Open Folder", "No file is currently open.")
             return
             
        path_to_show = os.path.abspath(self.current_file)
        
        try:
            if os.name == 'nt':
                # Windows: select file in explorer
                subprocess.Popen(['explorer', '/select,', path_to_show])
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', '-R', path_to_show])
            else:
                # Linux/Unix
                folder = os.path.dirname(path_to_show)
                subprocess.Popen(['xdg-open', folder])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open folder:\n{e}")

    def _read_file_robust(self, file_path: str) -> str:
        """Read files efficiently using chunked reading with encoding fallback"""
        chunk_size = 64 * 1024  # 64KB chunks
        
        # Attempt 1: UTF-8
        try:
            content_parts = []
            with open(file_path, 'r', encoding='utf-8') as file:
                while True:
                    chunk = file.read(chunk_size)
                    if not chunk:
                        break
                    content_parts.append(chunk)
            return ''.join(content_parts)
        except Exception:
            # If UTF-8 fails (UnicodeDecodeError or other), fall back to CP1251
            pass
            
        # Attempt 2: CP1251
        try:
            content_parts = []
            with open(file_path, 'r', encoding='cp1251') as file:
                while True:
                    chunk = file.read(chunk_size)
                    if not chunk:
                        break
                    content_parts.append(chunk)
            return ''.join(content_parts)
        except Exception as e:
            raise Exception(f"Failed to read file with any encoding: {str(e)}")
    
    
    def _open_zip_workflow(self, zip_path: str):
        """Handle opening of a zip file: detect XMLs, prompt user, extract to temp."""
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                # List XML files
                xml_files = [f for f in z.namelist() if f.lower().endswith('.xml')]
            
            if not xml_files:
                QMessageBox.warning(self, "Zip Error", "No XML files found in this archive.")
                return

            selected_arcname = None
            if len(xml_files) == 1:
                selected_arcname = xml_files[0]
            else:
                # Load default preference
                settings = QSettings("visxml.net", "LotusXmlEditor")
                default_pattern = settings.value("zip_default_file_pattern", "ExchangeRules.xml")
                
                default_index = 0
                found = False
                
                # 1. Try saved preference
                if default_pattern:
                    for i, fname in enumerate(xml_files):
                        if fname == default_pattern:
                            default_index = i
                            found = True
                            break
                
                # 2. Fallback to ExchangeRules.xml if preference not found
                if not found and default_pattern != "ExchangeRules.xml":
                     for i, fname in enumerate(xml_files):
                        if fname == "ExchangeRules.xml":
                            default_index = i
                            break
                
                # Let user choose
                item, ok = QInputDialog.getItem(
                    self, "Select XML from Archive", 
                    "Found multiple XML files. Select one to open:", 
                    xml_files, default_index, False
                )
                if ok and item:
                    selected_arcname = item
                    # Save preference
                    settings.setValue("zip_default_file_pattern", item)
            
            if not selected_arcname:
                return

            # Use shared method to open the item
            self._open_zip_item(zip_path, selected_arcname)

        except Exception as e:
            QMessageBox.critical(self, "Zip Error", f"Failed to open zip archive: {e}")
            
    def _open_zip_item(self, zip_path: str, arc_name: str):
        """Extract and open a specific file from a zip archive"""
        try:
            # Create temp directory
            temp_dir = tempfile.mkdtemp(prefix="lotus_lxe_")
            # Extract
            with zipfile.ZipFile(zip_path, 'r') as z:
                z.extract(arc_name, path=temp_dir)
            
            extracted_path = os.path.join(temp_dir, arc_name)
            
            # Open the extracted file
            self.open_file(extracted_path)
            
            # Set state to track origin
            zip_source = {
                'zip_path': zip_path,
                'arc_name': arc_name,
                'temp_dir': temp_dir
            }
            self.current_zip_source = zip_source
            
            # Also set on the editor widget for persistence
            if hasattr(self, 'xml_editor') and self.xml_editor:
                self.xml_editor.zip_source = zip_source
            
            # Update title to show context
            self._update_window_title()
            
        except Exception as e:
            QMessageBox.critical(self, "Zip Error", f"Failed to extract file from zip: {e}")
    
    def save_file(self):
        """Save current file"""
        if not self.current_file:
            self.save_file_as()
            return

        # Check if we are in Zip mode
        # Use editor's zip_source if available, otherwise fallback to MainWindow's
        zip_source = getattr(self.xml_editor, 'zip_source', None)
        if not zip_source:
             zip_source = self.current_zip_source

        if zip_source and self.current_file.startswith(zip_source['temp_dir']):
            # Save to temp first
            try:
                content = self.xml_editor.get_content()
                with open(self.current_file, 'w', encoding='utf-8') as file:
                    file.write(content)
                
                # Update Zip
                zip_path = zip_source['zip_path']
                arc_name = zip_source['arc_name']
                
                # Re-packaging approach for safety (standard "update zip" pattern):
                # 1. Create new temp zip
                # 2. Copy all files from old zip to new zip, EXCEPT the one we are updating.
                # 3. Add the updated file.
                # 4. Replace old zip with new zip.
                
                temp_zip_fd, temp_zip_path = tempfile.mkstemp(suffix=".zip")
                os.close(temp_zip_fd)
                
                try:
                    with zipfile.ZipFile(zip_path, 'r') as zin:
                        with zipfile.ZipFile(temp_zip_path, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
                            zout.comment = zin.comment # preserve comment
                            for item in zin.infolist():
                                if item.filename != arc_name:
                                    zout.writestr(item, zin.read(item.filename))
                            # Now add our updated file
                            zout.write(self.current_file, arc_name)
                    
                    # Replace original
                    shutil.move(temp_zip_path, zip_path)
                    
                    self.status_label.setText(f"Saved to Archive: {os.path.basename(zip_path)}")
                
                except Exception as e:
                    if os.path.exists(temp_zip_path):
                        os.remove(temp_zip_path)
                    raise e
            
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update zip archive: {str(e)}")
            return
        
        try:
            content = self.xml_editor.get_content()
            with open(self.current_file, 'w', encoding='utf-8') as file:
                file.write(content)
            
            self.xml_editor.document().setModified(False)
            self.status_label.setText(f"Saved: {self.current_file}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save file: {str(e)}")
    
    def save_file_as(self):
        """Save file as"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save XML File", "", "XML Files (*.xml);;All Files (*.*)"
        )
        
        if file_path:
            # Saving as a new file breaks the link to the zip
            self.current_zip_source = None
            self.current_file = file_path
            self.save_file()
            self._update_window_title()
    
    def undo(self):
        """Undo last action"""
        self.xml_editor.undo()
    
    def redo(self):
        """Redo last action"""
        self.xml_editor.redo()
    
    def show_find_dialog(self):
        """Show find dialog"""
        dialog = FindDialog(self)
        
        # Check for selected text in active editor
        selected_text = ""
        try:
            if hasattr(self, 'xml_editor') and self.xml_editor:
                if self.xml_editor.hasSelectedText():
                    selected_text = self.xml_editor.selectedText()
        except Exception:
            pass
            
        # Pre-fill with selected text or last search params
        if selected_text:
            dialog.find_input.setCurrentText(selected_text)
            # Restore other options from last search
            if self.last_search_params:
                try:
                    dialog.case_sensitive.setChecked(self.last_search_params.get('case_sensitive', False))
                    dialog.whole_word.setChecked(self.last_search_params.get('whole_word', False))
                    dialog.use_regex.setChecked(self.last_search_params.get('use_regex', False))
                except Exception:
                    pass
        elif self.last_search_params:
            try:
                if 'text' in self.last_search_params:
                    dialog.find_input.setCurrentText(self.last_search_params['text'])
                dialog.case_sensitive.setChecked(self.last_search_params.get('case_sensitive', False))
                dialog.whole_word.setChecked(self.last_search_params.get('whole_word', False))
                dialog.use_regex.setChecked(self.last_search_params.get('use_regex', False))
            except Exception:
                pass
        
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
            if not self.xml_editor.hasSelectedText():
                # Ensure selection for the current search index
                self._navigate_to_search_result(self.current_search_index if self.current_search_index >= 0 else 0)
            
            # Replace logic
            self.xml_editor.replaceSelectedText(replace_text)
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
            content = self.xml_editor.text()
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
                self.xml_editor.setText(new_content)
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

    def show_settings_dialog(self):
        """Show settings dialog"""
        try:
            dialog = SettingsDialog(self)
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(self, "Settings Error", f"Failed to open settings: {e}")
    
    def show_hotkey_help(self):
        """Show a dialog with a complete hotkey reference grouped by categories."""
        try:
            from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem
            
            dlg = QDialog(self)
            dlg.setWindowTitle("Keyboard Shortcuts")
            dlg.setModal(True)
            dlg.resize(600, 550)
            
            layout = QVBoxLayout()
            layout.setContentsMargins(8, 8, 8, 8)
            layout.setSpacing(6)
            
            label = QLabel("These shortcuts are available across menus and the editor:")
            label.setWordWrap(True)
            label.setStyleSheet("font-size: 11px; margin-bottom: 4px;")
            layout.addWidget(label)
            
            # Use QTreeWidget for better organization
            tree = QTreeWidget()
            tree.setHeaderHidden(True)
            tree.setRootIsDecorated(True)
            tree.setIndentation(12)
            
            # Define categories and shortcuts
            categories = [
                ("File Operations", [
                    "Ctrl+N - New",
                    "Ctrl+O - Open",
                    "Ctrl+S - Save",
                    "Ctrl+Shift+S - Save As / Split XML (context)",
                    "Ctrl+R - Reread from Disk",
                    "Ctrl+F2 - Rename File",
                    "Alt+Shift+O - Open Containing Folder",
                    "Ctrl+Q - Exit"
                ]),
                ("Editing Operations", [
                    "Ctrl+Z - Undo",
                    "Ctrl+Y - Redo",
                    "Ctrl+F - Find...",
                    "F3 - Find Next",
                    "Shift+F3 - Find Previous",
                    "Ctrl+H - Replace...",
                    "Ctrl+Shift+H - Replace All",
                    "Ctrl+G - Go to Line...",
                    "Ctrl+L - Toggle Line Numbers / Delete Line (context)",
                    "Ctrl+/ - Toggle comment (context sensitive)",
                    "Ctrl+\\ - Cycle syntax language",
                    "Ctrl+Shift+Up - Move lines up",
                    "Ctrl+Shift+Down - Move lines down",
                    "Ctrl+Shift+K - Escape XML Entities (selection)",
                    "Ctrl+Alt+U - Unescape XML Entities (selection)"
                ]),
                ("Bookmarks", [
                    "Ctrl+B - Toggle Bookmark at cursor",
                    "Ctrl+Shift+B - Clear all bookmarks / Tab Bar Autohide (context)",
                    "F2 - Next Bookmark",
                    "Shift+F2 - Previous Bookmark",
                    "Alt+F2 - Toggle Bookmark (menu)"
                ]),
                ("XPath Links", [
                    "Ctrl+F11 - Copy XPath of current position to Links",
                    "F12 - Navigate to XPath from Links tab"
                ]),
                ("Numbered Bookmarks", [
                    "Ctrl+Shift+1..9 - Set numbered bookmark",
                    "Ctrl+1..9 - Go to numbered bookmark"
                ]),
                ("XML Operations", [
                    "Ctrl+Shift+F - Format XML",
                    "Ctrl+Shift+V - Validate XML",
                    "Ctrl+Shift+T - Find in Tree / Toolbar Autohide (context)",
                    "Ctrl+Shift+C - Copy Current Node with Subnodes",
                    "Ctrl+Shift+N - Open Node in New Window",
                    "Ctrl+E - Export Tree",
                    "F5 - Rebuild Tree with auto-close tags",
                    "Shift+F11 - Toggle Update Tree on Tab Switch"
                ]),
                ("Code Folding", [
                    "Ctrl+Shift+[ - Fold current element",
                    "Ctrl+Shift+] - Unfold current element",
                    "Ctrl+Shift+U - Unfold all",
                    "Alt+2..9 - Fold all elements at level N"
                ]),
                ("Navigation & Selection", [
                    "Ctrl+T - Find in Tree (editor)",
                    "Shift+F4 - Select XML node near cursor",
                    "F4 - Select XML content (inner)",
                    "Ctrl+F4 - Select root element",
                    "Ctrl+Alt+F4 - Cycle top-level elements",
                    "F6 - Move selection to new tab with link",
                    "Shift+F5 - Replace link with edited text from separate tab",
                    "Ctrl+Up - Navigate Tree Up",
                    "Ctrl+Down - Navigate Tree Down",
                    "F8 - Open selected fragment in new window",
                    "Alt+←/→/↑/↓ - Tree-backed navigation",
                    "Ctrl+] - Jump to matching closing tag",
                    "Ctrl+[ - Jump to matching opening tag"
                ]),
                ("View", [
                    "F9 - Toggle Bottom Panel",
                    "Ctrl+M - XML Metro Navigator",
                    "Ctrl+Shift+M - Open Multicolumn Tree (Experimental)",
                    "Ctrl+Shift+E - Toggle Tree Column Header Autohide",
                    "Ctrl+Shift+H - Toggle Tree Header Autohide / Replace All (context)"
                ]),
                ("Binary File Transfer", [
                    "Win+Ctrl+Ins - Encode file from clipboard to base64 text",
                    "Win+Shift+Ins - Decode base64 text from clipboard to file"
                ]),
                ("Tree Operations", [
                    "Delete - Hide current node recursively (visual filter)",
                    "Ctrl+Delete - Delete XML Block (Model)",
                    "Ctrl+/ - Hide XML Block (Comment out)",
                    "Right Click - Context Menu (Delete/Hide Block)"
                ])
            ]
            
            # Populate tree
            for category_name, shortcuts in categories:
                category_item = QTreeWidgetItem(tree)
                category_item.setText(0, f"📁 {category_name}")
                category_item.setExpanded(True)
                
                for shortcut in shortcuts:
                    item = QTreeWidgetItem(category_item)
                    item.setText(0, f"  {shortcut}")
            
            tree.resizeColumnToContents(0)
            layout.addWidget(tree)
            
            # Close button
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            buttons.rejected.connect(dlg.reject)
            layout.addWidget(buttons)
            
            dlg.setLayout(layout)
            dlg.exec()
        except Exception as e:
            try:
                QMessageBox.information(self, "Shortcuts", f"Error loading help: {e}")
            except Exception:
                print(f"Error showing hotkey help: {e}")
    
    def show_about_dialog(self):
        """Show About dialog with application and file information"""
        try:
            current_file = self.current_file if hasattr(self, 'current_file') else None
            dialog = AboutDialog(self, current_file)
            dialog.exec()
        except Exception as e:
            QMessageBox.warning(self, "About Error", f"Failed to show About dialog: {e}")
    
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
        # Only check for selection if editor has focus to avoid crashes
        try:
            has_selection = False
            selected_text = ""
            
            if self.xml_editor.hasFocus():
                has_selection = self.xml_editor.hasSelectedText()
                if has_selection:
                    selected_text = self.xml_editor.selectedText()
            
            if has_selection and len(selected_text) > 0:
                # Check if selected text is different from current search term
                # If it's the same, just move to next occurrence instead of restarting search
                current_search_text = self.last_search_params.get('text', '') if self.last_search_params else ''
                if selected_text != current_search_text:
                    # New search term - start fresh search
                    self.last_search_term = selected_text
                    self.find_text({
                        'text': selected_text,
                        'case_sensitive': False,
                        'whole_word': False,
                        'use_regex': False
                    })
                    return
        except Exception as e:
            # If there's any issue checking selection, just continue with existing search
            print(f"Error checking selection in find_next: {e}")

        if not self.last_search_results or self.current_search_index == -1:
            # No previous search and no selection, show find dialog
            self.show_find_dialog()
            return
        
        # Move to next result
        self.current_search_index = (self.current_search_index + 1) % len(self.last_search_results)
        self._navigate_to_search_result(self.current_search_index)
    
    def find_previous(self):
        """Find previous occurrence (Shift+F3)"""
        if not self.last_search_results or self.current_search_index == -1:
            # No previous search, show find dialog
            self.show_find_dialog()
            return
        
        # Move to previous result (wrap around to end if at beginning)
        self.current_search_index = (self.current_search_index - 1) % len(self.last_search_results)
        self._navigate_to_search_result(self.current_search_index)
    
    def _navigate_to_search_result(self, result_index: int):
        """Navigate to a specific search result"""
        if not self.last_search_results or result_index < 0 or result_index >= len(self.last_search_results):
            print(f"DEBUG: Cannot navigate - invalid index {result_index} or no results")
            return
        
        line_num, col_start, col_end = self.last_search_results[result_index]
        print(f"DEBUG: Navigating to result {result_index}: line {line_num}, col {col_start}-{col_end}")
        
        line_idx = line_num - 1
        # QScintilla uses byte offsets for columns
        # We need to convert character indices to byte offsets
        # Get the line text first
        line_text = self.xml_editor.text(line_idx)
        
        # Calculate byte offsets
        byte_start = len(line_text[:col_start].encode('utf-8'))
        byte_end = len(line_text[:col_end].encode('utf-8'))
        
        self.xml_editor.setSelection(line_idx, byte_start, line_idx, byte_end)
        self.xml_editor.ensureLineVisible(line_idx)
        self.xml_editor.setFocus()
        
        # Update status
        self.status_label.setText(f"Found match {result_index + 1} of {len(self.last_search_results)} at line {line_num}")
    
    def goto_line(self, line_number: int):
        """Go to specific line"""
        if line_number <= 0:
            return
        
        self.xml_editor.setCursorPosition(line_number - 1, 0)
        self.xml_editor.ensureCursorVisible()
        self.xml_editor.setFocus()

    def goto_line_and_column(self, line_number: int, column: int):
        """Go to specific line and column within the editor."""
        if line_number <= 0:
            return
            
        self.xml_editor.setCursorPosition(line_number - 1, column if column > 0 else 0)
        self.xml_editor.ensureCursorVisible()
        self.xml_editor.setFocus()
    
    def find_in_tree(self):
        """Find current line in tree view (Ctrl+T functionality)"""
        try:
            # Get current cursor position
            line, _ = self.xml_editor.getCursorPosition()
            current_line = line + 1
            
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
    
    def remove_empty_lines(self):
        """Remove empty lines from selected text"""
        editor = self.xml_editor
        
        if not editor.hasSelectedText():
            self.status_label.setText("No text selected")
            return
        
        selected_text = editor.selectedText()
        
        if not selected_text:
            return

        lines = selected_text.split('\n')
        # Filter out empty lines or lines with only whitespace
        non_empty_lines = [line for line in lines if line.strip()]
        
        # Join with newlines
        new_text = '\n'.join(non_empty_lines)
        
        if new_text == selected_text:
            self.status_label.setText("No empty lines found in selection")
            return
            
        # Replace
        editor.replaceSelectedText(new_text)
        
        self.status_label.setText("Removed empty lines from selection")

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
    
    def show_progress_tip(self, text):
        """Show a floating progress tip"""
        if hasattr(self, '_progress_popup') and self._progress_popup:
             try:
                 self._progress_popup.close()
                 self._progress_popup.deleteLater()
             except Exception:
                 pass
        
        self._progress_popup = ProgressPopup(text, self)
        # Position at center of window
        geo = self.geometry()
        center = geo.center()
        # Adjust for popup size (approx)
        self._progress_popup.move(center.x() - 100, center.y() - 20)
        self._progress_popup.show()
        QApplication.processEvents()

    def hide_progress_tip(self):
        """Hide the progress tip"""
        if hasattr(self, '_progress_popup') and self._progress_popup:
             try:
                 self._progress_popup.close()
                 self._progress_popup.deleteLater()
             except Exception:
                 pass
             self._progress_popup = None

    def _on_autoclose_finished(self, fixed_content, modified):
        """Handle completion of auto-close worker"""
        try:
            # Check if content was modified
            if modified:
                # Update editor with fixed content
                if hasattr(self, 'xml_editor'):
                    self.xml_editor.set_content(fixed_content)
                    self.auto_fold_special_tags()
                self.status_label.setText("Auto-closed unclosed tags and rebuilt tree")
            else:
                self.status_label.setText("Rebuilt tree (no unclosed tags found)")
            
            # Rebuild the tree (forcing async to keep UI responsive)
            # Update popup text
            if hasattr(self, '_progress_popup') and self._progress_popup:
                self._progress_popup.label.setText("Populating tree...")
                QApplication.processEvents()
                
            self.xml_tree.populate_tree(fixed_content, show_progress=False, force_async=True)
            
            # We need to know when populate_tree finishes to hide the popup.
            # XmlTreeWidget stores the worker in self._parse_worker.
            if hasattr(self.xml_tree, '_parse_worker') and self.xml_tree._parse_worker:
                 self.xml_tree._parse_worker.finished.connect(self.hide_progress_tip)
            else:
                 self.hide_progress_tip()

            # Reset caches and optionally rebuild index
            try:
                self.path_line_cache = {}
                lines_count = len(fixed_content.split('\n')) if fixed_content else 0
                if self.sync_index_enabled and lines_count < 50000:
                    self._build_path_line_index(fixed_content)
            except Exception:
                pass
                
        except Exception as e:
            self.hide_progress_tip()
            QMessageBox.critical(self, "Error", f"Failed to rebuild tree: {str(e)}")
            self.status_label.setText(f"Error rebuilding tree: {str(e)}")

    def rebuild_tree_with_autoclose(self):
        """Rebuild tree from editor content with auto-close unclosed tags"""
        content = self.xml_editor.get_content()
        if not content.strip():
            self.status_label.setText("No content to rebuild")
            return
        
        try:
            # Hide rebuild indicator
            self._tree_needs_rebuild = False
            if hasattr(self, 'tree_rebuild_indicator'):
                self.tree_rebuild_indicator.setVisible(False)
            
            self.show_progress_tip("Auto-closing tags...")
            self.status_label.setText("Rebuilding tree...")
            
            # Start worker
            self.autoclose_worker = AutoCloseWorker(content, self.xml_service)
            self.autoclose_worker.finished.connect(self._on_autoclose_finished)
            self.autoclose_worker.start()
            
        except Exception as e:
            self.hide_progress_tip()
            QMessageBox.critical(self, "Error", f"Failed to start rebuild: {str(e)}")
            self.status_label.setText(f"Error starting rebuild: {str(e)}")
    
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
        """Handle content change with debounce"""
        # Suppress handling during programmatic file loads to avoid repeated rebuilds
        if getattr(self, '_loading_file', False):
            return
        
        # Check if timer is initialized
        if not hasattr(self, 'tree_update_timer'):
            return
        
        # Check if auto rebuild is enabled
        if not getattr(self, 'auto_rebuild_tree', True):
            # Show indicator that tree needs rebuild
            self._tree_needs_rebuild = True
            if hasattr(self, 'tree_rebuild_indicator'):
                self.tree_rebuild_indicator.setVisible(True)
            return
        
        # Store content and restart debounce timer
        self._pending_tree_content = self.xml_editor.get_content()
        self.tree_update_timer.stop()
        self.tree_update_timer.start(self.tree_update_debounce_interval)
    
    def _debounced_tree_update(self):
        """Actually update the tree after debounce period"""
        if self._pending_tree_content is None:
            return
        
        content = self._pending_tree_content
        self._pending_tree_content = None
        
        self.xml_tree.populate_tree(content, file_path=None)
        
        # Notify metro navigator if it's open
        if hasattr(self, 'metro_window') and self.metro_window and self.metro_window.isVisible():
            try:
                self.metro_window.show_refresh_button()
            except Exception as e:
                print(f"Error notifying metro navigator: {e}")
        
        # Optimization: If lxml is available, the tree nodes already have line numbers (from sourceline).
        # We don't need to rebuild the independent index unless we're in fallback mode.
        try:
            # Check availability via XmlService import or local flag
            try:
                from lxml import etree
                lxml_available = True
            except ImportError:
                lxml_available = False

            if lxml_available:
                 # Skip redundant indexing
                 self.sync_index_enabled = False
                 self._debug_print("DEBUG: Using direct lxml sourceline support (skipping separate index)")
            else:
                # Fallback logic for ElementTree
                lines_count = len(content.split('\n')) if content else 0
                self.sync_index_enabled = lines_count > 8000
                self.sync_cache_enabled = lines_count > 8000
                self.path_line_cache = {}
                self.path_line_index = {}
                if self.sync_index_enabled:
                    self._build_path_line_index(content)
                    self._debug_print(f"DEBUG: Rebuilt index after content change, entries={len(self.path_line_index)}")
                else:
                    self._debug_print("DEBUG: Index/cache disabled after content change (small file)")
        except Exception as e:
            self._debug_print(f"DEBUG: Error handling index/cache on content change: {e}")
        
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
        # Only if visible and not in Spartan Mode (to avoid heavy get_content calls)
        is_spartan = getattr(self, 'spartan_mode', False)
        if hasattr(self, 'breadcrumb_label') and self.breadcrumb_label.isVisible() and not is_spartan:
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
        """Get the proper XPath of the element at the given line number using XML parsing with line numbers"""
        self._debug_print(f"DEBUG: _get_element_path_at_line called with line_number={line_number}")
        
        import xml.sax
        import io

        class PathFinder(xml.sax.ContentHandler):
            def __init__(self, target_line):
                self.target_line = target_line
                self.best_path = ""
                self.stack = [] # (tag, path, start_line, child_counters)
                self.locator = None
                self.found = False

            def setDocumentLocator(self, locator):
                self.locator = locator

            def startElement(self, name, attrs):
                if self.found:
                    return

                start_line = self.locator.getLineNumber()
                
                # Calculate path
                if not self.stack:
                    # Root element
                    path = f"/{name}[1]"
                    child_counters = {}
                    self.stack.append((name, path, start_line, child_counters))
                else:
                    parent_tag, parent_path, parent_start, parent_counters = self.stack[-1]
                    
                    # Update parent's child counters
                    count = parent_counters.get(name, 0) + 1
                    parent_counters[name] = count
                    
                    path = f"{parent_path}/{name}[{count}]"
                    child_counters = {}
                    self.stack.append((name, path, start_line, child_counters))

            def endElement(self, name):
                if self.found:
                    return

                if not self.stack:
                    return

                tag, path, start_line, _ = self.stack.pop()
                end_line = self.locator.getLineNumber()

                # Check if this element covers the target line
                # Note: SAX line numbers are 1-based.
                if start_line <= self.target_line <= end_line:
                    # Found a candidate!
                    # Since we process children before parents (in endElement),
                    # the first match we hit is the deepest one.
                    self.best_path = path
                    self.found = True

        handler = PathFinder(line_number)
        parser = xml.sax.make_parser()
        parser.setContentHandler(handler)
        
        try:
            parser.parse(io.StringIO(xml_content))
        except Exception as e:
            # If we found the path, we might have stopped parsing early (if we optimized)
            # But here we parse full to be safe, or we could raise exception to stop
            if handler.best_path:
                self._debug_print(f"DEBUG: Resolved path (early exit): {handler.best_path}")
                return handler.best_path
            self._debug_print(f"DEBUG: SAX Parsing error: {e}")
            return ""
            
        if handler.best_path:
            self._debug_print(f"DEBUG: Resolved path: {handler.best_path}")
            return handler.best_path
            
        self._debug_print(f"DEBUG: No element found containing line {line_number}")
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
            line = 0
            line, _ = self.xml_editor.getCursorPosition()
            line += 1
                
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
        self._debug_print(f"DEBUG: _find_element_line_by_path called with path: {element_path}")

        if not element_path or element_path == "/":
            self._debug_print(f"DEBUG: Returning line 1 for root element")
            return 1  # Root element

        # Cache fast path
        if self.sync_cache_enabled and element_path in self.path_line_cache:
            line_cached = self.path_line_cache[element_path]
            self._debug_print(f"DEBUG: Cache hit for {element_path} -> line {line_cached}")
            return line_cached

        lines = content.split('\n')
        path_parts = element_path.split('/')[1:]  # Remove leading empty string

        if not path_parts:
            self._debug_print(f"DEBUG: No path parts, returning 0")
            return 0

        self._debug_print(f"DEBUG: Processing {len(lines)} lines for path parts: {path_parts}")

        # lxml index lookup
        if self.sync_index_enabled and self._sync_index_available:
            if element_path in self.path_line_index:
                line = self.path_line_index[element_path]
                self._debug_print(f"DEBUG: Index hit for {element_path} -> line {line}")
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
            self._debug_print(f"DEBUG: Anchored search from parent path {parent_path} at line {parent_line}")
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
                                    self._debug_print(f"DEBUG: Anchored match (attr) at line {i}")
                                    if self.sync_cache_enabled:
                                        self.path_line_cache[element_path] = i
                                    return i
                            elif exp_idx == tag_index:
                                if current_depth == len(relative_parts):
                                    self._debug_print(f"DEBUG: Anchored match at line {i}")
                                    if self.sync_cache_enabled:
                                        self.path_line_cache[element_path] = i
                                    return i
                            elif exp_idx == 1 and not exp_attr and tag_index == 1:
                                if current_depth == len(relative_parts):
                                    self._debug_print(f"DEBUG: Anchored simple match at line {i}")
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
                                    self._debug_print(f"DEBUG: Found target element by attribute at line {i}")
                                    if self.sync_cache_enabled:
                                        self.path_line_cache[element_path] = i
                                    return i
                            elif exp_idx == tag_index:
                                if current_depth == len(path_parts):
                                    self._debug_print(f"DEBUG: Found target element at line {i}")
                                    if self.sync_cache_enabled:
                                        self.path_line_cache[element_path] = i
                                    return i
                            elif exp_idx == 1 and not exp_attr and tag_index == 1:
                                if current_depth == len(path_parts):
                                    self._debug_print(f"DEBUG: Found target element by simple match at line {i}")
                                    if self.sync_cache_enabled:
                                        self.path_line_cache[element_path] = i
                                    return i
                    # push if not self-closing
                    if not self_closing:
                        element_stack.append((tn, tag_index))

        self._debug_print(f"DEBUG: Element not found, returning 0")
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
            
            # QScintilla highlighting using Indicators
            if isinstance(self.xml_editor, QsciScintilla):
                INDIC_BLOCK = 10 # Custom indicator for block highlight
                self.xml_editor.clearIndicatorRange(0, 0, self.xml_editor.lines(), self.xml_editor.lineLength(self.xml_editor.lines()-1), INDIC_BLOCK)
                self.xml_editor.indicatorDefine(QsciScintilla.StraightBoxIndicator, INDIC_BLOCK)
                self.xml_editor.setIndicatorForegroundColor(QColor(255, 140, 0), INDIC_BLOCK)
                self.xml_editor.setIndicatorAlpha(INDIC_BLOCK, 60)
                self.xml_editor.setIndicatorOutlineAlpha(INDIC_BLOCK, 255)
                self.xml_editor.setIndicatorDrawUnder(True, INDIC_BLOCK)
                l_start = start_line - 1
                l_end = end_line - 1
                len_end = self.xml_editor.lineLength(l_end)
                self.xml_editor.fillIndicatorRange(l_start, 0, l_end, len_end, INDIC_BLOCK)
                
                # Update status bar
                self.status_label.setText(f"Selected {xml_node.name} at line {start_line} ({line_count} line{'s' if line_count != 1 else ''})")
                print(f"HIGHLIGHT: Element {tag_name} from line {start_line} to {end_line} ({line_count} lines)")
                return

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
    
    def _get_file_state_key(self, file_path=None, zip_source=None):
        """Generate unique key for file state storage"""
        if zip_source:
            # Use zip path and internal arc name as key
            return f"{zip_source['zip_path']}|{zip_source['arc_name']}"
        if file_path:
            return file_path
        return None

    def _load_file_states(self):
        """Load file states from persistent storage"""
        self.file_states = {}
        try:
            # Load centralized file
            state_path = os.path.join(os.path.expanduser("~"), ".visxml_file_states.json")
            if os.path.exists(state_path):
                with open(state_path, 'r', encoding='utf-8') as f:
                    self.file_states = json.load(f)
        except Exception as e:
            print(f"Error loading file states: {e}")

    def _save_file_states(self):
        """Save file states to persistent storage"""
        try:
            from PyQt6.QtCore import QSettings
            
            # First, update state for all currently open tabs
            if hasattr(self, 'tab_widget'):
                for i in range(self.tab_widget.count()):
                    widget = self.tab_widget.widget(i)
                    if isinstance(widget, XmlEditorWidget):
                        self._capture_editor_state(widget)

            # Centralized save
            state_path = os.path.join(os.path.expanduser("~"), ".visxml_file_states.json")
            with open(state_path, 'w', encoding='utf-8') as f:
                json.dump(self.file_states, f, indent=2)
            
            # Sidecar save (if enabled)
            settings = QSettings("visxml.net", "LotusXmlEditor")
            use_sidecar = settings.value("flags/store_settings_in_file_dir", False, type=bool)
            
            if use_sidecar:
                 for key, state in self.file_states.items():
                     if "|" not in key and os.path.exists(key): # Regular file
                         try:
                             sidecar_path = key + ".visxml_state"
                             # Check if we have write permission
                             if os.access(os.path.dirname(sidecar_path), os.W_OK):
                                 with open(sidecar_path, 'w', encoding='utf-8') as f:
                                     json.dump(state, f, indent=2)
                         except Exception:
                             pass
        except Exception as e:
            print(f"Error saving file states: {e}")

    def _capture_editor_state(self, editor):
        """Capture state from an editor widget"""
        try:
            from PyQt6.QtCore import QSettings
            
            # Check if feature is enabled
            settings = QSettings("visxml.net", "LotusXmlEditor")
            save_cursor = settings.value("flags/save_cursor_position", True, type=bool)
            
            if not save_cursor:
                return

            key = self._get_file_state_key(getattr(editor, 'file_path', None), getattr(editor, 'zip_source', None))
            if not key:
                return
            
            state = {
                'timestamp': QDateTime.currentDateTime().toSecsSinceEpoch()
            }
            
            # Capture state using QScintilla API
            line, index = editor.getCursorPosition()
            state['cursor_line'] = line
            state['cursor_index'] = index
            state['first_visible_line'] = editor.SendScintilla(QsciScintilla.SCI_GETFIRSTVISIBLELINE)
            
            if editor.hasSelectedText():
                # getSelection returns (lineFrom, indexFrom, lineTo, indexTo)
                state['selection_range'] = list(editor.getSelection())
            
            # Tree state
            save_tree = settings.value("flags/save_tree_state", False, type=bool)

            if save_tree:
                is_current = False
                if hasattr(self, 'xml_editor') and editor == self.xml_editor:
                    is_current = True
                
                if is_current and hasattr(self, 'xml_tree'):
                    current_item = self.xml_tree.currentItem()
                    if current_item and hasattr(current_item, 'xml_node'):
                         node = current_item.xml_node
                         if hasattr(node, 'path'):
                             state['tree_path'] = node.path
            
            # Merge with existing state to preserve other fields (like tree_path if not current)
            if key in self.file_states:
                existing = self.file_states[key]
                if 'tree_path' in existing and 'tree_path' not in state:
                    state['tree_path'] = existing['tree_path']

            self.file_states[key] = state
        except Exception as e:
            print(f"Error capturing editor state: {e}")

    def _restore_editor_state(self, editor):
        """Restore state to an editor widget"""
        try:
            from PyQt6.QtCore import QSettings
            
            # Check if feature is enabled
            settings = QSettings("visxml.net", "LotusXmlEditor")
            save_cursor = settings.value("flags/save_cursor_position", True, type=bool)
            
            if not save_cursor:
                return

            key = self._get_file_state_key(getattr(editor, 'file_path', None), getattr(editor, 'zip_source', None))
            if not key:
                return
            
            state = None
            if key in self.file_states:
                state = self.file_states[key]
            else:
                # Try sidecar if enabled
                use_sidecar = settings.value("flags/store_settings_in_file_dir", False, type=bool)
                
                if use_sidecar and "|" not in key and os.path.exists(key + ".visxml_state"):
                    try:
                        with open(key + ".visxml_state", 'r', encoding='utf-8') as f:
                            state = json.load(f)
                            self.file_states[key] = state # Cache it
                    except Exception:
                        pass
            
            if not state:
                return
            
            # Restore cursor/selection using QScintilla API
            # Helper to convert char offset to line/index
            def pos_from_offset(offset):
                text = editor.text()
                # Clamp offset
                if offset < 0: offset = 0
                if offset > len(text): offset = len(text)
                
                line = text.count('\n', 0, offset)
                last_nl = text.rfind('\n', 0, offset)
                index = offset if last_nl == -1 else offset - last_nl - 1
                return line, index

            if 'cursor_line' in state and 'cursor_index' in state:
                editor.setCursorPosition(state['cursor_line'], state['cursor_index'])
                
                if 'selection_range' in state:
                    lf, if_, lt, it = state['selection_range']
                    editor.setSelection(lf, if_, lt, it)
            elif 'cursor_position' in state:
                 # Legacy fallback: convert char position to line/index
                 line, index = pos_from_offset(state['cursor_position'])
                 editor.setCursorPosition(line, index)
                 
                 # Legacy selection fallback
                 if 'selection_start' in state and 'selection_end' in state:
                     start = state['selection_start']
                     end = state['selection_end']
                     if start != end:
                         l1, i1 = pos_from_offset(start)
                         l2, i2 = pos_from_offset(end)
                         editor.setSelection(l1, i1, l2, i2)
            
            if 'first_visible_line' in state:
                editor.SendScintilla(QsciScintilla.SCI_SETFIRSTVISIBLELINE, state['first_visible_line'])
            
            editor.ensureCursorVisible()

            # Restore tree state
            save_tree = settings.value("flags/save_tree_state", False, type=bool)
            
            if save_tree and 'tree_path' in state and hasattr(self, 'xml_editor') and editor == self.xml_editor:
                 # Check if tree is populated
                 tree_ready = False
                 if hasattr(self, 'xml_tree') and self.xml_tree.topLevelItemCount() > 0:
                     # Check if it's a placeholder only
                     item = self.xml_tree.topLevelItem(0)
                     if not getattr(item, 'lazy_loaded', False): # If lazy_loaded flag is False (meaning done) or not set
                         tree_ready = True
                 
                 path = state['tree_path']
                 
                 if tree_ready:
                     if hasattr(self, '_find_tree_item_by_path'):
                         tree_item = self._find_tree_item_by_path(path)
                         if tree_item:
                             self.xml_tree.setCurrentItem(tree_item)
                             parent = tree_item.parent()
                             while parent:
                                 parent.setExpanded(True)
                                 parent = parent.parent()
                             self.xml_tree.scrollToItem(tree_item)
                             return

                 # If we reached here, either tree not ready or item not found
                 self._pending_tree_path = path
        except Exception as e:
            print(f"Error restoring editor state: {e}")

    def _on_tree_built(self):
        """Handle tree built signal to restore pending tree state"""
        if self._pending_tree_path and hasattr(self, '_find_tree_item_by_path'):
            path = self._pending_tree_path
            self._pending_tree_path = None # Clear it
            
            tree_item = self._find_tree_item_by_path(path)
            if tree_item:
                self.xml_tree.setCurrentItem(tree_item)
                parent = tree_item.parent()
                while parent:
                    parent.setExpanded(True)
                    parent = parent.parent()
                self.xml_tree.scrollToItem(tree_item)

    def _save_session(self):
        """Save current session state to file"""
        # Also save persistent file states
        self._save_file_states()
        
        try:
            session = {
                'tabs': [],
                'active_tab_index': self.tab_widget.currentIndex(),
                'find_results': [],
                'last_search_params': self.last_search_params,
                'last_search_results': self.last_search_results,
                'fragment_editors': []
            }
            
            # Save tabs
            for i in range(self.tab_widget.count()):
                widget = self.tab_widget.widget(i)
                if isinstance(widget, XmlEditorWidget):
                    tab_data = {
                        'file_path': widget.file_path,
                        'bookmarks': widget.bookmarks,
                        'numbered_bookmarks': widget.numbered_bookmarks
                    }
                    
                    # Save state using QScintilla API
                    line, index = widget.getCursorPosition()
                    tab_data['cursor_line'] = line
                    tab_data['cursor_index'] = index
                    tab_data['first_visible_line'] = widget.SendScintilla(QsciScintilla.SCI_GETFIRSTVISIBLELINE)
                    if widget.hasSelectedText():
                        tab_data['selection_range'] = list(widget.getSelection())
                    
                    # Save zip source if present
                    if getattr(widget, 'zip_source', None):
                        tab_data['zip_source'] = widget.zip_source
                    
                    if widget._folded_ranges:
                         tab_data['folded_ranges'] = list(widget._folded_ranges)
                    
                    if widget.file_path or getattr(widget, 'zip_source', None):
                        session['tabs'].append(tab_data)
            
            # Save find results
            if hasattr(self, 'bottom_panel') and hasattr(self.bottom_panel, 'find_results'):
                for i in range(self.bottom_panel.find_results.count()):
                    item = self.bottom_panel.find_results.item(i)
                    session['find_results'].append(item.text())
            
            # Save fragment editors
            if hasattr(self, 'fragment_editors'):
                for dialog in self.fragment_editors:
                    if dialog.isVisible():
                        frag_data = {
                            'content': dialog.editor.toPlainText(),
                            'language': dialog.syntax_group.checkedButton().text() if dialog.syntax_group.checkedButton() else 'XML',
                            'geometry': dialog.saveGeometry().toBase64().data().decode('ascii')
                        }
                        session['fragment_editors'].append(frag_data)
                        
            session_path = os.path.join(os.path.expanduser("~"), ".lotus_xml_editor_session.json")
            with open(session_path, 'w', encoding='utf-8') as f:
                json.dump(session, f, indent=2)
                
        except Exception as e:
            print(f"Error saving session: {e}")

    def _restore_session(self):
        """Restore session state from file"""
        try:
            session_path = os.path.join(os.path.expanduser("~"), ".lotus_xml_editor_session.json")
            if not os.path.exists(session_path):
                return
                
            with open(session_path, 'r', encoding='utf-8') as f:
                session = json.load(f)
            
            # Restore tabs
            if 'tabs' in session and session['tabs']:
                # Close initial empty tab if present and unmodified
                if self.tab_widget.count() == 1:
                    widget = self.tab_widget.widget(0)
                    if isinstance(widget, XmlEditorWidget) and not widget.file_path and not widget.get_content().strip():
                        self.tab_widget.removeTab(0)
                
                for tab_data in session['tabs']:
                    file_path = tab_data.get('file_path')
                    zip_source = tab_data.get('zip_source')
                    
                    # Determine if we can open this tab
                    can_open = False
                    if zip_source and os.path.exists(zip_source['zip_path']):
                        can_open = True
                    elif file_path and os.path.exists(file_path):
                        can_open = True
                        
                    if can_open:
                        # Create new tab if needed
                        current_has_file = False
                        if hasattr(self, 'xml_editor') and self.xml_editor:
                            if self.xml_editor.file_path or getattr(self.xml_editor, 'zip_source', None):
                                current_has_file = True
                                
                        if self.tab_widget.count() == 0 or current_has_file:
                             new_editor = XmlEditorWidget()
                             
                             # Apply line numbers setting
                             show_line_numbers = self._read_flag('show_line_numbers', False)
                             new_editor.set_line_numbers_visible(show_line_numbers)
                             
                             # Apply code folding setting
                             code_folding = self._read_flag('code_folding', True)
                             new_editor.set_code_folding_enabled(code_folding)
                             
                             self.tab_widget.addTab(new_editor, "Document")
                             self.tab_widget.setCurrentWidget(new_editor)
                             # Force update of xml_editor reference since signals might be queued
                             self.xml_editor = new_editor
                             self.current_file = None
                             # Connect signals for the new editor
                             self.xml_editor.content_changed.connect(self.on_content_changed)
                             self.xml_editor.cursor_position_changed.connect(self.on_cursor_changed)
                        
                        # Open file
                        if zip_source:
                            self._open_zip_item(zip_source['zip_path'], zip_source['arc_name'])
                        else:
                            self.open_file(file_path)
                            
                        editor = self.xml_editor
                        
                        # Restore state using QScintilla API
                        # Helper to convert char offset to line/index
                        def pos_from_offset(offset):
                            text = editor.text()
                            # Clamp offset
                            if offset < 0: offset = 0
                            if offset > len(text): offset = len(text)
                            
                            line = text.count('\n', 0, offset)
                            last_nl = text.rfind('\n', 0, offset)
                            index = offset if last_nl == -1 else offset - last_nl - 1
                            return line, index

                        if 'cursor_line' in tab_data and 'cursor_index' in tab_data:
                            editor.setCursorPosition(tab_data['cursor_line'], tab_data['cursor_index'])
                            if 'selection_range' in tab_data:
                                lf, if_, lt, it = tab_data['selection_range']
                                editor.setSelection(lf, if_, lt, it)
                        elif 'cursor_position' in tab_data:
                            # Legacy fallback
                            line, index = pos_from_offset(tab_data['cursor_position'])
                            editor.setCursorPosition(line, index)
                        
                        if 'first_visible_line' in tab_data:
                            editor.SendScintilla(QsciScintilla.SCI_SETFIRSTVISIBLELINE, tab_data['first_visible_line'])
                        
                        editor.ensureCursorVisible()
                            
                        if 'bookmarks' in tab_data:
                            bookmarks = {int(k): v for k, v in tab_data['bookmarks'].items()}
                            editor.bookmarks = bookmarks
                            
                        if 'numbered_bookmarks' in tab_data:
                            editor.numbered_bookmarks = {int(k): int(v) for k, v in tab_data['numbered_bookmarks'].items()}

                        if 'folded_ranges' in tab_data:
                             editor._folded_ranges = [tuple(x) for x in tab_data['folded_ranges']]
                
                # Restore active tab
                if 'active_tab_index' in session:
                    idx = session['active_tab_index']
                    if 0 <= idx < self.tab_widget.count():
                        self.tab_widget.setCurrentIndex(idx)

            # Restore find results
            if 'find_results' in session and session['find_results']:
                self.bottom_panel.clear_find_results()
                for text in session['find_results']:
                    self.bottom_panel.add_find_result(text)
                self.last_search_results = session.get('last_search_results', [])
                self.last_search_params = session.get('last_search_params')
                if self.last_search_results:
                     self._show_bottom_panel_auto("find")

            # Restore fragment editors
            if 'fragment_editors' in session:
                for frag_data in session['fragment_editors']:
                    text = frag_data.get('content', '')
                    lang = frag_data.get('language', 'XML')
                    
                    dialog = FragmentEditorDialog(text, self.language_registry, initial_language=lang, parent=self)
                    dialog.setWindowFlags(Qt.WindowType.Window)
                    
                    if 'geometry' in frag_data:
                        try:
                            dialog.restoreGeometry(QByteArray.fromBase64(frag_data['geometry'].encode('ascii')))
                        except:
                            pass
                            
                    dialog.show()
                    
                    if not hasattr(self, 'fragment_editors'):
                        self.fragment_editors = []
                    self.fragment_editors.append(dialog)
                    dialog.finished.connect(lambda result, d=dialog: self.fragment_editors.remove(d) if d in self.fragment_editors else None)

        except Exception as e:
            print(f"Error restoring session: {e}")

    def select_node_and_scroll(self, node):
        """Select node in tree and scroll to it in editor"""
        if not node:
            return
            
        # 1. Select in tree
        if hasattr(self, 'tree_widget'):
            self.tree_widget.select_node(node)
            
        # 2. Highlight in editor
        if hasattr(self, 'xml_editor') and node.line_number > 0:
            self.xml_editor.highlight_line(node.line_number)
            
        # 3. Focus
        self.activateWindow()
        self.raise_()

    def closeEvent(self, event):
        """Handle close event"""
        self._save_session()
        
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
        # Check current state from persisted flag
        is_dark = self._read_flag('dark_theme', True)
        
        # Use QTimer to defer theme application and prevent UI hang
        if is_dark:
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
        
        # Update editor for dark theme
        if hasattr(self, 'xml_editor') and hasattr(self.xml_editor, 'set_dark_theme'):
            self.xml_editor.set_dark_theme(True)
        
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
        light_style = """
        QMainWindow {
            background-color: #f0f0f0;
            color: #000000;
        }
        QMenuBar {
            background-color: #f0f0f0;
            color: #000000;
            border-bottom: 1px solid #ccc;
        }
        QMenuBar::item:selected {
            background-color: #e0e0e0;
        }
        QMenu {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #ccc;
        }
        QMenu::item:selected {
            background-color: #e0e0e0;
        }
        QToolBar {
            background-color: #f0f0f0;
            border: none;
            padding: 2px;
        }
        QToolButton {
            background-color: #f0f0f0;
            color: #000000;
            border: none;
            padding: 4px;
        }
        QToolButton:hover {
            background-color: #e0e0e0;
        }
        QToolButton:pressed {
            background-color: #d0d0d0;
        }
        QTreeWidget {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #ccc;
            alternate-background-color: #f9f9f9;
        }
        QTreeWidget::item:selected {
            background-color: #cce8ff;
            color: #000000;
        }
        QTreeWidget::header {
            background-color: #f0f0f0;
            color: #000000;
            border: 1px solid #ccc;
        }
        QTreeWidget::header::section {
            background-color: #f0f0f0;
            color: #000000;
            border: 1px solid #ccc;
            padding: 4px;
        }
        QTabWidget::pane {
            border: 1px solid #ccc;
            background-color: #ffffff;
        }
        QTabBar::tab {
            background-color: #e0e0e0;
            color: #000000;
            border: 1px solid #ccc;
            padding: 8px 16px;
        }
        QTabBar::tab:selected {
            background-color: #ffffff;
            border-bottom: 1px solid #ffffff;
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
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #ccc;
            padding: 4px;
        }
        QSpinBox {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #ccc;
        }
        QListWidget {
            background-color: #ffffff;
            color: #000000;
            border: 1px solid #ccc;
        }
        QLabel {
            background-color: transparent;
            color: #000000;
        }
        QScrollBar:vertical {
            background-color: #f0f0f0;
            border: none;
            width: 14px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background-color: #cdcdcd;
            border-radius: 7px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #a6a6a6;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            border: none;
            background: none;
            height: 0px;
        }
        QScrollBar:horizontal {
            background-color: #f0f0f0;
            border: none;
            height: 14px;
            margin: 0px;
        }
        QScrollBar::handle:horizontal {
            background-color: #cdcdcd;
            border-radius: 7px;
            min-width: 20px;
        }
        QScrollBar::handle:horizontal:hover {
            background-color: #a6a6a6;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            border: none;
            background: none;
            width: 0px;
        }
        """
        self.setStyleSheet(light_style)
        
        # Update editor for light theme
        if hasattr(self, 'xml_editor') and hasattr(self.xml_editor, 'set_dark_theme'):
            self.xml_editor.set_dark_theme(False)
        
        # Update breadcrumb label styling for light theme
        if hasattr(self, 'breadcrumb_label'):
            self.breadcrumb_label.setStyleSheet("""
                QLabel {
                    background-color: #f0f0f0;
                    color: #000000;
                    padding: 4px 8px;
                    border: 1px solid #ccc;
                    border-radius: 3px;
                }
            """)
        
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
                elif tab_name == "links":
                    self.bottom_panel.setCurrentWidget(self.bottom_panel.links_tab)
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
    
    def open_metro_navigator(self):
        """Open XML Metro Navigator window"""
        try:
            # Check if tree is built
            if self.xml_tree.topLevelItemCount() == 0:
                # No tree built - show message and offer to open file
                reply = QMessageBox.question(
                    self,
                    "No XML Tree",
                    "The XML tree has not been built yet.\n\n"
                    "Would you like to open an XML file?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    self.open_file()
                return
            
            # Get root node from tree
            root_item = self.xml_tree.topLevelItem(0)
            if not root_item or not hasattr(root_item, 'xml_node'):
                QMessageBox.information(
                    self,
                    "No XML Tree",
                    "Please open and parse an XML file first.\n\n"
                    "The tree structure is required for the Metro Navigator."
                )
                return
            
            root_node = root_item.xml_node
            
            # Create and show metro navigator window
            self.metro_window = MetroNavigatorWindow(root_node, parent=self)
            
            # Connect signals for synchronization
            self.metro_window.node_selected.connect(self.sync_editor_to_node)
            
            self.metro_window.show()
            self.status_label.setText("Opened XML Metro Navigator")
            
        except Exception as e:
            print(f"Error opening metro navigator: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to open Metro Navigator:\n{str(e)}"
            )
            self.status_label.setText(f"Error opening metro navigator: {str(e)}")
    
    def sync_editor_to_node(self, xml_node: XmlTreeNode):
        """Sync editor cursor to selected node from metro navigator"""
        try:
            if xml_node and xml_node.line_number > 0:
                # Move cursor to line in editor
                self.xml_editor.setCursorPosition(xml_node.line_number - 1, 0)
                self.xml_editor.ensureCursorVisible()
                self.status_label.setText(f"Jumped to line {xml_node.line_number}: {xml_node.name}")
        except Exception as e:
            print(f"Error syncing editor to node: {e}")
            self.status_label.setText(f"Error syncing to node: {str(e)}")
    
    
    def _extract_node_xml(self, xml_node, tree_item):
        """Extract XML content for a node and all its subnodes"""
        try:
            # Get the full XML content
            full_content = self.xml_editor.text()
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
        line_number = self.xml_editor.getCursorPosition()[0] + 1
        
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
        
        current_line = self.xml_editor.getCursorPosition()[0] + 1
        
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
        
        current_line = self.xml_editor.getCursorPosition()[0] + 1
        
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
            # QScintilla compatibility
            if isinstance(self.xml_editor, QsciScintilla):
                # Use markers for QScintilla
                # Marker 1 is used for bookmarks
                self.xml_editor.markerDeleteAll(1) 
                for line in self.bookmarks.keys():
                    self.xml_editor.markerAdd(line - 1, 1)
                return
        except Exception:
            pass

    def copy_xpath_link(self):
        """Copy XPath of current cursor position to Links tab (Ctrl+F11)"""
        try:
            # Get current cursor position
            line_number = self.xml_editor.getCursorPosition()[0] + 1
            
            # Get XML content
            content = self.xml_editor.get_content()
            if not content.strip():
                self.status_label.setText("No XML content to get XPath from")
                return
            
            # Get XPath for current line
            xpath = self._get_element_path_at_line(content, line_number)
            
            if xpath:
                # Add XPath to Links tab (append new line)
                current_text = self.bottom_panel.links_text.text()
                if current_text and not current_text.endswith('\n'):
                    self.bottom_panel.links_text.append('\n')
                
                self.bottom_panel.links_text.append(xpath)
                
                # Scroll to end
                self.bottom_panel.links_text.SendScintilla(QsciScintilla.SCI_DOCUMENTEND)
                
                # Show Links tab
                self._show_bottom_panel_auto("links")
                
                self.status_label.setText(f"XPath copied to Links: {xpath}")
            else:
                self.status_label.setText(f"Could not determine XPath for line {line_number}")
                
        except Exception as e:
            self.status_label.setText(f"Error copying XPath: {str(e)}")
            print(f"Error in copy_xpath_link: {e}")

    def navigate_xpath_link(self):
        """Navigate to XPath from current line in Links tab (F12)"""
        try:
            # Get current line from Links tab
            line, _ = self.bottom_panel.links_text.getCursorPosition()
            xpath = self.bottom_panel.links_text.text(line).strip()
            
            if not xpath or xpath.startswith("<!--"):
                self.status_label.setText("No XPath link on current line")
                return
            
            # Get XML content
            content = self.xml_editor.text()

            if not content.strip():
                self.status_label.setText("No XML content to navigate")
                return
            
            # Find line number for this XPath
            line_number = self._find_element_line_by_path(content, xpath)
            
            if line_number > 0:
                # Navigate to the line
                self.goto_line(line_number)
                self.status_label.setText(f"Navigated to XPath: {xpath} (line {line_number})")
                
                # Try to select the node in tree if available
                try:
                    if hasattr(self, 'xml_tree') and self.xml_tree:
                        item = self._find_tree_item_by_path(xpath)
                        if item:
                            self.xml_tree.setCurrentItem(item)
                            self.xml_tree.scrollToItem(item)
                except Exception as e:
                    print(f"Could not select tree item: {e}")
            else:
                self.status_label.setText(f"Could not find element for XPath: {xpath}")
                
        except Exception as e:
            self.status_label.setText(f"Error navigating to XPath: {str(e)}")
            print(f"Error in navigate_xpath_link: {e}")

    def set_numbered_bookmark(self, digit: int):
        """Set a numbered bookmark (1..9) to current line"""
        try:
            line, _ = self.xml_editor.getCursorPosition()
            line_number = line + 1
            
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
            self._debug_print(f"DEBUG: Loading file from path: {file_path}")
            self._debug_print(f"DEBUG: File exists: {os.path.exists(file_path)}")
            
            # Check file size first
            file_size = os.path.getsize(file_path)
            self._debug_print(f"DEBUG: File size: {file_size} bytes")
            
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
                    content = self._read_file_robust(file_path)
                else:
                    # Read small files normally with encoding fallback
                    try:
                        with open(file_path, 'r', encoding='utf-8') as file:
                            content = file.read()
                    except UnicodeDecodeError:
                        # Try with different encoding if UTF-8 fails (common for Cyrillic files)
                        try:
                            with open(file_path, 'r', encoding='cp1251') as file:
                                content = file.read()
                        except Exception:
                            # Last resort: try with latin-1 which accepts all bytes
                            with open(file_path, 'r', encoding='latin-1') as file:
                                content = file.read()
                
                self._debug_print(f"DEBUG: Content length: {len(content) if content else 0} characters")
                self._debug_print(f"DEBUG: First 100 chars: {content[:100] if content else 'None'}")
                
                self.xml_editor.set_content(content)
                
                # Defer tree building for large files to speed up initial load
                lines_count = len(content.split('\n')) if content else 0
                file_size_mb = (file_size / (1024 * 1024)) if file_size else 0
                
                if file_size_mb > 1.0:  # For files > 1MB, defer tree building
                    self.status_label.setText(f"File loaded. Building tree in background...")
                    QApplication.processEvents()
                    # Use QTimer to defer tree building, allowing UI to be responsive
                    QTimer.singleShot(100, lambda: self._deferred_tree_build(content, file_path, file_size))
                else:
                    try:
                        self.xml_tree.populate_tree(content)
                        self._finalize_file_load(file_path, file_size, content)
                    except Exception as tree_error:
                        self._debug_print(f"DEBUG: Tree population failed: {str(tree_error)}")
                        self.status_label.setText(f"Opened: {file_path} (tree build failed - XML may be malformed)")
                        self._finalize_file_load(file_path, file_size, content)
                
                # Save to cache for next startup
                if use_cache:
                    self._save_to_cache(file_path, content, file_size)
            
            # Exit loading mode
            self._loading_file = False
            
        except Exception as e:
            self._debug_print(f"DEBUG: Error loading file: {str(e)}")
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
            self._debug_print(f"DEBUG: Error in deferred tree build: {str(e)}")
            self.status_label.setText(f"Opened: {file_path} (tree build failed)")
    
    def _deferred_tree_build_from_open(self, content: str, file_path: str, file_size: int):
        """Build tree in a deferred manner for large files opened via open_file"""
        try:
            self.xml_tree.populate_tree(content, show_progress=True)
            self._finalize_file_load(file_path, file_size, content)
            self._finalize_open_file(file_path)
        except Exception as e:
            self._debug_print(f"DEBUG: Error in deferred tree build: {str(e)}")
            self.status_label.setText(f"Opened: {file_path} (tree build failed)")
            self._finalize_open_file(file_path)
    
    def _finalize_open_file(self, file_path: str):
        """Finalize file opening after tree is built"""
        self.current_file = file_path
        if hasattr(self, 'xml_editor') and self.xml_editor:
            self.xml_editor.file_path = file_path
            
            # Update tab title if we are in a tabbed environment
            if hasattr(self, 'tab_widget') and self.tab_widget:
                idx = self.tab_widget.indexOf(self.xml_editor)
                if idx >= 0:
                    self.tab_widget.setTabText(idx, os.path.basename(file_path))
                    self.tab_widget.setTabToolTip(idx, file_path)
        
        self._update_window_title()
        self.status_label.setText(f"Opened: {file_path}")
        
        # Update encoding label
        self.encoding_label.setText("UTF-8")
        
        # Restore editor state (cursor, selection, etc.)
        if hasattr(self, '_restore_editor_state') and hasattr(self, 'xml_editor'):
             self._restore_editor_state(self.xml_editor)
        
        # Add to recent files
        self._add_to_recent_files(file_path)
    
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
            self._debug_print(f"DEBUG: Index enabled={self.sync_index_enabled}, available={self._sync_index_available}, entries={len(self.path_line_index)}")
        else:
            self._debug_print(f"DEBUG: Index/cache disabled for small file (lines={lines_count}, size={file_size_mb:.2f}MB)")
        
        self.current_file = file_path
        self._update_window_title()
        self.status_label.setText(f"Opened: {file_path}")
        
        # Update encoding label
        self.encoding_label.setText("UTF-8")

        # Restore editor state (cursor, selection, etc.)
        if hasattr(self, '_restore_editor_state') and hasattr(self, 'xml_editor'):
             self._restore_editor_state(self.xml_editor)
    
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
                    self._debug_print(f"DEBUG: Loading from cache: {cache_file}")
                    with open(cache_file, 'rb') as f:
                        cached_data = pickle.load(f)
                    
                    # Load cached content
                    content = cached_data.get('content', '')
                    
                    # Validate content: if file has size but content is empty, cache is invalid
                    if not content and file_size > 0:
                        self._debug_print("DEBUG: Cached content is empty but file is not! Invalidating cache.")
                        return False
                    
                    self.xml_editor.set_content(content)
                    
                    # Verify content was set
                    current_content = self.xml_editor.get_content()
                    self._debug_print(f"DEBUG: Editor content length after set: {len(current_content)}")
                    
                    # Note: We still need to rebuild the tree as it contains Qt objects
                    # that can't be pickled, but having the content cached speeds things up
                    try:
                        self.xml_tree.populate_tree(content)
                        self._finalize_file_load(file_path, file_size, content)
                    except Exception as tree_error:
                        self._debug_print(f"DEBUG: Tree population failed from cache: {str(tree_error)}")
                        self.status_label.setText(f"Opened: {file_path} (tree build failed - XML may be malformed)")
                        self._finalize_file_load(file_path, file_size, content)
                    
                    self.status_label.setText(f"Loaded from cache: {os.path.basename(file_path)}")
                    self._debug_print(f"DEBUG: Successfully loaded from cache")
                    return True
            
            return False
        except Exception as e:
            self._debug_print(f"DEBUG: Cache load failed: {str(e)}")
            return False
    
    def _save_to_cache(self, file_path: str, content: str, file_size: int):
        """Save file content to cache for faster next startup"""
        try:
            import pickle
            import hashlib
            
            # Don't cache very large files (> 10MB)
            if file_size > 10 * 1024 * 1024:
                return
            
            # Don't cache empty content if file size indicates otherwise
            if not content and file_size > 0:
                self._debug_print("DEBUG: Skipping cache save for empty content")
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
            
            self._debug_print(f"DEBUG: Saved to cache: {cache_file}")
            
            # Clean up old cache files (keep only last 10)
            self._cleanup_old_cache(cache_dir)
            
        except Exception as e:
            self._debug_print(f"DEBUG: Cache save failed: {str(e)}")
    
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
                    self._debug_print(f"DEBUG: Removed old cache file: {filepath}")
                except Exception:
                    pass
        except Exception as e:
            self._debug_print(f"DEBUG: Cache cleanup failed: {str(e)}")
    
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
                self._update_window_title()
                self.status_label.setText(f"XML reconstructed from {os.path.basename(directory)}")
                
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


    def _encode_file_to_clipboard(self):
        """
        Win-Ctrl-Ins: Put entire zip file (or file in clipboard) into clipboard as base ansi text.
        Prefix: '''filename<CR><LF>
        """
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()
        
        file_path = None
        
        # Check for file URLs (standard)
        if mime_data.hasUrls():
            urls = mime_data.urls()
            if urls:
                file_path = urls[0].toLocalFile()
        
        # If no file in clipboard, check if we currently have a file open? 
        if not file_path:
             return
            
        if file_path and os.path.exists(file_path):
            try:
                # Read file content
                with open(file_path, 'rb') as f:
                    file_content = f.read()
                
                # Encode to base64
                encoded_content = base64.b64encode(file_content).decode('ascii')
                
                filename = os.path.basename(file_path)
                
                # Format: '''filename\r\n<content>
                final_text = f"'''{filename}\r\n{encoded_content}"
                
                clipboard.setText(final_text)
                if hasattr(self, 'status_label') and self.status_label:
                    self.status_label.setText(f"Encoded {filename} to clipboard as text")
                
            except Exception as e:
                QMessageBox.warning(self, "Encoding Error", f"Failed to encode file: {str(e)}")

    def _decode_file_from_clipboard(self):
        """
        Win-Shift-Ins: Receive ansi text from clipboard, check prefix, save to file.
        Prefix: '''filename<CR><LF>
        """
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        
        if not text.startswith("'''"):
            return # Not our format
            
        try:
            # Parse filename
            # Format: '''filename\r\n
            # Find first \r\n or \n
            newline_pos = text.find('\n')
            if newline_pos == -1:
                return
                
            first_line = text[:newline_pos].strip()
            # Remove leading '''
            if not first_line.startswith("'''"):
                return
            
            filename = first_line[3:].strip()
            if not filename:
                return
                
            # Content is after the first line (and potential \r)
            content_start = newline_pos + 1
            encoded_content = text[content_start:].strip()
            
            # Decode base64
            file_content = base64.b64decode(encoded_content)
            
            # Determine target directory
            # "temp dir (or dir opened in file tree, if active)"
            target_dir = tempfile.gettempdir()
            
            if self.current_file:
                target_dir = os.path.dirname(self.current_file)
            elif hasattr(self, 'file_navigator') and self.file_navigator.isVisible():
                 # Try to get path from file navigator
                 try:
                     index = self.file_navigator.tree.currentIndex()
                     if index.isValid():
                         path = self.file_navigator.model.filePath(index)
                         if os.path.isdir(path):
                             target_dir = path
                         else:
                             target_dir = os.path.dirname(path)
                     else:
                         target_dir = self.file_navigator.model.rootPath()
                 except Exception:
                     pass
            
            target_path = os.path.join(target_dir, filename)
            
            # Write file
            with open(target_path, 'wb') as f:
                f.write(file_content)
                
            # Put binary file into clipboard as a file
            data = QMimeData()
            url = QUrl.fromLocalFile(target_path)
            data.setUrls([url])
            clipboard.setMimeData(data)
            
            if hasattr(self, 'status_label') and self.status_label:
                self.status_label.setText(f"Decoded {filename} to {target_path} and put in clipboard")
            
        except Exception as e:
            QMessageBox.warning(self, "Decoding Error", f"Failed to decode file: {str(e)}")

    def _apply_text_transform(self, transform_func):
        """Apply a text transformation function to the selected text."""
        if not self.xml_editor.hasSelectedText():
             QMessageBox.information(self, "No Selection", "Please select text to transform.")
             return
        
        selected_text = self.xml_editor.selectedText()
        new_text = transform_func(selected_text)
        
        self.xml_editor.replaceSelectedText(new_text)
        
    def escape_selection_entities(self):
        """Convert special characters in selection to XML entities."""
        def escape_logic(text):
            # 1. Safe & escape (preserve existing entities)
            text = re.sub(r'&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)', '&amp;', text)
            # 2. Others
            text = text.replace('<', '&lt;')
            text = text.replace('>', '&gt;')
            text = text.replace('"', '&quot;')
            text = text.replace("'", '&apos;')
            text = text.replace('\u00A0', '&#160;')
            return text
            
        self._apply_text_transform(escape_logic)
        if hasattr(self, 'status_label'):
            self.status_label.setText("Escaped XML entities in selection")

    def unescape_selection_entities(self):
        """Convert XML entities in selection back to characters."""
        def unescape_logic(text):
            text = text.replace('&lt;', '<')
            text = text.replace('&gt;', '>')
            text = text.replace('&quot;', '"')
            text = text.replace('&apos;', "'")
            text = text.replace('&#160;', '\u00A0')
            text = text.replace('&#xA0;', '\u00A0')
            text = text.replace('&amp;', '&')
            return text
            
        self._apply_text_transform(unescape_logic)
        if hasattr(self, 'status_label'):
            self.status_label.setText("Unescaped XML entities in selection")



def main():
    """Main function"""
    app = QApplication(sys.argv)
    app.setApplicationName("Visual XML Editor")
    app.setApplicationVersion("1.0.0")
    
    # Set application style
    app.setStyle("Fusion")
    
    # Set application icon for taskbar (Windows)
    icon_path = os.path.join(os.path.dirname(__file__), "blotus.ico")
    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)
        
        # Windows-specific: Set app user model ID for taskbar icon
        try:
            import ctypes
            myappid = 'com.lotusxmleditor.app.1.0'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass
    
    # Handle command line arguments
    file_path = None
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        # Convert relative path to absolute path
        if not os.path.isabs(file_path):
            file_path = os.path.abspath(file_path)
    
    window = MainWindow(file_path)
    
    # Also set icon on the main window
    if os.path.exists(icon_path):
        window.setWindowIcon(app_icon)
    
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()