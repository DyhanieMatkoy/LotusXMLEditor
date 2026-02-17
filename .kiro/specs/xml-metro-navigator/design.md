# Design Document: XML Metro Navigator

## Overview

XML Metro Navigator - это интерактивный графический инструмент для визуализации и навигации по структуре XML-документов. Система представляет иерархию XML в виде карты железнодорожных станций (метро), где каждый узел отображается как станция, соединённая линиями с родительскими и дочерними узлами. Визуализация ограничена первыми тремя уровнями иерархии для обеспечения читаемости.

**Архитектурное решение:** Навигатор использует уже построенное дерево `XmlTreeNode` из основного редактора, что обеспечивает:
- ✅ Отсутствие повторного парсинга XML (быстрее)
- ✅ Использование кэшированных данных
- ✅ Сохранение всех метаданных (номера строк, XPath, атрибуты)
- ✅ Учёт пользовательских настроек дерева (глубина загрузки, скрытие листьев)

Ключевые особенности:
- Интеллектуальный алгоритм размещения узлов с минимизацией пересечений
- Масштабирование от 25% до 400% с адаптивным отображением деталей
- Интерактивное взаимодействие: клики, перетаскивание, выделение
- Интеграция с основным редактором XML
- Высокая производительность с виртуализацией для больших графов

## Architecture

### Архитектурный стиль

Система использует Model-View-Controller (MVC) архитектуру с дополнительным слоем для алгоритмов размещения:

```
┌─────────────────────────────────────────────────────────┐
│                    Main Application                      │
│                      (main.py)                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ├─ Opens/Integrates
                     ↓
┌─────────────────────────────────────────────────────────┐
│              MetroNavigatorWindow                        │
│              (metro_navigator.py)                       │
│  ┌─────────────────────────────────────────────────┐   │
│  │         MetroCanvasView (QGraphicsView)         │   │
│  │  ┌──────────────────────────────────────────┐   │   │
│  │  │    MetroCanvasScene (QGraphicsScene)     │   │   │
│  │  │  ┌────────────────────────────────────┐  │   │   │
│  │  │  │   StationNode (QGraphicsItem)      │  │   │   │
│  │  │  │   ConnectionLine (QGraphicsItem)   │  │   │   │
│  │  │  └────────────────────────────────────┘  │   │   │
│  │  └──────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │         MetroLayoutEngine                        │   │
│  │  - Force-directed layout                        │   │
│  │  - Collision detection                          │   │
│  │  - Layer-based positioning                      │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │         NodeInfoPanel (QWidget)                  │   │
│  │  - Selected node details                        │   │
│  │  - Attributes display                           │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                     │
                     ├─ Uses
                     ↓
┌─────────────────────────────────────────────────────────┐
│              XmlService (xml_service.py)                 │
│              XmlTreeNode (models.py)                     │
└─────────────────────────────────────────────────────────┘
```

### Компонентная структура

1. **MetroNavigatorWindow** - главное окно навигатора
2. **MetroCanvasView** - представление с поддержкой масштабирования и перетаскивания
3. **MetroCanvasScene** - сцена для отрисовки графа
4. **StationNode** - графический элемент станции
5. **ConnectionLine** - линия связи между станциями
6. **MetroLayoutEngine** - алгоритм размещения узлов
7. **NodeInfoPanel** - панель информации о выбранном узле

## Components and Interfaces

### 1. MetroNavigatorWindow

Главное окно приложения, управляющее всеми компонентами навигатора.

