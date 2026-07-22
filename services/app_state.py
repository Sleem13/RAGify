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
    """Persist only API-key digests; an empty store intentionally means open mode."""

    def __init__(self, path: Path = settings.api_keys_path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._keys: dict[str, dict[str, str]] = self._load()
        self._lock = threading.RLock()

    @staticmethod
    def _digest(key: str) -> str:
        import hashlib

        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def _load(self) -> dict[str, dict[str, str]]:
        if not self.path.exists():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except (OSError, json.JSONDecodeError):
            logger.warning("Could not read API-key store; starting in open mode.")
            return {}

    def _save(self) -> None:
        temporary_path = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temporary_path.write_text(
            json.dumps(self._keys, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        os.replace(temporary_path, self.path)

    def generate(self) -> str:
        with self._lock:
            key = f"ragify-{secrets.token_urlsafe(32)}"
            self._keys[self._digest(key)] = {
                "masked": f"{key[:12]}...{key[-4:]}",
            }
            self._save()
            return key

    def verify(self, candidate: str | None) -> bool:
        with self._lock:
            return not self._keys or bool(candidate and self._digest(candidate) in self._keys)

    def masked(self) -> list[str]:
        with self._lock:
            return sorted(entry["masked"] for entry in self._keys.values())

    def revoke(self, key: str) -> bool:
        with self._lock:
            digest = self._digest(key)
            if digest not in self._keys:
                return False
            del self._keys[digest]
            self._save()
            return True


class AppState:
    def __init__(self):
        self.registry = FileRegistry(settings.registry_path)
        self.api_keys = ApiKeyStore()


app_state = AppState()
