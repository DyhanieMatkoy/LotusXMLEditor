from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class XmlTreeNode:
    name: str
    tag: str
    value: Optional[str] = None
    attributes: Dict[str, str] = field(default_factory=dict)
    children: List['XmlTreeNode'] = field(default_factory=list)

def compute_display_name(xml_node, use_friendly_labels=True):
    """Compute label for a node based on current mode."""
    if not xml_node:
        return ""
    if not use_friendly_labels:
        attr = getattr(xml_node, 'attributes', {}) or {}
        attr_string = " ".join([f'{k}="{v}"' for k, v in attr.items()])
        return f"{xml_node.tag} [{attr_string}]" if attr_string else f"{xml_node.tag}"

    display_name = xml_node.name 
    
    preferred_name = None
    try:
        for child in getattr(xml_node, 'children', []) or []:
            # New logic
            tag = getattr(child, 'tag', '')
            if tag and tag.lower() in ("наименование", "имя", "name") and getattr(child, 'value', None):
                text = child.value.strip()
                if text:
                    preferred_name = text
                    break
    except Exception:
        preferred_name = None

    if preferred_name:
        attr = getattr(xml_node, 'attributes', {}) or {}
        attr_string = " ".join([f'{k}="{v}"' for k, v in attr.items()])
        display_name = f"{preferred_name} ({xml_node.tag} [{attr_string}])" if attr_string else f"{preferred_name} ({xml_node.tag})"
    return display_name

# Test cases
# 1. "Name" (Standard)
node1 = XmlTreeNode(name="Item", tag="Item")
child1 = XmlTreeNode(name="Name", tag="Name", value="Friendly Name 1")
node1.children.append(child1)

# 2. "name" (Lowercase)
node2 = XmlTreeNode(name="Item", tag="Item")
child2 = XmlTreeNode(name="name", tag="name", value="Friendly Name 2")
node2.children.append(child2)

# 3. "NAME" (Uppercase)
node3 = XmlTreeNode(name="Item", tag="Item")
child3 = XmlTreeNode(name="NAME", tag="NAME", value="Friendly Name 3")
node3.children.append(child3)

# 4. "Имя" (Cyrillic Standard)
node4 = XmlTreeNode(name="Item", tag="Item")
child4 = XmlTreeNode(name="Имя", tag="Имя", value="Friendly Name 4")
node4.children.append(child4)

# 5. "имя" (Cyrillic Lowercase)
node5 = XmlTreeNode(name="Item", tag="Item")
child5 = XmlTreeNode(name="имя", tag="имя", value="Friendly Name 5")
node5.children.append(child5)

print(f"1. Name: {compute_display_name(node1)}")
print(f"2. name: {compute_display_name(node2)}")
print(f"3. NAME: {compute_display_name(node3)}")
print(f"4. Имя: {compute_display_name(node4)}")
print(f"5. имя: {compute_display_name(node5)}")
