import os
import uuid
import ftplib
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget, 
                             QLabel, QLineEdit, QSpinBox, QCheckBox, QPushButton, 
                             QMessageBox, QDialogButtonBox, QWidget, QSplitter,
                             QTreeWidget, QTreeWidgetItem, QHeaderView, QProgressDialog)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QAction

from ftp_manager import FtpManager, FtpProfile

class FtpProfilesDialog(QDialog):
    """Dialog to manage FTP profiles"""
    
    def __init__(self, manager: FtpManager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FTP Profiles")
        self.resize(600, 400)
        self.manager = manager
        self._current_profile_id = None
        
        self._setup_ui()
        self._load_profiles()
        
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        
        # Left side: Profile List
        left_layout = QVBoxLayout()
        self.profile_list = QListWidget()
        self.profile_list.currentItemChanged.connect(self._on_profile_selected)
        left_layout.addWidget(self.profile_list)
        
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add")
        self.add_btn.clicked.connect(self._add_profile)
        self.del_btn = QPushButton("Delete")
        self.del_btn.clicked.connect(self._delete_profile)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.del_btn)
        left_layout.addLayout(btn_layout)
        
        # Right side: Profile Details
        self.details_widget = QWidget()
        right_layout = QVBoxLayout(self.details_widget)
        
        # Name
        right_layout.addWidget(QLabel("Profile Name:"))
        self.name_edit = QLineEdit()
        right_layout.addWidget(self.name_edit)
        
        # Host
        right_layout.addWidget(QLabel("Host:"))
        self.host_edit = QLineEdit()
        right_layout.addWidget(self.host_edit)
        
        # Port
        right_layout.addWidget(QLabel("Port:"))
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(21)
        right_layout.addWidget(self.port_spin)
        
        # User
        right_layout.addWidget(QLabel("User:"))
        self.user_edit = QLineEdit()
        right_layout.addWidget(self.user_edit)
        
        # Password
        right_layout.addWidget(QLabel("Password:"))
        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        right_layout.addWidget(self.pass_edit)
        
        # Remote Path
        right_layout.addWidget(QLabel("Remote Path:"))
        self.path_edit = QLineEdit()
        self.path_edit.setText("/")
        right_layout.addWidget(self.path_edit)
        
        # Passive Mode
        self.passive_chk = QCheckBox("Passive Mode")
        self.passive_chk.setChecked(True)
        right_layout.addWidget(self.passive_chk)
        
        # Save Button (for current changes)
        self.save_btn = QPushButton("Save Changes")
        self.save_btn.clicked.connect(self._save_current_profile)
        right_layout.addWidget(self.save_btn)
        
        right_layout.addStretch()
        
        # Test Connection
        self.test_btn = QPushButton("Test Connection")
        self.test_btn.clicked.connect(self._test_connection)
        right_layout.addWidget(self.test_btn)
        
        # Layout assembly
        splitter = QSplitter(Qt.Orientation.Horizontal)
        left_widget = QWidget()
        left_widget.setLayout(left_layout)
        splitter.addWidget(left_widget)
        splitter.addWidget(self.details_widget)
        splitter.setStretchFactor(1, 2)
        
        layout.addWidget(splitter)
        
        # Dialog Buttons
        bbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bbox.rejected.connect(self.accept)
        layout.addWidget(bbox) # Actually vertical layout for bbox is wrong here, needs fix
        
        # Fix layout: QHBoxLayout cannot take bbox at end like this directly if we want it at bottom
        # Let's change main layout to QVBoxLayout
    
    def _setup_ui(self):
        # Re-implementing correctly
        main_layout = QVBoxLayout(self)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left side
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0,0,0,0)
        self.profile_list = QListWidget()
        self.profile_list.currentItemChanged.connect(self._on_profile_selected)
        left_layout.addWidget(self.profile_list)
        
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add")
        self.add_btn.clicked.connect(self._add_profile)
        self.del_btn = QPushButton("Delete")
        self.del_btn.clicked.connect(self._delete_profile)
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.del_btn)
        left_layout.addLayout(btn_layout)
        
        splitter.addWidget(left_widget)
        
        # Right side
        self.details_widget = QWidget()
        right_layout = QVBoxLayout(self.details_widget)
        right_layout.setContentsMargins(10,0,0,0)
        
        form_layout = QVBoxLayout()
        
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Profile Name")
        form_layout.addWidget(QLabel("Name:"))
        form_layout.addWidget(self.name_edit)
        
        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("ftp.example.com")
        form_layout.addWidget(QLabel("Host:"))
        form_layout.addWidget(self.host_edit)
        
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(21)
        form_layout.addWidget(QLabel("Port:"))
        form_layout.addWidget(self.port_spin)
        
        self.user_edit = QLineEdit()
        self.user_edit.setPlaceholderText("Username")
        form_layout.addWidget(QLabel("User:"))
        form_layout.addWidget(self.user_edit)
        
        self.pass_edit = QLineEdit()
        self.pass_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_edit.setPlaceholderText("Password")
        form_layout.addWidget(QLabel("Password:"))
        form_layout.addWidget(self.pass_edit)
        
        self.path_edit = QLineEdit()
        self.path_edit.setText("/")
        form_layout.addWidget(QLabel("Initial Path:"))
        form_layout.addWidget(self.path_edit)
        
        self.passive_chk = QCheckBox("Passive Mode")
        self.passive_chk.setChecked(True)
        form_layout.addWidget(self.passive_chk)
        
        right_layout.addLayout(form_layout)
        
        action_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self._save_current_profile)
        self.test_btn = QPushButton("Test Connection")
        self.test_btn.clicked.connect(self._test_connection)
        action_layout.addWidget(self.save_btn)
        action_layout.addWidget(self.test_btn)
        right_layout.addLayout(action_layout)
        
        right_layout.addStretch()
        self.details_widget.setEnabled(False)
        
        splitter.addWidget(self.details_widget)
        splitter.setStretchFactor(1, 2)
        
        main_layout.addWidget(splitter)
        
        bbox = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bbox.rejected.connect(self.accept)
        main_layout.addWidget(bbox)

    def _load_profiles(self):
        self.profile_list.clear()
        for p in self.manager.profiles:
            item = QListWidget() # Wrong, should be QListWidgetItem
            self.profile_list.addItem(p.name)
            self.profile_list.item(self.profile_list.count() - 1).setData(Qt.ItemDataRole.UserRole, p.id)

    def _load_profiles(self):
        self.profile_list.clear()
        for p in self.manager.profiles:
            from PyQt6.QtWidgets import QListWidgetItem
            item = QListWidgetItem(p.name)
            item.setData(Qt.ItemDataRole.UserRole, p.id)
            self.profile_list.addItem(item)

    def _on_profile_selected(self, current, previous):
        if not current:
            self.details_widget.setEnabled(False)
            self._current_profile_id = None
            return
            
        self.details_widget.setEnabled(True)
        profile_id = current.data(Qt.ItemDataRole.UserRole)
        self._current_profile_id = profile_id
        profile = self.manager.get_profile(profile_id)
        
        if profile:
            self.name_edit.setText(profile.name)
            self.host_edit.setText(profile.host)
            self.port_spin.setValue(profile.port)
            self.user_edit.setText(profile.user)
            self.pass_edit.setText(profile.password)
            self.path_edit.setText(profile.remote_path)
            self.passive_chk.setChecked(profile.passive_mode)

    def _add_profile(self):
        new_id = str(uuid.uuid4())
        profile = FtpProfile(id=new_id, name="New Profile", host="")
        self.manager.add_profile(profile)
        self._load_profiles()
        # Select the new item
        for i in range(self.profile_list.count()):
            item = self.profile_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == new_id:
                self.profile_list.setCurrentItem(item)
                break

    def _delete_profile(self):
        if not self._current_profile_id:
            return
        
        if QMessageBox.question(self, "Confirm", "Delete this profile?") == QMessageBox.StandardButton.Yes:
            self.manager.delete_profile(self._current_profile_id)
            self._load_profiles()

    def _save_current_profile(self):
        if not self._current_profile_id:
            return
            
        profile = FtpProfile(
            id=self._current_profile_id,
            name=self.name_edit.text(),
            host=self.host_edit.text(),
            port=self.port_spin.value(),
            user=self.user_edit.text(),
            password=self.pass_edit.text(),
            passive_mode=self.passive_chk.isChecked(),
            remote_path=self.path_edit.text()
        )
        self.manager.update_profile(profile)
        
        # Update list item text
        current_item = self.profile_list.currentItem()
        if current_item:
            current_item.setText(profile.name)
            
        QMessageBox.information(self, "Saved", "Profile saved.")

    def _test_connection(self):
        profile = FtpProfile(
            id="test",
            name="test",
            host=self.host_edit.text(),
            port=self.port_spin.value(),
            user=self.user_edit.text(),
            password=self.pass_edit.text(),
            passive_mode=self.passive_chk.isChecked(),
            remote_path=self.path_edit.text()
        )
        
        try:
            ftp = self.manager.connect(profile)
            ftp.quit()
            QMessageBox.information(self, "Success", "Connection successful!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Connection failed: {e}")


