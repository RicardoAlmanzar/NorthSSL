from __future__ import annotations

import socket
import ssl
from dataclasses import dataclass
from datetime import datetime, timezone

from northssl.core.models import CertificateHealthSnapshot


@dataclass(slots=True)
class SSLMonitor:
    def probe(
        self,
        domain: str,
        port: int = 443,
        timeout_seconds: int = 10,
        verify_tls: bool = True,
        certificate_path: str | None = None,
    ) -> CertificateHealthSnapshot:
        checked_at = datetime.now(timezone.utc)
        try:
            context = ssl.create_default_context() if verify_tls else ssl._create_unverified_context()  # type: ignore[attr-defined]
            with socket.create_connection((domain, port), timeout=timeout_seconds) as raw_socket:
                with context.wrap_socket(raw_socket, server_hostname=domain) as tls_socket:
                    cert = tls_socket.getpeercert()
                    expires_at = self._parse_not_after(cert.get("notAfter"))
                    sans = [value for key, value in cert.get("subjectAltName", []) if key in {"DNS", "IP Address"}]
                    issuer = self._flatten_name(cert.get("issuer", []))
                    days_remaining = (expires_at - checked_at).days if expires_at else None

                    return CertificateHealthSnapshot(
                        domain=domain,
                        certificate_path=certificate_path,
                        expires_at=expires_at,
                        days_remaining=days_remaining,
                        issuer=issuer,
                        sans=sans,
                        valid=expires_at is None or checked_at <= expires_at,
                        renewal_due=days_remaining is not None and days_remaining <= 30,
                        https_reachable=True,
                        tls_version=tls_socket.version(),
                        checked_at=checked_at,
                    )
        except Exception as exc:
            return CertificateHealthSnapshot(
                domain=domain,
                certificate_path=certificate_path,
                expires_at=None,
                days_remaining=None,
                issuer=None,
                sans=[],
                valid=False,
                renewal_due=False,
                https_reachable=False,
                tls_error=str(exc),
                checked_at=checked_at,
            )

    def _parse_not_after(self, value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.strptime(value, "%b %d %H:%M:%S %Y %Z")
        except ValueError:
            return None
        return parsed.replace(tzinfo=timezone.utc)

    def _flatten_name(self, pairs: list[tuple[tuple[str, str], ...]]) -> str | None:
        components: list[str] = []
        for rdn in pairs:
            for key, value in rdn:
                components.append(f"{key}={value}")
        return ", ".join(components) if components else None