```python
class MetroNavigatorWindow(QMainWindow):
    """Main window for XML Metro Navigator"""
    
    def __init__(self, root_node: XmlTreeNode = None, parent=None):
        """
        Initialize navigator window
        
        Args:
            root_node: Root XmlTreeNode from main editor (preferred)
            parent: Parent widget
        """
        
    def load_from_tree(self, root_node: XmlTreeNode) -> None:
        """
        Load and visualize from existing XmlTreeNode
        
        Args:
            root_node: Root node from editor's tree
            
        Note:
            This is the preferred method as it reuses already parsed tree
        """
        
    def load_xml(self, xml_content: str) -> None:
        """
        Load and visualize XML content (fallback for standalone use)
        
        Args:
            xml_content: XML content string
        """
        
    def sync_with_editor(self, xpath: str) -> None:
        """
        Synchronize selection with main editor
        
        Args:
            xpath: XPath of selected node in editor
        """
        
    def get_current_settings(self) -> Dict[str, Any]:
        """Get current zoom and position settings"""
        
    def restore_settings(self, settings: Dict[str, Any]) -> None:
        """Restore zoom and position from settings"""
```

### 2. MetroCanvasView

Представление с поддержкой интерактивного взаимодействия.

```python
class MetroCanvasView(QGraphicsView):
    """Interactive canvas view with zoom and pan support"""
    
    zoom_changed = pyqtSignal(float)  # Emits zoom ratio
    
    def __init__(self, parent=None):
        """Initialize canvas view"""
        
    def wheelEvent(self, event: QWheelEvent) -> None:
        """Handle mouse wheel for zooming"""
        
    def set_zoom(self, zoom_ratio: float) -> None:
        """
        Set zoom level
        
        Args:
            zoom_ratio: Zoom ratio (0.25 to 4.0)
        """
        
    def fit_to_view(self) -> None:
        """Automatically fit entire graph to view"""
```

### 3. MetroCanvasScene

Сцена для управления графическими элементами.

```python
class MetroCanvasScene(QGraphicsScene):
    """Scene managing station nodes and connections"""
    
    node_selected = pyqtSignal(object)  # Emits XmlTreeNode
    
    def __init__(self, parent=None):
        """Initialize scene"""
        
    def build_graph(self, root_node: XmlTreeNode) -> None:
        """
        Build graph from XML tree structure
        
        Args:
            root_node: Root node of XML tree (limited to 3 levels)
        """
        
    def clear_graph(self) -> None:
        """Clear all nodes and connections"""
        
    def select_node(self, xpath: str) -> None:
        """
        Select node by XPath
        
        Args:
            xpath: XPath of node to select
        """
        
    def highlight_path(self, xpath: str) -> None:
        """
        Highlight path from root to node
        
        Args:
            xpath: XPath of target node
        """
```

### 4. StationNode

Графический элемент станции метро.

```python
class StationNode(QGraphicsItem):
    """Graphical representation of XML node as metro station"""
    
    def __init__(self, xml_node: XmlTreeNode, level: int, parent=None):
        """
        Initialize station node
        
        Args:
            xml_node: XML tree node data
            level: Depth level (0-2 for 3 levels)
            parent: Parent graphics item
        """
        
    def paint(self, painter: QPainter, option, widget) -> None:
        """Paint station node"""
        
    def boundingRect(self) -> QRectF:
        """Return bounding rectangle"""
        
    def set_selected(self, selected: bool) -> None:
        """Set selection state"""
        
    def set_highlighted(self, highlighted: bool) -> None:
        """Set highlight state for path visualization"""
        
    def set_zoom_level(self, zoom: float) -> None:
        """
        Adjust display based on zoom level
        
        Args:
            zoom: Current zoom ratio
        """
        
    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Handle mouse click"""
        
    def mouseDoubleClickEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Handle double click to open in editor"""
```

### 5. ConnectionLine

Линия связи между станциями.

```python
class ConnectionLine(QGraphicsLineItem):
    """Connection line between parent and child stations"""
    
    def __init__(self, start_node: StationNode, end_node: StationNode, parent=None):
        """
        Initialize connection line
        
        Args:
            start_node: Parent station node
            end_node: Child station node
            parent: Parent graphics item
        """
        
    def paint(self, painter: QPainter, option, widget) -> None:
        """Paint connection line with metro style"""
        
    def update_position(self) -> None:
        """Update line position based on node positions"""
        
    def set_highlighted(self, highlighted: bool) -> None:
        """Set highlight state"""
```

