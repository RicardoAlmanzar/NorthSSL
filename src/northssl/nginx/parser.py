from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from northssl.config.settings import NorthSSLSettings
from northssl.core.models import NginxConfigConflict, NginxConfigSnapshot, NginxServerBlockSnapshot

INCLUDE_PATTERN = re.compile(r"^\s*include\s+([^;]+);", re.MULTILINE)
SERVER_BLOCK_PATTERN = re.compile(r"\bserver\s*\{")


@dataclass(slots=True)
class ParsedNginxFile:
    path: Path
    content: str


class NginxConfigParser:
    def __init__(self, settings: NorthSSLSettings) -> None:
        self._settings = settings

    def discover(self) -> NginxConfigSnapshot:
        site_paths = self._discover_config_files()
        server_blocks: list[NginxServerBlockSnapshot] = []
        for path in site_paths:
            try:
                server_blocks.extend(self._parse_file(path))
            except FileNotFoundError:
                continue

        duplicate_domains: list[str] = []
        ssl_domains: list[str] = []
        conflicts: list[NginxConfigConflict] = []
        domain_index: dict[str, list[NginxServerBlockSnapshot]] = defaultdict(list)

        for block in server_blocks:
            if block.ssl_enabled:
                ssl_domains.extend(block.server_names)
            for server_name in block.server_names:
                domain_index[server_name].append(block)

        for domain, blocks in domain_index.items():
            if len(blocks) > 1:
                duplicate_domains.append(domain)
                conflicts.append(
                    NginxConfigConflict(
                        kind="duplicate_server_name",
                        domain=domain,
                        message=f"Domain {domain} appears in multiple nginx server blocks.",
                        file_paths=sorted({block.file_path for block in blocks}),
                        server_names=sorted({name for block in blocks for name in block.server_names}),
                    )
                )

        return NginxConfigSnapshot(
            main_config_path=str(self._settings.nginx_main_config_path),
            site_paths=[str(path) for path in site_paths],
            server_blocks=server_blocks,
            duplicate_domains=sorted(set(duplicate_domains)),
            ssl_domains=sorted(set(ssl_domains)),
            conflicts=conflicts,
            valid=True,
            parsed_at=datetime.now(timezone.utc),
        )

    def _discover_config_files(self) -> list[Path]:
        discovered: list[Path] = []
        seen: set[Path] = set()

        def visit(path: Path) -> None:
            resolved = path.resolve() if path.exists() else path
            if resolved in seen or not path.exists() or not path.is_file():
                return
            seen.add(resolved)
            discovered.append(resolved)
            content = path.read_text(encoding="utf-8", errors="replace")
            for include_path in self._extract_includes(content, path.parent):
                visit(include_path)

        visit(self._settings.nginx_main_config_path)
        for candidate in (
            self._settings.nginx_sites_available_dir,
            self._settings.nginx_sites_enabled_dir,
        ):
            if candidate.exists() and candidate.is_dir():
                for config_path in sorted(candidate.glob("*.conf")):
                    visit(config_path)

        return sorted(discovered)

    def _extract_includes(self, content: str, base_dir: Path) -> list[Path]:
        include_paths: list[Path] = []
        for match in INCLUDE_PATTERN.finditer(content):
            raw_path = match.group(1).strip().strip('"')
            candidate = Path(raw_path)
            if not candidate.is_absolute():
                candidate = base_dir / candidate
            if any(char in raw_path for char in "*?[]"):
                include_paths.extend(sorted(candidate.parent.glob(candidate.name)))
            elif candidate.exists():
                include_paths.append(candidate)
        return include_paths

    def _parse_file(self, path: Path) -> list[NginxServerBlockSnapshot]:
        text = path.read_text(encoding="utf-8", errors="replace")
        cleaned = self._strip_comments(text)
        blocks: list[NginxServerBlockSnapshot] = []

        search_index = 0
        while True:
            match = SERVER_BLOCK_PATTERN.search(cleaned, search_index)
            if not match:
                break
            start_index = match.end() - 1
            end_index = self._find_matching_brace(cleaned, start_index)
            block_text = cleaned[match.start(): end_index + 1]
            line_number = cleaned.count("\n", 0, match.start()) + 1
            blocks.append(self._parse_server_block(path, line_number, block_text))
            search_index = end_index + 1

        return blocks

    def _parse_server_block(self, path: Path, line_number: int, block_text: str) -> NginxServerBlockSnapshot:
        server_names = self._extract_list_directive(block_text, "server_name")
        listens = self._extract_raw_directives(block_text, "listen")
        certificate = self._extract_single_directive(block_text, "ssl_certificate")
        certificate_key = self._extract_single_directive(block_text, "ssl_certificate_key")
        root = self._extract_single_directive(block_text, "root")
        redirect_to_https = "return 301 https://" in block_text or "rewrite ^ https://" in block_text
        proxy_pass = self._extract_proxy_pass(block_text)

        ssl_enabled = any("ssl" in listen for listen in listens) or certificate is not None or certificate_key is not None

        return NginxServerBlockSnapshot(
            file_path=str(path),
            line_number=line_number,
            server_names=server_names,
            listens=listens,
            ssl_enabled=ssl_enabled,
            ssl_certificate=certificate,
            ssl_certificate_key=certificate_key,
            root=root,
            redirect_to_https=redirect_to_https,
            proxy_pass=proxy_pass,
            raw=block_text,
        )

    def _strip_comments(self, content: str) -> str:
        return "\n".join(line.split("#", 1)[0] for line in content.splitlines())

    def _find_matching_brace(self, content: str, start_index: int) -> int:
        depth = 0
        for index in range(start_index, len(content)):
            if content[index] == "{":
                depth += 1
            elif content[index] == "}":
                depth -= 1
                if depth == 0:
                    return index
        raise ValueError("Unbalanced nginx braces")

    def _extract_list_directive(self, content: str, directive: str) -> list[str]:
        match = re.search(rf"\b{directive}\s+([^;]+);", content)
        if not match:
            return []
        values = [value.strip() for value in match.group(1).split()]
        return [value for value in values if value and value != "_"]

    def _extract_raw_directives(self, content: str, directive: str) -> list[str]:
        return [match.group(1).strip() for match in re.finditer(rf"\b{directive}\s+([^;]+);", content)]

    def _extract_single_directive(self, content: str, directive: str) -> str | None:
        values = self._extract_raw_directives(content, directive)
        return values[0] if values else None

    def _extract_proxy_pass(self, content: str) -> str | None:
        match = re.search(r"\bproxy_pass\s+https?://([^;]+);", content)
        return match.group(1).strip() if match else None
