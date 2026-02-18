# Lotus XML Editor
## The Essential Tool for 1C Exchange Rules

---

![Lotus XML Editor](../blotus_splash.jpg)

---

### Why Lotus XML Editor?

Working with **1C:Enterprise exchange rules** can be challenging. Large XML files, complex structures, and ZIP packaging are daily realities for 1C integrators. **Lotus XML Editor** is designed specifically to solve these problems.

---

## 🎯 Key Features at a Glance

### 📦 ZIP Support
Open and edit XML files directly from ZIP archives without extraction!
```
📁 archive.zip
   └── 📄 exchangerules.xml  ← Edit directly!
```
- Automatic repackaging on save
- Preserves ZIP structure

### 🔗 1C Integration
Native support for 1C exchange rules format:
- **ПравилаОбмена** (Exchange Rules) parsing
- **Источник/Приемник** (Source/Destination) detection
- Pair metadata management (`pair.meta.json`)
- Semi-automatic and manual exchange modes

### 🌳 Tree View with Friendly Names
Navigate complex XML structures with ease:

```
├── 📁 ПравилаОбмена
│   ├── Источник: Розница
│   ├── Приемник: УправлениеТорговлей
│   └── 📁 ПравилаКонвертации
│       ├── 📄 Документ.РеализацияТоваров
│       └── 📄 Справочник.Номенклатура
```

**Human-readable labels** instead of raw XML tags!

### 🎨 Syntax Highlighting
Color-coded XML for better readability:

```xml
<Объект Тип="Документ.РеализацияТоваров" Нпп="1">
    <Свойство Имя="Номер">
        <Значение>00000001</Значение>
    </Свойство>
</Объект>
```

---

## 🚀 Workflow Example

### Opening Exchange Rules from ZIP

```
1. File → Open ZIP... 
   └── Select: rules.zip
2. Tree shows friendly names automatically
3. Edit XML with syntax highlighting
4. Save → ZIP updated automatically!
```

### Navigating Large Files

| Action | Shortcut |
|--------|----------|
| Fold element | `Ctrl+Shift+[` |
| Unfold element | `Ctrl+Shift+]` |
| Go to line | `Ctrl+G` |
| Find | `Ctrl+F` |
| Copy XPath | `Ctrl+F11` |
| Navigate to XPath | `F12` |

---

## 📋 More Powerful Features

### XML Split & Combine
Split large exchange rules into manageable parts:
- Threshold-based splitting
- Element-based splitting
- XPath-based rules
- Automatic backup

### XPath Links
Save navigation points for quick access:
```
/ПравилаОбмена[1]/ПравилаКонвертации[5]
/Объект[@Тип='Документ.Реализация'][1]
```

### Code Folding
Collapse XML blocks for better overview:
```
▼ <ПравилаОбмена>
  ▼ <ПравилаКонвертации>
    ... (collapsed)
  ▼ <ПравилаДляОбъектов>
    ... (collapsed)
```

### Metro Navigator
Visual structure diagram for quick orientation in large documents.

---

## 💡 Pro Tips for 1C Developers

1. **Use XPath Links** (`Ctrl+F11`) to mark frequently edited sections
2. **Fold by level** (`Alt+2..9`) to hide deep nesting
3. **Human-readable view** converts cryptic XML to readable format
4. **Auto-validation** catches errors before import

---

## 📥 Getting Started

```bash
# Install dependencies
pip install -r requirements.txt

# Run the editor
python main.py

# Or build standalone executable
python build_exe.py
```

---

## ⌨️ Essential Shortcuts

| Category | Action | Key |
|----------|--------|-----|
| **File** | Open | `Ctrl+O` |
| | Save | `Ctrl+S` |
| **Edit** | Find | `Ctrl+F` |
| | Go to Line | `Ctrl+G` |
| **Fold** | Fold | `Ctrl+Shift+[` |
| | Unfold All | `Ctrl+Shift+U` |
| **Nav** | Tree Up/Down | `F6/F7` |
| | XPath Copy | `Ctrl+F11` |
| | XPath Go | `F12` |

Press **F1** in the application for complete shortcuts list.

---

## 📄 Full Features List

See [FEATURES_TREE.md](FEATURES_TREE.md) for complete hierarchical feature list.

---

*Lotus XML Editor — Making 1C Exchange Rules Manageable*
