from __future__ import annotations

from fastapi import APIRouter

from northssl.api.dependencies import get_api_services
from northssl.api.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    services = get_api_services()
    settings = services.settings
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        environment=settings.environment,
        version=settings.version,
    )
