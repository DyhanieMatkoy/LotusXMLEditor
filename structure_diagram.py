from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsTextItem, QLabel, QPushButton
)
from PyQt6.QtGui import QPen, QBrush, QFont
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication

import xml.etree.ElementTree as ET


class DiagramNodeItem(QGraphicsRectItem):
    """
    Simple rectangular node with a label; calls a provided callback with its XPath on click.
    """
    def __init__(self, x: float, y: float, width: float, height: float, label: str, xpath: str, click_callback=None):
        super().__init__(x, y, width, height)
        self.setBrush(QBrush(Qt.GlobalColor.white))
        self.setPen(QPen(Qt.GlobalColor.black))
        self.setZValue(1)
        self.xpath = xpath
        self.click_callback = click_callback

        # Add text centered within the rectangle
        self.text_item = QGraphicsTextItem(label, self)
        # Position text roughly centered; QGraphicsTextItem does not auto-center by default
        text_rect = self.text_item.boundingRect()
        tx = x + (width - text_rect.width()) / 2
        ty = y + (height - text_rect.height()) / 2
        self.text_item.setPos(tx, ty)

    def mousePressEvent(self, event):
        try:
            if self.click_callback:
                self.click_callback(self.xpath)
        except Exception:
            pass
        super().mousePressEvent(event)

    def set_compact_mode(self, compact: bool):
        if compact:
            # Hide label, render as black box
            self.text_item.setVisible(False)
            self.setBrush(QBrush(Qt.GlobalColor.black))
            self.setPen(QPen(Qt.GlobalColor.black))
        else:
            self.text_item.setVisible(True)
            self.setBrush(QBrush(Qt.GlobalColor.white))
            self.setPen(QPen(Qt.GlobalColor.black))


