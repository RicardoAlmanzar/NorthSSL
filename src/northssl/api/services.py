from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from northssl.config.settings import NorthSSLSettings
from northssl.core.services.certificate_engine import CertificateEngine
from northssl.core.services.discovery import SystemDiscoveryService
from northssl.renewal.service import RenewalService

@dataclass(slots=True)
class LogSnapshot:
    path: str
    exists: bool
    line_count: int
    truncated: bool
    lines: list[str]


@dataclass(slots=True)
class LogService:
    settings: NorthSSLSettings

    def tail(self, limit: int = 200) -> LogSnapshot:
        log_path = self.settings.log_file_path
        if not log_path.exists():
            return LogSnapshot(
                path=str(log_path),
                exists=False,
                line_count=0,
                truncated=False,
                lines=[],
            )

        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
        if limit < 0:
            limit = 0
        selected = lines[-limit:] if limit else []
        return LogSnapshot(
            path=str(log_path),
            exists=True,
            line_count=len(lines),
            truncated=len(lines) > len(selected),
            lines=selected,
        )


@dataclass(slots=True)
class NorthSSLApiServices:
    settings: NorthSSLSettings
    certificate_engine: CertificateEngine
    discovery_service: SystemDiscoveryService
    log_service: LogService
    renewal_service: RenewalService


def build_api_services(settings: NorthSSLSettings) -> NorthSSLApiServices:
    return NorthSSLApiServices(
        settings=settings,
        certificate_engine=CertificateEngine(settings),
        discovery_service=SystemDiscoveryService(),
        log_service=LogService(settings),
        renewal_service=RenewalService(settings),
    )
