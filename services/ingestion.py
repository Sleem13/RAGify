"""Coordinate durable, asynchronous document ingestion stages."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from core.config import settings
from services.app_state import app_state
from services.data_analyzer import data_analyzer
from services.document_processor import document_processor
from services.job_store import job_store
from services.vector_db import vector_db


logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(self):
        self._tasks: set[asyncio.Task] = set()
        settings.upload_temp_path.mkdir(parents=True, exist_ok=True)
        for stale_upload in settings.upload_temp_path.glob("ragify-upload-*"):
            stale_upload.unlink(missing_ok=True)

    def enqueue(self, path: Path, filename: str) -> dict:
        job = job_store.create(filename)
        task = asyncio.create_task(self._process(job["id"], path, filename))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return job

    async def _process(self, job_id: str, path: Path, filename: str) -> None:
        try:
            job_store.update(job_id, status="processing", stage="extracting", progress=15)
            contents = await asyncio.to_thread(path.read_bytes)
            extension = Path(filename).suffix.lower()

            if extension in settings.excel_extensions:
                analysis = await data_analyzer.analyze_excel(contents, filename)
                job_store.update(job_id, stage="chunking", progress=50)
                chunks = await document_processor.process_excel_for_rag(contents, filename)
                if not chunks:
                    raise ValueError("The spreadsheet did not contain indexable data.")
                metadata = {
                    "type": "excel",
                    "chunks": len(chunks),
                    "charts": len(analysis.get("charts", [])),
                }
                result = {
                    "filename": filename,
                    "status": "analyzed",
                    "type": "excel",
                    "analysis": analysis,
                    "message": f"'{filename}' was analyzed and indexed successfully.",
                }
            else:
                chunks = await document_processor.process_file(contents, filename)
                if not chunks:
                    raise ValueError("No readable content was found in the uploaded document.")
                metadata = {"type": "document", "chunks": len(chunks)}
                result = {
                    "filename": filename,
                    "status": "processed",
                    "type": "document",
                    "chunks": len(chunks),
                    "message": f"'{filename}' was indexed in {len(chunks)} chunks and is ready for questions.",
                }

            job_store.update(job_id, stage="embedding", progress=70)
            previous_chunks = await asyncio.to_thread(
                vector_db.documents_for_filename, filename
            )
            await asyncio.to_thread(vector_db.replace_file_chunks, chunks, filename)
            job_store.update(job_id, stage="finalizing", progress=95)
            try:
                await asyncio.to_thread(app_state.registry.set, filename, metadata)
            except Exception:
                logger.exception("Registry commit failed for '%s'; rolling back its index.", filename)
                if previous_chunks:
                    await asyncio.to_thread(
                        vector_db.replace_file_chunks, previous_chunks, filename
                    )
                else:
                    await asyncio.to_thread(vector_db.delete_by_filename, filename)
                raise
            job_store.update(
                job_id,
                status="completed",
                stage="ready",
                progress=100,
                result=result,
                error=None,
            )
        except Exception as exc:
            logger.exception("Ingestion job %s failed for '%s'.", job_id, filename)
            job_store.update(
                job_id,
                status="failed",
                stage="failed",
                progress=100,
                error=str(exc) or type(exc).__name__,
            )
        finally:
            try:
                await asyncio.to_thread(path.unlink, missing_ok=True)
            except OSError:
                logger.warning("Could not remove temporary upload '%s'.", path)


ingestion_service = IngestionService()
