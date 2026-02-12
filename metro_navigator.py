"""
XML Metro Navigator - Interactive graphical navigator for XML structure visualization

This module provides a metro-style visualization of XML document structure,
displaying the first three levels of hierarchy as interconnected stations.
"""

from typing import Optional, Dict, Tuple, List, Any
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QGraphicsView, QGraphicsScene, QGraphicsItem, QGraphicsLineItem,
    QLabel, QPushButton, QToolBar, QStatusBar, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPointF, QSettings
from PyQt6.QtGui import (
    QPainter, QWheelEvent, QPen, QBrush, QColor,
    QFont, QPainterPath, QTransform
)
import math

from models import XmlTreeNode, MetroGraphNode, MetroNavigatorSettings
from xml_service import XmlService


def extract_N_levels_from_tree(root_node: Optional[XmlTreeNode], max_depth: int = 3) -> Optional[XmlTreeNode]:
    """
    Extract N levels from existing XmlTreeNode
    
    Args:
        root_node: Root node from editor's tree
        max_depth: Maximum depth to extract (default 3 for levels 0, 1, 2)
        
    Returns:
        New XmlTreeNode with only first N levels, or None if root_node is None
        
    Note:
        This function reuses the already parsed tree structure,
        avoiding redundant XML parsing. The max_depth parameter specifies
        the number of levels to include (e.g., max_depth=3 includes levels 0, 1, 2).
    """
    if root_node is None:
        return None
    
    def copy_node_limited_depth(node: XmlTreeNode, current_level: int, max_level: int) -> XmlTreeNode:
        """Recursively copy node up to max_level"""
        # Create a copy of the current node
        new_node = XmlTreeNode(
            name=node.name,
            tag=node.tag,
            value=node.value,
            attributes=node.attributes.copy(),
            path=node.path,
            line_number=node.line_number
        )
        
        # Only copy children if we haven't reached max depth
        # current_level starts at 0, so we check if current_level < max_level - 1
        if current_level < max_level - 1:
            for child in node.children:
                new_child = copy_node_limited_depth(child, current_level + 1, max_level)
                new_node.children.append(new_child)
        
        return new_node
    
    return copy_node_limited_depth(root_node, 0, max_depth)


def extract_three_levels_from_tree(root_node: XmlTreeNode) -> Optional[XmlTreeNode]:
    """
    Extract first three levels from existing XmlTreeNode
    
    Args:
        root_node: Root node from editor's tree
        
    Returns:
        New XmlTreeNode with only first 3 levels (0, 1, 2)
        
    Note:
        This is a convenience wrapper around extract_N_levels_from_tree
        that defaults to 3 levels for backward compatibility.
    """
    return extract_N_levels_from_tree(root_node, max_depth=3)


def convert_to_metro_graph(root_node: XmlTreeNode) -> Optional[MetroGraphNode]:
    """
    Convert XmlTreeNode to MetroGraphNode structure
    
    Args:
        root_node: Root XmlTreeNode (limited to 3 levels)
        
    Returns:
        Root MetroGraphNode with positions initialized to (0, 0)
    """
    if root_node is None:
        return None
    
    def build_metro_node(xml_node: XmlTreeNode, level: int, parent: Optional[MetroGraphNode] = None) -> MetroGraphNode:
        """Recursively build metro graph node"""
        metro_node = MetroGraphNode(
            xml_node=xml_node,
            level=level,
            position=(0.0, 0.0),
            parent=parent
        )
        
        for child in xml_node.children:
            child_metro_node = build_metro_node(child, level + 1, metro_node)
            metro_node.children.append(child_metro_node)
        
        return metro_node
    
    return build_metro_node(root_node, 0)


