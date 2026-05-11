from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from northssl.core.models import (
    CertificateInspection,
    CertificateMetadata,
    CertificateOperationResult,
    CertbotSnapshot,
    DiagnosticsReport,
    PlatformSnapshot,
    PortSnapshot,
    PrivilegeSnapshot,
    WebServerSnapshot,
)

@runtime_checkable
class SSLProvider(Protocol):
    name: str

    def is_available(self) -> bool: ...

    def issue_certificate(
        self,
        domain: str,
        email: str | None = None,
        validation_method: str = "standalone",
        webroot_path: str | None = None,
    ) -> CertificateOperationResult: ...

    def renew_certificate(self, domain: str) -> CertificateOperationResult: ...

    def revoke_certificate(self, certificate_path: str, reason: str = "keycompromise") -> CertificateOperationResult: ...

    def discover(self) -> CertbotSnapshot: ...


@runtime_checkable
class ProviderAdapter(Protocol):
    name: str

    def is_available(self) -> bool: ...

    def issue_certificate(self, domain: str, email: str | None = None, webroot_path: str | None = None) -> None: ...

    def renew_certificate(self, domain: str) -> None: ...

    def revoke_certificate(self, domain: str) -> None: ...

    def discover(self) -> CertbotSnapshot: ...

@runtime_checkable
class WebServerAdapter(Protocol):
    name: str

    def is_available(self) -> bool: ...

    def reload(self) -> None: ...

    def discover(self) -> WebServerSnapshot: ...

@runtime_checkable
class SchedulerAdapter(Protocol):
    name: str

    def schedule_renewal(self) -> None: ...


@runtime_checkable
class PlatformDetector(Protocol):
    def detect(self) -> PlatformSnapshot: ...


@runtime_checkable
class PrivilegeDetector(Protocol):
    def detect(self) -> PrivilegeSnapshot: ...


@runtime_checkable
class PortScanner(Protocol):
    def scan(self, ports: Sequence[int]) -> list[PortSnapshot]: ...


@runtime_checkable
class DiscoveryService(Protocol):
    def collect(self) -> DiagnosticsReport: ...
