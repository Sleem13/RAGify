"""Reusable FastAPI dependencies."""

from fastapi import Header, HTTPException

from services.app_state import app_state


def require_api_key(x_api_key: str | None = Header(default=None)) -> str | None:
    if not app_state.api_keys.verify(x_api_key):
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")
    return x_api_key
