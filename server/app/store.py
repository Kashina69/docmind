import threading
import time


class SimpleStore:
    def __init__(self) -> None:
        self._kv: dict[str, tuple[str, float | None]] = {}
        self._z: dict[str, dict[str, float]] = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> str | None:
        with self._lock:
            item = self._kv.get(key)
            if item is None:
                return None
            value, expire_at = item
            if expire_at is not None and time.time() > expire_at:
                del self._kv[key]
                return None
            return value

    def setex(self, key: str, ttl_seconds: int, value: str) -> None:
        with self._lock:
            self._kv[key] = (value, time.time() + ttl_seconds)

    def zremrangebyscore(self, key: str, min_score: float, max_score: float) -> int:
        with self._lock:
            members = self._z.get(key, {})
            expired = [m for m, s in members.items() if min_score <= s <= max_score]
            for m in expired:
                del members[m]
            return len(expired)

    def zcard(self, key: str) -> int:
        with self._lock:
            return len(self._z.get(key, {}))

    def zadd(self, key: str, mapping: dict[str, float]) -> int:
        with self._lock:
            members = self._z.setdefault(key, {})
            members.update(mapping)
            return len(mapping)


_store = SimpleStore()


def get_store() -> SimpleStore:
    return _store
