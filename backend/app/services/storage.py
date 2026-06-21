from __future__ import annotations

import uuid
from pathlib import Path

from app.config import get_settings

settings = get_settings()


class LocalStorage:
    """Local-disk object storage.

    Kept behind a tiny interface so it can be swapped for S3 (or any
    object store) in production without touching call sites.
    """

    def __init__(self, base_dir: str | None = None) -> None:
        self.base_dir = Path(base_dir or settings.storage_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, content: bytes, filename: str) -> str:
        # Prefix with a uuid to avoid collisions while keeping the original name readable.
        safe_name = Path(filename).name
        key = f"{uuid.uuid4().hex}_{safe_name}"
        path = self.base_dir / key
        path.write_bytes(content)
        return str(path)

    def read(self, storage_path: str) -> bytes:
        return Path(storage_path).read_bytes()


storage = LocalStorage()
