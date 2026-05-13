import os
import logging
import sys

# ANSI color codes
class LogColors:
    DEBUG = '\033[94m'   # Blue
    INFO = '\033[92m'    # Green
    WARNING = '\033[93m' # Yellow
    ERROR = '\033[91m'   # Red
    RESET = '\033[0m'

class ColorFormatter(logging.Formatter):
    FORMAT = "%(asctime)s - %(levelname)s - %(message)s "

    COLOR_MAP = {
        logging.DEBUG: LogColors.DEBUG,
        logging.INFO: LogColors.INFO,
        logging.WARNING: LogColors.WARNING,
        logging.ERROR: LogColors.ERROR,
    }

    def format(self, record):
        color = self.COLOR_MAP.get(record.levelno)
        if color:
            record.msg = f"{color}{record.msg}{LogColors.RESET}"
        return logging.Formatter(self.FORMAT).format(record)

class DebugLogger:
    def __init__(self):
        self.logger = logging.getLogger('DebugLogger')
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        self.logger.setLevel(getattr(logging, log_level, logging.INFO))

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(ColorFormatter())
        self.logger.addHandler(handler)

    def log(self, message, level='INFO'):
        level = level.upper()
        if level == 'DEBUG' or level == 'TRACE':
            self.logger.debug(message)
        elif level == 'WARNING':
            self.logger.warning(message)
        elif level == 'ERROR':
            self.logger.error(message)
        else:
            self.logger.info(message)


logger = DebugLogger()
