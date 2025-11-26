# Rebuild Tree with Auto-Close Tags Feature

## Overview
A new "Rebuild Tree" button has been added to the command bar that rebuilds the XML tree from the editor content and automatically closes any unclosed tags.

## Location
The "Rebuild Tree" button is located in the main toolbar, after the "Structure Diagram" button.

## Features

### 1. Rebuild Tree
- Rebuilds the XML tree view from the current editor content
- Useful when you've made manual edits to the XML and want to refresh the tree view

### 2. Auto-Close Tags
When rebuilding, the feature automatically:
- Detects unclosed XML tags in the editor content
- Closes them by the shortest path (LIFO - Last In First Out order)
- Maintains proper indentation based on the original tag's indent level
- Updates the editor content with the fixed XML

### 3. Smart Detection
- If the XML is already valid, no changes are made
- Only unclosed tags are fixed
- Self-closing tags (e.g., `<tag />`) are properly recognized and skipped
- Handles nested tags correctly

## How It Works

### Auto-Close Algorithm
1. Parses the XML line by line
2. Maintains a stack of open tags with their indentation levels
3. Tracks opening and closing tags, excluding self-closing tags
4. When the end of the file is reached, closes any remaining open tags in reverse order (LIFO)
5. Uses the original indentation level of each tag for proper formatting

### Example

**Before (unclosed tags):**
```xml
<?xml version="1.0"?>
<root>
  <level1>
    <level2>
      <data>Content</data>
```

**After (auto-closed):**
```xml
<?xml version="1.0"?>
<root>
  <level1>
    <level2>
      <data>Content</data>
      </level2>
    </level1>
</root>
```

## Usage

1. Edit your XML in the editor
2. Click the "Rebuild Tree" button in the toolbar
3. If there are unclosed tags:
   - They will be automatically closed
   - The editor content will be updated
   - The tree will be rebuilt
   - Status bar will show "Auto-closed unclosed tags and rebuilt tree"
4. If the XML is already valid:
   - The tree will simply be rebuilt
   - Status bar will show "Rebuilt tree (no unclosed tags found)"

## Benefits

- **Quick Fix**: Instantly fix malformed XML with unclosed tags
- **Safe**: Only modifies content if unclosed tags are detected
- **Smart**: Uses the shortest path to close tags (LIFO order)
- **Preserves Formatting**: Maintains original indentation levels
- **Non-Destructive**: If XML is already valid, no changes are made

## Technical Details

### Implementation
- **Method**: `rebuild_tree_with_autoclose()` in `MainWindow` class
- **Service**: `auto_close_tags()` in `XmlService` class
- **Location**: `main.py` and `xml_service.py`

### Error Handling
- If the rebuild fails, an error dialog is shown
- Original content is preserved on error
- Status bar displays error messages

## Testing

A test script `test_autoclose.py` is included to verify the auto-close functionality with various scenarios:
- Simple unclosed tags
- Multiple unclosed tags
- Already valid XML
- Nested unclosed tags

Run the test with:
```bash
python test_autoclose.py
```