### 6. MetroLayoutEngine

Алгоритм интеллектуального размещения узлов.

```python
class MetroLayoutEngine:
    """Intelligent node layout algorithm"""
    
    def __init__(self):
        """Initialize layout engine"""
        
    def compute_layout(self, root_node: XmlTreeNode, 
                      canvas_width: float, 
                      canvas_height: float) -> Dict[str, Tuple[float, float]]:
        """
        Compute optimal positions for all nodes
        
        Args:
            root_node: Root of XML tree
            canvas_width: Available canvas width
            canvas_height: Available canvas height
            
        Returns:
            Dictionary mapping node XPath to (x, y) position
        """
        
    def _apply_force_directed_layout(self, nodes: List[XmlTreeNode], 
                                     iterations: int = 100) -> Dict[str, Tuple[float, float]]:
        """
        Apply force-directed layout algorithm
        
        Args:
            nodes: List of nodes to position
            iterations: Number of simulation iterations
            
        Returns:
            Node positions
        """
        
    def _detect_collisions(self, positions: Dict[str, Tuple[float, float]], 
                          min_distance: float = 80.0) -> bool:
        """
        Detect if any nodes are too close
        
        Args:
            positions: Current node positions
            min_distance: Minimum allowed distance between nodes
            
        Returns:
            True if collisions detected
        """
        
    def _resolve_collisions(self, positions: Dict[str, Tuple[float, float]], 
                           min_distance: float = 80.0) -> Dict[str, Tuple[float, float]]:
        """
        Resolve node collisions by adjusting positions
        
        Args:
            positions: Current node positions
            min_distance: Minimum allowed distance
            
        Returns:
            Adjusted positions
        """
```

### 7. NodeInfoPanel

Панель информации о выбранном узле.

```python
class NodeInfoPanel(QWidget):
    """Information panel for selected node"""
    
    open_in_editor_requested = pyqtSignal(str)  # Emits XPath
    
    def __init__(self, parent=None):
        """Initialize info panel"""
        
    def show_node_info(self, xml_node: XmlTreeNode) -> None:
        """
        Display information about selected node
        
        Args:
            xml_node: Selected XML tree node
        """
        
    def clear(self) -> None:
        """Clear panel content"""
```

### 8. Helper Functions

Вспомогательные функции для работы с деревом.

```python
def extract_three_levels_from_tree(root_node: XmlTreeNode) -> XmlTreeNode:
    """
    Extract first three levels from existing XmlTreeNode
    
    Args:
        root_node: Root node from editor's tree
        
    Returns:
        New XmlTreeNode with only first 3 levels (0, 1, 2)
        
    Note:
        This function reuses the already parsed tree structure,
        avoiding redundant XML parsing
    """
    
def convert_to_metro_graph(root_node: XmlTreeNode) -> MetroGraphNode:
    """
    Convert XmlTreeNode to MetroGraphNode structure
    
    Args:
        root_node: Root XmlTreeNode (limited to 3 levels)
        
    Returns:
        Root MetroGraphNode with positions initialized to (0, 0)
    """
```

## Data Models

### MetroGraphNode

Расширенная модель узла для графа метро.

```python
@dataclass
class MetroGraphNode:
    """Extended node model for metro graph"""
    xml_node: XmlTreeNode
    level: int  # 0, 1, or 2 (for 3 levels)
    position: Tuple[float, float]  # (x, y) coordinates
    children: List['MetroGraphNode'] = field(default_factory=list)
    parent: Optional['MetroGraphNode'] = None
    is_selected: bool = False
    is_highlighted: bool = False
    
    @property
    def xpath(self) -> str:
        """Get XPath of this node"""
        return self.xml_node.path
        
    @property
    def display_name(self) -> str:
        """Get display name for station"""
        return self.xml_node.name
        
    @property
    def child_count(self) -> int:
        """Get number of children"""
        return len(self.children)
```

