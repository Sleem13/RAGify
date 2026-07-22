"""RAGify FastAPI application composition root."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

from api.routers import auth, chat, documents, exports, system
from core.config import settings


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=9999, reload=True)
