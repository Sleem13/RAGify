"""Backward-compatible import for the FastAPI application."""

from app.main import app, create_app

__all__ = ["app", "create_app"]
