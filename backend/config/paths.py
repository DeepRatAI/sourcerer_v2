import os
from pathlib import Path
from typing import Optional


def get_config_dir() -> Path:
    """Get configuration directory path"""
    config_home = os.environ.get('XDG_CONFIG_HOME')
    if config_home:
        return Path(config_home) / 'sourcerer'
    
    home = Path.home()
    return home / '.sourcerer'


def get_data_dir() -> Path:
    """Get data directory path"""
    data_home = os.environ.get('XDG_DATA_HOME')
    if data_home:
        return Path(data_home) / 'sourcerer'
    
    config_dir = get_config_dir()
    return config_dir


def get_logs_dir() -> Path:
    """Get logs directory path"""
    return get_data_dir() / 'logs'


def get_cache_dir() -> Path:
    """Get cache directory path"""
    cache_home = os.environ.get('XDG_CACHE_HOME')
    if cache_home:
        return Path(cache_home) / 'sourcerer'
    
    return get_data_dir() / 'cache'


def get_chats_dir() -> Path:
    """Get chats directory path"""
    return get_data_dir() / 'chats'


def get_sources_dir() -> Path:
    """Get sources directory path"""
    return get_data_dir() / 'sources'


def get_memory_dir() -> Path:
    """Get memory/RAG directory path"""
    return get_data_dir() / 'memory'


def get_outputs_dir() -> Path:
    """Get outputs directory path"""
    return get_data_dir() / 'outputs'


def get_backups_dir() -> Path:
    """Get backups directory path"""
    return get_data_dir() / 'backups'


def initialize_directories() -> None:
    """Create all necessary directories with proper permissions"""
    from ..utils.file_utils import ensure_directory
    
    directories = [
        get_config_dir() / 'config',
        get_chats_dir(),
        get_sources_dir(), 
        get_memory_dir() / 'vector_store',
        get_logs_dir(),
        get_cache_dir() / 'tmp',
        get_outputs_dir() / 'packages',
        get_outputs_dir() / 'images',
        get_backups_dir(),
    ]
    
    for directory in directories:
        ensure_directory(directory)