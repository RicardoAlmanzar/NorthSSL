from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from northssl.config.settings import NorthSSLSettings
from northssl.core.models import (
    CertificateMetadata,
    NginxAutomationRequest,
    NginxAutomationResult,
    NginxConfigSnapshot,
    NginxDeploymentResult,
)
from northssl.nginx.deployment import NginxDeploymentManager
from northssl.nginx.parser import NginxConfigParser
from northssl.nginx.reloader import NginxReloadManager
from northssl.nginx.templates import NginxTemplateEngine

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class NginxIntegrationService:
    settings: NorthSSLSettings = field(default_factory=NorthSSLSettings)
    certificate_engine: object = field(init=False)
    parser: NginxConfigParser = field(init=False)
    templates: NginxTemplateEngine = field(default_factory=NginxTemplateEngine)
    reloader: NginxReloadManager = field(init=False)
    deployment: NginxDeploymentManager = field(init=False)

    def __post_init__(self) -> None:
        from northssl.core.services.certificate_engine import CertificateEngine

        self.certificate_engine = CertificateEngine(self.settings)
        self.parser = NginxConfigParser(self.settings)
        self.reloader = NginxReloadManager(self.settings)
        self.deployment = NginxDeploymentManager(self.settings, self.reloader)

    def discover(self) -> NginxConfigSnapshot:
        if not self._is_linux():
            return NginxConfigSnapshot(
                main_config_path=str(self.settings.nginx_main_config_path),
                site_paths=[],
                server_blocks=[],
                duplicate_domains=[],
                ssl_domains=[],
                conflicts=[],
                valid=False,
            )
        return self.parser.discover()

    def automate(self, request: NginxAutomationRequest) -> NginxAutomationResult:
        certificate = self.certificate_engine.issue(
            domain=request.domain,
            provider_name=request.provider,
            email=request.email,
            validation_method=request.validation_method,
            webroot_path=request.document_root,
        )
        deployment = self.deploy_certificate(
            certificate=certificate,
            document_root=request.document_root,
            upstream_host=request.upstream_host,
            upstream_port=request.upstream_port,
            redirect_http=request.redirect_http,
        )

        success = deployment.success
        message = deployment.message if success else f"Certificate issued but nginx deployment failed: {deployment.message}"
        return NginxAutomationResult(
            success=success,
            message=message,
            certificate=certificate,
            deployment=deployment,
            config=self.discover(),
        )

    def deploy_certificate(
        self,
        *,
        certificate: CertificateMetadata,
        document_root: str | None = None,
        upstream_host: str | None = None,
        upstream_port: int | None = None,
        redirect_http: bool = True,
    ) -> NginxDeploymentResult:
        server_names = [certificate.domain]
        if self._is_linux() is False:
            return NginxDeploymentResult(
                success=False,
                domain=certificate.domain,
                config_path="",
                message="Nginx automation is only supported on Linux",
            )

        config = self.templates.render_https_site(
            server_names=server_names,
            certificate_path=certificate.certificate_path,
            certificate_key_path=certificate.private_key_path,
            document_root=document_root,
            proxy_pass_upstream=f"{upstream_host}:{upstream_port}" if upstream_host and upstream_port else None,
            enable_redirect=redirect_http,
        )
        return self.deployment.deploy(domain=certificate.domain, content=config)

    def validate_existing(self) -> NginxDeploymentResult:
        result = self.reloader.validate()
        return NginxDeploymentResult(
            success=result.success,
            domain="",
            config_path=str(self.settings.nginx_main_config_path),
            message=result.message,
            stdout=result.stdout,
            stderr=result.stderr,
        )

    def _is_linux(self) -> bool:
        return Path("/etc/nginx").exists()