class MetroLayoutEngine:
    """Intelligent node layout algorithm for metro graph"""
    
    def __init__(self):
        """Initialize layout engine"""
        self.repulsion_constant = 5000.0
        self.spring_constant = 0.1
        self.min_node_distance = 80.0
        self.min_level_distance = 120.0
        # Bounding box sizes (matching StationNode)
        self.root_node_width = 100.0  # 2 * 50
        self.root_node_height = 60.0  # 2 * 30
        self.standard_node_width = 80.0  # 2 * 40
        self.standard_node_height = 50.0  # 2 * 25
    
    def compute_layout(self, root_node: MetroGraphNode, 
                      canvas_width: float = 2000.0, 
                      canvas_height: float = 1500.0) -> Dict[str, Tuple[float, float]]:
        """
        Compute optimal positions for all nodes
        
        Args:
            root_node: Root of metro graph
            canvas_width: Available canvas width
            canvas_height: Available canvas height
            
        Returns:
            Dictionary mapping node XPath to (x, y) position
        """
        if root_node is None:
            return {}
        
        # Collect all nodes
        all_nodes = self._collect_nodes(root_node)
        
        # Initialize positions with good spacing
        positions = self._initialize_positions(all_nodes, canvas_width, canvas_height)
        
        # Apply force-directed layout with fewer iterations to preserve spacing
        positions = self._apply_force_directed_layout(all_nodes, positions, iterations=50)
        
        # Final vertical alignment pass
        positions = self._align_levels(all_nodes, positions)
        
        # Resolve any remaining collisions after alignment
        positions = self._resolve_collisions(positions, self.min_node_distance, all_nodes)
        
        return positions
    
    def _align_levels(self, nodes: List[MetroGraphNode], 
                     positions: Dict[str, Tuple[float, float]]) -> Dict[str, Tuple[float, float]]:
        """
        Align nodes to their designated vertical levels
        
        Args:
            nodes: List of all nodes
            positions: Current positions
            
        Returns:
            Positions with nodes aligned to level heights
        """
        aligned = dict(positions)
        
        # Group nodes by level and align them
        for node in nodes:
            target_y = node.level * self.min_level_distance + 100
            x, _ = aligned[node.xpath]
            aligned[node.xpath] = (x, target_y)
        
        return aligned
    
    def _collect_nodes(self, root: MetroGraphNode) -> List[MetroGraphNode]:
        """Collect all nodes in the graph"""
        nodes = []
        
        def traverse(node: MetroGraphNode):
            nodes.append(node)
            for child in node.children:
                traverse(child)
        
        traverse(root)
        return nodes
    
    def _initialize_positions(self, nodes: List[MetroGraphNode], 
                             width: float, height: float) -> Dict[str, Tuple[float, float]]:
        """
        Initialize node positions with proportional space allocation
        
        Args:
            nodes: List of all nodes
            width: Canvas width
            height: Canvas height
            
        Returns:
            Initial positions for all nodes
        """
        positions = {}
        
        # Group nodes by level
        levels = {}
        for node in nodes:
            if node.level not in levels:
                levels[node.level] = []
            levels[node.level].append(node)
        
        # Position nodes level by level with proportional spacing
        for level, level_nodes in levels.items():
            y = level * self.min_level_distance + 100
            count = len(level_nodes)
            
            if count == 1:
                # Single node: center it
                positions[level_nodes[0].xpath] = (width / 2, y)
            else:
                # Multiple nodes: distribute proportionally based on child count
                # Calculate total weight (number of descendants for each node)
                weights = []
                for node in level_nodes:
                    weight = self._count_descendants(node) + 1  # +1 for the node itself
                    weights.append(weight)
                
                total_weight = sum(weights)
                
                # Allocate horizontal space proportionally
                # Ensure minimum spacing between nodes
                min_spacing = self.standard_node_width + 20  # Node width + 20px margin
                total_min_width = count * min_spacing
                
                # Use the larger of proportional or minimum spacing
                available_width = max(width * 0.8, total_min_width)
                current_x = (width - available_width) / 2  # Center the layout
                
                for i, node in enumerate(level_nodes):
                    # Calculate proportional space for this node
                    node_space = (weights[i] / total_weight) * available_width
                    
                    # Ensure minimum spacing
                    node_space = max(node_space, min_spacing)
                    
                    # Position node in the center of its allocated space
                    x = current_x + node_space / 2
                    positions[node.xpath] = (x, y)
                    
                    # Move to next space
                    current_x += node_space
        
        return positions
    
    def _count_descendants(self, node: MetroGraphNode) -> int:
        """
        Count total number of descendants for a node
        
        Args:
            node: Node to count descendants for
            
        Returns:
            Total number of descendants
        """
        count = len(node.children)
        for child in node.children:
            count += self._count_descendants(child)
        return count
    
    def _apply_force_directed_layout(self, nodes: List[MetroGraphNode], 
                                    positions: Dict[str, Tuple[float, float]],
                                    iterations: int = 150) -> Dict[str, Tuple[float, float]]:
        """
        Apply force-directed layout algorithm
        
        Args:
            nodes: List of nodes to position
            positions: Initial positions
            iterations: Number of simulation iterations (default 150)
            
        Returns:
            Optimized node positions
        """
        # Create a mutable copy of positions
        current_positions = {k: list(v) for k, v in positions.items()}
        
        # Build edge list (parent-child relationships)
        edges = []
        for node in nodes:
            for child in node.children:
                edges.append((node.xpath, child.xpath))
        
        # Determine if we need strong grouping (for large graphs)
        use_strong_grouping = len(nodes) > 50
        grouping_strength = 0.5 if use_strong_grouping else 0.2
        
        # Simulation parameters
        damping = 0.85  # Velocity damping factor
        velocities = {xpath: [0.0, 0.0] for xpath in current_positions.keys()}
        
        # Run simulation
        for iteration in range(iterations):
            # Calculate forces for each node
            forces = {xpath: [0.0, 0.0] for xpath in current_positions.keys()}
            
            # 1. Repulsive forces between all node pairs
            node_xpaths = list(current_positions.keys())
            for i in range(len(node_xpaths)):
                for j in range(i + 1, len(node_xpaths)):
                    xpath1 = node_xpaths[i]
                    xpath2 = node_xpaths[j]
                    
                    pos1 = current_positions[xpath1]
                    pos2 = current_positions[xpath2]
                    
                    dx = pos2[0] - pos1[0]
                    dy = pos2[1] - pos1[1]
                    distance = math.sqrt(dx * dx + dy * dy)
                    
                    if distance > 0.1:  # Avoid division by zero
                        # Coulomb's law: F = k / d^2
                        repulsion = self.repulsion_constant / (distance * distance)
                        fx = (dx / distance) * repulsion
                        fy = (dy / distance) * repulsion
                        
                        forces[xpath1][0] -= fx
                        forces[xpath1][1] -= fy
                        forces[xpath2][0] += fx
                        forces[xpath2][1] += fy
            
            # 2. Attractive forces along edges (parent-child)
            for parent_xpath, child_xpath in edges:
                pos_parent = current_positions[parent_xpath]
                pos_child = current_positions[child_xpath]
                
                dx = pos_child[0] - pos_parent[0]
                dy = pos_child[1] - pos_parent[1]
                distance = math.sqrt(dx * dx + dy * dy)
                
                if distance > 0.1:
                    # Hooke's law: F = k * d
                    attraction = self.spring_constant * distance
                    fx = (dx / distance) * attraction
                    fy = (dy / distance) * attraction
                    
                    forces[parent_xpath][0] += fx
                    forces[parent_xpath][1] += fy
                    forces[child_xpath][0] -= fx
                    forces[child_xpath][1] -= fy
            
            # 3. Grouping forces (children stay close to parent)
            if use_strong_grouping:
                for node in nodes:
                    if node.children:
                        parent_pos = current_positions[node.xpath]
                        
                        # Calculate centroid of children
                        child_positions = [current_positions[child.xpath] for child in node.children]
                        centroid_x = sum(pos[0] for pos in child_positions) / len(child_positions)
                        centroid_y = sum(pos[1] for pos in child_positions) / len(child_positions)
                        
                        # Pull children toward parent (horizontally only, to preserve levels)
                        for child in node.children:
                            child_pos = current_positions[child.xpath]
                            dx = parent_pos[0] - child_pos[0]
                            
                            # Apply horizontal grouping force
                            grouping_force = dx * grouping_strength
                            forces[child.xpath][0] += grouping_force
            
            # 4. Apply forces to update velocities and positions
            for xpath in current_positions.keys():
                # Update velocity with damping
                velocities[xpath][0] = (velocities[xpath][0] + forces[xpath][0]) * damping
                velocities[xpath][1] = (velocities[xpath][1] + forces[xpath][1]) * damping
                
                # Update position
                current_positions[xpath][0] += velocities[xpath][0]
                current_positions[xpath][1] += velocities[xpath][1]
            
            # 5. Apply level constraints (keep nodes at their designated vertical levels)
            # Group nodes by level
            nodes_by_level = {}
            for node in nodes:
                if node.level not in nodes_by_level:
                    nodes_by_level[node.level] = []
                nodes_by_level[node.level].append(node)
            
            # Enforce vertical positioning by level
            for level, level_nodes in nodes_by_level.items():
                target_y = level * self.min_level_distance + 100
                for node in level_nodes:
                    # Gradually pull nodes toward their target Y position
                    current_y = current_positions[node.xpath][1]
                    dy = target_y - current_y
                    current_positions[node.xpath][1] += dy * 0.3  # 30% correction per iteration
        
        # Convert back to tuples
        return {k: (v[0], v[1]) for k, v in current_positions.items()}
    
    def _detect_collisions(self, positions: Dict[str, Tuple[float, float]], 
                          min_distance: float = 80.0) -> bool:
        """
        Detect if any nodes are too close
        
        Args:
            positions: Current node positions
            min_distance: Minimum allowed distance between nodes
            
        Returns:
            True if collisions detected, False otherwise
        """
        node_list = list(positions.items())
        for i in range(len(node_list)):
            for j in range(i + 1, len(node_list)):
                xpath1, pos1 = node_list[i]
                xpath2, pos2 = node_list[j]
                dx = pos2[0] - pos1[0]
                dy = pos2[1] - pos1[1]
                distance = math.sqrt(dx * dx + dy * dy)
                if distance < min_distance:
                    return True
        return False
    
    def _resolve_collisions(self, positions: Dict[str, Tuple[float, float]], 
                           min_distance: float = 80.0,
                           nodes: List[MetroGraphNode] = None) -> Dict[str, Tuple[float, float]]:
        """
        Resolve node collisions by adjusting positions
        
        Args:
            positions: Current node positions
            min_distance: Minimum allowed distance (center-to-center)
            nodes: List of nodes (needed to determine bounding box sizes)
            
        Returns:
            Adjusted positions with collisions resolved
        """
        # Create mutable copy
        adjusted = {k: list(v) for k, v in positions.items()}
        
        # Build a map of xpath to node for bounding box lookup
        node_map = {}
        if nodes:
            for node in nodes:
                node_map[node.xpath] = node
        
        def get_node_size(xpath: str) -> Tuple[float, float]:
            """Get width and height for a node"""
            if xpath in node_map:
                node = node_map[xpath]
                if node.level == 0:
                    return (self.root_node_width, self.root_node_height)
            return (self.standard_node_width, self.standard_node_height)
        
        def check_box_collision(xpath1: str, pos1: List[float], 
                               xpath2: str, pos2: List[float]) -> bool:
            """Check if two nodes' bounding boxes overlap"""
            w1, h1 = get_node_size(xpath1)
            w2, h2 = get_node_size(xpath2)
            
            # Calculate bounding boxes
            x1_min, y1_min = pos1[0] - w1/2, pos1[1] - h1/2
            x1_max, y1_max = pos1[0] + w1/2, pos1[1] + h1/2
            x2_min, y2_min = pos2[0] - w2/2, pos2[1] - h2/2
            x2_max, y2_max = pos2[0] + w2/2, pos2[1] + h2/2
            
            # Check for overlap
            x_overlap = not (x1_max < x2_min or x2_max < x1_min)
            y_overlap = not (y1_max < y2_min or y2_max < y1_min)
            
            return x_overlap and y_overlap
        
        # Iteratively resolve collisions
        max_iterations = 100
        for iteration in range(max_iterations):
            collision_found = False
            node_list = list(adjusted.items())
            
            for i in range(len(node_list)):
                for j in range(i + 1, len(node_list)):
                    xpath1, pos1 = node_list[i]
                    xpath2, pos2 = node_list[j]
                    
                    # Check for bounding box collision
                    if check_box_collision(xpath1, pos1, xpath2, pos2):
                        collision_found = True
                        
                        # Calculate separation vector
                        dx = pos2[0] - pos1[0]
                        dy = pos2[1] - pos1[1]
                        distance = math.sqrt(dx * dx + dy * dy)
                        
                        if distance < 0.1:
                            # Nodes are at same position, push them apart horizontally
                            dx = 1.0
                            dy = 0.0
                            distance = 1.0
                        
                        # Calculate required separation based on bounding boxes
                        w1, h1 = get_node_size(xpath1)
                        w2, h2 = get_node_size(xpath2)
                        
                        # Required distance is sum of half-widths plus min_distance
                        required_dist = (w1 + w2) / 2 + 10  # 10 pixel margin
                        
                        if distance < required_dist:
                            overlap = required_dist - distance
                            separation_x = (dx / distance) * overlap * 0.5
                            separation_y = (dy / distance) * overlap * 0.5
                            
                            # Move nodes apart (only horizontally to preserve level alignment)
                            adjusted[xpath1][0] -= separation_x
                            adjusted[xpath2][0] += separation_x
            
            # If no collisions found, we're done
            if not collision_found:
                break
        
        # Convert back to tuples
        return {k: (v[0], v[1]) for k, v in adjusted.items()}


