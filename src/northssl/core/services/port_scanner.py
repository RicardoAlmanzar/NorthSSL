from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Sequence

import psutil

from northssl.core.models import PortSnapshot

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SystemPortScanner:
    default_ports: tuple[int, ...] = (80, 443)

    def scan(self, ports: Sequence[int] | None = None) -> list[PortSnapshot]:
        target_ports = tuple(dict.fromkeys(ports or self.default_ports))
        snapshots = {
            port: PortSnapshot(port=port, occupied=False)
            for port in target_ports
        }

        try:
            connections = psutil.net_connections(kind="inet")
        except Exception as exc:  # pragma: no cover - platform dependent
            logger.warning("Port discovery failed: %s", exc)
            return list(snapshots.values())

        for connection in connections:
            if connection.status != psutil.CONN_LISTEN or not connection.laddr:
                continue

            local_port = getattr(connection.laddr, "port", None)
            if local_port not in snapshots:
                continue

            process_name: str | None = None
            command_line: list[str] = []

            if connection.pid is not None:
                try:
                    process = psutil.Process(connection.pid)
                    process_name = process.name()
                    command_line = process.cmdline()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    process_name = None
                    command_line = []

            snapshots[local_port] = PortSnapshot(
                port=local_port,
                occupied=True,
                process_id=connection.pid,
                process_name=process_name,
                command_line=command_line,
            )

        return [snapshots[port] for port in target_ports]