import json
import yaml
import os
from pathlib import Path
from typing import Any, Dict, Optional
import filelock
from datetime import datetime


def ensure_directory(path: Path) -> None:
    """Ensure directory exists with proper permissions"""
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, 0o700)  # Owner only


def safe_write_json(data: Any, file_path: Path, indent: int = 2) -> None:
    """Safely write JSON data to file with file locking"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    lock_path = file_path.with_suffix(file_path.suffix + '.lock')
    
    with filelock.FileLock(lock_path):
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=indent, default=str)
        
        # Set secure permissions
        os.chmod(file_path, 0o600)


def safe_read_json(file_path: Path) -> Optional[Dict[str, Any]]:
    """Safely read JSON data from file with file locking"""
    if not file_path.exists():
        return None
    
    lock_path = file_path.with_suffix(file_path.suffix + '.lock')
    
    with filelock.FileLock(lock_path):
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return None


def safe_write_yaml(data: Any, file_path: Path) -> None:
    """Safely write YAML data to file with file locking"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    lock_path = file_path.with_suffix(file_path.suffix + '.lock')
    
    with filelock.FileLock(lock_path):
        with open(file_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        
        # Set secure permissions
        os.chmod(file_path, 0o600)


def safe_read_yaml(file_path: Path) -> Optional[Dict[str, Any]]:
    """Safely read YAML data from file with file locking"""
    if not file_path.exists():
        return None
    
    lock_path = file_path.with_suffix(file_path.suffix + '.lock')
    
    with filelock.FileLock(lock_path):
        try:
            with open(file_path, 'r') as f:
                return yaml.safe_load(f)
        except (yaml.YAMLError, FileNotFoundError):
            return None


def append_jsonl(data: Dict[str, Any], file_path: Path) -> None:
    """Append JSON line to JSONL file"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, 'a') as f:
        json.dump(data, f, default=str)
        f.write('\n')


def read_jsonl(file_path: Path, limit: Optional[int] = None) -> list[Dict[str, Any]]:
    """Read JSONL file, optionally limiting number of lines"""
    if not file_path.exists():
        return []
    
    messages = []
    with open(file_path, 'r') as f:
        for line in f:
            if line.strip():
                try:
                    messages.append(json.loads(line))
                    if limit and len(messages) >= limit:
                        break
                except json.JSONDecodeError:
                    continue
    
    return messages


def create_backup(file_path: Path, backup_dir: Path) -> Path:
    """Create timestamped backup of file"""
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{file_path.stem}_{timestamp}{file_path.suffix}"
    
    import shutil
    shutil.copy2(file_path, backup_path)
    return backup_path