from __future__ import annotations

import getpass
import logging
import platform as platform_module
import socket
import sys
from dataclasses import dataclass
from pathlib import Path

from northssl.core.models import LinuxDistributionInfo, PlatformSnapshot

logger = logging.getLogger(__name__)


def _parse_os_release() -> dict[str, str]:
    try:
        if hasattr(platform_module, "freedesktop_os_release"):
            return platform_module.freedesktop_os_release()
    except OSError as exc:
        logger.debug("Unable to read freedesktop os-release: %s", exc)

    os_release_path = Path("/etc/os-release")
    if not os_release_path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in os_release_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value.strip().strip('"')
    return values


def _detect_linux_distribution() -> LinuxDistributionInfo | None:
    if platform_module.system().lower() != "linux":
        return None

    os_release = _parse_os_release()
    if not os_release:
        return LinuxDistributionInfo(name="Linux")

    return LinuxDistributionInfo(
        name=os_release.get("NAME"),
        distribution_id=os_release.get("ID"),
        version_id=os_release.get("VERSION_ID"),
        codename=os_release.get("VERSION_CODENAME"),
        pretty_name=os_release.get("PRETTY_NAME"),
    )


@dataclass(slots=True)
class SystemPlatformDetector:
    def detect(self) -> PlatformSnapshot:
        return PlatformSnapshot(
            system=platform_module.system() or "Unknown",
            release=platform_module.release(),
            version=platform_module.version(),
            machine=platform_module.machine(),
            python_version=platform_module.python_version(),
            executable=sys.executable,
            hostname=socket.gethostname(),
            fqdn=socket.getfqdn(),
            username=getpass.getuser(),
            current_directory=str(Path.cwd()),
            distribution=_detect_linux_distribution(),
        )


def detect_platform_snapshot() -> PlatformSnapshot:
    return SystemPlatformDetector().detect()
