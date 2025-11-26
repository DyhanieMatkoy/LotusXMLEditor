# Auto-Hide Feature - Quick Usage Guide

## What is Auto-Hide?

Auto-hide automatically hides UI elements when you're not using them, giving you more space to view and edit your XML content. Elements reappear when you need them by simply moving your mouse to the top of the screen.

## Quick Start

### Default Behavior

When you start the application:
- ✅ Toolbar is hidden by default
- ✅ Tree header (label and level buttons) is hidden by default
- ✅ Tree column headers ("Element", "Value") are hidden by default
- ✅ Tab bar (Document 1, etc.) is hidden by default
- 📍 Thin gray hover zones mark where hidden elements are

### Revealing Hidden Elements

**To reveal the toolbar:**
1. Move your mouse to the very top of the window
2. The toolbar slides down smoothly
3. It stays visible while you use it
4. It hides again 0.5 seconds after you move away

**To reveal the tree header:**
1. Move your mouse to the top of the tree panel (left side)
2. The "XML Structure" label and level buttons appear
3. They stay visible while you interact with them
4. They hide again after you move away

**To reveal the tree column headers:**
1. Move your mouse to the column header area of the tree
2. The "Element" and "Value" headers appear
3. They stay visible while you interact with them
4. They hide again after you move away

**To reveal the tab bar:**
1. Move your mouse to the top of the editor area
2. The document tabs (Document 1, etc.) appear
3. They stay visible while you interact with them
4. They hide again after you move away

### Toggling Auto-Hide On/Off

**Using the Menu:**
1. Open the **View** menu
2. Click **Auto-hide Toolbar** to toggle toolbar auto-hide
3. Click **Auto-hide Tree Header** to toggle tree header auto-hide
4. Click **Auto-hide Tree Column Header** to toggle column header auto-hide
5. Click **Auto-hide Tab Bar** to toggle tab bar auto-hide
6. ✓ Checkmark means auto-hide is enabled

**Using Keyboard Shortcuts:**
- Press `Ctrl+Shift+T` to toggle toolbar auto-hide
- Press `Ctrl+Shift+H` to toggle tree header auto-hide
- Press `Ctrl+Shift+E` to toggle tree column header auto-hide
- Press `Ctrl+Shift+B` to toggle tab bar auto-hide

### When to Disable Auto-Hide

Disable auto-hide if you:
- Frequently use toolbar buttons
- Need constant access to level collapse buttons
- Prefer traditional always-visible UI
- Find the animations distracting

## Visual Indicators

### Hover Zones

When an element is hidden, you'll see a thin 3-pixel bar:
- **Normal state**: Light gray (rgba 100, 100, 100)
- **On hover**: Brighter gray (rgba 150, 150, 150)
- **Cursor**: Changes to pointing hand 👆

### Animations

- **Reveal**: Smooth slide-down (200ms)
- **Hide**: Smooth slide-up (200ms)
- **Timing**: 500ms delay before hiding

## Common Workflows

### Maximum Screen Space

For maximum content viewing:
1. Enable auto-hide for both toolbar and tree header
2. Hide the bottom panel (View → Show Bottom Panel)
3. Hide the file navigator (View → Show File Navigator)
4. Result: Full screen for XML tree and editor

### Frequent Toolbar Use

If you use toolbar buttons often:
1. Disable toolbar auto-hide (`Ctrl+Shift+T`)
2. Keep tree header auto-hide enabled
3. Result: Toolbar always visible, tree header auto-hides

### Presentation Mode

For demos or presentations:
1. Enable auto-hide for all elements
2. Hide breadcrumbs and bottom panel
3. Result: Clean, distraction-free interface

## Tips & Tricks

1. **Quick Reveal**: Just touch the top edge with your mouse - you don't need to click

2. **Stay Visible**: Keep your mouse in the element area to prevent it from hiding

3. **Keyboard First**: Use keyboard shortcuts to avoid mouse movement when possible

4. **Persistent Settings**: Your auto-hide preferences are saved automatically

5. **Smooth Transitions**: Animations are optimized for smooth performance

## Keyboard Shortcuts Summary

| Action | Shortcut |
|--------|----------|
| Toggle Toolbar Auto-hide | `Ctrl+Shift+T` |
| Toggle Tree Header Auto-hide | `Ctrl+Shift+H` |

## Troubleshooting

**Q: The toolbar won't hide**
- A: Make sure auto-hide is enabled (View menu → Auto-hide Toolbar should be checked)
- A: Move your mouse away from the toolbar area
- A: Wait 0.5 seconds for the hide delay

**Q: I can't find the hidden element**
- A: Look for the thin gray hover zone at the top
- A: Move your mouse slowly across the top edge
- A: Try toggling auto-hide off and on again

**Q: The animation is jerky**
- A: This may be due to system performance
- A: Try closing other applications
- A: Consider disabling auto-hide if performance is an issue

**Q: I want the old behavior back**
- A: Simply disable auto-hide for both elements using the View menu or shortcuts
- A: Your preference will be saved for next time

## Feedback

The auto-hide feature is designed to give you more space while keeping tools accessible. If you have suggestions for improvements, please provide feedback through the application's help menu.
