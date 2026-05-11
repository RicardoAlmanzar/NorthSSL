from __future__ import annotations

from dataclasses import dataclass, field

from northssl.config.settings import NorthSSLSettings
from northssl.core.models import CertificateHealthSnapshot, RenewalJobSnapshot, RenewalRunResult
from northssl.renewal.engine import RenewalEngine
from northssl.renewal.scheduler import RenewalScheduler


@dataclass(slots=True)
class RenewalService:
    settings: NorthSSLSettings = field(default_factory=NorthSSLSettings)
    engine: RenewalEngine = field(init=False)
    scheduler: RenewalScheduler = field(init=False)

    def __post_init__(self) -> None:
        self.engine = RenewalEngine(self.settings)
        self.scheduler = RenewalScheduler(self.engine)

    def health(self) -> list[CertificateHealthSnapshot]:
        return self.engine.list_health()

    def run_cycle(self) -> list[RenewalRunResult]:
        return self.engine.run_scan_and_renew()

    def start(self) -> None:
        self.scheduler.start()

    def stop(self) -> None:
        self.scheduler.shutdown()

    def jobs(self) -> list[RenewalJobSnapshot]:
        return self.scheduler.snapshot()