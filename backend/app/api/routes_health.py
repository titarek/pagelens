from datetime import datetime, timezone
from fastapi import APIRouter
from app.core.config import settings
from app.schemas.request import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        timestamp=datetime.now(timezone.utc),
        environment=settings.environment,
    )
