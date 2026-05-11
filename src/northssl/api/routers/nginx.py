from __future__ import annotations

from fastapi import APIRouter, Depends

from northssl.api.dependencies import get_api_services
from northssl.api.schemas import (
    NginxAutomationRequestSchema,
    NginxAutomationResponseSchema,
    NginxConfigSnapshotSchema,
    NginxDeploymentResultSchema,
    CertificateMetadataSchema,
)
from northssl.api.services import NorthSSLApiServices
from northssl.core.models import NginxAutomationRequest
from northssl.nginx.service import NginxIntegrationService

router = APIRouter(prefix="/nginx", tags=["nginx"])


def _nginx_service(services: NorthSSLApiServices) -> NginxIntegrationService:
    return NginxIntegrationService(services.settings)


@router.get("/status", response_model=NginxConfigSnapshotSchema)
def nginx_status(services: NorthSSLApiServices = Depends(get_api_services)) -> NginxConfigSnapshotSchema:
    return NginxConfigSnapshotSchema.model_validate(_nginx_service(services).discover(), from_attributes=True)


@router.get("/configs", response_model=NginxConfigSnapshotSchema)
def nginx_configs(services: NorthSSLApiServices = Depends(get_api_services)) -> NginxConfigSnapshotSchema:
    return NginxConfigSnapshotSchema.model_validate(_nginx_service(services).discover(), from_attributes=True)


@router.post("/automate", response_model=NginxAutomationResponseSchema)
def automate_nginx(
    payload: NginxAutomationRequestSchema,
    services: NorthSSLApiServices = Depends(get_api_services),
) -> NginxAutomationResponseSchema:
    result = _nginx_service(services).automate(NginxAutomationRequest(**payload.model_dump()))
    return NginxAutomationResponseSchema(
        success=result.success,
        message=result.message,
        certificate=None if result.certificate is None else CertificateMetadataSchema.model_validate(result.certificate, from_attributes=True),
        deployment=None if result.deployment is None else NginxDeploymentResultSchema.model_validate(result.deployment, from_attributes=True),
        config=None if result.config is None else NginxConfigSnapshotSchema.model_validate(result.config, from_attributes=True),
    )


@router.post("/deploy", response_model=NginxDeploymentResultSchema)
def deploy_nginx(
    payload: NginxAutomationRequestSchema,
    services: NorthSSLApiServices = Depends(get_api_services),
) -> NginxDeploymentResultSchema:
    certificate = services.certificate_engine.issue(
        domain=payload.domain,
        provider_name=payload.provider,
        email=payload.email,
        validation_method=payload.validation_method,
        webroot_path=payload.document_root,
    )
    deployment = _nginx_service(services).deploy_certificate(
        certificate=certificate,
        document_root=payload.document_root,
        upstream_host=payload.upstream_host,
        upstream_port=payload.upstream_port,
        redirect_http=payload.redirect_http,
    )
    return NginxDeploymentResultSchema.model_validate(deployment, from_attributes=True)
