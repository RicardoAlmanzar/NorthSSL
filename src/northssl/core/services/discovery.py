from __future__ import annotations

import logging
from dataclasses import dataclass, field
from shutil import which

from northssl.core.models import (
    CertbotSnapshot,
    DiagnosticsReport,
    PortSnapshot,
    ToolAvailability,
    WebServerSnapshot,
)
from northssl.core.services.port_scanner import SystemPortScanner
from northssl.platforms.detection import SystemPlatformDetector
from northssl.platforms.privileges import SystemPrivilegeDetector
from northssl.providers.certbot import CertbotProvider
from northssl.webservers.apache import ApacheAdapter
from northssl.webservers.iis import IISAdapter
from northssl.webservers.nginx import NginxAdapter

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SystemDiscoveryService:
    platform_detector: SystemPlatformDetector = field(default_factory=SystemPlatformDetector)
    privilege_detector: SystemPrivilegeDetector = field(default_factory=SystemPrivilegeDetector)
    webserver_detectors: tuple[object, ...] = field(
        default_factory=lambda: (NginxAdapter(), ApacheAdapter(), IISAdapter())
    )
    certbot_provider: CertbotProvider = field(default_factory=CertbotProvider)
    port_scanner: SystemPortScanner = field(default_factory=SystemPortScanner)

    def collect(self) -> DiagnosticsReport:
        warnings: list[str] = []

        platform_snapshot = self.platform_detector.detect()
        privilege_snapshot = self.privilege_detector.detect()
        webservers = self._discover_webservers(warnings)
        certbot = self._discover_certbot(warnings)
        ports = self._scan_ports(warnings)

        webservers = self._attach_ports_to_webservers(webservers, ports)
        tools = self._build_tools(webservers, certbot)

        return DiagnosticsReport(
            platform=platform_snapshot,
            privilege=privilege_snapshot,
            webservers=webservers,
            certbot=certbot,
            ports=ports,
            tools=tools,
            warnings=warnings,
        )

    def _discover_webservers(self, warnings: list[str]) -> list[WebServerSnapshot]:
        discovered: list[WebServerSnapshot] = []
        for detector in self.webserver_detectors:
            detector_name = getattr(detector, "name", detector.__class__.__name__)
            try:
                discovered.append(detector.discover())
            except Exception as exc:  # pragma: no cover - defensive discovery guard
                message = f"{detector_name} discovery failed: {exc}"
                logger.exception(message)
                warnings.append(message)
                discovered.append(WebServerSnapshot(name=detector_name, installed=False, active=False))
        return discovered

    def _discover_certbot(self, warnings: list[str]) -> CertbotSnapshot:
        try:
            return self.certbot_provider.discover()
        except Exception as exc:  # pragma: no cover - defensive discovery guard
            message = f"certbot discovery failed: {exc}"
            logger.exception(message)
            warnings.append(message)
            return CertbotSnapshot(installed=False)

    def _scan_ports(self, warnings: list[str]) -> list[PortSnapshot]:
        try:
            return self.port_scanner.scan((80, 443))
        except Exception as exc:  # pragma: no cover - defensive discovery guard
            message = f"port scan failed: {exc}"
            logger.exception(message)
            warnings.append(message)
            return []

    def _attach_ports_to_webservers(
        self,
        webservers: list[WebServerSnapshot],
        ports: list[PortSnapshot],
    ) -> list[WebServerSnapshot]:
        for webserver in webservers:
            matched_ports = {
                port.port
                for port in ports
                if port.occupied
                and (
                    (webserver.process_id is not None and port.process_id == webserver.process_id)
                    or (
                        webserver.process_name is not None
                        and port.process_name is not None
                        and webserver.process_name.lower() in port.process_name.lower()
                    )
                    or (webserver.name == "iis" and port.port in (80, 443) and webserver.active)
                )
            }
            webserver.ports = sorted(matched_ports)
        return webservers

    def _build_tools(
        self,
        webservers: list[WebServerSnapshot],
        certbot: CertbotSnapshot,
    ) -> list[ToolAvailability]:
        tools: dict[str, ToolAvailability] = {}

        for webserver in webservers:
            if webserver.binary_path:
                tools[webserver.name] = ToolAvailability(
                    name=webserver.name,
                    available=webserver.installed,
                    path=webserver.binary_path,
                )

        if certbot.binary_path:
            tools["certbot"] = ToolAvailability(
                name="certbot",
                available=certbot.installed,
                path=certbot.binary_path,
            )
        else:
            certbot_path = which("certbot")
            tools["certbot"] = ToolAvailability(
                name="certbot",
                available=certbot.installed,
                path=certbot_path,
            )

        return list(tools.values())