from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class LinuxDistributionInfo:
    name: str | None = None
    distribution_id: str | None = None
    version_id: str | None = None
    codename: str | None = None
    pretty_name: str | None = None

@dataclass(slots=True)
class PlatformSnapshot:
    system: str
    release: str
    version: str
    machine: str
    python_version: str
    executable: str
    hostname: str | None = None
    fqdn: str | None = None
    username: str | None = None
    current_directory: str | None = None
    distribution: LinuxDistributionInfo | None = None


@dataclass(slots=True)
class PrivilegeSnapshot:
    elevated: bool
    mechanism: str
    username: str | None = None
    uid: int | None = None
    gid: int | None = None

@dataclass(slots=True)
class ToolAvailability:
    name: str
    available: bool
    path: str | None = None


@dataclass(slots=True)
class PortSnapshot:
    port: int
    protocol: str = "tcp"
    occupied: bool = False
    process_id: int | None = None
    process_name: str | None = None
    command_line: list[str] = field(default_factory=list)


@dataclass(slots=True)
class WebServerSnapshot:
    name: str
    installed: bool
    active: bool = False
    binary_path: str | None = None
    version: str | None = None
    service_name: str | None = None
    process_id: int | None = None
    process_name: str | None = None
    config_paths: list[str] = field(default_factory=list)
    ports: list[int] = field(default_factory=list)


@dataclass(slots=True)
class NginxServerBlockSnapshot:
    file_path: str
    line_number: int
    server_names: list[str] = field(default_factory=list)
    listens: list[str] = field(default_factory=list)
    ssl_enabled: bool = False
    ssl_certificate: str | None = None
    ssl_certificate_key: str | None = None
    root: str | None = None
    redirect_to_https: bool = False
    proxy_pass: str | None = None
    raw: str = ""


@dataclass(slots=True)
class NginxConfigConflict:
    kind: str
    message: str
    domain: str | None = None
    file_paths: list[str] = field(default_factory=list)
    server_names: list[str] = field(default_factory=list)


@dataclass(slots=True)
class NginxConfigSnapshot:
    main_config_path: str
    site_paths: list[str] = field(default_factory=list)
    server_blocks: list[NginxServerBlockSnapshot] = field(default_factory=list)
    duplicate_domains: list[str] = field(default_factory=list)
    ssl_domains: list[str] = field(default_factory=list)
    conflicts: list[NginxConfigConflict] = field(default_factory=list)
    valid: bool = True
    parsed_at: datetime | None = None


@dataclass(slots=True)
class NginxCommandResult:
    success: bool
    command: list[str]
    message: str
    stdout: str | None = None
    stderr: str | None = None
    exit_code: int | None = None


@dataclass(slots=True)
class NginxDeploymentResult:
    success: bool
    domain: str
    config_path: str
    backup_path: str | None = None
    validated: bool = False
    reloaded: bool = False
    rolled_back: bool = False
    message: str = ""
    stdout: str | None = None
    stderr: str | None = None
    conflicts: list[NginxConfigConflict] = field(default_factory=list)


@dataclass(slots=True)
class NginxAutomationRequest:
    domain: str
    email: str | None = None
    validation_method: str = "standalone"
    provider: str = "certbot"
    document_root: str = "/var/www/html"
    upstream_host: str = "127.0.0.1"
    upstream_port: int = 80
    redirect_http: bool = True


@dataclass(slots=True)
class NginxAutomationResult:
    success: bool
    message: str
    certificate: CertificateMetadata | None = None
    deployment: NginxDeploymentResult | None = None
    config: NginxConfigSnapshot | None = None


@dataclass(slots=True)
class CertbotSnapshot:
    installed: bool
    binary_path: str | None = None
    version: str | None = None
    compatible: bool = False
    raw_output: str | None = None

@dataclass(slots=True)
class DiagnosticsReport:
    platform: PlatformSnapshot
    privilege: PrivilegeSnapshot
    webservers: list[WebServerSnapshot] = field(default_factory=list)
    certbot: CertbotSnapshot | None = None
    ports: list[PortSnapshot] = field(default_factory=list)
    tools: list[ToolAvailability] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CertificateOperationResult:
    success: bool
    message: str
    provider: str
    domain: str | None = None
    validation_method: str | None = None
    certificate_path: str | None = None
    private_key_path: str | None = None
    chain_path: str | None = None
    raw_output: str | None = None
    exit_code: int | None = None


@dataclass(slots=True)
class ManualDnsChallengeSession:
    session_id: str
    domain: str
    provider: str
    validation_method: str
    record_name: str
    record_value: str
    started_at: datetime
    status: str = "waiting"
    ready_at: datetime | None = None
    challenge_file_path: str | None = None
    ready_file_path: str | None = None
    hook_script_path: str | None = None
    cleanup_script_path: str | None = None
    message: str | None = None
    raw_output: str | None = None
    certificate_path: str | None = None
    private_key_path: str | None = None
    chain_path: str | None = None
    exit_code: int | None = None


@dataclass(slots=True)
class CertificateMetadata:
    domain: str
    provider: str
    certificate_path: str
    private_key_path: str
    issued_at: datetime
    expires_at: datetime | None
    status: str
    validation_method: str
    chain_path: str | None = None
    issuer: str | None = None
    sans: list[str] = field(default_factory=list)
    serial_number: str | None = None


@dataclass(slots=True)
class CertificateInspection:
    certificate_path: str
    subject: str | None
    issuer: str | None
    sans: list[str] = field(default_factory=list)
    serial_number: str | None = None
    not_before: datetime | None = None
    not_after: datetime | None = None
    expired: bool = False
    valid: bool = False
    days_remaining: int | None = None


@dataclass(slots=True)
class RenewalPolicy:
    enabled: bool = True
    renew_before_days: int = 30
    max_retries: int = 3
    retry_delay_seconds: int = 300
    cooldown_seconds: int = 3600
    check_interval_seconds: int = 300
    lock_timeout_seconds: int = 900
    https_timeout_seconds: int = 10
    probe_port: int = 443
    verify_tls: bool = True


@dataclass(slots=True)
class CertificateHealthSnapshot:
    domain: str
    certificate_path: str | None
    expires_at: datetime | None
    days_remaining: int | None
    issuer: str | None
    sans: list[str] = field(default_factory=list)
    valid: bool = False
    renewal_due: bool = False
    https_reachable: bool | None = None
    tls_version: str | None = None
    tls_error: str | None = None
    checked_at: datetime | None = None


@dataclass(slots=True)
class RenewalRunResult:
    domain: str
    success: bool
    message: str
    attempted_at: datetime
    previous_expires_at: datetime | None = None
    new_expires_at: datetime | None = None
    retries_used: int = 0
    locked: bool = True


@dataclass(slots=True)
class RenewalJobSnapshot:
    name: str
    enabled: bool
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None
    last_message: str | None = None


@dataclass(slots=True)
class AuditEvent:
    event_type: str
    domain: str | None
    severity: str
    message: str
    created_at: datetime
    details: dict[str, str] = field(default_factory=dict)
