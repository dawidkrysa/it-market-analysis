"""Logging configuration module for the application.

Provides centralized logging setup with console and rotating file handlers.
"""

import logging
from typing import TextIO
from logging.handlers import RotatingFileHandler
from pathlib import Path
from config.settings import Settings
import streamlit as st
import sys


@st.cache_resource
def setup_logging():
    """
    Configure application-wide logging with console and file handlers.
    
    Sets up:
    - Console handler: INFO level with basic formatting
    - File handler: DEBUG level with detailed formatting and 10MB rotation
    
    Returns:
        logging.Logger: Configured root logger instance
    """
    
    log_dir: Path = Path(Settings.LOG_FILE).parent
    log_dir.mkdir(parents=True, exist_ok=True)
    
    logger: logging.Logger = logging.getLogger()

    # Close and clear handlers so we don't double-log on Streamlit hot reloads.
    for handler in list(logger.handlers):
        try:
            handler.close()
        except Exception:
            pass
    logger.handlers.clear()

    logger.propagate = False
    logger.setLevel(getattr(logging, Settings.LOG_LEVEL))

    console_handler: logging.StreamHandler[TextIO] = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(process)d - %(threadName)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    
    file_handler = RotatingFileHandler(
        Settings.LOG_FILE,
        maxBytes=10485760,
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(process)d - %(threadName)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger