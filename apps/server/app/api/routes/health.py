from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app.schemas.api import HealthResponse


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    return HealthResponse(status="ok", time_utc=datetime.now(timezone.utc))
