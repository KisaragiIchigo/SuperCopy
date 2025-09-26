import os, json

class Config:
    def __init__(self, app_name: str):
        self.app_name = app_name
        base = os.path.join(os.path.expanduser("~"), ".config", app_name)
        os.makedirs(base, exist_ok=True)
        self.path = os.path.join(base, f"{app_name}_config.json")
        self.data = {}
        self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception:
                self.data = {}
        else:
            self.data = {}

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
