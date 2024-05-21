from config_handler import ConfigReader


config = ConfigReader()


def get_default_height() -> int:
    return config.get_default_resolution()['height']

def get_default_width() -> int:
    return config.get_default_resolution()['width']

def get_default_volume() -> int:
    return config.get_default_volume()


# generates unique IDs for DTOS
def generateId(prefix="", start=1):
    counter = start
    while True:
        yield f"{prefix}{counter}"
        counter += 1
