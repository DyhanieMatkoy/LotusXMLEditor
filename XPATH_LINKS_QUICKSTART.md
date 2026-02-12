# XPath Links - Быстрый старт / Quick Start

## Русский

### Что это?
Механизм для сохранения и быстрой навигации по XML-элементам через XPath.

### Как использовать?

1. **Откройте XML-файл** (например, `xpath_links_demo.xml`)

2. **Сохраните ссылку на элемент:**
   - Поставьте курсор на нужную строку XML
   - Нажмите **Ctrl+F11**
   - XPath появится во вкладке "Links" внизу

3. **Перейдите по ссылке:**
   - Откройте вкладку "Links" (F9 для показа нижней панели)
   - Поставьте курсор на строку с XPath
   - Нажмите **F12**
   - Редактор перейдет к элементу

### Пример

Откройте `xpath_links_demo.xml` и попробуйте:

1. Курсор на `<Server>localhost</Server>` → Ctrl+F11
2. Курсор на `<LogLevel>INFO</LogLevel>` → Ctrl+F11
3. Курсор на `<Algorithm>AES-256</Algorithm>` → Ctrl+F11

Теперь во вкладке Links у вас 3 ссылки для быстрого перехода!

### Горячие клавиши

| Клавиша | Действие |
|---------|----------|
| **Ctrl+F11** | Копировать XPath текущей позиции |
| **F12** | Перейти по XPath из Links |
| **F9** | Показать/скрыть нижнюю панель |

---

## English

### What is it?
A mechanism for saving and quickly navigating to XML elements via XPath.

### How to use?

1. **Open an XML file** (e.g., `xpath_links_demo.xml`)

2. **Save a link to an element:**
   - Place cursor on the desired XML line
   - Press **Ctrl+F11**
   - XPath will appear in the "Links" tab at the bottom

3. **Navigate to a link:**
   - Open the "Links" tab (F9 to show bottom panel)
   - Place cursor on a line with XPath
   - Press **F12**
   - Editor will jump to the element

### Example

Open `xpath_links_demo.xml` and try:

1. Cursor on `<Server>localhost</Server>` → Ctrl+F11
2. Cursor on `<LogLevel>INFO</LogLevel>` → Ctrl+F11
3. Cursor on `<Algorithm>AES-256</Algorithm>` → Ctrl+F11

Now you have 3 links in the Links tab for quick navigation!

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **Ctrl+F11** | Copy XPath of current position |
| **F12** | Navigate to XPath from Links |
| **F9** | Show/hide bottom panel |

---

## Советы / Tips

### 🇷🇺 Русский
- Можно добавлять комментарии, начиная строку с `#`
- Ссылки можно редактировать вручную
- Используйте стрелки ↑↓ для перемещения между ссылками
- Содержимое Links можно скопировать и сохранить в файл

### 🇬🇧 English
- You can add comments by starting a line with `#`
- Links can be edited manually
- Use ↑↓ arrows to move between links
- Links content can be copied and saved to a file