class StationNode(QGraphicsItem):
    """Graphical representation of XML node as metro station"""
    
    def __init__(self, metro_node: MetroGraphNode, parent=None):
        """Initialize station node"""
        super().__init__(parent)
        self.metro_node = metro_node
        self.zoom_level = 1.0
        self._is_selected = False
        self._is_highlighted = False
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setAcceptHoverEvents(True)
        
        # Metro station colors based on level
        self.colors = {
            0: QColor(220, 50, 50),    # Root: Red
            1: QColor(50, 120, 220),   # Level 1: Blue
            2: QColor(50, 180, 100)    # Level 2: Green
        }
    
    def boundingRect(self) -> QRectF:
        """Return bounding rectangle"""
        # Base size depends on level (root is larger)
        if self.metro_node.level == 0:
            return QRectF(-50, -30, 100, 60)
        else:
            return QRectF(-40, -25, 80, 50)
    
    def paint(self, painter: QPainter, option, widget):
        """Paint station node in metro style"""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        rect = self.boundingRect()
        
        # Determine colors based on state
        base_color = self.colors.get(self.metro_node.level, QColor(100, 100, 100))
        
        if self._is_highlighted:
            # Highlighted: brighter color
            base_color = base_color.lighter(130)
        
        if self._is_selected or self.isSelected():
            # Selected: add yellow border
            painter.setPen(QPen(QColor(255, 200, 0), 3))
        else:
            # Normal: dark border
            painter.setPen(QPen(QColor(40, 40, 40), 2))
        
        # Fill with base color
        painter.setBrush(QBrush(base_color))
        
        # Draw rounded rectangle for metro station look
        corner_radius = 8 if self.metro_node.level == 0 else 6
        painter.drawRoundedRect(rect, corner_radius, corner_radius)
        
        # Adaptive display based on zoom level
        if self.zoom_level < 0.5:
            # Simplified mode: only show name
            self._draw_simplified(painter, rect)
        elif self.zoom_level > 1.5:
            # Detailed mode: show name + attributes + child count
            self._draw_detailed(painter, rect)
        else:
            # Normal mode: show name + child count badge
            self._draw_normal(painter, rect)
    
    def _draw_simplified(self, painter: QPainter, rect: QRectF):
        """Draw simplified view (zoom < 0.5): only name"""
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        font = QFont("Arial", 8, QFont.Weight.Bold)
        painter.setFont(font)
        
        # Truncate name if too long
        display_name = self.metro_node.display_name
        if len(display_name) > 10:
            display_name = display_name[:8] + "..."
        
        # Draw text centered
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, display_name)
    
    def _draw_normal(self, painter: QPainter, rect: QRectF):
        """Draw normal view (0.5 <= zoom <= 1.5): name + child badge"""
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        font = QFont("Arial", 10 if self.metro_node.level == 0 else 9, QFont.Weight.Bold)
        painter.setFont(font)
        
        # Truncate name if too long
        display_name = self.metro_node.display_name
        if len(display_name) > 15:
            display_name = display_name[:12] + "..."
        
        # Draw text centered
        text_rect = rect.adjusted(5, 5, -5, -5)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, display_name)
        
        # Draw child count indicator badge (if has children)
        if self.metro_node.child_count > 0:
            self._draw_child_badge(painter, rect)
    
    def _draw_detailed(self, painter: QPainter, rect: QRectF):
        """Draw detailed view (zoom > 1.5): name + attributes + child count"""
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        
        # Draw node name at top
        font = QFont("Arial", 10 if self.metro_node.level == 0 else 9, QFont.Weight.Bold)
        painter.setFont(font)
        
        display_name = self.metro_node.display_name
        if len(display_name) > 15:
            display_name = display_name[:12] + "..."
        
        name_rect = QRectF(rect.left() + 5, rect.top() + 5, rect.width() - 10, 15)
        painter.drawText(name_rect, Qt.AlignmentFlag.AlignCenter, display_name)
        
        # Draw attributes (if any) in smaller font
        if self.metro_node.xml_node.attributes:
            font_small = QFont("Arial", 7)
            painter.setFont(font_small)
            
            # Show first 2 attributes
            y_offset = rect.top() + 22
            attr_count = 0
            for key, value in self.metro_node.xml_node.attributes.items():
                if attr_count >= 2:
                    break
                attr_text = f"{key}={value[:8]}" if len(value) > 8 else f"{key}={value}"
                if len(attr_text) > 15:
                    attr_text = attr_text[:12] + "..."
                
                attr_rect = QRectF(rect.left() + 5, y_offset, rect.width() - 10, 10)
                painter.drawText(attr_rect, Qt.AlignmentFlag.AlignLeft, attr_text)
                y_offset += 10
                attr_count += 1
        
        # Draw child count at bottom
        if self.metro_node.child_count > 0:
            font_small = QFont("Arial", 8, QFont.Weight.Bold)
            painter.setFont(font_small)
            child_text = f"Children: {self.metro_node.child_count}"
            child_rect = QRectF(rect.left() + 5, rect.bottom() - 15, rect.width() - 10, 12)
            painter.drawText(child_rect, Qt.AlignmentFlag.AlignCenter, child_text)
    
    def _draw_child_badge(self, painter: QPainter, rect: QRectF):
        """Draw badge showing number of children"""
        # Position badge at bottom-right corner
        badge_size = 16
        badge_x = rect.right() - badge_size - 2
        badge_y = rect.bottom() - badge_size - 2
        badge_rect = QRectF(badge_x, badge_y, badge_size, badge_size)
        
        # Draw badge circle
        painter.setPen(QPen(QColor(40, 40, 40), 1))
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawEllipse(badge_rect)
        
        # Draw count text
        painter.setPen(QPen(QColor(40, 40, 40), 1))
        font = QFont("Arial", 8, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, str(self.metro_node.child_count))
    
    def set_selected(self, selected: bool):
        """Set selection state"""
        self._is_selected = selected
        self.setSelected(selected)
        self.update()
    
    def set_highlighted(self, highlighted: bool):
        """Set highlight state for path visualization"""
        self._is_highlighted = highlighted
        self.update()
    
    def set_zoom_level(self, zoom: float):
        """
        Adjust display based on zoom level
        
        Args:
            zoom: Current zoom ratio
        """
        self.zoom_level = zoom
        self.update()
    
    def mousePressEvent(self, event):
        """Handle mouse click"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Single click: select node and highlight path
            self.set_selected(True)
            # Emit signal through scene
            if self.scene():
                self.scene().node_selected.emit(self.metro_node)
                # Also highlight the path to this node
                self.scene().highlight_path(self.metro_node.xpath)
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        """Handle double click to open in editor"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Double click: request to open in editor
            if self.scene() and hasattr(self.scene(), 'open_in_editor_requested'):
                self.scene().open_in_editor_requested.emit(self.metro_node.xpath)
        super().mouseDoubleClickEvent(event)
    
    def hoverEnterEvent(self, event):
        """Handle mouse hover enter"""
        # Show tooltip with node information
        tooltip_text = f"{self.metro_node.display_name}"
        if self.metro_node.xml_node.attributes:
            tooltip_text += "\n\nAttributes:"
            for key, value in list(self.metro_node.xml_node.attributes.items())[:3]:
                tooltip_text += f"\n  {key}={value}"
            if len(self.metro_node.xml_node.attributes) > 3:
                tooltip_text += f"\n  ... and {len(self.metro_node.xml_node.attributes) - 3} more"
        if self.metro_node.child_count > 0:
            tooltip_text += f"\n\nChildren: {self.metro_node.child_count}"
        
        self.setToolTip(tooltip_text)
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        """Handle mouse hover leave"""
        super().hoverLeaveEvent(event)


