from northssl.core.models import DiagnosticsReport
from northssl.core.services.discovery import SystemDiscoveryService


def collect_diagnostics() -> DiagnosticsReport:
    return SystemDiscoveryService().collect()