### MetroNavigatorSettings

Настройки навигатора для сохранения состояния.

```python
@dataclass
class MetroNavigatorSettings:
    """Settings for metro navigator"""
    zoom_level: float = 1.0
    center_x: float = 0.0
    center_y: float = 0.0
    window_geometry: Optional[QRect] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MetroNavigatorSettings':
        """Create from dictionary"""
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Three-level depth limit

*For any* XML document, the metro navigator SHALL extract and display only the first three levels of the XML hierarchy, regardless of the total depth of the document.

**Validates: Requirements 1.2**

### Property 2: Minimum node spacing

*For any* computed layout, all station nodes SHALL maintain a minimum distance of 80 pixels from each other to ensure readability.

**Validates: Requirements 2.4**

### Property 3: Vertical level spacing

*For any* computed layout, nodes at different hierarchy levels SHALL be separated by at least 120 pixels vertically.

**Validates: Requirements 2.5**

### Property 4: Zoom range bounds

*For any* zoom operation, the resulting zoom level SHALL be within the range [0.25, 4.0] (25% to 400%).

**Validates: Requirements 5.1**

### Property 5: Node selection synchronization

*For any* node selection in the metro navigator, clicking the node SHALL emit a signal containing the correct XPath that can be used to locate the node in the main editor.

**Validates: Requirements 4.1, 7.3**

### Property 6: Path highlighting correctness

*For any* selected node, the highlighted path SHALL include all ancestor nodes from the root to the selected node, with no missing or extra nodes.

**Validates: Requirements 4.5**

### Property 7: Layout determinism

*For any* XML structure, running the layout algorithm multiple times with the same input SHALL produce positions that differ by no more than 1 pixel (accounting for floating-point precision).

**Validates: Requirements 2.1, 2.2**

### Property 8: Collision-free layout

*For any* final computed layout, no two station nodes SHALL have overlapping bounding rectangles.

**Validates: Requirements 2.1, 2.4**

### Property 9: Settings persistence round-trip

*For any* navigator settings (zoom, position), saving then loading the settings SHALL restore values that match the original within acceptable precision (0.01 for floats).

**Validates: Requirements 7.5**

### Property 10: Viewport virtualization threshold

*For any* graph with more than 100 nodes, the canvas SHALL render only nodes within the current viewport plus a margin, not all nodes.

**Validates: Requirements 6.1**

### Property 11: Frame rate maintenance

*For any* pan or zoom operation, the canvas SHALL maintain a frame rate of at least 30 FPS during the interaction.

**Validates: Requirements 6.2**

### Property 12: Adaptive detail display

*For any* zoom level below 0.5 (50%), station nodes SHALL display in simplified mode (name only), and for zoom above 1.5 (150%), SHALL display detailed mode (name + attributes + child count).

**Validates: Requirements 5.2, 5.3**

## Error Handling

### XML Parsing Errors

```python
def handle_parse_error(xml_content: str) -> Optional[str]:
    """
    Handle XML parsing errors gracefully
    
    Returns error message or None if successful
    """
    try:
        service = XmlService()
        root = service.parse_xml(xml_content)
        if root is None:
            return "Failed to parse XML: Invalid syntax"
        return None
    except Exception as e:
        return f"XML parsing error: {str(e)}"
```

### Layout Computation Errors

```python
def handle_layout_error(root_node: XmlTreeNode) -> bool:
    """
    Handle layout computation errors
    
    Returns True if layout succeeded, False otherwise
    """
    try:
        engine = MetroLayoutEngine()
        positions = engine.compute_layout(root_node, 2000, 1500)
        return len(positions) > 0
    except Exception as e:
        print(f"Layout computation failed: {e}")
        return False
