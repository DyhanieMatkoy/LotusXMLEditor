# How to Use the Orange Border Highlighting Feature

## Quick Start

1. **Open your XML file** in the Visual XML Editor
2. **Click on any node** in the tree view on the left
3. **See the magic happen**:
   - The editor automatically scrolls to the element
   - The entire XML block is highlighted with an orange background
   - The first and last lines have a darker orange border effect
   - The status bar shows: `Selected [element] at line X (Y lines)`

## Example

### Before Clicking
```
Tree View:          Editor:
├─ root             <?xml version="1.0"?>
│  ├─ parent        <root>
│  │  ├─ child        <parent>
│  │  │  ├─ name        <child id="1">
│  │  │  └─ value         <name>Test</name>
│  │  └─ child            <value>Data</value>
                        </child>
                      </parent>
                    </root>
```

### After Clicking "child" Node
```
Tree View:          Editor:
├─ root             <?xml version="1.0"?>
│  ├─ parent        <root>
│  │  ├─ child        <parent>
│  │  │  ├─ name    ┌─────────────────────────┐
│  │  │  └─ value   │   <child id="1">        │ ← Darker orange
                    │     <name>Test</name>   │ ← Light orange
                    │     <value>Data</value> │ ← Light orange
                    │   </child>              │ ← Darker orange
                    └─────────────────────────┘
                      </parent>
                    </root>

Status Bar: Selected child at line 4 (4 lines)
```

## Visual Indicators

### Color Coding
- **Light Orange Background**: The entire element block
- **Darker Orange Border**: First and last lines for clear boundaries
- **Status Bar**: Shows element name, starting line, and total line count

### What Gets Highlighted
- ✅ Opening tag line
- ✅ All content lines (text, attributes, child elements)
- ✅ Closing tag line
- ✅ Self-closing tags (single line)
- ✅ Nested elements (entire block)

## Benefits

1. **Visual Feedback**: Instantly see which text corresponds to the tree node
2. **Size Awareness**: Know how large the element is (line count)
3. **Navigation Aid**: Quickly locate elements in large XML files
4. **Context Understanding**: See the full scope of nested elements

## Tips

- The highlighting updates each time you click a different node
- Works with all XML element types (simple, nested, self-closing)
- The line count helps you understand element complexity
- Use this feature with the breadcrumb trail for better navigation
