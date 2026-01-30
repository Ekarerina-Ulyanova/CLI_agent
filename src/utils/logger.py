"""
Logging configuration for the Coding Agents system.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from rich.logging import RichHandler
from src.utils.config import settings


def setup_logger(name: str, log_file: Optional[str] = None) -> logging.Logger:
    """
    Set up a logger with consistent formatting.
    
    Args:
        name (str): Logger name
        log_file (Optional[str]): Path to log file
        
    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, settings.log_level.upper()))

    logger.handlers.clear()

    console_handler = RichHandler(
        rich_tracebacks=True,
        markup=True,
        show_time=True,
        show_path=False
    )
    console_handler.setFormatter(
        logging.Formatter('%(message)s', datefmt='[%X]')
    )
    logger.addHandler(console_handler)

    if log_file or settings.log_file:
        log_path = Path(log_file or settings.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name (str): Logger name
        
    Returns:
        logging.Logger: Logger instance
    """
    return logging.getLogger(name)