import os
import logging
import sys

# ANSI color codes
class LogColors:
    DEBUG = '\033[94m'  # Blue
    INFO = '\033[92m'   # Green
    WARNING = '\033[93m' # Yellow
    RESET = '\033[0m'   # Reset to default

# Custom Formatter
class ColorFormatter(logging.Formatter):
    FORMAT = "%(asctime)s - %(levelname)s - %(message)s "

    COLOR_MAP = {
        logging.DEBUG: LogColors.DEBUG,
        logging.INFO: LogColors.INFO,
        logging.WARNING: LogColors.WARNING
    }

    def format(self, record):
        color = self.COLOR_MAP.get(record.levelno)
        if color:
            record.msg = f"{color}{record.msg}{LogColors.RESET}"
        return logging.Formatter(self.FORMAT).format(record)

class DebugLogger:
    def __init__(self):
        self.logger = logging.getLogger('DebugLogger')
        log_level = os.getenv('LOG_LEVEL', 'WARNING').upper()
        self.logger.setLevel(getattr(logging, log_level, logging.WARNING))

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(ColorFormatter())
        self.logger.addHandler(handler)

    def log(self, message, level='INFO'):
        if level.upper() == 'DEBUG':
            self.logger.debug(message)
        elif level.upper() == 'WARNING':
            self.logger.warning(message)
        else:
            self.logger.info(message)

# Usage
logger = DebugLogger()
#logger.log("This is an info message.")
#logger.log("This is a debug message.", level='DEBUG')
#logger.log("This is a warning message.", level='WARNING')
