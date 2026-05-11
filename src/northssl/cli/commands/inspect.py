from __future__ import annotations

import json
from dataclasses import asdict

import typer

from northssl.core.exceptions import NorthSSLError
from northssl.core.services.certificate_engine import CertificateEngine


def inspect_command(
    ctx: typer.Context,
    target: str = typer.Argument(..., help="Certificate domain or certificate file path."),
    json_output: bool = typer.Option(False, "--json", help="Emit inspection as JSON."),
) -> None:
    engine = CertificateEngine(ctx.obj.settings)

    try:
        result = engine.inspect(target)
    except NorthSSLError as exc:
        typer.secho(f"Error: {exc}", err=True, fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    if json_output:
        typer.echo(json.dumps(asdict(result), indent=2, default=str))
        return

    typer.secho("Certificate inspection", bold=True)
    typer.echo(f"Domain: {result.domain}")
    typer.echo(f"Provider: {result.provider}")
    typer.echo(f"Certificate: {result.certificate_path}")
    typer.echo(f"Issuer: {result.issuer}")
    typer.echo(f"SANs: {', '.join(result.sans) if result.sans else 'n/a'}")
    typer.echo(f"Expires at: {result.expires_at}")
    typer.echo(f"Status: {result.status}")