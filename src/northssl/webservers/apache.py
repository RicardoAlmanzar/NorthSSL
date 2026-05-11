from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from shutil import which

import psutil

from northssl.core.models import WebServerSnapshot
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
    match = re.search(r"Apache/([0-9][\w.\-]*)", output)
    return match.group(1) if match else None


@dataclass(slots=True)
class ApacheAdapter:
    executable_candidates: tuple[str, ...] = ("apache2", "httpd", "httpd.exe")

    @property
    def name(self) -> str:
        return "apache"

    def is_available(self) -> bool:
        return self._resolve_executable() is not None

    def discover(self) -> WebServerSnapshot:
        executable = self._resolve_executable()
        process_pid, process_name = _find_process(("apache2", "httpd", "apache"))
        version = self._read_version(executable)

        return WebServerSnapshot(
            name=self.name,
            installed=executable is not None,
            active=process_pid is not None,
            binary_path=executable,
            version=version,
            service_name="apache2" if os.name != "nt" else None,
            process_id=process_pid,
            process_name=process_name,
            config_paths=self._config_paths(),
        )

    def reload(self) -> None:
        raise NotImplementedError("Apache reload orchestration is not implemented yet.")

    def _resolve_executable(self) -> str | None:
        for candidate in self.executable_candidates:
            resolved = which(candidate)
            if resolved:
                return resolved
        return None

    def _read_version(self, executable: str | None) -> str | None:
        if not executable:
            return None

        result = run_command([executable, "-v"])
        output = (result.stdout or "") + (result.stderr or "")
        return _extract_version(output)

    def _config_paths(self) -> list[str]:
        if os.name == "nt":
            return [
                r"C:\Apache24\conf\httpd.conf",
                r"C:\xampp\apache\conf\httpd.conf",
                r"C:\Program Files\Apache Software Foundation\Apache2.4\conf\httpd.conf",
            ]

        return ["/etc/apache2/apache2.conf", "/etc/httpd/conf/httpd.conf"]