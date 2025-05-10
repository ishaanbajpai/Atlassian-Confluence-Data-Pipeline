"""
Logging configuration for the Confluence Data Pipeline.
"""
import logging
import sys
from pathlib import Path
from datetime import datetime

from setup.config_conf import LOGS_DIR

def setup_logging(log_level=logging.INFO):
    """Set up logging for the application.

    Args:
        log_level (int, optional): Logging level. Defaults to logging.INFO.
    """
    # Create a timestamp for the log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOGS_DIR / f"confluence_pipeline_{timestamp}.log"

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    # Create formatters
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_formatter = logging.Formatter(
        "%(levelname)s: %(message)s"
    )

    # Create file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(file_formatter)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_formatter)

    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Log the start of the application
    logger.info(f"Logging initialized. Log file: {log_file}")

    return logger
