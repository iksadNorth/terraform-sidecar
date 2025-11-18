from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterator, Literal

from .schemas import LockInfo


class LockManager:
    def __init__(self, lock_dir: Path, ttl_seconds: int) -> None:
        self.lock_dir = lock_dir
        self.ttl = timedelta(seconds=ttl_seconds)
        self.lock_dir.mkdir(parents=True, exist_ok=True)

    def _lock_file(self, project_id: str) -> Path:
        safe_id = project_id.replace("/", "_")
        return self.lock_dir / f"tf_lock_{safe_id}.json"

    def get_lock(self, project_id: str) -> LockInfo | None:
        lock_file = self._lock_file(project_id)
        if not lock_file.exists():
            return None

        try:
            payload = json.loads(lock_file.read_text())
            lock = LockInfo(**payload)
        except Exception:
            lock_file.unlink(missing_ok=True)
            return None

        if datetime.now(tz=UTC) - lock.started_at > self.ttl:
            # TTL 초과 시 자동 해제
            lock_file.unlink(missing_ok=True)
            return None

        return lock

    def release(self, project_id: str) -> None:
        self._lock_file(project_id).unlink(missing_ok=True)

    @contextmanager
    def acquire(
        self,
        project_id: str,
        status: Literal["apply_running", "destroy_running", "git_clone"],
        message: str,
    ) -> Iterator[None]:
        lock_file = self._lock_file(project_id)
        now = datetime.now(tz=UTC)
        existing = self.get_lock(project_id)
        if existing:
            from .exceptions import ProjectLockedError

            raise ProjectLockedError(existing)

        try:
            fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(fd, "w", encoding="utf-8") as fp:
                lock_info = LockInfo(status=status, started_at=now, message=message)
                json.dump(lock_info.model_dump(mode="json"), fp)
        except FileExistsError:
            existing = self.get_lock(project_id)
            from .exceptions import ProjectLockedError

            raise ProjectLockedError(existing) from None

        try:
            yield
        finally:
            lock_file.unlink(missing_ok=True)

