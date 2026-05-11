from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from northssl.core.exceptions import SchedulerError
from northssl.core.models import RenewalJobSnapshot
from northssl.renewal.engine import RenewalEngine


@dataclass(slots=True)
class RenewalScheduler:
    engine: RenewalEngine
    scheduler: BackgroundScheduler = field(default_factory=BackgroundScheduler)
    started_at: datetime | None = None

    def start(self) -> None:
        if self.scheduler.running:
            return

        self.scheduler.add_job(
            self.engine.run_scan_and_renew,
            trigger=IntervalTrigger(seconds=self.engine.policy.check_interval_seconds),
            id="northssl-renewal-scan",
            name="NorthSSL Renewal Scan",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=self.engine.policy.check_interval_seconds,
        )
        self.scheduler.add_job(
            self._run_health_snapshot,
            trigger=IntervalTrigger(seconds=self.engine.policy.check_interval_seconds),
            id="northssl-ssl-health",
            name="NorthSSL SSL Health Check",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=self.engine.policy.check_interval_seconds,
        )
        self.scheduler.start()
        self.started_at = datetime.now(timezone.utc)

    def shutdown(self) -> None:
        if not self.scheduler.running:
            return
        self.scheduler.shutdown(wait=False)

    def run_once(self) -> list[object]:
        if not self.engine.policy.enabled:
            raise SchedulerError("Renewal scheduler is disabled")
        return [self.engine.run_scan_and_renew(), self._run_health_snapshot()]

    def snapshot(self) -> list[RenewalJobSnapshot]:
        snapshots: list[RenewalJobSnapshot] = []
        for job in self.scheduler.get_jobs():
            snapshots.append(
                RenewalJobSnapshot(
                    name=job.name,
                    enabled=job.next_run_time is not None,
                    next_run_at=job.next_run_time,
                )
            )
        return snapshots

    def _run_health_snapshot(self) -> list[object]:
        return [self.engine.record_health_snapshot(certificate) for certificate in self.engine.repository.list_all()]