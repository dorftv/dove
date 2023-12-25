
# generates unique IDs for DTOS

def generateId(prefix="input", start=1):
    counter = start
    while True:
        yield f"{prefix}{counter}"
        counter += 1
