import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional
import uuid
from contextvars import ContextVar

# Context variable for request ID tracking
request_id_ctx: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_ctx.get() or 'no-request'
        return True


def setup_logger(name: str, log_file: Optional[Path] = None, level: int = logging.INFO) -> logging.Logger:
    """Setup logger with file rotation and request ID tracking"""
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
        
    logger.setLevel(level)
    
    # Custom formatter with request ID
    formatter = logging.Formatter(
        '[%(asctime)s] [%(request_id)s] %(name)s:%(levelname)s - %(message)s'
    )
    
    # Add request ID filter
    request_filter = RequestIdFilter()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(request_filter)
    logger.addHandler(console_handler)
    
    # File handler if log_file provided
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_file, 
            maxBytes=5*1024*1024,  # 5MB
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        file_handler.addFilter(request_filter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get existing logger"""
    return logging.getLogger(name)


def set_request_id(request_id: str) -> None:
    """Set request ID for current context"""
    request_id_ctx.set(request_id)


def generate_request_id() -> str:
    """Generate new request ID"""
    return str(uuid.uuid4())[:8]


def clear_request_id() -> None:
    """Clear request ID from context"""
    request_id_ctx.set(None)