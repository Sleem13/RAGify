"""Document registry, upload, processing, and indexing endpoints."""

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from api.dependencies import require_api_key
from core.config import settings
from services.app_state import app_state
from services.data_analyzer import data_analyzer
from services.document_processor import document_processor
from services.vector_db import vector_db


logger = logging.getLogger(__name__)
router = APIRouter(tags=["Documents"])


@router.get("/files")
def list_files():
    files = app_state.registry.snapshot()
    return {"files": files, "total": len(files)}


@router.delete("/files/{filename}", dependencies=[Depends(require_api_key)])
def delete_file(filename: str):
    if filename not in app_state.registry:
        raise HTTPException(status_code=404, detail=f"File '{filename}' not found in registry.")

    deleted_from_faiss = vector_db.delete_by_filename(filename)
    app_state.registry.remove(filename)
    return {
        "message": f"'{filename}' removed from registry and vector database.",
        "faiss_deleted": deleted_from_faiss,
    }


@router.post("/upload", dependencies=[Depends(require_api_key)])
async def upload_file(file: UploadFile = File(...)):
    filename = file.filename or "unknown"
    extension = Path(filename).suffix.lower()
    contents = await file.read()

    if not contents:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(contents) > settings.max_file_size:
        size_mb = len(contents) / 1024 / 1024
        limit_mb = settings.max_file_size // 1024 // 1024
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f} MB). Maximum allowed size is {limit_mb} MB.",
        )

    if extension in settings.excel_extensions:
        return await _ingest_spreadsheet(contents, filename)
    if document_processor.is_supported(filename):
        return await _ingest_document(contents, filename)

    raise HTTPException(
        status_code=415,
        detail=(
            f"Unsupported file type '{extension}'. Supported: PDF, DOCX, TXT, PPTX, "
            "PNG, JPG, JPEG, XLSX, XLS, CSV, JSON."
        ),
    )


async def _ingest_spreadsheet(contents: bytes, filename: str) -> dict:
    try:
        analysis = await data_analyzer.analyze_excel(contents, filename)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis error: {exc}") from exc

    try:
        chunks = await document_processor.process_excel_for_rag(contents, filename)
        if not chunks:
            raise ValueError("The spreadsheet did not contain indexable data.")
        vector_db.replace_file_chunks(chunks, filename=filename)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Indexing error: {exc}") from exc

    metadata = {
        "type": "excel",
        "chunks": len(chunks),
        "charts": len(analysis.get("charts", [])),
    }
    app_state.registry.set(filename, metadata)
    return {
        "filename": filename,
        "status": "analyzed",
        "type": "excel",
        "analysis": analysis,
        "message": (
            f"'{filename}' was analyzed and indexed. You can ask questions about the data "
            "and view its dashboard."
        ),
    }


async def _ingest_document(contents: bytes, filename: str) -> dict:
    try:
        chunks = await document_processor.process_file(contents, filename)
    except ValueError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Processing error: {exc}") from exc

    if not chunks:
        raise HTTPException(
            status_code=422,
            detail="No readable content was found in the uploaded document.",
        )
    try:
        vector_db.replace_file_chunks(chunks, filename=filename)
    except Exception as exc:
        logger.exception("Could not index '%s'.", filename)
        raise HTTPException(status_code=500, detail=f"Indexing error: {exc}") from exc

    app_state.registry.set(filename, {"type": "document", "chunks": len(chunks)})
    return {
        "filename": filename,
        "status": "processed",
        "type": "document",
        "chunks": len(chunks),
        "message": f"'{filename}' was indexed in {len(chunks)} chunks and is ready for questions.",
    }
