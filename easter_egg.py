"""Easter egg dialog for unusual user actions"""

from PyQt6.QtWidgets import QDialog, QLabel, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from urllib.parse import urlparse


class EasterEggDialog(QDialog):
    """Dialog that displays an easter egg image"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎉")
        self.setModal(True)
        self.setMinimumSize(400, 400)
        
        layout = QVBoxLayout()
        
        # Image label
        self.image_label = QLabel("Loading...")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("QLabel { padding: 20px; }")
        layout.addWidget(self.image_label)
        
        self.setLayout(layout)
        
        # Network manager for loading image
        self.network_manager = QNetworkAccessManager()
        self.network_manager.finished.connect(self._on_image_loaded)
        
        # Auto-close timer
        self.close_timer = QTimer()
        self.close_timer.timeout.connect(self.accept)
        
    def show_image(self, url: str, auto_close_ms: int = 3000):
        """Load and display image from URL"""
        request = QNetworkRequest(urlparse(url).geturl())
        self.network_manager.get(request)
        
        if auto_close_ms > 0:
            self.close_timer.start(auto_close_ms)
        
        self.exec()
        
    def _on_image_loaded(self, reply: QNetworkReply):
        """Handle image download completion"""
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            
            if not pixmap.isNull():
                # Scale to fit dialog
                scaled = pixmap.scaled(
                    self.size() - self.layout().contentsMargins(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.image_label.setPixmap(scaled)
            else:
                self.image_label.setText("🎊 Surprise! 🎊")
        else:
            self.image_label.setText("🎉 You found an easter egg! 🎉")
        
        reply.deleteLater()


def show_easter_egg(parent=None):
    """Show the easter egg dialog"""
    dialog = EasterEggDialog(parent)
    dialog.show_image(
        "https://i.pinimg.com/originals/c2/f8/fa/c2f8fa4f04b6de59f8bd3f0c4274478e.jpg",
        auto_close_ms=3000
    )
