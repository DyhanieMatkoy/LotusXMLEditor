import xml.etree.ElementTree as ET
import io

def get_human_readable_1c_xml(xml_string):
    """
    Returns a human-readable string representation of 1C XML fragment.
    Based on logic provided in todo3.md.
    """
    output = io.StringIO()
    
    def print_out(*args, **kwargs):
        print(*args, file=output, **kwargs)

    # Оборачиваем в корневой тег, так как входящий XML может быть фрагментом
    # If it already has a root, this might be redundant but safe if it's a fragment list
    # However, if the user provides a full XML, wrapping it might cause double root if not careful.
    # But usually fragment editor has fragments. 
    # Let's try to parse as is, if fails, wrap.
    
    root = None
    try:
        root = ET.fromstring(xml_string)
    except ET.ParseError:
        try:
            wrapped_xml = f"<Root>{xml_string}</Root>"
            root = ET.fromstring(wrapped_xml)
        except ET.ParseError as e:
            return f"Error parsing XML: {e}"

    # If we wrapped it, iterate children. If not, iterate children of root?
    # The original script wrapped it unconditionally: xml_string = f"<Root>{xml_string}</Root>"
    # So let's follow that logic to be consistent with the user request.
    
    # Re-implementing exactly as requested:
    wrapped_xml = f"<Root>{xml_string}</Root>"
    try:
        root = ET.fromstring(wrapped_xml)
    except ET.ParseError as e:
        return f"Error parsing XML: {e}"

    found_supported_content = False
    for node in root:
        if node.tag == "ДанныеПоОбмену":
            found_supported_content = True
            print_out("=" * 50)
            print_out("ДАННЫЕ ПО ОБМЕНУ")
            print_out("=" * 50)
            for attr, val in node.attrib.items():
                print_out(f"{attr}: {val}")
            print_out("")

        elif node.tag == "Объект":
            found_supported_content = True
            obj_type = node.get("Тип")
            npp = node.get("Нпп")
            print_out("-" * 50)
            print_out(f"ОБЪЕКТ [{npp}]: {obj_type}")
            print_out("-" * 50)

            for child in node:
                # Обычное свойство
                if child.tag == "Свойство":
                    name = child.get("Имя")
                    val_elem = child.find("Значение")
                    link_elem = child.find("Ссылка")

                    value = ""
                    if val_elem is not None:
                        value = val_elem.text
                    elif link_elem is not None:
                        # Если это ссылка, попробуем достать Код или УИД из вложенных свойств
                        uid_prop = link_elem.find(".//Свойство[@Имя='{УникальныйИдентификатор}']/Значение")
                        code_prop = link_elem.find(".//Свойство[@Имя='Код']/Значение")
                        
                        if uid_prop is not None:
                            value = f"[Ссылка: {uid_prop.text}]"
                        elif code_prop is not None:
                            value = f"[Ссылка (Код): {code_prop.text}]"
                        else:
                            value = "[Ссылка]"

                    if value is None: value = ""
                    
                    # Форматирование многострочных комментариев
                    if "\n" in value:
                        print_out(f"{name}:")
                        for line in value.split("\n"):
                            print_out(f"  {line}")
                    else:
                        print_out(f"{name}: {value}")

                # Табличная часть
                elif child.tag == "ТабличнаяЧасть":
                    tb_name = child.get("Имя")
                    print_out(f"\n[Табличная часть: {tb_name}]")
                    
                    # Заголовки колонок (берем из первой строки для примера)
                    first_row = child.find("Запись")
                    if first_row is not None:
                        headers = []
                        for prop in first_row.findall("Свойство"):
                            headers.append(prop.get("Имя"))
                        print_out(f"  | {' | '.join(headers)} |")
                        print_out("  " + "-" * (len(" | ".join(headers)) + 2))

                    for row in child.findall("Запись"):
                        row_vals = []
                        for prop in row.findall("Свойство"):
                            v_elem = prop.find("Значение")
                            row_vals.append(v_elem.text if v_elem is not None else "")
                        print_out(f"  | {' | '.join(row_vals)} |")
                    print_out("")

                # Параметры (свойства объекта, не являющиеся реквизитами, например, для КД)
                elif child.tag == "ЗначениеПараметра":
                    name = child.get("Имя")
                    val = child.findtext("Значение")
                    print_out(f"* {name}: {val}")
            
            print_out("")
            
    result = output.getvalue()
    if not result.strip() and not found_supported_content:
        return "No supported 1C data found (ДанныеПоОбмену, Объект). This view mode supports 1C Exchange Data format."
        
    return result
