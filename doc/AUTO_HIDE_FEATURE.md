# Auto-Hide UI Elements Feature

## Overview

The auto-hide feature provides automatic hiding and revealing of UI elements to maximize screen space for content viewing. The toolbar and tree header elements automatically hide when not in use and reappear when the user hovers over their area.

## Features

### Auto-Hide Elements

1. **Toolbar (Command Panel)**
   - Contains buttons: New, Open, Save, Format, Validate, etc.
   - Auto-hides by default to save vertical space
   - Reveals on hover at the top edge of the window

2. **Tree Header Elements**
   - Contains "XML Structure" label and level collapse buttons
   - Auto-hides by default to maximize tree view space
   - Reveals on hover at the top of the tree panel

### User Controls

#### Menu Options (View Menu)

- **Auto-hide Toolbar** (Ctrl+Shift+T)
  - Toggle auto-hide behavior for the toolbar
  - When enabled: toolbar hides automatically
  - When disabled: toolbar stays permanently visible

- **Auto-hide Tree Header** (Ctrl+Shift+H)
  - Toggle auto-hide behavior for tree header elements
  - When enabled: tree header hides automatically
  - When disabled: tree header stays permanently visible

#### Keyboard Shortcuts

- `Ctrl+Shift+T` - Toggle toolbar auto-hide
- `Ctrl+Shift+H` - Toggle tree header auto-hide

### Behavior

#### Hover Zones

When an element is hidden, a thin 3-pixel hover zone appears in its place:
- **Visual Indicator**: Subtle gray bar that highlights on hover
- **Trigger**: Moving mouse into the zone reveals the hidden element
- **Cursor**: Changes to pointing hand to indicate interactivity

#### Animations

- **Duration**: 200 milliseconds for smooth transitions
- **Show Animation**: Slides down with ease-out curve
- **Hide Animation**: Slides up with ease-in curve
- **Debouncing**: Prevents flickering from rapid hover events

#### Hide Delay

- **Delay**: 500 milliseconds after mouse leaves
- **Cancellation**: Moving mouse back cancels the hide timer
- **Active Use**: Elements stay visible while being interacted with

### Persistence

Auto-hide preferences are saved and restored across application restarts:
- Toolbar auto-hide state
- Tree header auto-hide state

Settings are stored in the application's QSettings configuration.

## Technical Details

### Implementation

The feature is implemented using:
- `AutoHideManager` class in `auto_hide_manager.py`
- `HoverZone` widget for triggering reveals
- Qt property animations for smooth transitions
- Event filters for mouse tracking

### Configuration

Default values (can be adjusted in code):
- Hover zone height: 3 pixels
- Animation duration: 200 milliseconds
- Hide delay: 500 milliseconds

### Integration Points

1. **MainWindow.__init__**
   - Calls `_setup_auto_hide()` after UI creation

2. **View Menu**
   - Toggle actions for toolbar and tree header

3. **Settings Persistence**
   - `_load_persisted_flags()` - Loads saved preferences
   - `_save_flag()` - Saves preferences on toggle

## Usage Tips

1. **Maximize Space**: Enable auto-hide for both toolbar and tree header to maximize content viewing area

2. **Quick Access**: Simply move mouse to the top edge to reveal hidden elements

3. **Permanent Visibility**: Disable auto-hide if you prefer elements always visible

4. **Keyboard Control**: Use shortcuts to quickly toggle auto-hide without opening menus

## Troubleshooting

### Element Won't Hide

- Check if auto-hide is enabled in View menu
- Ensure mouse is not hovering over the element
- Wait for the hide delay (500ms) after mouse leaves

### Element Won't Reveal

- Move mouse into the hover zone at the top edge
- Check if hover zone is visible (subtle gray bar)
- Verify auto-hide is enabled for that element

### Animation Issues

- Animations may be affected by system performance
- Check Qt version compatibility
- Verify no conflicting event handlers

## Future Enhancements

Potential improvements:
- Configurable animation speeds
- Adjustable hover zone sizes
- Additional auto-hide elements (status bar, side panels)
- Context-sensitive auto-hide behavior
- Gesture-based reveal (e.g., swipe down)
