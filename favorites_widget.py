
import os
import json
from PyQt6.QtWidgets import (QTreeWidget, QTreeWidgetItem, QMenu, QFileDialog, 
                             QMessageBox, QApplication)
from PyQt6.QtCore import Qt, pyqtSignal, QMimeData
from PyQt6.QtGui import QAction, QIcon

class FavoritesWidget(QTreeWidget):
    """
    A widget to store favorite XML nodes.
    Supports drag-and-drop from the main XML tree.
    """
    navigate_requested = pyqtSignal(int)  # Signal to navigate to line number

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabels(["Favorite Node", "Line"])
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.setDragDropMode(QTreeWidget.DragDropMode.DropOnly)
        self.setAcceptDrops(True)
        
        # Context menu
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
        
        # Internal storage for file path (if loaded/saved)
        self.current_file_path = None

    def dragEnterEvent(self, event):
        """Accept drags from XmlTreeWidget"""
        if event.mimeData().hasFormat("application/x-lotus-xml-node"):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        """Accept drag moves"""
        if event.mimeData().hasFormat("application/x-lotus-xml-node"):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        """Handle dropped XML nodes"""
        if event.mimeData().hasFormat("application/x-lotus-xml-node"):
            data = event.mimeData().data("application/x-lotus-xml-node")
            try:
                # Decode JSON data
                json_data = json.loads(data.data().decode('utf-8'))
                self.add_favorite(json_data)
                event.acceptProposedAction()
            except Exception as e:
                print(f"Error dropping favorite: {e}")
        else:
            super().dropEvent(event)

    def add_favorite(self, data):
        """Add a favorite item"""
        # Check if already exists? Maybe allow duplicates as they might be different contexts.
        # User said "links to actively used nodes".
        
        tag = data.get("tag", "Unknown")
        name = data.get("name", "")
        # Use name if available and not empty, else tag
        display_text = name if name else tag
        
        line = data.get("line_number", 0)
        path = data.get("path", "")
        
        item = QTreeWidgetItem()
        item.setText(0, display_text)
        item.setText(1, str(line))
        item.setData(0, Qt.ItemDataRole.UserRole, data)
        
        self.addTopLevelItem(item)

    def _on_item_double_clicked(self, item, column):
        """Navigate to the node when double clicked"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data and "line_number" in data:
            self.navigate_requested.emit(data["line_number"])

    def _show_context_menu(self, position):
        """Show context menu"""
        item = self.itemAt(position)
        
        menu = QMenu(self)
        
        if item:
            nav_action = QAction("Navigate", self)
            nav_action.triggered.connect(lambda: self._on_item_double_clicked(item, 0))
            menu.addAction(nav_action)
            
            remove_action = QAction("Remove", self)
            remove_action.triggered.connect(lambda: self.takeTopLevelItem(self.indexOfTopLevelItem(item)))
            menu.addAction(remove_action)
            
            menu.addSeparator()

        save_action = QAction("Save Favorites...", self)
        save_action.triggered.connect(self.save_favorites)
        menu.addAction(save_action)
        
        load_action = QAction("Load Favorites...", self)
        load_action.triggered.connect(self.load_favorites)
        menu.addAction(load_action)
        
        clear_action = QAction("Clear All", self)
        clear_action.triggered.connect(self.clear)
        menu.addAction(clear_action)

        menu.exec(self.mapToGlobal(position))

    def save_favorites(self):
        """Save favorites to a file"""
        start_dir = ""
        if self.current_file_path:
            start_dir = os.path.dirname(self.current_file_path)
            
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Favorites", start_dir, "Lotus Favorites (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
            
        favorites = []
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            data = item.data(0, Qt.ItemDataRole.UserRole)
            favorites.append(data)
            
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(favorites, f, indent=2)
            # Don't update current_file_path here as it tracks the XML file, not the favorites file
            # or maybe we should track favorites file separately?
            # User said "save as separate file in same dir as xml".
            # Let's not confuse self.current_file_path (which I used for XML file) with favorites file.
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save favorites: {e}")

    def load_favorites(self):
        """Load favorites from a file"""
        start_dir = ""
        if self.current_file_path:
            start_dir = os.path.dirname(self.current_file_path)
            
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Favorites", start_dir, "Lotus Favorites (*.json);;All Files (*)"
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                favorites = json.load(f)
            
            self.clear()
            for fav in favorites:
                self.add_favorite(fav)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load favorites: {e}")
