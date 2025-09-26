import os, sys

def resource_path(rel_path: str) -> str:
    if hasattr(sys, "_MEIPASS") and os.path.exists(sys._MEIPASS):
        base = sys._MEIPASS
    else:
        base = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base, rel_path)
