# Auto-Hide Feature - Quick Reference Card

## 🎯 What It Does
Automatically hides toolbar, tree header, column headers, and tab bar to give you more screen space. Elements reappear when you hover over them.

## ⌨️ Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Toggle Toolbar Auto-hide | `Ctrl+Shift+T` |
| Toggle Tree Header Auto-hide | `Ctrl+Shift+H` |
| Toggle Tree Column Header Auto-hide | `Ctrl+Shift+E` |
| Toggle Tab Bar Auto-hide | `Ctrl+Shift+B` |

## 🖱️ Mouse Actions

| Action | Result |
|--------|--------|
| Hover at top of window | Reveals toolbar |
| Hover at top of tree panel | Reveals tree header |
| Hover at tree column area | Reveals column headers |
| Hover at top of editor | Reveals tab bar |
| Move mouse away | Hides after 0.5 seconds |
| Click on element | Keeps visible during use |

## 📍 Visual Indicators

- **Thin gray bar** = Hover zone (3 pixels high)
- **Brighter on hover** = Ready to reveal
- **Pointing hand cursor** = Interactive zone

## 🎨 Animations

- **Reveal**: 200ms slide down
- **Hide**: 200ms slide up
- **Delay**: 500ms before hiding

## 🔧 Menu Location

**View → Auto-hide Toolbar** (Ctrl+Shift+T)
**View → Auto-hide Tree Header** (Ctrl+Shift+H)
**View → Auto-hide Tree Column Header** (Ctrl+Shift+E)
**View → Auto-hide Tab Bar** (Ctrl+Shift+B)

## ✅ Default State

- ✓ Toolbar auto-hide: **ENABLED**
- ✓ Tree header auto-hide: **ENABLED**
- ✓ Tree column header auto-hide: **ENABLED**
- ✓ Tab bar auto-hide: **ENABLED**
- ✓ Settings: **SAVED AUTOMATICALLY**

## 💡 Quick Tips

1. **Maximize space**: Enable both auto-hides
2. **Quick reveal**: Just touch the top edge
3. **Stay visible**: Keep mouse in element area
4. **Disable anytime**: Use shortcuts or menu
5. **Persistent**: Settings saved on exit

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| Won't hide | Check menu is enabled, move mouse away |
| Won't reveal | Hover over gray bar at top |
| Can't find | Look for thin gray hover zone |
| Want old UI | Disable both auto-hides |

## 📊 Configuration

Default values (in code):
- Hover zone: **3px**
- Animation: **200ms**
- Hide delay: **500ms**

---

**Pro Tip**: Combine with hiding bottom panel and file navigator for maximum editing space!
