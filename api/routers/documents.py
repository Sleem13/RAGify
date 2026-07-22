"""Document upload, ingestion status, registry, and deletion endpoints."""

from pathlib import Path
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from api.dependencies import require_api_key
from core.config import settings
from services.app_state import app_state
from services.document_processor import document_processor
from services.ingestion import ingestion_service
from services.job_store import job_store
from services.vector_db import vector_db


router = APIRouter(tags=["Documents"])


@router.get("/files", dependencies=[Depends(require_api_key)])
def list_files():
    files = app_state.registry.snapshot()
    return {"files": files, "total": len(files)}


@router.get("/jobs/{job_id}", dependencies=[Depends(require_api_key)])
def get_ingestion_job(job_id: str):
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Ingestion job not found.")
    return job


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


@router.post(
    "/upload",
    dependencies=[Depends(require_api_key)],
    status_code=status.HTTP_202_ACCEPTED,
)
async def upload_file(file: UploadFile = File(...)):
    filename = Path(file.filename or "unknown").name
    extension = Path(filename).suffix.lower()
    supported = extension in settings.excel_extensions or document_processor.is_supported(filename)
    if not supported:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported file type '{extension}'. Supported: PDF, DOCX, TXT, PPTX, "
                "PNG, JPG, JPEG, XLSX, XLS, CSV, JSON."
            ),
        )

    settings.upload_temp_path.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    size = 0
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            suffix=extension,
            prefix="ragify-upload-",
            dir=settings.upload_temp_path,
        ) as temporary:
            temporary_path = Path(temporary.name)
            while chunk := await file.read(settings.upload_chunk_size):
                size += len(chunk)
                if size > settings.max_file_size:
                    limit_mb = settings.max_file_size // 1024 // 1024
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum allowed size is {limit_mb} MB.",
                    )
                temporary.write(chunk)
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    if size == 0:
        temporary_path.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    job = ingestion_service.enqueue(temporary_path, filename)
    return {
        "job_id": job["id"],
        "filename": filename,
        "status": job["status"],
        "stage": job["stage"],
        "progress": job["progress"],
        "message": f"'{filename}' was accepted and is being processed.",
    }
