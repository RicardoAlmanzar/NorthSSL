from dataclasses import asdict
import json

import typer

from northssl.core.services.diagnostics import collect_diagnostics


def status_command(ctx: typer.Context, json_output: bool = typer.Option(False, "--json", help="Emit status as JSON.")) -> None:
    settings = ctx.obj.settings
    diagnostics = collect_diagnostics()

    if json_output:
        typer.echo(json.dumps({"settings": settings.model_dump(mode="json"), "diagnostics": asdict(diagnostics)}, indent=2))
        raise typer.Exit(code=0)

    typer.secho("NorthSSL status", bold=True)
    typer.echo(f"Version: {settings.version}")
    typer.echo(f"Environment: {settings.environment}")
    typer.echo(f"Debug: {settings.debug}")
    typer.echo(f"Log level: {settings.log_level}")
    typer.echo(f"Data dir: {settings.data_dir}")
    typer.echo(f"Database path: {settings.database_path}")
    typer.echo(f"Platform: {diagnostics.platform.system} {diagnostics.platform.release}")
    typer.echo(f"Privilege: {diagnostics.privilege.mechanism} (elevated={diagnostics.privilege.elevated})")
    typer.echo(f"Certbot: {'installed' if diagnostics.certbot and diagnostics.certbot.installed else 'missing'}")
    typer.echo(f"Web servers discovered: {len(diagnostics.webservers)}")
    typer.echo(f"Ports inspected: {', '.join(str(port.port) for port in diagnostics.ports) if diagnostics.ports else 'none'}")

    if diagnostics.tools:
        typer.echo("Tools:")
        for tool in diagnostics.tools:
            status = "found" if tool.available else "missing"
            location = f" ({tool.path})" if tool.path else ""
            typer.echo(f"  - {tool.name}: {status}{location}")
