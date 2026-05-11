from __future__ import annotations

from fastapi import APIRouter, Depends

from northssl.api.dependencies import get_api_services
from northssl.api.schemas import DiagnosticsReportSchema, SystemStatusResponse
from northssl.api.services import NorthSSLApiServices

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status", response_model=SystemStatusResponse)
def system_status(services: NorthSSLApiServices = Depends(get_api_services)) -> SystemStatusResponse:
    diagnostics = services.discovery_service.collect()
    return SystemStatusResponse(
        settings=services.settings.model_dump(mode="json"),
        diagnostics=DiagnosticsReportSchema.model_validate(diagnostics, from_attributes=True),
    )
