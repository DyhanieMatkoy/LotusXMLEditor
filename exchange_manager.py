import os
import json
import xml.etree.ElementTree as ET
from zipfile import ZipFile
from typing import List, Tuple, Optional


def _ensure_dir(path: str):
    try:
        os.makedirs(path, exist_ok=True)
    except Exception:
        pass


def parse_exchange_tags_from_path(xml_path: str) -> Tuple[Optional[str], Optional[str]]:
    try:
        with open(xml_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return parse_exchange_tags_from_content(content)
    except Exception:
        return None, None


def parse_exchange_tags_from_content(xml_content: str) -> Tuple[Optional[str], Optional[str]]:
    try:
        root = ET.fromstring(xml_content)
        # Locate ПравилаОбмена/Источник and ПравилаОбмена/Приемник
        source_elem = None
        receiver_elem = None
        # Try absolute paths first
        source_elem = root.find('./ПравилаОбмена/Источник')
        receiver_elem = root.find('./ПравилаОбмена/Приемник')
        # Fallback: search deep
        if source_elem is None:
            source_elem = root.find('.//Источник')
        if receiver_elem is None:
            receiver_elem = root.find('.//Приемник')
        source = source_elem.text.strip() if source_elem is not None and source_elem.text else None
        receiver = receiver_elem.text.strip() if receiver_elem is not None and receiver_elem.text else None
        return source, receiver
    except Exception:
        return None, None


def identify_edited_file(imported_files: List[str], current_content: str) -> Optional[str]:
    cur_source, cur_receiver = parse_exchange_tags_from_content(current_content)
    if not cur_source or not cur_receiver:
        return None
    for f in imported_files:
        src, rec = parse_exchange_tags_from_path(f)
        if src == cur_source and rec == cur_receiver:
            return f
    return None


def save_pair_metadata(base_dir: str, source_value: str, receiver_value: str, edited_path: str, companion_path: str):
    _ensure_dir(base_dir)
    meta = {
        'source_value': source_value,
        'receiver_value': receiver_value,
        'edited_file_name': os.path.basename(edited_path),
        'companion_file_name': os.path.basename(companion_path)
    }
    with open(os.path.join(base_dir, 'pair.meta.json'), 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def load_pair_metadata(base_dir: str) -> Optional[dict]:
    try:
        with open(os.path.join(base_dir, 'pair.meta.json'), 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def package_zip(out_zip_path: str, edited_abs_path: str, edited_arcname: str, companion_abs_path: str, companion_arcname: str) -> bool:
    _ensure_dir(os.path.dirname(out_zip_path))
    try:
        with ZipFile(out_zip_path, 'w') as z:
            z.write(edited_abs_path, arcname=edited_arcname)
            z.write(companion_abs_path, arcname=companion_arcname)
        return True
    except Exception:
        return False


def compute_exchange_dir(root_work_dir: str, source_value: str, receiver_value: str) -> str:
    return os.path.join(root_work_dir, 'ПравилаОбмена', '_exchange', 'pair', source_value, receiver_value)