class DiagramGraphicsView(QGraphicsView):
    """
    Graphics view with Ctrl+mouse wheel zoom and under-mouse anchor.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.zoom = 1.0
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        # Right-button drag zoom state
        self._zoom_dragging = False
        self._last_mouse_pos = None
        self._zoom_sensitivity = 0.01  # factor per pixel moved

    def wheelEvent(self, event):
        modifiers = QGuiApplication.keyboardModifiers()
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            factor = 1.2 if delta > 0 else (1 / 1.2)
            new_zoom = self.zoom * factor
            # Clamp zoom to sensible bounds
            if 0.05 <= new_zoom <= 5.0:
                self.scale(factor, factor)
                self.zoom = new_zoom
                parent = self.parent()
                if hasattr(parent, 'on_zoom_changed'):
                    try:
                        parent.on_zoom_changed(self.zoom)
                    except Exception:
                        pass
                if hasattr(parent, 'debug_log'):
                    try:
                        parent.debug_log(f"Wheel zoom -> {self.zoom:.3f}")
                    except Exception:
                        pass
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self._zoom_dragging = True
            try:
                self._last_mouse_pos = event.position()
            except Exception:
                self._last_mouse_pos = event.pos()
            parent = self.parent()
            if hasattr(parent, 'debug_log'):
                try:
                    parent.debug_log("Zoom drag start")
                except Exception:
                    pass
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._zoom_dragging and self._last_mouse_pos is not None:
            try:
                pos = event.position()
            except Exception:
                pos = event.pos()
            dy = pos.y() - self._last_mouse_pos.y()
            # Upwards (negative dy) zooms in; downwards zooms out
            factor = pow(1.0 + self._zoom_sensitivity, -dy)
            new_zoom = self.zoom * factor
            if 0.05 <= new_zoom <= 5.0 and abs(factor - 1.0) > 1e-6:
                self.scale(factor, factor)
                self.zoom = new_zoom
                parent = self.parent()
                if hasattr(parent, 'on_zoom_changed'):
                    try:
                        parent.on_zoom_changed(self.zoom)
                    except Exception:
                        pass
                if hasattr(parent, 'debug_log'):
                    try:
                        parent.debug_log(f"Drag zoom -> {self.zoom:.3f}")
                    except Exception:
                        pass
            self._last_mouse_pos = pos
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self._zoom_dragging = False
            self._last_mouse_pos = None
            parent = self.parent()
            if hasattr(parent, 'debug_log'):
                try:
                    parent.debug_log("Zoom drag end")
                except Exception:
                    pass
            event.accept()
            return
        super().mouseReleaseEvent(event)


class StructureDiagramWidget(QWidget):
    """
    Displays an XML structure as a left-to-right layered diagram. Nodes are clickable and
    report their XPath via a callback provided on construction.
    """
    def __init__(self, xml_content: str, on_xpath_clicked=None, on_debug_log=None, parent=None):
        super().__init__(parent)
        self.on_xpath_clicked = on_xpath_clicked
        self._debug_logger = on_debug_log

        self.view = DiagramGraphicsView(self)
        self.scene = QGraphicsScene(self)
        self.view.setScene(self.scene)
        self.node_items = []

        # Overlay zoom label in top-left corner of the viewport
        self.zoom_label = QLabel(self.view.viewport())
        self.zoom_label.setText("100.0%")
        self.zoom_label.setStyleSheet(
            "background-color: rgba(0,0,0,140); color: white; padding: 4px 6px; border-radius: 4px;"
        )
        self.zoom_label.setFont(QFont("Segoe UI", 9))
        self.zoom_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.zoom_label.move(8, 8)
        self.zoom_label.show()

        # Overlay zoom buttons (gray +/-)
        btn_style = (
            "QPushButton { background-color: #888; color: white; border: none;"
            " border-radius: 4px; }"
            "QPushButton:hover { background-color: #999; }"
        )
        self.zoom_out_btn = QPushButton("-", self.view.viewport())
        self.zoom_out_btn.setFixedSize(28, 24)
        self.zoom_out_btn.setStyleSheet(btn_style)
        self.zoom_out_btn.move(8, 36)
        self.zoom_out_btn.clicked.connect(self._handle_zoom_out)
        self.zoom_out_btn.show()

        self.zoom_in_btn = QPushButton("+", self.view.viewport())
        self.zoom_in_btn.setFixedSize(28, 24)
        self.zoom_in_btn.setStyleSheet(btn_style)
        self.zoom_in_btn.move(40, 36)
        self.zoom_in_btn.clicked.connect(self._handle_zoom_in)
        self.zoom_in_btn.show()

        layout = QVBoxLayout(self)
        layout.addWidget(self.view)
        self.setLayout(layout)

        # Build diagram from content
        try:
            root = ET.fromstring(xml_content)
        except Exception:
            root = None
        if root is not None:
            self._render_diagram(root)
            self._apply_default_zoom()
            # Initialize compact mode and label according to default zoom
            self.on_zoom_changed(self.view.zoom)

    def debug_log(self, message: str):
        try:
            print(f"[StructureDiagram] {message}")
        except Exception:
            pass
        if callable(self._debug_logger):
            try:
                self._debug_logger(message)
            except Exception:
                pass

    def _apply_default_zoom(self):
        # Fit the entire diagram into an area roughly equal to two screens
        rect = self.scene.itemsBoundingRect()
        if rect.width() <= 0 or rect.height() <= 0:
            return
        screens = QGuiApplication.screens()
        if len(screens) >= 2:
            g1 = screens[0].geometry()
            g2 = screens[1].geometry()
            target_width = g1.width() + g2.width()
            target_height = max(g1.height(), g2.height()) * 2
        elif len(screens) == 1:
            g = screens[0].geometry()
            target_width = g.width() * 2
            target_height = g.height() * 2
        else:
            target_width = 1920 * 2
            target_height = 1080 * 2

        sx = target_width / rect.width()
        sy = target_height / rect.height()
        scale = min(sx, sy)
        if scale <= 0:
            return
        self.view.resetTransform()
        self.view.scale(scale, scale)
        # Update internal zoom tracker
        if isinstance(self.view, DiagramGraphicsView):
            self.view.zoom = scale
        self.view.centerOn(rect.center())

    def _render_diagram(self, root):
        # Render as an interactive treemap using slice-and-dice layout.
        scene_width = 4000
        scene_height = 2500

        def _element_weight(elem) -> float:
            try:
                return float(len(ET.tostring(elem, encoding='utf-8')))
            except Exception:
                return 1.0

        def _sibling_index(parent, child_idx):
            if parent is None:
                return 1
            tag = parent[child_idx].tag
            count = 0
            for i in range(child_idx + 1):
                if parent[i].tag == tag:
                    count += 1
            return count

        def _layout(elem, x, y, w, h, orientation_vertical: bool, base_xpath: str):
            # Create clickable rectangle for current element
            label = elem.tag
            node_item = DiagramNodeItem(x, y, w, h, label, base_xpath, click_callback=self.on_xpath_clicked)
            self.scene.addItem(node_item)
            self.node_items.append(node_item)

            children = list(elem)
            if not children:
                return

            # Inner margin for children
            margin = 3
            ix, iy = x + margin, y + margin
            iw, ih = max(0, w - 2 * margin), max(0, h - 2 * margin)
            if iw <= 0 or ih <= 0:
                return

            # Compute weights
            weights = [_element_weight(c) for c in children]
            total = sum(weights) if sum(weights) > 0 else len(children)

            # Slice-and-dice splitting
            cursor_x = ix
            cursor_y = iy
            for idx, child in enumerate(children):
                frac = (weights[idx] / total) if total > 0 else (1.0 / len(children))
                if orientation_vertical:
                    cw = max(1.0, iw * frac)
                    ch = ih
                    cx, cy = cursor_x, iy
                    cursor_x += cw
                else:
                    cw = iw
                    ch = max(1.0, ih * frac)
                    cx, cy = ix, cursor_y
                    cursor_y += ch

                # Child XPath
                child_index = _sibling_index(elem, idx)
                child_xpath = f"{base_xpath}/{child.tag}[{child_index}]"

                # Recurse for child within allocated rect (alternate orientation)
                _layout(child, cx, cy, cw, ch, not orientation_vertical, child_xpath)

        # Root XPath and layout kickoff
        root_xpath = f"/{root.tag}[1]"
        _layout(root, 0, 0, scene_width, scene_height, True, root_xpath)

    def on_zoom_changed(self, zoom_ratio: float):
        # Update zoom indicator
        pct = zoom_ratio * 100.0
        self.zoom_label.setText(f"{pct:.1f}%")
        # Compact mode threshold
        compact = zoom_ratio < 0.15
        self._update_compact_mode(compact)
        self.debug_log(f"Zoom indicator updated -> {pct:.1f}%")

    def _apply_zoom_factor(self, factor: float):
        try:
            new_zoom = self.view.zoom * factor
            if new_zoom < 0.05:
                new_zoom = 0.05
            if new_zoom > 5.0:
                new_zoom = 5.0
            # Apply absolute zoom: reset then scale to target
            self.view.resetTransform()
            self.view.scale(new_zoom, new_zoom)
            self.view.zoom = new_zoom
            self.on_zoom_changed(self.view.zoom)
            # Recenter to keep content visible
            rect = self.scene.itemsBoundingRect()
            self.view.centerOn(rect.center())
            self.debug_log(f"Button zoom -> {self.view.zoom:.3f}")
        except Exception as e:
            try:
                self.debug_log(f"Zoom error: {e}")
            except Exception:
                pass

    def _handle_zoom_in(self):
        self._apply_zoom_factor(1.2)

    def _handle_zoom_out(self):
        self._apply_zoom_factor(1/1.2)

    def _update_compact_mode(self, compact: bool):
        for item in self.node_items:
            item.set_compact_mode(compact)


class StructureDiagramWindow(QWidget):
    """
    Top-level form hosting the StructureDiagramWidget. Accepts XML content and a callback
    to handle XPath clicks from node selections.
    """
    def __init__(self, xml_content: str, on_xpath_clicked=None, on_debug_log=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Structure Diagram")
        self.resize(900, 600)
        layout = QVBoxLayout(self)
        # Top control bar
        top_bar = QWidget(self)
        top_layout = QHBoxLayout(top_bar)
        try:
            top_layout.setContentsMargins(4, 4, 4, 4)
            top_layout.setSpacing(6)
        except Exception:
            pass
        close_btn = QPushButton("Close", top_bar)
        fullscreen_btn = QPushButton("Toggle Fullscreen", top_bar)
        close_btn.clicked.connect(self.close)
        fullscreen_btn.clicked.connect(self._toggle_fullscreen)
        top_layout.addStretch()
        top_layout.addWidget(fullscreen_btn)
        top_layout.addWidget(close_btn)
        top_bar.setLayout(top_layout)

        self.widget = StructureDiagramWidget(xml_content, on_xpath_clicked=on_xpath_clicked, on_debug_log=on_debug_log)
        layout.addWidget(top_bar)
        layout.addWidget(self.widget)
        self.setLayout(layout)

        # Track fullscreen state
        self._is_fullscreen = False

        # Attempt to span two screens by setting geometry to the union of the first two screens
        try:
            screens = QGuiApplication.screens()
            if len(screens) >= 2:
                g1 = screens[0].geometry()
                g2 = screens[1].geometry()
                union = g1.united(g2)
                self.setGeometry(union)
            elif len(screens) == 1:
                # Expand beyond single screen to allow wider viewport scrolling
                g = screens[0].geometry()
                self.setGeometry(g)
        except Exception:
            pass

    def _toggle_fullscreen(self):
        try:
            if self._is_fullscreen:
                self.showNormal()
            else:
                self.showFullScreen()
            self._is_fullscreen = not self._is_fullscreen
        except Exception:
            pass