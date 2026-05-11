from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

from northssl.config.settings import NorthSSLSettings
from northssl.core.exceptions import CertificateOperationError, RenewalOperationError
from northssl.core.models import AuditEvent, CertificateHealthSnapshot, CertificateMetadata, RenewalPolicy, RenewalRunResult
from northssl.core.services.certificate_reader import CertificateReader
from northssl.database.audit_repository import AuditEventRepository
from northssl.database.repository import CertificateRepository
from northssl.providers.certbot import CertbotProvider
from northssl.renewal.locks import RenewalLockManager
from northssl.renewal.monitor import SSLMonitor

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RenewalEngine:
    settings: NorthSSLSettings = field(default_factory=NorthSSLSettings)
    repository: CertificateRepository = field(init=False)
    audit_repository: AuditEventRepository = field(init=False)
    reader: CertificateReader = field(default_factory=CertificateReader)
    provider: CertbotProvider = field(default_factory=CertbotProvider)
    monitor: SSLMonitor = field(default_factory=SSLMonitor)
    locks: RenewalLockManager = field(default_factory=RenewalLockManager)
    policy: RenewalPolicy = field(init=False)

    def __post_init__(self) -> None:
        self.repository = CertificateRepository.from_settings(self.settings)
        self.audit_repository = AuditEventRepository.from_settings(self.settings)
        self.policy = RenewalPolicy(
            enabled=self.settings.renewal_enabled,
            renew_before_days=self.settings.renewal_window_days,
            max_retries=self.settings.renewal_retry_count,
            retry_delay_seconds=self.settings.renewal_retry_delay_seconds,
            cooldown_seconds=self.settings.renewal_cooldown_seconds,
            check_interval_seconds=self.settings.renewal_check_interval_seconds,
            lock_timeout_seconds=self.settings.renewal_lock_timeout_seconds,
            https_timeout_seconds=self.settings.monitor_https_timeout_seconds,
            probe_port=self.settings.monitor_probe_port,
            verify_tls=self.settings.monitor_tls_verify,
        )

    def list_health(self) -> list[CertificateHealthSnapshot]:
        snapshots: list[CertificateHealthSnapshot] = []
        for certificate in self.repository.list_all():
            snapshots.append(self.inspect(certificate))
        return snapshots

    def inspect(self, certificate: CertificateMetadata) -> CertificateHealthSnapshot:
        inspection = self.reader.read(certificate.certificate_path)
        days_remaining = inspection.days_remaining
        renewal_due = days_remaining is not None and days_remaining <= self.policy.renew_before_days
        monitor_snapshot = self.monitor.probe(
            certificate.domain,
            port=self.policy.probe_port,
            timeout_seconds=self.policy.https_timeout_seconds,
            verify_tls=self.policy.verify_tls,
            certificate_path=certificate.certificate_path,
        )

        return CertificateHealthSnapshot(
            domain=certificate.domain,
            certificate_path=certificate.certificate_path,
            expires_at=inspection.not_after,
            days_remaining=days_remaining,
            issuer=inspection.issuer,
            sans=inspection.sans,
            valid=inspection.valid,
            renewal_due=renewal_due or monitor_snapshot.renewal_due,
            https_reachable=monitor_snapshot.https_reachable,
            tls_version=monitor_snapshot.tls_version,
            tls_error=monitor_snapshot.tls_error,
            checked_at=datetime.now(timezone.utc),
        )

    def due_certificates(self) -> list[CertificateMetadata]:
        due: list[CertificateMetadata] = []
        for certificate in self.repository.list_all():
            inspection = self.reader.read(certificate.certificate_path)
            if self._should_renew(certificate, inspection.days_remaining):
                due.append(certificate)
        return due

    def renew_due_certificates(self) -> list[RenewalRunResult]:
        results: list[RenewalRunResult] = []
        for certificate in self.due_certificates():
            results.append(self.renew_certificate(certificate.domain))
        return results

    def renew_certificate(self, domain: str) -> RenewalRunResult:
        started_at = datetime.now(timezone.utc)
        with self.locks.locked(domain, self.policy.lock_timeout_seconds):
            stored = self.repository.get_by_domain(domain)
            if stored is None:
                raise CertificateOperationError(f"No certificate stored for {domain}")

            previous_expires_at = stored.expires_at
            operation = self.provider.renew_certificate(domain)
            if not operation.success:
                result = RenewalRunResult(
                    domain=domain,
                    success=False,
                    message=operation.message,
                    attempted_at=started_at,
                    previous_expires_at=previous_expires_at,
                    retries_used=0,
                )
                self._record_event("renewal_failed", domain, "error", operation.message, {"provider": operation.provider})
                return result

            refreshed = self.reader.read(stored.certificate_path)
            stored.expires_at = refreshed.not_after
            stored.issuer = refreshed.issuer
            stored.sans = refreshed.sans
            stored.serial_number = refreshed.serial_number
            stored.status = "active" if refreshed.valid else "expired"
            self.repository.save(stored)

            result = RenewalRunResult(
                domain=domain,
                success=True,
                message=operation.message,
                attempted_at=started_at,
                previous_expires_at=previous_expires_at,
                new_expires_at=refreshed.not_after,
            )
            self._record_event("renewal_succeeded", domain, "info", operation.message, {"provider": operation.provider})
            return result

    def run_scan_and_renew(self) -> list[RenewalRunResult]:
        if not self.policy.enabled:
            raise RenewalOperationError("Renewal automation is disabled")
        return self.renew_due_certificates()

    def record_health_snapshot(self, certificate: CertificateMetadata) -> CertificateHealthSnapshot:
        snapshot = self.inspect(certificate)
        severity = "warn" if snapshot.renewal_due or snapshot.https_reachable is False else "info"
        self._record_event(
            "certificate_health",
            certificate.domain,
            severity,
            "Certificate health checked",
            {
                "valid": str(snapshot.valid),
                "renewal_due": str(snapshot.renewal_due),
                "https_reachable": str(snapshot.https_reachable),
            },
        )
        return snapshot

    def _should_renew(self, certificate: CertificateMetadata, days_remaining: int | None) -> bool:
        if not self.policy.enabled:
            return False
        if certificate.status not in {"active", "expiring", "issued"}:
            return False
        if days_remaining is None:
            return True
        return days_remaining <= self.policy.renew_before_days

    def _record_event(self, event_type: str, domain: str | None, severity: str, message: str, details: dict[str, str]) -> None:
        event = AuditEvent(
            event_type=event_type,
            domain=domain,
            severity=severity,
            message=message,
            created_at=datetime.now(timezone.utc),
            details=details,
        )
        try:
            self.audit_repository.save(event)
        except Exception:  # pragma: no cover - audit should never block renewal
            logger.exception("Failed to record audit event for %s", event_type)