from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from northssl import __version__

class NorthSSLSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="NORTHSSL_",
        extra="ignore",
    )

    app_name: str = "NorthSSL"
    version: str = __version__
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    data_dir: Path = Field(default_factory=lambda: Path.home() / ".northssl")
    database_name: str = "northssl.db"
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    api_cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:1420",
            "http://127.0.0.1:1420",
            "tauri://localhost",
        ]
    )
    nginx_main_config_path: Path = Path("/etc/nginx/nginx.conf")
    nginx_sites_available_dir: Path = Path("/etc/nginx/sites-available")
    nginx_sites_enabled_dir: Path = Path("/etc/nginx/sites-enabled")
    nginx_backup_dir: Path = Field(default_factory=lambda: Path.home() / ".northssl" / "backups" / "nginx")
    renewal_enabled: bool = True
    renewal_check_interval_seconds: int = 300
    renewal_window_days: int = 30
    renewal_retry_count: int = 3
    renewal_retry_delay_seconds: int = 300
    renewal_cooldown_seconds: int = 3600
    renewal_lock_timeout_seconds: int = 900
    monitor_https_timeout_seconds: int = 10
    monitor_probe_port: int = 443
    monitor_tls_verify: bool = True
    renewal_audit_limit: int = 200
    acme_staging: bool = False
    acme_server_url: str | None = None
    acme_dns_cloudflare_credentials_path: Path | None = None
    acme_dns_cloudflare_propagation_seconds: int = 60
    acme_dns_manual_wait_seconds: int = 1800
    acme_dns_manual_poll_seconds: int = 1

    @property
    def database_path(self) -> Path:
        return self.data_dir / self.database_name

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database_path.as_posix()}"

    @property
    def log_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def log_file_path(self) -> Path:
        return self.log_dir / "northssl.log"
