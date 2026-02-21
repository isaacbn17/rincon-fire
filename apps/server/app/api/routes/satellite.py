from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.config import get_settings


router = APIRouter(prefix="/satellite", tags=["satellite"])


@router.get("/files/{filename}", name="get_satellite_file")
def get_satellite_file(filename: str) -> FileResponse:
    settings = get_settings()
    file_path = (settings.satellite_dir / filename).resolve()

    try:
        file_path.relative_to(settings.satellite_dir.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid filename") from exc

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Satellite file not found")

    media_type = "image/png"
    if Path(filename).suffix.lower() in {".jpg", ".jpeg"}:
        media_type = "image/jpeg"

    return FileResponse(path=file_path, media_type=media_type)