class ConnectionLine(QGraphicsLineItem):
    """Connection line between parent and child stations"""
    
    def __init__(self, start_node: StationNode, end_node: StationNode, parent=None):
        """Initialize connection line"""
        super().__init__(parent)
        self.start_node = start_node
        self.end_node = end_node
        self._is_highlighted = False
        
        # Metro line style: solid, medium thickness
        self.normal_pen = QPen(QColor(100, 100, 100), 2)
        self.highlighted_pen = QPen(QColor(255, 200, 0), 3)
        
        self.setPen(self.normal_pen)
        self.setZValue(-1)  # Draw lines behind nodes
    
    def paint(self, painter: QPainter, option, widget):
        """Paint connection line with metro style"""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Use highlighted pen if highlighted
        if self._is_highlighted:
            painter.setPen(self.highlighted_pen)
        else:
            painter.setPen(self.normal_pen)
        
        # Get start and end positions
        start_pos = self.start_node.scenePos()
        end_pos = self.end_node.scenePos()
        
        # Draw line with rounded corners (metro style)
        # For now, draw a simple line - can be enhanced with curves later
        painter.drawLine(start_pos, end_pos)
    
    def update_position(self):
        """Update line position based on node positions"""
        start_pos = self.start_node.scenePos()
        end_pos = self.end_node.scenePos()
        self.setLine(start_pos.x(), start_pos.y(), end_pos.x(), end_pos.y())
    
    def set_highlighted(self, highlighted: bool):
        """Set highlight state"""
        self._is_highlighted = highlighted
        self.update()


