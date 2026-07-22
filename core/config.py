"""Centralized environment-backed configuration for RAGify."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _cors_origins() -> list[str]:
    default_origins = "http://localhost:3000,http://127.0.0.1:3000"
    origins = [
        origin.strip()
        for origin in os.getenv("FRONTEND_URL", default_origins).split(",")
        if origin.strip()
    ]
    return origins or default_origins.split(",")


@dataclass(frozen=True, slots=True)
class Settings:
    app_name: str = "RAGify API"
    app_version: str = "5.0.0"
    app_description: str = (
        "AI-powered document analysis and retrieval system. "
        "Upload files, ask questions, get insights."
    )
    max_file_size: int = 50 * 1024 * 1024
    registry_path: Path = BASE_DIR / "data" / "files_registry.json"
    jobs_path: Path = BASE_DIR / "data" / "ingestion_jobs.json"
    api_keys_path: Path = BASE_DIR / "data" / "api_keys.json"
    upload_temp_path: Path = BASE_DIR / "data" / "uploads"
    upload_chunk_size: int = 1024 * 1024
    excel_extensions: frozenset[str] = field(
        default_factory=lambda: frozenset({".xlsx", ".xls", ".csv", ".json"})
    )
    cors_origins: list[str] = field(default_factory=_cors_origins)


settings = Settings()
