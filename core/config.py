"""Centralized environment-backed configuration for RAGify."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _cors_origins() -> list[str]:
    origins = [
        origin.strip()
        for origin in os.getenv("FRONTEND_URL", "*").split(",")
        if origin.strip()
    ]
    return origins or ["*"]


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
    excel_extensions: frozenset[str] = field(
        default_factory=lambda: frozenset({".xlsx", ".xls", ".csv", ".json"})
    )
    cors_origins: list[str] = field(default_factory=_cors_origins)


settings = Settings()
