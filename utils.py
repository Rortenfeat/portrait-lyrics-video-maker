import os

def prewrite_file(path: str) -> None:
    if os.path.isfile(path):
        save_print(f"File {path} will be overwritten.")
    else:
        dir = os.path.dirname(path)
        if not os.path.exists(dir):
            os.makedirs(dir)
    return

def save_print(text: str) -> None:
    pass