import logging
import sys
import os

def setup_logging(verbosity: int = 0, logfile: str = None):
    """Configure logging level and optional file output."""
    if verbosity == 0:
        level = logging.CRITICAL + 1  # disables all log output to terminal
    elif verbosity == 1:
        level = logging.INFO
    else:
        level = logging.DEBUG

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    logger = logging.getLogger()
    logger.setLevel(level)
    logger.handlers.clear()

    # Console handler
    if verbosity > 0:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(level)
        logger.addHandler(console_handler)

    # Optional file handler
    if logfile:
        file_handler = logging.FileHandler(logfile, encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
        logger.addHandler(file_handler)
    
    # Log the exact CLI command that was run
    full_command = " ".join(sys.argv)
    logger.info(f"Command line: {full_command}")
    logger.info(f"Current working directory: {os.getcwd()}")