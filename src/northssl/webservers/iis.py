from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from shutil import which

import psutil

from northssl.core.models import WebServerSnapshot

def _is_service_running(service_name: str) -> bool:
    try:
        service = psutil.win_service_get(service_name)
        return service.status().lower() == "running"
    except Exception:
        return False


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


@dataclass(slots=True)
class IISAdapter:
    service_name: str = "W3SVC"

    @property
    def name(self) -> str:
        return "iis"

    def is_available(self) -> bool:
        return self._config_path().exists() or which("appcmd.exe") is not None or _is_service_running(self.service_name)

    def discover(self) -> WebServerSnapshot:
        config_path = self._config_path()
        process_pid, process_name = _find_process(("w3wp", "w3svc", "inetinfo", "iisexpress"))
        active = _is_service_running(self.service_name) or process_pid is not None

        return WebServerSnapshot(
            name=self.name,
            installed=config_path.exists() or which("appcmd.exe") is not None or active,
            active=active,
            binary_path=which("appcmd.exe"),
            version=None,
            service_name=self.service_name,
            process_id=process_pid,
            process_name=process_name,
            config_paths=[str(config_path)],
        )

    def reload(self) -> None:
        raise NotImplementedError("IIS reload orchestration is not implemented yet.")

    def _config_path(self) -> Path:
        windir = os.environ.get("WINDIR", r"C:\\Windows")
        return Path(windir) / "System32" / "inetsrv" / "config" / "applicationHost.config"