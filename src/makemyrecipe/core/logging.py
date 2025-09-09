"""Logging configuration for MakeMyRecipe application."""

import logging
import sys
from typing import Optional

from .config import settings


def setup_logging(
    level: Optional[str] = None,
    format_string: Optional[str] = None,
) -> None:
    """Set up application logging configuration.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_string: Log format string
    """
    log_level = level or settings.log_level
    log_format = format_string or settings.log_format

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.database_echo else logging.WARNING
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
