from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.backends import default_backend

from northssl.core.exceptions import CertificateNotFoundError
from northssl.core.models import CertificateInspection


@dataclass(slots=True)
class CertificateReader:
    def read(self, certificate_path: str) -> CertificateInspection:
        path = Path(certificate_path)
        if not path.exists():
            raise CertificateNotFoundError(f"Certificate file not found: {certificate_path}")

        data = path.read_bytes()
        try:
            certificate = x509.load_pem_x509_certificate(data, default_backend())
        except ValueError:
            certificate = x509.load_der_x509_certificate(data, default_backend())

        subject = certificate.subject.rfc4514_string()
        issuer = certificate.issuer.rfc4514_string()
        sans = self._read_sans(certificate)
        if hasattr(certificate, "not_valid_before_utc"):
            not_before = certificate.not_valid_before_utc
        else:
            not_before = certificate.not_valid_before.replace(tzinfo=timezone.utc)

        if hasattr(certificate, "not_valid_after_utc"):
            not_after = certificate.not_valid_after_utc
        else:
            not_after = certificate.not_valid_after.replace(tzinfo=timezone.utc)

        if not_before.tzinfo is None:
            not_before = not_before.replace(tzinfo=timezone.utc)
        if not_after.tzinfo is None:
            not_after = not_after.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)

        return CertificateInspection(
            certificate_path=str(path),
            subject=subject,
            issuer=issuer,
            sans=sans,
            serial_number=format(certificate.serial_number, "x"),
            not_before=not_before,
            not_after=not_after,
            expired=now > not_after,
            valid=not_before <= now <= not_after,
            days_remaining=(not_after - now).days,
        )

    def _read_sans(self, certificate: x509.Certificate) -> list[str]:
        try:
            extension = certificate.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        except x509.ExtensionNotFound:
            return []

        values: list[str] = []
        for value in extension.value:
            values.append(str(value.value) if hasattr(value, "value") else str(value))
        return values