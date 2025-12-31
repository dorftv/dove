from config_handler import ConfigReader


config = ConfigReader()

def get_default_framerate() -> str:
    return config.get_default_framerate()

def get_default_height() -> int:
    return config.get_default_resolution()['height']

def get_default_width() -> int:
    return config.get_default_resolution()['width']

def get_default_volume() -> int:
    return config.get_default_volume()


# generates unique IDs for DTOS
def generateId(prefix="", start=1):
    """Name generator that checks existing names to avoid duplicates.
    Set .existing to a callable returning current names before first use.
    """
    gen = _IdGenerator(prefix, start)
    return gen


class _IdGenerator:
    """Iterator that generates unique names by checking existing entities."""
    def __init__(self, prefix, start=1):
        self.prefix = prefix
        self.counter = start
        self.get_existing = None  # set by pipeline_handler after init

    def __iter__(self):
        return self

    def __next__(self):
        existing = self.get_existing() if self.get_existing else set()
        while True:
            name = f"{self.prefix}{self.counter}"
            self.counter += 1
            if name not in existing:
                return name
