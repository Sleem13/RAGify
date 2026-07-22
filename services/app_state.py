"""Thread-safe application state and persistent indexed-file registry."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import secrets
import threading
from typing import Any

from core.config import settings
from services.vector_db import vector_db


logger = logging.getLogger(__name__)


class FileRegistry:
    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.RLock()
        self._files = self._load()
        if self._files and not vector_db.has_index:
            logger.warning("Ignoring stale file registry because the FAISS index is missing.")
            self._files = {}
        logger.info("Loaded file registry: %s file(s) found.", len(self._files))

    def _load(self) -> dict[str, dict[str, Any]]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not read registry: %s", exc)
            return {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temporary_path.write_text(
            json.dumps(self._files, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temporary_path, self.path)

    def snapshot(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return {name: dict(metadata) for name, metadata in self._files.items()}

    def names(self) -> list[str]:
        with self._lock:
            return list(self._files)

    def __len__(self) -> int:
        with self._lock:
            return len(self._files)

    def __contains__(self, filename: str) -> bool:
        with self._lock:
            return filename in self._files

    def set(self, filename: str, metadata: dict[str, Any]) -> None:
        with self._lock:
            self._files[filename] = dict(metadata)
            self._save()

    def remove(self, filename: str) -> None:
        with self._lock:
            del self._files[filename]
            self._save()

    def clear(self) -> None:
        with self._lock:
            self._files.clear()
            self._save()


class ApiKeyStore:
    """In-memory API keys; an empty store intentionally means open mode."""

    def __init__(self):
        self._keys: set[str] = set()
        self._lock = threading.RLock()

    def generate(self) -> str:
        with self._lock:
            key = f"ragify-{secrets.token_urlsafe(32)}"
            self._keys.add(key)
            return key

    def verify(self, candidate: str | None) -> bool:
        with self._lock:
            return not self._keys or candidate in self._keys

    def masked(self) -> list[str]:
        with self._lock:
            return [f"{key[:12]}...{key[-4:]}" for key in sorted(self._keys)]

    def revoke(self, key: str) -> bool:
        with self._lock:
            if key not in self._keys:
                return False
            self._keys.remove(key)
            return True


class AppState:
    def __init__(self):
        self.registry = FileRegistry(settings.registry_path)
        self.api_keys = ApiKeyStore()


app_state = AppState()