class MetroCanvasScene(QGraphicsScene):
    """Scene managing station nodes and connections"""
    
    node_selected = pyqtSignal(object)  # Emits MetroGraphNode
    open_in_editor_requested = pyqtSignal(str)  # Emits XPath
    
    def __init__(self, parent=None):
        """Initialize scene"""
        super().__init__(parent)
        self.metro_root = None
        self.station_nodes = {}
        self.connection_lines = []
    
    def build_graph(self, root_node: XmlTreeNode):
        """Build graph from XML tree structure"""
        self.clear_graph()
        
        if root_node is None:
            raise ValueError("Cannot build graph: root_node is None")
        
        # Extract 3 levels
        limited_tree = extract_three_levels_from_tree(root_node)
        if limited_tree is None:
            raise ValueError("Failed to extract tree levels")
        
        # Convert to metro graph
        self.metro_root = convert_to_metro_graph(limited_tree)
        if self.metro_root is None:
            raise ValueError("Failed to convert to metro graph")
        
        # Compute layout
        engine = MetroLayoutEngine()
        positions = engine.compute_layout(self.metro_root)
        
        if not positions:
            raise ValueError("Failed to compute layout: no positions generated")
        
        # Create visual nodes
        self._create_visual_nodes(self.metro_root, positions)
        
        # Trigger virtualization update in the view if available
        for view in self.views():
            if hasattr(view, '_update_virtualization'):
                view._update_virtualization()
    
    def _create_visual_nodes(self, metro_node: MetroGraphNode, 
                            positions: Dict[str, Tuple[float, float]]):
        """Recursively create visual nodes"""
        # Create station node
        station = StationNode(metro_node)
        pos = positions.get(metro_node.xpath, (0, 0))
        station.setPos(pos[0], pos[1])
        self.addItem(station)
        self.station_nodes[metro_node.xpath] = station
        
        # Create connections and recurse to children
        for child in metro_node.children:
            self._create_visual_nodes(child, positions)
            
            # Create connection line
            child_station = self.station_nodes.get(child.xpath)
            if child_station:
                line = ConnectionLine(station, child_station)
                line.update_position()
                self.addItem(line)
                self.connection_lines.append(line)
    
    def update_zoom_level(self, zoom: float):
        """Update zoom level for all station nodes"""
        for station in self.station_nodes.values():
            station.set_zoom_level(zoom)
    
    def select_node(self, xpath: str):
        """
        Select node by XPath
        
        Args:
            xpath: XPath of node to select
        """
        # Clear previous selection
        for station in self.station_nodes.values():
            station.set_selected(False)
        
        # Select the target node
        if xpath in self.station_nodes:
            station = self.station_nodes[xpath]
            station.set_selected(True)
            # Emit signal
            self.node_selected.emit(station.metro_node)
    
    def highlight_path(self, xpath: str):
        """
        Highlight path from root to node
        
        Args:
            xpath: XPath of target node
        """
        # Clear previous highlighting
        for station in self.station_nodes.values():
            station.set_highlighted(False)
        for line in self.connection_lines:
            line.set_highlighted(False)
        
        # Find the target node
        if xpath not in self.station_nodes:
            return
        
        target_station = self.station_nodes[xpath]
        target_node = target_station.metro_node
        
        # Build path from root to target
        path_nodes = []
        current = target_node
        while current is not None:
            path_nodes.append(current)
            current = current.parent
        
        # Reverse to get root-to-target order
        path_nodes.reverse()
        
        # Highlight nodes in path
        for node in path_nodes:
            if node.xpath in self.station_nodes:
                self.station_nodes[node.xpath].set_highlighted(True)
        
        # Highlight connections in path
        for i in range(len(path_nodes) - 1):
            parent_xpath = path_nodes[i].xpath
            child_xpath = path_nodes[i + 1].xpath
            
            # Find the connection line between parent and child
            for line in self.connection_lines:
                if (line.start_node.metro_node.xpath == parent_xpath and 
                    line.end_node.metro_node.xpath == child_xpath):
                    line.set_highlighted(True)
                    break
    
    def clear_graph(self):
        """Clear all nodes and connections"""
        self.clear()
        self.station_nodes.clear()
        self.connection_lines.clear()
        self.metro_root = None


