import mimetypes

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.storage import get_storage
from app.storage.signing import verify

router = APIRouter(tags=["media"])


@router.get("/media/{key:path}")
def get_media(key: str, exp: int, sig: str):
    if not verify(key, exp, sig):
        raise HTTPException(status_code=403, detail="Invalid or expired media URL")

    storage = get_storage()
    if not storage.exists(key):
        raise HTTPException(status_code=404, detail="Not found")

    data = storage.read(key)
    media_type = mimetypes.guess_type(key)[0] or "application/octet-stream"
    return Response(content=data, media_type=media_type)
