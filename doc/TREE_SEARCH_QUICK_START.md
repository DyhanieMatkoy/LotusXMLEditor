# Tree Search Filter - Quick Start

## What's New?
A search filter box has been added above the XML tree structure panel.

## How to Use

### Step 1: Locate the Filter Box
Look for the **"Filter:"** input field at the top of the XML Structure panel (left side of the window).

### Step 2: Start Typing
Simply type any text you want to find:
- Element names (e.g., "item", "group", "metadata")
- Values (e.g., "author", "version")
- Attribute names or values

### Step 3: View Results
- Matching nodes are highlighted and shown
- Parent nodes automatically expand to show matches
- Non-matching nodes are hidden
- Status bar shows: "Found X matches"

### Step 4: Clear the Filter
- Click the X button in the search box, OR
- Delete all text manually
- Tree returns to normal view

## Examples

**Find all "item" elements:**
```
Type: item
Result: Shows all nodes with "item" in their name
```

**Find nodes with specific values:**
```
Type: author
Result: Shows nodes containing "author" in tag or value
```

**Find by attribute:**
```
Type: id="1"
Result: Shows nodes with matching attributes
```

## Tips
- Search is **case-insensitive** (Item = item = ITEM)
- Search works on **all fields** (names, values, attributes)
- Parents are **auto-expanded** to show context
- Works with **large XML files** efficiently

## Keyboard Shortcuts
While the feature doesn't have a dedicated shortcut, you can:
- Use **Tab** to navigate to the filter box
- Use **Ctrl+Shift+T** for the alternative "Find in Tree" dialog

---

**Note:** This filter is visual only - it doesn't modify your XML data.
