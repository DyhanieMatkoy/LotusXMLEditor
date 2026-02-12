# Tree Search Filter Feature

## Overview
The XML tree widget now includes a live search filter that allows you to quickly find nodes by typing part of their names, values, or attributes.

## Usage

### Basic Search
1. Locate the **Filter** input field above the XML tree structure
2. Type any text to filter the tree nodes
3. The tree will automatically update to show only matching nodes and their parent hierarchy

### Search Behavior
- **Live filtering**: Results update as you type
- **Case insensitive**: Searches ignore case (e.g., "item" matches "Item", "ITEM")
- **Multi-field search**: Searches across:
  - Element names/tags
  - Element values
  - Attribute names and values
- **Hierarchical display**: Matching nodes are shown with their full parent path for context
- **Auto-expand**: Parent nodes are automatically expanded to reveal matches

### Clearing the Filter
- Click the clear button (X) in the search field
- Or delete all text manually
- The tree will restore to its normal view

## Examples

### Search for specific elements
Type `item` to find all nodes with "item" in their name

### Search by value
Type `author` to find nodes containing "author" in their value or tag

### Search by attribute
Type part of an attribute name or value to find matching nodes

## Status Bar
The status bar shows the number of matches found:
- "Found X matches" - when search is active
- "Search cleared" - when filter is removed

## Keyboard Shortcuts
- **Ctrl+F**: Opens the main find dialog (for editor content)
- **Ctrl+Shift+T**: Find in Tree (alternative search method)

## Technical Details
- Search is performed on the entire tree structure
- Parent nodes are automatically shown to provide context
- The filter respects the "Hide Leaves" setting when cleared
- Search does not modify the underlying XML data
