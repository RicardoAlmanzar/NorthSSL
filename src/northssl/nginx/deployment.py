from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from northssl.config.settings import NorthSSLSettings
from northssl.core.models import NginxCommandResult, NginxDeploymentResult
from northssl.nginx.reloader import NginxReloadManager


@dataclass(slots=True)
class NginxDeploymentManager:
    settings: NorthSSLSettings
    reloader: NginxReloadManager

    def deploy(self, *, domain: str, content: str) -> NginxDeploymentResult:
        self._ensure_directories()
        target_path = self._site_available_path(domain)
        backup_path = self._backup_existing(target_path)
        enabled_path = self._site_enabled_path(domain)
        created_symlink = False

        try:
            self._write_atomically(target_path, content)
            self._ensure_symlink(target_path, enabled_path)
            created_symlink = True

            validation = self.reloader.validate()
            if not validation.success:
                raise RuntimeError(validation.stderr or validation.message)

            reload_result = self.reloader.reload()
            if not reload_result.success:
                raise RuntimeError(reload_result.stderr or reload_result.message)

            return NginxDeploymentResult(
                success=True,
                domain=domain,
                config_path=str(target_path),
                backup_path=str(backup_path) if backup_path else None,
                validated=True,
                reloaded=True,
                rolled_back=False,
                message=f"Nginx configuration deployed for {domain}",
                stdout=reload_result.stdout,
                stderr=reload_result.stderr,
            )
        except Exception as exc:
            self._rollback(target_path, backup_path, enabled_path, created_symlink)
            return NginxDeploymentResult(
                success=False,
                domain=domain,
                config_path=str(target_path),
                backup_path=str(backup_path) if backup_path else None,
                validated=False,
                reloaded=False,
                rolled_back=True,
                message=str(exc),
            )

    def _ensure_directories(self) -> None:
        self.settings.nginx_sites_available_dir.mkdir(parents=True, exist_ok=True)
        self.settings.nginx_sites_enabled_dir.mkdir(parents=True, exist_ok=True)
        self.settings.nginx_backup_dir.mkdir(parents=True, exist_ok=True)

    def _site_available_path(self, domain: str) -> Path:
        safe_name = domain.replace("*", "wildcard").replace("/", "_")
        return self.settings.nginx_sites_available_dir / f"northssl-{safe_name}.conf"

    def _site_enabled_path(self, domain: str) -> Path:
        return self.settings.nginx_sites_enabled_dir / self._site_available_path(domain).name

    def _backup_existing(self, target_path: Path) -> Path | None:
        if not target_path.exists():
            return None

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        backup_path = self.settings.nginx_backup_dir / f"{target_path.name}.{timestamp}.bak"
        shutil.copy2(target_path, backup_path)
        return backup_path

    def _write_atomically(self, target_path: Path, content: str) -> None:
        temp_path = target_path.with_suffix(target_path.suffix + ".tmp")
        temp_path.write_text(content, encoding="utf-8")
        temp_path.replace(target_path)

    def _ensure_symlink(self, target_path: Path, enabled_path: Path) -> None:
        if enabled_path.exists() or enabled_path.is_symlink():
            enabled_path.unlink()
        enabled_path.symlink_to(target_path)

    def _rollback(self, target_path: Path, backup_path: Path | None, enabled_path: Path, created_symlink: bool) -> None:
        if created_symlink and enabled_path.exists():
            enabled_path.unlink()

        if backup_path and backup_path.exists():
            shutil.copy2(backup_path, target_path)
        elif target_path.exists():
            target_path.unlink()
