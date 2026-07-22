"""Durable status records for asynchronous document ingestion."""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import threading
from typing import Any
from uuid import uuid4

from core.config import settings


class JobStore:
    def __init__(self, path: Path = settings.jobs_path):
        self.path = path
        self._lock = threading.RLock()
        self._jobs = self._load()
        for job in self._jobs.values():
            if job.get("status") in {"queued", "processing"}:
                job.update(
                    status="failed",
                    stage="interrupted",
                    error="Backend restarted before processing completed. Upload the file again.",
                )
        self._save()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _load(self) -> dict[str, dict[str, Any]]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            return {}
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temporary.write_text(json.dumps(self._jobs, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(temporary, self.path)

    def create(self, filename: str) -> dict[str, Any]:
        with self._lock:
            if len(self._jobs) >= 200:
                oldest = sorted(
                    self._jobs,
                    key=lambda key: self._jobs[key].get("updated_at", ""),
                )[: len(self._jobs) - 199]
                for old_job_id in oldest:
                    del self._jobs[old_job_id]
            job_id = uuid4().hex
            now = self._now()
            job = {
                "id": job_id,
                "filename": filename,
                "status": "queued",
                "stage": "queued",
                "progress": 5,
                "error": None,
                "result": None,
                "created_at": now,
                "updated_at": now,
            }
            self._jobs[job_id] = job
            self._save()
            return dict(job)

    def update(self, job_id: str, **changes: Any) -> dict[str, Any]:
        with self._lock:
            job = self._jobs[job_id]
            job.update(changes, updated_at=self._now())
            self._save()
            return dict(job)

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return dict(job) if job else None


job_store = JobStore()
