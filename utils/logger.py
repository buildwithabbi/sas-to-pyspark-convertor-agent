import sys
import logging
from rich.logging import RichHandler

def setup_logger(name: str = "sas_to_spark") -> logging.Logger:
    """Configures a rich logger instance for standard logging output."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = RichHandler(rich_tracebacks=True, show_time=True, show_path=False)
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger

logger = setup_logger()
