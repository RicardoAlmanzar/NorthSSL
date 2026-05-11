from __future__ import annotations

import ipaddress
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from northssl.config.settings import NorthSSLSettings
from northssl.core.exceptions import (
    CertificateOperationError,
    DomainValidationError,
    PortConflictError,
    PrivilegeError,
    ProviderUnavailableError,
    ValidationError,
)
from northssl.core.contracts import SSLProvider
from northssl.core.models import CertificateMetadata
from northssl.core.models import ManualDnsChallengeSession
from northssl.core.services.certificate_reader import CertificateReader
from northssl.core.services.discovery import SystemDiscoveryService
from northssl.database.repository import CertificateRepository
from northssl.providers.certbot import CertbotProvider
from northssl.providers.self_signed import SelfSignedProvider

logger = logging.getLogger(__name__)

DOMAIN_PATTERN = re.compile(r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?<!-)(\.(?!-)[A-Za-z0-9-]{1,63}(?<!-))+$")
SUPPORTED_VALIDATION_METHODS = {"standalone", "webroot", "dns-01", "self-signed"}


@dataclass(slots=True)
class CertificateEngine:
    settings: NorthSSLSettings = field(default_factory=NorthSSLSettings)
    discovery_service: SystemDiscoveryService = field(default_factory=SystemDiscoveryService)
    reader: CertificateReader = field(default_factory=CertificateReader)
    repository: CertificateRepository = field(init=False)
    providers: dict[str, SSLProvider] = field(init=False)

    def __post_init__(self) -> None:
        self.repository = CertificateRepository.from_settings(self.settings)
        self.providers = {
            "certbot": CertbotProvider(settings=self.settings),
            "self-signed": SelfSignedProvider(settings=self.settings),
        }

    def issue(
        self,
        domain: str,
        provider_name: str = "certbot",
        email: str | None = None,
        validation_method: str = "standalone",
        webroot_path: str | None = None,
    ) -> CertificateMetadata:
        normalized_domain = self._validate_domain(domain)
        provider = self._resolve_provider(provider_name)
        self._validate_validation_method(validation_method)
        if validation_method.strip().lower() in {"dns-manual", "dns-01-manual"}:
            raise ValidationError("Use the DNS-01 assistant flow for manual DNS validation")
        diagnostics = self.discovery_service.collect()
        self._validate_environment(diagnostics, validation_method)

        operation = provider.issue_certificate(
            normalized_domain,
            email=email,
            validation_method=validation_method,
            webroot_path=webroot_path,
        )
        if not operation.success or not operation.certificate_path or not operation.private_key_path:
            raise CertificateOperationError(operation.message)

        inspection = self.reader.read(operation.certificate_path)
        metadata = CertificateMetadata(
            domain=normalized_domain,
            provider=provider.name,
            certificate_path=operation.certificate_path,
            private_key_path=operation.private_key_path,
            issued_at=datetime.now(timezone.utc),
            expires_at=inspection.not_after,
            status="active",
            validation_method=validation_method,
            chain_path=operation.chain_path,
            issuer=inspection.issuer,
            sans=inspection.sans,
            serial_number=inspection.serial_number,
        )
        saved = self.repository.save(metadata)
        logger.info("Issued certificate for %s via %s", normalized_domain, provider.name)
        return saved

    def list(self) -> list[CertificateMetadata]:
        return self.repository.list_all()

    def inspect(self, target: str) -> CertificateMetadata:
        path = Path(target)
        if path.exists():
            inspection = self.reader.read(str(path))
            return CertificateMetadata(
                domain=path.stem,
                provider="file",
                certificate_path=str(path),
                private_key_path="",
                issued_at=inspection.not_before or datetime.now(timezone.utc),
                expires_at=inspection.not_after,
                status="active" if inspection.valid else "expired",
                validation_method="unknown",
                issuer=inspection.issuer,
                sans=inspection.sans,
                serial_number=inspection.serial_number,
            )

        stored = self.repository.get_by_domain(target)
        if stored is None:
            raise CertificateOperationError(f"No certificate found for {target}")

        inspection = self.reader.read(stored.certificate_path)
        stored.issuer = inspection.issuer
        stored.sans = inspection.sans
        stored.expires_at = inspection.not_after
        return stored

    def revoke(self, domain: str, provider_name: str = "certbot", reason: str = "keycompromise") -> CertificateMetadata:
        stored = self.repository.get_by_domain(domain)
        if stored is None:
            raise CertificateOperationError(f"No certificate stored for {domain}")

        provider = self._resolve_provider(provider_name)
        operation = provider.revoke_certificate(stored.certificate_path, reason=reason)
        if not operation.success:
            raise CertificateOperationError(operation.message)

        stored.status = "revoked"
        saved = self.repository.save(stored)
        logger.info("Revoked certificate for %s via %s", domain, provider.name)
        return saved

    def start_manual_dns(self, domain: str, provider_name: str = "certbot", email: str | None = None) -> ManualDnsChallengeSession:
        normalized_domain = self._validate_domain(domain)
        provider = self._resolve_provider(provider_name)
        challenge = getattr(provider, "start_manual_dns_challenge", None)
        if challenge is None:
            raise ProviderUnavailableError(f"Provider {provider_name} does not support manual DNS-01")

        return challenge(normalized_domain, email=email)

    def complete_manual_dns(self, session_id: str, provider_name: str = "certbot") -> CertificateMetadata:
        provider = self._resolve_provider(provider_name)
        complete = getattr(provider, "complete_manual_dns_challenge", None)
        if complete is None:
            raise ProviderUnavailableError(f"Provider {provider_name} does not support manual DNS-01")

        operation = complete(session_id)
        if not operation.success or not operation.certificate_path or not operation.private_key_path:
            raise CertificateOperationError(operation.message)

        inspection = self.reader.read(operation.certificate_path)
        metadata = CertificateMetadata(
            domain=operation.domain or session_id,
            provider=provider.name,
            certificate_path=operation.certificate_path,
            private_key_path=operation.private_key_path,
            issued_at=datetime.now(timezone.utc),
            expires_at=inspection.not_after,
            status="active",
            validation_method=operation.validation_method or "dns-manual",
            chain_path=operation.chain_path,
            issuer=inspection.issuer,
            sans=inspection.sans,
            serial_number=inspection.serial_number,
        )
        saved = self.repository.save(metadata)
        logger.info("Completed manual DNS-01 certificate for %s via %s", saved.domain, provider.name)
        return saved

    def _resolve_provider(self, provider_name: str) -> SSLProvider:
        provider = self.providers.get(provider_name)
        if provider is None:
            raise ProviderUnavailableError(f"Unsupported provider: {provider_name}")
        if not provider.is_available():
            raise ProviderUnavailableError(f"Provider {provider_name} is not available")
        return provider

    def _validate_validation_method(self, validation_method: str) -> None:
        normalized_method = validation_method.strip().lower()
        if normalized_method not in SUPPORTED_VALIDATION_METHODS:
            raise ValidationError(f"Unsupported validation method: {validation_method}")

    def _validate_environment(self, diagnostics, validation_method: str) -> None:
        if validation_method in {"standalone", "http-01"} and not diagnostics.privilege.elevated:
            raise PrivilegeError("Standalone issuance requires elevated privileges")

        if validation_method in {"standalone", "http-01"}:
            occupied = [port.port for port in diagnostics.ports if port.port == 80 and port.occupied]
            if occupied:
                raise PortConflictError("Port 80 is already in use")

    def _validate_domain(self, domain: str) -> str:
        normalized = domain.strip().lower().rstrip(".")
        if not normalized or "/" in normalized or "://" in normalized or normalized.startswith("*."):
            raise DomainValidationError(f"Invalid domain: {domain}")

        try:
            ipaddress.ip_address(normalized)
        except ValueError:
            pass
        else:
            raise DomainValidationError("IP addresses are not valid certificate domains")

        try:
            normalized.encode("idna")
        except UnicodeError as exc:
            raise DomainValidationError(f"Invalid IDNA domain: {domain}") from exc

        if not DOMAIN_PATTERN.match(normalized):
            raise DomainValidationError(f"Invalid domain format: {domain}")

        return normalized