from collections import deque
from typing import Deque, Dict, Any, List

class RollingBuffer:
    def __init__(self, max_len: int = 12):
        self.buf: Deque[Dict[str, Any]] = deque(maxlen=max_len)

    def extend(self, messages: List[Dict[str, Any]]):
        for m in messages: self.buf.append(m)

    def as_messages(self)->List[Dict[str,Any]]:
        return list(self.buf)
