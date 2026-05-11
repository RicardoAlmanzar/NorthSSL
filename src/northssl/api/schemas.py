from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LinuxDistributionInfoSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str | None = None
    distribution_id: str | None = None
    version_id: str | None = None
    codename: str | None = None
    pretty_name: str | None = None


class PlatformSnapshotSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    distribution: LinuxDistributionInfoSchema | None = None


class PrivilegeSnapshotSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    elevated: bool
    mechanism: str
    username: str | None = None
    uid: int | None = None
    gid: int | None = None


class ToolAvailabilitySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    available: bool
    path: str | None = None


class PortSnapshotSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    port: int
    protocol: str = "tcp"
    occupied: bool = False
    process_id: int | None = None
    process_name: str | None = None
    command_line: list[str] = Field(default_factory=list)


class WebServerSnapshotSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    installed: bool
    active: bool = False
    binary_path: str | None = None
    version: str | None = None
    service_name: str | None = None
    process_id: int | None = None
    process_name: str | None = None
    config_paths: list[str] = Field(default_factory=list)
    ports: list[int] = Field(default_factory=list)


class CertbotSnapshotSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    installed: bool
    binary_path: str | None = None
    version: str | None = None
    compatible: bool = False
    raw_output: str | None = None


class DiagnosticsReportSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    platform: PlatformSnapshotSchema
    privilege: PrivilegeSnapshotSchema
    webservers: list[WebServerSnapshotSchema] = Field(default_factory=list)
    certbot: CertbotSnapshotSchema | None = None
    ports: list[PortSnapshotSchema] = Field(default_factory=list)
    tools: list[ToolAvailabilitySchema] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CertificateMetadataSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    domain: str
    provider: str
    certificate_path: str
    private_key_path: str
    issued_at: datetime
    expires_at: datetime | None = None
    status: str
    validation_method: str
    chain_path: str | None = None
    issuer: str | None = None
    sans: list[str] = Field(default_factory=list)
    serial_number: str | None = None


class CertificateIssueRequest(BaseModel):
    domain: str
    provider: str = "certbot"
    email: str | None = None
    validation_method: str = "standalone"
    webroot_path: str | None = None


class CertificateIssueResponse(BaseModel):
    message: str
    certificate: CertificateMetadataSchema


class ManualDnsChallengeSessionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    domain: str
    provider: str
    validation_method: str
    record_name: str
    record_value: str
    started_at: datetime
    status: str
    ready_at: datetime | None = None
    challenge_file_path: str | None = None
    ready_file_path: str | None = None
    hook_script_path: str | None = None
    cleanup_script_path: str | None = None
    message: str | None = None


class ManualDnsChallengeStartRequest(BaseModel):
    domain: str
    provider: str = "certbot"
    email: str | None = None


class ManualDnsChallengeStartResponse(BaseModel):
    message: str
    session: ManualDnsChallengeSessionSchema


class ManualDnsChallengeCompleteRequest(BaseModel):
    session_id: str
    provider: str = "certbot"


class ManualDnsChallengeCompleteResponse(BaseModel):
    message: str
    certificate: CertificateMetadataSchema


class HealthResponse(BaseModel):
    status: str
    app: str
    environment: str
    version: str


class SystemStatusResponse(BaseModel):
    settings: dict[str, Any]
    diagnostics: DiagnosticsReportSchema


class LogsResponse(BaseModel):
    path: str
    exists: bool
    line_count: int
    truncated: bool
    lines: list[str]


class NginxServerBlockSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    file_path: str
    line_number: int
    server_names: list[str] = Field(default_factory=list)
    listens: list[str] = Field(default_factory=list)
    ssl_enabled: bool = False
    ssl_certificate: str | None = None
    ssl_certificate_key: str | None = None
    root: str | None = None
    redirect_to_https: bool = False
    proxy_pass: str | None = None
    raw: str = ""


class NginxConfigConflictSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kind: str
    message: str
    domain: str | None = None
    file_paths: list[str] = Field(default_factory=list)
    server_names: list[str] = Field(default_factory=list)


class NginxConfigSnapshotSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    main_config_path: str
    site_paths: list[str] = Field(default_factory=list)
    server_blocks: list[NginxServerBlockSchema] = Field(default_factory=list)
    duplicate_domains: list[str] = Field(default_factory=list)
    ssl_domains: list[str] = Field(default_factory=list)
    conflicts: list[NginxConfigConflictSchema] = Field(default_factory=list)
    valid: bool = True
    parsed_at: datetime | None = None


class NginxDeploymentResultSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    conflicts: list[NginxConfigConflictSchema] = Field(default_factory=list)


class NginxAutomationRequestSchema(BaseModel):
    domain: str
    email: str | None = None
    validation_method: str = "standalone"
    provider: str = "certbot"
    document_root: str = "/var/www/html"
    upstream_host: str = "127.0.0.1"
    upstream_port: int = 80
    redirect_http: bool = True


class NginxAutomationResponseSchema(BaseModel):
    success: bool
    message: str
    certificate: CertificateMetadataSchema | None = None
    deployment: NginxDeploymentResultSchema | None = None
    config: NginxConfigSnapshotSchema | None = None


class CertificateHealthSnapshotSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    domain: str
    certificate_path: str | None = None
    expires_at: datetime | None = None
    days_remaining: int | None = None
    issuer: str | None = None
    sans: list[str] = Field(default_factory=list)
    valid: bool = False
    renewal_due: bool = False
    https_reachable: bool | None = None
    tls_version: str | None = None
    tls_error: str | None = None
    checked_at: datetime | None = None


class RenewalRunResultSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    domain: str
    success: bool
    message: str
    attempted_at: datetime
    previous_expires_at: datetime | None = None
    new_expires_at: datetime | None = None
    retries_used: int = 0
    locked: bool = True


class RenewalJobSnapshotSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    enabled: bool
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None
    last_message: str | None = None


class RenewalStatusResponseSchema(BaseModel):
    enabled: bool
    policy: dict[str, Any]
    jobs: list[RenewalJobSnapshotSchema] = Field(default_factory=list)
    health: list[CertificateHealthSnapshotSchema] = Field(default_factory=list)


class RenewalRunResponseSchema(BaseModel):
    success: bool
    message: str
    results: list[RenewalRunResultSchema] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    detail: str
    code: str
