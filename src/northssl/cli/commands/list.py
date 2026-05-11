from __future__ import annotations

import json
from dataclasses import asdict

import typer

from northssl.core.services.certificate_engine import CertificateEngine

def list_command(ctx: typer.Context, json_output: bool = typer.Option(False, "--json", help="Emit records as JSON.")) -> None:
    engine = CertificateEngine(ctx.obj.settings)
    certificates = engine.list()

    if json_output:
        typer.echo(json.dumps([asdict(cert) for cert in certificates], indent=2, default=str))
        return

    if not certificates:
        typer.echo("No certificates found.")
        return

    for certificate in certificates:
        typer.echo(f"{certificate.domain} | {certificate.status} | {certificate.provider} | {certificate.expires_at}")