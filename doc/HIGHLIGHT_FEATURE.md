# Orange Border Highlighting Feature

## Overview
When you click on a tree node in the XML tree view, the corresponding text block in the editor is now visually highlighted with an orange border effect, and the status bar displays the size of the block in lines.

## Features

### Visual Highlighting
- **Orange Background**: The selected XML element block is highlighted with a semi-transparent orange background
- **Border Effect**: Darker orange highlighting on the first and last lines creates a border-like visual effect
- **Multi-line Support**: Works correctly for both single-line and multi-line XML elements

### Line Count Display
- The status bar shows the number of lines in the selected element
- Format: `Selected [element_name] at line [start_line] ([line_count] line(s))`
- Example: `Selected child at line 4 (4 lines)`

## Implementation Details

### New Methods Added

1. **`_find_element_end_line(content, tag_name, start_line)`**
   - Finds the closing tag line for an XML element
   - Handles self-closing tags (e.g., `<tag />`)
   - Handles single-line elements (e.g., `<tag>value</tag>`)
   - Tracks nesting depth for multi-line elements
   - Returns the line number of the closing tag

2. **`_highlight_element_block(xml_node, start_line)`**
   - Creates visual highlighting for the selected element block
   - Uses PyQt6's `ExtraSelection` mechanism
   - Creates multiple selections to simulate a border effect:
     - Main block: Light orange background (RGB: 255, 140, 0, alpha: 60)
     - Top border: Darker orange (RGB: 255, 100, 0, alpha: 120)
     - Bottom border: Darker orange (RGB: 255, 100, 0, alpha: 120)
   - Updates status bar with element name, line number, and line count

### Modified Methods

1. **`on_tree_node_selected(xml_node)`**
   - Added call to `_highlight_element_block()` after navigating to the element
   - Highlighting is applied after the cursor is positioned at the element

## Usage

1. Open an XML file in the Visual XML Editor
2. Click on any node in the tree view
3. The editor will:
   - Jump to the corresponding line in the text
   - Highlight the entire element block with an orange border effect
   - Display the line count in the status bar

## Testing

A test script `test_highlight.py` is provided to verify the functionality:

```bash
python test_highlight.py
```

This will open a test window with sample XML. Click on tree nodes to see the highlighting in action.

## Technical Notes

- The highlighting uses `QTextEdit.ExtraSelection` which is a non-intrusive way to add visual effects
- The highlighting is cleared when a new node is selected
- The border effect is simulated using darker orange on the first and last lines
- The implementation correctly handles:
  - Self-closing tags
  - Single-line elements
  - Multi-line nested elements
  - Elements with complex nesting

## Color Scheme

- **Main block background**: Orange with 60 alpha (semi-transparent)
- **Border lines**: Darker orange with 120 alpha (more opaque)
- **RGB values**: 
  - Light orange: (255, 140, 0)
  - Dark orange: (255, 100, 0)
