from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from northssl.core.exceptions import (
    CertificateNotFoundError,
    CertificateOperationError,
    DomainValidationError,
    NorthSSLError,
    PortConflictError,
    PrivilegeError,
    ProviderUnavailableError,
    ValidationError,
)

logger = logging.getLogger(__name__)


def _status_for_exception(exc: Exception) -> int:
    if isinstance(exc, (ValidationError, DomainValidationError)):
        return 400
    if isinstance(exc, CertificateNotFoundError):
        return 404
    if isinstance(exc, PrivilegeError):
        return 403
    if isinstance(exc, PortConflictError):
        return 409
    if isinstance(exc, ProviderUnavailableError):
        return 503
    if isinstance(exc, CertificateOperationError):
        return 422
    if isinstance(exc, NorthSSLError):
        return 400
    return 500


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NorthSSLError)
    async def handle_northssl_error(request: Request, exc: NorthSSLError) -> JSONResponse:
        status_code = _status_for_exception(exc)
        logger.warning("NorthSSL API error on %s: %s", request.url.path, exc)
        return JSONResponse(status_code=status_code, content={"detail": str(exc), "code": exc.code})
