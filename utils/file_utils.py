import os
import json
import zipfile
from pathlib import Path
from typing import Dict, Any, Optional

def read_text_file(filepath: str) -> str:
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    return path.read_text(encoding='utf-8', errors='ignore')

def write_text_file(filepath: str, content: str) -> str:
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    return str(path)

def write_json_file(filepath: str, data: Any) -> str:
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding='utf-8')
    return str(path)

def read_json_file(filepath: str) -> Any:
    content = read_text_file(filepath)
    return json.loads(content)
