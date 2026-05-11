from __future__ import annotations

from pathlib import Path

from northssl.config.settings import NorthSSLSettings
from northssl.core.models import NginxCommandResult
from northssl.utils.subprocess import run_command


class NginxReloadManager:
    def __init__(self, settings: NorthSSLSettings) -> None:
        self._settings = settings

    def validate(self) -> NginxCommandResult:
        command = ["nginx", "-t", "-c", str(self._settings.nginx_main_config_path)]
        result = run_command(command)
        success = result.returncode == 0
        return NginxCommandResult(
            success=success,
            command=command,
            message="nginx config validated" if success else "nginx config validation failed",
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.returncode,
        )

    def reload(self) -> NginxCommandResult:
        command = ["systemctl", "reload", "nginx"]
        result = run_command(command)
        if result.returncode != 0:
            fallback_command = ["nginx", "-s", "reload"]
            result = run_command(fallback_command)
            command = fallback_command

        success = result.returncode == 0
        return NginxCommandResult(
            success=success,
            command=command,
            message="nginx reloaded" if success else "nginx reload failed",
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.returncode,
        )
