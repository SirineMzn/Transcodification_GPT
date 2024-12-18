"""
Utility functions for data processing and validation.
"""
import logging
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from datetime import datetime
import os
from config import LogConfig, DataConfig

def setup_logging() -> None:
    """Configure logging for the application."""
    if not os.path.exists(LogConfig.LOG_DIR):
        os.makedirs(LogConfig.LOG_DIR)
    
    log_file = os.path.join(
        LogConfig.LOG_DIR, 
        f'transcogpt_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    )
    
    logging.basicConfig(
        level=logging.INFO,
        format=LogConfig.LOG_FORMAT,
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

def validate_file(file: Any) -> Tuple[bool, str]:
    """
    Validate uploaded file.
    
    Args:
        file: Uploaded file object
    
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if file is None:
        return False, "No file uploaded"
    
    # Check file size
    file_size_mb = file.size / (1024 * 1024)
    if file_size_mb > DataConfig.MAX_FILE_SIZE_MB:
        return False, f"File size exceeds {DataConfig.MAX_FILE_SIZE_MB}MB limit"
    
    # Validate file extension
    if not file.name.endswith('.xlsx'):
        return False, "Only .xlsx files are supported"
    
    return True, ""

def clean_text(text: Any) -> str:
    """
    Normalize account type text.
    
    Args:
        text: Input text to normalize
    
    Returns:
        str: Normalized text ('BS' or 'P&L')
    """
    if not isinstance(text, str):
        text = str(text)
    text_cleaned = text.lower()
    
    if text_cleaned.startswith('b'):
        return 'BS'
    elif text_cleaned.startswith('p'):
        return 'P&L'
    
    return text_cleaned

def normalize_number(num_str: str) -> str:
    """
    Normalize account numbers.
    
    Args:
        num_str: Account number string
    
    Returns:
        str: Normalized account number
    """
    try:
        num_str = num_str.strip().lstrip('*').strip()
        num = float(num_str)
        return str(int(num)) if num.is_integer() else str(num)
    except (ValueError, AttributeError):
        return num_str

class DataValidationError(Exception):
    """Custom exception for data validation errors."""
    pass