```

### Empty or Invalid XML

- Если XML пустой или содержит только корневой элемент без детей, отобразить сообщение "No structure to visualize"
- Если XML имеет менее 3 уровней, отобразить доступные уровни
- Если узлов слишком много (>500), показать предупреждение о возможном снижении производительности

### Zoom Limits

- При попытке zoom за пределы [0.25, 4.0], ограничить значение границами
- Показать визуальную индикацию достижения предела (например, кратковременная анимация)

### Node Selection Errors

- Если XPath не найден при синхронизации, показать сообщение "Node not found in current view"
- Если узел находится за пределами 3 уровней, выбрать ближайшего видимого предка

## Testing Strategy

### Dual Testing Approach

Тестирование будет включать как unit-тесты для конкретных примеров, так и property-based тесты для проверки универсальных свойств.

**Unit Tests:**
- Конкретные примеры XML-структур (простые, вложенные, с атрибутами)
- Граничные случаи (пустой XML, один узел, ровно 3 уровня)
- Интеграционные точки (взаимодействие с XmlService, синхронизация с редактором)
- Специфические сценарии ошибок

**Property-Based Tests:**
- Универсальные свойства, которые должны выполняться для всех входных данных
- Генерация случайных XML-структур для проверки корректности
- Минимум 100 итераций на каждый property-тест

### Property-Based Testing Framework

Используем **Hypothesis** для Python - мощная библиотека для property-based testing.

```python
from hypothesis import given, strategies as st
from hypothesis.strategies import composite
import xml.etree.ElementTree as ET

@composite
def xml_tree_strategy(draw, max_depth=5, max_children=10):
    """Generate random XML tree structures"""
    # Strategy implementation
    pass
```

### Test Configuration

- Минимум 100 итераций для каждого property-теста
- Каждый тест должен ссылаться на свойство из документа проектирования
- Формат тега: `# Feature: xml-metro-navigator, Property {N}: {property_text}`

### Test Coverage Goals

- **Unit Tests**: Покрытие критических путей и граничных случаев
- **Property Tests**: Проверка всех 12 свойств корректности
- **Integration Tests**: Взаимодействие с основным приложением
- **Performance Tests**: Проверка требований производительности (FPS, время расчёта)

### Example Test Structure

```python
# Unit Test Example
def test_three_level_extraction():
    """Test that only 3 levels are extracted from deep XML"""
    xml = """
    <root>
        <level1>
            <level2>
                <level3>
                    <level4>Should not appear</level4>
                </level3>
            </level2>
        </level1>
    </root>
    """
    navigator = MetroNavigatorWindow(xml)
    nodes = navigator.get_all_nodes()
    max_level = max(node.level for node in nodes)
    assert max_level == 2  # 0, 1, 2 = 3 levels

# Property Test Example
@given(xml_tree_strategy(max_depth=10))
def test_property_three_level_limit(xml_tree):
    """
    Feature: xml-metro-navigator, Property 1: Three-level depth limit
    For any XML document, only first 3 levels are displayed
    """
    xml_string = ET.tostring(xml_tree, encoding='unicode')
    navigator = MetroNavigatorWindow(xml_string)
    nodes = navigator.get_all_nodes()
    
    # Property: all nodes must be at level 0, 1, or 2
    assert all(node.level <= 2 for node in nodes)
```

## Implementation Notes

### Force-Directed Layout Algorithm

Алгоритм основан на физической симуляции:

1. **Repulsive Force**: Все узлы отталкиваются друг от друга (закон Кулона)
2. **Attractive Force**: Связанные узлы притягиваются (закон Гука)
3. **Layer Constraint**: Узлы одного уровня выравниваются по вертикали
4. **Iteration**: Симуляция выполняется 100-200 итераций до стабилизации

