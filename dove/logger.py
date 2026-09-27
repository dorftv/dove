import os
import logging
import re
import sys

# Credentials that end up in logs via URIs and pipeline strings.
# Bare "pass=" is excluded on purpose — x264 "pass=cbr" must stay readable.
_SECRET_PATTERNS = [
    (re.compile(r'(\w+://)[^/\s:@]+:[^/\s@]+@'), r'\1***:***@'),                   # scheme://user:pass@host
    (re.compile(r'(?i)\b(passphrase|password|passwd|streamid|token|secret|api_key|key)=("[^"]*"|[^\s&"\',;]+)'),
     r'\1=***'),                                                                     # query params / element props
    (re.compile(r'(rtmps?://[^/\s]+/[^/\s]+/)[^\s"\'?]+'), r'\1***'),                # rtmp://host/app/<stream key>
]


def redact(text: str) -> str:
    for pattern, repl in _SECRET_PATTERNS:
        text = pattern.sub(repl, text)
    return text


class RedactSecretsFilter(logging.Filter):
    """Scrub credentials from log records (message and string args — uvicorn's access formatter unpacks args)."""
    def filter(self, record):
        if isinstance(record.msg, str):
            record.msg = redact(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(redact(a) if isinstance(a, str) else a for a in record.args)
        return True

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
        self.logger.addFilter(RedactSecretsFilter())

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
