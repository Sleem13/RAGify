"""Render-safe FastAPI application entry point."""

from __future__ import annotations

import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from api.routers import auth, chat, documents, exports, system
from core.config import settings


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def create_app() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/", tags=["System"])
    def root() -> dict[str, str]:
        return {
            "status": "healthy",
            "app": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
        }

    @application.get("/health", tags=["System"])
    def health() -> dict[str, str]:
        return {"status": "healthy"}

    @application.middleware("http")
    async def request_observability(request: Request, call_next):
        request_id = request.headers.get("X-Request-Id") or uuid4().hex
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            logging.getLogger("ragify.request").exception(
                "request_failed request_id=%s method=%s path=%s duration_ms=%.1f",
                request_id,
                request.method,
                request.url.path,
                (time.perf_counter() - started) * 1000,
            )
            raise
        response.headers["X-Request-Id"] = request_id
        logging.getLogger("ragify.request").info(
            "request_complete request_id=%s method=%s path=%s status=%s duration_ms=%.1f",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            (time.perf_counter() - started) * 1000,
        )
        return response

    for router in (
        system.router,
        auth.router,
        documents.router,
        chat.router,
        exports.router,
    ):
        application.include_router(router)
    return application


app = create_app()
