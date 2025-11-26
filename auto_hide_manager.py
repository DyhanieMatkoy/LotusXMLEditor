"""
Auto-hide Manager for UI Elements
Provides auto-hiding functionality for toolbar and tree header elements
"""

from PyQt6.QtWidgets import QWidget, QFrame
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, pyqtSignal, QObject
from PyQt6.QtGui import QPainter, QColor


class HoverZone(QFrame):
    """A thin hover zone that triggers reveal of hidden elements"""
    hovered = pyqtSignal()
    
    def __init__(self, parent=None, height=3):
        super().__init__(parent)
        self.setFixedHeight(height)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(100, 100, 100, 100);
                border: none;
            }
            QFrame:hover {
                background-color: rgba(150, 150, 150, 150);
            }
        """)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)
    
    def enterEvent(self, event):
        """Handle mouse enter"""
        super().enterEvent(event)
        self.hovered.emit()


class AutoHideManager(QObject):
    """Manages auto-hide behavior for UI elements"""
    
    def __init__(self, widget, hover_zone_height=3, animation_duration=200, hide_delay=500):
        """
        Initialize auto-hide manager
        
        Args:
            widget: The widget to manage auto-hide for
            hover_zone_height: Height of the hover zone in pixels
            animation_duration: Duration of show/hide animations in milliseconds
            hide_delay: Delay before hiding after mouse leaves in milliseconds
        """
        super().__init__()
        self.widget = widget
        self.hover_zone_height = hover_zone_height
        self.animation_duration = animation_duration
        self.hide_delay = hide_delay
        
        self.is_hidden = False
        self.auto_hide_enabled = True
        self.hover_zone = None
        self.hide_timer = QTimer()
        self.hide_timer.setSingleShot(True)
        self.hide_timer.timeout.connect(self._perform_hide)
        
        self.animation = None
        self.original_height = 0
        self.is_animating = False
        self.mouse_inside = False
        
        # Store original widget properties
        if widget:
            self.original_height = widget.height()
            widget.installEventFilter(self)
    
    def set_auto_hide_enabled(self, enabled):
        """Enable or disable auto-hide"""
        self.auto_hide_enabled = enabled
        
        if enabled:
            # Update original height before hiding
            if self.widget and self.widget.isVisible():
                self.original_height = max(self.widget.height(), self.original_height)
            # Hide the widget and show hover zone
            self._perform_hide()
        else:
            # Show the widget and hide hover zone
            self._perform_show()
            if self.hover_zone:
                self.hover_zone.hide()
    
    def create_hover_zone(self, parent):
        """Create and return a hover zone widget"""
        self.hover_zone = HoverZone(parent, self.hover_zone_height)
        self.hover_zone.hovered.connect(self._on_hover_zone_entered)
        return self.hover_zone
    
    def _on_hover_zone_entered(self):
        """Handle hover zone entered"""
        if self.auto_hide_enabled and self.is_hidden:
            self.show_widget()
    
    def show_widget(self):
        """Show the widget with animation"""
        if not self.widget or not self.auto_hide_enabled:
            return
        
        # Cancel any pending hide
        self.hide_timer.stop()
        
        # If already visible or animating to visible, do nothing
        if not self.is_hidden and not self.is_animating:
            return
        
        self._perform_show()
    
    def hide_widget(self):
        """Hide the widget with animation after delay"""
        if not self.widget or not self.auto_hide_enabled:
            return
        
        # Start hide timer
        if not self.mouse_inside:
            self.hide_timer.start(self.hide_delay)
    
    def _perform_show(self):
        """Perform the show animation"""
        if not self.widget:
            return
        
        # Stop any existing animation
        if self.animation:
            self.animation.stop()
        
        # Hide hover zone
        if self.hover_zone:
            self.hover_zone.hide()
        
        # Show widget
        self.widget.show()
        self.is_hidden = False
        self.is_animating = True
        
        # Animate height from 0 to original
        self.animation = QPropertyAnimation(self.widget, b"maximumHeight")
        self.animation.setDuration(self.animation_duration)
        self.animation.setStartValue(0)
        self.animation.setEndValue(self.original_height)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.finished.connect(self._on_show_finished)
        self.animation.start()
    
    def _perform_hide(self):
        """Perform the hide animation"""
        if not self.widget or self.mouse_inside:
            return
        
        # Update original height if widget is visible and has a valid height
        if self.widget.isVisible() and self.widget.height() > 0:
            self.original_height = max(self.widget.height(), self.original_height)
        
        # Stop any existing animation
        if self.animation:
            self.animation.stop()
        
        self.is_animating = True
        
        # Get current height, use original if current is 0
        current_height = self.widget.height() if self.widget.height() > 0 else self.original_height
        
        # Animate height from current to 0
        self.animation = QPropertyAnimation(self.widget, b"maximumHeight")
        self.animation.setDuration(self.animation_duration)
        self.animation.setStartValue(current_height)
        self.animation.setEndValue(0)
        self.animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self.animation.finished.connect(self._on_hide_finished)
        self.animation.start()
    
    def _on_show_finished(self):
        """Handle show animation finished"""
        self.is_animating = False
        if self.widget:
            self.widget.setMaximumHeight(16777215)  # Reset to no limit
    
    def _on_hide_finished(self):
        """Handle hide animation finished"""
        self.is_animating = False
        if self.widget:
            self.widget.hide()
            self.is_hidden = True
            
            # Show hover zone
            if self.hover_zone:
                self.hover_zone.show()
    
    def eventFilter(self, obj, event):
        """Filter events for the managed widget"""
        if obj == self.widget and self.auto_hide_enabled:
            if event.type() == event.Type.Enter:
                self.mouse_inside = True
                self.hide_timer.stop()
                if self.is_hidden:
                    self.show_widget()
            elif event.type() == event.Type.Leave:
                self.mouse_inside = False
                if not self.is_hidden:
                    self.hide_widget()
        
        return False
    
    def update_original_height(self, height):
        """Update the original height (call when widget size changes)"""
        self.original_height = height
