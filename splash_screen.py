"""
Splash screen for large file loading
"""

from PyQt6.QtWidgets import QSplashScreen, QLabel
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
import os


class LoadingSplashScreen(QSplashScreen):
    """Custom splash screen shown when loading large files"""
    
    def __init__(self):
        # Load the splash image
        image_path = os.path.join(os.path.dirname(__file__), 'blotus_splash.jpg')
        
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            # Scale to reasonable size if too large
            if pixmap.width() > 600 or pixmap.height() > 600:
                pixmap = pixmap.scaled(600, 600, Qt.AspectRatioMode.KeepAspectRatio, 
                                      Qt.TransformationMode.SmoothTransformation)
        else:
            # Fallback: create a simple colored splash
            pixmap = QPixmap(400, 300)
            pixmap.fill(QColor(240, 240, 240))
        
        super().__init__(pixmap)
        
        # Set window flags to keep it on top
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.SplashScreen)
        
    def show_message(self, message: str):
        """Show a message on the splash screen"""
        self.showMessage(
            message,
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
            QColor(255, 255, 255)
        )
    
    def drawContents(self, painter: QPainter):
        """Custom drawing for the splash screen"""
        # Draw a semi-transparent overlay for better text visibility
        painter.save()
        painter.fillRect(0, self.height() - 60, self.width(), 60, QColor(0, 0, 0, 180))
        painter.restore()
        
        # Draw the message text
        super().drawContents(painter)
