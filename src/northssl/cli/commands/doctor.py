import json
from dataclasses import asdict

import typer

from northssl.core.services.diagnostics import collect_diagnostics

doctor_app = typer.Typer(add_completion=False, help="Platform diagnostics.")

@doctor_app.callback(invoke_without_command=True)
def doctor_command(json_output: bool = typer.Option(False, "--json", help="Emit diagnostics as JSON.")) -> None:
    report = collect_diagnostics()

    if json_output:
        typer.echo(json.dumps(asdict(report), indent=2))
        raise typer.Exit(code=0)

    typer.secho("NorthSSL doctor", bold=True)
    typer.echo("Platform:")
    typer.echo(f"  - System: {report.platform.system}")
    typer.echo(f"  - Release: {report.platform.release}")
    typer.echo(f"  - Machine: {report.platform.machine}")
    typer.echo(f"  - Python: {report.platform.python_version}")
    typer.echo(f"  - Hostname: {report.platform.hostname}")
    typer.echo(f"  - FQDN: {report.platform.fqdn}")
    typer.echo(f"  - User: {report.platform.username}")
    typer.echo(f"  - Working dir: {report.platform.current_directory}")

    if report.platform.distribution:
        typer.echo("  - Linux distro:")
        typer.echo(f"      name: {report.platform.distribution.name}")
        typer.echo(f"      id: {report.platform.distribution.distribution_id}")
        typer.echo(f"      version: {report.platform.distribution.version_id}")
        typer.echo(f"      codename: {report.platform.distribution.codename}")
        typer.echo(f"      pretty: {report.platform.distribution.pretty_name}")

    typer.echo("Privileges:")
    typer.echo(f"  - Elevated: {report.privilege.elevated}")
    typer.echo(f"  - Mechanism: {report.privilege.mechanism}")
    typer.echo(f"  - Username: {report.privilege.username}")
    typer.echo(f"  - UID: {report.privilege.uid}")
    typer.echo(f"  - GID: {report.privilege.gid}")

    typer.echo("Web servers:")
    for webserver in report.webservers:
        typer.echo(f"  - {webserver.name}")
        typer.echo(f"      installed: {webserver.installed}")
        typer.echo(f"      active: {webserver.active}")
        typer.echo(f"      binary: {webserver.binary_path}")
        typer.echo(f"      version: {webserver.version}")
        typer.echo(f"      service: {webserver.service_name}")
        typer.echo(f"      process: {webserver.process_name} ({webserver.process_id})")
        typer.echo(f"      config: {', '.join(webserver.config_paths) if webserver.config_paths else 'n/a'}")
        typer.echo(f"      ports: {', '.join(str(port) for port in webserver.ports) if webserver.ports else 'n/a'}")

    typer.echo("Certbot:")
    typer.echo(f"  - installed: {report.certbot.installed if report.certbot else False}")
    typer.echo(f"  - binary: {report.certbot.binary_path if report.certbot else None}")
    typer.echo(f"  - version: {report.certbot.version if report.certbot else None}")
    typer.echo(f"  - compatible: {report.certbot.compatible if report.certbot else False}")

    typer.echo("Ports:")
    for port in report.ports:
        status = "occupied" if port.occupied else "free"
        process = f" {port.process_name} ({port.process_id})" if port.process_name or port.process_id else ""
        typer.echo(f"  - {port.port}/{port.protocol}: {status}{process}")

    if report.tools:
        typer.echo("Tools:")
        for tool in report.tools:
            status = "found" if tool.available else "missing"
            location = f" ({tool.path})" if tool.path else ""
            typer.echo(f"  - {tool.name}: {status}{location}")

    if report.warnings:
        typer.echo("Warnings:")
        for warning in report.warnings:
            typer.echo(f"  - {warning}")
