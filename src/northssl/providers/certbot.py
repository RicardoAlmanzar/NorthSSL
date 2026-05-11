from __future__ import annotations

import json
import logging
import re
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from shutil import which
from subprocess import PIPE, Popen
from threading import Lock
from time import sleep
from uuid import uuid4

from northssl.config.settings import NorthSSLSettings
from northssl.core.models import CertbotSnapshot, CertificateOperationResult, ManualDnsChallengeSession
from northssl.utils.subprocess import run_command

logger = logging.getLogger(__name__)


def _extract_version(output: str) -> str | None:
    match = re.search(r"([0-9]+(?:\.[0-9]+)+)", output)
    return match.group(1) if match else None

@dataclass(slots=True)
class CertbotProvider:
    executable: str = "certbot"
    settings: NorthSSLSettings | None = None
    _manual_sessions: dict[str, tuple[Popen[str], ManualDnsChallengeSession]] = field(default_factory=dict, init=False, repr=False)
    _manual_sessions_lock: Lock = field(default_factory=Lock, init=False, repr=False)

    @property
    def name(self) -> str:
        return "certbot"

    def is_available(self) -> bool:
        return which(self.executable) is not None

    def discover(self) -> CertbotSnapshot:
        binary_path = which(self.executable)
        if not binary_path:
            return CertbotSnapshot(installed=False)

        result = run_command([binary_path, "--version"])
        output = (result.stdout or "").strip() or (result.stderr or "").strip()
        version = _extract_version(output)

        return CertbotSnapshot(
            installed=True,
            binary_path=binary_path,
            version=version,
            compatible=self._is_compatible(version),
            raw_output=output or None,
        )

    def issue_certificate(
        self,
        domain: str,
        email: str | None = None,
        validation_method: str = "standalone",
        webroot_path: str | None = None,
    ) -> CertificateOperationResult:
        binary_path = which(self.executable)
        if not binary_path:
            return CertificateOperationResult(
                success=False,
                message="certbot is not installed",
                provider=self.name,
                domain=domain,
                validation_method=validation_method,
            )

        arguments = [
            binary_path,
            "certonly",
            "--non-interactive",
            "--agree-tos",
            "--cert-name",
            domain,
            "-d",
            domain,
        ]

        normalized_method = validation_method.strip().lower()
        authenticator = normalized_method

        if self.settings is not None:
            if self.settings.acme_server_url:
                arguments.extend(["--server", self.settings.acme_server_url])
            elif self.settings.acme_staging:
                arguments.append("--test-cert")

        if email:
            arguments.extend(["--email", email])
        else:
            arguments.append("--register-unsafely-without-email")

        if normalized_method == "standalone":
            arguments.extend(["--preferred-challenges", "http"])
            arguments.extend(["--http-01-port", "80"])
        elif normalized_method == "webroot":
            arguments.extend(["--preferred-challenges", "http"])
            webroot = (webroot_path or "/var/www/html").strip()
            arguments.extend(["--webroot", "--webroot-path", webroot])
        elif normalized_method == "dns-01":
            arguments.extend(["--preferred-challenges", "dns"])
            authenticator = "dns-cloudflare"
            credentials_path = self._resolve_cloudflare_credentials_path()
            if credentials_path is None:
                return CertificateOperationResult(
                    success=False,
                    message=(
                        "DNS-01 with Cloudflare requires NORTHSSL_ACME_CLOUDFLARE_CREDENTIALS_PATH "
                        "pointing to a certbot credentials file"
                    ),
                    provider=self.name,
                    domain=domain,
                    validation_method=validation_method,
                )

            propagation_seconds = 60
            if self.settings is not None:
                propagation_seconds = self.settings.acme_dns_cloudflare_propagation_seconds

            arguments.extend([
                "--dns-cloudflare",
                "--dns-cloudflare-credentials",
                str(credentials_path),
                "--dns-cloudflare-propagation-seconds",
                str(propagation_seconds),
            ])
        elif normalized_method in {"dns-manual", "dns-01-manual"}:
            challenge = self.start_manual_dns_challenge(domain=domain, email=email)
            return CertificateOperationResult(
                success=True,
                message=challenge.message or "Manual DNS-01 challenge started",
                provider=self.name,
                domain=domain,
                validation_method=validation_method,
                raw_output=challenge.raw_output,
                exit_code=0,
            )

        arguments.extend(["--authenticator", authenticator])

        result = run_command(arguments, timeout=900)
        output = (result.stdout or "") + (result.stderr or "")
        logger.debug("certbot issue output for %s: %s", domain, output.strip())

        return CertificateOperationResult(
            success=result.returncode == 0,
            message=output.strip() or ("certificate issued" if result.returncode == 0 else "certificate issuance failed"),
            provider=self.name,
            domain=domain,
            validation_method=validation_method,
            certificate_path=self._extract_path(output, r"Certificate is saved at:\s*(.+)"),
            private_key_path=self._extract_path(output, r"Key is saved at:\s*(.+)"),
            chain_path=self._extract_path(output, r"Chain is saved at:\s*(.+)"),
            raw_output=output or None,
            exit_code=result.returncode,
        )

    def renew_certificate(self, domain: str) -> CertificateOperationResult:
        binary_path = which(self.executable)
        if not binary_path:
            return CertificateOperationResult(success=False, message="certbot is not installed", provider=self.name, domain=domain)

        result = run_command([binary_path, "renew", "--cert-name", domain, "--non-interactive"], timeout=900)
        output = (result.stdout or "") + (result.stderr or "")

        return CertificateOperationResult(
            success=result.returncode == 0,
            message=output.strip() or ("certificate renewed" if result.returncode == 0 else "certificate renewal failed"),
            provider=self.name,
            domain=domain,
            raw_output=output or None,
            exit_code=result.returncode,
        )

    def revoke_certificate(self, certificate_path: str, reason: str = "keycompromise") -> CertificateOperationResult:
        binary_path = which(self.executable)
        if not binary_path:
            return CertificateOperationResult(success=False, message="certbot is not installed", provider=self.name)

        result = run_command(
            [binary_path, "revoke", "--cert-path", certificate_path, "--reason", reason, "--non-interactive", "--delete-after-revoke"],
            timeout=900,
        )
        output = (result.stdout or "") + (result.stderr or "")

        return CertificateOperationResult(
            success=result.returncode == 0,
            message=output.strip() or ("certificate revoked" if result.returncode == 0 else "certificate revocation failed"),
            provider=self.name,
            certificate_path=certificate_path,
            raw_output=output or None,
            exit_code=result.returncode,
        )

    def _is_compatible(self, version: str | None) -> bool:
        if not version:
            return False

        try:
            major = int(version.split(".", 1)[0])
        except ValueError:
            return False

        return major >= 1

    def _extract_path(self, output: str, pattern: str) -> str | None:
        match = re.search(pattern, output, re.IGNORECASE)
        return match.group(1).strip() if match else None

    def _resolve_cloudflare_credentials_path(self) -> Path | None:
        if self.settings is None or self.settings.acme_dns_cloudflare_credentials_path is None:
            return None

        credentials_path = Path(self.settings.acme_dns_cloudflare_credentials_path)
        if not credentials_path.exists():
            return None

        return credentials_path

    def start_manual_dns_challenge(self, domain: str, email: str | None = None) -> ManualDnsChallengeSession:
        binary_path = which(self.executable)
        if not binary_path:
            raise RuntimeError("certbot is not installed")

        if self._manual_sessions is None:
            self._manual_sessions = {}

        session_id = uuid4().hex
        session = self._build_manual_dns_session(session_id, domain)
        self._ensure_manual_dns_hooks()

        data_dir = self.settings.data_dir if self.settings is not None else Path.home() / ".northssl"
        letsencrypt_config_dir = data_dir / "letsencrypt" / "config"
        letsencrypt_work_dir = data_dir / "letsencrypt" / "work"
        letsencrypt_logs_dir = data_dir / "letsencrypt" / "logs"
        for d in (letsencrypt_config_dir, letsencrypt_work_dir, letsencrypt_logs_dir):
            d.mkdir(parents=True, exist_ok=True)

        command = [
            binary_path,
            "certonly",
            "--manual",
            "--preferred-challenges",
            "dns",
            "--non-interactive",
            "--agree-tos",
            "--config-dir",
            str(letsencrypt_config_dir),
            "--work-dir",
            str(letsencrypt_work_dir),
            "--logs-dir",
            str(letsencrypt_logs_dir),
            "--cert-name",
            domain,
            "-d",
            domain,
            "--manual-auth-hook",
            str(session.hook_script_path),
            "--manual-cleanup-hook",
            str(session.cleanup_script_path),
        ]

        if self.settings is not None:
            if self.settings.acme_server_url:
                command.extend(["--server", self.settings.acme_server_url])
            elif self.settings.acme_staging:
                command.append("--test-cert")

        if email:
            command.extend(["--email", email])
        else:
            command.append("--register-unsafely-without-email")

        process_env = {
            **self._manual_dns_environment(session),
        }

        process = Popen(
            command,
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
            cwd=str(self.settings.data_dir if self.settings is not None else Path.home()),
            env={**process_env, **self._base_environment()},
            text=True,
        )

        session.status = "running"
        session.message = "Waiting for the DNS TXT record to be created"
        session.raw_output = f"Launched certbot process {process.pid}"

        with self._manual_sessions_lock:
            self._manual_sessions[session_id] = (process, session)

        self._wait_for_manual_dns_challenge_file(session)
        return session

    def complete_manual_dns_challenge(self, session_id: str) -> CertificateOperationResult:
        if self._manual_sessions is None:
            return CertificateOperationResult(success=False, message="No manual DNS sessions are active", provider=self.name)

        with self._manual_sessions_lock:
            entry = self._manual_sessions.get(session_id)

        if entry is None:
            return CertificateOperationResult(success=False, message=f"Unknown DNS session: {session_id}", provider=self.name)

        process, session = entry
        if session.ready_file_path is None:
            return CertificateOperationResult(success=False, message="DNS session is not ready", provider=self.name)

        Path(session.ready_file_path).write_text("ready", encoding="utf-8")

        try:
            stdout, stderr = process.communicate(timeout=900)
        except Exception as exc:
            process.kill()
            return CertificateOperationResult(success=False, message=f"Manual DNS-01 completion failed: {exc}", provider=self.name, domain=session.domain, validation_method=session.validation_method)

        output = (stdout or "") + (stderr or "")
        success = process.returncode == 0
        return CertificateOperationResult(
            success=success,
            message=output.strip() or ("certificate issued" if success else "certificate issuance failed"),
            provider=self.name,
            domain=session.domain,
            validation_method=session.validation_method,
            certificate_path=self._extract_path(output, r"Certificate is saved at:\s*(.+)"),
            private_key_path=self._extract_path(output, r"Key is saved at:\s*(.+)"),
            chain_path=self._extract_path(output, r"Chain is saved at:\s*(.+)"),
            raw_output=output or None,
            exit_code=process.returncode,
        )

    def _base_environment(self) -> dict[str, str]:
        return dict(os.environ)

    def _manual_dns_sessions_dir(self) -> Path:
        if self.settings is None:
            return Path.home() / ".northssl" / "manual-dns"
        return self.settings.data_dir / "manual-dns"

    def _manual_dns_hook_dir(self) -> Path:
        return self._manual_dns_sessions_dir() / "hooks"

    def _build_manual_dns_session(self, session_id: str, domain: str) -> ManualDnsChallengeSession:
        session_dir = self._manual_dns_sessions_dir() / session_id
        hook_dir = self._manual_dns_hook_dir()
        session_dir.mkdir(parents=True, exist_ok=True)
        hook_dir.mkdir(parents=True, exist_ok=True)

        hook_script = hook_dir / "auth.sh"
        cleanup_script = hook_dir / "cleanup.sh"
        challenge_file = session_dir / "challenge.json"
        ready_file = session_dir / "ready"

        return ManualDnsChallengeSession(
            session_id=session_id,
            domain=domain,
            provider=self.name,
            validation_method="dns-manual",
            record_name=f"_acme-challenge.{domain}",
            record_value="",
            started_at=datetime.now(timezone.utc),
            challenge_file_path=str(challenge_file),
            ready_file_path=str(ready_file),
            hook_script_path=str(hook_script),
            cleanup_script_path=str(cleanup_script),
        )

    def _ensure_manual_dns_hooks(self) -> None:
        hook_dir = self._manual_dns_hook_dir()
        hook_dir.mkdir(parents=True, exist_ok=True)
        auth_hook = hook_dir / "auth.sh"
        cleanup_hook = hook_dir / "cleanup.sh"

        if not auth_hook.exists():
            auth_hook.write_text(
                """#!/bin/sh
set -eu

: "${NORTHSSL_DNS01_SESSION_DIR:?Missing NORTHSSL_DNS01_SESSION_DIR}"
: "${NORTHSSL_DNS01_WAIT_SECONDS:=1800}"

session_dir="$NORTHSSL_DNS01_SESSION_DIR"
challenge_file="$session_dir/challenge.json"
ready_file="$session_dir/ready"
mkdir -p "$session_dir"

cat > "$challenge_file" <<EOF
{"identifier":"${CERTBOT_IDENTIFIER}","validation":"${CERTBOT_VALIDATION}","record_name":"_acme-challenge.${CERTBOT_IDENTIFIER}","record_value":"${CERTBOT_VALIDATION}"}
EOF

elapsed=0
while [ ! -f "$ready_file" ]; do
  sleep "${NORTHSSL_DNS01_POLL_SECONDS:-1}"
  elapsed=$((elapsed + ${NORTHSSL_DNS01_POLL_SECONDS:-1}))
  if [ "$elapsed" -ge "$NORTHSSL_DNS01_WAIT_SECONDS" ]; then
    echo "Timed out waiting for DNS confirmation" >&2
    exit 1
  fi
done

exit 0
""",
                encoding="utf-8",
            )
            auth_hook.chmod(0o755)

        if not cleanup_hook.exists():
            cleanup_hook.write_text(
                """#!/bin/sh
set -eu

: "${NORTHSSL_DNS01_SESSION_DIR:?Missing NORTHSSL_DNS01_SESSION_DIR}"
rm -f "$NORTHSSL_DNS01_SESSION_DIR/challenge.json" "$NORTHSSL_DNS01_SESSION_DIR/ready"
exit 0
""",
                encoding="utf-8",
            )
            cleanup_hook.chmod(0o755)

    def _manual_dns_environment(self, session: ManualDnsChallengeSession) -> dict[str, str]:
        session_dir = Path(session.challenge_file_path or "").parent if session.challenge_file_path else self._manual_dns_sessions_dir() / session.session_id
        return {
            "NORTHSSL_DNS01_SESSION_ID": session.session_id,
            "NORTHSSL_DNS01_SESSION_DIR": str(session_dir),
            "NORTHSSL_DNS01_WAIT_SECONDS": str(self.settings.acme_dns_manual_wait_seconds if self.settings is not None else 1800),
            "NORTHSSL_DNS01_POLL_SECONDS": str(self.settings.acme_dns_manual_poll_seconds if self.settings is not None else 1),
        }

    def _wait_for_manual_dns_challenge_file(self, session: ManualDnsChallengeSession) -> None:
        challenge_path = Path(session.challenge_file_path or "")
        if not session.challenge_file_path:
            raise RuntimeError("DNS challenge file path is unavailable")

        with self._manual_sessions_lock:
            entry = self._manual_sessions.get(session.session_id)
        process = entry[0] if entry else None

        timeout_seconds = self.settings.acme_dns_manual_wait_seconds if self.settings is not None else 1800
        poll_seconds = self.settings.acme_dns_manual_poll_seconds if self.settings is not None else 1
        waited = 0
        while waited < timeout_seconds:
            if challenge_path.exists():
                payload = json.loads(challenge_path.read_text(encoding="utf-8"))
                session.record_name = payload.get("record_name", session.record_name)
                session.record_value = payload.get("record_value", session.record_value)
                session.message = "Create the TXT record in your DNS provider, then continue the challenge"
                session.status = "waiting"
                return

            if process is not None and process.poll() is not None:
                try:
                    out, err = process.communicate(timeout=2)
                except Exception:
                    out, err = "", ""
                certbot_output = ((out or "") + (err or "")).strip()
                session.raw_output = certbot_output or "certbot exited with no output"
                session.status = "failed"
                break

            sleep(poll_seconds)
            waited += poll_seconds

        if challenge_path.exists():
            payload = json.loads(challenge_path.read_text(encoding="utf-8"))
            session.record_name = payload.get("record_name", session.record_name)
            session.record_value = payload.get("record_value", session.record_value)
            session.message = "Create the TXT record in your DNS provider, then continue the challenge"
            session.status = "waiting"
            return

        certbot_error = getattr(session, "raw_output", "") or "no output"
        raise RuntimeError(f"Certbot exited before producing a DNS challenge. Output: {certbot_error}")