class FtpBrowserDialog(QDialog):
    """Dialog to browse FTP files"""
    
    file_selected = pyqtSignal(str, object) # local_path, ftp_profile
    
    def __init__(self, manager: FtpManager, mode="open", parent=None):
        super().__init__(parent)
        self.manager = manager
        self.mode = mode # "open" or "save"
        self.current_ftp = None
        self.current_profile = None
        self.current_path = "/"
        
        self.setWindowTitle("FTP Browser")
        self.resize(800, 500)
        
        self._setup_ui()
        self._load_profiles_combo()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Top bar: Profile selector and Connect button
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Profile:"))
        self.profile_combo = QWidget() # Placeholder, will be QComboBox
        from PyQt6.QtWidgets import QComboBox
        self.profile_combo = QComboBox()
        top_layout.addWidget(self.profile_combo)
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._connect)
        top_layout.addWidget(self.connect_btn)
        
        self.manage_btn = QPushButton("Manage Profiles")
        self.manage_btn.clicked.connect(self._manage_profiles)
        top_layout.addWidget(self.manage_btn)
        
        layout.addLayout(top_layout)
        
        # Address bar
        addr_layout = QHBoxLayout()
        addr_layout.addWidget(QLabel("Remote Path:"))
        self.path_input = QLineEdit()
        self.path_input.returnPressed.connect(self._navigate_path)
        addr_layout.addWidget(self.path_input)
        self.up_btn = QPushButton("Up")
        self.up_btn.clicked.connect(self._go_up)
        addr_layout.addWidget(self.up_btn)
        layout.addLayout(addr_layout)
        
        # File list
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Size", "Type"])
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self.tree)
        
        # Bottom bar: Filename input (for save) and buttons
        if self.mode == "save":
            file_layout = QHBoxLayout()
            file_layout.addWidget(QLabel("Filename:"))
            self.filename_input = QLineEdit()
            file_layout.addWidget(self.filename_input)
            layout.addLayout(file_layout)
        
        btn_layout = QHBoxLayout()
        self.action_btn = QPushButton("Open" if self.mode == "open" else "Save")
        self.action_btn.clicked.connect(self._on_action)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.action_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
    def _load_profiles_combo(self):
        self.profile_combo.clear()
        for p in self.manager.profiles:
            self.profile_combo.addItem(p.name, p.id)
            
    def _manage_profiles(self):
        dlg = FtpProfilesDialog(self.manager, self)
        dlg.exec()
        self._load_profiles_combo()
        
    def _connect(self):
        idx = self.profile_combo.currentIndex()
        if idx < 0:
            return
        
        profile_id = self.profile_combo.currentData()
        self.current_profile = self.manager.get_profile(profile_id)
        
        if not self.current_profile:
            return
            
        try:
            if self.current_ftp:
                try:
                    self.current_ftp.quit()
                except:
                    pass
            
            self.current_ftp = self.manager.connect(self.current_profile)
            self.current_path = self.current_profile.remote_path or "/"
            self._list_files()
            self.path_input.setText(self.current_path)
        except Exception as e:
            QMessageBox.critical(self, "Connection Error", str(e))
            
    def _list_files(self):
        if not self.current_ftp:
            return
            
        try:
            self.tree.clear()
            items = self.manager.list_files(self.current_ftp, self.current_path)
            
            for item in items:
                tree_item = QTreeWidgetItem(self.tree)
                tree_item.setText(0, item['name'])
                tree_item.setText(1, str(item['size']) if not item['is_dir'] else "")
                tree_item.setText(2, "Folder" if item['is_dir'] else "File")
                
                if item['is_dir']:
                    tree_item.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_DirIcon))
                else:
                    tree_item.setIcon(0, self.style().standardIcon(self.style().StandardPixmap.SP_FileIcon))
                    
                tree_item.setData(0, Qt.ItemDataRole.UserRole, item)
                
            self.path_input.setText(self.current_path)
            
        except Exception as e:
            QMessageBox.critical(self, "List Error", str(e))

    def _on_item_double_clicked(self, item, column):
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data['is_dir']:
            self.current_path = data['path']
            self._list_files()
        else:
            if self.mode == "open":
                self._download_and_accept(data)
            elif self.mode == "save":
                self.filename_input.setText(data['name'])

    def _navigate_path(self):
        new_path = self.path_input.text()
        # Verify path exists by listing it? 
        # Or just try to change to it
        self.current_path = new_path
        self._list_files()

    def _go_up(self):
        if self.current_path == "/":
            return
        self.current_path = os.path.dirname(self.current_path).replace("\\", "/")
        if not self.current_path:
            self.current_path = "/"
        self._list_files()

    def _on_action(self):
        if self.mode == "open":
            item = self.tree.currentItem()
            if not item:
                return
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data['is_dir']:
                return
            self._download_and_accept(data)
            
        elif self.mode == "save":
            filename = self.filename_input.text()
            if not filename:
                return
            
            # Check if overwriting?
            # We will handle upload in main window or here?
            # Better to return the target path and let main window upload
            
            target_path = f"{self.current_path.rstrip('/')}/{filename}"
            self.file_selected.emit(target_path, self.current_profile)
            self.accept()

    def _download_and_accept(self, file_data):
        # Download to temp
        try:
            self.manager.ensure_temp_dir()
            
            # If zip, we might need special handling if we want to browse inside zip.
            # But requirement says "including zip files with xml".
            # If user opens zip, we probably just open it as a file (Lotus handles zip opening).
            
            remote_path = file_data['path']
            local_filename = f"{uuid.uuid4()}_{file_data['name']}"
            local_path = self.manager.get_temp_file_path(local_filename)
            
            # Show progress?
            progress = QProgressDialog("Downloading...", "Cancel", 0, 0, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()
            
            self.manager.download_file(self.current_ftp, remote_path, local_path)
            
            progress.close()
            
            # Store metadata to know it's from FTP for saving back
            # We can use a sidecar file or pass metadata back
            
            # We pass local path and profile + remote path back
            # But we need a way to tell MainWindow to save it back to FTP
            
            # I will return the local path, but I also need to associate it with FTP info.
            # MainWindow has `zip_source` concept. I can add `ftp_source`.
            
            # Construct a special return object or signal
            
            # We'll attach the ftp info to the file path effectively or pass it separately
            
            ftp_info = {
                "profile_id": self.current_profile.id,
                "remote_path": remote_path,
                "host": self.current_profile.host
            }
            
            self.file_selected.emit(local_path, ftp_info)
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Download Error", str(e))

