from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends

from northssl.api.dependencies import get_api_services
from northssl.api.schemas import RenewalRunResponseSchema, RenewalRunResultSchema, RenewalStatusResponseSchema
from northssl.api.services import NorthSSLApiServices

router = APIRouter(prefix="/renewal", tags=["renewal"])


@router.get("/status", response_model=RenewalStatusResponseSchema)
def get_renewal_status(services: NorthSSLApiServices = Depends(get_api_services)) -> RenewalStatusResponseSchema:
    renewal = services.renewal_service
    return RenewalStatusResponseSchema(
        enabled=renewal.engine.policy.enabled,
        policy=asdict(renewal.engine.policy),
        jobs=renewal.jobs(),
        health=renewal.health(),
    )


@router.post("/run", response_model=RenewalRunResponseSchema)
def run_renewal_cycle(services: NorthSSLApiServices = Depends(get_api_services)) -> RenewalRunResponseSchema:
    results = services.renewal_service.run_cycle()
    return RenewalRunResponseSchema(
        success=True,
        message="Renewal cycle completed",
        results=results,
    )


@router.post("/start", response_model=dict[str, str])
def start_renewal_scheduler(services: NorthSSLApiServices = Depends(get_api_services)) -> dict[str, str]:
    services.renewal_service.start()
    return {"status": "started"}


@router.post("/stop", response_model=dict[str, str])
def stop_renewal_scheduler(services: NorthSSLApiServices = Depends(get_api_services)) -> dict[str, str]:
    services.renewal_service.stop()
    return {"status": "stopped"}