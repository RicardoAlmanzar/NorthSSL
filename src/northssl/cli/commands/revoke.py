from __future__ import annotations

import json
from dataclasses import asdict

import typer

from northssl.core.exceptions import NorthSSLError
from northssl.core.services.certificate_engine import CertificateEngine


def revoke_command(
    ctx: typer.Context,
    domain: str = typer.Argument(..., help="Domain to revoke."),
    provider: str = typer.Option("certbot", "--provider", help="SSL provider to use."),
    reason: str = typer.Option("keycompromise", "--reason", help="Revocation reason."),
    yes: bool = typer.Option(False, "--yes", help="Confirm revocation without prompting."),
    json_output: bool = typer.Option(False, "--json", help="Emit result as JSON."),
) -> None:
    if not yes:
        typer.secho("Pass --yes to confirm revocation.", err=True, fg=typer.colors.YELLOW)
        raise typer.Exit(code=2)

    engine = CertificateEngine(ctx.obj.settings)

    try:
        metadata = engine.revoke(domain, provider_name=provider, reason=reason)
    except NorthSSLError as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    if json_output:
        typer.echo(json.dumps(asdict(metadata), indent=2, default=str))
        return

    typer.secho("Certificate revoked", bold=True)
    typer.echo(f"Domain: {metadata.domain}")
    typer.echo(f"Status: {metadata.status}")