class MetroCanvasView(QGraphicsView):
    """Interactive canvas view with zoom and pan support"""
    
    zoom_changed = pyqtSignal(float)  # Emits zoom ratio
    
    def __init__(self, parent=None):
        """Initialize canvas view"""
        super().__init__(parent)
        self.current_zoom = 1.0
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.virtualization_threshold = 100
        self.viewport_margin = 200  # Margin in pixels around viewport for pre-loading
    
    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel for zooming"""
        # Zoom with Ctrl key
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            new_zoom = self.current_zoom * factor
            
            # Clamp zoom to [0.25, 4.0]
            new_zoom = max(0.25, min(4.0, new_zoom))
            
            if new_zoom != self.current_zoom:
                scale_factor = new_zoom / self.current_zoom
                self.scale(scale_factor, scale_factor)
                self.current_zoom = new_zoom
                self.zoom_changed.emit(self.current_zoom)
                
                # Update virtualization after zoom
                self._update_virtualization()
        else:
            super().wheelEvent(event)
    
    def scrollContentsBy(self, dx: int, dy: int):
        """Override to update virtualization when scrolling"""
        super().scrollContentsBy(dx, dy)
        self._update_virtualization()
    
    def set_zoom(self, zoom_ratio: float):
        """Set zoom level"""
        zoom_ratio = max(0.25, min(4.0, zoom_ratio))
        if zoom_ratio != self.current_zoom:
            scale_factor = zoom_ratio / self.current_zoom
            self.scale(scale_factor, scale_factor)
            self.current_zoom = zoom_ratio
            self.zoom_changed.emit(self.current_zoom)
            
            # Update virtualization after zoom change
            self._update_virtualization()
    
    def fit_to_view(self):
        """Automatically fit entire graph to view"""
        if self.scene():
            self.fitInView(self.scene().itemsBoundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
            # Update zoom level based on transform
            transform = self.transform()
            self.current_zoom = transform.m11()
            self.zoom_changed.emit(self.current_zoom)
            
            # Update virtualization after fit
            self._update_virtualization()
    
    def _update_virtualization(self):
        """
        Update node visibility based on viewport for large graphs
        
        For graphs with more than 100 nodes, only render nodes within
        the current viewport plus a margin.
        """
        if not self.scene():
            return
        
        # Check if we have a MetroCanvasScene with station nodes
        if not hasattr(self.scene(), 'station_nodes'):
            return
        
        station_nodes = self.scene().station_nodes
        
        # Only apply virtualization for large graphs (>100 nodes)
        if len(station_nodes) <= self.virtualization_threshold:
            # For small graphs, ensure all nodes are visible
            for station in station_nodes.values():
                station.setVisible(True)
            return
        
        # Get visible rect in scene coordinates
        visible_rect = self.mapToScene(self.viewport().rect()).boundingRect()
        
        # Expand rect by margin for pre-loading
        margin = self.viewport_margin / self.current_zoom  # Adjust margin for zoom level
        expanded_rect = visible_rect.adjusted(-margin, -margin, margin, margin)
        
        # Update visibility for each station node
        for station in station_nodes.values():
            # Check if station's bounding rect intersects with expanded viewport
            station_rect = station.sceneBoundingRect()
            is_visible = expanded_rect.intersects(station_rect)
            station.setVisible(is_visible)
        
        # Connection lines visibility is handled automatically by Qt
        # (they're hidden when their connected nodes are hidden)


class NodeInfoPanel(QWidget):
    """Information panel for selected node"""
    
    open_in_editor_requested = pyqtSignal(str)  # Emits XPath
    
    def __init__(self, parent=None):
        """Initialize info panel"""
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup UI components"""
        layout = QVBoxLayout(self)
        
        self.name_label = QLabel("No node selected")
        self.name_label.setWordWrap(True)
        layout.addWidget(self.name_label)
        
        self.attrs_label = QLabel("")
        self.attrs_label.setWordWrap(True)
        layout.addWidget(self.attrs_label)
        
        self.children_label = QLabel("")
        layout.addWidget(self.children_label)
        
        self.open_button = QPushButton("Open in Editor")
        self.open_button.clicked.connect(self._on_open_clicked)
        self.open_button.setEnabled(False)
        layout.addWidget(self.open_button)
        
        layout.addStretch()
        
        self.current_xpath = None
    
    def show_node_info(self, metro_node: MetroGraphNode):
        """Display information about selected node"""
        if metro_node is None:
            self.clear()
            return
        
        self.current_xpath = metro_node.xpath
        self.name_label.setText(f"<b>{metro_node.display_name}</b>")
        
        # Show attributes
        if metro_node.xml_node.attributes:
            attrs_text = "Attributes:\n" + "\n".join(
                f"  {k}={v}" for k, v in metro_node.xml_node.attributes.items()
            )
            self.attrs_label.setText(attrs_text)
        else:
            self.attrs_label.setText("No attributes")
        
        # Show children count
        self.children_label.setText(f"Children: {metro_node.child_count}")
        
        self.open_button.setEnabled(True)
    
    def clear(self):
        """Clear panel content"""
        self.name_label.setText("No node selected")
        self.attrs_label.setText("")
        self.children_label.setText("")
        self.open_button.setEnabled(False)
        self.current_xpath = None
    
    def _on_open_clicked(self):
        """Handle open in editor button click"""
        if self.current_xpath:
            self.open_in_editor_requested.emit(self.current_xpath)


