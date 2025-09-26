from typing import List

class ClipboardStore:
    def __init__(self):
        self.history: List[str] = []
        self._last = ""

    def add(self, text: str) -> bool:
        """#説明: 空白のみ＆Noneを除外、直前／既存の重複はスキップ。"""
        if not text: return False
        t = text.strip()
        if not t: return False
        if t == self._last: return False
        if t in self.history:
            self._last = t
            return False
        self.history.append(t)
        self._last = t
        return True

    def clear(self):
        self.history.clear()
        self._last = ""
