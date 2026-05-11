from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from northssl.api.dependencies import get_api_services
from northssl.api.schemas import LogsResponse
from northssl.api.services import NorthSSLApiServices

router = APIRouter(tags=["logs"])


@router.get("/logs", response_model=LogsResponse)
def get_logs(
    limit: int = Query(default=200, ge=0, le=1000),
    services: NorthSSLApiServices = Depends(get_api_services),
) -> LogsResponse:
    snapshot = services.log_service.tail(limit=limit)
    return LogsResponse(
        path=snapshot.path,
        exists=snapshot.exists,
        line_count=snapshot.line_count,
        truncated=snapshot.truncated,
        lines=snapshot.lines,
    )
