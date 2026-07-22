"""Grounded RAG chat endpoint."""

import json
import logging

from fastapi import APIRouter, Depends, Form, HTTPException

from api.dependencies import require_api_key
from services.retrieval import build_context, build_grounded_prompt, normalize_history


logger = logging.getLogger(__name__)
router = APIRouter(tags=["Chat"])


@router.post("/chat", dependencies=[Depends(require_api_key)])
async def chat(message: str = Form(...), history: str = Form(default="[]")):
    from services.app_state import app_state
    from services.llm_manager import llm_manager
    from services.vector_db import vector_db

    message = message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    try:
        chat_history = normalize_history(json.loads(history))
    except (TypeError, json.JSONDecodeError):
        chat_history = []

    try:
        matches = vector_db.hybrid_search(message, top_k=10)
    except Exception as exc:
        logger.warning("Hybrid retrieval failed: %s", exc)
        matches = []

    context, sources = build_context(matches)
    indexed_files = app_state.registry.names()
    if not context:
        response = (
            "I could not find this information in the uploaded files."
            if indexed_files
            else "Upload a document or spreadsheet first, then ask a question about it."
        )
        return {
            "response": response,
            "context_found": False,
            "action": None,
            "sources": [],
        }

    prompt = build_grounded_prompt(message, context, chat_history, indexed_files)
    try:
        response_text = await llm_manager.generate_response(prompt)
    except RuntimeError as exc:
        return {
            "response": "All AI providers are currently unavailable. Please try again in a moment.",
            "context_found": False,
            "sources": sources,
            "error": str(exc),
        }

    action = None
    if "[ACTION: GENERATE_DASHBOARD]" in response_text:
        action = "GENERATE_DASHBOARD"
        response_text = response_text.replace("[ACTION: GENERATE_DASHBOARD]", "").strip()
        if not response_text:
            response_text = "I analyzed the data and prepared your dashboard."

    return {
        "response": response_text,
        "context_found": True,
        "action": action,
        "sources": sources,
    }
