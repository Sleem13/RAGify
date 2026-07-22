"""API-key management endpoints."""

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import require_api_key
from services.app_state import app_state


router = APIRouter(tags=["API Key"])


@router.post("/generate-api-key", dependencies=[Depends(require_api_key)])
def generate_api_key():
    key = app_state.api_keys.generate()
    return {
        "api_key": key,
        "message": "Keep this key safe. Use it in the 'X-Api-Key' header for all API requests.",
    }


@router.get("/list-api-keys", dependencies=[Depends(require_api_key)])
def list_api_keys():
    masked = app_state.api_keys.masked()
    return {"active_keys": masked, "total": len(masked)}


@router.delete("/revoke-api-key", dependencies=[Depends(require_api_key)])
def revoke_api_key(api_key: str):
    if app_state.api_keys.revoke(api_key):
        return {"message": "API key revoked successfully."}
    raise HTTPException(status_code=404, detail="API key not found.")
