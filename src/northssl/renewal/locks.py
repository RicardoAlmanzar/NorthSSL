from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Lock

from northssl.core.exceptions import RenewalLockError


@dataclass(slots=True)
class RenewalLockManager:
    locks: dict[str, Lock] = field(default_factory=dict)

    def _get_lock(self, key: str) -> Lock:
        lock = self.locks.get(key)
        if lock is None:
            lock = Lock()
            self.locks[key] = lock
        return lock

    @contextmanager
    def locked(self, key: str, timeout_seconds: int) -> object:
        lock = self._get_lock(key)
        acquired = lock.acquire(timeout=timeout_seconds)
        if not acquired:
            raise RenewalLockError(f"Could not acquire renewal lock for {key}")
        try:
            yield
        finally:
            lock.release()