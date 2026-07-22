"""Health and knowledge-base lifecycle endpoints."""

import logging

from fastapi import APIRouter, Depends

from api.dependencies import require_api_key
logger = logging.getLogger(__name__)
router = APIRouter(tags=["System"])


@router.delete("/reset", dependencies=[Depends(require_api_key)])
def reset_knowledge_base():
    from services.app_state import app_state
    from services.vector_db import vector_db

    vector_db.reset()
    app_state.registry.clear()
    logger.info("FAISS vector database and file registry wiped.")
    return {"message": "Knowledge base reset. All documents have been removed."}
