
with open(r'e:\vibeCode\LotusXMLEditor\main.py', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f, 1):
        if 'def _deferred_tree_build_from_open' in line:
            print(f"Found at line {i}: {line.strip()}")
