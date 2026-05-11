from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from shutil import which

import psutil

from northssl.config.settings import NorthSSLSettings
from northssl.core.models import WebServerSnapshot
from northssl.nginx.service import NginxIntegrationService
from northssl.utils.subprocess import run_command


def _find_process(candidates: tuple[str, ...]) -> tuple[int | None, str | None]:
    lowered_candidates = {candidate.lower() for candidate in candidates}
    for process in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            name = (process.info.get("name") or "").lower()
            cmdline = " ".join(process.info.get("cmdline") or []).lower()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

        if any(candidate in name or candidate in cmdline for candidate in lowered_candidates):
            return process.info.get("pid"), process.info.get("name")

    return None, None


def _extract_version(output: str) -> str | None:
    match = re.search(r"nginx/([0-9][\w.\-]*)", output)
    return match.group(1) if match else None


@dataclass(slots=True)
class NginxAdapter:
    executable: str = "nginx"
    settings: NorthSSLSettings = field(default_factory=NorthSSLSettings)

    @property
    def name(self) -> str:
        return "nginx"

    def is_available(self) -> bool:
        return os.name == "posix" and which(self.executable) is not None

    def discover(self) -> WebServerSnapshot:
        executable = which(self.executable)
        process_pid, process_name = _find_process(("nginx",))
        version = self._read_version(executable)

        return WebServerSnapshot(
            name=self.name,
            installed=executable is not None,
            active=process_pid is not None,
            binary_path=executable,
            version=version,
            service_name="nginx" if os.name != "nt" else None,
            process_id=process_pid,
            process_name=process_name,
            config_paths=self._config_paths(),
        )

    def reload(self) -> None:
        NginxIntegrationService(self.settings).reloader.reload()

    def _read_version(self, executable: str | None) -> str | None:
        if not executable:
            return None

        result = run_command([executable, "-v"])
        output = (result.stdout or "") + (result.stderr or "")
        return _extract_version(output)

    def _config_paths(self) -> list[str]:
        if os.name != "posix":
            return []

        return [
            str(self.settings.nginx_main_config_path),
            str(self.settings.nginx_sites_available_dir),
            str(self.settings.nginx_sites_enabled_dir),
        ]
