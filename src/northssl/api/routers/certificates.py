from __future__ import annotations

from fastapi import APIRouter, Depends, status

from northssl.api.dependencies import get_api_services
from northssl.api.schemas import (
    CertificateIssueRequest,
    CertificateIssueResponse,
    CertificateMetadataSchema,
    ManualDnsChallengeCompleteRequest,
    ManualDnsChallengeCompleteResponse,
    ManualDnsChallengeSessionSchema,
    ManualDnsChallengeStartRequest,
    ManualDnsChallengeStartResponse,
)
from northssl.api.services import NorthSSLApiServices

router = APIRouter(prefix="/certificates", tags=["certificates"])


@router.get("", response_model=list[CertificateMetadataSchema])
def list_certificates(services: NorthSSLApiServices = Depends(get_api_services)) -> list[CertificateMetadataSchema]:
    return [CertificateMetadataSchema.model_validate(item, from_attributes=True) for item in services.certificate_engine.list()]


@router.post("/issue", response_model=CertificateIssueResponse, status_code=status.HTTP_201_CREATED)
def issue_certificate(
    payload: CertificateIssueRequest,
    services: NorthSSLApiServices = Depends(get_api_services),
) -> CertificateIssueResponse:
    certificate = services.certificate_engine.issue(
        domain=payload.domain,
        provider_name=payload.provider,
        email=payload.email,
        validation_method=payload.validation_method,
        webroot_path=payload.webroot_path,
    )
    return CertificateIssueResponse(
        message=f"Issued certificate for {certificate.domain}",
        certificate=CertificateMetadataSchema.model_validate(certificate, from_attributes=True),
    )


@router.post("/dns-01/start", response_model=ManualDnsChallengeStartResponse, status_code=status.HTTP_201_CREATED)
def start_manual_dns_challenge(
    payload: ManualDnsChallengeStartRequest,
    services: NorthSSLApiServices = Depends(get_api_services),
) -> ManualDnsChallengeStartResponse:
    session = services.certificate_engine.start_manual_dns(domain=payload.domain, provider_name=payload.provider, email=payload.email)
    return ManualDnsChallengeStartResponse(
        message="Create the TXT record in your DNS provider, then complete the challenge",
        session=ManualDnsChallengeSessionSchema.model_validate(session, from_attributes=True),
    )


@router.post("/dns-01/complete", response_model=ManualDnsChallengeCompleteResponse)
def complete_manual_dns_challenge(
    payload: ManualDnsChallengeCompleteRequest,
    services: NorthSSLApiServices = Depends(get_api_services),
) -> ManualDnsChallengeCompleteResponse:
    certificate = services.certificate_engine.complete_manual_dns(session_id=payload.session_id, provider_name=payload.provider)
    return ManualDnsChallengeCompleteResponse(
        message=f"Issued certificate for {certificate.domain}",
        certificate=CertificateMetadataSchema.model_validate(certificate, from_attributes=True),
    )
