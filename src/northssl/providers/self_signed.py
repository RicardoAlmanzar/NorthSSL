from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from shutil import rmtree

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from northssl.config.settings import NorthSSLSettings
from northssl.core.models import CertbotSnapshot, CertificateOperationResult

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SelfSignedProvider:
    settings: NorthSSLSettings | None = None

    @property
    def name(self) -> str:
        return "self-signed"

    def is_available(self) -> bool:
        return True

    def discover(self) -> CertbotSnapshot:
        return CertbotSnapshot(
            installed=True,
            binary_path="builtin",
            version="local",
            compatible=True,
            raw_output="Self-signed certificate provider is available",
        )

    def issue_certificate(
        self,
        domain: str,
        email: str | None = None,
        validation_method: str = "self-signed",
        webroot_path: str | None = None,
    ) -> CertificateOperationResult:
        try:
            normalized_domain = domain.strip().lower().rstrip(".")
            certificate_path, private_key_path = self._paths_for_domain(normalized_domain)
            certificate_path.parent.mkdir(parents=True, exist_ok=True)

            private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            subject = x509.Name(
                [
                    x509.NameAttribute(NameOID.COMMON_NAME, normalized_domain),
                    x509.NameAttribute(NameOID.ORGANIZATION_NAME, "NorthSSL"),
                ]
            )
            now = datetime.now(timezone.utc)
            certificate = (
                x509.CertificateBuilder()
                .subject_name(subject)
                .issuer_name(subject)
                .public_key(private_key.public_key())
                .serial_number(x509.random_serial_number())
                .not_valid_before(now - timedelta(minutes=1))
                .not_valid_after(now + timedelta(days=365))
                .add_extension(x509.SubjectAlternativeName([x509.DNSName(normalized_domain)]), critical=False)
                .sign(private_key, hashes.SHA256(), default_backend())
            )

            private_key_path.write_bytes(
                private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.TraditionalOpenSSL,
                    encryption_algorithm=serialization.NoEncryption(),
                )
            )
            certificate_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))

            return CertificateOperationResult(
                success=True,
                message=f"Self-signed certificate generated for {normalized_domain}",
                provider=self.name,
                domain=normalized_domain,
                validation_method=validation_method,
                certificate_path=str(certificate_path),
                private_key_path=str(private_key_path),
                chain_path=None,
                raw_output="Generated a local self-signed certificate",
                exit_code=0,
            )
        except Exception as exc:  # pragma: no cover - defensive wrapper around crypto/file IO
            logger.exception("Failed to generate self-signed certificate for %s", domain)
            return CertificateOperationResult(
                success=False,
                message=f"Failed to generate self-signed certificate: {exc}",
                provider=self.name,
                domain=domain,
                validation_method=validation_method,
                raw_output=str(exc),
                exit_code=1,
            )

    def renew_certificate(self, domain: str) -> CertificateOperationResult:
        return self.issue_certificate(domain, validation_method="self-signed")

    def revoke_certificate(self, certificate_path: str, reason: str = "keycompromise") -> CertificateOperationResult:
        path = Path(certificate_path)
        if not path.exists():
            return CertificateOperationResult(
                success=False,
                message=f"Certificate file not found: {certificate_path}",
                provider=self.name,
                certificate_path=certificate_path,
                raw_output="Certificate file missing",
                exit_code=1,
            )

        private_key_path = path.parent / path.name.replace(".crt.pem", ".key.pem")
        path.unlink(missing_ok=True)
        private_key_path.unlink(missing_ok=True)

        parent = path.parent
        if parent.exists() and not any(parent.iterdir()):
            rmtree(parent, ignore_errors=True)

        return CertificateOperationResult(
            success=True,
            message="Self-signed certificate removed",
            provider=self.name,
            certificate_path=certificate_path,
            raw_output=f"Removed certificate for reason: {reason}",
            exit_code=0,
        )

    def _paths_for_domain(self, domain: str) -> tuple[Path, Path]:
        data_dir = self.settings.data_dir if self.settings is not None else Path.home() / ".northssl"
        base_dir = data_dir / "certificates" / "self-signed" / domain
        certificate_path = base_dir / f"{domain}.crt.pem"
        private_key_path = base_dir / f"{domain}.key.pem"
        return certificate_path, private_key_path