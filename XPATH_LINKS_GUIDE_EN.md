# XPath Links - User Guide

## Overview

The XPath Links feature allows you to save references to XML nodes and quickly navigate to them. This is useful for navigating large XML files and working with frequently used elements.

## New "Links" Tab

A new **"Links"** tab has been added to the bottom panel, containing a text field for storing XPath links. Each link is placed on a separate line.

## Keyboard Shortcuts

### Ctrl+F11 - Copy XPath of Current Position

1. Place the cursor on the desired XML element in the editor
2. Press **Ctrl+F11**
3. The XPath of the current element will be added to a new line in the "Links" tab
4. The bottom panel will automatically open and switch to the "Links" tab

**Example:**
```xml
<root>
    <parent id="1">
        <child name="first">Value 1</child>  <!-- Cursor here -->
    </parent>
</root>
```

After pressing Ctrl+F11, this will be added to Links: `/root[1]/parent[1]/child[1]`

### F12 - Navigate to Link

1. Open the "Links" tab in the bottom panel
2. Place the cursor on the line with the desired XPath
3. Press **F12**
4. The editor will jump to the corresponding element
5. If the XML tree is open, the element will also be highlighted in the tree

## Menu Access

These functions are also available through the **Edit** menu:
- **Copy XPath Link** (Ctrl+F11)
- **Navigate to XPath Link** (F12)

## Usage Examples

### Example 1: Navigating Complex Structure

```xml
<Configuration>
    <Database>
        <Connection>
            <Server>localhost</Server>
            <Port>5432</Port>
        </Connection>
    </Database>
    <Application>
        <Settings>
            <Timeout>30</Timeout>
        </Settings>
    </Application>
</Configuration>
```

1. Place cursor on `<Server>` and press Ctrl+F11
2. Place cursor on `<Timeout>` and press Ctrl+F11
3. Now you have two links in Links for quick navigation

### Example 2: Working with Repeating Elements

```xml
<Orders>
    <Order id="1">
        <Item>Product A</Item>
    </Order>
    <Order id="2">
        <Item>Product B</Item>
    </Order>
    <Order id="3">
        <Item>Product C</Item>
    </Order>
</Orders>
```

Save XPath for each Order to quickly switch between them:
- `/Orders[1]/Order[1]`
- `/Orders[1]/Order[2]`
- `/Orders[1]/Order[3]`

## XPath Format

The system uses a simplified XPath format with indices:
- `/root[1]` - root element
- `/root[1]/parent[2]` - second parent element
- `/root[1]/parent[1]/child[3]` - third child element

Indices start from 1 (as in standard XPath).

## Tips

1. **Organizing Links**: You can add comments in Links by starting a line with `#`:
   ```
   # Database settings
   /Configuration[1]/Database[1]/Connection[1]
   
   # Application settings
   /Configuration[1]/Application[1]/Settings[1]
   ```

2. **Editing Links**: You can manually edit XPath in the Links text field

3. **Saving Links**: The Links tab content can be copied and saved to a separate file for reuse

4. **Quick Navigation**: Use up/down arrows to move between links, then F12 to navigate

## Troubleshooting

**Issue**: XPath is not copied
- **Solution**: Make sure the cursor is on a line with an XML element, not on an empty line or comment

**Issue**: Navigation to link doesn't work
- **Solution**: Check that the XPath is correct and matches the current document structure

**Issue**: Element not found
- **Solution**: The document structure may have changed. Update the XPath by copying it again with Ctrl+F11

## Integration with Other Features

- **Bookmarks (F2)**: Use bookmarks for temporary marks, and Links for permanent structural references
- **Search (Ctrl+F)**: Find an element through search, then save its XPath with Ctrl+F11
- **XML Tree**: Element selection in the tree is synchronized with the editor, making it easier to copy XPath

## Technical Details

- XPath is calculated based on the current cursor position in the editor
- The system accounts for indices for elements with the same names
- Navigation works even if the XML tree is not built
- Links are stored only in the current session (not saved when closing the file)
