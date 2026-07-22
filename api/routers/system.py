"""Health and knowledge-base lifecycle endpoints."""

import logging

from fastapi import APIRouter, Depends

from api.dependencies import require_api_key
from core.config import settings
from services.app_state import app_state
from services.llm_manager import llm_manager
from services.vector_db import vector_db


logger = logging.getLogger(__name__)
router = APIRouter(tags=["System"])


@router.get("/")
def health_check():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
        "loaded_models": llm_manager.available_models,
        "indexed_files": len(app_state.registry),
        "docs": "/docs",
    }


@router.delete("/reset", dependencies=[Depends(require_api_key)])
def reset_knowledge_base():
    vector_db.reset()
    app_state.registry.clear()
    logger.info("FAISS vector database and file registry wiped.")
    return {"message": "Knowledge base reset. All documents have been removed."}