```python
def compute_forces(nodes, edges):
    """Compute repulsive and attractive forces"""
    forces = {node.xpath: (0.0, 0.0) for node in nodes}
    
    # Repulsive forces between all pairs
    for i, node1 in enumerate(nodes):
        for node2 in nodes[i+1:]:
            dx = node2.position[0] - node1.position[0]
            dy = node2.position[1] - node1.position[1]
            distance = math.sqrt(dx*dx + dy*dy)
            if distance > 0:
                repulsion = REPULSION_CONSTANT / (distance * distance)
                fx = (dx / distance) * repulsion
                fy = (dy / distance) * repulsion
                forces[node1.xpath] = (forces[node1.xpath][0] - fx, 
                                      forces[node1.xpath][1] - fy)
                forces[node2.xpath] = (forces[node2.xpath][0] + fx,
                                      forces[node2.xpath][1] + fy)
    
    # Attractive forces along edges
    for parent, child in edges:
        dx = child.position[0] - parent.position[0]
        dy = child.position[1] - parent.position[1]
        distance = math.sqrt(dx*dx + dy*dy)
        if distance > 0:
            attraction = SPRING_CONSTANT * distance
            fx = (dx / distance) * attraction
            fy = (dy / distance) * attraction
            forces[parent.xpath] = (forces[parent.xpath][0] + fx,
                                   forces[parent.xpath][1] + fy)
            forces[child.xpath] = (forces[child.xpath][0] - fx,
                                  forces[child.xpath][1] - fy)
    
    return forces
```

### Performance Optimizations

1. **Viewport Culling**: Отрисовка только видимых узлов
2. **Level of Detail (LOD)**: Упрощение отображения при малом масштабе
3. **Caching**: Кэширование вычисленных позиций
4. **Incremental Updates**: Обновление только изменённых элементов

### Integration with Main Application

```python
# In main.py, add menu action
def create_metro_navigator_action(self):
    """Create menu action for metro navigator"""
    action = QAction("XML Metro Navigator", self)
    action.setShortcut("Ctrl+M")
    action.triggered.connect(self.open_metro_navigator)
    return action

def open_metro_navigator(self):
    """Open metro navigator window"""
    # Get existing tree from editor
    root_item = self.xml_tree.topLevelItem(0)
    if not root_item or not hasattr(root_item, 'xml_node'):
        QMessageBox.information(self, "No XML Tree", 
                               "Please open and parse an XML file first")
        return
    
    root_node = root_item.xml_node
    
    # Create navigator with existing tree (no re-parsing needed!)
    self.metro_window = MetroNavigatorWindow(root_node, parent=self)
    self.metro_window.node_selected.connect(self.sync_editor_to_node)
    self.metro_window.show()
    
def sync_editor_to_node(self, xml_node: XmlTreeNode):
    """Sync editor cursor to selected node"""
    if xml_node and xml_node.line_number > 0:
        # Move cursor to line in editor
        cursor = self.xml_editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        cursor.movePosition(QTextCursor.MoveOperation.Down, 
                          QTextCursor.MoveMode.MoveAnchor, 
                          xml_node.line_number - 1)
        self.xml_editor.setTextCursor(cursor)
        self.xml_editor.centerCursor()
```

**Преимущества этого подхода:**
1. ✅ Не требуется повторный парсинг XML
2. ✅ Используется уже построенное и кэшированное дерево
3. ✅ Сохраняются все метаданные (line_number, path, attributes)
4. ✅ Учитываются настройки дерева (max_load_depth, hide_leaves)
5. ✅ Быстрее - нет overhead на парсинг

## Future Enhancements

1. **Animated Transitions**: Плавная анимация при изменении структуры
2. **Search and Filter**: Поиск узлов по имени/атрибутам
3. **Export to Image**: Экспорт карты в PNG/SVG
4. **Custom Themes**: Различные цветовые схемы (метро разных городов)
5. **Minimap**: Миникарта для навигации по большим графам
6. **Collapsible Branches**: Возможность сворачивать ветви графа
