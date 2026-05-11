from __future__ import annotations

import json
from dataclasses import asdict

import typer

from northssl.core.exceptions import NorthSSLError
from northssl.core.services.certificate_engine import CertificateEngine


def issue_command(
    ctx: typer.Context,
    domain: str = typer.Argument(..., help="Domain to secure."),
    email: str | None = typer.Option(None, "--email", help="ACME account email."),
    provider: str = typer.Option("certbot", "--provider", help="SSL provider to use."),
    validation_method: str = typer.Option("standalone", "--validation", help="Validation method."),
    webroot_path: str | None = typer.Option(None, "--webroot-path", help="Path served for HTTP-01 webroot challenges."),
    json_output: bool = typer.Option(False, "--json", help="Emit result as JSON."),
) -> None:
    engine = CertificateEngine(ctx.obj.settings)

    try:
        metadata = engine.issue(
            domain,
            provider_name=provider,
            email=email,
            validation_method=validation_method,
            webroot_path=webroot_path,
        )
    except NorthSSLError as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    if json_output:
        typer.echo(json.dumps(asdict(metadata), indent=2, default=str))
        return

    typer.secho("Certificate issued", bold=True)
    typer.echo(f"Domain: {metadata.domain}")
    typer.echo(f"Provider: {metadata.provider}")
    typer.echo(f"Certificate: {metadata.certificate_path}")
    typer.echo(f"Private key: {metadata.private_key_path}")
    typer.echo(f"Expires at: {metadata.expires_at}")