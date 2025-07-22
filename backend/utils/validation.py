import re
from urllib.parse import urlparse
from typing import Optional


def validate_url(url: str) -> bool:
    """Validate URL format"""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def validate_api_key(api_key: str, min_length: int = 10) -> bool:
    """Validate API key format and length"""
    if not api_key or len(api_key) < min_length:
        return False
    
    # Check if it's not just spaces or common placeholders
    if api_key.strip() in ['', 'your-api-key', 'sk-...', 'YOUR_API_KEY']:
        return False
    
    return True


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing/replacing invalid characters"""
    # Remove or replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove control characters
    sanitized = ''.join(char for char in sanitized if ord(char) >= 32)
    
    # Limit length
    if len(sanitized) > 200:
        sanitized = sanitized[:200]
    
    # Ensure it's not empty or just dots
    if not sanitized or sanitized.strip('.') == '':
        sanitized = 'untitled'
    
    return sanitized


def validate_provider_name(name: str) -> bool:
    """Validate provider name format"""
    if not name or len(name) < 2:
        return False
    
    # Allow alphanumeric, underscores, hyphens
    pattern = r'^[a-zA-Z0-9_-]+$'
    return bool(re.match(pattern, name))


def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_json_path(path: str) -> bool:
    """Validate JSON path format (simplified)"""
    if not path:
        return False
    
    # Basic validation for common patterns like "data[].id", "models[].name"
    pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*(\[\])?(\.[a-zA-Z_][a-zA-Z0-9_]*(\[\])?)*$'
    return bool(re.match(pattern, path))


def sanitize_prompt(prompt: str, max_length: int = 8000) -> str:
    """Sanitize user prompt by removing control characters and limiting length"""
    if not prompt:
        return ""
    
    # Remove control characters except newlines and tabs
    sanitized = ''.join(char for char in prompt if ord(char) >= 32 or char in '\n\t')
    
    # Limit length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized.strip()