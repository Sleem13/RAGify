"""Analytics export endpoint."""

import io
import json

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import StreamingResponse

from api.dependencies import require_api_key
from services.exporter import export_analytics


router = APIRouter(tags=["Export"])


@router.post("/export", dependencies=[Depends(require_api_key)])
async def export_data(format: str = Form("json"), data: str = Form(...)):
    try:
        parsed = json.loads(data)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON data provided.") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail="Export data must be a JSON object.")

    try:
        content, media_type, filename = export_analytics(format, parsed)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return StreamingResponse(
        io.BytesIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