class MetroNavigatorWindow(QMainWindow):
    """Main window for XML Metro Navigator"""
    
    node_selected = pyqtSignal(object)  # Emits XmlTreeNode
    
    def __init__(self, root_node: Optional[XmlTreeNode] = None, parent=None):
        """Initialize navigator window"""
        super().__init__(parent)
        self.setWindowTitle("XML Metro Navigator")
        self.resize(1200, 800)
        
        self._setup_ui()
        
        if root_node:
            self.load_from_tree(root_node)
    
    def _setup_ui(self):
        """Setup UI components"""
        # Create central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        
        # Create canvas view and scene
        self.scene = MetroCanvasScene()
        self.view = MetroCanvasView()
        self.view.setScene(self.scene)
        layout.addWidget(self.view, stretch=3)
        
        # Create info panel
        self.info_panel = NodeInfoPanel()
        layout.addWidget(self.info_panel, stretch=1)
        
        # Create toolbar
        self._create_toolbar()
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.zoom_label = QLabel("Zoom: 100%")
        self.status_bar.addPermanentWidget(self.zoom_label)
        
        # Connect signals
        self.view.zoom_changed.connect(self._on_zoom_changed)
        self.view.zoom_changed.connect(self.scene.update_zoom_level)
        self.scene.node_selected.connect(self.info_panel.show_node_info)
        self.scene.node_selected.connect(self._on_node_selected)
        self.info_panel.open_in_editor_requested.connect(self.scene.open_in_editor_requested.emit)
    
    def _create_toolbar(self):
        """Create toolbar with navigation controls"""
        toolbar = QToolBar("Navigation")
        self.addToolBar(toolbar)
        
        # Refresh action
        self.refresh_action = toolbar.addAction("Refresh Navigator")
        self.refresh_action.triggered.connect(self._refresh_graph)
        self.refresh_action.setVisible(False)  # Hidden by default
        self.refresh_action.setToolTip("Reload the graph from the current XML tree")
        
        toolbar.addSeparator()
        
        # Fit to view action
        fit_action = toolbar.addAction("Fit to View")
        fit_action.triggered.connect(self.view.fit_to_view)
        
        # Zoom in action
        zoom_in_action = toolbar.addAction("Zoom In")
        zoom_in_action.triggered.connect(lambda: self.view.set_zoom(self.view.current_zoom * 1.2))
        
        # Zoom out action
        zoom_out_action = toolbar.addAction("Zoom Out")
        zoom_out_action.triggered.connect(lambda: self.view.set_zoom(self.view.current_zoom / 1.2))
    
    def _refresh_graph(self):
        """Refresh the graph from the parent editor"""
        try:
            # Get the parent main window
            parent = self.parent()
            if parent and hasattr(parent, 'xml_tree'):
                # Get root node from parent's tree
                if parent.xml_tree.topLevelItemCount() > 0:
                    root_item = parent.xml_tree.topLevelItem(0)
                    if root_item and hasattr(root_item, 'xml_node'):
                        root_node = root_item.xml_node
                        self.load_from_tree(root_node)
                        self.refresh_action.setVisible(False)
                        self.status_bar.showMessage("Graph refreshed", 3000)
                        return
            
            # Fallback: show message
            QMessageBox.information(
                self,
                "Cannot Refresh",
                "Unable to refresh the graph.\n\n"
                "Please close and reopen the navigator."
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Refresh Error",
                f"Failed to refresh graph:\n{str(e)}"
            )
    
    def show_refresh_button(self):
        """Show the refresh button to indicate changes"""
        if hasattr(self, 'refresh_action'):
            self.refresh_action.setVisible(True)
            self.status_bar.showMessage("XML has changed - click Refresh to update", 5000)
    
    def load_from_tree(self, root_node: XmlTreeNode):
        """Load and visualize from existing XmlTreeNode"""
        if root_node is None:
            QMessageBox.warning(
                self, 
                "No XML Tree", 
                "Cannot load navigator: No XML tree provided.\n\n"
                "Please ensure the XML document is properly parsed before opening the navigator."
            )
            return
        
        try:
            self.scene.build_graph(root_node)
            self.view.fit_to_view()
            self.status_bar.showMessage("Graph loaded successfully", 3000)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error Loading Graph",
                f"Failed to build metro graph:\n{str(e)}"
            )
            self.status_bar.showMessage("Failed to load graph", 5000)
    
    def load_xml(self, xml_content: str):
        """
        Load and visualize XML content (fallback for standalone use)
        
        Args:
            xml_content: XML content string
            
        Note:
            This method is for standalone use when the navigator is opened
            without the main editor. It uses XmlService to parse the XML.
            For integration with the editor, use load_from_tree() instead.
        """
        if not xml_content or not xml_content.strip():
            QMessageBox.warning(
                self,
                "Empty XML",
                "Cannot load navigator: XML content is empty."
            )
            return
        
        try:
            # Parse XML and build tree using XmlService
            xml_service = XmlService()
            root_node = xml_service.build_xml_tree(xml_content)
            
            if root_node is None:
                QMessageBox.warning(
                    self,
                    "Parse Error",
                    "Failed to parse XML content.\n\n"
                    "Please ensure the XML is well-formed."
                )
                return
            
            # Use the existing load_from_tree method
            self.load_from_tree(root_node)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error Parsing XML",
                f"Failed to parse XML content:\n{str(e)}"
            )
            self.status_bar.showMessage("Failed to parse XML", 5000)
    
    def sync_with_editor(self, xpath: str):
        """
        Synchronize selection with main editor
        
        Args:
            xpath: XPath of selected node in editor
            
        Note:
            This method is called when a node is selected in the main editor
            to highlight and scroll to the corresponding node in the navigator.
        """
        if not xpath:
            return
        
        try:
            # Select the node in the scene
            self.scene.select_node(xpath)
            
            # Highlight the path to the node
            self.scene.highlight_path(xpath)
            
            # Get the station node to center the view on it
            if xpath in self.scene.station_nodes:
                station = self.scene.station_nodes[xpath]
                # Center the view on the selected node
                self.view.centerOn(station)
                
        except Exception as e:
            print(f"Error syncing with editor: {e}")
            # Don't show error dialog for sync issues, just log it
    
    def _on_zoom_changed(self, zoom: float):
        """Handle zoom level change"""
        self.zoom_label.setText(f"Zoom: {int(zoom * 100)}%")
    
    def _on_node_selected(self, metro_node: MetroGraphNode):
        """Handle node selection in scene"""
        # Emit the window's node_selected signal with the XmlTreeNode
        if metro_node and metro_node.xml_node:
            self.node_selected.emit(metro_node.xml_node)
    
    def get_current_settings(self) -> MetroNavigatorSettings:
        """Get current zoom and position settings"""
        return MetroNavigatorSettings(
            zoom_level=self.view.current_zoom,
            center_x=self.view.horizontalScrollBar().value(),
            center_y=self.view.verticalScrollBar().value()
        )
    
    def restore_settings(self, settings: MetroNavigatorSettings):
        """Restore zoom and position from settings"""
        if settings:
            self.view.set_zoom(settings.zoom_level)
            self.view.horizontalScrollBar().setValue(int(settings.center_x))
            self.view.verticalScrollBar().setValue(int(settings.center_y))
